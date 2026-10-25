"""Export and verify the real first training batch and fixed held-out test images.

Replays the documented CUDA seed/config. Stops if the recorded first-step loss
or test metrics do not match. Original worn crops are targets, not clean seals.
"""
import argparse
import hashlib
import json
from pathlib import Path
import random
import sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import torch
from train_denoiser import ResidualDenoiser, load_split, add_noise, masked_mse, evaluate


def save_image(tensor,path):
    path.parent.mkdir(parents=True,exist_ok=True)
    pixels=(tensor.detach().cpu().permute(1,2,0).numpy()*255).round().clip(0,255).astype(np.uint8)
    if pixels.shape[2]==1:pixels=pixels[:,:,0]
    Image.fromarray(pixels).save(path)


def run(args):
    out=Path(args.out).resolve();out.mkdir(parents=True,exist_ok=True)
    project=Path(args.project).resolve()
    metrics=json.loads((project/'evidence/gpu-denoiser-v1/metrics.json').read_text(encoding='utf-8'))
    recorded_selection=json.loads((project/'evidence/gpu-denoiser-v1/selection.json').read_text(encoding='utf-8'))
    if torch.__version__!=metrics['torch'] or not torch.cuda.is_available():
        raise RuntimeError('Exact replay requires the recorded CUDA PyTorch runtime')
    seed=metrics['seed'];torch.set_num_threads(4)
    random.seed(seed);np.random.seed(seed);torch.manual_seed(seed);torch.cuda.manual_seed_all(seed)
    torch.backends.cudnn.benchmark=False;torch.backends.cudnn.deterministic=True
    datasets={}
    for split,count in [('train',metrics['train_images']),('validation',metrics['validation_images']),('test',metrics['test_images'])]:
        images,masks,rows=load_split(project/'data/raw-crops-audit'/(split+'.jsonl'),count,seed,metrics['size'])
        assert [r['sha256'] for r in rows]==[r['sha256'] for r in recorded_selection[split]],'Selection changed'
        datasets[split]=(images.cuda(),masks.cuda(),rows)
    initial=ResidualDenoiser().cuda()
    train,mask,rows=datasets['train']
    indices=torch.randint(len(train),(metrics['batch'],),device='cuda')
    targets,masks=train[indices],mask[indices]
    inputs=add_noise(targets,masks,metrics['noise_sigma'])
    with torch.no_grad():loss=float(masked_mse(initial(inputs),targets,masks))
    recorded_loss=metrics['history'][0]['train_mse']
    if abs(loss-recorded_loss)>1e-8:
        raise RuntimeError('First batch does not reproduce the recorded loss: '+str(loss))
    index_values=indices.cpu().tolist()
    folder=out/'used-inputs/train-step-0001';folder.mkdir(parents=True,exist_ok=True)
    np.savez_compressed(folder/'exact-float32-tensors.npz',input=inputs.cpu().numpy(),target=targets.cpu().numpy(),
                        content_mask=masks.cpu().numpy(),train_indices=np.array(index_values,dtype=np.int64))
    first_rows=[]
    for i,index in enumerate(index_values):
        name='{:02d}_'.format(i)+rows[index]['name']
        for kind,tensor in [('input',inputs[i]),('target',targets[i]),('mask',masks[i])]:save_image(tensor,folder/kind/name)
        first_rows.append({'batch_index':i,'train_pool_index':index,'source_name':rows[index]['name'],
           'source_sha256':rows[index]['sha256'],'input':'used-inputs/train-step-0001/input/'+name,
           'target':'used-inputs/train-step-0001/target/'+name,'mask':'used-inputs/train-step-0001/mask/'+name})
    model_path=project/'models/experimental'/metrics['model_file']
    assert hashlib.sha256(model_path.read_bytes()).hexdigest()==metrics['model_sha256']
    model=torch.jit.load(str(model_path),map_location='cuda').eval()
    test,test_mask,test_rows=datasets['test']
    test_metrics=evaluate(model,test,test_mask,metrics['noise_sigma'],seed+200)
    if abs(test_metrics['model_psnr_db']-metrics['test']['model_psnr_db'])>1e-4:
        raise RuntimeError('Recorded test metric could not be reproduced')
    test_inputs=add_noise(test,test_mask,metrics['noise_sigma'],seed+200)
    outputs=[]
    with torch.no_grad():
        for i in range(0,len(test),16):outputs.append(model(test_inputs[i:i+16]).cpu())
    outputs=torch.cat(outputs)
    test_folder=out/'used-inputs/fixed-test-128';test_folder.mkdir(parents=True,exist_ok=True)
    np.savez_compressed(test_folder/'exact-float32-tensors.npz',input=test_inputs.cpu().numpy(),
                        target=test.cpu().numpy(),content_mask=test_mask.cpu().numpy(),output=outputs.numpy())
    evaluated=[]
    for i,row in enumerate(test_rows):
        for kind,tensor in [('input',test_inputs[i]),('target',test[i]),('mask',test_mask[i]),('output',outputs[i])]:
            save_image(tensor,test_folder/kind/row['name'])
        evaluated.append({'source_name':row['name'],'source_sha256':row['sha256'],
                          **{kind:'used-inputs/fixed-test-128/'+kind+'/'+row['name'] for kind in ['input','target','mask','output']}})
    font_path=Path('C:/Windows/Fonts/simsun.ttc')
    font=ImageFont.truetype(str(font_path),18) if font_path.exists() else ImageFont.load_default()
    small=ImageFont.truetype(str(font_path),12) if font_path.exists() else ImageFont.load_default()
    sheet=Image.new('RGB',(1000,1160),'#f1eadc');draw=ImageDraw.Draw(sheet)
    draw.text((18,14),'首批训练图像：实际第1步 / CUDA固定种子回放核验通过',font=font,fill='#30231a')
    draw.text((18,42),'每格左：合成噪声输入  |  右：原始有损裁图目标（不是无损真值）',font=font,fill='#70432a')
    for i,item in enumerate(first_rows):
        col=i%4;row=i//4;x=col*250+7;y=row*265+90
        for j,kind in enumerate(['input','target']):
            with Image.open(out/item[kind]) as im:sheet.paste(im.convert('RGB').resize((114,114),Image.NEAREST),(x+j*120,y))
        draw.text((x,y+121),'步骤1 · batch {:02d}'.format(i),font=small,fill='#583a24')
        draw.text((x,y+143),item['source_name'],font=small,fill='#583a24')
        draw.text((x,y+167),'输入            原裁图目标',font=small,fill='#70432a')
    sheet.save(out/'真实训练输入对照.png')
    result={'scope':'Verified CUDA replay, not newly invented supervision','torch':torch.__version__,
            'gpu':torch.cuda.get_device_name(0),'first_training_batch_count':len(first_rows),
            'recorded_step1_loss':recorded_loss,'replayed_step1_loss':loss,'step1_loss_matches_atol_1e-8':True,
            'recorded_test':metrics['test'],'replayed_test':test_metrics,'test_psnr_matches_atol_1e-4':True,
            'first_batch':first_rows,'fixed_test':evaluated,'model_sha256':metrics['model_sha256'],
            'png_note':'PNG is rounded to 8-bit for viewing. NPZ preserves exact float32 input/target/mask arrays; load with allow_pickle=False.',
            'no_ocr_labels':True,'targets_are_original_worn_scans':True,'missing_stroke_ground_truth_available':False}
    (out/'used-inputs/replay-verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k not in ['first_batch','fixed_test']},ensure_ascii=False,indent=2),flush=True)


if __name__=='__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--project',required=True);parser.add_argument('--out',required=True)
    run(parser.parse_args())
