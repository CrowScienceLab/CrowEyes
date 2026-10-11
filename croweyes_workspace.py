"""Viewer/editor workspaces. Switching layout never starts indexing or AI."""
import queue
import sys
import threading
import tkinter as tk
from tkinter import ttk
from PIL import ImageTk


def core(viewer):
    return sys.modules[viewer.__class__.__module__]


class WorkspaceToolbar(ttk.Frame):
    def __init__(self, master, viewer):
        super().__init__(master, style='Toolbar.TFrame', padding=(10,4))
        self.viewer=viewer
        self._columns=None
        self.menu_row=ttk.Frame(self,style='Toolbar.TFrame')
        self.menu_row.pack(fill=tk.X)
        viewer._menus=[]
        viewer._workspace_menus={}
        self.build_menus()
        heading=ttk.Frame(self,style='Toolbar.TFrame')
        heading.pack(fill=tk.X,pady=(4,6))
        viewer._brand_logo_label=ttk.Label(heading,image=viewer._icons['eye'],style='Logo.TLabel')
        viewer._brand_logo_label.pack(side=tk.LEFT,padx=(0,8))
        viewer._brand_label=ttk.Label(heading,text='CrowEyes',style='Brand.TLabel')
        viewer._brand_label.pack(side=tk.LEFT,padx=(0,24))
        self.mode_buttons={}
        for mode,label in [('viewer','뷰어'),('editor','편집')]:
            button=ttk.Button(heading,text=label,command=lambda m=mode:viewer.set_workspace(m),style='Icon.Tool.TButton')
            button.pack(side=tk.LEFT,padx=4,ipadx=12,ipady=5)
            self.mode_buttons[mode]=button
        ttk.Label(heading,text='2.0',style='Crumb.TLabel').pack(side=tk.RIGHT,padx=10)
        self.buttons=ttk.Frame(self,style='Toolbar.TFrame')
        self.buttons.pack(fill=tk.X)
        self.buttons.bind('<Configure>',lambda e:self.reflow(e.width))
        self.populate()

    def build_menus(self):
        v=self.viewer
        c=core(v)
        def menu(label):
            button=ttk.Menubutton(self.menu_row,text=label,style='Chrome.TMenubutton')
            button.pack(side=tk.LEFT,padx=(0,7))
            result=tk.Menu(button,tearoff=False)
            button.configure(menu=result)
            v._menus.append(result)
            v._workspace_menus[label]=result
            return result
        def add(m,label,command,key=''):
            m.add_command(label=label,command=v._action(command),accelerator=key)
        m=menu('파일')
        for label,cmd,key in [('파일 열기',v.open_file_dialog,'Ctrl+O'),('폴더 열기',v.open_folder_dialog,'Ctrl+Shift+O'),('다른 이름으로 저장',v.save_as,'Ctrl+S'),('품질·목표 용량 내보내기',v.quality_dialog,''),('인쇄',v.print_current_image,'Ctrl+P')]:add(m,label,cmd,key)
        m.add_separator();m.add_command(label='종료',command=v._on_close)
        m=menu('보기')
        for label,cmd,key in [('화면에 맞춤',v.fit_to_window,'Ctrl+1'),('100% 보기',v.actual_size,'Ctrl+0'),('확대',lambda:v.zoom_by(1.15),'+'),('축소',lambda:v.zoom_by(1/1.15),'-'),('전체 화면',v.toggle_image_fullscreen,'F11')]:add(m,label,cmd,key)
        m.add_command(label='슬라이드쇼 재생 / 정지',command=v.toggle_slideshow,accelerator='F5')
        add(m,'선택 이미지 2 / 4장 비교',v.compare_selected)
        m.add_separator()
        for name in c.LIST_MODES:
            m.add_radiobutton(label=c.LIST_MODE_LABELS[name],variable=v._list_mode_var,value=name,command=lambda n=name:v.set_list_mode(n))
        m.add_separator()
        m.add_checkbutton(label='파일 목록 패널',variable=v._playlist_panel_var,command=v.toggle_playlist_panel)
        m.add_checkbutton(label='사진 정보 패널',variable=v._info_panel_var,command=v.toggle_info_panel)
        m=menu('편집')
        add(m,'편집 작업 공간',lambda:v.set_workspace('editor'))
        for label,cmd,key in [('실행 취소',v.undo_edit,'Ctrl+Z'),('재실행',v.redo_edit,'Ctrl+Y'),('원본 복원',v.restore_original,''),('오른쪽 회전',lambda:v.rotate(90),'Ctrl+R'),('왼쪽 회전',lambda:v.rotate(-90),'Ctrl+L'),('좌우 반전',v.toggle_flip_h,''),('상하 반전',v.toggle_flip_v,''),('크기·비율 변경 후 저장',v.show_resize_dialog,''),('영역 선택 후 복사',v.start_region_copy,''),('영역 선택 후 저장',lambda:v.start_region_copy('save'),''),('주석·모자이크',v.annotation_dialog,''),('편집 전후 비교',v.compare_before_after,'')]:add(m,label,cmd,key)
        m=menu('정리')
        for label,cmd in [('별점·태그·즐겨찾기',v.catalog_dialog),('분류·날짜·내용 검색',v.search_dialog),('이름 변경',v.rename_selected_file),('일괄 이름 변경',v.rename_batch_dialog),('일괄 변환·크기·이름 변경',v.batch_dialog),('동일 파일 찾기',lambda:v.duplicate_dialog(False)),('유사 이미지 찾기',lambda:v.duplicate_dialog(True)),('선택 파일 복사',v.copy_selected_files),('휴지통으로 삭제',v.delete_selected_files),('파일 위치 열기',v.open_selected_file_location)]:add(m,label,cmd)
        m.add_separator()
        for name in c.SORT_KEYS:
            m.add_radiobutton(label=c.SORT_LABELS[name],variable=v._sort_var,value=name,command=lambda n=name:v.set_sort(n))
        m.add_radiobutton(label='오름차순',variable=v._sort_desc_var,value=False,command=lambda:v.set_sort_direction(False))
        m.add_radiobutton(label='내림차순',variable=v._sort_desc_var,value=True,command=lambda:v.set_sort_direction(True))
        m=menu('도구')
        for label,cmd in [('글자 인식 (OCR)',v.ocr_dialog),('영역 글자 인식',v.ocr_region),('촬영일 색인',lambda:v.index_collection(False)),('OCR 내용 색인',lambda:v.index_collection(True)),('AI 내용 검색 · 선택 모듈',v.semantic_dialog),('C2PA 출처 확인 · 선택 모듈',v.provenance_dialog),('EXIF·GPS·색상 정보',v.metadata_dialog)]:add(m,label,cmd)
        m=menu('설정')
        for label,cmd in [('선택 모듈 관리',v.extensions_dialog),('보기·성능',v.performance_dialog),('환경설정·콘텐츠 필터',v.show_preferences),('기본 앱 등록',v.show_file_association_dialog),('Windows 실행 차단 안내',v.show_windows_security_help),('업데이트 확인',lambda:v.check_for_updates(manual=True)),('CrowEyes 정보',v.show_about)]:add(m,label,cmd)

    def populate(self):
        v=self.viewer;c=core(v)
        for widget in self.buttons.winfo_children():widget.destroy()
        v._toolbar_buttons=[];v._responsive_buttons=[];v._responsive_dropdowns=[];v._responsive_hide_narrow=[];v._toolbar_pack_layout=[]
        v._toolbar_primary=v._toolbar_actions=self.buttons
        self._columns=None
        editor=v._workspace_mode=='editor'
        actions=[('previous','이전','이전 사진',v.prev_image),('next','다음','다음 사진',v.next_image)]
        if editor:
            actions += [('undo','취소','실행 취소 (Ctrl+Z)',v.undo_edit),('redo','재실행','재실행 (Ctrl+Y)',v.redo_edit),('compare','전후 비교','편집 전후 비교',v.compare_before_after),('save','사본 저장','품질·목표 용량 저장',v.quality_dialog)]
        else:
            actions=[('open_image','열기','이미지 열기 (Ctrl+O)',v.open_file_dialog),('folder','폴더','폴더 열기',v.open_folder_dialog)]+actions+[('fit','화면 맞춤','화면에 맞춤 (Ctrl+1)',v.fit_to_window),('actual','100% 보기','100% 보기 (Ctrl+0)',v.actual_size),('zoom_in','확대','확대 (+)',lambda:v.zoom_by(1.15)),('zoom_out','축소','축소 (-)',lambda:v.zoom_by(1/1.15)),('play','재생','슬라이드쇼 (F5)',v.toggle_slideshow),('compare','비교','선택 이미지 2 / 4장 비교',v.compare_selected),('info','정보','사진 정보 패널 (F8)',v.toggle_info_panel)]
        v._slide_btn=None
        for name,label,tip,command in actions:
            callback=command if name=='play' else v._action(command)
            button=c._tool_button(self.buttons,label,tip,callback,0,v._icons['toolbar_'+name])
            button.configure(compound=tk.LEFT)
            v._toolbar_buttons.append(button)
            if name=='play':v._slide_btn=button
        for mode,button in self.mode_buttons.items():
            button.configure(style='Accent.Icon.Tool.TButton' if mode==v._workspace_mode else 'Icon.Tool.TButton')
        self.after_idle(lambda:self.reflow(self.buttons.winfo_width()))
        if hasattr(v,'slideshow_job'):v._update_slide_button()

    def reflow(self,width):
        if not self.winfo_exists() or not self.viewer._toolbar_buttons:return
        buttons=self.viewer._toolbar_buttons
        tile=max(b.winfo_reqwidth() for b in buttons)+4
        cols=max(1,min(len(buttons),max(1,width)//tile))
        if cols==self._columns:return
        self._columns=cols
        for i in range(16):self.buttons.columnconfigure(i,minsize=tile if i<cols else 0)
        for i,b in enumerate(buttons):b.grid(row=i//cols,column=i%cols,padx=2,pady=3,sticky='ew')


class WorkspaceMixin:
    def __init__(self,*args,**kwargs):
        self._workspace_mode='viewer'
        self._editor_panel=None
        self._filmstrip=None
        self._film_generation=0
        self._film_job=None
        self._film_photos=[]
        super().__init__(*args,**kwargs)

    def _build_ui(self):
        super()._build_ui()
        # Shared adjustment variables remain, but viewing has no editing sliders.
        controls=self._brightness_scale.master
        for child in controls.winfo_children():child.pack_forget()
        self._safety_indicator.pack(side=tk.LEFT,padx=8)
        self._anim_btn.pack(side=tk.LEFT,padx=3)
        self.after_idle(self._create_editor)

    def _create_editor(self):
        if self._editor_panel is not None:self._editor_panel.destroy()
        self._editor_panel=ttk.Frame(self.paned,style='Panel.TFrame',padding=12,width=250)
        canvas=tk.Canvas(self._editor_panel,highlightthickness=0,bd=0,background=self._theme()['panel'],width=240,height=200)
        scroll=ttk.Scrollbar(self._editor_panel,orient=tk.VERTICAL,command=canvas.yview)
        scroll.pack(side=tk.RIGHT,fill=tk.Y);canvas.pack(side=tk.LEFT,fill=tk.BOTH,expand=True)
        canvas.configure(yscrollcommand=scroll.set)
        panel=ttk.Frame(canvas,style='Panel.TFrame')
        item=canvas.create_window(0,0,anchor='nw',window=panel)
        panel.bind('<Configure>',lambda e:canvas.configure(scrollregion=canvas.bbox('all')))
        canvas.bind('<Configure>',lambda e:canvas.itemconfigure(item,width=e.width))
        ttk.Label(panel,text='편집',style='Section.TLabel').pack(anchor='w',pady=(0,8))
        def action(label,command):
            ttk.Button(panel,text=label,command=self._action(command)).pack(fill=tk.X,pady=3)
        action('오른쪽 회전  ↻',lambda:self.rotate(90))
        row=ttk.Frame(panel,style='Panel.TFrame');row.pack(fill=tk.X,pady=3)
        ttk.Button(row,text='좌우 반전',command=self._action(self.toggle_flip_h)).pack(side=tk.LEFT,fill=tk.X,expand=True)
        ttk.Button(row,text='상하 반전',command=self._action(self.toggle_flip_v)).pack(side=tk.LEFT,fill=tk.X,expand=True,padx=(5,0))
        action('크기 · 비율 변경',self.show_resize_dialog)
        action('영역 저장',lambda:self.start_region_copy('save'))
        action('영역 클립보드 복사',self.start_region_copy)
        ttk.Separator(panel).pack(fill=tk.X,pady=10)
        for name,var in [('밝기',self.bright_var),('대비',self.contrast_var)]:
            header=ttk.Frame(panel,style='Panel.TFrame');header.pack(fill=tk.X)
            ttk.Label(header,text=name,style='Panel.TLabel').pack(side=tk.LEFT)
            value=ttk.Label(header,style='Panel.TLabel');value.pack(side=tk.RIGHT)
            def update_value(*_,label=value,variable=var):
                if label.winfo_exists():label.configure(text=f'{variable.get():.2f}')
            update_value()
            # Widget-scoped trace cleanup prevents theme changes accumulating callbacks.
            trace=var.trace_add('write',update_value)
            value.bind('<Destroy>',lambda e,variable=var,token=trace:variable.trace_remove('write',token))
            ttk.Scale(panel,from_=0.2,to=2.0,variable=var,command=self._on_adjust,style='CrowEyes.Horizontal.TScale').pack(fill=tk.X,pady=(5,12))
        ttk.Separator(panel).pack(fill=tk.X,pady=7)
        action('주석 · 형광펜 · 모자이크',self.annotation_dialog)
        action('원본 복원',self.restore_original)
        ttk.Label(panel,text='원본을 유지하고 사본으로 저장합니다.',style='Panel.TLabel',wraplength=220).pack(anchor='w',pady=(12,0))
        def wheel(event):
            canvas.yview_scroll(-1 if event.delta>0 else 1,'units')
            return 'break'
        def bind_wheel(widget):
            widget.bind('<MouseWheel>',wheel)
            for child in widget.winfo_children():bind_wheel(child)
        bind_wheel(panel)
        if self._filmstrip is None:
            self._filmstrip=ttk.Frame(self,style='Panel.TFrame',padding=(8,4))
        if self._workspace_mode=='editor':self._restore_panes()

    def set_workspace(self,mode):
        if mode not in {'viewer','editor'} or mode==self._workspace_mode:return
        self._interrupt_slideshow()
        if self._image_fullscreen:self.exit_image_fullscreen()
        self._workspace_mode=mode
        self._film_generation+=1
        self.__dict__.pop('_film_key',None)
        if self._editor_panel is None:self._create_editor()
        self.toolbar.populate()
        self._restore_panes()
        self._refresh_filmstrip()
        self.status.configure(text='편집 · 저장은 사본으로 내보냅니다' if mode=='editor' else '뷰어 · 방향키로 사진을 이동합니다')

    def _restore_panes(self):
        if self._workspace_mode=='editor' and self._editor_panel is not None:
            for pane in self.paned.panes():self.paned.forget(pane)
            self.paned.add(self._center_panel,weight=1)
            self.paned.add(self._editor_panel,weight=0)
            self.navigation_bar.grid_remove()
            self._filmstrip.grid(row=3,column=0,sticky='ew',padx=10)
            self.context_bar.grid(row=4,column=0,sticky='ew')
            self._sashes_applied=False
            self.after(40,self._init_sashes)
        else:
            super()._restore_panes()
            if self._filmstrip is not None:self._filmstrip.grid_remove()
            self.navigation_bar.grid(row=1,column=0,sticky='ew')
            self.context_bar.grid(row=3,column=0,sticky='ew')
            if not self._context_visible:self.context_bar.grid_remove()

    def _init_sashes(self,retry=0):
        if self._workspace_mode=='editor':
            if len(self.paned.panes())==2:
                width=self.paned.winfo_width()
                if width>300:self.paned.sashpos(0,max(180,width-min(270,max(210,int(width*.23)))))
                self._sashes_applied=True
            return
        return super()._init_sashes(retry)

    def _update_info(self):
        super()._update_info()
        self._refresh_filmstrip()

    def _refresh_filmstrip(self):
        if self._workspace_mode!='editor' or self._filmstrip is None or self._image_fullscreen:return
        # Redraw/zoom may update info frequently; only refresh when files change.
        width=max(320,self.winfo_width())
        count=max(1,min(11,(width-48)//120))
        start=max(0,min(self.index-count//2,len(self.folder_files)-count))
        paths=list(enumerate(self.folder_files))[start:start+count]
        key=(tuple(str(p) for _,p in paths),self.index,self._content_filter_mode,self.settings.get('ui_theme'),self.settings.get('color_management',True))
        if self.__dict__.get('_film_key')==key:return
        self._film_key=key
        self._film_generation+=1;generation=self._film_generation
        for child in self._filmstrip.winfo_children():child.destroy()
        self._film_photos=[]
        if not paths:return
        messages=queue.Queue();mode=self._content_filter_mode
        def worker():
            for index,path in paths:
                if generation!=self._film_generation:return
                if mode=='explicit' and self._safety_manager.check(path,vector_loader=self._safety_vector_loader).status!='SAFE':
                    messages.put((index,None));continue
                messages.put((index,self._make_thumb_pil(path,72)))
            messages.put(None)
        threading.Thread(target=worker,name='CrowEyesFilmstrip',daemon=True).start()
        cells={}
        for index,path in paths:
            button=ttk.Button(self._filmstrip,text=path.name,compound=tk.TOP,width=12,style='Accent.Icon.Tool.TButton' if index==self.index else 'Icon.Tool.TButton',command=lambda i=index:self.goto_index(i))
            button.pack(side=tk.LEFT,padx=3,pady=2,fill=tk.X,expand=True)
            core(self).ToolTip(button,path.name)
            cells[index]=button
        def poll():
            self._film_job=None
            if generation!=self._film_generation or self._workspace_mode!='editor':return
            try:
                while True:
                    item=messages.get_nowait()
                    if item is None:return
                    index,im=item
                    if im is not None:
                        photo=ImageTk.PhotoImage(im,master=self)
                        self._film_photos.append(photo);cells[index].configure(image=photo)
                    else:cells[index].configure(text='표시 제한')
            except queue.Empty:self._film_job=self.after(30,poll)
        self._film_job=self.after(30,poll)

    def enter_image_fullscreen(self):
        super().enter_image_fullscreen()
        if self._editor_panel is not None and str(self._editor_panel) in self.paned.panes():self.paned.forget(self._editor_panel)
        if self._filmstrip is not None:self._filmstrip.grid_remove()

    def exit_image_fullscreen(self):
        super().exit_image_fullscreen()
        self._restore_panes()

    def _rebuild_icon_chrome(self):
        super()._rebuild_icon_chrome()
        controls=self._brightness_scale.master
        for child in controls.winfo_children():child.pack_forget()
        self._safety_indicator.pack(side=tk.LEFT,padx=8);self._anim_btn.pack(side=tk.LEFT,padx=3)
        self._create_editor()
        self.__dict__.pop('_film_key',None)
        self._restore_panes();self._refresh_filmstrip()

    def _on_root_configure(self,event):
        super()._on_root_configure(event)
        if event.widget is self:self._refresh_filmstrip()

    def install_tools_menu(self,menu):
        # Context menu has the same task categories, without a version bucket.
        for name in ('편집','정리','도구'):
            original=self._workspace_menus.get(name)
            if original is not None:menu.add_cascade(label=name,menu=original)

    def _on_close(self):
        self._film_generation+=1
        if self._film_job is not None:
            self.after_cancel(self._film_job);self._film_job=None
        # Base close saves viewer pane geometry; editor panes have a different shape.
        if self._workspace_mode=='editor':
            self._workspace_mode='viewer'
            self._restore_panes()
        super()._on_close()
