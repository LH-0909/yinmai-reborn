"""Read-only image corpus audit and page-grouped splits; never invent OCR labels."""
import argparse
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
import csv
import hashlib
import io
import json
from pathlib import Path
import random
import re
import statistics
from PIL import Image, ImageDraw, ImageFont, ImageOps
import numpy as np

SUFFIXES={'.png','.jpg','.jpeg','.webp','.bmp','.tif','.tiff'}

def page_group(path):
    match=re.match(r'(.+)_p(\d+)_[^_]+$',path.stem)
    return f'{match[1]}_p{match[2]}' if match else path.stem

def inspect(path):
    result={'path':str(path),'name':path.name,'page_group':page_group(path),'bytes':path.stat().st_size}
    try:
        data=path.read_bytes()
        with Image.open(io.BytesIO(data)) as image:
            image.load()
            result.update(width=image.width,height=image.height,mode=image.mode,format=image.format)
            rgb=image.convert('RGB')
            result['sha256']=hashlib.sha256(data).hexdigest()
            result['pixel_sha256']=hashlib.sha256(str(rgb.size).encode()+rgb.tobytes()).hexdigest()
            small=np.asarray(rgb.resize((64,64)),dtype=np.float32)
            gray=small.mean(2)
            result['contrast_std']=round(float(gray.std()),3)
            result['red_ratio']=round(float(((small[:,:,0]>small[:,:,1]+25)&(small[:,:,0]>small[:,:,2]+25)).mean()),5)
            result['low_contrast_flag']=bool(gray.std()<8)
            result['eligible']=min(image.size)>=32
            result['status']='valid' if result['eligible'] else 'too_small'
    except Exception as error:
        result.update(status='decode_error',eligible=False,error=type(error).__name__+': '+str(error)[:150])
    return result

def run(source,out,workers=8):
    source=Path(source).resolve();out=Path(out).resolve()
    if source==out or source in out.parents:raise ValueError('Audit output must be outside the original corpus')
    out.mkdir(parents=True,exist_ok=True)
    all_files=sorted(p for p in source.rglob('*') if p.is_file())
    sidecars=[p for p in all_files if p.name.startswith('._') or p.name=='.DS_Store']
    sidecar_set=set(sidecars)
    images=[p for p in all_files if p.suffix.lower() in SUFFIXES and p not in sidecar_set]
    others=[str(p.relative_to(source)) for p in all_files if p not in sidecar_set and p.suffix.lower() not in SUFFIXES]
    with ThreadPoolExecutor(max_workers=workers) as pool:
        rows=[]
        for i,row in enumerate(pool.map(inspect,images),1):
            rows.append(row)
            if i%2000==0:print(f'Audited {i}/{len(images)} images',flush=True)
    canonical={};duplicates=[]
    for row in rows:
        if not row['eligible']:continue
        digest=row['pixel_sha256']
        if digest in canonical:
            row.update(eligible=False,status='exact_duplicate',duplicate_of=canonical[digest]);duplicates.append(row['name'])
        else:canonical[digest]=row['name']
    for row in rows:
        if row['eligible']:
            bucket=int(hashlib.sha256(('yinmai-v1:'+row['page_group']).encode()).hexdigest()[:8],16)%100
            row['split']='train' if bucket<80 else 'validation' if bucket<90 else 'test'
        else:row['split']='excluded'
    with (out/'manifest.jsonl').open('w',encoding='utf-8') as f:
        for row in rows:f.write(json.dumps(row,ensure_ascii=False)+'\n')
    for split in ['train','validation','test']:
        selected=[r for r in rows if r['split']==split]
        (out/(split+'.jsonl')).write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in selected),encoding='utf-8')
    valid=[r for r in rows if 'width' in r]
    split_counts=dict(Counter(r['split'] for r in rows));groups={s:set(r['page_group'] for r in rows if r['split']==s) for s in ['train','validation','test']}
    assert not(groups['train']&groups['validation'] or groups['train']&groups['test'] or groups['test']&groups['validation'])
    digests={s:set(r['pixel_sha256'] for r in rows if r['split']==s) for s in groups}
    assert not(digests['train']&digests['validation'] or digests['train']&digests['test'] or digests['test']&digests['validation'])
    summary={'source':str(source),'total_files':len(all_files),'apple_sidecars_excluded':len(sidecars),'candidate_images':len(images),
        'decodable_images':len(valid),'status_counts':dict(Counter(r['status'] for r in rows)),'eligible_unique_images':sum(r['eligible'] for r in rows),
        'split_counts':split_counts,'page_groups_per_split':{k:len(v) for k,v in groups.items()},'page_group_overlap':False,'exact_pixel_overlap':False,
        'width_range':[min(r['width'] for r in valid),max(r['width'] for r in valid)],'height_range':[min(r['height'] for r in valid),max(r['height'] for r in valid)],
        'median_size':[statistics.median(r['width'] for r in valid),statistics.median(r['height'] for r in valid)],
        'low_contrast_flags':sum(r.get('low_contrast_flag',False) for r in rows),'red_pixel_ratio_median':statistics.median(r['red_ratio'] for r in valid),
        'non_image_files':others,'ocr_labels_found':False,'paired_restoration_targets_found':False,'split_unit':'filename source-page; duplicates excluded by decoded RGB pixel hash',
        'limitation':'No OCR transcription, character boxes, clean restoration targets or source-license manifest found. Split does not guarantee independence between different pages from the same book.'}
    (out/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
    font_path=Path('C:/Windows/Fonts/simsun.ttc')
    font=ImageFont.truetype(str(font_path),15) if font_path.exists() else ImageFont.load_default()
    sampled=random.Random(19).sample(valid,min(30,len(valid)))
    sheet=Image.new('RGB',(1200,1200),'#e8dfce');draw=ImageDraw.Draw(sheet)
    for i,row in enumerate(sampled):
        with Image.open(row['path']) as im:im=ImageOps.contain(im.convert('RGB'),(182,200))
        x=(i%6)*200+(200-im.width)//2;y=(i//6)*240+5
        sheet.paste(im,(x,y));draw.text(((i%6)*200+5,(i//6)*240+209),row['name'],font=font,fill='#332414')
    sheet.save(out/'contact-sheet.png')
    print(json.dumps(summary,ensure_ascii=False,indent=2),flush=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--source',required=True);parser.add_argument('--out',required=True);parser.add_argument('--workers',type=int,default=8)
    a=parser.parse_args();run(a.source,a.out,a.workers)
