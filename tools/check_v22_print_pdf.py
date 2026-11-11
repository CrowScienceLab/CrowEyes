"""Exercise the production GDI pipeline without sending paper to a printer."""
import importlib.util,json,re,shutil,subprocess,sys,uuid
from pathlib import Path
from PIL import Image,ImageDraw

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
spec=importlib.util.spec_from_file_location('v22_pdf',ROOT/'CrowEyes_Image_Viewer_2.0.py')
core=importlib.util.module_from_spec(spec);sys.modules[spec.name]=core;spec.loader.exec_module(core)
assert 'Microsoft Print to PDF' in core.enumerate_printer_names()
renderer=shutil.which('pdftoppm')
assert renderer,'Poppler pdftoppm is required for visual output verification'
folder=ROOT/'tmp/v22-print-pdf'/uuid.uuid4().hex;folder.mkdir(parents=True)
results=[]
for pages in (2,4):
    image=Image.new('RGB',(840,594 if pages==2 else 1188),'white');draw=ImageDraw.Draw(image)
    colors=[(255,0,0),(0,128,0),(0,0,255),(255,255,0)][:pages]
    for n,color in enumerate(colors):
        x=(n%2)*420;y=(n//2)*594
        draw.rectangle((x,y,x+419,y+593),fill=color)
    pdf=folder/f'poster-{pages}.pdf'
    assert core.print_image_windows(lambda w,h:image.copy(),0,'CrowEyes 2.2 split verification',
        printer_name='Microsoft Print to PDF',output_path=str(pdf),tiles=pages,margins_mm=(12,15,12,15))
    assert len(re.findall(rb'/Type\s*/Page\b',pdf.read_bytes()))==pages
    prefix=folder/f'page-{pages}'
    subprocess.run([renderer,'-r','50','-png',str(pdf),str(prefix)],check=True,capture_output=True,timeout=60)
    samples=[]
    for n,color in enumerate(colors,1):
        with Image.open(folder/f'page-{pages}-{n}.png') as rendered:
            pixel=rendered.convert('RGB').getpixel((rendered.width//2,rendered.height//2))
            assert all(abs(a-b)<=2 for a,b in zip(pixel,color)),(n,pixel,color)
            assert rendered.convert('RGB').getpixel((5,5))==(255,255,255)
            samples.append(pixel)
    results.append(dict(pages=pages,path=str(pdf),center_rgb=samples,white_margin=True))
report=ROOT/'docs/maintenance/2026-11-11-v2.2-review/print-pdf.json'
report.write_text(json.dumps(dict(status='PASS',results=results),indent=2),encoding='utf-8')
print('PASS: real GDI -> Microsoft Print to PDF -> Poppler; 2/4 pages, quadrant order, white margins')
