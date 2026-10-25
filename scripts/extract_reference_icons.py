from pathlib import Path
from PIL import Image
import json,hashlib
P=Path(__file__).resolve().parents[1];A=P/'frontend/public/assets/museum';R=P/'references/20261021'
pages={'home':(1,[167,223,276,329,382,436,490]),'generate':(2,[167,221,276,330,383,436,490]),'catalog':(3,[167,213,263,312,362,413,464]),'detail':(4,[167,221,276,329,383,436,489]),'culture':(5,[167,222,276,330,383,436,490]),'customize':(6,[166,214,266,318,371,423,473,523]),'experience':(7,[167,223,276,330,383,436,490]),'account':(8,[166,215,267,319,371,423,475,526])}
for name,(n,centres) in pages.items():
    im=Image.open(next(R.glob(f'{n:02d}-*.png')))
    for i,y in enumerate(centres):im.crop((30,y-10,51,y+11)).save(A/f'nav-{name}-{i}.png')
im=Image.open(R/'01-home.png')
im.crop((1498,18,1535,56)).save(A/'tool-bell.png');im.crop((1551,18,1588,56)).save(A/'tool-moon.png')
catalog=json.loads((P/'docs/ui-assets-20261021.json').read_text(encoding='utf-8'))
catalog['final_asset_sha256']={f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in A.glob('*.png')}
catalog['icon_provenance']='Sidebar and topbar icon artwork extracted from user reference images; live controls retain accessible names and event handlers.'
(P/'docs/ui-assets-20261021.json').write_text(json.dumps(catalog,ensure_ascii=False,indent=2),encoding='utf-8')
print('Reference icon assets extracted.')
