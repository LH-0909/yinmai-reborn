from pathlib import Path
from PIL import Image
P=Path(__file__).resolve().parents[1];A=P/'frontend/public/assets/museum'
im=Image.open(P/'references/20261021/02-generate.png')
for i,(l,r) in enumerate([(675,770),(782,881),(894,996),(1007,1110),(1121,1223),(1234,1335),(1346,1448),(1458,1561)]):im.crop((l,793,r,862)).save(A/f'history-{i}.png')
im=Image.open(P/'references/20261021/05-culture.png')
for i,(t,b) in enumerate([(778,816),(817,855),(856,894),(895,937)]):im.crop((1324,t,1459,b)).save(A/f'event-{i}.png')
im=Image.open(P/'references/20261021/03-catalog.png');im.crop((0,488,170,670)).save(A/'sidebar-catalog.png')
print('History crops and fourth event prepared.')
