"""Small CUDA experiment: synthetic Gaussian noise -> original worn crop.

This does NOT learn historical stroke completion, transcription, or recovery of
damage already present in the original image. Never auto-enable in the web API.
Python 3.8 / torch 1.13 compatible; uses no externally downloaded checkpoints.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import random
import time

import numpy as np
from PIL import Image, ImageDraw
import torch
from torch import nn


class ResidualDenoiser(nn.Module):
    def __init__(self, width=24):
        super().__init__()
        self.body = nn.Sequential(
            nn.Conv2d(3, width, 3, padding=1), nn.ReLU(),
            nn.Conv2d(width, width, 3, padding=1), nn.ReLU(),
            nn.Conv2d(width, width, 3, padding=1), nn.ReLU(),
            nn.Conv2d(width, 3, 3, padding=1))
        nn.init.zeros_(self.body[-1].weight)
        nn.init.zeros_(self.body[-1].bias)

    def forward(self, image):
        return torch.clamp(image + self.body(image), 0., 1.)


def load_split(manifest, count, seed, size):
    rows = [json.loads(line) for line in Path(manifest).read_text(encoding='utf-8').splitlines() if line.strip()]
    selected = random.Random(seed).sample(rows, min(count, len(rows)))
    images, masks = [], []
    for row in selected:
        path = Path(row['path'])
        if not path.is_absolute(): path = (Path(manifest).resolve().parent/path).resolve()
        if hashlib.sha256(path.read_bytes()).hexdigest() != row['sha256']:
            raise ValueError('Source changed since audit: ' + row['name'])
        with Image.open(path) as original:
            im = original.convert('RGB')
            scale = min(size / im.width, size / im.height)
            w, h = max(1, round(im.width * scale)), max(1, round(im.height * scale))
            im = im.resize((w, h), Image.BICUBIC)
            image = np.ones((size, size, 3), dtype=np.float32)
            mask = np.zeros((size, size, 1), dtype=np.float32)
            x, y = (size-w)//2, (size-h)//2
            image[y:y+h, x:x+w] = np.asarray(im, dtype=np.float32)/255.
            mask[y:y+h, x:x+w] = 1.
        images.append(torch.from_numpy(image.transpose(2, 0, 1)))
        masks.append(torch.from_numpy(mask.transpose(2, 0, 1)))
    return torch.stack(images), torch.stack(masks), selected


def add_noise(image, mask, sigma, seed=None):
    if seed is None:
        noise = torch.randn_like(image)
    else:
        generator = torch.Generator(device=image.device).manual_seed(seed)
        noise = torch.randn(image.shape, device=image.device, dtype=image.dtype, generator=generator)
    return torch.clamp(image + sigma * noise * mask, 0., 1.)


def masked_mse(prediction, target, mask):
    return ((prediction-target).square()*mask).sum() / (mask.sum()*3)


def evaluate(model, images, masks, sigma, seed, batch=16):
    model.eval()
    sums = [0., 0., 0.]
    with torch.no_grad():
        # Generate the entire corruption once so comparison uses identical noise.
        noisy = add_noise(images, masks, sigma, seed)
        for i in range(0, len(images), batch):
            target, mask, degraded = images[i:i+batch], masks[i:i+batch], noisy[i:i+batch]
            result = model(degraded)
            sums[0] += float(((degraded-target).square()*mask).sum())
            sums[1] += float(((result-target).square()*mask).sum())
            sums[2] += float(mask.sum()*3)
    baseline, model_mse = sums[0]/sums[2], sums[1]/sums[2]
    return {'noisy_mse': baseline, 'model_mse': model_mse,
            'noisy_psnr_db': -10*math.log10(max(baseline, 1e-12)),
            'model_psnr_db': -10*math.log10(max(model_mse, 1e-12)),
            'psnr_gain_db': 10*math.log10(max(baseline, 1e-12)/max(model_mse, 1e-12))}


def run(args):
    if not torch.cuda.is_available():
        raise RuntimeError('CUDA required; refusing to silently train on CPU')
    out = Path(args.out).resolve(); out.mkdir(parents=True, exist_ok=True)
    export = Path(args.model).resolve(); export.parent.mkdir(parents=True, exist_ok=True)
    torch.set_num_threads(4)
    random.seed(args.seed); np.random.seed(args.seed); torch.manual_seed(args.seed)
    torch.cuda.manual_seed_all(args.seed)
    torch.backends.cudnn.benchmark = False
    torch.backends.cudnn.deterministic = True
    datasets = {}
    for split, count in [('train', args.train_images), ('validation', args.eval_images), ('test', args.eval_images)]:
        images, masks, rows = load_split(Path(args.audit)/(split+'.jsonl'), count, args.seed, args.size)
        datasets[split] = (images.cuda(), masks.cuda(), rows)
    for a, b in [('train', 'validation'), ('train', 'test'), ('validation', 'test')]:
        assert not ({r['page_group'] for r in datasets[a][2]} & {r['page_group'] for r in datasets[b][2]})
        assert not ({r['pixel_sha256'] for r in datasets[a][2]} & {r['pixel_sha256'] for r in datasets[b][2]})
    model = ResidualDenoiser().cuda()
    optimizer = torch.optim.Adam(model.parameters(), lr=.001)
    train, train_mask, _ = datasets['train']
    val, val_mask, _ = datasets['validation']
    if args.epochs is not None:
        args.steps=math.ceil(len(train)/args.batch)*args.epochs
    seen=torch.zeros(len(train),dtype=torch.bool,device='cuda')
    order=None;cursor=len(train)
    torch.cuda.reset_peak_memory_stats(); torch.cuda.synchronize()
    started = time.perf_counter(); history = []; best = float('inf'); best_state = None
    for step in range(1, args.steps+1):
        model.train()
        if args.sampling=='epoch_shuffle':
            if cursor>=len(train):
                order=torch.randperm(len(train),device='cuda');cursor=0
            index=order[cursor:cursor+args.batch];cursor+=args.batch
        else:
            index = torch.randint(len(train), (args.batch,), device='cuda')
        seen[index]=True
        target, mask = train[index], train_mask[index]
        noisy = add_noise(target, mask, args.sigma)
        loss = masked_mse(model(noisy), target, mask)
        optimizer.zero_grad(set_to_none=True); loss.backward(); optimizer.step()
        if step == 1 or step % args.eval_every == 0 or step == args.steps:
            metrics = evaluate(model, val, val_mask, args.sigma, args.seed+100)
            entry = {'step':step, 'train_mse':float(loss), 'validation':metrics}
            history.append(entry)
            if metrics['model_mse'] < best:
                best = metrics['model_mse']; best_state = {k:v.detach().cpu().clone() for k,v in model.state_dict().items()}
            print(json.dumps(entry), flush=True)
    torch.cuda.synchronize(); seconds = time.perf_counter()-started
    model.load_state_dict(best_state); model.eval()
    test, test_mask, test_rows = datasets['test']
    test_result = evaluate(model, test, test_mask, args.sigma, args.seed+200)
    validation = evaluate(model, val, val_mask, args.sigma, args.seed+100)
    with torch.no_grad():
        noisy = add_noise(test[:6], test_mask[:6], args.sigma, args.seed+300)
        prediction = model(noisy)
        sheet = Image.new('RGB', (4*200, 32+6*200), '#f1ede4'); draw = ImageDraw.Draw(sheet)
        for col, title in enumerate(['Original worn target', 'Synthetic noise', 'CNN output', 'Difference x4']):
            draw.text((col*200+5, 8), title, fill='black')
        for row in range(6):
            panels = [test[row], noisy[row], prediction[row], torch.clamp(4*(prediction[row]-test[row]).abs(),0,1)]
            for col, panel in enumerate(panels):
                pixels = (panel.cpu().permute(1,2,0).numpy()*255).round().astype(np.uint8)
                im = Image.fromarray(pixels).resize((192,192), Image.NEAREST)
                sheet.paste(im,(col*200+4, 32+row*200))
        sheet.save(out/'synthetic-noise-comparison.png')
    cpu_model = model.cpu().eval()
    scripted = torch.jit.script(cpu_model)
    scripted.save(str(export))
    # Export must support the existing restoration plugin shape, but is not enabled.
    with torch.no_grad():
        sample = torch.rand(1,3,256,256); result = scripted(sample)
        assert result.shape == sample.shape and torch.isfinite(result).all()
    report = {'experiment':'synthetic-gaussian-denoising-v1', 'experimental_only':True,
        'task':'Remove newly added Gaussian noise; target is the original worn scan, NOT undamaged ground truth',
        'does_not_establish':['ancient seal OCR accuracy','missing-stroke restoration','historical authenticity','production readiness'],
        'source_read_only':True, 'raw_images_uploaded':False, 'seed':args.seed,
        'torch':torch.__version__, 'cuda_runtime':torch.version.cuda, 'gpu':torch.cuda.get_device_name(0),
        'device':'cuda:0', 'size':args.size,'batch':args.batch,'steps':args.steps,'noise_sigma':args.sigma,
        'train_images':len(train),'validation_images':len(val),'test_images':len(test),
        'sampling':args.sampling,'requested_epochs':args.epochs,'train_unique_images_seen':int(seen.sum()),
        'selection':'seeded subset of audited source-page grouped split; all source SHA256 verified',
        'page_group_overlap':False,'exact_pixel_overlap':False,'metric':'global content-only RGB MSE / PSNR, excluding letterbox padding',
        'best_selected_on':'validation MSE only; test read for final evaluation after selection',
        'parameters':sum(p.numel() for p in cpu_model.parameters()),'training_seconds':seconds,
        'peak_allocated_mb':torch.cuda.max_memory_allocated()/1024**2,'peak_reserved_mb':torch.cuda.max_memory_reserved()/1024**2,
        'validation':validation,'test':test_result,'history':history,
        'model_file':export.name,'model_sha256':hashlib.sha256(export.read_bytes()).hexdigest(),
        'api_model_enabled':False, 'limitation':'Single synthetic noise level and one seed; different pages may share a book. No real damage or OCR quality measured.'}
    (out/'metrics.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    (out/'selection.json').write_text(json.dumps({k:[{'name':r['name'],'page_group':r['page_group'],'sha256':r['sha256']} for r in v[2]] for k,v in datasets.items()},indent=2),encoding='utf-8')
    (export.parent/(export.name+'.json')).write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False,indent=2),flush=True)


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--audit',required=True); parser.add_argument('--out',required=True); parser.add_argument('--model',required=True)
    parser.add_argument('--steps',type=int,default=400); parser.add_argument('--train-images',type=int,default=2048)
    parser.add_argument('--eval-images',type=int,default=128); parser.add_argument('--batch',type=int,default=16)
    parser.add_argument('--size',type=int,default=96); parser.add_argument('--sigma',type=float,default=.08)
    parser.add_argument('--seed',type=int,default=19); parser.add_argument('--eval-every',type=int,default=50)
    parser.add_argument('--sampling',choices=['with_replacement','epoch_shuffle'],default='with_replacement')
    parser.add_argument('--epochs',type=int,default=None,help='Complete epochs; requires epoch_shuffle and overrides --steps')
    args=parser.parse_args()
    if min(args.steps,args.train_images,args.eval_images,args.batch,args.size,args.eval_every)<1 or args.sigma<=0:
        parser.error('Counts, size and sigma must be positive')
    if args.epochs is not None and (args.epochs<1 or args.sampling!='epoch_shuffle'):
        parser.error('--epochs must be positive and requires --sampling epoch_shuffle')
    run(args)
