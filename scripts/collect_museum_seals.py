"""Three explicitly selected Palace Museum object records, not a general crawler.

Read official catalogue text + catalogue-linked photos/impressions. Preserve
captions, watermarks, hashes and identity; do not infer a mesh or train a model.
"""
from pathlib import Path
from urllib.request import Request, build_opener, HTTPRedirectHandler
from urllib.parse import urlsplit
from html.parser import HTMLParser
from datetime import datetime, timezone
from PIL import Image
import hashlib, json, io, re, sys

ROOT=Path(__file__).resolve().parents[1]
sys.stdout.reconfigure(encoding='utf-8')
SELECTION=[
    dict(page='233558',label='皇帝尊亲之宝',title='白玉盘龙纽“皇帝尊亲之宝”',accession='故00166815',period='清早期',material='白玉',script='汉文篆书、满文篆书',size='印面6.8厘米见方，通高6.1厘米，纽高4.3厘米'),
    dict(page='233652',label='乾清宫宝',title='青玉交龙纽“乾清宫宝”',accession='故00166295',period='清乾隆',material='青玉',script='汉文篆书',size='印面11.6厘米见方，通高8.5厘米，纽高4.4厘米'),
    dict(page='233579',label='敕命之宝',title='碧玉交龙纽“敕命之宝”',accession='故00166806',period='清早期',material='碧玉',script='汉文篆书、满文篆书',size='印面11.3厘米见方，通高9厘米，纽高5.5厘米'),
]
def ident(prefix,*parts):return prefix+'-'+hashlib.sha256('\x1f'.join(parts).encode()).hexdigest()[:28]
def digest(raw):return hashlib.sha256(raw).hexdigest()
class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs):return None
def fetch(url,limit):
    parsed=urlsplit(url)
    assert parsed.scheme=='https' and parsed.hostname in {'www.dpm.org.cn','img.dpm.org.cn'}
    with build_opener(NoRedirect).open(Request(url,headers={'User-Agent':'YinmaiLocalResearch/0.1 (three selected official collection records)'}),timeout=25) as response:
        raw=response.read(limit+1)
        assert response.status==200 and response.url==url and len(raw)<=limit
        return raw
class Images(HTMLParser):
    def __init__(self):super().__init__();self.images=[]
    def handle_starttag(self,tag,attrs):
        if tag=='img':self.images.append(dict(attrs))

def collect():
    if (ROOT/'data/heritage/records.json').exists():
        raise RuntimeError('Published catalogue exists. Use the staged harvest/publish pipeline; this legacy three-object collector must not overwrite it.')
    output=ROOT/'frontend/public/assets/seal-previews';output.mkdir(parents=True,exist_ok=True)
    nodes={};edges=[];docs=[];registry={}
    source=dict(id='dpm',title='故宫博物院 · 馆藏玺印',url='https://www.dpm.org.cn/collection/seals.html',priority=5,access_state='official_object_records',note='实际读取3条官方藏品记录及其文物号、照片和钤本。官方记录证明有对应馆藏，不等于系统自行完成真伪鉴定或取得训练授权。')
    def node(label,kind,attrs=None,identity=None):
        id=ident('node',kind,identity or label);nodes[id]=dict(id=id,label=label,kind=kind,attributes=attrs or {});return id
    def edge(subject,predicate,object,document,attrs=None):
        edges.append(dict(id=ident('edge',subject,predicate,object,document),subject=subject,predicate=predicate,object=object,document_id=document,status='page_asserted',attributes=attrs or {}))
    institution=node('故宫博物院','resource',{'source_id':'dpm','url':source['url']})
    for chosen in SELECTION:
        url=f"https://www.dpm.org.cn/collection/seal/{chosen['page']}.html"
        raw=fetch(url,3_000_000);html=raw.decode('utf-8');parser=Images();parser.feed(html)
        # Reject changed identity or body fields instead of silently using another object.
        text=re.sub('<[^>]+>',' ',html)
        for required in [chosen['title'],chosen['accession'],chosen['period'],chosen['material']]:
            assert required in text, f'Catalogue field changed: {chosen["page"]}'
        compact=re.sub(r'\s+','',text)
        assert all(number+'厘米' in compact for number in re.findall(r'\d+(?:\.\d+)?',chosen['size']))
        assert all(script in compact for script in chosen['script'].split('、'))
        photo=next(i for i in parser.images if i.get('alt')==chosen['title'] and i.get('src','').startswith('https://img.dpm.org.cn/Uploads/Picture/'))
        impression=next(i for i in parser.images if i.get('alt')==chosen['title']+'钤本' and i.get('src','').startswith('https://img.dpm.org.cn/Uploads/Picture/'))
        stamp=node(chosen['label'],'seal_object',dict(url=url,official_title=chosen['title'],transcription=chosen['label'],museum='故宫博物院',accession_number=chosen['accession'],record_type='museum_object',period=chosen['period'],material=chosen['material'],dimensions=chosen['size'],transcription_scope='中文印文；不代替满文转写'),'dpm:'+chosen['accession'])
        document=ident('doc',url);when=datetime.now(timezone.utc).isoformat()
        docs.append(dict(id=document,source_id='dpm',title=chosen['title']+' · '+chosen['accession'],url=url,summary=f"故宫官方藏品页；文物号{chosen['accession']}。中文印文{chosen['label']}，{chosen['period']}，{chosen['material']}。",sha256=digest(raw),fetched_at=when,method='public_html_metadata_extraction'))
        row=dict(node_id=stamp,label=chosen['label'],page_url=url,status='available',official_title=chosen['title'],accession_number=chosen['accession'],museum='故宫博物院',document_id=document,page_sha256=digest(raw),fetched_at=when,period=chosen['period'],material=chosen['material'],dimensions=chosen['size'],script=chosen['script'],transcription=chosen['label'],transcription_scope='中文印文；不代替满文转写',usage='Local source-linked study preview; no public commercial or model-training license asserted')
        for variant,img in [('photo',photo),('impression',impression)]:
            imgraw=fetch(img['src'],8_000_000);image=Image.open(io.BytesIO(imgraw));assert image.width*image.height<=25_000_000;image.load()
            # Keep the entire photograph including institutional watermark.
            image=image.convert('RGB');image.thumbnail((1024,1024));filename=stamp+('' if variant=='photo' else '-impression')+'.webp';image.save(output/filename,'WEBP',quality=94)
            preview=dict(image_url=img['src'],display_url='/assets/seal-previews/'+filename,caption=img['alt'],original_sha256=digest(imgraw),preview_sha256=digest((output/filename).read_bytes()),width=image.width,height=image.height)
            if variant=='photo':row.update(preview)
            else:row['impression']=preview
        registry[stamp]=row
        for char in dict.fromkeys(chosen['label']):edge(stamp,'contains_character',node(char,'character',{'unicode':'U+'+format(ord(char),'04X')}),document,{'positions':[i+1 for i,c in enumerate(chosen['label']) if c==char],'scope':'Chinese inscription as named by official catalogue; no Manchu transcription'})
        edge(stamp,'has_script',node(chosen['script'],'script'),document)
        edge(stamp,'recorded_in',institution,document,{'accession_number':chosen['accession']})
        print(chosen['accession'],chosen['title'],'photo + impression verified',flush=True)
    seed=dict(version=1,purpose='Three source-backed physical collection objects; no reconstructed artifact or generated image',sources=[source],documents=docs,nodes=list(nodes.values()),edges=edges)
    (ROOT/'data/knowledge-graph/verified-museum-seals.json').write_text(json.dumps(seed,ensure_ascii=False,indent=2),encoding='utf-8')
    (ROOT/'frontend/src/graph/museum-seals.json').write_text(json.dumps(registry,ensure_ascii=False,indent=2),encoding='utf-8')
    (output/'museum-manifest.json').write_text(json.dumps({'purpose':seed['purpose'],'items':list(registry.values())},ensure_ascii=False,indent=2),encoding='utf-8')
    print('Collected exactly three physical collection records; no old graph records or user reviews modified.')

if __name__=='__main__':collect()
