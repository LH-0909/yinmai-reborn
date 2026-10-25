"""Bounded public-catalogue harvest. Stage records, never silently publish them."""
from pathlib import Path
from html.parser import HTMLParser
from urllib.request import Request,build_opener,HTTPRedirectHandler
from urllib.parse import urljoin,urlsplit,parse_qs
from datetime import datetime,timezone
from threading import Lock
from concurrent.futures import ThreadPoolExecutor,as_completed
from PIL import Image
import re,json,hashlib,time,io,sys,argparse
sys.stdout.reconfigure(encoding='utf-8')
PROJECT=Path(__file__).resolve().parents[1]
STAGE=PROJECT/'runtime/heritage-harvest';STAGE.mkdir(parents=True,exist_ok=True)
CACHE=STAGE/'html';CACHE.mkdir(exist_ok=True)
ASSETS=STAGE/'images';ASSETS.mkdir(exist_ok=True)
class Element:
    def __init__(self,tag='',attrs=None):self.tag=tag;self.attrs=dict(attrs or []);self.children=[]
    def text(self,br='\n'):return ''.join(c if isinstance(c,str) else (br if c.tag=='br' else c.text(br)) for c in self.children)
    def all(self,test):
        found=[]
        for child in self.children:
            if isinstance(child,Element):
                if test(child):found.append(child)
                found.extend(child.all(test))
        return found
    def has(self,cls):return cls in self.attrs.get('class','').split()
class DOM(HTMLParser):
    VOID={'area','base','br','col','embed','hr','img','input','link','meta','param','source','track','wbr'}
    def __init__(self,text):super().__init__(convert_charrefs=True);self.root=Element('root');self.stack=[self.root];self.feed(text)
    def handle_starttag(self,tag,attrs):
        node=Element(tag,attrs);self.stack[-1].children.append(node)
        if tag not in self.VOID:self.stack.append(node)
    def handle_startendtag(self,tag,attrs):self.stack[-1].children.append(Element(tag,attrs))
    def handle_endtag(self,tag):
        for i in range(len(self.stack)-1,0,-1):
            if self.stack[i].tag==tag:self.stack=self.stack[:i];break
    def handle_data(self,data):self.stack[-1].children.append(data)
def clean(text):return re.sub(r'\s+',' ',text).strip()
def digest(raw):return hashlib.sha256(raw).hexdigest()
def ident(prefix,*parts):return prefix+'-'+digest('\x1f'.join(parts).encode())[:28]
class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs):return None
lock=Lock();last_request=0.
def get(url,limit=3_000_000,ajax=False):
    global last_request
    host=urlsplit(url).hostname
    assert url.startswith('https://') and host in {'www.dpm.org.cn','img.dpm.org.cn'}
    with lock:
        wait=max(0,.45-(time.monotonic()-last_request))
        if wait:time.sleep(wait)
        last_request=time.monotonic()
    headers={'User-Agent':'Mozilla/5.0 (Yinmai local catalogue research)','Referer':'https://www.dpm.org.cn/collection/seals.html'}
    if ajax:headers['X-Requested-With']='XMLHttpRequest'
    with build_opener(NoRedirect).open(Request(url,headers=headers),timeout=20) as r:
        raw=r.read(limit+1);assert r.status==200 and r.url==url and len(raw)<=limit
    return raw
def catalogue(page):
    url=f'https://www.dpm.org.cn/searchs/seals.html?category_id=95&pagesize=12&dbg=0&type=seals&p={page}'
    path=CACHE/f'index-{page}.html'
    if path.exists():raw=path.read_bytes()
    else:raw=get(url,ajax=True);path.write_bytes(raw)
    dom=DOM(raw.decode('utf-8')).root;rows=[]
    for li in dom.all(lambda e:e.has('li') and not e.has('li-th')):
        spans=li.all(lambda e:e.tag=='div' and e.has('span'))
        links=li.all(lambda e:e.tag=='a' and re.fullmatch(r'/collection/seal/\d+\.html',e.attrs.get('href','')))
        if not links or len(spans)<2:continue
        a=links[0];rows.append(dict(url=urljoin('https://www.dpm.org.cn',a.attrs['href']),title=clean(a.text()),period=clean(spans[1].text()),maker=clean(spans[2].text()) if len(spans)>2 else '',index_page=page,index_url=f'https://www.dpm.org.cn/collection/seals.html?p={page}',index_transport_url=url,index_sha256=digest(raw)))
    maxes=dom.all(lambda e:e.attrs.get('id')=='jumpPage');maximum=int(maxes[0].attrs['data-max']) if maxes else 1
    assert rows and maximum<=40
    return rows,maximum
def asset(image,id,suffix=''):
    src=image.attrs.get('data-img') or image.attrs.get('src','');assert re.match(r'https://img\.dpm\.org\.cn/Uploads/',src)
    previous=OLD_ASSETS.get(src)
    if previous and previous['display_url']=='/assets/seal-previews/'+id+suffix+'.webp' and (ASSETS/(id+suffix+'.webp')).exists() and digest((ASSETS/(id+suffix+'.webp')).read_bytes())==previous['preview_sha256']:
        return {k:previous[k] for k in ('image_url','display_url','caption','original_sha256','preview_sha256','width','height')}
    raw=get(src,8_000_000);im=Image.open(io.BytesIO(raw));assert 0<im.width*im.height<=25_000_000;im.load();im=im.convert('RGB');im.thumbnail((1024,1024))
    file=id+suffix+'.webp';im.save(ASSETS/file,'WEBP',quality=92)
    return dict(image_url=src,display_url='/assets/seal-previews/'+file,caption=image.attrs.get('alt',''),original_sha256=digest(raw),preview_sha256=digest((ASSETS/file).read_bytes()),width=im.width,height=im.height)
def object_record(row,images):
    try:
        page=row['url'].split('/')[-1];path=CACHE/page
        if path.exists():raw=path.read_bytes()
        else:raw=get(row['url']);path.write_bytes(raw)
        dom=DOM(raw.decode('utf-8')).root
        headings=dom.all(lambda e:e.tag=='div' and e.has('s-title'))
        assert len(headings)==1,'no_unique_object_title'
        title=clean(headings[0].text()).strip('【】 ')
        assert title==row['title'],'catalogue_heading_mismatch'
        assert not re.search(r'『\d+』',title),'missing_glyph_in_title'
        assert title.count('“')==title.count('”'),'unbalanced_quotation_in_official_title'
        hao=dom.all(lambda e:e.has('hao'));assert len(hao)==1,'no_unique_accession_container'
        # Do not invent a number for missing or grouped collection objects.
        number_text=next((c for c in hao[0].children if isinstance(c,str) and c.strip()),'').strip()
        assert re.fullmatch(r'(?:故|新)\d{8}(?:[-－]\d+(?:/\d+)?)?',number_text),'ambiguous_or_missing_accession'
        content=dom.all(lambda e:e.attrs.get('id')=='content_with_keyword');assert len(content)==1,'no_object_body'
        body=clean(content[0].text());assert len(body)>10,'no_descriptive_text'
        candidates=dom.all(lambda e:e.tag=='img' and e.attrs.get('data-img'))
        quoted=re.findall('“([^”]+)”',title)
        photo=next((i for i in candidates if clean(i.attrs.get('alt',''))==title),None)
        basis='exact_official_title'
        if photo is None and len(quoted)==1 and quoted[0] in body:
            photo=next((i for i in candidates if re.findall('“([^”]+)”',i.attrs.get('alt',''))==quoted and not re.search('钤本|印面|背面|局部|边款',i.attrs.get('alt',''))),None)
            basis='official_object_gallery_same_complete_named_inscription'
        assert photo is not None,'photo_caption_mismatch'
        for material_name in ['青玉','白玉','碧玉','墨玉','寿山石','青田石']:
            if material_name in photo.attrs.get('alt',''):assert material_name in title,'conflicting_material_in_caption'
        impression=next((i for i in candidates if clean(i.attrs.get('alt','')) in {title+'钤本',clean(photo.attrs.get('alt',''))+'钤本'}),None)
        transcription=quoted[0] if len(quoted)==1 and all('\u3400'<=c<='\u9fff' for c in quoted[0]) and quoted[0] in body else ''
        stamp=ident('node','seal_object','dpm:'+number_text)
        # Museum names and objects are distinct from authors of the web article.
        first=clean(content[0].text(br='\u2028').split('\u2028',1)[0])
        period_index=row['period'] or ''
        intro_after_name=re.split('[，,]',first,maxsplit=1)[-1].split('。',1)[0]
        era_match=re.match(r'清(?:早期|中期|晚期|康熙|雍正|乾隆|嘉庆|道光|咸丰|同治|光绪|宣统|顺治)?|明(?:早期|中期|晚期|洪武|永乐|宣德|弘治|正德|嘉靖|万历|天启|崇祯)?|东汉|西汉|东晋|西晋|北宋|南宋|南北朝|十六国|近现代|民国|战国|三国|五代|西夏|秦|汉|晋|隋|唐|宋|辽|金|元',intro_after_name[:75])
        period_body=era_match[0] if era_match else ''
        if period_index and period_index in re.split('[，,]',intro_after_name,maxsplit=1)[0]:period_body=period_index if not period_body or not period_body.startswith(period_index) else period_body
        period_conflict=bool(period_index and period_body and not (period_index.startswith(period_body) or period_body.startswith(period_index)))
        period='目录与正文分期不同，待核对' if period_conflict else (period_body or period_index)
        prefix=title.split('“',1)[0]
        material=next((m for m in ['寿山石','青田石','昌化石','田黄石','滑石','花乳石','玛瑙','象牙','犀角','金镶玉','银镀金','铜鎏金','鎏金铜','银鎏金','铜镀金','檀香木','栴檀木','白玉','青玉','碧玉','墨玉','金','银','铜','木','玉','石','瓷'] if m in first and m in prefix),'')
        dims='；'.join(re.findall(r'(?:印面|通高|纽高|钮高|长宽|面宽|面长|直径|厚|面|高|长|宽|横|纵|重)(?:边长|为|约|各|：|\s){0,3}\d[^，。；]{0,25}?(?:厘米|cm|毫米|克)(?:见方)?',first))
        known_scripts=[s for s in ['汉文篆书','满文篆书','满文','篆书','小篆','九叠篆','八思巴文','西夏文','蒙古文','鸟虫书','隶书'] if s in first]
        if '汉文篆书' in known_scripts:known_scripts=[s for s in known_scripts if s!='篆书']
        record=dict(node_id=stamp,label=transcription or title,page_url=row['url'],status='available',official_title=title,accession_number=number_text,museum='故宫博物院',source_id='dpm',document_id=ident('doc',row['url']),page_sha256=digest(raw),fetched_at=datetime.fromtimestamp(path.stat().st_mtime,timezone.utc).isoformat(),period=period,period_index=period_index,period_body=period_body,period_conflict=period_conflict,material=material or '官方条目未明确提取',dimensions=dims or '官方条目未明确提取',script='、'.join(known_scripts) or '未提取',transcription=transcription,transcription_scope='官方题名所引中文印文；未做OCR，不代替其他文字转写' if transcription else '未提取：保留官方题名，不自动补写印文',maker=row['maker'],field_provenance={'period_and_maker':{k:row[k] for k in ['index_url','index_transport_url','index_sha256','index_page','period','maker']},'description':{'url':row['url'],'sha256':digest(raw)}},source_excerpt=first[:180],source_excerpt_is_quote=True,source_excerpt_truncated=len(first)>180,image_match_basis=basis,caption_note='' if basis=='exact_official_title' else '官方题名与图片说明名称不同；同一藏品页画廊的完整印文一致，保留两处原文。',usage='Local source-linked study preview only; no image-training or public-commercial license asserted')
        if images:
            record.update(asset(photo,stamp))
            if impression:record['impression']=asset(impression,stamp,'-impression')
        else:
            record.update(image_url=photo.attrs['data-img'],caption=photo.attrs.get('alt',''),has_impression=bool(impression))
        return dict(status='accepted',record=record)
    except Exception as e:return dict(status='quarantined',url=row['url'],title=row['title'],reason=str(e)[:180] or type(e).__name__)

OLD_ASSETS={}
if (STAGE/'records-stage.json').exists():
    for result in json.loads((STAGE/'records-stage.json').read_text(encoding='utf-8'))['results']:
        if result['status']=='accepted':
            r=result['record']
            if 'preview_sha256' in r:OLD_ASSETS[r['image_url']]=r
            if 'impression' in r:OLD_ASSETS[r['impression']['image_url']]=r['impression']
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--probe',action='store_true');parser.add_argument('--limit',type=int,default=90);parser.add_argument('--images',action='store_true');args=parser.parse_args()
    first,maximum=catalogue(1);rows=list(first)
    if not args.probe:
        for page in range(2,maximum+1):
            found,_=catalogue(page);rows.extend(found)
            if page%5==0:print('Index',page,'/',maximum,'records',len(rows),flush=True)
    unique=list({r['url']:r for r in rows}.values());(STAGE/'catalogue-index.json').write_text(json.dumps(unique,ensure_ascii=False,indent=2),encoding='utf-8')
    # Spread the bounded sample through the actual catalogue; avoid a Qing-only corpus.
    selected=unique[:5] if args.probe else [unique[i] for i in sorted(set(round(i*(len(unique)-1)/(min(args.limit,len(unique))-1)) for i in range(min(args.limit,len(unique)))))]
    results=[]
    with ThreadPoolExecutor(max_workers=3) as pool:
        pending={pool.submit(object_record,row,args.images):row for row in selected}
        for future in as_completed(pending):
            result=future.result();results.append(result)
            if len(results)%10==0 or args.probe:print(len(results),'checked;',sum(r['status']=='accepted' for r in results),'accepted;',result.get('record',{}).get('official_title') or result.get('reason'),flush=True)
    (STAGE/('probe.json' if args.probe else 'records-stage.json')).write_text(json.dumps({'selection_limit':args.limit,'indexed':len(unique),'checked':len(results),'accepted':sum(r['status']=='accepted' for r in results),'results':results},ensure_ascii=False,indent=2),encoding='utf-8')
    print('Finished staging:',sum(r['status']=='accepted' for r in results),'accepted of',len(results),'checked.',flush=True)
if __name__=='__main__':main()
