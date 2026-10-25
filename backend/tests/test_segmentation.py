"""Known-layout fixtures and real-MySQL candidate/provenance safeguards."""
import hashlib
import io
from PIL import Image, ImageDraw
import pytest
from app.segmentation import segment,SegmentOptions
from test_pipeline import client


def fixture_image(polarity='zhu',rows=2,cols=2):
    image=Image.new('RGB',(224,224),'#f8f4e8');d=ImageDraw.Draw(image);red='#b03129'
    if polarity=='bai':d.rectangle((20,20,204,204),fill=red);ink='#fffaf1'
    else:d.rectangle((20,20,204,204),outline=red,width=4);ink=red
    centres=[]
    for row in range(rows):
        for col in range(cols):
            cx=int(28+(col+.5)*168/cols);cy=int(28+(row+.5)*168/rows)
            halfw=int(168/cols*.25);halfh=int(168/rows*.31)
            d.line((cx-halfw,cy-halfh,cx+halfw,cy-halfh),fill=ink,width=7)
            d.line((cx,cy-halfh,cx,cy+halfh),fill=ink,width=7)
            d.line((cx-halfw,cy+halfh,cx+halfw,cy+halfh),fill=ink,width=7)
            centres.append((cx/224,cy/224))
    buf=io.BytesIO();image.save(buf,'PNG');return buf.getvalue(),centres


@pytest.mark.parametrize('polarity',['zhu','bai'])
def test_four_glyph_fixture(polarity):
    data,centres=fixture_image(polarity)
    original=hashlib.sha256(data).hexdigest()
    result=segment(data)
    assert result['polarity']==polarity
    assert result['layout']=='2x2',result
    assert len(result['glyphs'])==4
    for x,y in centres:
        assert sum(g['box'][0]<=x<=g['box'][2] and g['box'][1]<=y<=g['box'][3] for g in result['glyphs'])==1
    assert all(g['char']=='' and g['reviewed'] is False for g in result['glyphs'])
    assert result['character_labels_assigned'] is False and result['font_split_assigned'] is False
    assert result['ai_inference'] is False and hashlib.sha256(data).hexdigest()==original


def test_two_tall_characters_not_forced_into_four():
    data,_=fixture_image('bai',1,2)
    result=segment(data)
    assert result['layout']=='1x2' and len(result['glyphs'])==2,result


def test_explicit_layout_is_available_for_touching_characters():
    data,_=fixture_image('bai',1,2)
    result=segment(data,SegmentOptions(layout='2x2',polarity='bai'))
    assert result['layout']=='2x2' and result['human_review_required']
    assert len(result['glyphs'])==4


def test_blank_image_does_not_create_fake_character():
    image=Image.new('RGB',(80,80),'white');buf=io.BytesIO();image.save(buf,'PNG')
    result=segment(buf.getvalue())
    assert result['glyphs']==[] and result['status']=='no_foreground'


def test_huge_or_undecodable_input_rejected():
    with pytest.raises(ValueError):segment(b'not an image')


def test_api_candidates_can_be_saved_without_fake_text(client):
    data,_=fixture_image('bai')
    seal=client.post('/api/seals',files={'file':('segmentation-qa.png',data,'image/png')},
                     data={'source_kind':'synthetic_test','title':'自动分割QA合成图'}).json()
    source=seal['artifacts'][0]['id']
    payload={'source_artifact_id':source,'source_sha256':seal['sha256'],'layout':'auto','polarity':'auto'}
    r=client.post(f"/api/seals/{seal['id']}/segment-glyphs",json=payload)
    assert r.status_code==201,r.text
    result=r.json();assert len(result['result']['glyphs'])==4
    assert result['artifact']['metadata']['character_labels_assigned'] is False
    b={'source_artifact_id':source,'source_sha256':seal['sha256'],'annotator':'QA流程验证',
       'style':'未归类QA','proposal_artifact_id':result['artifact']['id'],'glyphs':result['result']['glyphs']}
    saved=client.post(f"/api/seals/{seal['id']}/glyphs",json=b)
    assert saved.status_code==201,saved.text
    assert saved.json()['document']['glyphs'][0]['char']==''
    assert client.get('/api/font/dataset.zip',params={'style':'未归类QA'}).status_code==422
    b['glyphs'][0]['reviewed']=True
    assert client.post(f"/api/seals/{seal['id']}/glyphs",json=b).status_code==422
    assert client.get(seal['original_url']).content==data
    payload['source_sha256']='0'*64
    assert client.post(f"/api/seals/{seal['id']}/segment-glyphs",json=payload).status_code==409
    b['glyphs'][0]['reviewed']=False;b['proposal_artifact_id']=source
    assert client.post(f"/api/seals/{seal['id']}/glyphs",json=b).status_code==422
    b['proposal_artifact_id']=result['artifact']['id'];b['style']='待归类'
    assert client.post(f"/api/seals/{seal['id']}/glyphs",json=b).status_code==201
    assert client.get('/api/font/dataset.zip',params={'style':'待归类'}).status_code==422
