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
