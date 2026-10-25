"""Human-labelled glyph pairs for font generation, separate from denoising."""
import hashlib
import io
import json
import math
import os
from pathlib import Path
from typing import Literal
import zipfile

import numpy as np
from PIL import Image, ImageFont, ImageDraw, ImageOps
from pydantic import BaseModel, Field, model_validator
from sqlalchemy import select
from .database import ROOT, STORAGE, Artifact, Seal

UNCLASSIFIED_STYLES = {'', '待归类', '未归类', '待细分', '汉印（待细分）'}


class Glyph(BaseModel):
    char: str = Field('', max_length=1)
    # Fractions of ORIGINAL image dimensions. End coordinates are exclusive.
    box: tuple[float, float, float, float]
    polarity: Literal['zhu', 'bai', 'black'] = 'zhu'
    mirrored: bool = False
    reviewed: bool = False

    @model_validator(mode='after')
    def check(self):
        if self.reviewed and not self.char:
            raise ValueError('未填写释文的候选框不能勾选已核对')
        if self.char and not (0x3400 <= ord(self.char) <= 0x9fff or 0x20000 <= ord(self.char) <= 0x323af):
            raise ValueError('每个框须填写一个已核对的汉字；异体字可记录对应Unicode汉字')
        x0, y0, x1, y1 = self.box
        if not all(math.isfinite(v) and 0 <= v <= 1 for v in self.box) or x1 <= x0 or y1 <= y0:
            raise ValueError('字框必须位于原图内，并具有正宽度和高度')
        return self


class GlyphDocument(BaseModel):
    source_artifact_id: str
    source_sha256: str = Field(pattern=r'^[a-f0-9]{64}$')
    style: str = Field(min_length=1, max_length=80)
    annotator: str = Field(min_length=1, max_length=80)
    glyphs: list[Glyph] = Field(max_length=64)
    notes: str = Field('', max_length=3000)
    proposal_artifact_id: str | None = None

    @model_validator(mode='after')
    def check(self):
        if not self.style.strip() or not self.annotator.strip():
            raise ValueError('请填写风格分组和标注人')
        return self


def split_for_char(char):
    # Same character in all books/styles always shares a split.
    n = int(hashlib.sha256(('yinmai-font-v1:' + char).encode()).hexdigest()[:8], 16) % 10
    return 'test' if n == 0 else 'validation' if n == 1 else 'train'


def crop_mask(data, glyph, size=128):
    with Image.open(io.BytesIO(data)) as image:
        image = ImageOps.exif_transpose(image).convert('RGB')
        x0, y0, x1, y1 = glyph['box']
        box = (math.floor(x0*image.width), math.floor(y0*image.height),
               math.ceil(x1*image.width), math.ceil(y1*image.height))
        if box[2]-box[0] < 8 or box[3]-box[1] < 8:
            raise ValueError('单字框至少需要8×8个原始像素')
        image = image.crop(box)
        if glyph['mirrored']: image = ImageOps.mirror(image)
        p = np.asarray(image, dtype=np.float32)
        if glyph['polarity'] == 'black':
            mask = 1. - p.mean(2)/255.
        else:
            red = ((p[:,:,0]-np.maximum(p[:,:,1], p[:,:,2])) > 25) & (p[:,:,0] > 65)
            if not .01 < red.mean() < .99:
                raise ValueError('字框没有足够的红白差异，请核对朱白文和框选范围')
            mask = red.astype(np.float32) if glyph['polarity'] == 'zhu' else 1. - red.astype(np.float32)
        image = Image.fromarray((mask*255).round().astype('uint8'), 'L')
        image.thumbnail((size-16, size-16), Image.Resampling.LANCZOS)
        out = Image.new('L', (size, size), 0)
        out.paste(image, ((size-image.width)//2, (size-image.height)//2))
        return out


def latest_documents(db):
    rows = db.scalars(select(Artifact).where(Artifact.kind == 'glyph_annotation')
                      .order_by(Artifact.created_at.desc(), Artifact.id.desc()))
    seen = set()
    for row in rows:
        if row.seal_id in seen: continue
        seen.add(row.seal_id)
        yield row, json.loads((STORAGE/row.filename).read_text(encoding='utf-8'))


def inventory(db):
    styles = {}
    for a, doc in latest_documents(db):
        seal = db.get(Seal, a.seal_id)
        if seal.source_kind == 'synthetic_test': continue
        group = styles.setdefault(doc['style'], {'style':doc['style'], 'unclassified':doc['style'] in UNCLASSIFIED_STYLES,
                                                   'boxes':0, 'reviewed':0, 'characters':set(),
                                                   'splits':{'train':set(), 'validation':set(), 'test':set()}})
        for g in doc['glyphs']:
            group['boxes'] += 1
            if g['reviewed']:
                group['reviewed'] += 1
                group['characters'].add(g['char'])
                group['splits'][split_for_char(g['char'])].add(g['char'])
    result = []
    for group in styles.values():
        group['characters'] = len(group['characters'])
        group['splits'] = {k:len(v) for k,v in group['splits'].items()}
        result.append(group)
    return result


def export_pairs(db, style):
    if style.strip() in UNCLASSIFIED_STYLES:
        raise ValueError('请先确认具体印风分组；待归类候选不能导出为字体训练集')
    buf = io.BytesIO(); manifest = []; char_groups = {}
    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as z:
        for annotation, doc in latest_documents(db):
            if doc['style'] != style: continue
            seal = db.get(Seal, annotation.seal_id)
            if seal.source_kind == 'synthetic_test': continue
            source = db.get(Artifact, doc['source_artifact_id'])
            if not source or source.seal_id != seal.id or source.kind != 'original':
                raise ValueError('字形标注未绑定原稿')
            data = (STORAGE/source.filename).read_bytes()
            if hashlib.sha256(data).hexdigest() != doc['source_sha256']:
                raise ValueError('原图哈希变化，请重新核对标注')
            for index, g in enumerate(doc['glyphs']):
                if not g['reviewed']: continue
                mask = crop_mask(data, g)
                pixels = np.asarray(mask)
                if not .01 < (pixels > 127).mean() < .85:
                    raise ValueError('字形掩膜为空或几乎全填充，请核对字框与朱白文')
                ident = f'{annotation.id}-{index:03d}'
                path = 'targets/'+ident+'.png'; image_buf = io.BytesIO(); mask.save(image_buf, 'PNG')
                target = image_buf.getvalue(); z.writestr(path, target)
                # Duplicated pixels cannot be relabelled as different characters/splits.
                pixel_hash = hashlib.sha256(mask.tobytes()).hexdigest()
                if pixel_hash in char_groups and char_groups[pixel_hash] != g['char']:
                    raise ValueError('相同字形被标成了不同汉字，请复核')
                char_groups[pixel_hash] = g['char']
                manifest.append({'id':ident, 'char':g['char'], 'style':style, 'split':split_for_char(g['char']),
                    'target':path, 'target_sha256':hashlib.sha256(target).hexdigest(),
                    'source_sha256':doc['source_sha256'], 'source_seal_id':seal.id,
                    'source_annotation_id':annotation.id, 'annotator':doc['annotator'],
                    'box':g['box'], 'polarity':g['polarity'], 'mirrored':g['mirrored'],
                    'reviewed':True, 'provenance':'human_labelled_seal_crop',
                    'old_denoising_split':source.details.get('dataset_split','unassigned')})
        if not manifest: raise ValueError('该风格还没有经人工核对的单字，不能生成训练集')
        z.writestr('manifest.jsonl', '\n'.join(json.dumps(r,ensure_ascii=False) for r in manifest)+'\n')
        z.writestr('README.txt', 'Human-labelled single glyph targets. White=stroke, black=background.\n'
                   'Splits are by Unicode character, separate from the denoising task.\n'
                   'Run train_font.py with a locally available source font.\n'
                   'These targets retain observed damage; they are not recovered originals.\n')
    return buf.getvalue()


def source_font():
    configured = os.environ.get('FONT_CONTENT_FONT')
    candidates = [Path(configured)] if configured else [Path('C:/Windows/Fonts/NotoSansSC-VF.ttf')]
    for p in candidates:
        if p.is_file(): return p
    raise RuntimeError('请配置FONT_CONTENT_FONT为包含目标汉字的字体文件')


def render_char(font_path, char, size=128):
    # Never silently generate .notdef boxes for unsupported text.
    from fontTools.ttLib import TTFont
    with TTFont(str(font_path), fontNumber=0) as font:
        if ord(char) not in font.getBestCmap(): raise ValueError(f'内容字体不支持汉字：{char}')
    font = ImageFont.truetype(str(font_path), size-24)
    box = font.getbbox(char)
    image = Image.new('L',(size,size),0)
    width,height = box[2]-box[0], box[3]-box[1]
    ImageDraw.Draw(image).text(((size-width)//2-box[0],(size-height)//2-box[1]),char,font=font,fill=255)
    return image


def models():
    result = []
    folder = ROOT/'models/font-generation'
    for p in sorted(folder.glob('*/model.json')):
        try:
            card = json.loads(p.read_text(encoding='utf-8'))
            weights = p.parent/'generator.ts'
            if card['model_sha256'] != hashlib.sha256(weights.read_bytes()).hexdigest(): continue
            result.append({'id':p.parent.name, 'style':card['style'], 'provenance':card['provenance'],
                           'demo_only':card['provenance'] != 'human_labelled_seal_crop',
                           'train_characters':card['train_characters'], 'test':card['test'],
                           'model_sha256':card['model_sha256']})
        except (OSError,ValueError,KeyError): continue
    return result


def generate(model_id, text):
    if model_id not in {m['id'] for m in models()}: raise ValueError('生成模型不存在或校验失败')
    if not all(0x3400 <= ord(c) <= 0x9fff or 0x20000 <= ord(c) <= 0x323af for c in text):
        raise ValueError('当前字形基线仅接受汉字，请去除空格、标点和其他字符')
    import torch
    folder = ROOT/'models/font-generation'/model_id
    card = json.loads((folder/'model.json').read_text(encoding='utf-8'))
    path = source_font()
    if hashlib.sha256(path.read_bytes()).hexdigest() != card['content_font_sha256']:
        raise RuntimeError('内容字体与训练时不同，请配置相同的FONT_CONTENT_FONT')
    tensors = [torch.from_numpy(np.asarray(render_char(path,c),dtype=np.float32).copy()/255.)[None] for c in text]
    model = torch.jit.load(str(folder/'generator.ts'),map_location='cpu').eval()
    with torch.inference_mode(): result = model(torch.stack(tensors))
    if result.shape != (len(text),1,128,128) or not torch.isfinite(result).all():
        raise RuntimeError('字形生成模型输出无效')
    out = Image.new('RGB',(len(text)*144+16,160),'#f5efdf')
    for i,pred in enumerate(result):
        alpha = Image.fromarray((pred[0].clamp(0,1).numpy()*255).round().astype('uint8'),'L')
        out.paste(Image.new('RGB',(128,128),'#a7352d'),(16+i*144,16),alpha)
    buf = io.BytesIO(); out.save(buf,'PNG')
    return buf.getvalue(), card
