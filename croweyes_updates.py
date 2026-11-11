"""Independent GitHub/Store checks, explicit partial failures, Store wins ties."""
import json
import re
import sys
import threading
import time
import urllib.request
from urllib.parse import urlparse
import webbrowser
import os
from tkinter import messagebox

STORE_ID='9NNHX36VPSQZ'
STORE_FEED='https://raw.githubusercontent.com/CrowScienceLab/CrowEyes/main/update-channels.json'


def version_key(value):
    if not isinstance(value,str) or not re.fullmatch(r'v?\d+(?:\.\d+){0,3}',value):raise ValueError('올바르지 않은 버전 정보')
    parts=tuple(map(int,value.lstrip('v').split('.')))
    return parts+(0,)*(4-len(parts))


def published_store(data):
    item=data.get('store',{})
    if item.get('product_id')!=STORE_ID or item.get('published') is not True:
        raise ValueError('Store 게시가 확인된 버전 정보가 없습니다.')
    version_key(item.get('version'))
    return dict(status='ok',version=item['version'],source='게시 확인 정보')


def select_update(current,github,store):
    base=version_key(current);choices=[]
    for channel,item in [('github',github),('store',store)]:
        if item.get('status')!='ok':continue
        version=item.get('version')
        if version and version_key(version)>base:
            if channel=='store' and item.get('available') is False:continue
            choices.append((version_key(version),channel,item))
    # StoreContext can prove an update is available without revealing a target version.
    if store.get('status')=='ok' and store.get('available') is True and not store.get('version'):
        return 'store',store
    if not choices:return None
    _,channel,item=max(choices,key=lambda row:(row[0],row[1]=='store'))
    return channel,item


def fetch_json(url,version):
    request=urllib.request.Request(url,headers={'Accept':'application/json','User-Agent':f'CrowEyes/{version}'})
    with urllib.request.urlopen(request,timeout=12) as response:
        raw=response.read(2*1024*1024+1)
        if len(raw)>2*1024*1024:raise ValueError('업데이트 응답 크기 초과')
    value=json.loads(raw.decode('utf-8-sig'))
    if not isinstance(value,dict):raise ValueError('잘못된 업데이트 응답')
    return value


class UpdateCoordinator:
    def __init__(self,viewer):
        self.viewer=viewer;self.core=sys.modules[viewer.__class__.__module__]
        self.generation=0;self.operation=None;self.context=None

    def start(self,manual=False):
        self.generation+=1;generation=self.generation
        if self.operation:
            try:self.operation.cancel()
            except Exception:pass
        self.operation=None;results={};deadline=time.monotonic()+16
        self.viewer.status.configure(text='GitHub · Microsoft Store 업데이트를 확인하는 중…')
        def worker(kind,url):
            try:
                payload=fetch_json(url,self.core.APP_VERSION)
                if kind=='github':
                    version_key(payload.get('tag_name'))
                    if payload.get('draft') or payload.get('prerelease'):raise ValueError('정식 릴리스가 아닙니다.')
                    value=dict(status='ok',version=payload['tag_name'],release=payload)
                else:value=published_store(payload)
            except Exception as exc:value=dict(status='error',error=str(exc))
            results[kind]=value
        for kind,url in [('github',self.core.GITHUB_RELEASES_URL),('store_feed',STORE_FEED)]:
            threading.Thread(target=worker,args=(kind,url),name=f'CrowEyesUpdate-{kind}',daemon=True).start()
        packaged=self.core.is_microsoft_store_package()
        if not packaged:
            def catalog_worker():
                try:
                    request=urllib.request.Request(self.core.MICROSOFT_STORE_URL,method='HEAD',headers={'User-Agent':f'CrowEyes/{self.core.APP_VERSION}'})
                    with urllib.request.urlopen(request,timeout=12) as response:
                        if urlparse(response.url).hostname!='apps.microsoft.com':raise ValueError('잘못된 Store 응답 경로')
                    results['store_catalog']=dict(status='ok')
                except Exception as exc:results['store_catalog']=dict(status='error',error=str(exc))
            threading.Thread(target=catalog_worker,name='CrowEyesUpdate-StoreCatalog',daemon=True).start()
        if packaged:
            try:
                # Start on the Tk/UI thread and poll completion without blocking it.
                from winrt.windows.services.store import StoreContext
                from winrt.runtime.interop import initialize_with_window
                self.context=StoreContext.get_default()
                initialize_with_window(self.context,self.viewer._native_owner())
                self.operation=self.context.get_app_and_optional_store_package_updates_async()
            except Exception as exc:results['store_api']=dict(status='error',error=str(exc))
        self.viewer.after(80,lambda:self._poll(generation,manual,packaged,results,deadline))

    def _poll(self,generation,manual,packaged,results,deadline):
        if generation!=self.generation:return
        if packaged and 'store_api' not in results and self.operation:
            try:
                status=int(self.operation.status)
                if status==1:
                    updates=self.operation.get_results()
                    results['store_api']=dict(status='ok',available=bool(len(updates)),source='Store 공식 API')
                elif status in (2,3):raise OSError('Store 업데이트 조회를 완료하지 못했습니다.')
            except Exception as exc:results['store_api']=dict(status='error',error=str(exc))
        needed=['github','store_feed']+(['store_api'] if packaged else ['store_catalog'])
        if not all(k in results for k in needed) and time.monotonic()<deadline:
            self.viewer.after(100,lambda:self._poll(generation,manual,packaged,results,deadline));return
        for key in needed:results.setdefault(key,dict(status='error',error='확인 시간 초과'))
        if self.operation:
            try:self.operation.cancel() if '시간 초과' in results.get('store_api',{}).get('error','') else None
            except Exception:pass
        store=results['store_feed'].copy()
        if not packaged and results['store_catalog']['status']!='ok':store=results['store_catalog']
        if packaged and results['store_api']['status']=='ok':
            api=results['store_api'];store.update(api)
            if api['available'] and store.get('version') and version_key(store['version'])<=version_key(self.core.APP_VERSION):
                store.pop('version',None)
        self.viewer.settings['last_update_check']=time.time();self.core.save_settings(self.viewer.settings)
        github=results['github'];choice=select_update(self.core.APP_VERSION,github,store)
        errors=[]
        if github['status']!='ok':errors.append('GitHub 확인 실패')
        if store['status']!='ok':errors.append('Microsoft Store 확인 실패')
        if packaged and results['store_api']['status']!='ok':errors.append('Store 공식 API 확인 실패 · 게시 확인 정보 사용')
        detail='\n'.join([f'GitHub: {github.get("version", "확인 실패")}',
                          f'Microsoft Store: {store.get("version") or ("새 업데이트 있음" if store.get("available") else "현재 설치 최신" if store.get("status")=="ok" else "확인 실패")}',
                          '같은 최신 버전은 Microsoft Store를 우선합니다.'])
        if not choice:
            text='일부 업데이트 경로를 확인하지 못했습니다.' if errors else f'CrowEyes {self.core.APP_VERSION}이 최신 버전입니다.'
            self.viewer.status.configure(text=text)
            if manual:messagebox.showinfo('업데이트 확인',text+'\n\n'+detail,parent=self.viewer)
            return
        channel,item=choice;target=item.get('version','새 버전')
        self.viewer.status.configure(text=f'{channel}: {target} 업데이트 가능'+(' · 일부 확인 실패' if errors else ''))
        if channel=='store' or packaged:
            explanation='Microsoft Store에서 업데이트할 수 있습니다.' if channel=='store' else 'GitHub에 새 버전이 있습니다. Store 설치형은 Store 배포를 확인해 주세요.'
            if messagebox.askyesno('CrowEyes 업데이트',explanation+'\n\n'+detail+'\n\nMicrosoft Store를 열까요?',parent=self.viewer):
                try:os.startfile(self.core.MICROSOFT_STORE_URI)
                except OSError:webbrowser.open(self.core.MICROSOFT_STORE_URL)
        elif messagebox.askyesno('CrowEyes 업데이트',f'새 버전 {target}\n\n{detail}\n\nGitHub에서 내려받고 SHA-256을 확인할까요?',parent=self.viewer):
            self.viewer._show_update_download(item['release'])
