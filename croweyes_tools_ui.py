"""Tools are created on demand; workers never access Tk objects."""
import io
import json
import queue
import threading
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog
from PIL import Image, ImageTk


class FeaturesMixin:
    def __init__(self, *args, **kwargs):
        self._undo_states = []
        self._redo_states = []
        self._restoring = False
        self._catalog = None
        self._catalog_rows = {}
        self._collection_filter = {}
        self._provenance_values = {}
        self._tool_cancels = []
        super().__init__(*args, **kwargs)
        self.bind('<Control-z>', lambda e: self.undo_edit())
        self.bind('<Control-y>', lambda e: self.redo_edit())

    def _window(self, title, size=None):
        from croweyes_dialogs import EmbeddedDialog
        win=EmbeddedDialog(self,title,size)
        return win,win.body

    def _text(self, title, text):
        win, frame = self._window(title, '560x340')
        view = tk.Text(frame, wrap='word',width=45,height=8,background=self._theme()['panel'],foreground=self._theme()['fg'],insertbackground=self._theme()['fg'],relief='flat')
        view.pack(fill='both', expand=True)
        view.insert('1.0', text)
        view.configure(state='disabled')
        ttk.Button(frame, text='전체 복사', command=lambda: (self.clipboard_clear(), self.clipboard_append(text))).pack(pady=6)
        return win

    def _paths(self):
        return [p for p in self._selected_playlist_paths() if p.is_file()]

    def _guard_paths(self, paths, cancel):
        if self._content_filter_mode != 'explicit':
            return
        for path in paths:
            if cancel.is_set():
                return
            result=self._safety_manager.check(path,vector_loader=self._safety_vector_loader)
            if result.status != 'SAFE':
                raise ValueError(path.name+' · 콘텐츠 필터에 의해 작업이 제한되었습니다.')

    def _job(self, title, work, done):
        win, frame = self._window(title,'460x220')
        progress = ttk.Progressbar(frame, length=220, maximum=100)
        progress.pack(fill='x')
        status = ttk.Label(frame, text='작업 준비 중')
        status.pack(pady=8)
        cancelled = threading.Event()
        messages = queue.Queue()
        self._tool_cancels.append(cancelled)
        ttk.Button(frame, text='취소', command=cancelled.set).pack()
        win.protocol('WM_DELETE_WINDOW', cancelled.set)

        def worker():
            try:
                result = work(cancelled, lambda i, n: messages.put(('progress', i, n)))
                messages.put(('result', result))
            except Exception as exc:
                messages.put(('error', str(exc)))

        def poll():
            try:
                while True:
                    msg = messages.get_nowait()
                    if msg[0] == 'progress':
                        progress['value'] = msg[1] / max(1, msg[2]) * 100
                        status.configure(text=f'{msg[1]} / {msg[2]}' + (' · 취소 중' if cancelled.is_set() else ''))
                    else:
                        win.destroy()
                        self._tool_cancels.remove(cancelled)
                        if msg[0] == 'error':
                            self._text(title,msg[1])
                        else:
                            done(msg[1])
                        return
            except queue.Empty:
                self.after(60, poll)

        threading.Thread(target=worker, daemon=True, name='CrowEyesTool').start()
        self.after(60, poll)

    def _state(self):
        return self.rotation, self.flip_h, self.flip_v, self.brightness, self.contrast

    def _record(self):
        if self._restoring or self.pil_image is None:
            return
        state = self._state()
        if not self._undo_states or self._undo_states[-1] != state:
            self._undo_states.append(state)
            self._undo_states = self._undo_states[-100:]
        self._redo_states.clear()

    def rotate(self, degrees):
        self._record()
        super().rotate(degrees)

    def toggle_flip_h(self):
        self._record()
        super().toggle_flip_h()

    def toggle_flip_v(self):
        self._record()
        super().toggle_flip_v()

    def _on_adjust(self, value=None):
        self._record()
        super()._on_adjust(value)

    def _restore_state(self, state):
        self._restoring = True
        self.rotation, self.flip_h, self.flip_v, self.brightness, self.contrast = state
        self.bright_var.set(self.brightness)
        self.contrast_var.set(self.contrast)
        self._rotation_text_var.set(f'{self.rotation}°')
        self._rebuild_display()
        self.redraw()
        self._update_info()
        self._restoring = False

    def undo_edit(self):
        if self._undo_states:
            self._redo_states.append(self._state())
            self._restore_state(self._undo_states.pop())
        return 'break'

    def redo_edit(self):
        if self._redo_states:
            self._undo_states.append(self._state())
            self._restore_state(self._redo_states.pop())
        return 'break'

    def restore_original(self):
        self._record()
        self._restore_state((0, False, False, 1.0, 1.0))

    def goto_index(self, idx, from_list=False):
        if idx != self.index:
            self._undo_states.clear()
            self._redo_states.clear()
        super().goto_index(idx, from_list)

    def zoom_by(self, factor, event=None):
        if self.display_image is None:
            return
        self._interrupt_slideshow()
        old = self.zoom
        new = max(0.02, min(32.0, old * factor))
        x = event.x if event is not None else self.canvas.winfo_width()/2
        y = event.y if event is not None else self.canvas.winfo_height()/2
        cx, cy = self.canvas.winfo_width()/2, self.canvas.winfo_height()/2
        self.offset_x = (x-cx) - ((x-cx)-self.offset_x)*new/old
        self.offset_y = (y-cy) - ((y-cy)-self.offset_y)*new/old
        self.zoom, self._view_mode = new, 'custom'
        self.redraw()
        self._maybe_rerender_vector()
        self._update_info()

    def _on_mousewheel(self, event):
        if self.settings.get('mouse_wheel_action') == 'zoom':
            factor = float(self.settings.get('wheel_zoom', 1.15))
            delta = getattr(event, 'delta', 0) or (120 if getattr(event, 'num', 0) == 4 else -120)
            self.zoom_by(factor if delta > 0 else 1/factor, event)
            return 'break'
        return super()._on_mousewheel(event)

    def batch_dialog(self):
        from croweyes_workflows import batch
        paths = self._paths()
        if not paths:
            return
        win, frame = self._window(f'일괄 처리 · {len(paths)}장')
        variables = {}
        for row, (key, label, default) in enumerate((('folder','출력 폴더',''),('width','가로 (0: 원본)','0'),('height','세로 (0: 원본)','0'),('prefix','이름 접두사 (빈 값: 원래 이름)',''),('quality','품질 (1~100)','90'))):
            variables[key] = tk.StringVar(value=default)
            ttk.Label(frame, text=label).grid(row=row, column=0, sticky='w', pady=4)
            ttk.Entry(frame, textvariable=variables[key], width=40).grid(row=row, column=1)
        ttk.Button(frame, text='폴더 선택', command=lambda: variables['folder'].set(filedialog.askdirectory(parent=win))).grid(row=0,column=2)
        fmt = tk.StringVar(value='.jpg')
        ttk.Combobox(frame, textvariable=fmt, values=['.jpg','.png','.webp','.avif','.tiff','.bmp'], state='readonly').grid(row=5,column=1)
        ratio = tk.BooleanVar(value=True)
        ttk.Checkbutton(frame, text='비율 유지 (지정 상자 안에 맞춤)', variable=ratio).grid(row=6,column=0,columnspan=2)
        ttk.Label(frame, text='원본 보존 · 충돌 시 번호 추가 · EXIF/GPS 제거 · 결과 JSON 저장').grid(row=7,column=0,columnspan=3,pady=8)

        def start():
            try:
                width, height, quality = (int(variables[k].get()) for k in ('width','height','quality'))
                folder, prefix, suffix, keep = variables['folder'].get(), variables['prefix'].get(), fmt.get(), ratio.get()
                if not folder or not 1 <= quality <= 100 or min(width,height) < 0 or bool(width) != bool(height):
                    raise ValueError('폴더·품질·가로/세로를 확인하세요. 원본 크기는 둘 다 0입니다.')
                if width:
                    from croweyes_editing import validate_size
                    validate_size(width,height)
                win.destroy()
                def work(c,p):
                    self._guard_paths(paths,c)
                    return batch(paths,folder,width,height,suffix,quality,prefix,c,p,keep)
                self._job('일괄 처리',work,lambda result:self._text('일괄 처리 결과',str(result[0])+'\n'+json.dumps(result[1],ensure_ascii=False,indent=2)))
            except ValueError as exc:
                messagebox.showerror('일괄 처리', str(exc), parent=win)

        ttk.Button(frame, text='실행', command=start).grid(row=8,column=1,pady=8)

    def rename_batch_dialog(self):
        paths = self._paths()
        if not paths:
            return
        prefix = simpledialog.askstring('이름 변경', '접두사 + 0001 형식으로 변경합니다. 접두사:', parent=self)
        if not prefix:
            return
        if any(c in prefix for c in '/\\:*?"<>|'):
            messagebox.showerror('이름 변경','파일 이름에 사용할 수 없는 문자',parent=self)
            return
        targets = [p.with_name(prefix+f'{i+1:04d}'+p.suffix) for i,p in enumerate(paths)]
        if any(t.exists() and t != p for p,t in zip(paths,targets)):
            messagebox.showerror('이름 변경','대상 이름이 이미 있습니다. 다른 접두사를 사용하세요.',parent=self)
            return
        if not messagebox.askyesno('이름 변경', '\n'.join(p.name+' → '+t.name for p,t in list(zip(paths,targets))[:12])+f'\n총 {len(paths)}개 변경',parent=self):
            return
        completed = []
        try:
            for p,t in zip(paths,targets):
                p.rename(t)
                completed.append((p,t))
            if self._catalog:
                for p,t in completed:
                    self._catalog.move(p,t)
                self._catalog_rows = self._catalog.all()
        except OSError as exc:
            for p,t in reversed(completed):
                if not p.exists():
                    t.rename(p)
            messagebox.showerror('이름 변경',str(exc),parent=self)
        self.refresh_folder()

    def compare_before_after(self):
        if self.pil_image is not None:
            from croweyes_compare import show
            show(self,[self.pil_image,self.display_image],['원본','현재 편집'])

    def compare_selected(self):
        paths=self._paths()
        if len(paths) not in (2,4):
            messagebox.showinfo('비교','플레이리스트에서 Ctrl 키로 2장 또는 4장을 선택하세요.',parent=self)
            return
        from croweyes_workflows import open_image
        def work(c,p):
            self._guard_paths(paths,c)
            images=[]
            for i,path in enumerate(paths):
                if c.is_set():
                    return []
                image=open_image(path,preview=True)
                image.thumbnail((2048,2048))
                images.append(image)
                p(i+1,len(paths))
            return images
        def done(images):
            if images:
                from croweyes_compare import show
                show(self,images,[p.name for p in paths])
        self._job('비교 이미지 준비',work,done)

    def ocr_dialog(self):
        if self.display_image is None:
            return
        from croweyes_ocr import recognize
        image=self.display_image.copy()
        self._job('글자 인식',lambda c,p:recognize(image,c),lambda text:self._text('인식된 글자',text or '인식한 글자 없음'))

    def ocr_region(self):
        self.start_region_copy('ocr')

    def index_collection(self, ocr):
        self._ensure_catalog()
        paths=list(self.folder_files)
        catalog=self._catalog
        from croweyes_workflows import metadata,open_image
        def work(c,p):
            errors=[]
            for i,path in enumerate(paths):
                if c.is_set():
                    break
                try:
                    stat=path.stat()
                    fingerprint=f'{stat.st_size}:{stat.st_mtime_ns}'
                    if ocr:
                        self._guard_paths([path],c)
                        from croweyes_ocr import recognize
                        catalog.set(path,text=recognize(open_image(path,preview=True),c),fingerprint=fingerprint)
                    else:
                        info=metadata(path)
                        catalog.set(path,taken=str(info.get('DateTimeOriginal',info.get('DateTime',''))),fingerprint=fingerprint)
                except Exception as exc:
                    errors.append(path.name+': '+str(exc))
                p(i+1,len(paths))
            return errors
        def done(errors):
            self._catalog_rows=catalog.all()
            self._apply_playlist_filter()
            self._text('색인 결과','PC 검색 DB에 저장했습니다. 정리 → 촬영일·OCR 글자 검색에서 찾을 수 있습니다.\n취소된 작업은 완료된 항목까지 보존됩니다.\n'+('\n'.join(errors) if errors else '처리한 항목에 오류 없음'))
        self._job('OCR 색인' if ocr else '촬영 정보 색인',work,done)

    def _save_display_image(self, destination, image=None):
        self.quality_dialog(image=image, destination=destination)

    def quality_dialog(self, image=None, destination=None):
        if image is None:
            image = self.display_image
        if image is None:
            return
        from croweyes_workflows import encode, atomic_write
        # A snapshot is made only while the user explicitly edits/exports.
        image = image.copy()
        win, frame = self._window('저장 품질·메타데이터', '760x600')
        saved = self.settings.get('export_preset', {})
        quality = tk.IntVar(value=saved.get('quality',90))
        budget = tk.StringVar(value=str(saved.get('target_kib',0)))
        fmt = tk.StringVar(value=Path(destination).suffix if destination else '.jpg')
        preserve = tk.BooleanVar(value=False)
        ttk.Label(frame,text='형식').pack()
        ttk.Combobox(frame,textvariable=fmt,values=['.jpg','.png','.webp','.avif','.bmp','.tiff'],state='readonly').pack()
        ttk.Scale(frame,from_=1,to=100,variable=quality).pack(fill='x')
        ttk.Label(frame,textvariable=quality).pack()
        ttk.Label(frame,text='목표 KiB (0: 제한 없음)').pack()
        ttk.Entry(frame,textvariable=budget).pack()
        ttk.Checkbutton(frame,text='EXIF/GPS 보존 (기본값: 제거)',variable=preserve).pack()
        ttk.Label(frame,text='변경된 이미지의 이전 C2PA 인증 정보는 보존하지 않습니다.').pack()
        preview = ttk.Label(frame)
        preview.pack(fill='both',expand=True)
        info = ttk.Label(frame,text='미리보기를 누르면 실제 결과 용량과 압축 품질을 확인합니다.')
        info.pack()

        def values():
            q,b = int(quality.get()),int(budget.get())
            if not 1 <= q <= 100 or b < 0:
                raise ValueError('품질·목표 용량을 확인하세요.')
            return fmt.get(),q,b,preserve.get()

        def run(save=False):
            try:
                suffix,q,b,keep = values()
                target = destination
                if save:
                    target = filedialog.asksaveasfilename(parent=win,initialfile=Path(destination).name if destination else 'image'+suffix,defaultextension=suffix,filetypes=[('Image','*'+suffix)])
                    if not target:
                        return
                    if Path(target).suffix.lower() != suffix:
                        raise ValueError('선택 형식과 파일 확장자를 맞춰 주세요.')
                def work(c,p):
                    data = encode(image,suffix,q,b,keep)
                    if c.is_set():
                        return None
                    if save:
                        atomic_write(target,data)
                    return data
                def done(data):
                    if not data or not win.winfo_exists():
                        return
                    info.configure(text=f'{len(data)/1024:.1f} KiB'+(' · 저장 완료' if save else ' · 예상 저장 용량'))
                    with Image.open(io.BytesIO(data)) as result:
                        result.thumbnail((650,320))
                        preview.image = ImageTk.PhotoImage(result)
                        preview.configure(image=preview.image)
                    if save:
                        self.settings['export_preset']={'quality':q,'target_kib':b}
                self._job('저장' if save else '압축 미리보기',work,done)
            except Exception as exc:
                messagebox.showerror('저장',str(exc),parent=win)
        buttons=ttk.Frame(frame)
        buttons.pack()
        ttk.Button(buttons,text='미리보기',command=run).pack(side='left')
        ttk.Button(buttons,text='저장',command=lambda:run(True)).pack(side='left')

    def metadata_dialog(self):
        if not self.source_path:
            return
        from croweyes_workflows import metadata
        path = self.source_path
        self._job('사진 정보',lambda c,p:metadata(path),lambda result:self._text('EXIF·GPS·ICC',json.dumps(result,ensure_ascii=False,indent=2)))

    def _ensure_catalog(self):
        if self._catalog is None:
            from croweyes_workflows import Catalog
            self._catalog = Catalog()
        self._catalog_rows = self._catalog.all()

    def search_dialog(self):
        self._ensure_catalog()
        win,frame=self._window('촬영일·OCR 글자 검색','480x350')
        text=tk.StringVar();date=tk.StringVar()
        for label,var in [('촬영일 앞부분 (예: 2026:10)',date),('사진 속 글자',text)]:
            ttk.Label(frame,text=label).pack(anchor='w')
            ttk.Entry(frame,textvariable=var,width=38).pack(fill='x',pady=4)
        def apply():
            self._collection_filter=dict(date=date.get(),text=text.get().casefold())
            self._apply_playlist_filter();win.destroy()
        ttk.Button(frame,text='검색 적용',command=apply).pack(pady=5)
        ttk.Button(frame,text='검색 해제',command=lambda:(self._collection_filter.clear(),self._apply_playlist_filter(),win.destroy())).pack()
        ttk.Button(frame,text='현재 폴더 촬영일 색인',command=lambda:self.index_collection(False)).pack(pady=4)
        ttk.Button(frame,text='사진 속 글자 검색 준비 (OCR 색인)',command=lambda:self.index_collection(True)).pack()

    def _visible_playlist_indices(self):
        indices=super()._visible_playlist_indices()
        f=self._collection_filter
        if not f:
            return indices
        def matches(i):
            item=self._catalog_rows.get(str(self.folder_files[i].resolve()),{})
            return item.get('taken','').startswith(f.get('date','')) and f.get('text','') in item.get('text','').casefold()
        return [i for i in indices if matches(i)]

    def duplicate_dialog(self, similar):
        from croweyes_workflows import duplicates
        paths=list(self.folder_files)
        if not paths:
            return
        self._job('유사 이미지' if similar else '동일 파일',lambda c,p:duplicates(paths,similar,c,p),lambda results:self._text('비교 결과 · 자동 삭제하지 않습니다', '\n\n'.join(a+'\n'+b+f'\n차이 {d}' for a,b,d in results) or '일치 항목 없음'))

    def provenance_dialog(self):
        if not self.source_path:
            return
        from croweyes_provenance import inspect
        path=self.source_path
        def done(result):
            self._provenance_values[str(path)]=result
            self._update_info()
            self._text('출처 정보 · C2PA',f'파일: {path.name}\n\nAI 기록: {result.get("ai", "판별 불가")}\n출처 기록: {result.get("credential", "없음")}\n검증: {result.get("validation", "확인 불가")}\n\n'+json.dumps(result,ensure_ascii=False,indent=2)+'\n\n출처 정보 없음은 AI가 아니라는 뜻이 아닙니다.')
        self._job('출처 정보 확인',lambda c,p:inspect(path),done)

    def extensions_dialog(self):
        from croweyes_dialogs import FittedDialog
        win=FittedDialog(self,'기본 포함 기능 안내',700);frame=win.body
        ttk.Label(frame,text='별도 설치 없이 사용 · 필요한 순간에만 기능을 불러옵니다.',style='Section.TLabel',wraplength=640).pack(anchor='w',pady=(0,10))
        tabs=ttk.Notebook(frame);tabs.pack(fill='both',expand=True)
        groups=[]
        for title in ('빠른 보기·출처','필터·글자 인식','편집·단축키'):
            page=ttk.Frame(tabs,style='Panel.TFrame',padding=10);tabs.add(page,text=title);groups.append(page)
        features=[
            ('빠른 이미지 보기','일반 사진은 AI 모델 없이 바로 봅니다. RAW는 파일을 열 때 미리보기를 준비합니다.\n열기 Ctrl+O · 맞춤 Ctrl+1 · 원본 크기 Ctrl+0'),
            ('C2PA 출처 / AI 생성 판단','상단 AI 생성 판단 → 현재 사진 출처 검사. 생성·편집 선언과 출처 검증을 확인합니다. 기록이 없으면 판별 불가입니다.'),
            ('성인 콘텐츠 필터','상단 성인 필터에서 켜고 적용합니다. PC 안에서 처리하며 판별 불가 파일도 숨깁니다. 기본값은 끄기입니다.'),
            ('글자 인식 / 촬영일 색인','상단 도구에서 OCR과 색인을 실행합니다. 인식 결과는 복사하고, 색인한 글자·촬영일은 PC의 검색 DB에서 찾습니다.'),
            ('사본으로 편집·저장','주석·형광펜·모자이크, 영역 복사, 크기·비율 변경을 제공합니다.\n취소 Ctrl+Z · 재실행 Ctrl+Y · 저장 Ctrl+S'),
            ('사진에 집중하는 화면','공통 4열 파일목록, 필요할 때 여는 정보·검사 열을 사용합니다.\n이전/다음 ←/→ · 재생 F5 · 정보 F8 · 전체 화면 F11')]
        for i,(title,description) in enumerate(features):
            card=ttk.Frame(groups[i//2],style='Panel.TFrame',padding=(0,4,10,8))
            card.grid(row=0,column=i%2,sticky='nsew')
            ttk.Label(card,text=title,style='Section.TLabel').pack(anchor='w',pady=(0,4))
            ttk.Label(card,text=description,wraplength=282,justify='left').pack(anchor='w')
        for page in groups:
            for i in (0,1):page.columnconfigure(i,weight=1,uniform='feature')
        ttk.Button(frame,text='환경설정 열기',command=lambda:(win.destroy(),self.show_preferences())).pack(pady=(8,0))

    def performance_dialog(self):
        from croweyes_dialogs import FittedDialog
        win=FittedDialog(self,'보기·성능 옵션',640);frame=win.body
        keep=tk.BooleanVar(value=self.settings.get('keep_zoom',False))
        color=tk.BooleanVar(value=self.settings.get('color_management',True))
        for label,var in [('다음 이미지에서 확대율 유지',keep),('ICC 프로파일을 sRGB로 변환',color)]:
            ttk.Checkbutton(frame,text=label,variable=var).pack(anchor='w')
        ttk.Label(frame,text='고해상도 이미지는 최대 4096px 축소 미리보기로 표시합니다.\n이미지 내보내기는 현재 표시 픽셀 기준입니다.\n일괄 처리에서 원본 파일을 읽어 지정 크기로 저장할 수 있습니다.',wraplength=590,justify='left').pack(anchor='w',pady=14)
        def save():
            changed=self.settings.get('color_management',True)!=color.get()
            self.settings.update(keep_zoom=keep.get(),color_management=color.get())
            win.destroy()
            if changed:
                with self._decoded_cache_lock:
                    self._decoded_cache.clear()
                    self._decoded_cache_order.clear()
                self._thumb_photos.clear()
                self._thumb_loaded.clear()
                if self.folder_files:
                    self.goto_index(self.index)
        ttk.Button(frame,text='적용',command=save).pack()

    def _on_close(self):
        for cancel in self._tool_cancels:
            cancel.set()
        super()._on_close()

    def _set_content_filter(self, mode):
        import sys
        from croweyes_extensions import available
        if mode == 'explicit' and getattr(sys,'frozen',False) and not available('safety'):
            self._text('성인 콘텐츠 필터','기본 포함 필터 파일이 누락되었습니다. 공식 배포 파일을 다시 설치하세요.')
            mode = 'off'
        return super()._set_content_filter(mode)
