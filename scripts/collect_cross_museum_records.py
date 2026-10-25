from pathlib import Path
from urllib.request import Request,urlopen
from urllib.parse import urljoin,parse_qs,urlsplit
from datetime import datetime,timezone
from html import unescape
from PIL import Image
from harvest_official_seals import DOM,clean,ident,digest
import re,json,io,sys
sys.stdout.reconfigure(encoding='utf-8')
BASE=Path(__file__).resolve().parents[1]/'runtime/heritage-harvest';CACHE=BASE/'cross';ASSETS=BASE/'images'
CACHE.mkdir(parents=True,exist_ok=True);ASSETS.mkdir(parents=True,exist_ok=True)
SELECT=[
 dict(key='nmc-emperor',source_id='nmc',museum='中国国家博物馆',url='https://www.chnmuseum.cn/zp/zpml/csp/202111/t20211126_252412.shtml',label='皇帝之宝',material='碧玉',script='满汉合璧',image_scope='official_catalogue_image'),
 dict(key='nmc-chu',source_id='nmc',museum='中国国家博物馆',url='https://www.chnmuseum.cn/zp/zpml/csp/201812/t20181218_28017.shtml',label='君之信鉩',material='玉',script='古文大篆',image_scope='official_catalogue_image'),
 dict(key='nmc-dian',source_id='nmc',museum='中国国家博物馆',url='https://www.chnmuseum.cn/zp/zpml/kgfjp/202110/t20211028_251978.shtml',label='滇王之印',material='金',script='未明确提取',image_scope='official_catalogue_image'),
 dict(key='nyw-emperor',source_id='nyw',museum='南越王博物院',url='https://www.nywmuseum.org.cn/Collection/Details/?nid=47',label='文帝行玺',material='金',script='小篆',image_scope='official_catalogue_image'),
 dict(key='nyw-lady',source_id='nyw',museum='南越王博物院',url='https://www.nywmuseum.org.cn/Collection/Details/dcjp?nid=67',label='右夫人玺',material='金',script='篆文',image_scope='official_catalogue_image'),
]
def main():
    records=[]
    for choice in SELECT:
     path=CACHE/(choice['key']+'.html');raw=path.read_bytes();html=raw.decode('utf-8');dom=DOM(html).root
     if choice['source_id']=='nmc':
      metas={e.attrs.get('name'):e.attrs.get('content','') for e in dom.all(lambda e:e.tag=='meta')}
      title=metas['ArticleTitle'];record_id=metas['contentid']
      assert record_id==re.search(r'_(\d+)\.shtml$',choice['url'])[1]
      content_values=[clean(unescape(v)) for v in re.findall(r"var content='([^']*)';",html)]
      period=next((v for v in content_values if re.search('战国|秦|汉|明|清',v)),'官方条目未明确提取')
      dimensions=next((v for v in content_values if re.search('厘米|cm',v)),'官方条目未明确提取')
      paragraphs=[clean(e.text()) for e in dom.all(lambda e:e.tag=='p') if choice['label'] in e.text()]
      assert paragraphs,'no_body_transcription'
      body=paragraphs[0]
      image=re.search(r"data-src='([^']+)' data-caption='([^']+)'",html)
      assert image and unescape(image[2])==title
      image_url=urljoin(choice['url'],image[1]);caption=unescape(image[2])
     else:
      right=dom.all(lambda e:e.has('detail-r'));assert len(right)==1
      titles=right[0].all(lambda e:e.has('title'));title=clean(titles[0].text());record_id=parse_qs(urlsplit(choice['url']).query)['nid'][0]
      cont=right[0].all(lambda e:e.has('cont'));assert len(cont)==1
      ps=[clean(e.text()) for e in cont[0].all(lambda e:e.tag=='p') if clean(e.text())]
      period=ps[0];dimensions=ps[1];body=ps[-1]
      left=dom.all(lambda e:e.has('detail-l'));assert len(left)==1
      images=left[0].all(lambda e:e.tag=='img' and e.attrs.get('src','').startswith('https://file.nywmuseum.org.cn/'))
      assert images;image_url=images[0].attrs['src'];caption=title
     assert choice['label'] in body and choice['label'] in title.replace('玺','鉩') if choice['key']=='nmc-chu' else choice['label'] in body
     assert choice['material'] in body or choice['material'] in title
     stamp=ident('node','seal_object',choice['source_id']+':catalogue:'+record_id)
     preview=dict(status='unavailable',image_url=image_url,display_url='',caption=caption,width=0,height=0)
     try:
      with urlopen(Request(image_url,headers={'User-Agent':'Mozilla/5.0','Referer':choice['url']}),timeout=10) as response:
       image_raw=response.read(8_000_001);assert len(image_raw)<=8_000_000 and urlsplit(response.url).hostname==urlsplit(image_url).hostname
      photo=Image.open(io.BytesIO(image_raw));assert photo.width*photo.height<=25_000_000;photo.load();photo=photo.convert('RGB');photo.thumbnail((1024,1024));file=ASSETS/(stamp+'.webp');photo.save(file,'WEBP',quality=92)
      preview.update(status='available',display_url='/assets/seal-previews/'+stamp+'.webp',original_sha256=digest(image_raw),preview_sha256=digest(file.read_bytes()),width=photo.width,height=photo.height)
     except Exception as exc:preview['image_error_type']=type(exc).__name__
     record=dict(node_id=stamp,label=choice['label'],page_url=choice['url'],official_title=title,accession_number='',catalogue_record_id=record_id,identifier_label='官方条目号（非文物号）',museum=choice['museum'],source_id=choice['source_id'],document_id=ident('doc',choice['url']),page_sha256=digest(raw),fetched_at=datetime.fromtimestamp(path.stat().st_mtime,timezone.utc).isoformat(),period=period,period_conflict=False,material=choice['material'],dimensions=dimensions,script=choice['script'],transcription=choice['label'],transcription_scope='官方正文所引中文印文；原字保留，不作OCR或其他文字转写',source_excerpt=body[:180],source_excerpt_is_quote=True,source_excerpt_truncated=len(body)>180,maker='',image_match_basis='official_single_object_catalogue_image',usage='Local source-linked study preview; no training or public-commercial license asserted',interpretation_note='原文关于身世、用途和真伪的推测保留为原文观点，不提升为系统定论。',**preview)
     records.append(record);print(choice['museum'],title,'official catalogue id',record_id,'verified',flush=True)
    (BASE/'cross-records.json').write_text(json.dumps(records,ensure_ascii=False,indent=2),encoding='utf-8')

if __name__=='__main__':main()
