"""Annotation documents store vector operations, not a bitmap per undo step."""
import math
import tkinter as tk
from tkinter import ttk, simpledialog, colorchooser
from PIL import Image, ImageDraw, ImageFont, ImageTk


def render(image, operations):
    result=image.convert('RGBA').copy()
    draw=ImageDraw.Draw(result)
    for item in operations:
        kind,box,color,text=item
        x0,y0,x1,y1=box
        if kind=='모자이크':
            crop=result.crop(box)
            crop=crop.resize((max(1,crop.width//12),max(1,crop.height//12)),Image.Resampling.BILINEAR).resize(crop.size,Image.Resampling.NEAREST)
            result.paste(crop,box[:2])
        elif kind=='형광펜':
            overlay=Image.new('RGBA',result.size)
            ImageDraw.Draw(overlay).rectangle(box,fill=color+'66')
            result=Image.alpha_composite(result,overlay)
            draw=ImageDraw.Draw(result)
        elif kind=='텍스트':
            try:
                font=ImageFont.truetype('C:/Windows/Fonts/malgun.ttf',max(16,result.width//60))
            except OSError:
                font=ImageFont.load_default()
            draw.text((x0,y0),text,fill=color,font=font)
        elif kind=='화살표':
            draw.line((x0,y0,x1,y1),fill=color,width=max(3,result.width//400))
            angle=math.atan2(y1-y0,x1-x0)
            length=max(12,result.width//50)
            points=[(x1,y1)]+[(x1-length*math.cos(angle+a),y1-length*math.sin(angle+a)) for a in (-0.45,0.45)]
            draw.polygon(points,fill=color)
        else:
            draw.rectangle(box,outline=color,width=max(3,result.width//400))
    return result


def editor(viewer,image):
    image=image.copy()
    win,frame=viewer._window('주석·모자이크', '1000x760')
    operations,redo=[],[]
    mode=tk.StringVar(value='화살표')
    color=['#ff4444']
    row=ttk.Frame(frame)
    row.pack(fill='x')
    ttk.Combobox(row,textvariable=mode,values=['화살표','텍스트','사각형','형광펜','모자이크'],state='readonly').pack(side='left')
    def choose():
        selected=colorchooser.askcolor(color[0],parent=win)[1]
        if selected:
            color[0]=selected
    ttk.Button(row,text='색상',command=choose).pack(side='left')
    canvas=tk.Canvas(frame,bg='#202428')
    canvas.pack(fill='both',expand=True)
    state={'scale':1,'left':0,'top':0,'start':None,'ghost':None}
    def redraw(e=None):
        composed=render(image,operations)
        state['scale']=min(max(1,canvas.winfo_width())/image.width,max(1,canvas.winfo_height())/image.height)
        shown=composed.resize((max(1,int(image.width*state['scale'])),max(1,int(image.height*state['scale']))),Image.Resampling.LANCZOS)
        state['left']=(canvas.winfo_width()-shown.width)/2
        state['top']=(canvas.winfo_height()-shown.height)/2
        canvas.photo=ImageTk.PhotoImage(shown)
        canvas.delete('all')
        canvas.create_image(state['left'],state['top'],image=canvas.photo,anchor='nw')
    def point(e):
        return (max(0,min(image.width,int((e.x-state['left'])/state['scale']))),max(0,min(image.height,int((e.y-state['top'])/state['scale']))))
    def press(e):
        state['start']=point(e)
        state['ghost']=canvas.create_rectangle(e.x,e.y,e.x,e.y,outline=color[0],dash=(4,3))
        state['screen']=(e.x,e.y)
    def move(e):
        if state['ghost']:
            canvas.coords(state['ghost'],*state['screen'],e.x,e.y)
    def release(e):
        if state['start'] is None:
            return
        a,b=state['start'],point(e)
        state['start']=None
        text=simpledialog.askstring('텍스트','내용:',parent=win) if mode.get()=='텍스트' else ''
        box=(a[0],a[1],b[0],b[1]) if mode.get()=='화살표' else (min(a[0],b[0]),min(a[1],b[1]),max(a[0],b[0]),max(a[1],b[1]))
        if mode.get()=='텍스트' and not text:
            redraw()
            return
        if mode.get()!='텍스트' and (box[0]==box[2] or box[1]==box[3]):
            redraw()
            return
        operations.append((mode.get(),box,color[0],text))
        redo.clear()
        redraw()
    def undo():
        if operations:
            redo.append(operations.pop())
            redraw()
        return 'break'
    def again():
        if redo:
            operations.append(redo.pop())
            redraw()
        return 'break'
    canvas.bind('<Configure>',redraw)
    canvas.bind('<Button-1>',press)
    canvas.bind('<B1-Motion>',move)
    canvas.bind('<ButtonRelease-1>',release)
    win.bind('<Control-z>',lambda e:undo())
    win.bind('<Control-y>',lambda e:again())
    ttk.Button(row,text='실행 취소',command=undo).pack(side='left')
    ttk.Button(row,text='재실행',command=again).pack(side='left')
    ttk.Button(row,text='원본 복원',command=lambda:(operations.clear(),redo.clear(),redraw())).pack(side='left')
    ttk.Button(row,text='다른 이름으로 저장',command=lambda:viewer.quality_dialog(render(image,operations))).pack(side='right')
    return win
