"""Small, source-backed property graph in MySQL. No generated historical facts.

Public-page assertions, manual candidates and human reviews remain separate.
An edge is a claim supported by exactly one document; parallel claims retain
their individual evidence. Path search means shared attributes, not lineage.
"""
from collections import deque, Counter
from datetime import datetime
import hashlib
import json
from pathlib import Path
from typing import Literal
from urllib.parse import urlsplit
import uuid

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import Response
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import String, Text, JSON, ForeignKey, select
from sqlalchemy.dialects.mysql import DATETIME
from sqlalchemy.orm import Mapped, mapped_column
from .database import Base, Session, now, ROOT, Event

router=APIRouter(prefix='/api/graph',tags=['evidence knowledge graph'])
Kind=Literal['seal_draft','seal_object','character','script','seal_type','collection','resource','document','person','period','place']
Predicate=Literal['contains_character','has_script','has_type','cites_collection','recorded_in','describes','created_by','dated_to','located_at','cites']
KINDS={'seal_draft':'文献印稿（未核实实物）','seal_object':'馆藏实物记录','character':'汉字','script':'书体','seal_type':'类型','collection':'来源集','resource':'资源平台','document':'文献','person':'人物','period':'时期','place':'地点'}
PREDICATES={'contains_character':'包含汉字','has_script':'书体','has_type':'印章类型','cites_collection':'页面来源','recorded_in':'收录于','describes':'介绍','created_by':'创作者','dated_to':'时代','located_at':'地点','cites':'引用'}
STATUSES={'page_asserted':'页面记载','candidate':'待核验','human_reviewed':'人工复核','rejected':'已排除'}
SOURCE_HOSTS={'fudan':{'yin.fudan.edu.cn'},'yingaoku':{'yingaoku.cn','www.yingaoku.cn'},'fuiframe':{'fuiframe.art'},'nlc':{'guji.nlc.cn','www.nlc.cn'},'dpm':{'www.dpm.org.cn'},'nmc':{'www.chnmuseum.cn'},'nyw':{'www.nywmuseum.org.cn'}}
FETCHED_METHODS={'public_html_metadata_extraction','public_catalogue_ajax_extraction'}
NODE_LIMIT=1500

def ident(prefix,*parts):return prefix+'-'+hashlib.sha256('\x1f'.join(parts).encode()).hexdigest()[:28]
def iso(t):return t.isoformat()+'Z' if t else None

class GraphSource(Base):
    __tablename__='graph_sources'
    id:Mapped[str]=mapped_column(String(50),primary_key=True)
    title:Mapped[str]=mapped_column(String(150))
    url:Mapped[str]=mapped_column(String(700))
    priority:Mapped[int]
    access_state:Mapped[str]=mapped_column(String(60))
    note:Mapped[str]=mapped_column(Text)

class GraphDocument(Base):
    __tablename__='graph_documents'
    id:Mapped[str]=mapped_column(String(40),primary_key=True)
    source_id:Mapped[str]=mapped_column(ForeignKey('graph_sources.id'))
    title:Mapped[str]=mapped_column(String(200))
    url:Mapped[str]=mapped_column(String(700))
    summary:Mapped[str]=mapped_column(Text)
    sha256:Mapped[str|None]=mapped_column(String(64),nullable=True)
    fetched_at:Mapped[datetime|None]=mapped_column(DATETIME(fsp=6),nullable=True)
    method:Mapped[str]=mapped_column(String(60))

class GraphNode(Base):
    __tablename__='graph_nodes'
    id:Mapped[str]=mapped_column(String(40),primary_key=True)
    label:Mapped[str]=mapped_column(String(150))
    kind:Mapped[str]=mapped_column(String(30),index=True)
    attributes:Mapped[dict]=mapped_column(JSON,default=dict)

class GraphRelation(Base):
    __tablename__='graph_relations'
    id:Mapped[str]=mapped_column(String(40),primary_key=True)
    subject:Mapped[str]=mapped_column(ForeignKey('graph_nodes.id'),index=True)
    predicate:Mapped[str]=mapped_column(String(40))
    object:Mapped[str]=mapped_column(ForeignKey('graph_nodes.id'),index=True)
    document_id:Mapped[str]=mapped_column(ForeignKey('graph_documents.id'),index=True)
    status:Mapped[str]=mapped_column(String(30),index=True)
    attributes:Mapped[dict]=mapped_column(JSON,default=dict)
    reviewer:Mapped[str|None]=mapped_column(String(80),nullable=True)
    review_note:Mapped[str|None]=mapped_column(Text,nullable=True)
    reviewed_at:Mapped[datetime|None]=mapped_column(DATETIME(fsp=6),nullable=True)
    created_at:Mapped[datetime]=mapped_column(DATETIME(fsp=6),default=now)

def seed_graph(db):
    """Idempotent checked-in receipt, built from successful public HTML fetches.

    Never overwrite manual review on restart. Site statistics and illustrative
    UI relationships are intentionally absent from this seed.
    """
    data={key:[] for key in ('sources','documents','nodes','edges')}
    for name in ('verified-public-metadata.json','verified-museum-seals.json','verified-museum-expansion.json'):
        path=ROOT/'data/knowledge-graph'/name
        if path.exists():
            receipt=json.loads(path.read_text(encoding='utf-8'))
            for key in data:data[key].extend(receipt[key])
    for cls,key in [(GraphSource,'sources'),(GraphDocument,'documents'),(GraphNode,'nodes'),(GraphRelation,'edges')]:
        for item in data[key]:
            item=dict(item)
            if item.get('fetched_at'):item['fetched_at']=datetime.fromisoformat(item['fetched_at'].replace('Z','+00:00')).replace(tzinfo=None)
            existing=db.get(cls,item['id'])
            if not existing:db.add(cls(**item))
            elif cls is GraphSource:
                for field in ('title','url','priority','access_state','note'):setattr(existing,field,item[field])
            elif cls is GraphNode and item['kind']=='resource' and item['attributes'].get('source_id'):
                existing.attributes={**existing.attributes,'url':item['attributes']['url']}
        db.flush()

def source_json(s):return {k:getattr(s,k) for k in ('id','title','url','priority','access_state','note')}
def document_json(d):return {'id':d.id,'source_id':d.source_id,'title':d.title,'url':d.url,'summary':d.summary,'sha256':d.sha256,'fetched_at':iso(d.fetched_at),'method':d.method}
def edge_json(e,document=None):return {'id':e.id,'source':e.subject,'target':e.object,'predicate':e.predicate,'label':PREDICATES[e.predicate],'document_id':e.document_id,'status':e.status,'assertion_source':('page_fetched' if document.method in FETCHED_METHODS else 'manual_citation') if document else None,'review_state':e.status if e.status in ('human_reviewed','rejected') else 'unreviewed','attributes':e.attributes,'reviewer':e.reviewer,'review_note':e.review_note,'reviewed_at':iso(e.reviewed_at)}
def snapshot(db,q='',kind='',source='',status='',focus='',depth=1,assertion_source=''):
    ns=list(db.scalars(select(GraphNode).order_by(GraphNode.kind,GraphNode.label)))
    ds={d.id:d for d in db.scalars(select(GraphDocument))}
    es=[e for e in db.scalars(select(GraphRelation).order_by(GraphRelation.id))
        if (e.status==status if status else e.status not in ('candidate','rejected')) and (not source or ds[e.document_id].source_id==source)
        and (not assertion_source or ('page_fetched' if ds[e.document_id].method in FETCHED_METHODS else 'manual_citation')==assertion_source)]
    visible={x for e in es for x in (e.subject,e.object)}|{n.id for n in ns if n.kind=='resource' and n.attributes.get('source_id')}
    if source or status:visible={x for e in es for x in (e.subject,e.object)}|{n.id for n in ns if n.kind=='resource' and n.attributes.get('source_id')==source}
    roots={n.id for n in ns if n.id in visible and (not q or q.casefold() in n.label.casefold()) and (not kind or n.kind==kind)}
    if focus:
        if focus not in visible:raise HTTPException(404,'节点不在当前筛选结果中')
        roots={focus}
    # Search/type results include bounded adjacent context. All edges still match
    # source/review filters; search never silently reintroduces excluded claims.
    keep=set(roots)
    if q or kind or focus:
        for _ in range(depth):
            keep|={other for e in es for one,other in ((e.subject,e.object),(e.object,e.subject)) if one in keep}
    limited=len(keep)>NODE_LIMIT
    keep=set(sorted(keep)[:NODE_LIMIT])
    es=[e for e in es if e.subject in keep and e.object in keep]
    doc_ids={e.document_id for e in es}
    # Resource nodes have source links even when no object-level records exist.
    nodes=[{'id':n.id,'label':n.label,'kind':n.kind,'kind_label':KINDS[n.kind],'attributes':n.attributes,
        'matched':n.id in roots,'statuses':sorted({e.status for e in es if n.id in (e.subject,e.object)})} for n in ns if n.id in keep]
    receipts=[document_json(d) for d in ds.values() if not source or d.source_id==source]
    return {'nodes':nodes,'edges':[edge_json(e,ds[e.document_id]) for e in es],
        'documents':[document_json(ds[i]) for i in sorted(doc_ids)],
        'receipts':receipts,
        'sources':[source_json(s) for s in db.scalars(select(GraphSource).order_by(GraphSource.priority))],
        'counts':{'nodes':len(nodes),'edges':len(es),'documents':len(doc_ids),'receipts':len(receipts),'matched':len(roots&keep),'context':len(keep-roots),'by_kind':dict(Counter(n['kind'] for n in nodes))},
        'limited':limited,'node_limit':NODE_LIMIT,'kinds':KINDS,'predicates':PREDICATES,'statuses':STATUSES,
        'notice':'页面记载表示已读取该网页，尚非文物专家鉴定。图中路径只表示资料关联，不代表传承、因果或字形训练标签。'}

@router.get('')
def graph(q:str=Query('',max_length=100),kind:str='',source:str='',status:str='',focus:str='',depth:int=Query(1,ge=0,le=2),assertion_source:Literal['','page_fetched','manual_citation']=''):
    if kind and kind not in KINDS:raise HTTPException(422,'未知节点类型')
    if status and status not in STATUSES:raise HTTPException(422,'未知核验状态')
    with Session() as db:return snapshot(db,q,kind,source,status,focus,depth,assertion_source)

@router.get('/path')
def path(start:str,end:str,source:str='',q:str=Query('',max_length=100),kind:str='',status:str='',assertion_source:Literal['','page_fetched','manual_citation']=''):
    with Session() as db:
        data=snapshot(db,q=q,kind=kind,source=source,status=status,assertion_source=assertion_source)
    nodes={n['id']:n for n in data['nodes']}
    if start not in nodes or end not in nodes:raise HTTPException(404,'路径端点不存在或被筛选排除')
    adjacency={i:[] for i in nodes}
    for e in data['edges']:
        adjacency[e['source']].append((e['target'],e));adjacency[e['target']].append((e['source'],e))
    queue=deque([start]);previous={start:None}
    while queue:
        item=queue.popleft()
        if item==end:break
        for other,e in adjacency[item]:
            if other not in previous:previous[other]=(item,e);queue.append(other)
    if end not in previous:return {'found':False,'nodes':[],'edges':[],'documents':[],'notice':'当前有据关系中没有路径。'}
    ids=[end];edges=[];cursor=end
    while previous[cursor]:
        cursor,e=previous[cursor];ids.append(cursor);edges.append(e)
    edges.reverse();ids.reverse()
    return {'found':True,'nodes':[nodes[i] for i in ids],'edges':edges,
        'documents':[d for d in data['documents'] if d['id'] in {e['document_id'] for e in edges}],
        'notice':'无向最短资料关联路径；共享书体或汉字不构成传承关系。'}

class EntityInput(BaseModel):
    label:str=Field(min_length=1,max_length=150)
    kind:Kind
    @field_validator('label')
    @classmethod
    def clean(cls,v):
        if not v.strip():raise ValueError('节点名称不能为空')
        return v.strip()

class ClaimInput(BaseModel):
    subject:EntityInput
    predicate:Predicate
    object:EntityInput

class ImportInput(BaseModel):
    source_id:str=Field(min_length=1,max_length=50)
    url:str=Field(min_length=8,max_length=700)
    title:str=Field(min_length=1,max_length=200)
    note:str=Field(min_length=5,max_length=1500)
    claims:list[ClaimInput]=Field(min_length=1,max_length=100)
    @field_validator('url')
    @classmethod
    def public_url(cls,v):
        u=urlsplit(v)
        if u.scheme not in ('http','https') or not u.hostname or u.username or u.password or any(c.isspace() for c in v):raise ValueError('请提供不含凭据的网页地址')
        return v
    @field_validator('title','note')
    @classmethod
    def meaningful(cls,v):
        if not v.strip():raise ValueError('内容不能为空')
        return v.strip()

@router.post('/imports',status_code=201)
def import_claims(body:ImportInput):
    # Citation is stored only. This API does not fetch a supplied URL, execute
    # external queries, or promote user assertions into page-verified evidence.
    if any(entity.kind=='seal_object' for claim in body.claims for entity in (claim.subject,claim.object)):
        raise HTTPException(422,'馆藏实物记录须由官方藏品凭证采集；普通资料线索请使用文献印稿，不能直接指定为真实馆藏。')
    with Session() as db:
        if not db.get(GraphSource,body.source_id):raise HTTPException(422,'请选择已有来源平台')
        if urlsplit(body.url).hostname not in SOURCE_HOSTS.get(body.source_id,set()):raise HTTPException(422,'引用网址的主机与所选资料平台不一致')
        document=GraphDocument(id='doc-'+uuid.uuid4().hex[:28],source_id=body.source_id,title=body.title,url=body.url,
            summary=body.note,sha256=None,fetched_at=None,method='manual_citation_not_fetched')
        db.add(document);db.flush();ids=[]
        for claim in body.claims:
            ends=[]
            for entity in (claim.subject,claim.object):
                nid=ident('node',entity.kind,entity.label)
                if not db.get(GraphNode,nid):db.add(GraphNode(id=nid,label=entity.label,kind=entity.kind,attributes={}))
                db.flush();ends.append(nid)
            eid=ident('edge',ends[0],claim.predicate,ends[1],document.id)
            if not db.get(GraphRelation,eid):
                db.add(GraphRelation(id=eid,subject=ends[0],predicate=claim.predicate,object=ends[1],document_id=document.id,status='candidate',attributes={}))
                db.flush();ids.append(eid)
        db.add(Event(id=str(uuid.uuid4()),seal_id=None,action='graph_import',details={'document_id':document.id,'claims':len(ids),'status':'candidate'}))
        db.commit();return {'document':document_json(document),'edge_ids':ids,'status':'candidate','notice':'已保存为待核验线索，默认有据图谱中不展示。'}

class ReviewInput(BaseModel):
    decision:Literal['human_reviewed','rejected']
    reviewer:str=Field(min_length=2,max_length=80)
    note:str=Field(min_length=5,max_length=1500)
    @field_validator('reviewer','note')
    @classmethod
    def clean(cls,v,info):
        if len(v.strip()) < (2 if info.field_name=='reviewer' else 5):raise ValueError('请填写可追溯的复核人和至少5字依据')
        return v.strip()

@router.post('/edges/{edge_id}/review')
def review(edge_id:str,body:ReviewInput):
    with Session() as db:
        e=db.get(GraphRelation,edge_id)
        if not e:raise HTTPException(404,'关系不存在')
        old=e.status;e.status=body.decision;e.reviewer=body.reviewer;e.review_note=body.note;e.reviewed_at=now()
        db.add(Event(id=str(uuid.uuid4()),seal_id=None,action='graph_review',details={'edge_id':e.id,'before':old,'after':e.status,'reviewer':body.reviewer,'note':body.note}))
        db.commit();return edge_json(e,db.get(GraphDocument,e.document_id))

@router.get('/export')
def export(format:Literal['json','turtle','json-ld']='json',q:str=Query('',max_length=100),kind:str='',source:str='',status:str='',assertion_source:Literal['','page_fetched','manual_citation']=''):
    with Session() as db:data=snapshot(db,q,kind,source,status,assertion_source=assertion_source)
    if format=='json':payload=json.dumps(data,ensure_ascii=False,indent=2);mime='application/json';ext='json'
    else:
        from rdflib import Graph, Namespace, URIRef, Literal as RDFLiteral
        from rdflib.namespace import RDF,RDFS,PROV,XSD
        g=Graph();ns=Namespace('https://yinmai.local/graph/');g.bind('ym',ns);g.bind('prov',PROV)
        for n in data['nodes']:
            subject=ns[n['id']];g.add((subject,RDF.type,ns[n['kind']]));g.add((subject,RDFS.label,RDFLiteral(n['label'],lang='zh')))
            g.add((subject,ns.attributes,RDFLiteral(json.dumps(n['attributes'],ensure_ascii=False))))
        for s in data['sources']:
            subject=ns['source-'+s['id']];g.add((subject,RDF.type,ns.Source));g.add((subject,RDFS.label,RDFLiteral(s['title'],lang='zh')));g.add((subject,PROV.atLocation,URIRef(s['url'])));g.add((subject,ns.accessState,RDFLiteral(s['access_state'])));g.add((subject,ns.note,RDFLiteral(s['note'],lang='zh')))
        for d in data['receipts']:
            doc=ns[d['id']];g.add((doc,RDF.type,PROV.Entity));g.add((doc,PROV.atLocation,URIRef(d['url'])));g.add((doc,RDFS.label,RDFLiteral(d['title'],lang='zh')))
            g.add((doc,ns.method,RDFLiteral(d['method'])));g.add((doc,ns.summary,RDFLiteral(d['summary'],lang='zh')));g.add((doc,ns.source,ns['source-'+d['source_id']]))
            if d['sha256']:g.add((doc,ns.sha256,RDFLiteral(d['sha256'])))
            if d['fetched_at']:g.add((doc,PROV.generatedAtTime,RDFLiteral(d['fetched_at'],datatype=XSD.dateTime)))
        for e in data['edges']:
            claim=ns[e['id']];g.add((claim,RDF.type,RDF.Statement));g.add((claim,RDF.subject,ns[e['source']]));g.add((claim,RDF.predicate,ns[e['predicate']]));g.add((claim,RDF.object,ns[e['target']]));g.add((claim,PROV.wasDerivedFrom,ns[e['document_id']]));g.add((claim,ns.reviewStatus,RDFLiteral(e['status'])))
            g.add((claim,ns.assertionSource,RDFLiteral(e['assertion_source'])));g.add((claim,ns.reviewState,RDFLiteral(e['review_state'])));g.add((claim,ns.attributes,RDFLiteral(json.dumps(e['attributes'],ensure_ascii=False))))
            if e['reviewer']:g.add((claim,ns.reviewer,RDFLiteral(e['reviewer'])))
            if e['review_note']:g.add((claim,ns.reviewNote,RDFLiteral(e['review_note'],lang='zh')))
            if e['reviewed_at']:g.add((claim,ns.reviewedAt,RDFLiteral(e['reviewed_at'],datatype=XSD.dateTime)))
            # Reification preserves candidate/rejected status without asserting
            # those claims as ordinary facts to downstream RDF consumers.
            # Export all assertions as cited claims only; consumers must choose
            # their own review policy before materialising ordinary fact triples.
        payload=g.serialize(format=format);mime='text/turtle' if format=='turtle' else 'application/ld+json';ext='ttl' if format=='turtle' else 'jsonld'
    return Response(payload,media_type=mime,headers={'Content-Disposition':f'attachment; filename="yinmai-graph.{ext}"'})
