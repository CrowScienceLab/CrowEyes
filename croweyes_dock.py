"""Demand-driven pages in the third column; no model loads on tab selection."""
import tkinter as tk
from tkinter import ttk


class ModeSwitch(tk.Canvas):
    def __init__(self, master, viewer):
        super().__init__(master,width=154,height=42,highlightthickness=0,cursor='hand2',takefocus=True)
        self.viewer=viewer
        self.bind('<Button-1>',lambda e:viewer.set_workspace('viewer' if e.x<77 else 'editor'))
        self.bind('<B1-Motion>',lambda e:viewer.set_workspace('viewer' if e.x<77 else 'editor'))
        self.bind('<Left>',lambda e:viewer.set_workspace('viewer'))
        self.bind('<Right>',lambda e:viewer.set_workspace('editor'))
        self.bind('<space>',lambda e:viewer.set_workspace('editor' if viewer._workspace_mode=='viewer' else 'viewer'))
        self.bind('<Configure>',lambda e:self.redraw())
        self.redraw()

    def redraw(self):
        t=self.viewer._theme();self.configure(bg=t['toolbar']);self.delete('all')
        def pill(x1,y1,x2,y2,color):
            r=(y2-y1)/2
            self.create_rectangle(x1+r,y1,x2-r,y2,fill=color,outline=color)
            self.create_oval(x1,y1,x1+2*r,y2,fill=color,outline=color)
            self.create_oval(x2-2*r,y1,x2,y2,fill=color,outline=color)
        pill(2,5,152,39,'#111923');pill(3,4,151,36,'#465365');pill(5,6,149,34,'#202A38')
        x=7 if self.viewer._workspace_mode=='viewer' else 78
        pill(x,7,x+69,33,'#3277B3');pill(x+1,8,x+68,21,'#579CD5')
        for cx,label,mode in [(41,'뷰어','viewer'),(113,'편집','editor')]:
            active=mode==self.viewer._workspace_mode
            self.create_text(cx-5,20,text=label,fill='#FFFFFF' if active else '#ABB8C8',font=('맑은 고딕',10,'bold'))
            if active:
                for r,color in [(6,'#316E7C'),(4,'#49B9BA'),(2,'#B2FFF3')]:
                    self.create_oval(cx+22-r,20-r,cx+22+r,20+r,fill=color,outline=color)
            else:self.create_oval(cx+20,18,cx+24,22,fill='#627081',outline='')


class DockSurface(ttk.Frame):
    def __init__(self,parent,title,viewer):
        super().__init__(parent,style='Panel.TFrame',padding=8)
        self._close=lambda:None
        self._running=False
        ttk.Label(self,text=title,style='Section.TLabel',wraplength=230).pack(anchor='w',pady=8)
        self.body=ttk.Frame(self,style='Panel.TFrame');self.body.pack(fill='both',expand=True)
        self.pack(fill='both',expand=True)

    def protocol(self,name,callback):
        if name=='WM_DELETE_WINDOW':self._close=callback;self._running=True


class DockPage(ttk.Frame):
    """Keep controls reachable when the third column is short or narrow."""
    def __init__(self,parent,viewer):
        super().__init__(parent,style='Panel.TFrame',width=270)
        self.canvas=tk.Canvas(self,highlightthickness=0,bg=viewer._theme()['panel'],width=260)
        scroll=ttk.Scrollbar(self,command=self.canvas.yview)
        scroll.pack(side='right',fill='y');self.canvas.pack(side='left',fill='both',expand=True)
        self.canvas.configure(yscrollcommand=scroll.set)
        self.body=ttk.Frame(self.canvas,style='Panel.TFrame',padding=8)
        self.item=self.canvas.create_window(0,0,window=self.body,anchor='nw')
        self.canvas.bind('<Configure>',self.layout)
        self.body.bind('<Configure>',self.layout)
        self.canvas.bind('<MouseWheel>',self.wheel)

    def layout(self,event=None):
        self.canvas.itemconfigure(self.item,width=max(1,self.canvas.winfo_width()))
        self.canvas.configure(scrollregion=(0,0,max(1,self.canvas.winfo_width()),max(self.canvas.winfo_height(),self.body.winfo_reqheight())))
        def visit(widget):
            for child in widget.winfo_children():
                if not isinstance(child,(tk.Text,ttk.Combobox)):
                    child.bind('<MouseWheel>',self.wheel)
                visit(child)
        visit(self.body)

    def wheel(self,event):
        self.canvas.yview_scroll(-3 if event.delta>0 else 3,'units');return 'break'


class DockMixin:
    def toggle_info_panel(self):
        if hasattr(self,'_dock_pages') and self._dock_page!='정보':
            self._activate_dock('정보')
        else:super().toggle_info_panel()

    def _build_dock(self):
        panel=self._right_panel
        self._dock_page='정보';self._dock_pages={}
        original=list(panel.winfo_children())
        self._dock_title=original[0]
        self._dock_info=original[1]
        self._dock_pages['정보']=self._dock_info
        for name in ('AI 생성 판단','성인 필터','도구'):
            self._dock_pages[name]=DockPage(panel,self)
        ai=self._dock_pages['AI 생성 판단'].body
        ttk.Label(ai,text='C2PA 생성·편집 기록',style='Section.TLabel').pack(anchor='w',pady=8)
        ttk.Label(ai,text='AI 생성 여부는 출처 기록을 근거로 확인합니다.\n기록이 없는 사진은 판단할 수 없습니다.',wraplength=230).pack(anchor='w',pady=8)
        ttk.Button(ai,text='현재 사진 출처 검사',command=self.provenance_dialog).pack(fill='x',pady=6)
        self._dock_tasks={}
        for name in ('AI 생성 판단','도구'):
            host=ttk.Frame(self._dock_pages[name].body,style='Panel.TFrame')
            host.pack(fill='both',expand=True)
            self._dock_tasks[name]=host
        safety=self._dock_pages['성인 필터'].body
        ttk.Label(safety,text='성인 콘텐츠 필터',style='Section.TLabel').pack(anchor='w',pady=8)
        ttk.Label(safety,text='PC에서 처리합니다. 켤 때 모델을 불러옵니다.\n판별 불가 파일도 숨김 처리합니다.',wraplength=230).pack(anchor='w',pady=8)
        self._dock_filter=tk.StringVar(value=self._content_filter_mode)
        for label,value in [('끄기','off'),('켜기','explicit')]:
            ttk.Radiobutton(safety,text=label,variable=self._dock_filter,value=value).pack(anchor='w',pady=4)
        self._dock_filter_status=ttk.Label(safety,text='',wraplength=230)
        def apply():
            self._set_content_filter(self._dock_filter.get())
            self._dock_filter.set(self._content_filter_mode)
            self._dock_filter_status.configure(text='필터 켜짐 · 파일을 열 때 검사' if self._content_filter_mode=='explicit' else '필터 꺼짐')
        ttk.Button(safety,text='필터 적용',command=apply).pack(fill='x',pady=8)
        self._dock_filter_status.pack(anchor='w',pady=8)
        tools=self._dock_pages['도구'].body
        commands=[('정보 색인 · 촬영일 + OCR',self.index_all),('검색 색인 삭제',self.delete_index_dialog)]
        for text,command in commands:ttk.Button(tools,text=text,command=command).pack(fill='x',pady=3,before=self._dock_tasks['도구'])
    def _sync_dock_buttons(self):
        for name,button in getattr(self,'_dock_tab_buttons',{}).items():
            button.configure(style='Accent.Icon.Tool.TButton' if self._info_visible and name==self._dock_page else 'Icon.Tool.TButton')

    def hide_info_panel(self):
        super().hide_info_panel()
        self._sync_dock_buttons()

    def select_dock(self,name):
        if name==self._dock_page and self._info_visible:
            self.hide_info_panel();return
        self._activate_dock(name)

    def _activate_dock(self,name):
        self._dock_page=name
        if name=='성인 필터':self._dock_filter.set(self._content_filter_mode)
        for key,page in self._dock_pages.items():
            page.pack_forget()
        self._dock_pages[name].pack(fill='both',expand=True)
        for child in self._dock_title.winfo_children():
            if isinstance(child,ttk.Label):child.configure(text='사진 정보' if name=='정보' else name)
        if not self._info_visible:self.show_info_panel()
        self._sync_dock_buttons()

    def _window(self,title,size=None):
        if any(word in title for word in ('출처','C2PA','글자','OCR','색인','촬영 정보','검색')):
            from croweyes_dialogs import FittedDialog
            win=FittedDialog(self,title,540)
            return win,win.body
        return super()._window(title,size)

    def _text(self,title,text):
        if any(word in title for word in ('출처','C2PA','글자','OCR','색인','검색','촬영 정보')):
            win,frame=self._window(title)
            if '색인' in title or '출처' in title or 'C2PA' in title:
                # Results have a content-sized card; no copy button or scrollbar.
                import textwrap
                lines=[]
                for line in str(text).splitlines():
                    lines.extend(textwrap.wrap(line,52,replace_whitespace=False,drop_whitespace=False) or [''])
                pages=['\n'.join(lines[i:i+8]) for i in range(0,len(lines),8)] or ['']
                label=ttk.Label(frame,text=pages[0],wraplength=480,justify='left')
                label.pack(fill='x',pady=8)
                if len(pages)>1:
                    row=ttk.Frame(frame);row.pack(fill='x',pady=6)
                    number=ttk.Label(row);number.pack(side='left',expand=True)
                    state=[0]
                    def show(delta):
                        state[0]=max(0,min(len(pages)-1,state[0]+delta))
                        label.configure(text=pages[state[0]])
                        number.configure(text=f'{state[0]+1} / {len(pages)}')
                        prev.configure(state='disabled' if state[0]==0 else 'normal')
                        nxt.configure(state='disabled' if state[0]==len(pages)-1 else 'normal')
                    prev=ttk.Button(row,text='이전',command=lambda:show(-1));prev.pack(side='left',padx=3)
                    nxt=ttk.Button(row,text='다음',command=lambda:show(1));nxt.pack(side='left',padx=3)
                    show(0)
            else:
                view=tk.Text(frame,width=48,height=8,wrap='word',relief='flat',bg=self._theme()['panel'],fg=self._theme()['fg'])
                scroll=ttk.Scrollbar(frame,command=view.yview)
                view.configure(yscrollcommand=scroll.set)
                scroll.pack(side='right',fill='y');view.pack(fill='both',expand=True)
                view.insert('1.0',text);view.configure(state='disabled')
                ttk.Button(frame,text='글자 복사',command=lambda:(self.clipboard_clear(),self.clipboard_append(text))).pack(pady=6)
            return win
        return super()._text(title,text)

    def adult_filter_dialog(self):
        from croweyes_dialogs import FittedDialog
        win=FittedDialog(self,'19 · 성인 콘텐츠 필터',520);frame=win.body
        ttk.Label(frame,text='  성인 콘텐츠 보호',image=self._icons['toolbar_shield'],compound='left',style='Section.TLabel').pack(anchor='w',pady=(0,8))
        ttk.Label(frame,text='사진을 PC 안에서 검사합니다. 필터를 켜면 성인 콘텐츠와 판별할 수 없는 파일을 가립니다. 모델은 켤 때만 불러옵니다. 판별 결과가 항상 정확하지는 않습니다.',wraplength=460,justify='left').pack(fill='x',pady=8)
        enabled=tk.BooleanVar(value=self._content_filter_mode=='explicit')
        options=ttk.Frame(frame);options.pack(fill='x',pady=10)
        ttk.Radiobutton(options,text='ON · 보호 켜기',variable=enabled,value=True).pack(side='left',padx=12)
        ttk.Radiobutton(options,text='OFF · 보호 끄기',variable=enabled,value=False).pack(side='left',padx=12)
        def apply():
            self._set_content_filter('explicit' if enabled.get() else 'off')
            win.destroy()
        ttk.Button(frame,text='적용',style='Accent.TButton',command=apply).pack(anchor='e',pady=6)
        return win
