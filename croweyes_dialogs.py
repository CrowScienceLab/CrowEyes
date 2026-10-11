"""Compact tool surfaces contained by the viewer window."""
import tkinter as tk
from tkinter import ttk


class EmbeddedDialog(ttk.Frame):
    def __init__(self, viewer, title, size=None):
        super().__init__(viewer, style='Panel.TFrame', relief='solid', borderwidth=1)
        self.viewer=viewer
        self._close=self.destroy
        viewer.update_idletasks()
        requested=tuple(map(int,size.split('x'))) if size else (500,480)
        self._size=requested
        header=ttk.Frame(self,style='Panel.TFrame',padding=(12,8))
        header.pack(fill='x')
        ttk.Label(header,text=title,style='Section.TLabel').pack(side='left')
        ttk.Button(header,text='×',width=3,command=lambda:self._close()).pack(side='right')
        container=ttk.Frame(self,style='Panel.TFrame')
        container.pack(fill='both',expand=True)
        container.rowconfigure(0,weight=1);container.columnconfigure(0,weight=1)
        self.canvas=tk.Canvas(container,background=viewer._theme()['panel'],highlightthickness=0)
        self.canvas.grid(row=0,column=0,sticky='nsew')
        vertical=ttk.Scrollbar(container,orient='vertical',command=self.canvas.yview)
        horizontal=ttk.Scrollbar(container,orient='horizontal',command=self.canvas.xview)
        vertical.grid(row=0,column=1,sticky='ns');horizontal.grid(row=1,column=0,sticky='ew')
        self.canvas.configure(yscrollcommand=vertical.set,xscrollcommand=horizontal.set)
        self.body=ttk.Frame(self.canvas,style='Panel.TFrame',padding=(14,8))
        self._item=self.canvas.create_window(0,0,window=self.body,anchor='nw')
        self.body.bind('<Configure>',self._layout)
        self.canvas.bind('<Configure>',self._layout)
        self._resize_binding=viewer.bind('<Configure>',self._resize,add='+')
        self._resize()
        self.lift()
        self.bind('<Escape>',lambda e:self._close())
        self.focus_set()
        self.after_idle(self._bind_children)

    def _bind_children(self):
        def visit(widget):
            for child in widget.winfo_children():
                tags=list(child.bindtags())
                if str(self) not in tags:tags.insert(2,str(self));child.bindtags(tuple(tags))
                visit(child)
        visit(self)

    def _layout(self,event=None):
        self.canvas.itemconfigure(self._item,width=max(self.canvas.winfo_width(),self.body.winfo_reqwidth()),height=max(self.canvas.winfo_height(),self.body.winfo_reqheight()))
        self.canvas.configure(scrollregion=self.canvas.bbox('all'))

    def _resize(self,event=None):
        if event is not None and event.widget is not self.viewer:return
        width=min(self._size[0],max(260,self.viewer.winfo_width()-60))
        height=min(self._size[1],max(160,self.viewer.winfo_height()-160))
        self.place(relx=.5,rely=.52,anchor='center',width=width,height=height)

    def protocol(self,name,command):
        if name=='WM_DELETE_WINDOW':self._close=command

    def destroy(self):
        if self._resize_binding:
            self.viewer.unbind('<Configure>',self._resize_binding)
            self._resize_binding=None
        super().destroy()


class FittedDialog(ttk.Frame):
    """Content-sized settings card without scrolling surfaces."""
    def __init__(self,viewer,title,width=640):
        super().__init__(viewer,style='Panel.TFrame',relief='solid',borderwidth=1)
        self.viewer=viewer;self._width=width;self._close=self.destroy
        header=ttk.Frame(self,style='Panel.TFrame',padding=(14,8))
        header.pack(fill='x')
        ttk.Label(header,text=title,style='Section.TLabel').pack(side='left')
        ttk.Button(header,text='×',width=3,command=lambda:self._close()).pack(side='right')
        self.body=ttk.Frame(self,style='Panel.TFrame',padding=(18,12))
        self.body.pack(fill='both',expand=True)
        self._resize_binding=viewer.bind('<Configure>',self._resize,add='+')
        self.body.bind('<Configure>',self._resize)
        self.bind('<Escape>',lambda e:self._close())
        self.after_idle(self._resize)
        self.place(relx=.5,rely=.5,anchor='center',width=width,height=300)
        self.lift()

    def _resize(self,event=None):
        if event is not None and event.widget not in (self.viewer,self.body):return
        width=min(self._width,max(260,self.viewer.winfo_width()-40))
        height=min(max(160,self.winfo_reqheight()+8),max(180,self.viewer.winfo_height()-50))
        self.place(relx=.5,rely=.5,anchor='center',width=width,height=height)

    def protocol(self,name,callback):
        if name=='WM_DELETE_WINDOW':self._close=callback

    def destroy(self):
        if self._resize_binding:
            self.viewer.unbind('<Configure>',self._resize_binding);self._resize_binding=None
        super().destroy()


def settings_combo(parent,viewer,variable,values,category):
    """Readable compact selectors with distinct appearance/interaction colors."""
    dark=viewer.settings.get('ui_theme','croweyes_dark')=='croweyes_dark'
    palette={'appearance':('#20364A','#DFF1FF','#4AA6DF') if dark else ('#E9F5FF','#174C78','#287CB5'),
             'interaction':('#203D36','#DDF7ED','#43A681') if dark else ('#E6F5EE','#185B40','#247654')}
    bg,fg,accent=palette[category]
    style_name=category.title()+'.Settings.TCombobox'
    style=ttk.Style(viewer)
    style.configure(style_name,fieldbackground=bg,foreground=fg,background=accent,arrowcolor=fg,padding=(7,5),font=('맑은 고딕',10))
    style.map(style_name,fieldbackground=[('readonly',bg)],foreground=[('readonly',fg)],selectbackground=[('readonly',bg)],selectforeground=[('readonly',fg)])
    combo=ttk.Combobox(parent,textvariable=variable,values=values,state='readonly',width=22,height=min(6,len(values)),style=style_name)
    combo._croweyes_style=style_name
    combo.tk.call(combo._w,'configure','-style',style_name)
    def style_popup():
        popup=combo.tk.call('ttk::combobox::PopdownWindow',combo)
        combo.tk.call(str(popup)+'.f.l','configure','-background',bg,'-foreground',fg,'-selectbackground',accent,'-selectforeground','#FFFFFF','-font',('맑은 고딕',10))
    combo.configure(postcommand=style_popup)
    return combo
