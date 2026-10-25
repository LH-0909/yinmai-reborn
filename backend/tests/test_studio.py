"""Real MySQL persistence and actual image/STL contracts for the new UI."""
import io
import os
import numpy as np
import pytest
import trimesh
from PIL import Image
from fastapi.testclient import TestClient
from app.main import app
from app.database import engine

@pytest.fixture(scope='module')
def client():
    assert os.environ['MYSQL_DATABASE'].startswith('yinmai_qa_')
    with TestClient(app) as c:yield c

def test_reference_catalog_has_explicit_unverified_provenance(client):
    data=client.get('/api/studio/catalog').json()
    assert data['total']==11
    assert all(r['provenance']=='user_supplied_ui_reference' and r['historical_metadata_verified'] is False for r in data['items'])
    assert all(r['era']=='秦汉' for r in client.get('/api/studio/catalog?era=秦汉').json()['items'])
    assert client.get('/api/studio/catalog?q=不存在的文字').json()['total']==0

def test_favorite_survives_connection_reopen_and_is_idempotent(client):
    for _ in range(2):assert client.put('/api/studio/favorites/han-01',json={'selected':True}).status_code==200
    engine.dispose()
    state=client.get('/api/studio/state').json()
    assert state['favorites'].count('han-01')==1
    assert state['counts']['favorites']==len(state['favorites'])
    assert client.put('/api/studio/favorites/missing',json={'selected':True}).status_code==404
    client.put('/api/studio/favorites/han-01',json={'selected':False})
    assert 'han-01' not in client.get('/api/studio/state').json()['favorites']

def test_profile_and_design_keep_chinese_parameters(client):
    assert client.patch('/api/studio/profile',json={'name':'测试藏家','bio':'测试个人简介'}).status_code==200
    r=client.post('/api/studio/designs',json={'title':'测试定制草案','parameters':{'ink':'#b82e25','depth':67,'edge':'云纹'}})
    assert r.status_code==201,r.text
    engine.dispose()
    state=client.get('/api/studio/state').json()
    assert state['profile']['name']=='测试藏家'
    assert next(d for d in state['designs'] if d['id']==r.json()['id'])['parameters']['depth']==67
    assert r.json()['source_kind']=='parameter_draft'
    assert client.post('/api/studio/designs',json={'title':'错误关联','parameters':{},'seal_id':'missing'}).status_code==422

@pytest.mark.parametrize('layout',['square','vertical','horizontal'])
def test_typeset_is_real_image_and_truthful_not_trained_style(client,layout):
    r=client.post('/api/studio/compose',json={'text':'印脉重生','layout':layout,'requested_style':'秦篆','ink':'#b82e25'})
    assert r.status_code==201,r.text
    data=r.json();assert data['ai_inference'] is False and data['style_model_applied'] is False
    assert data['seal']['source_kind']=='native_typeset'
    image=Image.open(io.BytesIO(client.get(data['seal']['original_url']).content))
    assert image.size==(512,512)
    a=np.asarray(image);assert np.count_nonzero((a[:,:,0]>a[:,:,1]+40)&(a[:,:,0]>a[:,:,2]+40))>1000
    meta=data['seal']['artifacts'][0]['metadata']
    assert meta['layout']==layout and meta['style_model_applied'] is False
    assert len(meta['content_font_sha256'])==64
    if layout=='square':
        for style in ['zhu','bai']:
            mesh=client.post('/api/seals/'+data['seal']['id']+'/reconstruct',json={'resolution':32,'style':style,'mirror':True,'base_mm':3})
            assert mesh.status_code==200,mesh.text
            artifact=mesh.json()
            decoded=trimesh.load(io.BytesIO(client.get(artifact['url']).content),file_type='stl',process=True)
            assert decoded.is_watertight and decoded.is_winding_consistent and decoded.volume>0
            assert artifact['metadata']['style']==style and artifact['metadata']['mirror'] is True

@pytest.mark.parametrize('body',[{'text':'abc'},{'text':'印 脉'},{'text':''},{'text':'印','ink':'wrong'},{'text':'印','layout':'wrong'},{'text':'印'*13}])
def test_typeset_rejects_unsupported_input_without_fake_result(client,body):
    assert client.post('/api/studio/compose',json=body).status_code==422

def test_negative_impression_and_geometry_keep_separate_provenance(client):
    result=client.post('/api/studio/compose',json={'text':'印脉','polarity':'bai'}).json()
    assert result['preview_polarity']=='bai'
    assert result['preview_url']!=result['seal']['original_url']
    positive=np.asarray(Image.open(io.BytesIO(client.get(result['seal']['original_url']).content)))
    negative=np.asarray(Image.open(io.BytesIO(client.get(result['preview_url']).content)))
    assert not np.array_equal(positive,negative)
    artifacts=result['seal']['artifacts']
    original=next(a for a in artifacts if a['kind']=='original')
    impression=next(a for a in artifacts if a['kind']=='ink_preview')
    assert original['metadata']['polarity_applied']=='zhu'
    assert impression['metadata']['polarity_applied']=='bai'
    assert impression['metadata']['source_artifact_id']==original['id']
    # Linked design changes remain drafts, even with a valid source image.
    saved=client.post('/api/studio/designs',json={'title':'修改白文草案','seal_id':result['seal']['id'],
          'parameters':{'layout':'vertical','customization':{'layout':'多字','depth':88}}})
    assert saved.status_code==201
    assert saved.json()['source_kind']=='parameter_draft'
    assert saved.json()['parameters']['layout']=='vertical'


def test_stroke_and_border_controls_change_actual_image_and_geometry_source(client):
    def render(**options):
        response=client.post('/api/studio/compose',json={'text':'印脉',**options})
        assert response.status_code==201,response.text
        result=response.json()
        pixels=np.asarray(Image.open(io.BytesIO(client.get(result['seal']['original_url']).content))).astype(int)
        ink=(pixels[:,:,0]>pixels[:,:,1]+40)&(pixels[:,:,0]>pixels[:,:,2]+40)
        return result,ink
    normal,normal_ink=render(border=False,stroke_px=0)
    bold,bold_ink=render(border=False,stroke_px=3,polarity='bai')
    assert bold_ink.sum()>normal_ink.sum()*1.2
    assert not normal_ink[:35,:].any() and not bold_ink[:35,:].any()
    framed,framed_ink=render(border=True,stroke_px=3)
    assert framed_ink[24:35,24:489].sum()>1000
    original=next(a for a in bold['seal']['artifacts'] if a['kind']=='original')
    assert original['metadata']['stroke_px']==3 and original['metadata']['border'] is False
    assert original['metadata']['style_model_applied'] is False
    mesh=client.post('/api/seals/'+bold['seal']['id']+'/reconstruct',json={'resolution':48,'style':'bai','mirror':True,'source_artifact_id':original['id']})
    assert mesh.status_code==200,mesh.text
    assert mesh.json()['metadata']['source_artifact_id']==original['id']
    assert mesh.json()['metadata']['watertight'] is True
    assert client.post('/api/studio/compose',json={'text':'印','stroke_px':9}).status_code==422
