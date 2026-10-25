"""Extract supplied artwork at measured coordinates; never a screenshot-only UI."""
from pathlib import Path
import hashlib
import json
import argparse
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser();parser.add_argument('--source-dir',type=Path)
args=parser.parse_args()
SOURCE=args.source_dir or (Path('E:/LH1/图像') if Path('E:/LH1/图像').is_dir() else ROOT/'references/20261021')
OUT=ROOT/'frontend/public/assets/museum'
OUT.mkdir(parents=True,exist_ok=True)
REF=ROOT/'references/20261021';REF.mkdir(parents=True,exist_ok=True)
pages={}
names=['home','generate','catalog','detail','culture','customize','experience','account']
for number,name in enumerate(names,1):
    candidates=list(SOURCE.glob(f'*-{number}.png')) or list(SOURCE.glob(f'{number:02d}-*.png'))
    if not candidates:raise FileNotFoundError(f'Missing reference {number} in {SOURCE}')
    path=candidates[0]
    pages[name]=Image.open(path).convert('RGB')
    (REF/f'{number:02d}-{name}.png').write_bytes(path.read_bytes())
assets=[]
def crop(name,page,box,holes=()):
    im=pages[page].crop(box).convert('RGBA')
    if holes:
        from PIL import ImageDraw
        mask=Image.new('L',im.size,255);d=ImageDraw.Draw(mask)
        for x0,y0,x1,y1 in holes:d.rectangle((x0-box[0],y0-box[1],x1-box[0]-1,y1-box[1]-1),fill=0)
        im.putalpha(mask)
    im.save(OUT/(name+'.png'))
    assets.append({'name':name,'source':page,'box':list(box),'size':list(im.size),
        'purpose':'supplied artwork / texture; live UI rendered as components',
        'sha256':hashlib.sha256((OUT/(name+'.png')).read_bytes()).hexdigest()})
def frame(name,page,box,slice_size=14):
    im=pages[page].crop(box).convert('RGBA')
    from PIL import ImageDraw
    mask=Image.new('L',im.size,255);ImageDraw.Draw(mask).rectangle((slice_size,slice_size,im.width-slice_size-1,im.height-slice_size-1),fill=0)
    im.putalpha(mask);im.save(OUT/(name+'.png'))
    assets.append({'name':name,'source':page,'box':list(box),'size':list(im.size),'purpose':'border-only nine-slice, centre transparent'})

crop('brand','home',(0,0,170,138))
crop('sidebar-scenery','home',(0,508,170,709))
crop('sidebar-bottom','home',(0,838,170,941))
crop('sidebar-texture','home',(9,400,21,480))
crop('avatar','home',(1608,18,1648,57))
frame('nav-active','home',(8,145,164,192),9)
frame('panel-frame','home',(196,397,1243,557),14)
frame('button-frame','home',(974,483,1216,541),14)
frame('small-button','catalog',(467,638,613,673),10)
crop('field-texture','home',(850,429,1150,452))
crop('surface-texture','generate',(843,111,934,135))
crop('backdrop-texture','home',(1260,560,1642,569))

crop('home-hero','home',(170,0,1255,394),[(1185,16,1255,61)])
crop('home-quote-art','home',(1269,200,1648,313))
crop('home-database-art','home',(201,632,535,742))
crop('home-culture-art','home',(922,634,1278,744))
crop('home-experience-art','home',(1300,634,1647,718))
for i,box in enumerate([(587,644,646,707),(655,644,715,707),(725,644,784,707),(798,644,861,707)]):crop(f'home-style-{i}','home',box)
for i,(x0,x1) in enumerate([(245,384),(405,544),(563,702),(719,858),(877,1014),(1032,1174),(1189,1330),(1349,1497)]):
    crop(f'featured-{i}','home',(x0,797,x1,883))

crop('generate-mountains','generate',(170,0,1672,69),[(1180,15,1655,62)])
crop('generate-view','generate',(646,136,1217,741))
for i,box in enumerate([(1239,139,1431,354),(1446,139,1639,354),(1239,428,1431,646),(1446,428,1639,646)]):crop(f'scheme-{i}','generate',box)
for i,box in enumerate([(240,391,289,438),(316,391,364,438),(397,391,447,438),(476,391,525,438),(551,391,600,438)]):crop(f'style-{i}','generate',box)
for i,box in enumerate([(240,579,284,622),(321,579,365,622),(404,579,447,622),(479,579,524,622),(558,579,601,622)]):crop(f'shape-{i}','generate',box)
for i,box in enumerate([(233,689,291,726),(315,689,372,726),(394,689,451,726),(473,689,531,726),(554,689,612,726)]):crop(f'material-{i}','generate',box)
for i,(x0,x1) in enumerate([(245,274),(301,332),(355,385),(410,441),(463,493),(515,546),(571,601)]):crop(f'knob-{i}','generate',(x0,786,x1,817))
for i,x in enumerate([679,781,883,985,1087,1189,1291,1393]):crop(f'history-{i}','generate',(x,797,x+71,864))

crop('catalog-hero','catalog',(170,0,1672,245),[(1182,15,1655,62)])
catalog_boxes=[]
for row,(top,bottom) in enumerate([(403,561),(695,850)]):
    for col,(left,right) in enumerate([(463,620),(636,790),(810,964),(981,1136),(1157,1311)]):
        box=(left,top,right,bottom);catalog_boxes.append(box);crop(f'catalog-{row*5+col}','catalog',box)
crop('catalog-feature','catalog',(1335,292,1639,458))
crop('detail-scene','detail',(170,0,1113,701),[(170,0,640,65)])
crop('detail-main-art','detail',(461,67,1112,656))
for i,(top,bottom) in enumerate([(278,359),(379,460),(480,561),(582,664)]):crop(f'detail-side-{i}','detail',(244,top,393,bottom))
for i,(left,right) in enumerate([(264,449),(469,652),(674,856),(877,1061)]):crop(f'detail-close-{i}','detail',(left,758,right,877))
crop('detail-rubbing','detail',(1143,474,1272,606))
crop('detail-stone','detail',(1138,695,1303,773))
for i,(left,right) in enumerate([(1146,1237),(1250,1344),(1358,1450),(1466,1559)]):crop(f'detail-3d-{i}','detail',(left,832,right,900))

crop('culture-hero','culture',(170,0,1672,199),[(1201,16,1657,62)])
for i,(left,right) in enumerate([(191,295),(300,404),(410,515),(520,625),(632,738),(744,851),(858,964),(970,1075),(1082,1186)]):
    crop(f'era-{i}','culture',(left,252,right,351))
crop('culture-map','culture',(1236,250,1537,477))
crop('culture-graph','culture',(190,521,1220,774))
crop('culture-tree','culture',(1243,525,1644,731))
for i,(left,right) in enumerate([(201,245),(261,307),(321,366),(382,427),(442,487),(502,549),(563,609),(624,669),(684,730)]):crop(f'evolution-{i}','culture',(left,829,right,880))
for i,(left,right) in enumerate([(818,888),(894,965),(970,1044),(1049,1123),(1128,1203)]):crop(f'book-{i}','culture',(left,819,right,883))
for i,(top,bottom) in enumerate([(783,840),(844,892),(895,937)]):crop(f'event-{i}','culture',(1324,top,1459,bottom))

crop('customize-scene','customize',(170,0,1672,592),[(1161,139,1656,486),(582,62,1656,118)])
crop('customize-before','customize',(277,227,472,481))
crop('customize-main-art','customize',(476,123,1133,553))
crop('customize-impression','customize',(1181,184,1399,419))
for i,(left,right) in enumerate([(1432,1487),(1511,1566),(1591,1646)]):
    crop(f'ink-{i}','customize',(left,218,right,275));crop(f'ink-{i+3}','customize',(left,311,right,368))
crop('customize-depth','customize',(482,642,688,784))
for i,(left,right) in enumerate([(750,801),(809,858),(869,918),(929,978),(989,1035)]):
    crop(f'edge-{i}','customize',(left,683,right,730));crop(f'edge-{i+5}','customize',(left,742,right,789))
for i,(left,right) in enumerate([(1060,1124),(1133,1198),(1209,1271),(1285,1346)]):
    crop(f'stone-{i}','customize',(left,684,right,747));crop(f'stone-{i+4}','customize',(left,782,right,845))
for i,(left,right) in enumerate([(1387,1440),(1467,1522),(1543,1598)]):crop(f'gold-{i}','customize',(left,649,right,702))
for i,x in enumerate([1387,1438,1489,1540,1591]):crop(f'base-{i}','customize',(x,831,x+45,879))

crop('experience-hero','experience',(170,0,1672,515),[(1185,16,1657,62)])
for i,(left,right) in enumerate([(215,777),(795,1064),(1083,1350),(1371,1645)]):crop(f'experience-{i}','experience',(left,574,right,749))
# The wide AR illustration and distinct digital cabinet are separate crops.
crop('experience-ar','experience',(215,574,492,749))
crop('experience-cabinet','experience',(513,574,777,749))

crop('account-hero','account',(170,0,1672,247),[(1180,16,1658,62)])
crop('account-avatar','account',(222,81,361,219))
for i,(left,right) in enumerate([(213,450),(464,702),(715,952),(966,1208)]):
    crop(f'account-{i}','account',(left,501,right,645));crop(f'account-{i+4}','account',(left,749,right,894))
for i,(top,bottom) in enumerate([(420,455),(467,502),(514,549),(560,595)]):crop(f'recent-{i}','account',(1264,top,1303,bottom))
for i,(left,right) in enumerate([(1266,1380),(1393,1508),(1521,1636)]):crop(f'published-{i}','account',(left,678,right,732))

(ROOT/'docs/ui-assets-20261021.json').write_text(json.dumps({'reference_size':[1672,941],'assets':assets,
    'method':'Exact crops of supplied artwork, brand, illustration thumbnails and transparent-centre border strips; no full-page raster is used as the interface.'},ensure_ascii=False,indent=2),encoding='utf-8')
print('Extracted',len(assets),'measured source assets from 8 references.')
