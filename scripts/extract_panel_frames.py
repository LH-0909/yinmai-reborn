"""Border-only source ornaments; every control and label remains native HTML."""
from pathlib import Path
import re,json,hashlib
from PIL import Image,ImageDraw
P=Path(__file__).resolve().parents[1];A=P/'frontend/public/assets/museum';R=P/'references/20261021';mapping={}
names=['Home','Generate','Catalog','Detail','Culture','Customize','Experience','Account']
for n,name in enumerate(names,1):
    page=name.lower();im=Image.open(next(R.glob(f'{n:02d}-*.png'))).convert('RGBA')
    source=(P/f'frontend/src/museum/{name}.vue').read_text(encoding='utf-8')
    boxes=[]
    for tag in re.findall(r'<Rect\b[^>]*>',source):
        if re.search(r'\bplain\b',tag):continue
        coords=[re.search(rf':{k}="(\d+)"',tag) for k in ['x','y','w','h']]
        if all(coords):boxes.append(tuple(int(m.group(1)) for m in coords))
    if page=='home':boxes.extend((x,569,w,180) for x,w in zip([196,554,922,1300],[344,354,362,351]))
    if page=='experience':boxes.extend((212+i*287,515,273,288) for i in range(5))
    for i,(x,y,w,h) in enumerate(boxes):
        f=im.crop((x,y,x+w,y+h));d=ImageDraw.Draw(f)
        d.rectangle((7,7,w-8,h-8),fill=(0,0,0,0))
        # Preserve individual corners without sampling internal UI labels.
        original=im.crop((x,y,x+w,y+h))
        for l,t in [(0,0),(w-14,0),(0,h-14),(w-14,h-14)]:f.paste(original.crop((l,t,l+14,t+14)),(l,t))
        asset=f'frame-{page}-{i}';f.save(A/(asset+'.png'));mapping[f'{page}:{x}:{y}:{w}:{h}']=asset
(P/'frontend/src/museum/frames.json').write_text(json.dumps(mapping,ensure_ascii=False,indent=2),encoding='utf-8')
catalog=json.loads((P/'docs/ui-assets-20261021.json').read_text(encoding='utf-8'));catalog['panel_frame_mapping']=mapping
catalog['final_asset_sha256']={f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in A.glob('*.png')}
(P/'docs/ui-assets-20261021.json').write_text(json.dumps(catalog,ensure_ascii=False,indent=2),encoding='utf-8')
print('Exact border ornament frames:',len(mapping))
