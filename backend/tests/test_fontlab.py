"""Real MySQL glyph provenance, split isolation and actual generator checks."""
import hashlib
import io
import json
import zipfile
import numpy as np
from PIL import Image, ImageDraw
import pytest
from pydantic import ValidationError
from app import fontlab
from app.database import Session, engine
from test_pipeline import client


@pytest.fixture(scope='module')
def glyph_source(client):
    # Explicit flow fixture in isolated QA database, never actual expert labels.
    image=Image.new('RGB',(100,100),'white');draw=ImageDraw.Draw(image)
    draw.rectangle((20,40,75,55),fill='#a7352d')
    buf=io.BytesIO();image.save(buf,'PNG')
    r=client.post('/api/seals',files={'file':('glyph-flow-fixture.png',buf.getvalue(),'image/png')},
                  data={'title':'字形流程QA，非专家标注','source_kind':'user_upload'})
    assert r.status_code==201
    return r.json()


def body(seal):
    return {'source_artifact_id':seal['artifacts'][0]['id'],'source_sha256':seal['sha256'],
            'style':'QA字形流程','annotator':'QA流程验证','notes':'仅验证流程，非印谱字形真值',
            'glyphs':[{'char':'一','box':[.1,.2,.9,.8],'polarity':'zhu','mirrored':False,'reviewed':False}]}


def test_drafts_are_not_exported(client,glyph_source):
    r=client.post(f"/api/seals/{glyph_source['id']}/glyphs",json=body(glyph_source))
    assert r.status_code==201,r.text
    assert r.json()['document']['glyphs'][0]['reviewed'] is False
    assert client.get('/api/font/dataset.zip',params={'style':'QA字形流程'}).status_code==422


def test_confirmed_glyph_export_is_hashed_and_source_immutable(client,glyph_source):
    before=client.get(glyph_source['original_url']).content
    b=body(glyph_source);b['glyphs'][0]['reviewed']=True
    r=client.post(f"/api/seals/{glyph_source['id']}/glyphs",json=b)
    assert r.status_code==201,r.text
    engine.dispose()
    latest=client.get(f"/api/seals/{glyph_source['id']}/glyphs/latest").json()
    assert latest['document']['glyphs']==b['glyphs']
    response=client.get('/api/font/dataset.zip',params={'style':'QA字形流程'})
    assert response.status_code==200,response.text
    with zipfile.ZipFile(io.BytesIO(response.content)) as z:
        rows=[json.loads(s) for s in z.read('manifest.jsonl').decode().splitlines()]
        assert len(rows)==1
        row=rows[0];target=z.read(row['target'])
        assert hashlib.sha256(target).hexdigest()==row['target_sha256']
        assert row['source_sha256']==glyph_source['sha256'] and row['char']=='一'
        assert row['split']==fontlab.split_for_char('一') and row['provenance']=='human_labelled_seal_crop'
        image=Image.open(io.BytesIO(target));assert image.size==(128,128)
        assert set(np.unique(np.asarray(image)))>={0,255}
    assert client.get(glyph_source['original_url']).content==before


@pytest.mark.parametrize('change',[
    {'glyphs':[{'char':'两个','box':[0,0,.5,.5]}]},
    {'glyphs':[{'char':'印','box':[.8,0,.2,.5]}]},
    {'glyphs':[{'char':'印','box':[-.1,0,.5,.5]}]},
    {'annotator':'   '}, {'style':'   '}
])
def test_invalid_glyph_labels_rejected(client,glyph_source,change):
    b=body(glyph_source);b.update(change)
    assert client.post(f"/api/seals/{glyph_source['id']}/glyphs",json=b).status_code==422


def test_source_tamper_and_non_original_rejected(client,glyph_source):
    b=body(glyph_source);b['source_sha256']='0'*64
    assert client.post(f"/api/seals/{glyph_source['id']}/glyphs",json=b).status_code==409
    r=client.post(f"/api/seals/{glyph_source['id']}/process",json={'operation':'extract'})
    b=body(glyph_source);b['source_artifact_id']=r.json()['id']
    assert client.post(f"/api/seals/{glyph_source['id']}/glyphs",json=b).status_code==422


def test_synthetic_qa_never_enters_font_training(client):
    data=client.get('/api/test-sample').content
    seal=client.post('/api/seals',files={'file':('synthetic.png',data,'image/png')},
                     data={'source_kind':'synthetic_test','title':'字形合成测试'}).json()
    b=body(seal);b['style']='合成字形不可训练';b['glyphs'][0].update(box=[.1,.1,.9,.9],reviewed=True)
    assert client.post(f"/api/seals/{seal['id']}/glyphs",json=b).status_code==201
    assert client.get('/api/font/dataset.zip',params={'style':b['style']}).status_code==422
    assert b['style'] not in {s['style'] for s in client.get('/api/font/status').json()['styles']}


def test_actual_generator_records_demo_provenance(client):
    model=next((m for m in fontlab.models() if m['demo_only']),None)
    if not model:pytest.skip('No local font pipeline demonstration model')
    result=client.post('/api/font/generate',json={'model_id':model['id'],'text':'印脉重生'})
    assert result.status_code==201,result.text
    item=result.json()['artifact'];meta=item['metadata']
    assert meta['demo_only'] is True and meta['ai_inference'] is True
    assert meta['training_provenance']=='local_font_rasterization_demo'
    assert meta['historical_authenticity_verified'] is False
    assert Image.open(io.BytesIO(client.get(item['url']).content)).size==(592,160)
    assert client.post('/api/font/generate',json={'model_id':'nonexistent','text':'印'}).status_code==422
    assert client.post('/api/font/generate',json={'model_id':model['id'],'text':'?'}).status_code==422


def test_character_split_does_not_depend_on_style():
    assert all(fontlab.split_for_char(c) in {'train','validation','test'} for c in '印脉重生')
