"""Evidence graph contracts on a separate, real MySQL database."""
import json
import os
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select,func
from rdflib import Graph,Namespace
from rdflib.namespace import RDF,PROV
from app.main import app
from app.database import Session,engine,Event
from app.graph import seed_graph,GraphNode,GraphRelation,GraphDocument
from app.database import ROOT
SEED=json.loads((ROOT/'data/knowledge-graph/verified-public-metadata.json').read_text(encoding='utf-8'))
MUSEUM=json.loads((ROOT/'data/knowledge-graph/verified-museum-seals.json').read_text(encoding='utf-8'))
EXPANSION=json.loads((ROOT/'data/knowledge-graph/verified-museum-expansion.json').read_text(encoding='utf-8'))
REGISTRY=json.loads((ROOT/'data/heritage/records.json').read_text(encoding='utf-8'))
BASE_EDGES=list(SEED['edges'])
SEED={key:list({row['id']:row for row in SEED[key]+MUSEUM[key]+EXPANSION[key]}.values()) for key in ('nodes','edges','documents','sources')}

@pytest.fixture(scope='module')
def client():
    assert os.environ['MYSQL_DATABASE'].startswith('yinmai_qa_')
    with TestClient(app) as c:yield c

def test_seed_is_real_provenance_and_idempotent(client):
    data=client.get('/api/graph').json()
    expected=[len(SEED[k]) for k in ('nodes','edges','documents')]
    assert (data['counts']['nodes'],data['counts']['edges'])==tuple(expected[:2])
    assert len(data['sources'])==7 and data['sources'][0]['id']=='fudan'
    assert data['sources'][0]['access_state']=='homepage_only'
    assert all(e['status']=='page_asserted' for e in data['edges'])
    assert not any(n['kind']=='place' for n in data['nodes'])
    assert sum(n['kind']=='person' for n in data['nodes'])==8
    assert not data['limited']
    docs={d['id']:d for d in data['documents']}
    assert all(e['document_id'] in docs for e in data['edges'])
    assert all(len(d['sha256'])==64 and d['fetched_at'] and d['url'].startswith('https://') for d in docs.values())
    with Session() as db:
        before=[db.scalar(select(func.count()).select_from(c)) for c in (GraphNode,GraphRelation,GraphDocument)]
        seed_graph(db);seed_graph(db);db.commit()
        after=[db.scalar(select(func.count()).select_from(c)) for c in (GraphNode,GraphRelation,GraphDocument)]
    assert before==after==expected
    engine.dispose()
    assert client.get('/api/graph').json()['counts']['edges']==expected[1]

def test_filters_include_context_without_reintroducing_other_sources(client):
    all_=client.get('/api/graph').json()
    found=client.get('/api/graph',params={'q':'人生一梦','depth':0}).json()
    assert len(found['nodes'])==1 and found['nodes'][0]['label']=='人生一梦' and not found['edges']
    with_context=client.get('/api/graph',params={'q':'人生一梦'}).json()
    assert len(with_context['edges'])==8
    fudan=client.get('/api/graph?source=fudan').json()
    assert len(fudan['nodes'])==1 and len(fudan['receipts'])==1 and not fudan['edges']
    assert fudan['receipts'][0]['url']=='https://yin.fudan.edu.cn/'
    guji=client.get('/api/graph?source=nlc').json()
    assert len(guji['edges'])==1 and guji['edges'][0]['predicate']=='describes'
    assert len(client.get('/api/graph?q=没有此节点').json()['nodes'])==0
    assert client.get('/api/graph?kind=unknown').status_code==422
    assert client.get('/api/graph?status=verified_by_ai').status_code==422
    assert client.get('/api/graph?depth=3').status_code==422

def test_paths_are_evidence_backed_and_do_not_invent_lineage(client):
    data=client.get('/api/graph').json();ids={n['label']:n['id'] for n in data['nodes']}
    path=client.get('/api/graph/path',params={'start':ids['人生一梦'],'end':ids['人生如梦']}).json()
    assert path['found'] and len(path['edges'])==2 and len(path['nodes'])==3
    assert path['nodes'][0]['id']==ids['人生一梦'] and path['nodes'][-1]['id']==ids['人生如梦']
    assert all(e['document_id'] in {d['id'] for d in path['documents']} for e in path['edges'])
    isolated=client.get('/api/graph/path',params={'start':ids['人生一梦'],'end':ids['复旦大学 · 印藏']}).json()
    assert not isolated['found'] and not isolated['edges']
    assert client.get('/api/graph/path?start=missing&end=missing').status_code==404

@pytest.mark.parametrize('format',['json','turtle','json-ld'])
def test_exports_roundtrip_with_provenance(client,format):
    r=client.get('/api/graph/export',params={'format':format,'source':'yingaoku'})
    assert r.status_code==200 and 'attachment' in r.headers['content-disposition']
    if format=='json':
        data=r.json();assert len(data['edges'])==len(BASE_EDGES)-1 and len(data['documents'])==14
    else:
        rdf=Graph().parse(data=r.text,format=format)
        assert len(list(rdf.triples((None,RDF.type,RDF.Statement))))==len(BASE_EDGES)-1
        assert len(list(rdf.triples((None,PROV.wasDerivedFrom,None))))==len(BASE_EDGES)-1
        ns=Namespace('https://yinmai.local/graph/')
        assert not list(rdf.triples((None,ns.contains_character,None)))
        assert list(rdf.triples((None,ns.assertionSource,None)))

def claim_body():return {'source_id':'fudan','url':'https://yin.fudan.edu.cn/#/qa-citation','title':'QA人工线索（非真实条目）','note':'仅用于检查候选状态和持久化，不作为实际资料。','claims':[{'subject':{'label':'QA待核验印稿','kind':'seal_draft'},'predicate':'has_script','object':{'label':'QA待核验书体','kind':'script'}}]}

def test_physical_seals_have_distinct_official_collection_receipts(client):
    data=client.get('/api/graph?source=dpm').json()
    objects=[n for n in data['nodes'] if n['kind']=='seal_object']
    assert len(objects)==120
    assert not any(n['kind']=='seal_draft' for n in data['nodes'])
    assert {n['attributes']['accession_number'] for n in objects}>={'故00166815','故00166295','故00166806'}
    for node in objects:
        assert node['attributes']['museum']=='故宫博物院'
        document=next(d for d in data['documents'] if d['url']==node['attributes']['url'])
        assert document['source_id']=='dpm' and document['sha256'] and document['fetched_at']
        chars=[e for e in data['edges'] if e['source']==node['id'] and e['predicate']=='contains_character']
        assert chars and all(e['document_id']==document['id'] for e in chars)
    assert client.get('/api/graph?kind=seal_object').status_code==200
    all_objects=client.get('/api/graph?kind=seal_object&depth=0').json()
    assert {n['id'] for n in all_objects['nodes']}==set(REGISTRY)
    index_edges=[e for e in data['edges'] if e['predicate'] in ('dated_to','created_by')]
    assert index_edges and all(e['assertion_source']=='page_fetched' for e in index_edges)

def test_manual_claim_cannot_create_a_physical_collection_record(client):
    body=claim_body();body.update(source_id='dpm',url='https://www.dpm.org.cn/collection/seal/999999.html')
    body['claims'][0]['subject']={'label':'QA未核实实物','kind':'seal_object'}
    result=client.post('/api/graph/imports',json=body);assert result.status_code==422
    body['claims'][0]['subject']['kind']='seal_draft'
    result=client.post('/api/graph/imports',json=body);assert result.status_code==201
    assert result.json()['document']['sha256'] is None
    assert not client.get('/api/graph?q=QA未核实实物').json()['nodes']
    candidates=client.get('/api/graph?source=dpm&status=candidate').json()
    assert any(n['label']=='QA未核实实物' for n in candidates['nodes'])
    body['url']='https://dpm.org.cn.evil.example/collection/seal/1.html'
    assert client.post('/api/graph/imports',json=body).status_code==422

def test_manual_import_stays_candidate_until_explicit_human_review(client):
    body=claim_body();body['claims']*=2
    r=client.post('/api/graph/imports',json=body);assert r.status_code==201,r.text
    result=r.json();assert result['status']=='candidate' and len(result['edge_ids'])==1
    assert result['document']['sha256'] is None and result['document']['fetched_at'] is None
    assert result['document']['method']=='manual_citation_not_fetched'
    edge_id=result['edge_ids'][0];engine.dispose()
    assert not client.get('/api/graph?q=QA').json()['nodes']
    candidates=client.get('/api/graph?status=candidate').json()
    assert any(e['id']==edge_id for e in candidates['edges'])
    rdf=Graph().parse(data=client.get('/api/graph/export?format=turtle&status=candidate').text,format='turtle')
    ns=Namespace('https://yinmai.local/graph/');edge=next(e for e in candidates['edges'] if e['id']==edge_id)
    assert (ns[edge['source']],ns.has_script,ns[edge['target']]) not in rdf
    assert (ns[edge_id],ns.reviewStatus,None) in rdf
    bad=client.post('/api/graph/edges/'+edge_id+'/review',json={'decision':'human_reviewed','reviewer':'','note':''})
    assert bad.status_code==422
    reviewed=client.post('/api/graph/edges/'+edge_id+'/review',json={'decision':'human_reviewed','reviewer':'QA复核人','note':'测试人工复核记录，非历史结论。'})
    assert reviewed.status_code==200 and reviewed.json()['reviewer']=='QA复核人'
    assert reviewed.json()['assertion_source']=='manual_citation' and reviewed.json()['review_state']=='human_reviewed'
    assert client.get('/api/graph?q=QA').json()['edges']
    rdf=Graph().parse(data=client.get('/api/graph/export?format=turtle&status=human_reviewed').text,format='turtle')
    assert (ns[edge_id],ns.reviewer,None) in rdf and (ns[edge_id],ns.reviewNote,None) in rdf
    assert not client.get('/api/graph?assertion_source=page_fetched&q=QA').json()['edges']
    with Session() as db:
        seed_graph(db);db.commit()
        assert db.get(GraphRelation,edge_id).status=='human_reviewed'
        assert any(e.details['edge_id']==edge_id for e in db.scalars(select(Event).where(Event.action=='graph_review')))
    rejected=client.post('/api/graph/edges/'+edge_id+'/review',json={'decision':'rejected','reviewer':'QA复核人','note':'检查排除操作及默认视图过滤。'})
    assert rejected.status_code==200
    assert not client.get('/api/graph?q=QA').json()['nodes']

@pytest.mark.parametrize('field,value',[('url','file:///private'),('url','https://name:secret@example.com'),('url','https://example.com/a b'),('url','https://example.com/fake-fudan'),('url','http://127.0.0.1/private'),('source_id','unknown')])
def test_import_rejects_invalid_citations(client,field,value):
    body=claim_body();body[field]=value
    assert client.post('/api/graph/imports',json=body).status_code==422

def test_invalid_relation_kind_and_empty_batch_are_rejected(client):
    body=claim_body();body['claims'][0]['predicate']='ai_invented_relation'
    assert client.post('/api/graph/imports',json=body).status_code==422
    body=claim_body();body['claims']=[]
    assert client.post('/api/graph/imports',json=body).status_code==422
