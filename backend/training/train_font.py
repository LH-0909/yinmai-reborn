"""Paired character-to-character font style baseline (not a denoiser).

One model per style. No pre-trained checkpoints. No few-shot claim. Python3.8+.
"""
import argparse
import hashlib
import json
from pathlib import Path
import random
import time

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from fontTools.ttLib import TTFont
import torch
from torch import nn
from torch.nn import functional as F


def digest(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def split_for_char(char):
    n = int(hashlib.sha256(('yinmai-font-v1:'+char).encode()).hexdigest()[:8],16) % 10
    return 'test' if n == 0 else 'validation' if n == 1 else 'train'


def cmap(path):
    with TTFont(str(path),fontNumber=0) as f: return set(f.getBestCmap())


def render(font,char):
    image = Image.new('L',(128,128),0); box = font.getbbox(char)
    w,h = box[2]-box[0],box[3]-box[1]
    ImageDraw.Draw(image).text(((128-w)//2-box[0],(128-h)//2-box[1]),char,font=font,fill=255)
    return image


def prepare_demo(args):
    root=Path(args.dataset); root.mkdir(parents=True,exist_ok=True)
    if (root/'manifest.jsonl').exists(): raise ValueError('Dataset already exists; choose a new directory')
    source=Path(args.source_font);target=Path(args.target_font)
    available = cmap(source) & cmap(target)
    chars=[]
    for a in range(0xb0,0xd8):
        for b in range(0xa1,0xff):
            try: c=bytes([a,b]).decode('gb2312')
            except UnicodeDecodeError: continue
            if ord(c) in available: chars.append(c)
    chars=random.Random(args.seed).sample(chars,min(args.demo_characters,len(chars)))
    for c in '印脉重生':
        if c not in chars and ord(c) in available: chars.append(c)
    font=ImageFont.truetype(str(target),104); (root/'targets').mkdir(exist_ok=True)
    rows=[]
    for c in chars:
        path=root/'targets'/('u%X.png'%ord(c)); render(font,c).save(path)
        rows.append({'id':'u%X'%ord(c),'char':c,'target':path.relative_to(root).as_posix(),
            'target_sha256':digest(path),'style':'本机宋体风格流程验证（非印谱）','split':split_for_char(c),
            'reviewed':True,'provenance':'local_font_rasterization_demo'})
    (root/'manifest.jsonl').write_text('\n'.join(json.dumps(r,ensure_ascii=False) for r in rows)+'\n',encoding='utf-8')
    print(json.dumps({'demo_characters':len(rows),'source_font_sha256':digest(source),
        'target_font_sha256':digest(target),'provenance':'local_font_rasterization_demo'}),flush=True)


class Block(nn.Module):
    def __init__(self,a,b):
        super().__init__(); self.layers=nn.Sequential(nn.Conv2d(a,b,3,padding=1),nn.GroupNorm(4,b),nn.SiLU(),
            nn.Conv2d(b,b,3,padding=1),nn.GroupNorm(4,b),nn.SiLU())
    def forward(self,x): return self.layers(x)


class GlyphUNet(nn.Module):
    def __init__(self):
        super().__init__()
        self.e1=Block(1,16);self.e2=Block(16,32);self.e3=Block(32,64);self.mid=Block(64,96)
        self.d3=Block(96+64,64);self.d2=Block(64+32,32);self.d1=Block(32+16,16)
        self.out=nn.Conv2d(16,1,1)
    def forward(self,x):
        a=self.e1(x);b=self.e2(F.avg_pool2d(a,2));c=self.e3(F.avg_pool2d(b,2))
        h=self.mid(F.avg_pool2d(c,2))
        h=self.d3(torch.cat([F.interpolate(h,scale_factor=2.,mode='nearest'),c],1))
        h=self.d2(torch.cat([F.interpolate(h,scale_factor=2.,mode='nearest'),b],1))
        h=self.d1(torch.cat([F.interpolate(h,scale_factor=2.,mode='nearest'),a],1))
        return torch.sigmoid(self.out(h))


def losses(pred,target):
    weights=1+3*target
    bce=(F.binary_cross_entropy(pred.clamp(1e-5,1-1e-5),target,reduction='none')*weights).mean()
    dx=(pred[:,:,:,1:]-pred[:,:,:,:-1])-(target[:,:,:,1:]-target[:,:,:,:-1])
    dy=(pred[:,:,1:,:]-pred[:,:,:-1,:])-(target[:,:,1:,:]-target[:,:,:-1,:])
    return bce+.5*(dx.abs().mean()+dy.abs().mean())


def evaluate(model,data,batch=16):
    model.eval();src,target=data;err=0.;intersection=0.;union=0.;n=0
    with torch.no_grad():
        for i in range(0,len(src),batch):
            pred=model(src[i:i+batch]);truth=target[i:i+batch]
            err+=float((pred-truth).abs().sum());n+=truth.numel()
            intersection+=float(((pred>.5)&(truth>.5)).sum());union+=float(((pred>.5)|(truth>.5)).sum())
    return {'pixel_l1':err/n,'foreground_iou':intersection/max(union,1)}


def train(args):
    if not torch.cuda.is_available(): raise RuntimeError('CUDA is required; no silent CPU fallback')
    if min(args.epochs,args.batch,args.eval_every) < 1: raise ValueError('Epochs/batch/eval-every must be positive')
    root=Path(args.dataset).resolve();out=Path(args.out).resolve()
    if (out/'model.json').exists(): raise ValueError('Model already exists; use a new output directory')
    rows=[json.loads(l) for l in (root/'manifest.jsonl').read_text(encoding='utf-8').splitlines() if l.strip()]
    if not rows: raise ValueError('Empty dataset; annotate characters first')
    provenances={r.get('provenance') for r in rows};styles={r.get('style') for r in rows}
    if len(provenances)!=1 or not provenances <= {'human_labelled_seal_crop','local_font_rasterization_demo'}:
        raise ValueError('Do not mix seal targets, demos or unverified provenance')
    if len(styles)!=1: raise ValueError('One style per model; export a single style group')
    font_path=Path(args.source_font);available=cmap(font_path);font=ImageFont.truetype(str(font_path),104)
    groups={k:[] for k in ['train','validation','test']};seen_pixels={}
    for r in rows:
        c=r['char']
        if len(c)!=1 or ord(c) not in available: raise ValueError('Missing content glyph: '+c)
        if r.get('reviewed') is not True: raise ValueError('Unreviewed glyph cannot enter training')
        if r['split'] != split_for_char(c): raise ValueError('Split mismatch; use deterministic character split')
        path=(root/r['target']).resolve()
        if root not in path.parents: raise ValueError('Target outside dataset')
        if digest(path)!=r['target_sha256']: raise ValueError('Changed target: '+c)
        im=Image.open(path).convert('L')
        if im.size!=(128,128): raise ValueError('Expected 128px normalized target')
        pixel=hashlib.sha256(im.tobytes()).hexdigest()
        if pixel in seen_pixels and seen_pixels[pixel]!=c: raise ValueError('Same pixels assigned to different characters')
        seen_pixels[pixel]=c
        src=torch.from_numpy(np.array(render(font,c),dtype=np.float32)[None]/255.)
        target=torch.from_numpy(np.array(im,dtype=np.float32)[None]/255.)
        groups[r['split']].append((src,target,r))
    for k in groups:
        unique={r[2]['char'] for r in groups[k]}
        minimum=32 if k=='train' else 8
        if len(unique)<minimum: raise ValueError(f'{k} has only {len(unique)} labelled characters; need at least {minimum} for a pipeline baseline (not a quality guarantee)')
    torch.set_num_threads(4);random.seed(args.seed);np.random.seed(args.seed);torch.manual_seed(args.seed)
    torch.cuda.manual_seed_all(args.seed);torch.backends.cudnn.benchmark=False
    torch.backends.cudnn.deterministic=True
    data={k:(torch.stack([r[0] for r in rows]).cuda(),torch.stack([r[1] for r in rows]).cuda()) for k,rows in groups.items()}
    model=GlyphUNet().cuda();optimizer=torch.optim.Adam(model.parameters(),lr=args.lr)
    src,target=data['train'];best=float('inf');state=None;history=[];step=0;seen=set()
    out.mkdir(parents=True,exist_ok=True);torch.cuda.reset_peak_memory_stats();started=time.perf_counter()
    for epoch in range(1,args.epochs+1):
        model.train();order=torch.randperm(len(src),device='cuda')
        for i in range(0,len(src),args.batch):
            index=order[i:i+args.batch];seen.update(index.cpu().tolist());step+=1
            optimizer.zero_grad(set_to_none=True);loss=losses(model(src[index]),target[index]);loss.backward();optimizer.step()
        if epoch==1 or epoch%args.eval_every==0 or epoch==args.epochs:
            val=evaluate(model,data['validation']);record={'epoch':epoch,'step':step,'train_loss':float(loss),'validation':val}
            history.append(record);print(json.dumps(record),flush=True)
            if val['pixel_l1']<best: best=val['pixel_l1'];state={k:v.detach().cpu().clone() for k,v in model.state_dict().items()}
    torch.cuda.synchronize();seconds=time.perf_counter()-started
    model.load_state_dict(state);model.eval();test=evaluate(model,data['test'])
    test_src,test_target=data['test']
    baseline=evaluate(nn.Identity().cuda(),data['test'])
    with torch.no_grad(): predictions=model(test_src[:12]).cpu()
    sheet=Image.new('RGB',(3*144,40+len(predictions)*144),'#eee9df');draw=ImageDraw.Draw(sheet)
    for i,title in enumerate(['Content input','Generated','Target (held-out)']):draw.text((i*144+4,12),title,fill='black')
    for j,pred in enumerate(predictions):
        for i,im in enumerate([test_src[j].cpu(),pred,test_target[j].cpu()]):
            im=Image.fromarray((255*(1-im[0].clamp(0,1).numpy())).round().astype('uint8'),'L')
            sheet.paste(im,(i*144+8,40+j*144))
    sheet.save(out/'held-out-comparison.png')
    model=model.cpu().eval();scripted=torch.jit.script(model);scripted.save(str(out/'generator.ts'))
    with torch.no_grad():
        probe=torch.rand(2,1,128,128);assert torch.allclose(scripted(probe),model(probe),atol=1e-6)
    report={'task':'paired_glyph_style_generation','provenance':next(iter(provenances)),'style':next(iter(styles)),
        'experimental_only':True,'is_few_shot_model':False,'font_file_export_available':False,
        'train_characters':len({r[2]['char'] for r in groups['train']}),
        'validation_characters':len({r[2]['char'] for r in groups['validation']}),
        'test_characters':len({r[2]['char'] for r in groups['test']}),
        'training_samples':len(src),'unique_training_samples_seen':len(seen),'epochs':args.epochs,'steps':step,
        'history':history,'test':test,'identity_content_baseline':baseline,
        'test_character_overlap':False,'selection':'validation pixel L1; test accessed only after checkpoint selection',
        'model_sha256':digest(out/'generator.ts'),'content_font_sha256':digest(font_path),
        'gpu':torch.cuda.get_device_name(0),'torch':torch.__version__,'seed':args.seed,
        'parameters':sum(p.numel() for p in model.parameters()),'seconds':seconds,
        'peak_allocated_mb':torch.cuda.max_memory_allocated()/1024**2,
        'limitations':['No historical authenticity check','Unseen seal character structure not validated',
                      'Raster glyph output; no vector font exported','One style per trained model; no reference-image few-shot inference']}
    (out/'model.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    (out/'selection.json').write_text(json.dumps({k:[r[2] for r in v] for k,v in groups.items()},ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k!='history'},ensure_ascii=False,indent=2),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--dataset',required=True);p.add_argument('--source-font',required=True)
    p.add_argument('--out');p.add_argument('--epochs',type=int,default=30);p.add_argument('--batch',type=int,default=16)
    p.add_argument('--lr',type=float,default=.001);p.add_argument('--seed',type=int,default=20)
    p.add_argument('--eval-every',type=int,default=5)
    p.add_argument('--prepare-demo',action='store_true');p.add_argument('--target-font')
    p.add_argument('--demo-characters',type=int,default=1024)
    args=p.parse_args()
    if args.prepare_demo:
        if not args.target_font:p.error('--prepare-demo requires --target-font')
        prepare_demo(args)
    else:
        if not args.out:p.error('Training requires --out')
        train(args)
