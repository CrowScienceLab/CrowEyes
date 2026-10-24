"""File-list menus and reversible Windows hidden attributes."""
import sys
import tkinter as tk
from tkinter import ttk, messagebox
from pathlib import Path
from croweyes_files import is_hidden, set_hidden


class FileBrowserMixin:
    def __init__(self, *args, **kwargs):
        self._opened_folders = []
        self._browser_restore = None
        super().__init__(*args, **kwargs)

    def build_browser_menus(self, header):
        c = sys.modules[self.__class__.__module__]
        if not hasattr(self,'_show_hidden_var'):
            self._show_hidden_var = tk.BooleanVar(self, bool(self.settings.get('show_hidden_files', False)))
        self._browser_menu_buttons = []
        for title, icon, attr in [('정렬', 'sort', '_browser_sort_menu'), ('보기', 'view', '_browser_view_menu')]:
            button = ttk.Menubutton(header, text=title, image=self._icons[icon], compound='left',width=0,
                                    style='Browser.TMenubutton', padding=(3, 3))
            button.pack(side='left', padx=(5, 0))
            menu = tk.Menu(button, tearoff=False)
            button.configure(menu=menu)
            setattr(self, attr, menu)
            self._browser_menu_buttons.append((button, icon))
        self._fill_sort_menu(self._browser_sort_menu)
        self._fill_view_menu(self._browser_view_menu)

    def _fill_sort_menu(self, menu):
        for key, label in [('name','이름'),('date','수정한 날짜'),('ext','유형'),('size','크기')]:
            menu.add_radiobutton(label=label, variable=self._sort_var, value=key,
                                 command=lambda k=key:self.set_sort(k))
        menu.add_separator()
        for descending, label in [(False,'오름차순'),(True,'내림차순')]:
            menu.add_radiobutton(label=label, variable=self._sort_desc_var, value=descending,
                                 command=lambda d=descending:self.set_sort_direction(d))

    def _fill_view_menu(self, menu):
        c = sys.modules[self.__class__.__module__]
        if not hasattr(self,'_show_hidden_var'):
            self._show_hidden_var = tk.BooleanVar(self, bool(self.settings.get('show_hidden_files', False)))
        for key in c.LIST_MODES:
            menu.add_radiobutton(label=c.LIST_MODE_LABELS[key], variable=self._list_mode_var, value=key,
                                 command=lambda k=key:self.set_list_mode(k))
        menu.add_separator()
        menu.add_checkbutton(label='숨김 파일 표시', variable=self._show_hidden_var, command=self.toggle_show_hidden)

    def _style_browser_menus(self):
        t=self._theme()
        style=ttk.Style(self)
        style.configure('Browser.TMenubutton', background=t['panel'],foreground=t['fg'],
                        borderwidth=0, relief='flat', font=('Segoe UI',9),padding=(3,3))
        style.map('Browser.TMenubutton',background=[('active',t['select'])],foreground=[('active',t['select_fg'])])
        for button,icon in getattr(self,'_browser_menu_buttons',[]):
            button.configure(image=self._icons[icon])
            button.tk.call(button._w,'configure','-style','Browser.TMenubutton')
        for attr in ('_browser_sort_menu','_browser_view_menu'):
            menu=getattr(self,attr,None)
            if menu:menu.configure(bg=t['panel'],fg=t['fg'],activebackground=t['select'],
                                   activeforeground=t['select_fg'],selectcolor=t['accent'],bd=0,font=('Segoe UI',10))

    def toggle_show_hidden(self):
        c=sys.modules[self.__class__.__module__]
        self.settings['show_hidden_files']=self._show_hidden_var.get()
        c.save_settings(self.settings)
        self._refresh_browser_visibility()

    def _refresh_browser_visibility(self):
        current=self.folder_files[self.index] if 0<=self.index<len(self.folder_files) else None
        self._browser_restore=(current,list(self._selected_playlist_paths()))
        self._interrupt_slideshow()
        self._stop_animation_timer()
        self._image_load_gen+=1
        self._vector_render_gen+=1
        self._pending_playlist_build=None
        # Invalidate pending decodes before a now-hidden image can reappear.
        if current and not self._show_hidden_var.get() and is_hidden(current):
            self.pil_image=self.display_image=None
            self.source_path=None
            self.anim_frames=[]
            self.redraw()
        folders=self._opened_folders or ([self.current_folder] if self.current_folder else [])
        if folders:
            self._history_navigation=True
            self.open_folders(folders)

    def change_hidden(self, paths, hidden):
        failures=[];count=0
        for path in dict.fromkeys(map(Path,paths)):
            try:
                set_hidden(path,hidden);count+=1
            except OSError as exc:failures.append(f'{path.name}: {exc}')
        if count:self._refresh_browser_visibility()
        if failures:messagebox.showwarning('일부 파일 속성 변경 실패','\n'.join(failures[:10]),parent=self)
        self.status.configure(text=f'{count}개 파일 '+('숨김 처리' if hidden else '숨김 해제')+' · 보기에서 숨김 파일 표시를 전환할 수 있습니다')

    def add_visibility_commands(self, menu, paths):
        paths=tuple(paths)
        menu.add_separator()
        menu.add_command(label='숨김',image=self._icons['hidden'],compound='left',
                         state='normal' if paths else 'disabled',command=lambda:self.change_hidden(paths,True))
        menu.add_command(label='숨김 해제',image=self._icons['visible'],compound='left',
                         state='normal' if any(is_hidden(p) for p in paths) else 'disabled',
                         command=lambda:self.change_hidden(paths,False))
        menu.add_checkbutton(label='숨김 파일 표시',variable=self._show_hidden_var,command=self.toggle_show_hidden)

    def _poll_folder_scan(self, generation):
        ready=generation in self._scan_results and generation==self._playlist_gen
        super()._poll_folder_scan(generation)
        if not ready:return
        restore=self._browser_restore;self._browser_restore=None
        if restore and self.folder_files:
            current,selected=restore
            target=self.folder_files.index(current) if current in self.folder_files else 0
            if self.index!=target:self.goto_index(target)
            self._playlist_selection={i for i,p in enumerate(self.folder_files) if p in selected}
            if not self._playlist_selection:self._playlist_selection={target}
            self._restore_playlist_selection_visuals()
        elif not self.folder_files:
            self.source_path=None;self._playlist_selection.clear()
            self._update_info()
