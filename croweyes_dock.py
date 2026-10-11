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

    def _update_info(self):
        super()._update_info()
        if hasattr(self,'_pixel_label'):self._clear_pixel()

    def _build_dock(self):
        panel=self._right_panel
        self._dock_page='정보';self._dock_pages={}
        original=list(panel.winfo_children())
        self._dock_title=original[0]
        self._dock_info=original[1]
        self._dock_pages['정보']=self._dock_info
        footer=ttk.Frame(self._dock_info,style='Panel.TFrame')
        footer.pack(side='bottom',fill='x',before=self.info_text)
        self._pixel_swatch=tk.Label(footer,width=3,height=2,relief='solid',borderwidth=1,bg=self._theme()['panel'])
        self._pixel_swatch.pack(side='left',padx=4,pady=8)
        self._pixel_label=ttk.Label(footer,text='이미지 위로 포인터를 이동하세요',wraplength=190)
        self._pixel_label.pack(side='left',fill='x',expand=True)
        self.canvas.bind('<Leave>',lambda e:self._clear_pixel(),add='+')
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
        commands=[('글자 인식 (OCR)',self.ocr_dialog),('영역 글자 인식',self.ocr_region),
                  ('촬영일 색인',lambda:self.index_collection(False)),('OCR 내용 색인',lambda:self.index_collection(True)),
                  ('촬영일·글자 검색',self.search_dialog)]
        for text,command in commands:ttk.Button(tools,text=text,command=command).pack(fill='x',pady=3,before=self._dock_tasks['도구'])
        self._dock_tabs=ttk.Frame(self,style='Toolbar.TFrame')
        self._dock_tab_buttons={}
        for name,label in [('정보','정\n보'),('AI 생성 판단','AI 생성\n판단'),('성인 필터','성인\n필터'),('도구','도\n구')]:
            button=ttk.Button(self._dock_tabs,text=label,width=6,command=lambda n=name:self.select_dock(n))
            button.pack(fill='x',pady=3,ipady=4)
            self._dock_tab_buttons[name]=button
        self._info_tab=self._dock_tabs
        self._dock_tabs.grid(row=2,column=1,sticky='ne',pady=12,padx=(0,4))

    def _clear_pixel(self):
        self._pixel_label.configure(text='이미지 위로 포인터를 이동하세요')
        self._pixel_swatch.configure(bg=self._theme()['panel'])

    def select_dock(self,name):
        if name==self._dock_page and self._info_visible:
            self.hide_info_panel();return
        self._activate_dock(name)

    def _activate_dock(self,name):
        self._dock_page=name
        if name=='성인 필터':self._dock_filter.set(self._content_filter_mode)
        for key,page in self._dock_pages.items():
            page.pack_forget()
            self._dock_tab_buttons[key].configure(style='Accent.Icon.Tool.TButton' if key==name else 'Icon.Tool.TButton')
        self._dock_pages[name].pack(fill='both',expand=True)
        for child in self._dock_title.winfo_children():
            if isinstance(child,ttk.Label):child.configure(text='사진 정보' if name=='정보' else name)
        if not self._info_visible:self.show_info_panel()

    def _window(self,title,size=None):
        ai=any(word in title for word in ('출처','C2PA'))
        tools=any(word in title for word in ('글자','OCR','색인','촬영 정보','검색'))
        if hasattr(self,'_dock_tasks') and (ai or tools):
            name='AI 생성 판단' if ai else '도구';self._activate_dock(name)
            host=self._dock_tasks[name]
            # Keep active progress widgets alive until their worker finishes.
            for child in host.winfo_children():
                if getattr(child,'_running',False):
                    child._close();child.pack_forget()
                else:child.destroy()
            surface=DockSurface(host,title,self)
            return surface,surface.body
        return super()._window(title,size)

    def _text(self,title,text):
        if hasattr(self,'_dock_tasks') and any(word in title for word in ('출처','C2PA','글자','OCR','색인','검색','촬영 정보')):
            win,frame=self._window(title)
            view=tk.Text(frame,width=26,height=10,wrap='word',relief='flat',bg=self._theme()['panel'],fg=self._theme()['fg'])
            scroll=ttk.Scrollbar(frame,command=view.yview);scroll.pack(side='right',fill='y')
            view.configure(yscrollcommand=scroll.set);view.pack(fill='both',expand=True)
            view.insert('1.0',text);view.configure(state='disabled')
            ttk.Button(win,text='전체 복사',command=lambda:(self.clipboard_clear(),self.clipboard_append(text))).pack(pady=6)
            return win
        return super()._text(title,text)
