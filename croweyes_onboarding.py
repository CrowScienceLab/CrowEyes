"""Store first-run consent, stable AUMID shortcut, and honest association guidance."""
import ctypes
import os
from pathlib import Path
import shutil
import subprocess
import sys
import uuid
import tkinter as tk
from tkinter import ttk


def package_family():
    kernel=ctypes.WinDLL('kernel32',use_last_error=True)
    fn=kernel.GetCurrentPackageFamilyName
    fn.argtypes=[ctypes.POINTER(ctypes.c_uint32),ctypes.c_wchar_p];fn.restype=ctypes.c_long
    length=ctypes.c_uint32()
    if fn(ctypes.byref(length),None)!=122:raise OSError('Store 패키지 식별자가 없습니다.')
    buffer=ctypes.create_unicode_buffer(length.value)
    if fn(ctypes.byref(length),buffer)!=0:raise OSError('Store 패키지 식별자를 읽지 못했습니다.')
    return buffer.value


def desktop_path():
    from ctypes import wintypes
    guid=ctypes.create_string_buffer(uuid.UUID('B4BFCC3A-DB2C-424C-B029-7FE99A87C641').bytes_le)
    shell=ctypes.WinDLL('shell32');fn=shell.SHGetKnownFolderPath
    fn.argtypes=[ctypes.c_void_p,wintypes.DWORD,wintypes.HANDLE,ctypes.POINTER(ctypes.c_void_p)]
    fn.restype=ctypes.c_long;pointer=ctypes.c_void_p()
    if fn(guid,0,None,ctypes.byref(pointer))<0:raise OSError('바탕화면 경로를 찾지 못했습니다.')
    try:return Path(ctypes.wstring_at(pointer))
    finally:
        free=ctypes.WinDLL('ole32').CoTaskMemFree;free.argtypes=[ctypes.c_void_p];free(pointer)


def create_store_shortcut(icon_source,*,destination=None,icon_cache=None):
    aumid=package_family()+'!CrowEyes'
    target=(desktop_path() if destination is None else Path(destination))/'CrowEyes.lnk'
    if target.exists():raise FileExistsError('CrowEyes 바로가기가 이미 있습니다. 기존 파일은 유지했습니다.')
    icon=Path(icon_cache) if icon_cache else Path(os.environ.get('LOCALAPPDATA',str(Path.home())))/'CrowEyes'/'shortcut'/'CrowEyes.ico'
    icon.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(icon_source,icon)
    def quote(value):return "'"+str(value).replace("'","''")+"'"
    explorer=Path(os.environ.get('WINDIR','C:/Windows'))/'explorer.exe'
    command=("$ErrorActionPreference='Stop';$shell=New-Object -ComObject WScript.Shell;"
             f"$link=$shell.CreateShortcut({quote(target)});$link.TargetPath={quote(explorer)};"
             f"$link.Arguments={quote('shell:AppsFolder'+chr(92)+aumid)};"
             f"$link.IconLocation={quote(str(icon)+',0')};$link.Description='CrowEyes';$link.Save()")
    subprocess.run(['powershell.exe','-NoProfile','-NonInteractive','-Command',command],capture_output=True,
                   timeout=15,check=True,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    if not target.exists():raise OSError('바로가기를 저장하지 못했습니다.')
    return target


def show_store_onboarding(viewer):
    from croweyes_dialogs import FittedDialog
    core=sys.modules[viewer.__class__.__module__]
    if viewer.settings.get('store_onboarding_complete'):return
    win=FittedDialog(viewer,'CrowEyes 설치 후 시작 설정',660)
    body=win.body
    ttk.Label(body,text='바탕화면에 CrowEyes 바로가기를 추가할까요?',style='Section.TLabel').pack(anchor='w',pady=(0,8))
    ttk.Label(body,text='추가하면 Store 업데이트 뒤에도 같은 바로가기로 실행할 수 있습니다.\n아래에서 추가 또는 추가하지 않음을 선택해 주세요.',wraplength=590).pack(anchor='w')
    ttk.Separator(body).pack(fill='x',pady=14)
    ttk.Label(body,text='이미지 연결 프로그램 등록 안내',style='Section.TLabel').pack(anchor='w',pady=(0,6))
    ttk.Label(body,text='지원 이미지 형식은 Store 패키지 설치 과정에서 연결 프로그램 후보로 등록됩니다.\n기존 Windows 기본 앱은 유지합니다. CrowEyes를 기본 앱으로 사용하려면 Windows 설정에서 직접 선택해 주세요.',wraplength=590,justify='left').pack(anchor='w')
    status=tk.StringVar()
    ttk.Label(body,textvariable=status,wraplength=590).pack(anchor='w',pady=10)
    buttons=ttk.Frame(body);buttons.pack(fill='x',pady=(6,0))
    def finish(add):
        if add:
            try:create_store_shortcut(core.resource_path('assets','icons','croweyes-2.0.ico'))
            except FileExistsError as exc:status.set(str(exc))
            except Exception as exc:status.set('바로가기 추가 실패: '+str(exc));return
        viewer.settings.update(store_onboarding_complete=True,store_desktop_shortcut_requested=bool(add),
                               initial_associations_registered=True)
        core.save_settings(viewer.settings);win.destroy()
        viewer.status.configure(text='Store 연결 프로그램 등록 안내 완료 · 기본 앱은 Windows 설정에서 선택하세요.')
        if viewer.settings.get('auto_check_updates',True):viewer.after(300,lambda:viewer.check_for_updates(False))
    ttk.Button(buttons,text='바로가기 추가',style='Accent.TButton',command=lambda:finish(True)).pack(side='left',padx=(0,8))
    ttk.Button(buttons,text='추가하지 않음',command=lambda:finish(False)).pack(side='left')
    ttk.Button(buttons,text='Windows 기본 앱 설정',command=lambda:os.startfile('ms-settings:defaultapps')).pack(side='right')
    return win
