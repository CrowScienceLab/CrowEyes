"""Bounded 2/4 image comparison with shared normalized pan and zoom."""
import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk


def show(viewer,images,labels):
    win,frame=viewer._window('이미지 비교 · 휠 확대 / 드래그 이동', '1100x760')
    panels=[]
    state={'zoom':1.0,'x':0.5,'y':0.5,'start':None}
    for i,(image,label) in enumerate(zip(images,labels)):
        image=image.copy()
        image.thumbnail((2048,2048),Image.Resampling.LANCZOS)
        cell=ttk.Frame(frame)
        cell.grid(row=i//2,column=i%2,sticky='nsew')
        frame.rowconfigure(i//2,weight=1)
        frame.columnconfigure(i%2,weight=1)
        ttk.Label(cell,text=label).pack()
        canvas=tk.Canvas(cell,bg='#202428',width=400,height=280)
        canvas.pack(fill='both',expand=True)
        panels.append((canvas,image))
    def redraw(e=None):
        for canvas,image in panels:
            w,h=max(1,canvas.winfo_width()),max(1,canvas.winfo_height())
            fit=min(w/image.width,h/image.height)
            # Crop the source before scaling; zoom cannot allocate giant bitmaps.
            scale=fit*state['zoom']
            crop_w,crop_h=min(image.width,w/scale),min(image.height,h/scale)
            left=max(0,min(image.width-crop_w,state['x']*image.width-crop_w/2))
            top=max(0,min(image.height-crop_h,state['y']*image.height-crop_h/2))
            crop=image.crop((int(left),int(top),max(int(left)+1,int(left+crop_w)),max(int(top)+1,int(top+crop_h))))
            shown=crop.resize((max(1,int(crop.width*scale)),max(1,int(crop.height*scale))),Image.Resampling.LANCZOS)
            canvas.photo=ImageTk.PhotoImage(shown)
            canvas.delete('all')
            canvas.create_image(w/2,h/2,image=canvas.photo)
    def wheel(e):
        state['zoom']=max(1,min(16,state['zoom']*(1.2 if e.delta>0 else 1/1.2)))
        redraw()
    def press(e):
        state['start']=(e.x,e.y)
    def move(e):
        if state['start']:
            x,y=state['start']
            state['x']=max(0,min(1,state['x']-(e.x-x)/max(1,e.widget.winfo_width())/state['zoom']))
            state['y']=max(0,min(1,state['y']-(e.y-y)/max(1,e.widget.winfo_height())/state['zoom']))
            state['start']=(e.x,e.y)
            redraw()
    for canvas,image in panels:
        canvas.bind('<Configure>',redraw)
        canvas.bind('<MouseWheel>',wheel)
        canvas.bind('<Button-1>',press)
        canvas.bind('<B1-Motion>',move)
        canvas.bind('<ButtonRelease-1>',lambda e:state.update(start=None))
    return win
