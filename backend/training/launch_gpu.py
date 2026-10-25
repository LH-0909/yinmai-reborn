"""One-command CUDA denoising trainer. No silent CPU fallback or model promotion."""
import argparse
from datetime import datetime,timezone
import json
from pathlib import Path
import subprocess
import sys
import uuid


def choose_audit(project,data=None):
    candidates=[Path(data).resolve()] if data else [project/'training-data',project.parent/'yinmai-training-data',project/'data/raw-crops-audit']
    for folder in candidates:
        for audit in [folder/'manifests',folder]:
            if all((audit/(split+'.jsonl')).is_file() for split in ['train','validation','test']):return audit
    raise RuntimeError('No training images/manifests found. Extract the full-with-images package or pass --data to the image package directory.')


def run(args):
    import torch
    if not torch.cuda.is_available():raise RuntimeError('CUDA is unavailable in this Python. Install/configure a CUDA PyTorch environment or choose it with -Python. CPU fallback is disabled.')
    project=Path(__file__).resolve().parents[2];audit=choose_audit(project,args.data)
    counts={s:sum(bool(l.strip()) for l in (audit/(s+'.jsonl')).read_text(encoding='utf-8').splitlines()) for s in ['train','validation','test']}
    train_count=counts['train'] if args.full else min(args.train_images,counts['train'])
    eval_count=max(counts['validation'],counts['test']) if args.full else args.eval_images
    if args.smoke:train_count=min(64,counts['train']);eval_count=16
    run_id=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'-'+uuid.uuid4().hex[:6]
    out=project/'evidence/gpu-runs'/run_id;out.mkdir(parents=True,exist_ok=False)
    model=project/'models/experimental/runs'/(run_id+'.torchscript.pt')
    command=[sys.executable,'-u',str(Path(__file__).parent/'train_denoiser.py'),'--audit',str(audit),'--out',str(out),
        '--model',str(model),'--batch',str(args.batch),'--size',str(args.size),'--train-images',str(train_count),
        '--eval-images',str(eval_count),'--seed','19','--sigma','.08','--sampling','epoch_shuffle','--eval-every','200']
    if args.smoke:command+=['--steps','20','--eval-every','20']
    elif args.steps:command+=['--steps',str(args.steps)]
    else:command+=['--epochs',str(args.epochs)]
    plan={'run_id':run_id,'task':'Synthetic Gaussian denoising only; original worn scans are targets',
        'gpu':torch.cuda.get_device_name(0),'torch':torch.__version__,'cuda':torch.version.cuda,
        'audit':str(audit),'all_split_counts':counts,'train_pool':train_count,'requested_epochs':None if args.smoke or args.steps else args.epochs,
        'python':sys.executable,'command':command,'experimental_only':True,'web_model_auto_replaced':False}
    (out/'launch.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2),encoding='utf-8')
    print('GPU: '+plan['gpu']+' | torch '+torch.__version__,flush=True)
    print('Training pool: '+str(train_count)+' | audit: '+str(audit),flush=True)
    print('Log/output: '+str(out),flush=True)
    with (out/'console.log').open('w',encoding='utf-8') as log:
        child=subprocess.Popen(command,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,encoding='utf-8',errors='replace')
        for line in child.stdout:print(line,end='',flush=True);log.write(line);log.flush()
        code=child.wait()
    if code:raise RuntimeError('Training failed with exit '+str(code)+'. Inspect '+str(out/'console.log'))
    result=json.loads((out/'metrics.json').read_text(encoding='utf-8'))
    assert result['device']=='cuda:0' and result['model_sha256'] and model.is_file()
    if args.full and not args.smoke and not args.steps:
        assert result['train_unique_images_seen']==counts['train'],'A full epoch must visit every training image'
    result_summary={'run_id':run_id,'out':str(out.relative_to(project)),'model':str(model.relative_to(project)),
        'task':plan['task'],'device':result['device'],'gpu':plan['gpu'],'train_images':result['train_images'],
        'train_unique_images_seen':result['train_unique_images_seen'],'steps':result['steps'],
        'test':result['test'],'peak_allocated_mb':result['peak_allocated_mb'],'model_sha256':result['model_sha256'],
        'web_model_auto_replaced':False}
    (project/'evidence/latest-training-run.json').write_text(json.dumps(result_summary,ensure_ascii=False,indent=2),encoding='utf-8')
    print('Completed. Model: '+str(model),flush=True)
    print('The web model was not automatically replaced.',flush=True)


if __name__=='__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data');parser.add_argument('--full',action='store_true');parser.add_argument('--smoke',action='store_true')
    parser.add_argument('--epochs',type=int,default=5);parser.add_argument('--steps',type=int)
    parser.add_argument('--batch',type=int,default=16);parser.add_argument('--size',type=int,default=96)
    parser.add_argument('--train-images',type=int,default=2048);parser.add_argument('--eval-images',type=int,default=128)
    a=parser.parse_args()
    if min(a.epochs,a.batch,a.size,a.train_images,a.eval_images)<1 or (a.steps is not None and a.steps<1):parser.error('Training counts must be positive')
    run(a)
