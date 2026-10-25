"""Published, receipt-matched museum records. Never fill missing catalogue facts."""
from collections import Counter
from pathlib import Path
import hashlib,json,re
from fastapi import APIRouter,Query
from sqlalchemy import select
from .database import ROOT,Session
from .graph import GraphNode,GraphDocument,GraphRelation,ident,FETCHED_METHODS

router=APIRouter(prefix='/api/heritage',tags=['verified heritage catalogue'])
REGISTRY=json.loads((ROOT/'data/heritage/records.json').read_text(encoding='utf-8'))
CATALOGUE_DIGEST=hashlib.sha256((ROOT/'data/heritage/records.json').read_bytes()).hexdigest()
BIBLIOGRAPHY=json.loads((ROOT/'data/heritage/bibliography.json').read_text(encoding='utf-8'))
EXPECTED_DOCS={d['id']:d for d in json.loads((ROOT/'data/knowledge-graph/verified-museum-expansion.json').read_text(encoding='utf-8'))['documents']}
ASSERTED={'page_asserted','human_reviewed'}
PHOTO_CACHE={}

@router.get('/version')
def version():return {'schema_version':'heritage-2','catalogue_digest':CATALOGUE_DIGEST}

def preview_available(row,image=None,suffix=''):
    image=row if image is None else image
    expected='/assets/seal-previews/'+row['node_id']+suffix+'.webp'
    if (not suffix and row.get('status')!='available') or not image or image.get('display_url')!=expected:return False
    path=ROOT/'frontend/public'/expected.lstrip('/')
    if not path.is_file():return False
    signature=(path.stat().st_mtime_ns,path.stat().st_size,image.get('preview_sha256'))
    old=PHOTO_CACHE.get(str(path))
    if old and old[0]==signature:return old[1]
    valid=hashlib.sha256(path.read_bytes()).hexdigest()==image.get('preview_sha256')
    PHOTO_CACHE[str(path)]=(signature,valid);return valid

def published_records(db):
    nodes={n.id:n for n in db.scalars(select(GraphNode).where(GraphNode.id.in_(list(REGISTRY))))}
    docs={d.id:d for d in db.scalars(select(GraphDocument).where(GraphDocument.id.in_([r['document_id'] for r in REGISTRY.values()])))}
    proofs={(e.subject,e.document_id):e for e in db.scalars(select(GraphRelation).where(GraphRelation.predicate=='recorded_in',GraphRelation.status.in_(ASSERTED)))}
    institutions={n.id:n.attributes.get('source_id') for n in db.scalars(select(GraphNode).where(GraphNode.kind=='resource'))}
    result=[]
    for id,row in REGISTRY.items():
        n=nodes.get(id);d=docs.get(row['document_id']);proof=proofs.get((id,row['document_id']))
        if not n or n.kind!='seal_object' or not d or not proof or institutions.get(proof.object)!=row['source_id']:continue
        attrs=n.attributes
        if attrs.get('record_type')!='museum_object' or n.label!=row['label']:continue
        if any(attrs.get(k)!=row[k] for k in ['official_title','accession_number','museum','period','material','dimensions','transcription']):continue
        if attrs.get('url')!=row['page_url'] or d.url!=row['page_url'] or d.source_id!=row['source_id'] or d.sha256!=row['page_sha256'] or not d.fetched_at or d.method!='public_html_metadata_extraction':continue
        if proof.attributes.get('accession_number')!=row['accession_number']:continue
        if row.get('catalogue_record_id') and (attrs.get('catalogue_record_id')!=row['catalogue_record_id'] or proof.attributes.get('catalogue_record_id')!=row['catalogue_record_id']):continue
        result.append({**row,'preview_available':preview_available(row),'impression_available':bool(row.get('impression')) and preview_available(row,row.get('impression'),'-impression'),'historical_authentication':'official_catalogue_record_not_independent_authentication'})
    return sorted(result,key=lambda r:(r['museum'],r['official_title']))

def published_bibliography(db):
    expected_ids={r['receipt_document_id'] for r in BIBLIOGRAPHY}
    docs={d.id:d for d in db.scalars(select(GraphDocument).where(GraphDocument.id.in_(expected_ids)))}
    nodes={n.id for n in db.scalars(select(GraphNode).where(GraphNode.kind=='document'))}
    proofs={(e.object,e.document_id) for e in db.scalars(select(GraphRelation).where(GraphRelation.predicate=='cites',GraphRelation.status.in_(ASSERTED)))}
    def receipt_matches(id):
        d=docs.get(id);expected=EXPECTED_DOCS.get(id)
        return bool(d and expected and d.sha256==expected['sha256'] and d.url==expected['url'] and d.source_id==expected['source_id'] and d.fetched_at and d.method in FETCHED_METHODS)
    return [r for r in BIBLIOGRAPHY if ident('node','document',r['id']) in nodes and (ident('node','document',r['id']),r['receipt_document_id']) in proofs and receipt_matches(r['receipt_document_id'])]

def period_group(row):
    if row.get('period_conflict'):return '分期待核对'
    value=row['period']
    for group in ['战国','秦','西汉','东汉','汉','三国','东晋','西晋','晋','十六国','南北朝','隋','唐','五代','辽','北宋','南宋','宋','西夏','金','元','明','清','民国','近现代']:
        if value.startswith(group):return group
    return '未归类'

@router.get('/overview')
def overview():
    with Session() as db:
        records=published_records(db);books=published_bibliography(db)
        receipts=[d for d in db.scalars(select(GraphDocument)) if d.sha256 and d.fetched_at and d.method in FETCHED_METHODS]
        maker_names={r.get('maker') for r in records if re.fullmatch(r'[\u3400-\u9fff]{2,5}',r.get('maker',''))}
        groups=Counter(period_group(r) for r in records)
        chosen=[]
        # Source and period diversity are browsing choices, never historical links.
        for source in ['nyw','nmc']:
            pick=next((r for r in records if r['source_id']==source and r['preview_available']),None)
            if pick:chosen.append(pick)
        for group in ['战国','秦','西汉','东汉','唐','明','清','近现代']:
            pick=next((r for r in records if period_group(r)==group and r['preview_available'] and r not in chosen),None)
            if pick:chosen.append(pick)
            if len(chosen)>=8:break
        return {'counts':{'catalogue_records':len(records),'local_photos':sum(r['preview_available'] for r in records),'local_impressions':sum(r['impression_available'] for r in records),'institutions':len({r['museum'] for r in records}),'period_labels':len({r['period'] for r in records if not r.get('period_conflict')}),'period_groups':len([g for g in groups if g not in ('分期待核对','未归类')]),'named_seal_makers':len(maker_names),'bibliography_citations':len(books),'bibliography_full_texts_read':0,'source_receipts':len(receipts),'period_disagreements':sum(bool(r.get('period_conflict')) for r in records)},'by_period_group':dict(groups),'period_grouping_scope':'按来源年代文字前缀浏览归类，不据此推导制作年','institutions':dict(Counter(r['museum'] for r in records)),'featured':chosen,'bibliography':books,'notice':'馆藏记录与照片均可追溯；文献目录不等于全文已读，来源分期不同保留待核对。'}

@router.get('/catalogue')
def catalogue(q:str=Query('',max_length=100),institution:str=Query('',max_length=100),period:str=Query('',max_length=100),character:str=Query('',max_length=4),page:int=Query(1,ge=1),page_size:int=Query(12,ge=1,le=48)):
    with Session() as db:rows=published_records(db)
    total=len(rows)
    rows=[r for r in rows if (not institution or r['museum']==institution) and (not period or period_group(r)==period) and (not character or character in r['transcription']) and (not q or q in ' '.join([r['official_title'],r['transcription'],r['accession_number'],r.get('catalogue_record_id',''),r['period'],r['material'],r.get('maker','')]))]
    start=(page-1)*page_size
    return {'items':rows[start:start+page_size],'matched':len(rows),'total_published':total,'page':page,'page_size':page_size,'notice':'数量表示已接入的官方条目，不是馆藏总件数；组印按一条记录计。'}

@router.get('/bibliography')
def bibliography():
    with Session() as db:rows=published_bibliography(db)
    return {'items':rows,'count':len(rows),'full_texts_read':0,'notice':'官方推荐目录著录，不代表已取得或核读全文。'}
