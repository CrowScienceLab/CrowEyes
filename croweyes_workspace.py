"""Viewer/editor workspaces. Switching layout never starts indexing or AI."""
import sys
import tkinter as tk
from tkinter import ttk
from croweyes_inline import InlineEditorMixin


def core(viewer):
    return sys.modules[viewer.__class__.__module__]


class WorkspaceToolbar(ttk.Frame):
    def __init__(self, master, viewer):
        super().__init__(master, style='Toolbar.TFrame', padding=(10,4))
        self.viewer=viewer
        self._columns=None
        self.menu_row=tk.Menu(viewer,tearoff=False)
        viewer.configure(menu=self.menu_row)
        viewer._menus=[]
        viewer._workspace_menus={}
        self.build_menus()
        heading=ttk.Frame(self,style='Toolbar.TFrame')
        heading.pack(side=tk.LEFT,padx=(0,12))
        viewer._brand_logo_label=ttk.Label(heading,image=viewer._icons['eye'],style='Logo.TLabel')
        viewer._brand_logo_label.pack(side=tk.LEFT,padx=(0,8))
        viewer._brand_label=ttk.Label(heading,text='CrowEyes',style='Brand.TLabel')
        viewer._brand_label.pack(side=tk.LEFT,padx=(0,24))
        self.mode_buttons={}
        for mode,label in [('viewer','뷰어'),('editor','편집')]:
            button=ttk.Button(heading,text=label,command=lambda m=mode:viewer.set_workspace(m),style='Icon.Tool.TButton')
            button.pack(side=tk.LEFT,padx=4,ipadx=12,ipady=5)
            self.mode_buttons[mode]=button
        self.buttons=ttk.Frame(self,style='Toolbar.TFrame')
        self.buttons.pack(side=tk.LEFT,fill=tk.X,expand=True)
        self.buttons.bind('<Configure>',lambda e:self.reflow(e.width))
        self.populate()

    def build_menus(self):
        v=self.viewer
        c=core(v)
        def menu(label):
            result=tk.Menu(self.menu_row,tearoff=False)
            self.menu_row.add_cascade(label=label,menu=result)
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
        for label,cmd,key in [('실행 취소',v.undo_edit,'Ctrl+Z'),('재실행',v.redo_edit,'Ctrl+Y'),('원본 복원',v.restore_original,''),('오른쪽 회전',lambda:v.rotate(90),'Ctrl+R'),('왼쪽 회전',lambda:v.rotate(-90),'Ctrl+L'),('좌우 반전',v.toggle_flip_h,''),('상하 반전',v.toggle_flip_v,''),('크기·비율 변경 후 저장',lambda:v.select_edit_tool('크기·비율'),''),('영역 선택 후 복사',v.start_region_copy,''),('영역 선택 후 저장',lambda:v.start_region_copy('save'),''),('주석',v.annotation_dialog,''),('형광펜',lambda:v.select_edit_tool('형광펜'),''),('모자이크',lambda:v.select_edit_tool('모자이크'),''),('편집 전후 비교',v.compare_before_after,'')]:add(m,label,cmd,key)
        m=menu('정리')
        for label,cmd in [('촬영일·OCR 글자 검색',v.search_dialog),('이름 변경',v.rename_selected_file),('일괄 이름 변경',v.rename_batch_dialog),('일괄 변환·크기·이름 변경',v.batch_dialog),('동일 파일 찾기',lambda:v.duplicate_dialog(False)),('유사 이미지 찾기',lambda:v.duplicate_dialog(True)),('선택 파일 복사',v.copy_selected_files),('휴지통으로 삭제',v.delete_selected_files),('파일 위치 열기',v.open_selected_file_location)]:add(m,label,cmd)
        m.add_separator()
        for name in c.SORT_KEYS:
            m.add_radiobutton(label=c.SORT_LABELS[name],variable=v._sort_var,value=name,command=lambda n=name:v.set_sort(n))
        m.add_radiobutton(label='오름차순',variable=v._sort_desc_var,value=False,command=lambda:v.set_sort_direction(False))
        m.add_radiobutton(label='내림차순',variable=v._sort_desc_var,value=True,command=lambda:v.set_sort_direction(True))
        m=menu('도구')
        for label,cmd in [('글자 인식 (OCR)',v.ocr_dialog),('영역 글자 인식',v.ocr_region),('촬영일 색인',lambda:v.index_collection(False)),('OCR 내용 색인',lambda:v.index_collection(True)),('C2PA 출처 확인',v.provenance_dialog),('EXIF·GPS·색상 정보',v.metadata_dialog)]:add(m,label,cmd)
        m=menu('설정')
        for label,cmd in [('기본 포함 기능 안내',v.extensions_dialog),('보기·성능',v.performance_dialog),('환경설정·콘텐츠 필터',v.show_preferences),('기본 앱 등록',v.show_file_association_dialog),('Windows 실행 차단 안내',v.show_windows_security_help),('업데이트 확인',lambda:v.check_for_updates(manual=True)),('CrowEyes 정보',v.show_about)]:add(m,label,cmd)

    def populate(self):
        v=self.viewer;c=core(v)
        for widget in self.buttons.winfo_children():widget.destroy()
        v._toolbar_buttons=[];v._responsive_buttons=[];v._responsive_dropdowns=[];v._responsive_hide_narrow=[];v._toolbar_pack_layout=[]
        v._toolbar_primary=v._toolbar_actions=self.buttons
        self._columns=None
        actions=[('open_image','열기','이미지 열기 (Ctrl+O)',v.open_file_dialog),('folder','폴더','폴더 열기',v.open_folder_dialog),('previous','이전','이전 사진',v.prev_image),('next','다음','다음 사진',v.next_image),('fit','화면맞춤','화면에 맞춤 (Ctrl+1)',v.fit_to_window),('zoom_out','축소','축소 (-)',lambda:v.zoom_by(1/1.15)),('actual','100%','100% 보기 (Ctrl+0)',v.actual_size),('zoom_in','확대','확대 (+)',lambda:v.zoom_by(1.15)),('play','재생','슬라이드쇼 (F5)',v.toggle_slideshow),('compare','비교','선택 이미지 2 / 4장 비교',v.compare_selected),('info','정보','사진 정보 패널 (F8)',v.toggle_info_panel)]
        if v._workspace_mode=='editor':
            actions=[('undo','취소','실행 취소 (Ctrl+Z)',v.undo_edit),('redo','재실행','재실행 (Ctrl+Y)',v.redo_edit),('restore','원본','원본 복원',v.restore_original),('rotate_right','회전','오른쪽 회전',lambda:v.rotate(90)),('flip_h','좌우','좌우 반전',v.toggle_flip_h),('flip_v','상하','상하 반전',v.toggle_flip_v),('resize','크기','크기·비율 변경',lambda:v.select_edit_tool('크기·비율')),('copy','영역','영역 클립보드 복사',v.start_region_copy),('adjust','조정','밝기·대비',lambda:v.select_edit_tool('밝기·대비')),('annotation','주석','주석: 글자·화살표·사각형',v.annotation_dialog),('highlight','형광펜','형광펜',lambda:v.select_edit_tool('형광펜')),('mosaic','모자이크','모자이크',lambda:v.select_edit_tool('모자이크')),('compare','전후','편집 전후 비교',v.compare_before_after),('save','저장','사본 저장',v.quality_dialog)]
        v._slide_btn=None
        for name,label,tip,command in actions:
            callback=command if name=='play' else v._action(command)
            button=c._tool_button(self.buttons,"",tip,callback,0,v._icons['toolbar_'+name])
            button.configure(compound=tk.NONE, text="")
            v._toolbar_buttons.append(button)
            button._croweyes_action=name
            if name=='play':v._slide_btn=button
        for mode,button in self.mode_buttons.items():
            button._croweyes_style='Accent.Icon.Tool.TButton' if mode==v._workspace_mode else 'Icon.Tool.TButton'
            button.configure(style=button._croweyes_style)
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


class WorkspaceMixin(InlineEditorMixin):
    def __init__(self,*args,**kwargs):
        self._workspace_mode='viewer'
        self._editor_panel=None
        self._filmstrip=None
        super().__init__(*args,**kwargs)

    def _build_ui(self):
        super()._build_ui()
        # Shared adjustment variables remain, but viewing has no editing sliders.
        controls=self._brightness_scale.master
        for child in controls.winfo_children():child.pack_forget()
        self._safety_indicator.pack(side=tk.LEFT,padx=8)
        self._anim_btn.pack(side=tk.LEFT,padx=3)
        self._info_tab=ttk.Button(self,text='정\n보',width=2,command=self.toggle_info_panel,style='Icon.Tool.TButton')
        core(self).ToolTip(self._info_tab,'사진 정보 열기 / 닫기 (F8)')
        self._info_tab.place(relx=1,rely=.48,anchor='e')

    def set_workspace(self,mode):
        if mode not in {'viewer','editor'} or mode==self._workspace_mode:return
        self._interrupt_slideshow()
        if self._image_fullscreen:self.exit_image_fullscreen()
        self._workspace_mode=mode
        self.end_edit_tool()
        self.toolbar.populate()
        self._apply_theme()
        self._restore_panes()
        self.status.configure(text='편집 · 저장은 사본으로 내보냅니다' if mode=='editor' else '뷰어 · 방향키로 사진을 이동합니다')

    def _restore_panes(self):
        super()._restore_panes()
        self.navigation_bar.grid(row=1,column=0,sticky='ew')
        self.context_bar.grid(row=3,column=0,sticky='ew')
        if not self._context_visible:self.context_bar.grid_remove()

    def enter_image_fullscreen(self):
        self.end_edit_tool()
        self.configure(menu='')
        super().enter_image_fullscreen()
        self._info_tab.place_forget()

    def exit_image_fullscreen(self):
        super().exit_image_fullscreen()
        self.configure(menu=self.toolbar.menu_row)
        self._info_tab.place(relx=1,rely=.48,anchor='e')
        self._restore_panes()

    def _rebuild_icon_chrome(self):
        super()._rebuild_icon_chrome()
        controls=self._brightness_scale.master
        for child in controls.winfo_children():child.pack_forget()
        self._safety_indicator.pack(side=tk.LEFT,padx=8);self._anim_btn.pack(side=tk.LEFT,padx=3)
        self._restore_panes()

    def _update_slide_button(self):
        super()._update_slide_button()
        if self._slide_btn is not None:self._slide_btn.configure(text='')

    def install_tools_menu(self,menu):
        # Context menu has the same task categories, without a version bucket.
        for name in ('편집','정리','도구'):
            original=self._workspace_menus.get(name)
            if original is not None:menu.add_cascade(label=name,menu=original)

    def show_preferences(self):
        c=core(self)
        win,frame=self._window('환경설정','540x470')
        theme=tk.StringVar(value=c.THEME_LABELS.get(self.settings.get('ui_theme','croweyes_dark')))
        wheel=tk.StringVar(value=c.WHEEL_ACTION_LABELS.get(self.settings.get('mouse_wheel_action','navigate')))
        safety=tk.StringVar(value=self._content_filter_mode)
        fit=tk.BooleanVar(value=self.settings.get('fit_on_open',True))
        updates=tk.BooleanVar(value=self.settings.get('auto_check_updates',True))
        slide=tk.IntVar(value=self.settings.get('slideshow_ms',3000))
        ttk.Label(frame,text='테마').pack(anchor='w')
        ttk.Combobox(frame,textvariable=theme,values=list(c.THEME_LABELS.values()),state='readonly').pack(fill='x',pady=4)
        ttk.Label(frame,text='마우스 휠 동작').pack(anchor='w')
        ttk.Combobox(frame,textvariable=wheel,values=list(c.WHEEL_ACTION_LABELS.values()),state='readonly').pack(fill='x',pady=4)
        ttk.Checkbutton(frame,text='열 때 화면에 맞춤',variable=fit).pack(anchor='w')
        ttk.Checkbutton(frame,text='시작할 때 업데이트 확인',variable=updates).pack(anchor='w')
        ttk.Label(frame,text='슬라이드쇼 간격 (ms)').pack(anchor='w',pady=(8,0))
        ttk.Spinbox(frame,from_=200,to=60000,textvariable=slide).pack(fill='x')
        ttk.Separator(frame).pack(fill='x',pady=10)
        ttk.Label(frame,text='성인 콘텐츠 필터 · PC 안에서 처리').pack(anchor='w')
        ttk.Radiobutton(frame,text='끄기 (기본값)',variable=safety,value='off').pack(anchor='w')
        ttk.Radiobutton(frame,text='켜기 · 판별이 불가능한 파일도 숨김',variable=safety,value='explicit').pack(anchor='w')
        def apply():
            values=(next(k for k,v in c.THEME_LABELS.items() if v==theme.get()),next(k for k,v in c.WHEEL_ACTION_LABELS.items() if v==wheel.get()),fit.get(),updates.get(),slide.get(),safety.get())
            if not 200<=values[4]<=60000:return
            win.destroy()
            self.settings.update(mouse_wheel_action=values[1],fit_on_open=values[2],auto_check_updates=values[3],slideshow_ms=values[4])
            self.set_ui_theme(values[0]);self._set_content_filter(values[5]);c.save_settings(self.settings)
        ttk.Button(frame,text='적용',command=apply).pack(pady=10)
