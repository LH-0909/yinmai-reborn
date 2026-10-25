"""Promote only receipt-checked staged records. Raw HTML stays outside delivery."""
from pathlib import Path
from datetime import datetime,timezone
from collections import Counter
from harvest_official_seals import DOM,clean,ident,digest
import json,re,shutil
P=Path(__file__).resolve().parents[1];STAGE=P/'runtime/heritage-harvest'
def main():
    base=json.loads((P/'frontend/src/graph/museum-seals.json').read_text(encoding='utf-8'))
    # This script is idempotent for a release: the original three core receipts are immutable.
    core_path=P/'data/heritage/core-museum-records.json';core_path.parent.mkdir(parents=True,exist_ok=True)
    if not core_path.exists():core_path.write_text(json.dumps(base,ensure_ascii=False,indent=2),encoding='utf-8')
    base=json.loads(core_path.read_text(encoding='utf-8'))
    for row in base.values():row['source_id']='dpm'
    batch=json.loads((STAGE/'records-stage.json').read_text(encoding='utf-8'))
    incoming=[x['record'] for x in batch['results'] if x['status']=='accepted']+json.loads((STAGE/'cross-records.json').read_text(encoding='utf-8'))
    CROSS_FILES={'nmc:252412':'nmc-emperor','nmc:28017':'nmc-chu','nmc:251978':'nmc-dian','nyw:47':'nyw-emperor','nyw:67':'nyw-lady'}
    records=dict(base)
    for row in incoming:
        if row['node_id'] in records:continue
        page=(STAGE/'cross'/(CROSS_FILES[row['source_id']+':'+row['catalogue_record_id']]+'.html')) if row['source_id']!='dpm' else STAGE/'html'/row['page_url'].split('/')[-1]
        assert digest(page.read_bytes())==row['page_sha256']
        for image in [row]+([row['impression']] if row.get('impression') else []):
            if not image.get('display_url'):continue
            source=STAGE/'images'/image['display_url'].split('/')[-1]
            assert source.is_file() and digest(source.read_bytes())==image['preview_sha256']
            shutil.copyfile(source,P/'frontend/public'/image['display_url'].lstrip('/'))
        records[row['node_id']]=row
    
    sources=[
     dict(id='dpm',title='故宫博物院 · 馆藏玺印',url='https://www.dpm.org.cn/collection/seals.html',priority=5,access_state='official_object_records',note='读取公开目录及选定藏品页，逐件保留文物号、原图、字段出处和不一致项；不是独立真伪鉴定。'),
     dict(id='nmc',title='中国国家博物馆 · 馆藏精品',url='https://www.chnmuseum.cn/zp/zpml/',priority=6,access_state='official_object_records',note='选定官方藏品页。未公开文物号时仅记录官方条目号，绝不将网页编号冒充文物号；图像不可取得时保留缺项。'),
     dict(id='nyw',title='南越王博物院 · 典藏',url='https://www.nywmuseum.org.cn/Collection/',priority=7,access_state='official_object_records',note='选定官方典藏条目及对应照片。条目号不等于文物号；用途及身世按原站记载，不自行定论。'),
    ]
    nodes={};documents={};edges={};bibliography=[]
    def node(label,kind,attrs=None,identity=None):
        id=ident('node',kind,identity or label);nodes.setdefault(id,dict(id=id,label=label,kind=kind,attributes=attrs or {}));return id
    def edge(subject,predicate,object,document,attrs=None):
        id=ident('edge',subject,predicate,object,document);edges[id]=dict(id=id,subject=subject,predicate=predicate,object=object,document_id=document,status='page_asserted',attributes=attrs or {})
    institutions={s['id']:node(s['title'].split(' · ')[0],'resource',{'source_id':s['id'],'url':s['url']}) for s in sources}
    for id,row in records.items():
        if id in base:continue
        documents[row['document_id']]=dict(id=row['document_id'],source_id=row['source_id'],title=row['official_title']+' · '+(row['accession_number'] or '官方条目 '+row['catalogue_record_id']),url=row['page_url'],summary='官方藏品记录。名称、编号及明确字段照录；图像、推测及缺项另行标注。',sha256=row['page_sha256'],fetched_at=row['fetched_at'],method='public_html_metadata_extraction')
        attrs={key:row[key] for key in ['official_title','accession_number','museum','period','material','dimensions','transcription','transcription_scope']}
        attrs.update(url=row['page_url'],record_type='museum_object',source_id=row['source_id'],catalogue_record_id=row.get('catalogue_record_id',''),period_conflict=row.get('period_conflict',False),maker_as_catalogued=row.get('maker',''),source_excerpt=row.get('source_excerpt',''),field_provenance=row.get('field_provenance',{}))
        nodes[id]=dict(id=id,label=row['label'],kind='seal_object',attributes=attrs)
        edge(id,'recorded_in',institutions[row['source_id']],row['document_id'],{'accession_number':row['accession_number'],'catalogue_record_id':row.get('catalogue_record_id','')})
        for char in dict.fromkeys(row['transcription']):
            character=node(char,'character',{'unicode':'U+'+format(ord(char),'04X')})
            edge(id,'contains_character',character,row['document_id'],{'positions':[i+1 for i,c in enumerate(row['transcription']) if c==char],'scope':row['transcription_scope']})
        if row['script'] not in ('未提取','未明确提取'):edge(id,'has_script',node(row['script'],'script'),row['document_id'])
        catalogue=row.get('field_provenance',{}).get('period_and_maker')
        index_doc=None
        if catalogue:
            rawpath=STAGE/'html'/f"index-{catalogue['index_page']}.html"
            assert digest(rawpath.read_bytes())==catalogue['index_sha256']
            index_doc=ident('doc',catalogue['index_transport_url'])
            documents[index_doc]=dict(id=index_doc,source_id='dpm',title=f"故宫玺印公开目录 · 第{catalogue['index_page']}页",url=catalogue['index_transport_url'],summary='公开目录AJAX响应；哈希对应实际响应字节，正常浏览入口：'+catalogue['index_url'],sha256=catalogue['index_sha256'],fetched_at=datetime.fromtimestamp(rawpath.stat().st_mtime,timezone.utc).isoformat(),method='public_catalogue_ajax_extraction')
        if row['period'] and not row.get('period_conflict') and '未明确' not in row['period']:
            support=row['document_id'] if row.get('period_body') or not catalogue else index_doc
            edge(id,'dated_to',node(row['period'],'period',{'classification':'source_period_label_not_a_computed_date'}),support,{'canonical_url':catalogue['index_url'] if support==index_doc else row['page_url'],'scope':'来源年代标签，不推导制作年'})
        maker=row.get('maker','')
        if maker and re.fullmatch(r'[\u3400-\u9fff]{2,5}',maker):
            person=node(maker,'person',{'role':'catalogued_seal_maker','attribution_scope':'官方目录制印人归属，未自行鉴定'})
            edge(id,'created_by',person,index_doc,{'canonical_url':catalogue['index_url'],'scope':'官方目录“(制印人)作者”栏；不等同网页撰稿人或独立鉴定'})
    
    # Preserve bibliography as citations, never claim that twenty full books were read.
    index_raw=(TASK/'work/museum-html/index-19.html').read_bytes();index_dom=DOM(index_raw.decode('utf-8')).root
    index_url='https://www.dpm.org.cn/collection/seals/p/19.html';index_doc=ident('doc',index_url)
    documents[index_doc]=dict(id=index_doc,source_id='dpm',title='故宫玺印概述、论谈与推荐书目',url=index_url,summary='读取概述及论文/书目目录；书目记录不是全文已读。',sha256=digest(index_raw),fetched_at=datetime.fromtimestamp((TASK/'work/museum-html/index-19.html').stat().st_mtime,timezone.utc).isoformat(),method='public_html_metadata_extraction')
    for table in index_dom.all(lambda e:e.has('table')):
        lines=table.all(lambda e:e.has('li'));heads=lines[0].text() if lines else ''
        if '论文名称' not in heads and '书名' not in heads:continue
        kind='paper' if '论文名称' in heads else 'book'
        for line in lines[1:]:
            cells=line.all(lambda e:e.has('span'));assert len(cells)>=4
            title,author,publication,year=[clean(c.text()) for c in cells[:4]]
            links=cells[0].all(lambda e:e.tag=='a' and e.attrs.get('href','').startswith('/seals/talk/'))
            url='https://www.dpm.org.cn'+links[0].attrs['href'] if links else index_url
            record=dict(id=ident('biblio',title,kind),title=title,kind=kind,author_as_listed=author,publication_as_listed=publication,date_as_listed=year,url=url,receipt_document_id=index_doc,access_state='catalogue_citation_only',full_text_read=False,notice='只核对官方目录著录；出版栏原样保留，未自行校订版次或读取全文。')
            bibliography.append(record)
            nid=node(title,'document',record,record['id']);edge(institutions['dpm'],'cites',nid,index_doc,{'scope':'官方推荐目录著录；非全文已读','canonical_url':index_url})
    
    # All material below is a versioned, inspectable local release, not generated history.
    release=dict(version=2,sources=sources,documents=list(documents.values()),nodes=list(nodes.values()),edges=list(edges.values()))
    (P/'data/knowledge-graph/verified-museum-expansion.json').write_text(json.dumps(release,ensure_ascii=False,indent=2),encoding='utf-8')
    (P/'data/heritage/records.json').write_text(json.dumps(records,ensure_ascii=False,indent=2),encoding='utf-8')
    (P/'frontend/src/graph/museum-seals.json').write_text(json.dumps(records,ensure_ascii=False,indent=2),encoding='utf-8')
    (P/'data/heritage/bibliography.json').write_text(json.dumps(bibliography,ensure_ascii=False,indent=2),encoding='utf-8')
    manifest=dict(purpose='Source-linked museum catalogue records; no generated artifact, no expert authentication, no training authorization',items=list(records.values()))
    (P/'frontend/public/assets/seal-previews/museum-manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
    audit={k:batch[k] for k in ['indexed','checked','accepted']};audit.update(quarantined=[r for r in batch['results'] if r['status']!='accepted'],published_collection_records=len(records),local_photos=sum(r.get('status')=='available' for r in records.values()),local_impressions=sum(bool(r.get('impression')) for r in records.values()),period_disagreements=[{k:r.get(k) for k in ['node_id','official_title','period_index','period_body','page_url']} for r in records.values() if r.get('period_conflict')],institutions=dict(Counter(r['museum'] for r in records.values())),bibliography_citations=len(bibliography),bibliography_full_texts_read=0,extraction_scope='Automated field/title/image match with explicit exceptions and sampled inspection; not independent artifact authentication')
    (P/'evidence/heritage-expansion-20261023/collection-audit.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2),encoding='utf-8')
    combined={key:{} for key in ('nodes','edges','documents','sources')}
    for filename in ['verified-public-metadata.json','verified-museum-seals.json','verified-museum-expansion.json']:
        data=json.loads((P/'data/knowledge-graph'/filename).read_text(encoding='utf-8'))
        for key in combined:combined[key].update({r['id']:r for r in data[key]})
    print(json.dumps({'published':len(records),'institutions':audit['institutions'],'photos':audit['local_photos'],'impressions':audit['local_impressions'],'date_disagreements':len(audit['period_disagreements']),'citations':len(bibliography),'graph':{k:len(v) for k,v in combined.items()}},ensure_ascii=False),flush=True)

if __name__=='__main__':main()
