"""Physical poster layout shared by preview and printer; all geometry is in mm."""
from dataclasses import dataclass
import math

PAPERS = {'A4': (210.0, 297.0), 'A3': (297.0, 420.0), 'A2': (420.0, 594.0), 'Letter': (215.9, 279.4)}


@dataclass(frozen=True)
class Tile:
    number: int
    row: int
    column: int
    source: tuple | None  # normalized source coordinates, common across all tiles
    destination: tuple | None  # physical sheet coordinates in mm


@dataclass(frozen=True)
class PrintPlan:
    paper: tuple
    margins: tuple
    columns: int
    rows: int
    image_mm: tuple
    clipped: bool
    tiles: tuple


def finite(value, label, minimum, maximum):
    try:
        result=float(value)
    except (ValueError, TypeError, OverflowError):
        raise ValueError(f'{label}: 올바른 숫자를 입력하세요.') from None
    if not math.isfinite(result) or not minimum<=result<=maximum:
        raise ValueError(f'{label}: {minimum:g}~{maximum:g} 범위로 입력하세요.')
    return result


def preview_dpi(viewer):
    """Keep physical size when the viewer uses a reduced-resolution source."""
    image=getattr(viewer,'pil_image',None)
    metadata=getattr(image,'info',{}).get('dpi',(96,96))
    try:
        dpi=float(metadata[0] if isinstance(metadata,(tuple,list)) else metadata)
        if not math.isfinite(dpi) or not 1<=dpi<=2400:dpi=96
    except (TypeError,ValueError,IndexError):dpi=96
    scale=float(getattr(viewer,'source_render_scale',1) or 1)
    return max(.01,min(2400,dpi*scale))


def make_plan(image_size, paper=(210,297), margins=(10,10,10,10), *, mode='fit',
              percent=100, source_dpi=96, tiles=1, physical_size=None, hardware=(0,0,0,0)):
    """Margins: left/top/right/bottom. Two-sheet direction maximizes usable image area.

    100% means image pixels/source DPI; fit means fit across ALL selected sheets.
    Clipping is explicit, rather than silently scaling an oversized actual image.
    """
    iw,ih=image_size
    if min(iw,ih)<=0:raise ValueError('이미지 크기가 올바르지 않습니다.')
    pw,ph=map(float,paper)
    if not all(math.isfinite(x) and x>0 for x in (pw,ph)):raise ValueError('용지 크기가 올바르지 않습니다.')
    if mode not in ('fit','actual','percent'):raise ValueError('인쇄 크기 옵션이 올바르지 않습니다.')
    if tiles not in (1,2,4):raise ValueError('분할 출력은 1장, 2장, 4장만 가능합니다.')
    pct=finite(percent,'배율',1,1000)
    dpi=finite(source_dpi,'인쇄 DPI',.01,2400)
    user=tuple(finite(x,'여백(mm)',0,200) for x in margins)
    if len(user)!=4 or len(hardware)!=4:raise ValueError('상하좌우 여백이 필요합니다.')
    left,top,right,bottom=effective=tuple(max(u,float(h)) for u,h in zip(user,hardware))
    aw,ah=pw-left-right,ph-top-bottom
    if min(aw,ah)<1:raise ValueError('여백이 너무 큽니다. 인쇄 가능 영역을 1mm 이상 남겨 주세요.')
    grids=[(1,1)] if tiles==1 else ([(2,2)] if tiles==4 else [(2,1),(1,2)])
    columns,rows=max(grids,key=lambda g:min(aw*g[0]/iw,ah*g[1]/ih))
    width,height=aw*columns,ah*rows
    if mode=='fit':
        factor=min(width/iw,height/ih);dw,dh=iw*factor,ih*factor
    else:
        base=physical_size or (iw/dpi*25.4,ih/dpi*25.4)
        scale=1 if mode=='actual' else pct/100
        dw,dh=base[0]*scale,base[1]*scale
        if not all(math.isfinite(x) and x>0 for x in (dw,dh)):raise ValueError('원본 인쇄 크기가 올바르지 않습니다.')
    ox,oy=(width-dw)/2,(height-dh)/2
    result=[]
    for row in range(rows):
        for column in range(columns):
            x,y=column*aw,row*ah
            x0,y0=max(x,ox),max(y,oy)
            x1,y1=min(x+aw,ox+dw),min(y+ah,oy+dh)
            if x1<=x0 or y1<=y0:src=dest=None
            else:
                src=((x0-ox)/dw,(y0-oy)/dh,(x1-ox)/dw,(y1-oy)/dh)
                dest=(left+x0-x,top+y0-y,left+x1-x,top+y1-y)
            result.append(Tile(len(result)+1,row,column,src,dest))
    return PrintPlan((pw,ph),effective,columns,rows,(dw,dh),dw>width+.01 or dh>height+.01,tuple(result))


def device_rect(tile, dpi, offset=(0,0)):
    if tile.destination is None:return None
    return tuple(round(value/25.4*dpi[i%2])-offset[i%2] for i,value in enumerate(tile.destination))


def tile_bitmap(image, tile, target=None):
    from PIL import Image
    if tile.source is None:return None
    box=tuple(v*image.size[i%2] for i,v in enumerate(tile.source))
    if target is None:target=(max(1,round(box[2]-box[0])),max(1,round(box[3]-box[1])))
    return image.transform(target,Image.Transform.EXTENT,box,resample=Image.Resampling.BICUBIC)
