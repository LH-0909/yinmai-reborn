"""Receipt-gated catalogue behaviour against an isolated real MySQL schema."""
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.database import Session
from app.graph import GraphNode,GraphDocument,GraphRelation
from app.heritage import REGISTRY,BIBLIOGRAPHY,published_records,published_bibliography

@pytest.fixture(scope='module')
def client():
    with TestClient(app) as c:yield c

def test_actual_overview_and_citation_scope(client):
    r=client.get('/api/heritage/overview');assert r.status_code==200
    counts=r.json()['counts']
    assert counts=={'catalogue_records':125,'local_photos':125,'local_impressions':106,'institutions':3,'period_labels':33,'period_groups':18,'named_seal_makers':8,'bibliography_citations':20,'bibliography_full_texts_read':0,'source_receipts':170,'period_disagreements':5}
    assert len(r.json()['featured'])==8
    b=client.get('/api/heritage/bibliography').json()
    assert b['count']==20 and b['full_texts_read']==0
    assert all(x['full_text_read'] is False and x['access_state']=='catalogue_citation_only' for x in b['items'])

def test_real_pagination_filters_and_source_characters(client):
    first=client.get('/api/heritage/catalogue?page_size=6').json()
    second=client.get('/api/heritage/catalogue?page_size=6&page=2').json()
    assert first['total_published']==first['matched']==125
    assert len(first['items'])==len(second['items'])==6
    assert not {r['node_id'] for r in first['items']}&{r['node_id'] for r in second['items']}
    assert client.get('/api/heritage/catalogue?page_size=49').status_code==422
    assert client.get('/api/heritage/catalogue?page=0').status_code==422
    for institution,count in [('故宫博物院',120),('中国国家博物馆',3),('南越王博物院',2)]:
        response=client.get('/api/heritage/catalogue',params={'institution':institution}).json()
        assert response['matched']==count and all(r['museum']==institution for r in response['items'])
    result=client.get('/api/heritage/catalogue',params={'character':'鉩'}).json()
    assert result['matched']>=1 and all('鉩' in r['transcription'] for r in result['items'])
    assert client.get('/api/heritage/catalogue?q=NONEXISTENT').json()['matched']==0
    disputed=client.get('/api/heritage/catalogue',params={'period':'分期待核对'}).json()
    assert disputed['matched']==5 and all(r['period_conflict'] for r in disputed['items'])

def test_bibliographic_citation_requires_fetched_official_receipt():
    with Session() as db:
        assert len(published_bibliography(db))==20
        doc=db.get(GraphDocument,BIBLIOGRAPHY[0]['receipt_document_id'])
        doc.method='manual_citation_not_fetched';db.flush()
        assert not published_bibliography(db)
        db.rollback()

@pytest.mark.parametrize('tamper',['node','receipt','proof'])
def test_inconsistent_database_evidence_excludes_object_without_modifying_seed(tamper):
    row=next(iter(REGISTRY.values()))
    with Session() as db:
        assert len(published_records(db))==125
        if tamper=='node':
            n=db.get(GraphNode,row['node_id']);n.attributes={**n.attributes,'accession_number':'伪造文物号'}
        elif tamper=='receipt':db.get(GraphDocument,row['document_id']).sha256='0'*64
        else:
            from sqlalchemy import select
            relation=db.scalar(select(GraphRelation).where(GraphRelation.subject==row['node_id'],GraphRelation.predicate=='recorded_in'))
            relation.status='candidate'
        db.flush()
        assert len(published_records(db))==124
        assert row['node_id'] not in {r['node_id'] for r in published_records(db)}
        db.rollback()
