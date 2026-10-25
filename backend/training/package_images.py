"""Copy actual audited PNGs into portable splits, preserving bytes and hashes."""
import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
import csv
import hashlib
import json
from pathlib import Path
import sys


def run(args):
    source=Path(args.source).resolve();audit=Path(args.audit).resolve();out=Path(args.out).resolve()
    if source==out or source in out.parents: raise ValueError('Output must be outside the original image folder')
    out.mkdir(parents=True,exist_ok=True)
    rows=[json.loads(l) for l in (audit/'manifest.jsonl').read_text(encoding='utf-8').splitlines() if l.strip()]
    project=Path(__file__).resolve().parents[2]
    selection=json.loads((project/'evidence/gpu-denoiser-v1/selection.json').read_text(encoding='utf-8'))
    selected={r['sha256'] for group in selection.values() for r in group}
    def copy(row):
        name=row['name']
        if Path(name).name!=name or name.startswith('._'): raise ValueError('Unsafe or sidecar filename')
        path=(source/name).resolve()
        if source not in path.parents: raise ValueError('Source path escaped original image folder')
        data=path.read_bytes()
        if hashlib.sha256(data).hexdigest()!=row['sha256']: raise ValueError('Source hash changed: '+name)
        dest=out/'images'/row['split']/name;dest.parent.mkdir(parents=True,exist_ok=True)
        if dest.exists():
            if hashlib.sha256(dest.read_bytes()).hexdigest()!=row['sha256']: raise ValueError('Output already contains different bytes: '+name)
        else: dest.write_bytes(data)
        result={**row,'path':'../images/'+row['split']+'/'+name,'baseline_used':row['sha256'] in selected}
        return result
    with ThreadPoolExecutor(max_workers=8) as pool:
        copied=[]
        for i,row in enumerate(pool.map(copy,rows),1):
            copied.append(row)
            if i%3000==0: print('Copied and SHA256 verified '+str(i)+'/'+str(len(rows)),flush=True)
    manifests=out/'manifests';manifests.mkdir(exist_ok=True)
    for split in ['train','validation','test','excluded']:
        (manifests/(split+'.jsonl')).write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in copied if r['split']==split),encoding='utf-8')
    (manifests/'all.jsonl').write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in copied),encoding='utf-8')
    counts=dict(Counter(r['split'] for r in copied))
    groups={s:{r['page_group'] for r in copied if r['split']==s} for s in ['train','validation','test']}
    assert not(groups['train']&groups['validation'] or groups['train']&groups['test'] or groups['test']&groups['validation'])
    by_name={r['name']:r for r in copied}
    with (audit/'annotation-seed.csv').open(encoding='utf-8-sig',newline='') as f: seeds=list(csv.DictReader(f))
    with (out/'annotation-seed.csv').open('w',encoding='utf-8-sig',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(seeds[0]));writer.writeheader()
        for row in seeds:
            name=Path(row['file']).name
            assert by_name[name]['split']=='validation'
            row['file']='validation/'+name;writer.writerow(row)
    items=[{'name':r['name'],'split':r['split'],'page':r['page_group'],'width':r['width'],'height':r['height'],
            'path':'images/'+r['split']+'/'+r['name'],'baseline_used':r['baseline_used']} for r in copied]
    replay_path=out/'used-inputs/replay-verification.json'
    replay=json.loads(replay_path.read_text(encoding='utf-8')) if replay_path.exists() else {}
    payload=json.dumps({'counts':counts,'items':items,'first_batch':replay.get('first_batch',[])},ensure_ascii=False).replace('</','<\\/')
    template=(Path(__file__).parent/'training_gallery.html').read_text(encoding='utf-8')
    (out/'index.html').write_text(template.replace('__CATALOG_JSON__',payload),encoding='utf-8')
    summary={'actual_original_png_files':len(copied),'split_counts':counts,'source_bytes':sum(r['bytes'] for r in copied),
             'all_source_sha256_verified':True,'original_files_modified':False,'page_group_overlap':False,
             'baseline_selected':len(selected),'ocr_labels_available':False,'undamaged_targets_available':False,
             'annotation_candidates':len(seeds),'manifest_path_base':'Each JSONL file directory',
             'first_batch_replay_verified':bool(replay.get('step1_loss_matches_atol_1e-8'))}
    (out/'dataset-summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
    guide='''# 真实训练图像包

本包实际包含13,646张用户提供的PNG裁图，不是UI参考图或只有路径的清单。原稿按字节复制并逐张核验SHA256，D:/LH/raw_crops没有被改动。

| 目录 | 实际图片数 | 用途 |
|---|---:|---|
| images/train | 11,144 | 训练 |
| images/validation | 1,167 | 验证与模型选择 |
| images/test | 1,333 | 保留测试 |
| images/excluded | 2 | 短边不足32px，保留但不参与训练 |

直接用浏览器打开index.html可以翻页查看全部真实图片；默认显示训练组。勾选“只看已用于GPU基线的图片”会筛出实际训练池2,048张、验证128张、测试128张。不同组按来源页隔离，不能随意混在一起。

## 实际训练输入与目标

`used-inputs/train-step-0001/`包含固定种子回放并核验的第1步16张输入、原裁图目标与有效区域掩膜。第1步损失与原记录完全相同。`真实训练输入对照.png`可直接查看。

`used-inputs/fixed-test-128/`包含固定测试的128张输入、目标、区域掩膜和模型输出；重算的PSNR与原记录一致。不是新造指标。PNG为便于查看的8位图；`exact-float32-tensors.npz`保留实际float32数组，可用NumPy的allow_pickle=False读取。

目标始终是已有残损的原裁图。输入是在它上面添加合成高斯噪声；这不是完整历史原貌，没有OCR标签，也没有缺笔补全真值。整个训练过程逐批即时添加噪声，不存在预先落盘的400步输入图文件夹；这里补出了已核验的首批输入和固定测试图。

## 迁移到其他目录或设备

`manifests/train.jsonl`、`validation.jsonl`、`test.jsonl`中的path相对于清单文件所在目录，不依赖D盘。使用配套新版项目训练脚本时，例如：

```powershell
python backend/training/train_denoiser.py --audit training-data/manifests --out evidence/new-gpu-run --model models/experimental/new-run.pt
```

该命令需要CUDA版PyTorch。训练参数和原实验说明在项目docs/GPU_TRAINING.md。不要覆盖保留测试集或把验证组标注自动投入训练。

配套完整包将本目录放在项目training-data/，图像源可自动识别。若单独解压到其他位置，在项目.env填写TRAINING_CORPUS_PATH=<本目录>/images和ANNOTATION_SEED_PATH=<本目录>/annotation-seed.csv，重启后端即可在标注页读取候选。

本包供用户在本机开发使用；原目录未提供独立素材许可说明，未将它发布到外部服务。
'''
    (out/'训练图像使用说明.md').write_text(guide,encoding='utf-8')
    print(json.dumps(summary,ensure_ascii=False,indent=2),flush=True)


if __name__=='__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',required=True);parser.add_argument('--audit',required=True);parser.add_argument('--out',required=True)
    run(parser.parse_args())
