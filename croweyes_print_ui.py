"""Resizable print preview with a fixed footer and physical multi-sheet layout."""
import sys
import threading
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from PIL import Image, ImageTk
from croweyes_printing import PAPERS, make_plan, tile_bitmap, finite, preview_dpi


class PrintPreview(tk.Toplevel):
    PAPER_MM=PAPERS

    def __init__(self,viewer):
        super().__init__(viewer)
        self.viewer=viewer;self.core=sys.modules[viewer.__class__.__module__]
        self.title('이미지 인쇄 · 배율 / 여백 / 분할 출력')
        self.transient(viewer)
        width=min(1160,self.winfo_screenwidth()-70);height=min(800,self.winfo_screenheight()-100)
        viewer.update_idletasks()
        x=max(0,min(self.winfo_screenwidth()-width-12,viewer.winfo_rootx()+(viewer.winfo_width()-width)//2))
        y=max(30,min(self.winfo_screenheight()-height-70,viewer.winfo_rooty()+(viewer.winfo_height()-height)//2))
        self.geometry(f'{width}x{height}+{x}+{y}');self.minsize(min(880,width),min(600,height))
        try:self.iconbitmap(str(self.core.resource_path('assets','icons','croweyes-2.0.ico')))
        except tk.TclError:pass
        self.columnconfigure(0,weight=1);self.rowconfigure(0,weight=1)
        settings=viewer.settings
        self.printer_names=self.core.enumerate_printer_names()
        selected=str(settings.get('print_printer',''))
        if selected not in self.printer_names:selected=self.core.get_default_printer_name()
        self.printer_var=tk.StringVar(value=selected)
        paper=settings.get('print_paper','A4');self.paper_var=tk.StringVar(value=paper if paper in PAPERS else 'A4')
        self.orientation_var=tk.StringVar(value=settings.get('print_orientation','portrait'))
        self.scale_var=tk.StringVar(value=settings.get('print_scale_mode','fit'))
        self.percent_var=tk.StringVar(value=str(settings.get('print_percent',100)))
        self.dpi_var=tk.StringVar(value=f'{preview_dpi(viewer):.6g}')
        self.copies_var=tk.StringVar(value=str(settings.get('print_copies',1)))
        self.tiles_var=tk.IntVar(value=settings.get('print_tiles',1))
        self.margins_vars={key:tk.StringVar(value=str(settings.get('print_margins',{}).get(key,10))) for key in ('left','top','right','bottom')}
        self.print_to_file_var=tk.BooleanVar(value=False);self.save_defaults_var=tk.BooleanVar(value=False)
        self.summary=tk.StringVar();self.preview_photos=[];self.preview_photo=None
        self._redraw_job=None;self._geometry_cache={};self._geometry_results={};self._geometry_pending=set()
        self._poll_job=None
        body=ttk.Frame(self,padding=12,style='Panel.TFrame');body.grid(row=0,column=0,sticky='nsew')
        body.rowconfigure(0,weight=1);body.columnconfigure(0,weight=1)
        self.preview=tk.Canvas(body,bg='#171E28',highlightthickness=0)
        self.preview.grid(row=0,column=0,sticky='nsew',padx=(0,12))
        side=ttk.Frame(body,style='Panel.TFrame');side.grid(row=0,column=1,sticky='ns')
        ttk.Label(side,text='인쇄 설정',style='Title.TLabel').pack(anchor='w',pady=(4,10))
        tabs=ttk.Notebook(side);tabs.pack(fill='both',expand=True)
        basic=ttk.Frame(tabs,padding=12);size=ttk.Frame(tabs,padding=12);poster=ttk.Frame(tabs,padding=12)
        for page,label in ((basic,'기본'),(size,'크기·여백'),(poster,'분할 출력')):tabs.add(page,text=label)
        def combo(parent,label,var,values):
            ttk.Label(parent,text=label).pack(anchor='w',pady=(6,3))
            control=ttk.Combobox(parent,textvariable=var,values=values,state='readonly',width=26)
            control.pack(fill='x',pady=(0,7));return control
        combo(basic,'프린터',self.printer_var,self.printer_names)
        combo(basic,'용지',self.paper_var,list(PAPERS))
        ttk.Label(basic,text='용지 방향').pack(anchor='w',pady=(10,4))
        for label,value in [('세로','portrait'),('가로','landscape')]:
            ttk.Radiobutton(basic,text=label,variable=self.orientation_var,value=value).pack(anchor='w',pady=2)
        ttk.Label(basic,text='인쇄 부수 (분할 전체 묶음)').pack(anchor='w',pady=(12,4))
        ttk.Spinbox(basic,from_=1,to=999,textvariable=self.copies_var,width=9).pack(anchor='w')
        ttk.Checkbutton(basic,text='파일로 출력 (PDF / PRN)',variable=self.print_to_file_var).pack(anchor='w',pady=(14,4))
        ttk.Checkbutton(basic,text='이 설정을 다음에도 사용',variable=self.save_defaults_var).pack(anchor='w')
        for label,value in [('선택한 전체 용지에 맞춤','fit'),('원본 크기 (100%)','actual'),('사용자 배율 (%)','percent')]:
            ttk.Radiobutton(size,text=label,variable=self.scale_var,value=value).pack(anchor='w',pady=3)
        row=ttk.Frame(size);row.pack(fill='x',pady=6)
        ttk.Spinbox(row,from_=1,to=1000,increment=5,textvariable=self.percent_var,width=9).pack(side='left')
        ttk.Label(row,text=' %  (1~1000)').pack(side='left')
        ttk.Label(size,text='인쇄 해상도 (DPI)').pack(anchor='w',pady=(8,3))
        ttk.Spinbox(size,from_=.01,to=2400,textvariable=self.dpi_var,width=9).pack(anchor='w')
        ttk.Label(size,text='원본 DPI·미리보기 축소율 반영\nDPI 없으면 96 기준 · 하단 mm 확인',wraplength=270).pack(anchor='w',pady=4)
        ttk.Separator(size).pack(fill='x',pady=7)
        ttk.Label(size,text='용지 가장자리 여백 (mm)').pack(anchor='w')
        margins=ttk.Frame(size);margins.pack(fill='x',pady=5)
        for i,(key,label) in enumerate([('left','왼쪽'),('top','위'),('right','오른쪽'),('bottom','아래')]):
            ttk.Label(margins,text=label).grid(row=i//2,column=(i%2)*2,sticky='w',padx=(0,5),pady=3)
            ttk.Spinbox(margins,from_=0,to=200,textvariable=self.margins_vars[key],width=6).grid(row=i//2,column=(i%2)*2+1,padx=(0,10))
        ttk.Label(size,text='프린터 최소 여백은 자동 반영됩니다.',wraplength=270).pack(anchor='w',pady=4)
        for label,value in [('1장 출력','1'),('2장 분할 (방향 자동 선택)','2'),('4장 분할 (2 × 2)','4')]:
            ttk.Radiobutton(poster,text=label,variable=self.tiles_var,value=int(value)).pack(anchor='w',pady=8)
        ttk.Label(poster,text='예: A2 포스터 → A4 4장\n\n원본 크기·배율을 선택하거나 전체 용지에 맞춰 출력하세요.\n\n점선은 인쇄되지 않습니다. 여백을 잘라 순서대로 이어 붙이세요.',wraplength=270,justify='left').pack(anchor='w',pady=6)
        # Footer is a separate grid row, so controls can never push it offscreen.
        footer=ttk.Frame(self,padding=(14,8),style='Panel.TFrame');footer.grid(row=1,column=0,sticky='ew')
        footer.columnconfigure(0,weight=1)
        ttk.Label(footer,textvariable=self.summary,wraplength=600,justify='left').grid(row=0,column=0,sticky='w',padx=(0,10))
        self.close_button=ttk.Button(footer,text='닫기',command=self.destroy)
        self.close_button.grid(row=0,column=1,padx=6)
        self.print_button=ttk.Button(footer,text='인쇄',style='Accent.TButton',command=self.do_print)
        self.print_button.grid(row=0,column=2,padx=6,ipadx=12,ipady=4)
        for var in [self.printer_var,self.paper_var,self.orientation_var,self.scale_var,self.percent_var,self.dpi_var,self.copies_var,self.tiles_var,*self.margins_vars.values()]:
            var.trace_add('write',self._schedule)
        self.preview.bind('<Configure>',self._schedule)
        self.bind('<Escape>',lambda e:self.destroy())
        self.after_idle(self.redraw_preview)

    def _schedule(self,*_):
        if self._redraw_job:self.after_cancel(self._redraw_job)
        self._redraw_job=self.after(100,self.redraw_preview)

    def _paper_size(self):
        paper=PAPERS[self.paper_var.get()]
        return paper[::-1] if self.orientation_var.get()=='landscape' else paper

    def _printer_geometry(self):
        key=(self.printer_var.get(),self.paper_var.get(),self.orientation_var.get())
        if key in self._geometry_cache:return self._geometry_cache[key]
        if key not in self._geometry_pending:
            self._geometry_pending.add(key)
            owner=self.winfo_id()
            def worker():
                try:
                    value=self.core.print_image_windows(None,owner,'',printer_name=key[0],paper=key[1],orientation=key[2],geometry_only=True)
                except Exception:value=None
                self._geometry_results[key]=value
            threading.Thread(target=worker,name='CrowEyesPrintGeometry',daemon=True).start()
            if self._poll_job is None:self._poll_job=self.after(80,self._poll_geometry)
        return None

    def _poll_geometry(self):
        self._poll_job=None
        if not self.winfo_exists():return
        for key,value in list(self._geometry_results.items()):
            self._geometry_cache[key]=value;self._geometry_results.pop(key,None);self._geometry_pending.discard(key)
        self.redraw_preview()
        if self._geometry_pending:self._poll_job=self.after(100,self._poll_geometry)

    def _print_options(self):
        margins=tuple(finite(v.get(),'여백(mm)',0,200) for v in self.margins_vars.values())
        percent=finite(self.percent_var.get(),'배율',1,1000)
        dpi=finite(self.dpi_var.get(),'DPI',.01,2400)
        copies=finite(self.copies_var.get(),'부수',1,999)
        if copies!=int(copies):raise ValueError('부수는 정수로 입력하세요.')
        return dict(scale_percent=percent,margins_mm=margins,tiles=self.tiles_var.get(),source_dpi=dpi,copies=int(copies))

    def _plan(self,options):
        geometry=self._printer_geometry()
        return make_plan(self.viewer.display_image.size,geometry['paper'] if geometry else self._paper_size(),
                         options['margins_mm'],mode=self.scale_var.get(),percent=options['scale_percent'],
                         source_dpi=options['source_dpi'],tiles=options['tiles'],hardware=geometry['hardware'] if geometry else (0,0,0,0))

    def redraw_preview(self):
        self._redraw_job=None
        if not self.winfo_exists() or self.viewer.display_image is None:return
        self.preview.delete('all');self.preview_photos=[]
        try:
            options=self._print_options();plan=self._plan(options)
        except (ValueError,tk.TclError) as exc:
            self.summary.set(str(exc));self.print_button.configure(state='disabled');return
        self.print_button.configure(state='normal')
        cw,ch=max(1,self.preview.winfo_width()),max(1,self.preview.winfo_height())
        gap=16;pw,ph=plan.paper
        scale=max(.01,min((cw-40-gap*(plan.columns-1))/(pw*plan.columns),(ch-48-gap*(plan.rows-1))/(ph*plan.rows)))
        width,height=pw*scale,ph*scale
        ox=(cw-width*plan.columns-gap*(plan.columns-1))/2;oy=(ch-height*plan.rows-gap*(plan.rows-1))/2
        image=self.viewer.display_image.convert('RGBA')
        for tile in plan.tiles:
            x,y=ox+tile.column*(width+gap),oy+tile.row*(height+gap)
            self.preview.create_rectangle(x,y,x+width,y+height,fill='white',outline='#bacbdf',tags='paper')
            l,t,r,b=plan.margins
            self.preview.create_rectangle(x+l*scale,y+t*scale,x+width-r*scale,y+height-b*scale,outline='#b5bfcb',dash=(3,3))
            if tile.source:
                dx,dy,ex,ey=tile.destination
                bitmap=tile_bitmap(image,tile,(max(1,round((ex-dx)*scale)),max(1,round((ey-dy)*scale))))
                photo=ImageTk.PhotoImage(bitmap,master=self);self.preview_photos.append(photo);self.preview_photo=photo
                self.preview.create_image(x+dx*scale,y+dy*scale,image=photo,anchor='nw')
            self.preview.create_text(x+7,y+7,text=str(tile.number),anchor='nw',fill='#1769aa',font=('Segoe UI',10,'bold'))
        for col in range(1,plan.columns):
            x=ox+col*width+(col-.5)*gap
            self.preview.create_line(x,oy-5,x,oy+height*plan.rows+(plan.rows-1)*gap+5,fill='#ffd060',dash=(6,4),width=2,tags='split_line')
        for row in range(1,plan.rows):
            y=oy+row*height+(row-.5)*gap
            self.preview.create_line(ox-5,y,ox+width*plan.columns+(plan.columns-1)*gap+5,y,fill='#ffd060',dash=(6,4),width=2,tags='split_line')
        status=f'용지 {plan.paper[0]:.1f} × {plan.paper[1]:.1f} mm · {len(plan.tiles)}장 × {options["copies"]}부 = 총 {len(plan.tiles)*options["copies"]}장 · 이미지 {plan.image_mm[0]:.1f} × {plan.image_mm[1]:.1f} mm'
        key=(self.printer_var.get(),self.paper_var.get(),self.orientation_var.get())
        if not self._geometry_cache.get(key):status+='\n프린터 인쇄 영역 확인 전 예상 미리보기'
        if plan.clipped:status+='\n⚠ 이미지 일부가 잘립니다. 전체 용지에 맞춤 또는 더 작은 배율을 선택하세요.'
        self.summary.set(status)

    def do_print(self):
        try:options=self._print_options();plan=self._plan(options)
        except (ValueError,tk.TclError) as exc:messagebox.showerror('인쇄 설정',str(exc),parent=self);return
        if not self.printer_var.get().strip():messagebox.showwarning('인쇄','프린터를 선택하세요.',parent=self);return
        if plan.clipped and not messagebox.askyesno('인쇄 영역 초과','이미지 일부가 잘립니다. 미리보기대로 출력할까요?',parent=self):return
        output=None
        if self.print_to_file_var.get():
            suffix='.pdf' if 'pdf' in self.printer_var.get().lower() else '.prn'
            output=filedialog.asksaveasfilename(parent=self,title='인쇄 파일 저장',defaultextension=suffix,filetypes=[('Printer output','*'+suffix)])
            if not output:return
        if self.save_defaults_var.get():
            self.viewer.settings.update(print_printer=self.printer_var.get(),print_paper=self.paper_var.get(),
                print_orientation=self.orientation_var.get(),print_scale_mode=self.scale_var.get(),print_copies=options['copies'],
                print_percent=options['scale_percent'],print_source_dpi=options['source_dpi'],print_tiles=options['tiles'],
                print_margins={k:float(v.get()) for k,v in self.margins_vars.items()})
            self.core.save_settings(self.viewer.settings)
        physical=(self.viewer.display_image.width/options['source_dpi']*25.4,self.viewer.display_image.height/options['source_dpi']*25.4)
        if self.viewer._print_with_options(self.orientation_var.get(),self.paper_var.get(),self.scale_var.get(),
                printer_name=self.printer_var.get(),output_path=output,parent=self,physical_size=physical,**options):self.destroy()

    def destroy(self):
        for job in (getattr(self,'_redraw_job',None),getattr(self,'_poll_job',None)):
            if job:
                try:self.after_cancel(job)
                except tk.TclError:pass
        super().destroy()
