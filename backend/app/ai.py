"""Optional trained TorchScript plugins. No random/untrained fallback."""
import hashlib
import importlib.util
import json
import os
from functools import lru_cache
from pathlib import Path
import cv2
import numpy as np

def status():
    result = {'torch_installed': importlib.util.find_spec('torch') is not None}
    for name, env in [('restoration', 'RESTORE_MODEL_PATH'), ('recognition', 'OCR_MODEL_PATH')]:
        p = Path(os.environ.get(env, '__not_configured__'))
        configured = bool(os.environ.get(env)) and p.is_file()
        result[name] = {'configured': configured, 'state': 'configured_not_verified' if configured else 'unavailable',
            'reason': '需实际加载模型并推理验证' if configured else '未提供经训练的TorchScript权重；没有生成AI结果'}
    return result

@lru_cache(maxsize=2)
def load_model(path):
    import torch
    model = torch.jit.load(path, map_location='cpu').eval()
    return model, hashlib.sha256(Path(path).read_bytes()).hexdigest()

def infer(image, task):
    env = 'RESTORE_MODEL_PATH' if task == 'restoration' else 'OCR_MODEL_PATH'
    path = os.environ.get(env)
    if not path or not Path(path).is_file():
        raise RuntimeError('未配置经训练的模型权重，此AI模块尚不可用')
    import torch
    model, digest = load_model(path)
    rgb = cv2.cvtColor(cv2.resize(image, (256, 256)), cv2.COLOR_BGR2RGB)
    tensor = torch.from_numpy(np.transpose(rgb.astype(np.float32) / 255., (2, 0, 1))).unsqueeze(0)
    with torch.inference_mode():
        prediction = model(tensor)
    provenance = {'engine': 'PyTorch/TorchScript', 'model_sha256': digest, 'ai_inference': True,
        'human_review_required': True, 'input_shape': [1, 3, 256, 256]}
    if task == 'restoration':
        if prediction.shape != tensor.shape or not torch.isfinite(prediction).all():
            raise ValueError('修复模型输出必须为有限数值NCHW RGB图像')
        result = (prediction[0].clamp(0, 1).permute(1, 2, 0).cpu().numpy() * 255).astype(np.uint8)
        return cv2.cvtColor(result, cv2.COLOR_RGB2BGR), provenance
    labels_path = os.environ.get('OCR_LABELS_PATH')
    if not labels_path:
        raise RuntimeError('缺少识别模型字符表OCR_LABELS_PATH')
    labels = json.loads(Path(labels_path).read_text(encoding='utf-8'))
    if not isinstance(labels, list) or prediction.ndim != 2 or prediction.shape != (1, len(labels)) or not torch.isfinite(prediction).all():
        raise ValueError('当前识别插件仅支持单字分类[1,C]，字符表须与输出类别一一对应')
    probs = prediction.softmax(dim=-1)[0]
    value, index = probs.max(dim=-1)
    return {'character': labels[int(index)], 'score': float(value), 'scope': '单字分类；非多字古印OCR', **provenance}, provenance
