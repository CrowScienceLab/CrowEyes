"""Original CrowEyes 2.1 command artwork: optical 32px SVG, no boxed glyphs.

Small silhouettes have one clear meaning. Color families group navigation,
editing and file operations. Assets are rasterized locally, never downloaded.
"""
import io
from functools import lru_cache
from PIL import Image
import resvg_py


def path(d, fill='none', stroke='ink', width=2):
    return f'<path d="{d}" fill="{fill}" stroke="{stroke}" stroke-width="{width}" stroke-linecap="round" stroke-linejoin="round"/>'


def rect(x,y,w,h,fill,rx=2,stroke='none'):
    return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{fill}" stroke="{stroke}" stroke-width="1.5"/>'


def circle(x,y,r,fill,stroke='none',width=2):
    return f'<circle cx="{x}" cy="{y}" r="{r}" fill="{fill}" stroke="{stroke}" stroke-width="{width}"/>'


def artwork(name):
    blue='url(#blue)';gold='url(#gold)';green='url(#green)';purple='url(#purple)';red='url(#red)'
    # Silhouettes use the full optical square; individual buttons have no baked-in frame.
    if name in ('previous','next','up'):
        rotate={'previous':0,'next':180,'up':90}[name]
        return f'<g transform="rotate({rotate} 16 16)">'+path('M17 6 6 16l11 10v-6h10v-8H17Z',blue,'#1976b9',1)+path('m17 8-8 8',stroke='#c3edff',width=1.4)+'</g>'
    if name in ('undo','redo'):
        flip='translate(32 0) scale(-1 1)' if name=='redo' else ''
        return f'<g transform="{flip}">'+path('M12 5 3 13l9 7v-5h6c6 0 9 4 8 11 6-11 0-17-8-17h-6Z',gold,'#c58113',.8)+path('M13 11h6q7 0 9 6',stroke='#ffe7a5',width=1)+'</g>'
    if name=='folder':
        return path('M3 9q0-3 3-3h7l3 3h10q3 0 3 3v13q0 2-3 2H5q-2 0-2-2Z','#d6951b','none')+path('M3 12h26l-3 14H5Z',gold,'#c88d21',1)+path('M6 14h19',stroke='#fff1b7',width=1)
    if name in ('open_image','location'):
        return rect(4,4,24,24,'#f4faff',3,'#58a8d4')+rect(6,6,20,19,blue,2)+circle(21,11,3,'#ffe085')+path('m6 23 7-9 5 6 3-3 5 6Z','#4ac3b2','none')+path('m6 24 7-9 5 6',stroke='#b9fff0',width=1)
    if name in ('zoom_in','zoom_out','search','actual'):
        lens=circle(13,13,9,'#d8f5ff','#438eaf',1.5)+circle(13,13,6.7,'#92d8f4')+path('m20 20 8 8',stroke='#596d88',width=5)+path('m23 22 5 5',stroke='#bacbe0',width=1.4)
        if name in ('zoom_in','zoom_out'):lens+=path('M8 13h10',stroke='#17698b',width=2)
        if name=='zoom_in':lens+=path('M13 8v10',stroke='#17698b',width=2)
        if name=='actual':lens+=path('M11 10l2-1v9m-3 0h6',stroke='#17698b',width=2)
        return lens
    if name in ('fit','fullscreen','resize'):
        border=path('M3 11V5h7m12 0h7v6M3 21v6h7m12 0h7v-6',stroke='#70b8e2',width=2.4)
        if name=='resize':return rect(5,9,15,17,'#4b96cd',2)+rect(12,5,15,14,'#a4e5fb',2,'#368ac5')+path('m14 17 10-10m-6 0h6v6',stroke='#166d9d',width=1.8)
        return border+rect(9,10,14,12,blue,2)
    if name in ('rotate_left','rotate_right','refresh','restore'):
        flip='translate(32 0) scale(-1 1)' if name=='rotate_left' else ''
        color=green if name in ('refresh','restore') else red
        return f'<g transform="{flip}">'+path('M25 12a10 10 0 1 0 0 9',stroke=color,width=4)+path('m20 12 8 2-1-9Z',color,'none')+(rect(11,11,9,10,'#d2f5ec',1) if name=='restore' else '')+'</g>'
    if name in ('flip_h','flip_v'):
        turn='rotate(90 16 16)' if name=='flip_v' else ''
        return f'<g transform="{turn}">'+path('M14 5 3 26h11Z',blue,'#2789bd',.7)+path('M19 5 29 26H19Z','#b9e6fa','#2789bd',.7)+path('M16.5 3v26',stroke='ink',width=1)+'</g>'
    if name in ('annotation','highlight','ocr_region'):
        if name=='ocr_region':
            return path('M4 11V4h7m10 0h7v7M4 21v7h7m10 0h7v-7',stroke='#f39b36',width=2)+path('M10 10h12m-6 0v12m-3 0h6',stroke='ink',width=2.2)+path('m24 23 4-4 2 2-4 4-3 1Z',gold,'#c47c20',.7)
        if name=='highlight':return path('m9 18 11-14 8 6-11 14Z',gold,'#d6a526',1)+path('m9 18-4 9 11-3Z','#fff6ba','#b58b19',1)+path('M4 29h23',stroke='#ffdf3c',width=3)+path('m13 15 9-11',stroke='#fff5ba',width=1.6)
        return path('m7 21 14-17 7 6-15 17-8 2Z',purple,'#7951c1',1)+path('m7 21 6 6-8 2Z','#ffe7bd','#b8a58a',.6)+path('m12 20 12-14',stroke='#e5d4ff',width=1.2)+path('m5 26 2 2-3 1Z','#514b60','none')
    if name in ('mosaic','view'):
        return ''.join(rect(4+c*8,4+r*8,6.5,6.5,(['#fa89b4','#d95991','#a956a1'][c] if name=='mosaic' else ['#5bade4','#83d5ec','#75bdca'][r]),1.4) for r in range(3) for c in range(3))
    if name in ('compare','panel'):
        return rect(3,5,26,23,'#cdd8f4',3,'#768fc9')+rect(5,7,10,19,blue,1)+rect(17,7,10,19,purple,1)+path('M16 4v25',stroke='ink',width=1)
    if name=='copy':return rect(10,4,18,21,'#a7dfef',3,'#4b9bbf')+rect(4,10,18,19,blue,3,'#2786b7')+path('M8 15h10M8 19h7',stroke='#daffff',width=1.4)
    if name=='save':return path('M5 4h18l5 5v19H5Z',green,'#28997b',1)+rect(10,4,12,9,'#c9fff0',1)+rect(10,19,13,9,'#edfff9',1)+rect(18,5,3,6,'#47a78f',0)
    if name=='print':return rect(8,3,16,10,'#f8fbff',1,'#a8b4cc')+rect(3,11,26,13,purple,3,'#7055ae')+rect(8,20,16,10,'#f7faff',1,'#9dabc1')+path('M11 24h10M11 27h7',stroke='#8d9cb2',width=1)+circle(25,15,1,'#9affd2')
    if name in ('adjust','brightness','contrast','settings'):
        if name=='brightness':return circle(16,16,7,gold)+''.join(path(f'M{x} {y} {xx} {yy}',stroke='#eab847',width=2) for x,y,xx,yy in [(16,2,16,5),(16,27,16,30),(2,16,5,16),(27,16,30,16),(6,6,8,8),(24,24,26,26),(6,26,8,24),(24,8,26,6)])
        return ''.join(path(f'M5 {y}h22',stroke='#97afc7',width=2)+circle(x,y,3.4,[blue,gold,purple][i],'#ecf6ff',.7) for i,(y,x) in enumerate([(8,12),(16,22),(24,10)]))
    if name in ('play','slideshow'):return path('M9 4q-2-1-2 2v21q0 2 2 1l19-11q2-1 0-2Z',green,'#229779',1)+path('M10 8v15',stroke='#b6ffdf',width=1.5)
    if name=='pause':return rect(6,5,7,23,gold,2)+rect(20,5,7,23,gold,2)
    if name=='info':return circle(16,16,13,blue,'#438ebc',1)+circle(16,9,1.7,'#f0fcff')+path('M14 14h3v10m-3 0h6',stroke='#f0fcff',width=2)
    if name=='ai_generated':return path('M16 2 20 11l10 5-10 4-4 10-4-10-10-4 10-5Z',purple,'#aa83dc',.7)+path('m23 3 1 3 3 1-3 1-1 3-1-3-3-1 3-1Z','#e5c5ff','none')+path('M16 8v5l-4 3',stroke='#f6eaff',width=1.5)
    if name=='shield':return circle(16,16,13,'#fff3f5','#f15c72',2.5)+'<text x="16" y="21" text-anchor="middle" font-family="Segoe UI" font-weight="700" font-size="14" fill="#ce2c4c">19</text>'
    if name=='index':return path('M5 8h22v17q-11 7-22 0Z',blue,'#3083af',1)+'<ellipse cx="16" cy="8" rx="11" ry="4.5" fill="#b7ecff" stroke="#489ecc" stroke-width="1.2"/>'+path('M5 15q11 7 22 0M5 22q11 7 22 0',stroke='#c0f4ff',width=1.3)
    if name in ('hidden','visible'):
        result=path('M2 16Q16 0 30 16Q16 32 2 16Z','#c8e8f9','#65b3da',1)+circle(16,16,5,blue)+circle(17,14,1.4,'#f4ffff')
        return result+(path('M5 28 28 4',stroke='#e16c7f',width=2.8) if name=='hidden' else '')
    if name in ('sort','ascending','descending'):
        return path('M8 4v24m-4-5 4 5 4-5',stroke='#5eaada',width=2)+path('M17 7h12M17 15h9M17 23h5',stroke='ink',width=2)
    if name=='close':return path('m8 8 16 16M24 8 8 24',stroke='ink',width=2.4)
    if name=='computer':return rect(3,4,26,19,blue,3,'#5f9bbb')+rect(5,6,22,14,'#bbecfb',1)+path('M16 24v4m-6 0h12',stroke='ink',width=2)
    if name=='delete':return rect(8,9,17,21,'#f0b0b6',2,'#d76879')+path('M5 8h23M12 4h9M13 13v11m6-11v11',stroke='#b74861',width=2)
    if name=='more':return ''.join(circle(x,16,2.4,'ink') for x in (6,16,26))
    return None


@lru_cache(maxsize=256)
def render_icon(name, size, dark):
    drawing=artwork(name)
    if drawing is None:return None
    ink='#d6e5f5' if dark else '#405773'
    gradients={'blue':('#8de1ff','#278bd1'),'gold':('#ffe79a','#f4ad2e'),
               'green':('#90efd2','#21af8b'),'purple':('#d6b7ff','#9463d6'),'red':('#ffa7b4','#e25976')}
    defs=''.join(f'<linearGradient id="{k}" x2=".3" y2="1"><stop stop-color="{a}"/><stop offset="1" stop-color="{b}"/></linearGradient>' for k,(a,b) in gradients.items())
    svg=f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 32 32"><defs>{defs}</defs>{drawing.replace("ink",ink)}</svg>'
    return Image.open(io.BytesIO(resvg_py.svg_to_bytes(svg_string=svg))).convert('RGBA')
