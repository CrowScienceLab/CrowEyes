"""Check only the distribution channel of the running CrowEyes executable."""
from concurrent.futures import Future
import json
import os
import re
import sys
import threading
import time
from tkinter import messagebox
import urllib.request
import webbrowser


def version_key(value):
    if not isinstance(value, str) or not re.fullmatch(r'v?\d+(?:\.\d+){0,3}', value):
        raise ValueError('올바르지 않은 버전 정보')
    parts = tuple(map(int, value.lstrip('v').split('.')))
    return parts + (0,) * (4 - len(parts))


def fetch_json(url, version):
    request = urllib.request.Request(url, headers={'Accept': 'application/json', 'User-Agent': f'CrowEyes/{version}'})
    with urllib.request.urlopen(request, timeout=12) as response:
        raw = response.read(2 * 1024 * 1024 + 1)
    if len(raw) > 2 * 1024 * 1024:
        raise ValueError('업데이트 응답 크기 초과')
    value = json.loads(raw.decode('utf-8-sig'))
    if not isinstance(value, dict):
        raise ValueError('잘못된 업데이트 응답')
    return value


class UpdateCoordinator:
    def __init__(self, viewer):
        self.viewer = viewer
        self.core = sys.modules[viewer.__class__.__module__]
        self.is_store = viewer._runs_as_store
        self.channel = 'Microsoft Store' if self.is_store else 'GitHub'
        self.result = None
        self.manual = False
        self.store_context = None
        self.store_operation = None

    def start(self, manual=False):
        self.manual |= manual
        if self.result is not None:
            return
        self.result = Future()
        deadline = time.monotonic() + 16
        self.viewer.status.configure(text=f'{self.channel} 업데이트를 확인하는 중…')
        if self.is_store:
            try:
                # StoreContext needs the UI thread and the application's HWND.
                from winrt.windows.services.store import StoreContext
                from winrt.runtime.interop import initialize_with_window

                self.store_context = StoreContext.get_default()
                initialize_with_window(self.store_context, self.viewer._native_owner())
                self.store_operation = self.store_context.get_app_and_optional_store_package_updates_async()
            except Exception as exc:
                self.result.set_exception(exc)
        else:
            threading.Thread(
                target=self._query_github, args=(self.result,), name='CrowEyesUpdate-GitHub', daemon=True,
            ).start()
        self.viewer.after(80, self._poll, deadline)

    def _query_github(self, result):
        try:
            release = fetch_json(self.core.GITHUB_RELEASES_URL, self.core.APP_VERSION)
            if release.get('draft') or release.get('prerelease'):
                raise ValueError('정식 릴리스가 아닙니다.')
            available = version_key(release.get('tag_name')) > version_key(self.core.APP_VERSION)
            result.set_result(release if available else None)
        except Exception as exc:
            result.set_exception(exc)

    def _poll(self, deadline):
        result = self.result
        if self.store_operation is not None and not result.done():
            try:
                status = int(self.store_operation.status)
                if status == 1:  # AsyncStatus.COMPLETED
                    result.set_result(bool(len(self.store_operation.get_results())))
                elif status != 0:  # AsyncStatus.STARTED
                    raise OSError('Store 업데이트 조회를 완료하지 못했습니다.')
            except Exception as exc:
                result.set_exception(exc)
        if not result.done() and time.monotonic() < deadline:
            self.viewer.after(100, self._poll, deadline)
            return

        if not result.done() and self.store_operation is not None:
            try:
                self.store_operation.cancel()
            except Exception:
                pass
        self.store_operation = self.store_context = self.result = None
        manual, self.manual = self.manual, False
        try:
            update = result.result(timeout=0)
        except Exception as exc:
            text = f'{self.channel} 업데이트를 확인하지 못했습니다.'
            self.viewer.status.configure(text=text)
            if manual:
                detail = '확인 시간이 초과되었습니다.' if isinstance(exc, TimeoutError) else str(exc)
                messagebox.showwarning('업데이트 확인', f'{text}\n\n{detail}', parent=self.viewer)
            return

        self.viewer.settings['last_update_check'] = time.time()
        self.core.save_settings(self.viewer.settings)
        if not update:
            text = f'{self.channel}에서 CrowEyes {self.core.APP_VERSION}이 최신 버전입니다.'
            self.viewer.status.configure(text=text)
            if manual:
                messagebox.showinfo('업데이트 확인', text, parent=self.viewer)
        elif self.is_store:
            text = 'Microsoft Store에서 CrowEyes 업데이트를 사용할 수 있습니다.'
            self.viewer.status.configure(text=text)
            if messagebox.askyesno('CrowEyes 업데이트', text + '\n\nMicrosoft Store를 열까요?', parent=self.viewer):
                try:
                    os.startfile(self.core.MICROSOFT_STORE_URI)
                except OSError:
                    webbrowser.open(self.core.MICROSOFT_STORE_URL)
        else:
            text = f'GitHub에 CrowEyes {update["tag_name"]} 업데이트가 있습니다.'
            self.viewer.status.configure(text=text)
            if messagebox.askyesno('CrowEyes 업데이트', text + '\n\n다운로드하고 SHA-256을 확인할까요?', parent=self.viewer):
                self.viewer._show_update_download(update)
