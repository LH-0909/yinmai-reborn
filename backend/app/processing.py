"""Deterministic OpenCV processing; never described as learned AI."""
import io
import cv2
import numpy as np
from PIL import Image, ImageOps, UnidentifiedImageError

MAX_BYTES = 15 * 1024 * 1024
MAX_PIXELS = 20_000_000

def decode_image(data: bytes) -> np.ndarray:
    if not data or len(data) > MAX_BYTES:
        raise ValueError('图片为空或超过15MB')
    try:
        with Image.open(io.BytesIO(data)) as im:
            if im.format not in ('PNG', 'JPEG', 'WEBP'):
                raise ValueError('仅支持 PNG、JPEG、WebP')
            if im.width * im.height > MAX_PIXELS or min(im.size) < 16:
                raise ValueError('图片须至少16×16，最多2000万像素')
            im = ImageOps.exif_transpose(im).convert('RGB')
            im.thumbnail((2048, 2048))
            return cv2.cvtColor(np.array(im), cv2.COLOR_RGB2BGR)
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as exc:
        raise ValueError('无法解码图片') from exc

def encode_png(image: np.ndarray) -> bytes:
    ok, data = cv2.imencode('.png', image)
    if not ok:
        raise ValueError('PNG编码失败')
    return data.tobytes()

def extract_mask(image: np.ndarray, threshold: int = 0) -> np.ndarray:
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    red = cv2.inRange(hsv, (0, 65, 35), (15, 255, 255)) | cv2.inRange(hsv, (165, 65, 35), (180, 255, 255))
    if np.count_nonzero(red) / red.size > 0.005 and not threshold:
        return red
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    _, mask = cv2.threshold(gray, threshold, 255, cv2.THRESH_BINARY_INV | (cv2.THRESH_OTSU if threshold == 0 else 0))
    return mask

def process(image: np.ndarray, operation: str, strength: int, threshold: int, mirror: bool):
    mask = extract_mask(image, threshold)
    if operation == 'clean':
        count, labels, stats, _ = cv2.connectedComponentsWithStats(mask)
        cleaned = np.zeros_like(mask)
        for i in range(1, count):
            if stats[i, cv2.CC_STAT_AREA] >= strength * 3:
                cleaned[labels == i] = 255
        mask = cleaned
    elif operation == 'repair':
        # A small morphological close reconnects nearby ink; it does not infer lost characters.
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * strength + 1, 2 * strength + 1))
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
    if mirror:
        mask = cv2.flip(mask, 1)
    result = np.full_like(image, 248)
    result[mask > 0] = (49, 51, 166)
    return result, {'engine': 'OpenCV', 'operation': operation, 'strength': strength,
        'threshold': threshold, 'mirror': mirror, 'ink_ratio': round(float(np.count_nonzero(mask) / mask.size), 5),
        'ai_inference': False, 'limitation': '形态学处理不能推断失传篆字，结果须由人工确认'}
