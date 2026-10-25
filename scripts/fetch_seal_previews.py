"""Bounded display previews for the already selected fourteen public seal pages.
No crawling, authentication, historical inference, or training labels.
"""
from pathlib import Path
from urllib.request import Request,build_opener,HTTPRedirectHandler
from urllib.parse import urljoin,urlparse
from html.parser import HTMLParser
from html import unescape
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime,timezone
from PIL import Image
import hashlib,io,json,re
P=Path(__file__).resolve().parents[1]
seed=json.loads((P/'data/knowledge-graph/verified-public-metadata.json').read_text(encoding='utf-8'))
target=P/'frontend/public/assets/seal-previews';target.mkdir(parents=True,exist_ok=True)
ALLOWED_PAGE_URLS=frozenset(['https://yingaoku.cn/seal/1', 'https://yingaoku.cn/seal/105', 'https://yingaoku.cn/seal/140', 'https://yingaoku.cn/seal/160', 'https://yingaoku.cn/seal/161', 'https://yingaoku.cn/seal/176', 'https://yingaoku.cn/seal/2', 'https://yingaoku.cn/seal/216', 'https://yingaoku.cn/seal/293', 'https://yingaoku.cn/seal/3', 'https://yingaoku.cn/seal/319', 'https://yingaoku.cn/seal/49', 'https://yingaoku.cn/seal/86', 'https://yingaoku.cn/seal/91'])
class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs):return None
def get(url,limit):
    with build_opener(NoRedirect).open(Request(url,headers={'User-Agent':'YinmaiLocalResearch/0.1 (selected display previews; not training)'}),timeout=18) as r:
        raw=r.read(limit+1)
        if r.status!=200 or r.url!=url or len(raw)>limit:raise ValueError('unexpected response')
        return raw
class Images(HTMLParser):
    def __init__(self):super().__init__();self.images=[]
    def handle_starttag(self,tag,attrs):
        if tag=='img':self.images.append(dict(attrs))
def one(node):
    url=node['attributes']['url'];result={'node_id':node['id'],'label':node['label'],'page_url':url,'status':'unavailable'}
    try:
        raw=get(url,2_000_000);html=raw.decode('utf-8');p=Images();p.feed(html)
        title=unescape(re.sub('<[^>]+>','',re.search(r'<h1 class="seal-title">(.*?)</h1>',html,re.S)[1])).strip()
        if title!=node['label']:raise ValueError('title mismatch')
        candidates=[x for x in p.images if x.get('alt','').strip()==title and x.get('src')]
        if not candidates:raise ValueError('no matching image')
        image_url=urljoin(url,candidates[0]['src']);parsed=urlparse(image_url)
        if parsed.scheme!='https' or parsed.hostname!='yingaoku.cn' or not parsed.path.startswith('/images/'):raise ValueError('image host/path outside bounded source')
        imgraw=get(image_url,5_000_000);img=Image.open(io.BytesIO(imgraw))
        if img.width*img.height>20_000_000:raise ValueError('image too large')
        img.load()
        file=node['id']+'.webp'
        preview=img.convert('RGB');preview.thumbnail((960,960));preview.save(target/file,'WEBP',quality=92)
        result.update(status='available',image_url=image_url,display_url='/assets/seal-previews/'+file,original_sha256=hashlib.sha256(imgraw).hexdigest(),preview_sha256=hashlib.sha256((target/file).read_bytes()).hexdigest(),page_sha256=hashlib.sha256(raw).hexdigest(),width=preview.width,height=preview.height,fetched_at=datetime.now(timezone.utc).isoformat(),usage='Local learning/research display preview; not a training input or redistributable license grant',source_notice='https://yingaoku.cn/seal/1')
    except Exception as exc:result['error_type']=type(exc).__name__
    print(result['label'],result['status'],flush=True)
    return result
nodes=[n for n in seed['nodes'] if n['kind']=='seal_draft' and n.get('attributes',{}).get('url') in ALLOWED_PAGE_URLS]
with ThreadPoolExecutor(max_workers=3) as pool:rows=list(pool.map(one,nodes))
manifest={'version':1,'purpose':'source-matched local display previews, not AI or OCR results','items':rows}
(target/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
registry_path=P/'frontend/src/graph/seal-previews.json'
registry_path.write_text(json.dumps({r['node_id']:r for r in rows if r['status']=='available'},ensure_ascii=False,indent=2),encoding='utf-8')
(P/'evidence/seal-universe-20261023').mkdir(parents=True,exist_ok=True)
(P/'evidence/seal-universe-20261023/preview-fetch.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
print('Available:',sum(r['status']=='available' for r in rows),'of',len(rows))
