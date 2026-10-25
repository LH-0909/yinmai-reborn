"""Batch unlabelled glyph proposals. Read originals, write a separate review set."""
import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
import csv
import hashlib
import io
import json
from pathlib import Path
import sys
import time
import cv2
from PIL import Image, ImageDraw, ImageOps

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app.segmentation import segment, SegmentOptions


def run(args):
    source=Path(args.source).resolve();out=Path(args.out).resolve()
    if not source.is_dir():raise ValueError('Source directory not found')
    if source==out or source in out.parents:raise ValueError('Output must be outside the original material directory')
    if out.exists():raise ValueError('Choose a new output directory; existing review results will not be overwritten')
    paths=sorted(p for p in source.rglob('*') if p.is_file() and not p.name.startswith('._') and p.suffix.lower() in {'.png','.jpg','.jpeg','.webp'})
    if args.limit:paths=paths[:args.limit]
    if not paths:raise ValueError('No images found')
    out.mkdir(parents=True);(out/'crops').mkdir();(out/'previews').mkdir()
    options=SegmentOptions(layout=args.layout,polarity=args.polarity,frame_inset=args.frame_inset)
    cv2.setNumThreads(1);started=time.perf_counter()
    def process(path):
        rel=path.relative_to(source).as_posix()
        try:
            data=path.read_bytes();sha=hashlib.sha256(data).hexdigest();ident=hashlib.sha256(rel.encode()+data).hexdigest()[:20]
            result=segment(data,options)
            with Image.open(io.BytesIO(data)) as image:original=ImageOps.exif_transpose(image).convert('RGB')
            overlay=original.copy();draw=ImageDraw.Draw(overlay);glyphs=[]
            for i,g in enumerate(result['glyphs']):
                x0,y0,x1,y1=g['box'];box=(int(x0*original.width),int(y0*original.height),
                    min(original.width,int(x1*original.width+.999)),min(original.height,int(y1*original.height+.999)))
                name=f'crops/{ident}-{i+1:02d}.png';crop=original.crop(box);crop.save(out/name)
                draw.rectangle((box[0],box[1],box[2]-1,box[3]-1),outline='#007ac2',width=max(1,original.width//180))
                glyphs.append({**g,'id':f'{ident}-{i+1:02d}','crop':name,
                    'crop_sha256':hashlib.sha256((out/name).read_bytes()).hexdigest(),
                    'style':'','font_split':'unassigned'})
            overlay.thumbnail((280,280));preview=f'previews/{ident}.jpg';overlay.save(out/preview,quality=88)
            return {'id':ident,'source_file':rel,'source_sha256':sha,'preview':preview,
                'layout':result['layout'],'polarity':result.get('polarity'),'status':result['status'],
                'warnings':result['warnings'],'alternatives':result['alternatives'],'glyphs':glyphs,
                'engine':result['engine'],'ai_inference':False,'human_review_required':True}
        except Exception as exc:
            return {'source_file':rel,'status':'error','error':type(exc).__name__+': '+str(exc),'glyphs':[]}
    rows=[]
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        for i,row in enumerate(pool.map(process,paths),1):
            rows.append(row)
            if i%500==0 or i==len(paths):print(json.dumps({'processed':i,'total':len(paths)}),flush=True)
    with (out/'manifest.jsonl').open('w',encoding='utf-8') as f:
        for row in rows:f.write(json.dumps(row,ensure_ascii=False)+'\n')
    columns=['id','source_file','source_sha256','crop','crop_sha256','suggested_layout','suggested_polarity',
             'x0','y0','x1','y1','character','style','box_reviewed','human_verified','font_split']
    with (out/'glyph-candidates.csv').open('w',encoding='utf-8-sig',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=columns);writer.writeheader()
        for row in rows:
            for g in row['glyphs']:
                writer.writerow({'id':g['id'],'source_file':row['source_file'],'source_sha256':row['source_sha256'],
                    'crop':g['crop'],'crop_sha256':g['crop_sha256'],'suggested_layout':row['layout'],
                    'suggested_polarity':g['polarity'],**dict(zip(['x0','y0','x1','y1'],g['box'])),
                    'character':'','style':'','box_reviewed':False,'human_verified':False,'font_split':'unassigned'})
    report={'task':'unlabelled_automatic_segmentation','source':str(source),'source_images_modified':False,
        'source_images':len(paths),'processed_images':sum(r['status']!='error' for r in rows),
        'error_images':sum(r['status']=='error' for r in rows),'candidate_crops':sum(len(r['glyphs']) for r in rows),
        'whole_seal_candidates':sum(r.get('layout')=='1x1' for r in rows),
        'no_candidate_images':sum(not r['glyphs'] for r in rows),
        'single_candidate_images':sum(len(r['glyphs'])==1 for r in rows),
        'multi_box_images':sum(len(r['glyphs'])>1 for r in rows),
        'layout_counts':dict(Counter(r.get('layout') or 'none' for r in rows)),
        'characters_assigned':0,'styles_assigned':0,'font_split_assigned':False,
        'all_candidates_require_human_review':True,'automatic_character_recognition':False,
        'method':'OpenCV colour, stamp/frame bounds, projection valleys and connected-stroke penalties',
        'options':options.model_dump(),'seconds':time.perf_counter()-started,
        'accuracy_measured':False,'limitation':'No expert character boxes available. 1x1 may retain several characters. Touching strokes, irregular layouts, frames and polarity can cause incorrect cuts.'}
    (out/'summary.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    (out/'data.js').write_text('window.SEGMENTATION_DATA='+json.dumps(rows,ensure_ascii=False).replace('</','<\\/')+';',encoding='utf-8')
    (out/'index.html').write_text(Path(__file__).with_name('segmentation_gallery.html').read_text(encoding='utf-8'),encoding='utf-8')
    (out/'使用说明.txt').write_text('自动分割产生的是待核对候选，不是已经识别的单字训练集。\n'
        '双击index.html查看原图上的候选框和对应裁图，可按布局/文件名筛选。\n'
        'crops保存原色裁图；manifest.jsonl和glyph-candidates.csv保留来源哈希与归一化坐标。\n'
        '文字、风格均留空，字体训练分组未划分。1x1可能仍包含多个字。\n'
        'Web工坊/font支持重新建议布局、单字边界调整、空释文草稿保存与人工核对。\n'
        '原始图片未移动或修改。该方法是OpenCV启发式，不是训练完成的字符检测模型。\n',encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False,indent=2),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source',required=True);p.add_argument('--out',required=True)
    p.add_argument('--layout',default='auto');p.add_argument('--polarity',default='auto')
    p.add_argument('--frame-inset',type=float,default=.025)
    p.add_argument('--workers',type=int,default=4);p.add_argument('--limit',type=int,default=0)
    args=p.parse_args()
    if not 1<=args.workers<=16 or args.limit<0:p.error('Workers must be 1..16, limit non-negative')
    run(args)
