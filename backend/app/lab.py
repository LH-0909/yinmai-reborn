"""Local corpus access, experimental denoising and unverified human annotations."""
import csv
import hashlib
import io
import json
import os
from pathlib import Path
from typing import Annotated, Literal
import cv2
import numpy as np
from PIL import Image, ImageDraw
from pydantic import BaseModel, Field, model_validator
from .database import ROOT
from . import ai

MODEL = ROOT / 'models/experimental/rgb-denoiser-v1.torchscript.pt'
SEED = Path(os.environ.get('ANNOTATION_SEED_PATH') or ROOT / 'data/raw-crops-audit/annotation-seed.csv')
Unit = Annotated[float, Field(ge=0, le=1)]


def corpus_root():
    configured=os.environ.get('TRAINING_CORPUS_PATH')
    if configured:return Path(configured).resolve()
    bundled=ROOT/'training-data/images'
    return bundled.resolve() if bundled.is_dir() else None


def corpus_entries():
    root=corpus_root()
    seed=SEED
    if not os.environ.get('TRAINING_CORPUS_PATH') and not os.environ.get('ANNOTATION_SEED_PATH'):
        seed=ROOT/'training-data/annotation-seed.csv'
    if root is None or not seed.is_file():
        return []
    if not root.is_dir():
        raise ValueError('本机训练素材目录不可用')
    result = []
    with seed.open(encoding='utf-8-sig', newline='') as stream:
        for row in csv.DictReader(stream):
            path = Path(row['file'])
            path = path.resolve() if path.is_absolute() else (root/path).resolve()
            if root not in path.parents or path.name.startswith('._'):
                raise ValueError('标注清单包含素材目录之外的路径')
            ident = hashlib.sha256((row['sha256'] + ':' + path.name).encode()).hexdigest()
            result.append({'id':ident, 'filename':path.name, 'path':path, 'sha256':row['sha256'],
                           'page_group':row['page_group'], 'split':'validation'})
    return result


def corpus_file(ident):
    row = next((r for r in corpus_entries() if r['id']==ident), None)
    if row is None:
        raise ValueError('素材不在已审计的标注清单中')
    # Resolve again: refuse a newly substituted symlink outside the corpus.
    root = corpus_root()
    if root is None: raise ValueError('素材目录未配置')
    path = row['path'].resolve()
    if root not in path.parents or not path.is_file():
        raise ValueError('原始素材已移动或路径不符合范围')
    if path.stat().st_size > 12*1024*1024:
        raise ValueError('素材超过读取大小限制')
    data = path.read_bytes()
    if hashlib.sha256(data).hexdigest() != row['sha256']:
        raise ValueError('原图与审计哈希不一致，请重新审计')
    return row, data


def model_card():
    if not MODEL.is_file():
        raise RuntimeError('尚未提供实验去噪权重')
    card = json.loads(MODEL.with_name(MODEL.name+'.json').read_text(encoding='utf-8'))
    digest = hashlib.sha256(MODEL.read_bytes()).hexdigest()
    if card.get('model_sha256') != digest or card.get('experimental_only') is not True:
        raise RuntimeError('实验模型清单或哈希不匹配')
    return card


def enhance(image):
    if max(image.shape[:2]) > 512:
        raise ValueError('实验去噪仅支持边长不超过512像素的裁图；请先准备单印裁图')
    import torch
    card = model_card()
    model, digest = ai.load_model(str(MODEL))
    if digest != card['model_sha256']:
        ai.load_model.cache_clear()
        model,digest = ai.load_model(str(MODEL))
        if digest != card['model_sha256']: raise RuntimeError('模型在加载期间变化，请重试')
    rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB).astype(np.float32)/255.
    tensor = torch.from_numpy(rgb.transpose(2,0,1).copy()).unsqueeze(0)
    with torch.inference_mode(): prediction = model(tensor)
    if prediction.shape != tensor.shape or not torch.isfinite(prediction).all():
        raise RuntimeError('实验模型输出无效')
    output = (prediction[0].clamp(0,1).permute(1,2,0).numpy()*255).round().astype(np.uint8)
    return cv2.cvtColor(output, cv2.COLOR_RGB2BGR), {
        'engine':'PyTorch/TorchScript', 'task':'synthetic_noise_denoising', 'ai_inference':True,
        'experimental_only':True, 'model_sha256':digest, 'input_shape':list(tensor.shape),
        'training_resolution':card['size'], 'training_steps':card['steps'],
        'human_review_required':True, 'missing_strokes_restored':False,
        'limitation':'仅训练去除合成高斯噪声；真实噪声、缺笔和OCR效果未验证，可能平滑细笔画'}


class Stroke(BaseModel):
    width: float = Field(.03, ge=.002, le=.15)
    points: list[tuple[Unit,Unit]] = Field(min_length=1, max_length=1000)


class Annotation(BaseModel):
    source_artifact_id: str
    source_sha256: str = Field(pattern=r'^[0-9a-f]{64}$')
    annotator: str = Field(min_length=1, max_length=80)
    transcription: str = Field('', max_length=300)
    legibility: Literal['unsure','readable','partial','unreadable'] = 'unsure'
    notes: str = Field('', max_length=3000)
    mask_mode: Literal['unlabeled','drawn'] = 'unlabeled'
    strokes: list[Stroke] = Field(default_factory=list, max_length=80)

    @model_validator(mode='after')
    def validate_annotation(self):
        if not self.annotator.strip(): raise ValueError('请填写标注人')
        if sum(len(s.points) for s in self.strokes) > 10000: raise ValueError('笔迹过多，请分次简化')
        if self.mask_mode=='drawn' and not self.strokes: raise ValueError('未画掩膜时不能标为已绘制')
        if self.mask_mode=='unlabeled' and self.strokes: raise ValueError('存在笔迹时须明确标为手绘掩膜')
        return self


def render_mask(body, width, height):
    if body.mask_mode=='unlabeled': return None
    mask = Image.new('L',(width,height),0);draw=ImageDraw.Draw(mask)
    for stroke in body.strokes:
        line_width=max(1,round(stroke.width*min(width,height)))
        points=[(round(x*(width-1)),round(y*(height-1))) for x,y in stroke.points]
        if len(points)>1: draw.line(points,fill=255,width=line_width,joint='curve')
        radius=line_width/2
        for x,y in points:
            draw.ellipse((max(0,x-radius),max(0,y-radius),min(width-1,x+radius),min(height-1,y+radius)),fill=255)
    data=io.BytesIO();mask.save(data,format='PNG')
    return data.getvalue()
