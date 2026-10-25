"""Integration tests require a dedicated real MySQL schema. No mocks/SQLite."""
import io
import os
import cv2
import numpy as np
import pytest
import trimesh
from fastapi.testclient import TestClient
from sqlalchemy import select, text
from app.main import app
from app.database import Session, Seal, Artifact, engine
from app.processing import decode_image, encode_png, extract_mask
from app.mesh import make_seal

@pytest.fixture(scope='module')
def client():
    assert os.environ['MYSQL_DATABASE'].startswith('yinmai_qa_'), 'Run tests only in an isolated QA schema'
    with TestClient(app) as client:
        yield client

@pytest.fixture(scope='module')
def seal(client):
    sample=client.get('/api/test-sample')
    r=client.post('/api/seals',files={'file':('synthetic-test.png',sample.content,'image/png')},data={'title':'自动化合成测试','source_kind':'synthetic_test'})
    assert r.status_code==201, r.text
    return r.json()

def test_mysql_persistence(client,seal):
    assert client.get('/api/health').json()['database_engine']=='MySQL'
    engine.dispose()
    with Session() as db:
        stored=db.get(Seal,seal['id'])
        assert stored.title=='自动化合成测试'
        assert db.scalar(text('SELECT VERSION()')).startswith('8.4')
    assert client.get('/api/seals/'+seal['id']).json()['sha256']==seal['sha256']

def test_original_jpeg_bytes_are_preserved(client):
    from PIL import Image
    sample=Image.open(io.BytesIO(client.get('/api/test-sample').content))
    buf=io.BytesIO(); sample.save(buf,format='JPEG',quality=91);original=buf.getvalue()
    r=client.post('/api/seals',files={'file':('original.jpg',original,'image/jpeg')},data={'title':'原稿字节保存验证','source_kind':'synthetic_test'})
    assert r.status_code==201
    response=client.get(r.json()['original_url'])
    assert response.content==original
    assert response.headers['content-type']=='image/jpeg'

@pytest.mark.parametrize('operation',['extract','clean','repair'])
def test_processing_and_source_immutable(client,seal,operation):
    url=seal['original_url'];before=client.get(url).content
    result=client.post('/api/seals/'+seal['id']+'/process',json={'operation':operation,'strength':2,'mirror':True})
    assert result.status_code==200,result.text
    a=result.json(); assert a['metadata']['ai_inference'] is False
    assert a['metadata']['source_artifact_id']==seal['artifacts'][0]['id']
    data=client.get(a['url']).content
    assert cv2.imdecode(np.frombuffer(data,np.uint8),cv2.IMREAD_COLOR) is not None
    assert client.get(url).content==before

@pytest.mark.parametrize('style',['zhu','bai'])
@pytest.mark.parametrize('mirror',[True,False])
def test_real_stl_roundtrip(client,seal,style,mirror):
    r=client.post('/api/seals/'+seal['id']+'/reconstruct',json={'style':style,'mirror':mirror,'resolution':48,'width_mm':32,'base_mm':6,'relief_mm':1.5})
    assert r.status_code==200,r.text
    a=r.json(); assert a['metadata']['mirror'] is mirror
    mesh=trimesh.load(io.BytesIO(client.get(a['url']).content),file_type='stl',process=True)
    assert mesh.is_watertight and mesh.is_winding_consistent and mesh.volume>0
    np.testing.assert_allclose(mesh.extents,[32,32,7.5],atol=1e-5)
    assert a['metadata']['style']==style

def test_heightmap_mirror_and_zhu_bai_semantics():
    image=np.full((64,64,3),248,np.uint8)
    image[10:24,7:20]=(30,30,190)
    direct,_=make_seal(image,resolution=32,mirror=False,style='zhu')
    mirror,_=make_seal(image,resolution=32,mirror=True,style='zhu')
    negative,_=make_seal(image,resolution=32,mirror=False,style='bai')
    mask=cv2.resize(extract_mask(image),(32,32),interpolation=cv2.INTER_AREA)>=127.5
    def heights(mesh):
        vertices=mesh.vertices[mesh.vertices[:,2]>0]
        out=np.empty((32,32))
        for x,y,z in vertices:
            i=round((x+15)/30*31);j=round((y+15)/30*31);out[j,i]=z
        return out
    d,m,b=map(heights,[direct,mirror,negative])
    assert np.all(d[mask]>8.1) and np.all(d[~mask]==8)
    np.testing.assert_allclose(m,np.fliplr(d))
    np.testing.assert_allclose(d+b,np.full((32,32),17.2))

@pytest.mark.parametrize('body',[{'width_mm':0},{'resolution':1024},{'style':'invalid'},{'relief_mm':-1},{'base_mm':0}])
def test_invalid_mesh_inputs(client,seal,body):
    assert client.post('/api/seals/'+seal['id']+'/reconstruct',json=body).status_code==422

def test_foreign_source_rejected(client,seal):
    sample=client.get('/api/test-sample').content
    other=client.post('/api/seals',files={'file':('other.png',sample,'image/png')},data={'title':'第二测试','source_kind':'synthetic_test'}).json()
    assert client.post('/api/seals/'+seal['id']+'/process',json={'source_artifact_id':other['artifacts'][0]['id']}).status_code==400

@pytest.mark.parametrize('data',[b'not an image',b'',b'<svg></svg>'])
def test_invalid_upload(client,data):
    assert client.post('/api/seals',files={'file':('unsafe.png',data,'image/png')}).status_code==422

def test_ai_unavailable_is_honest(client,seal):
    count=len(client.get('/api/seals/'+seal['id']).json()['artifacts'])
    for task in ['recognition','restoration']:
        assert client.post('/api/seals/'+seal['id']+'/ai',json={'task':task}).status_code==503
    assert len(client.get('/api/seals/'+seal['id']).json()['artifacts'])==count
    assert client.post('/api/chat',json={'question':'如何制印？'}).status_code==503

def test_records_rename_knowledge(client,seal):
    r=client.post('/api/seals/'+seal['id']+'/records',json={'kind':'manufacturing','physical_trial':False,'material':'树脂','comment':'尚未试制'})
    assert r.status_code==201
    assert any(e['action']=='manufacturing' and e['details']['physical_trial'] is False for e in client.get('/api/events').json())
    assert client.patch('/api/seals/'+seal['id'],json={'title':'测试重命名'}).status_code==200
    assert client.get('/api/seals/'+seal['id']).json()['title']=='测试重命名'
    assert client.get('/api/knowledge',params={'q':'朱文'}).json()
    assert client.get('/api/knowledge',params={'q':"%' OR 1=1 --"}).json()==[]

def test_empty_image_reconstruction_rejected():
    with pytest.raises(ValueError):make_seal(np.full((64,64,3),255,np.uint8))

def test_file_ids_are_not_paths(client):
    assert client.get('/api/files/does-not-exist').status_code==404
    assert client.get('/api/seals/does-not-exist').status_code==404
