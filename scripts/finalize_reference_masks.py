"""Remove baked editable controls from the supplied background illustrations."""
from pathlib import Path
from PIL import Image,ImageDraw
P=Path(__file__).resolve().parents[1];A=P/'frontend/public/assets/museum';R=P/'references/20261021'
def crop(page,name,box,holes=()):
    out=Image.open(R/page).convert('RGBA').crop(box);d=ImageDraw.Draw(out)
    for x0,y0,x1,y1 in holes:d.rectangle((x0-box[0],y0-box[1],x1-box[0]-1,y1-box[1]-1),fill=(0,0,0,0))
    out.save(A/(name+'.png'))
crop('04-detail.png','detail-title',(292,75,614,148))
crop('04-detail.png','detail-scene',(170,0,1113,701),[(236,18,859,61),(238,73,672,269),(232,270,405,671),(639,644,955,699)])
crop('06-customize.png','customize-scene',(170,0,1672,592),[(1161,139,1656,486),(582,62,1656,118),(267,175,479,511),(950,175,1128,438),(689,546,1079,587),(1183,16,1658,61)])
crop('06-customize.png','customize-main-art',(476,123,1133,553),[(950,175,1128,438)])
crop('08-account.png','account-hero',(170,0,1672,247),[(1180,16,1658,62),(217,78,364,225),(392,104,785,216)])
for kind,count in [('catalog',10),('account',8)]:
    for i in range(count):
        f=A/f'{kind}-{i}.png';im=Image.open(f).convert('RGBA');d=ImageDraw.Draw(im)
        size=37 if kind=='catalog' else 39;d.rectangle((im.width-size,0,im.width,36 if kind=='catalog' else 40),fill=(8,11,9,255))
        if kind=='catalog':
            # The crop includes baked dynasty tags and a sliver of the title.
            # Native text below must be the only editable title/tag layer.
            d.rectangle((0,im.height-25,im.width,im.height),fill=(7,10,8,255))
        im.save(f)
