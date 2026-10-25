import cv2
import numpy as np
import trimesh
from .processing import extract_mask

def make_seal(image, width_mm=30., base_mm=8., relief_mm=1.2, resolution=96, style='zhu', mirror=True):
    mask = cv2.resize(extract_mask(image), (resolution, resolution), interpolation=cv2.INTER_AREA) / 255.
    if mask.max() == 0:
        raise ValueError('图片中未检测到印文，无法生成印面')
    if mirror:
        mask = np.fliplr(mask)
    ink = mask >= 0.5
    height = base_mm + relief_mm * (ink if style == 'zhu' else ~ink)
    n = resolution
    xs = np.linspace(-width_mm / 2, width_mm / 2, n)
    ys = np.linspace(-width_mm / 2, width_mm / 2, n)
    xx, yy = np.meshgrid(xs, ys)
    vertices = np.vstack([np.column_stack([xx.ravel(), yy.ravel(), height.ravel()]),
                          np.column_stack([xx.ravel(), yy.ravel(), np.zeros(n * n)])])
    faces = []
    offset = n * n
    for j in range(n - 1):
        for i in range(n - 1):
            a = j * n + i
            b, c, d = a + 1, a + n, a + n + 1
            faces.extend([(a, b, d), (a, d, c), (offset + a, offset + d, offset + b), (offset + a, offset + c, offset + d)])
    ring = list(range(n)) + [j * n + n - 1 for j in range(1, n)] + list(range(n * n - 2, n * (n - 1) - 1, -1)) + [j * n for j in range(n - 2, 0, -1)]
    for a, b in zip(ring, ring[1:] + ring[:1]):
        faces.extend([(a, offset + a, offset + b), (a, offset + b, b)])
    mesh = trimesh.Trimesh(vertices, faces, process=True)
    # Face winding is constructed explicitly above; inspect rather than silently repair it.
    if not mesh.is_watertight or mesh.volume <= 0 or not mesh.is_winding_consistent:
        raise ValueError('网格完整性检查失败，已拒绝导出')
    return mesh, {'engine': 'heightfield-to-STL', 'units': 'mm', 'width_mm': width_mm,
        'base_mm': base_mm, 'relief_mm': relief_mm, 'resolution': resolution, 'style': style,
        'mirror': mirror, 'watertight': bool(mesh.is_watertight), 'winding_consistent': bool(mesh.is_winding_consistent),
        'volume_mm3': round(float(mesh.volume), 3), 'faces': len(mesh.faces), 'vertices': len(mesh.vertices),
        'bounds_mm': mesh.bounds.tolist(), 'ai_inference': False,
        'limitation': '由二维印文构建的印面浮雕，不是文物真实形制复原；STL本身不携带单位'}
