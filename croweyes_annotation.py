"""Annotation documents store vector operations, not a bitmap per undo step."""
import math
from PIL import Image, ImageDraw, ImageFont


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
