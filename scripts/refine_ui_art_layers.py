from pathlib import Path
from PIL import Image,ImageDraw
P=Path(__file__).resolve().parents[1];A=P/'frontend/public/assets/museum';R=P/'references/20261021'
def crop(page,name,box,holes=()):
    out=Image.open(R/page).convert('RGBA').crop(box);d=ImageDraw.Draw(out)
    for x0,y0,x1,y1 in holes:d.rectangle((x0-box[0],y0-box[1],x1-box[0]-1,y1-box[1]-1),fill=(0,0,0,0))
    out.save(A/(name+'.png'))
crop('07-experience.png','experience-hero',(170,0,1672,515))
crop('07-experience.png','experience-floor',(170,803,1672,941),[(398,820,680,917),(775,819,1081,888),(1152,820,1440,917)])
crop('05-culture.png','culture-hero',(170,0,1672,199),[(1201,16,1657,62),(1180,131,1656,198)])
crop('04-detail.png','detail-main-art',(461,67,1112,656),[(461,202,673,268)])
# Extra source reference motifs for the layout picker, distinct from font styles.
for i,(left,right) in enumerate([(198,250),(264,316),(330,381),(396,447)]):crop('06-customize.png',f'layout-{i}',(left,690,right,740))
for i,(left,right) in enumerate([(213,450),(464,702),(715,952),(966,1208)]):
    crop('08-account.png',f'account-{i+4}',(left,749,right,854),[(right-39,749,right,789)])
# Pure ornament strips for the history frame; no sample stamps are substituted.
# Record final asset hashes after all deterministic extraction passes.
import hashlib,json
catalog=json.loads((P/'docs/ui-assets-20261021.json').read_text(encoding='utf-8'))
catalog['final_asset_sha256']={f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in A.glob('*.png')}
catalog['refinements']='Source crops for clean panel borders, static brush title, floor, layout and account images; baked action glyphs removed under native controls.'
(P/'docs/ui-assets-20261021.json').write_text(json.dumps(catalog,ensure_ascii=False,indent=2),encoding='utf-8')
print('Art layer refinements complete.')
