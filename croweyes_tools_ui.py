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

    def install_tools_menu(self, menu):
        tools = tk.Menu(menu, tearoff=False)
        for label, command in (
            ('실행 취소 (Ctrl+Z)', self.undo_edit), ('재실행 (Ctrl+Y)', self.redo_edit),
            ('원본 복원', self.restore_original), ('편집 전후 비교', self.compare_before_after),
            ('일괄 변환·크기·이름 변경', self.batch_dialog), ('선택 파일 일괄 이름 변경', self.rename_batch_dialog),
            ('주석·모자이크', self.annotation_dialog), ('선택 이미지 2/4장 비교', self.compare_selected),
            ('품질·목표 용량 저장', self.quality_dialog), ('EXIF·GPS·색상 정보', self.metadata_dialog),
            ('별점·태그·즐겨찾기', self.catalog_dialog), ('분류·날짜·내용 검색', self.search_dialog),
            ('정확히 같은 파일 찾기', lambda: self.duplicate_dialog(False)),
            ('AI 내용 검색 (선택 모듈)', self.semantic_dialog),
            ('유사 이미지 찾기', lambda: self.duplicate_dialog(True)),
            ('글자 인식 (OCR)', self.ocr_dialog), ('출처 정보 확인 (C2PA)', self.provenance_dialog),
            ('선택 모듈 관리', self.extensions_dialog), ('보기·성능 옵션', self.performance_dialog),
        ):
            tools.add_command(label=label, command=command)
        menu.add_cascade(label='2.0 작업 도구', menu=tools)

    def _window(self, title, size=None):
        win = tk.Toplevel(self)
        win.title(title)
        win.transient(self)
        if size:
            win.geometry(size)
        frame = ttk.Frame(win, padding=14)
        frame.pack(fill='both', expand=True)
        return win, frame

    def _text(self, title, text):
        win, frame = self._window(title, '780x520')
        view = tk.Text(frame, wrap='word')
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
        win, frame = self._window(title)
        progress = ttk.Progressbar(frame, length=420, maximum=100)
        progress.pack()
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
                            messagebox.showerror(title, msg[1], parent=self)
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

    def annotation_dialog(self):
        if self.display_image is not None:
            self._interrupt_slideshow()
            from croweyes_annotation import editor
            editor(self,self.display_image)

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
            self._text('색인 결과','취소된 작업은 완료된 항목까지 보존됩니다.\n'+('\n'.join(errors) if errors else '처리한 항목에 오류 없음'))
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

    def catalog_dialog(self):
        paths=self._paths()
        if not paths:
            return
        self._ensure_catalog()
        item=self._catalog_rows.get(str(paths[0].resolve()),{})
        win,frame=self._window('선택 사진 분류')
        rating=tk.IntVar(value=item.get('rating',0))
        favorite=tk.BooleanVar(value=bool(item.get('favorite',0)))
        tags=tk.StringVar(value=item.get('tags',''))
        ttk.Label(frame,text=f'{len(paths)}장에 적용 · 원본 파일은 변경하지 않습니다.').pack()
        ttk.Combobox(frame,textvariable=rating,values=list(range(6)),state='readonly').pack()
        ttk.Checkbutton(frame,text='즐겨찾기',variable=favorite).pack()
        ttk.Label(frame,text='태그 (쉼표로 구분)').pack()
        ttk.Entry(frame,textvariable=tags,width=45).pack()
        def save():
            for path in paths:
                self._catalog.set(path,rating=rating.get(),favorite=int(favorite.get()),tags=tags.get())
            self._catalog_rows=self._catalog.all()
            win.destroy()
            self._apply_playlist_filter()
        ttk.Button(frame,text='적용',command=save).pack(pady=8)

    def search_dialog(self):
        self._ensure_catalog()
        win,frame=self._window('분류·날짜·OCR 내용 검색')
        favorite=tk.BooleanVar(value=False)
        rating=tk.IntVar(value=0)
        tag=tk.StringVar()
        text=tk.StringVar()
        date=tk.StringVar()
        ttk.Checkbutton(frame,text='즐겨찾기만',variable=favorite).pack()
        for label,var in [('최소 별점 (0~5)',rating),('태그',tag),('촬영일 앞부분 (예: 2026:10)',date),('OCR로 색인한 글자',text)]:
            ttk.Label(frame,text=label).pack()
            ttk.Entry(frame,textvariable=var,width=45).pack()
        ttk.Label(frame,text='날짜·내용은 아래 색인을 실행한 파일에서 검색합니다.').pack(pady=8)
        def apply():
            self._collection_filter=dict(favorite=favorite.get(),rating=rating.get(),tag=tag.get().casefold(),date=date.get(),text=text.get().casefold())
            self._apply_playlist_filter()
            win.destroy()
        ttk.Button(frame,text='검색 적용',command=apply).pack()
        ttk.Button(frame,text='필터 해제',command=lambda:(self._collection_filter.clear(),self._apply_playlist_filter(),win.destroy())).pack()
        ttk.Button(frame,text='현재 폴더 EXIF 색인',command=lambda:self.index_collection(False)).pack()
        ttk.Button(frame,text='현재 폴더 OCR 내용 색인',command=lambda:self.index_collection(True)).pack()

    def _visible_playlist_indices(self):
        indices=super()._visible_playlist_indices()
        f=self._collection_filter
        if not f:
            return indices
        def matches(i):
            item=self._catalog_rows.get(str(self.folder_files[i].resolve()),{})
            return (not f.get('favorite') or item.get('favorite')) and item.get('rating',0)>=f.get('rating',0) and f.get('tag','') in item.get('tags','').casefold() and item.get('taken','').startswith(f.get('date','')) and f.get('text','') in item.get('text','').casefold()
        return [i for i in indices if matches(i)]

    def duplicate_dialog(self, similar):
        from croweyes_workflows import duplicates
        paths=list(self.folder_files)
        if not paths:
            return
        self._job('유사 이미지' if similar else '동일 파일',lambda c,p:duplicates(paths,similar,c,p),lambda results:self._text('비교 결과 · 자동 삭제하지 않습니다', '\n\n'.join(a+'\n'+b+f'\n차이 {d}' for a,b,d in results) or '일치 항목 없음'))

    def semantic_dialog(self):
        paths=list(self.folder_files)
        if not paths:
            return
        query=simpledialog.askstring('AI 내용 검색','영어로 이미지 내용을 입력하세요 (예: a photo of a flower).\n한국어 글자 검색은 OCR 내용 검색을 사용하세요.\n처음 실행할 때만 선택 모듈을 로드하고 폴더를 색인합니다.',parent=self)
        if not query:
            return
        def work(c,p):
            self._guard_paths(paths,c)
            from croweyes_semantic import Search
            from croweyes_workflows import catalog_path
            engine=Search(catalog_path().with_name('semantic.sqlite3'))
            return engine.query(query,paths,c,p)
        def done(result):
            matches,errors=result
            win,frame=self._window('내용 검색 결과 · 유사도 순위 (정확도 확률 아님)','850x520')
            table=ttk.Treeview(frame,columns=('score','file'),show='headings')
            table.heading('score',text='유사도')
            table.heading('file',text='파일')
            table.column('score',width=100)
            table.column('file',width=660)
            table.pack(fill='both',expand=True)
            for i,(score,path) in enumerate(matches):
                table.insert('', 'end', iid=str(i),values=(f'{score:.3f}',path))
            def open_result(e=None):
                if table.selection():
                    path=Path(matches[int(table.selection()[0])][1])
                    if path in self.folder_files:self.goto_index(self.folder_files.index(path))
            table.bind('<Double-1>',open_result)
            ttk.Button(frame,text='선택 이미지 열기',command=open_result).pack()
            if errors:
                ttk.Button(frame,text=f'처리 실패 {len(errors)}개 확인',command=lambda:self._text('실패한 파일','\n'.join(errors))).pack()
        self._job('로컬 AI 내용 검색',work,done)

    def provenance_dialog(self):
        if not self.source_path:
            return
        from croweyes_provenance import inspect
        path=self.source_path
        def done(result):
            self._provenance_values[str(path)]=result
            self._update_info()
            self._text('출처 정보 · C2PA',json.dumps(result,ensure_ascii=False,indent=2)+'\n\n출처 정보 없음은 AI가 아니라는 뜻이 아닙니다.')
        self._job('출처 정보 확인',lambda c,p:inspect(path),done)

    def extensions_dialog(self):
        from croweyes_extensions import available, install, manifest
        win,frame=self._window('선택 모듈 관리')
        ttk.Label(frame,text='이 빌드의 공식 모듈 ZIP만 SHA-256 검증 후 설치합니다.\n기본 보기에는 모델과 C2PA 라이브러리를 불러오지 않습니다.').pack()
        for kind,label in [('provenance','C2PA 출처 확인'),('safety','성인 콘텐츠 필터'),('formats','RAW 미리보기'),('semantic','AI 내용 검색')]:
            row=ttk.Frame(frame)
            row.pack(fill='x',pady=6)
            status=ttk.Label(row,text=label+(' · 설치됨' if available(kind) else ' · 미설치'))
            status.pack(side='left')
            def choose(k=kind,s=status):
                archive=filedialog.askopenfilename(parent=win,title=manifest().get(k,{}).get('filename',k),filetypes=[('선택 모듈','*.zip')])
                if archive:
                    self._job('선택 모듈 설치',lambda c,p:install(archive,k),lambda r:s.configure(text='설치 완료 · 필요하면 앱을 다시 시작하세요'))
            ttk.Button(row,text='ZIP 설치',command=choose).pack(side='right')
        ttk.Button(frame,text='공식 다운로드 페이지',command=lambda:__import__('webbrowser').open('https://github.com/CrowScienceLab/CrowEyes/releases/latest')).pack(pady=8)

    def performance_dialog(self):
        win,frame=self._window('보기·성능 옵션')
        keep=tk.BooleanVar(value=self.settings.get('keep_zoom',False))
        color=tk.BooleanVar(value=self.settings.get('color_management',True))
        for label,var in [('다음 이미지에서 확대율 유지',keep),('ICC 프로파일을 sRGB로 변환',color)]:
            ttk.Checkbutton(frame,text=label,variable=var).pack(anchor='w')
        ttk.Label(frame,text='고해상도 이미지는 최대 4096px 축소 미리보기로 표시합니다.\n이미지 내보내기는 현재 표시 픽셀 기준입니다.\n일괄 처리에서 원본 파일을 읽어 지정 크기로 저장할 수 있습니다.').pack(pady=10)
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
            messagebox.showinfo('성인 콘텐츠 필터','선택 모듈 관리에서 필터 모듈을 먼저 설치하세요.',parent=self)
            mode = 'off'
        return super()._set_content_filter(mode)
