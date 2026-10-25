"""Real MySQL, actual trained denoiser, human-draft and source integrity checks."""
import csv
import hashlib
import io
import json
import cv2
import numpy as np
import pytest
from PIL import Image
from app import lab
from app.database import engine,Session
from sqlalchemy import text
from test_pipeline import client

@pytest.fixture(scope='module')
def small_seal(client):
    data=client.get('/api/test-sample').content
    image=cv2.imdecode(np.frombuffer(data,np.uint8),cv2.IMREAD_COLOR)
    data=cv2.imencode('.png',cv2.resize(image,(128,128)))[1].tobytes()
    response=client.post('/api/seals',files={'file':('lab-synthetic-qa.png',data,'image/png')},
                         data={'title':'增强与标注QA合成图','source_kind':'synthetic_test'})
    assert response.status_code==201
    return response.json()

def payload(seal):
    return {'source_artifact_id':seal['artifacts'][0]['id'],'source_sha256':seal['sha256'],
            'annotator':'QA流程验证','transcription':'','legibility':'unsure','notes':'合成图流程检查，非历史释文',
            'mask_mode':'unlabeled','strokes':[]}

def test_actual_denoiser_is_recorded_and_preserves_source(client,small_seal):
    assert client.get('/api/lab/status').json()['enhancement']['available']
    original=client.get(small_seal['original_url']).content
    result=client.post('/api/seals/'+small_seal['id']+'/enhance',json={})
    assert result.status_code==200,result.text
    item=result.json();meta=item['metadata'];output=client.get(item['url']).content
    assert item['kind']=='enhancement' and meta['experimental_only'] and meta['ai_inference']
    assert meta['missing_strokes_restored'] is False and meta['training_steps']==400
    assert meta['source_artifact_id']==small_seal['artifacts'][0]['id']
    assert hashlib.sha256(lab.MODEL.read_bytes()).hexdigest()==meta['model_sha256']
    assert hashlib.sha256(output).hexdigest()==meta['sha256']
    assert original!=output and client.get(small_seal['original_url']).content==original
    assert Image.open(io.BytesIO(output)).size==(128,128)

def test_blank_text_is_not_auto_filled_or_promoted(client,small_seal):
    body=payload(small_seal);body['ground_truth_verified']=True
    result=client.post('/api/seals/'+small_seal['id']+'/annotations',json=body)
    assert result.status_code==201,result.text
    document=result.json()['document']
    assert document['transcription']=='' and document['strokes']==[]
    assert document['review_state']=='draft' and document['ground_truth_verified'] is False
    assert document['ai_inference'] is False and document['auto_use_for_training'] is False
    assert result.json()['mask'] is None
    assert json.loads(client.get(result.json()['annotation']['url']).content)==document

def test_hand_mask_is_binary_and_annotations_persist_as_versions(client,small_seal):
    body=payload(small_seal);body.update(mask_mode='drawn',strokes=[{'width':.08,'points':[[.3,.3],[.6,.6]]}])
    result=client.post('/api/seals/'+small_seal['id']+'/annotations',json=body)
    assert result.status_code==201,result.text
    mask=Image.open(io.BytesIO(client.get(result.json()['mask']['url']).content))
    pixels=np.array(mask)
    assert mask.mode=='L' and mask.size==(128,128)
    assert set(np.unique(pixels))=={0,255} and pixels[0,0]==0 and pixels[60,60]==255
    engine.dispose()
    latest=client.get('/api/seals/'+small_seal['id']+'/annotations/latest').json()
    assert latest['annotation']['id']==result.json()['annotation']['id']
    assert latest['document']['strokes']==body['strokes']
    seal=client.get('/api/seals/'+small_seal['id']).json()
    assert len([a for a in seal['artifacts'] if a['kind']=='annotation'])>=2
    with Session() as db:
        precision=db.scalar(text("SELECT DATETIME_PRECISION FROM information_schema.COLUMNS WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='artifacts' AND COLUMN_NAME='created_at'"))
        assert precision==6,'Same-second annotation versions need sub-second timestamp precision'

@pytest.mark.parametrize('change',[
    {'annotator':'   '}, {'mask_mode':'drawn','strokes':[]},
    {'mask_mode':'drawn','strokes':[{'width':.03,'points':[[1.1,.5]]}]},
    {'mask_mode':'unlabeled','strokes':[{'width':.03,'points':[[.5,.5]]}]}])
def test_invalid_human_annotations_rejected(client,small_seal,change):
    body=payload(small_seal);body.update(change)
    assert client.post('/api/seals/'+small_seal['id']+'/annotations',json=body).status_code==422

def test_wrong_hash_and_processed_source_cannot_become_manual_ground_truth(client,small_seal):
    body=payload(small_seal);body['source_sha256']='0'*64
    assert client.post('/api/seals/'+small_seal['id']+'/annotations',json=body).status_code==409
    derived=client.post('/api/seals/'+small_seal['id']+'/process',json={'operation':'clean'}).json()
    body=payload(small_seal);body['source_artifact_id']=derived['id']
    assert client.post('/api/seals/'+small_seal['id']+'/annotations',json=body).status_code==422

def test_absent_model_and_large_image_fail_honestly(client,small_seal,monkeypatch,tmp_path):
    monkeypatch.setattr(lab,'MODEL',tmp_path/'absent.pt')
    assert client.get('/api/lab/status').json()['enhancement']['available'] is False
    before=len(client.get('/api/seals/'+small_seal['id']).json()['artifacts'])
    assert client.post('/api/seals/'+small_seal['id']+'/enhance',json={}).status_code==503
    assert len(client.get('/api/seals/'+small_seal['id']).json()['artifacts'])==before
    with pytest.raises(ValueError):lab.enhance(np.zeros((513,100,3),dtype=np.uint8))

def test_corpus_allowlist_idempotent_import_and_immutable_hash(client,monkeypatch,tmp_path):
    source=tmp_path/'corpus';source.mkdir();image=source/'qa_p0001_01.png'
    Image.new('RGB',(80,90),'#e9dabc').save(image)
    digest=hashlib.sha256(image.read_bytes()).hexdigest()
    seed=tmp_path/'seed.csv'
    with seed.open('w',newline='',encoding='utf-8-sig') as f:
        writer=csv.DictWriter(f,fieldnames=['file','sha256','page_group']);writer.writeheader()
        writer.writerow({'file':str(image),'sha256':digest,'page_group':'qa_p0001'})
    monkeypatch.setenv('TRAINING_CORPUS_PATH',str(source));monkeypatch.setattr(lab,'SEED',seed)
    row=client.get('/api/lab/corpus').json()[0]
    assert row['split']=='validation' and 'path' not in row
    preview=client.get(row['preview_url']);assert hashlib.sha256(preview.content).hexdigest()==digest
    a=client.post('/api/lab/corpus/'+row['id']+'/import').json()
    b=client.post('/api/lab/corpus/'+row['id']+'/import').json()
    assert a['id']==b['id'] and a['sha256']==digest
    assert a['artifacts'][0]['metadata']['dataset_split']=='validation'
    assert hashlib.sha256(image.read_bytes()).hexdigest()==digest
    assert client.get('/api/lab/corpus/not-a-candidate/preview').status_code==422
    image.write_bytes(b'changed original for tamper-test only')
    assert client.get(row['preview_url']).status_code==422
    monkeypatch.setenv('TRAINING_CORPUS_PATH',str(tmp_path/'different-root'))
    (tmp_path/'different-root').mkdir()
    assert client.get('/api/lab/corpus').status_code==503

def test_bundled_images_work_without_original_d_drive_path(monkeypatch,tmp_path):
    project=tmp_path/'project';root=project/'training-data/images'
    folder=root/'validation';folder.mkdir(parents=True)
    image=folder/'portable_p0001_01.png';Image.new('RGB',(64,80),'#efdfc6').save(image)
    digest=hashlib.sha256(image.read_bytes()).hexdigest()
    with (project/'training-data/annotation-seed.csv').open('w',newline='',encoding='utf-8-sig') as f:
        writer=csv.DictWriter(f,fieldnames=['file','sha256','page_group']);writer.writeheader()
        writer.writerow({'file':'validation/'+image.name,'sha256':digest,'page_group':'portable_p0001'})
    monkeypatch.delenv('TRAINING_CORPUS_PATH',raising=False);monkeypatch.delenv('ANNOTATION_SEED_PATH',raising=False)
    monkeypatch.setattr(lab,'ROOT',project)
    row=lab.corpus_entries()[0]
    assert lab.corpus_root()==root.resolve()
    assert hashlib.sha256(lab.corpus_file(row['id'])[1]).hexdigest()==digest
