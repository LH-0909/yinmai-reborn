from pathlib import Path
from PIL import Image,ImageDraw
P=Path(__file__).resolve().parents[1];A=P/'frontend/public/assets/museum';R=P/'references/20261021'
# Clean, text-free black/gold surface and border sampled from the supplied art.
im=Image.open(R/'04-detail.png').convert('RGBA')
f=im.crop((1117,75,1651,383));d=ImageDraw.Draw(f);d.rectangle((12,12,f.width-13,f.height-13),fill=(0,0,0,0));f.save(A/'panel-frame.png')
im.crop((1160,124,1280,137)).save(A/'surface-texture.png')
im=Image.open(R/'01-home.png').convert('RGBA')
im.crop((1269,222,1648,313)).save(A/'home-quote-art.png')
# Explicit per-component fill texture for red buttons, avoiding baked text.
im.crop((994,501,1014,519)).save(A/'red-texture.png')
print('Refined clean panel surfaces.')
