"""Fetch eighteen explicitly selected public pages and extract minimal metadata.

No image downloading, full-site crawl, credentials or hidden service access.
Raw HTML is not redistributed. Hashes describe the actual fetched bytes.
Run BEFORE starting the API to seed a new database; existing reviews survive.
"""
from datetime import datetime, timezone
import hashlib
from html import unescape
import json
from pathlib import Path
import re
from urllib.request import Request,build_opener,HTTPRedirectHandler

ROOT=Path(__file__).resolve().parents[1]
URLS=['https://yin.fudan.edu.cn/','https://yingaoku.cn/seal/1','https://yingaoku.cn/seal/2','https://yingaoku.cn/seal/3','https://fuiframe.art/stamp/home','https://guji.nlc.cn/','https://www.nlc.cn/web/dsb_zx/gtxw/20250520_2645084.shtml']
# Further pages were explicitly linked by the first and third selected entries.
URLS += [f'https://yingaoku.cn/seal/{i}' for i in (49,86,91,161,176,105,140,160,216,293,319)]
class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self,req,fp,code,msg,headers,newurl):return None
def ident(prefix,*parts):return prefix+'-'+hashlib.sha256('\x1f'.join(parts).encode()).hexdigest()[:28]
def plain(s):return unescape(re.sub('<[^>]+>','',s)).strip()
def capture(pattern,s):
    match=re.search(pattern,s,re.S)
    if not match:raise ValueError('Public page structure changed; no seed written')
    return plain(match.group(1))

def main():
    receipts=[];pages=[]
    opener=build_opener(NoRedirect)
    for url in URLS:
        with opener.open(Request(url,headers={'User-Agent':'YinmaiResearch/0.1 (selected public metadata pages; no images)'}),timeout=25) as response:
            raw=response.read(2_000_001)
            if response.status!=200 or len(raw)>2_000_000:raise ValueError('Unexpected response or excessive HTML')
            if response.url!=url:raise ValueError('Redirect requires source review before import')
        pages.append(raw.decode('utf-8',errors='strict'))
        receipts.append({'url':url,'http_status':200,'sha256':hashlib.sha256(raw).hexdigest(),'fetched_at':datetime.now(timezone.utc).isoformat().replace('+00:00','Z'),'bytes':len(raw)})
    sources=[
        {'id':'fudan','title':'复旦大学 · 印藏','url':URLS[0],'priority':1,'access_state':'homepage_only','note':'首页HTTP可达；动态目录在当前浏览器读取超时。尚未导入馆藏条目，保留优先接入位置。'},
        {'id':'yingaoku','title':'篆刻印稿数据库','url':'https://yingaoku.cn/','priority':2,'access_state':'selected_metadata_verified','note':'已读取14条选定详情的文字字段。展示预览另由fetch_seal_previews.py登记，见前端预览凭证；页面记载不等于专家鉴定，未获得训练使用授权。'},
        {'id':'fuiframe','title':'中国篆刻','url':URLS[4],'priority':3,'access_state':'resource_index_only','note':'已核对公开资源首页。条目目录、作者和印谱记录尚未导入，不计入本地图谱馆藏。'},
        {'id':'nlc','title':'国家图书馆 · 古籍智慧化服务','url':URLS[5],'priority':4,'access_state':'official_service_notice','note':'首页为动态应用；已读取国图官方上线介绍，仅建立平台与官方文献关系，未导入古籍全文。'}]
    documents=[];nodes={};edges=[]
    def node(kind,label,**attrs):
        nid=ident('node',kind,label)
        if nid not in nodes:nodes[nid]={'id':nid,'label':label,'kind':kind,'attributes':attrs}
        return nid
    def doc(index,source,title,summary):
        r=receipts[index];did=ident('doc',r['url'])
        documents.append({'id':did,'source_id':source,'title':title,'url':r['url'],'summary':summary,'sha256':r['sha256'],'fetched_at':r['fetched_at'],'method':'public_html_metadata_extraction'})
        return did
    def edge(s,p,o,d,**attrs):edges.append({'id':ident('edge',s,p,o,d),'subject':s,'predicate':p,'object':o,'document_id':d,'status':'page_asserted','attributes':attrs})
    resources={s['id']:node('resource',s['title'],url=s['url'],source_id=s['id']) for s in sources}
    doc(0,'fudan','复旦印谱文献虚拟图书馆 · 首页','仅核对网页标题和资源入口；尚无对象级数据。')
    doc(4,'fuiframe','中国篆刻 · 资源首页','仅登记公开首页；不将网站自报数量作为本地统计。')
    doc(5,'nlc','中华古籍智慧化服务平台 · 首页','动态首页的标题与入口已读取；目录条目尚未采集。')
    for i in [j for j,u in enumerate(URLS) if u.startswith('https://yingaoku.cn/seal/')]:
        html=pages[i]
        title=capture(r'<h1 class="seal-title">(.*?)</h1>',html)
        main=html.split('<div class="seal-info">',1)[1].split('<section class="related-seals">',1)[0]
        script=capture(r'<span class="meta-label">书体</span>\s*<span class="meta-value">(.*?)</span>',main)
        type_=capture(r'<span class="meta-label">类型</span>\s*<span class="meta-value">(.*?)</span>',main)
        collection=capture(r'<div class="source-info">.*?<strong>(.*?)</strong>',html)
        chars=[plain(x) for x in re.findall(r'class="character-tag">(.*?)</a>',main,re.S)]
        if ''.join(chars)!=title or any(len(x)!=1 for x in chars):raise ValueError('Character metadata needs manual review')
        d=doc(i,'yingaoku',title,'字段来自该详情页的印文、书体、类型和来源栏；创作者、年代及馆藏未作推断。')
        seal=node('seal_draft',title,url=URLS[i],transcription=''.join(chars))
        for c in dict.fromkeys(chars):edge(seal,'contains_character',node('character',c),d,positions=[k+1 for k,x in enumerate(chars) if x==c])
        edge(seal,'has_script',node('script',script),d)
        edge(seal,'has_type',node('seal_type',type_),d)
        edge(seal,'cites_collection',node('collection',collection),d)
        edge(seal,'recorded_in',resources['yingaoku'],d)
    if '中华古籍智慧化服务平台' not in pages[6] or '2025' not in pages[6]:raise ValueError('Official notice must be checked')
    d=doc(6,'nlc','“中华古籍智慧化服务平台”上线试运行','国图2025年5月20日公开介绍平台试运行及检索、古籍知识组织等服务；仅登记服务文献。')
    notice=node('document','古籍智慧化服务平台上线介绍',url=URLS[6],publication_date='2025-05-20')
    edge(notice,'describes',resources['nlc'],d)
    result={'schema_version':1,'built_at':datetime.now(timezone.utc).isoformat(),'sources':sources,'documents':documents,'nodes':list(nodes.values()),'edges':edges,
        'boundaries':['Only fourteen selected seal-draft pages, not a complete corpus','No images or training permission imported','No inferred people, periods or museum holdings','Page assertions are not expert historical verification']}
    target=ROOT/'data/knowledge-graph';target.mkdir(parents=True,exist_ok=True)
    (target/'verified-public-metadata.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    evidence=ROOT/'evidence/graph-sources-20261022';evidence.mkdir(parents=True,exist_ok=True)
    (evidence/'fetch-manifest.json').write_text(json.dumps(receipts,ensure_ascii=False,indent=2),encoding='utf-8')
    # Earlier inspection copies belong in the local scratch directory, not in
    # the deliverable. Remove only our exact seven known HTML/text filenames.
    for i in range(7):
        for suffix in ('page.html','text.txt'):
            path=evidence/f'{i:02}-{suffix}'
            if path.exists():path.unlink()
    print(json.dumps({'sources':len(sources),'documents':len(documents),'nodes':len(nodes),'edges':len(edges),'images_downloaded':0}))

if __name__=='__main__':main()
