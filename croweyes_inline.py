"""Edit directly on the main canvas with vector history and inline controls."""
import tkinter as tk
from tkinter import ttk
from PIL import Image


class InlineEditorMixin:
    def __init__(self,*args,**kwargs):
        self._annotation_ops=[]
        self._annotation_source=None
        self._edit_tool=None
        self._draw_start=None
        self._draw_ghost=None
        super().__init__(*args,**kwargs)

    def _build_ui(self):
        super()._build_ui()
        self._edit_parameters=ttk.Frame(self._center_panel,style='Panel.TFrame',padding=8)
        self.canvas.grid_configure(row=1)
        self._center_panel.rowconfigure(0,weight=0)
        self._center_panel.rowconfigure(1,weight=1)

    def _state(self):
        return (*super()._state(),tuple(self._annotation_ops))

    def _restore_state(self,state):
        self._annotation_ops=list(state[5]) if len(state)>5 else []
        super()._restore_state(state[:5])

    def _apply_current_transforms(self,image):
        source=str(self.source_path)
        if source!=self._annotation_source:
            self._annotation_source=source
            self._annotation_ops=[]
            self._undo_states.clear();self._redo_states.clear()
        if self._annotation_ops:
            from croweyes_annotation import render
            operations=[(kind,tuple(round(value*(image.width if i%2==0 else image.height)) for i,value in enumerate(box)),color,text) for kind,box,color,text in self._annotation_ops]
            image=render(image,operations)
        return super()._apply_current_transforms(image)

    def annotation_dialog(self):
        self.select_edit_tool('주석')

    def show_resize_dialog(self):
        self.select_edit_tool('크기·비율')

    def select_edit_tool(self,tool):
        if self._workspace_mode!='editor':self.set_workspace('editor')
        self._interrupt_slideshow()
        if self.anim_playing:self.toggle_animation()
        if self._region_copy_mode:self._cancel_region_copy()
        self._edit_tool=tool
        self._draw_start=None
        for child in self._edit_parameters.winfo_children():child.destroy()
        self._edit_parameters.grid(row=0,column=0,sticky='ew')
        self.canvas.configure(cursor='crosshair' if tool in ('주석','형광펜','모자이크') else 'arrow')
        ttk.Label(self._edit_parameters,text=tool,style='Section.TLabel').pack(side='left',padx=(0,10))
        if tool in ('주석','형광펜','모자이크'):
            self._draw_kind=tk.StringVar(value='화살표' if tool=='주석' else tool)
            self._draw_color=tk.StringVar(value='#ef4444' if tool=='주석' else '#facc15')
            self._draw_text=tk.StringVar()
            if tool=='주석':
                ttk.Combobox(self._edit_parameters,textvariable=self._draw_kind,values=['화살표','사각형','텍스트'],state='readonly',width=8).pack(side='left',padx=4)
                ttk.Entry(self._edit_parameters,textvariable=self._draw_text,width=12).pack(side='left',padx=4)
            if tool!='모자이크':
                ttk.Combobox(self._edit_parameters,textvariable=self._draw_color,values=['#ef4444','#facc15','#22c55e','#38bdf8','#ffffff'],state='readonly',width=8).pack(side='left',padx=4)
            ttk.Label(self._edit_parameters,text='드래그',style='Section.TLabel').pack(side='left',padx=4)
        elif tool=='밝기·대비':
            for label,var in [('밝기',self.bright_var),('대비',self.contrast_var)]:
                ttk.Label(self._edit_parameters,text=label,style='Section.TLabel').pack(side='left',padx=4)
                ttk.Scale(self._edit_parameters,from_=.2,to=2,variable=var,command=self._on_adjust,length=130).pack(side='left')
        elif tool=='크기·비율':
            size=self.display_image.size if self.display_image else (0,0)
            width=tk.StringVar(value=str(size[0]));height=tk.StringVar(value=str(size[1]));ratio=tk.BooleanVar(value=True)
            for label,var in [('가로',width),('세로',height)]:
                ttk.Label(self._edit_parameters,text=label).pack(side='left',padx=4)
                ttk.Entry(self._edit_parameters,textvariable=var,width=5).pack(side='left')
            ttk.Checkbutton(self._edit_parameters,text='비율 유지',variable=ratio).pack(side='left',padx=6)
            def save_size():
                if self.display_image is None:return
                try:
                    from croweyes_editing import validate_size
                    w,h=int(width.get()),int(height.get());validate_size(w,h)
                except ValueError as exc:
                    self.status.configure(text=str(exc));return
                image=self.display_image.copy()
                if ratio.get():
                    factor=min(w/image.width,h/image.height)
                    image=image.resize((max(1,round(image.width*factor)),max(1,round(image.height*factor))),Image.Resampling.LANCZOS)
                else:image=image.resize((w,h),Image.Resampling.LANCZOS)
                self.quality_dialog(image=image)
            ttk.Button(self._edit_parameters,text='저장',command=save_size).pack(side='left',padx=6)
        ttk.Button(self._edit_parameters,text='완료',command=self.end_edit_tool).pack(side='right')
        self.canvas.focus_set()

    def end_edit_tool(self):
        self._edit_tool=None;self._draw_start=None
        self._edit_parameters.grid_remove()
        self.canvas.configure(cursor='arrow')
        if self._draw_ghost is not None:self.canvas.delete(self._draw_ghost)
        self._draw_ghost=None

    def start_region_copy(self,*args,**kwargs):
        self.end_edit_tool()
        return super().start_region_copy(*args,**kwargs)

    def _source_point(self,event):
        if self.display_image is None or self.pil_image is None:return None
        z=self._effective_bitmap_zoom()
        x=(event.x-self.canvas.winfo_width()/2-self.offset_x)/z+self.display_image.width/2
        y=(event.y-self.canvas.winfo_height()/2-self.offset_y)/z+self.display_image.height/2
        if not (0<=x<=self.display_image.width and 0<=y<=self.display_image.height):return None
        w,h=self.pil_image.size
        rotation=self.rotation%360
        if rotation==90:x,y=y,h-x
        elif rotation==180:x,y=w-x,h-y
        elif rotation==270:x,y=w-y,x
        if self.flip_h:x=w-x
        if self.flip_v:y=h-y
        return max(0,min(1,x/w)),max(0,min(1,y/h))

    def _pan_start(self,event):
        if self._edit_tool not in ('주석','형광펜','모자이크'):return super()._pan_start(event)
        self._draw_start=self._source_point(event)
        if self._draw_start is not None:
            self._draw_screen=(event.x,event.y)
            self._draw_ghost=self.canvas.create_rectangle(event.x,event.y,event.x,event.y,outline=self._draw_color.get(),dash=(4,3))
        return 'break'

    def _pan_move(self,event):
        if self._edit_tool not in ('주석','형광펜','모자이크'):return super()._pan_move(event)
        if self._draw_ghost is not None:self.canvas.coords(self._draw_ghost,*self._draw_screen,event.x,event.y)
        return 'break'

    def _pan_end(self,event):
        if self._edit_tool not in ('주석','형광펜','모자이크'):return super()._pan_end(event)
        start,end=self._draw_start,self._source_point(event)
        self._draw_start=None
        if self._draw_ghost is not None:self.canvas.delete(self._draw_ghost)
        self._draw_ghost=None
        if start is None or end is None:return 'break'
        kind=self._draw_kind.get();text=self._draw_text.get()
        if kind=='텍스트' and not text:
            self.status.configure(text='상단에 주석 글자를 입력한 뒤 사진 위에 표시하세요.');return 'break'
        if kind!='텍스트' and (abs(start[0]-end[0])<.001 or abs(start[1]-end[1])<.001):return 'break'
        box=(*start,*end) if kind=='화살표' else (min(start[0],end[0]),min(start[1],end[1]),max(start[0],end[0]),max(start[1],end[1]))
        self._record()
        self._annotation_ops.append((kind,box,self._draw_color.get(),text))
        self._rebuild_display();self.redraw();self._update_info()
        return 'break'
