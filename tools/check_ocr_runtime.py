"""Real Windows OCR from a local bitmap; catches StorageFile path denial."""
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from PIL import Image,ImageDraw,ImageFont
from croweyes_ocr import recognize
im=Image.new('RGB',(1000,180),'white')
ImageDraw.Draw(im).text((30,40),'CROWEYES PHOTO 2026',font=ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf',60),fill='black')
text=recognize(im)
assert 'CROWEYES' in text.upper() and '2026' in text,text
print('PASS: Windows OCR recognizes actual text from managed memory stream:',text)
