"""Read-only inventory of uncurated font materials. Never assigns labels/splits."""
import argparse
from collections import Counter, defaultdict
import csv
import hashlib
import json
from pathlib import Path
from PIL import Image


def inventory(root, output):
    root = Path(root).resolve()
    output = Path(output).resolve()
    if not root.is_dir():
        raise ValueError('Material directory does not exist')
    if output == root or root in output.parents:
        raise ValueError('Write audit output outside the read-only material directory')
    output.mkdir(parents=True, exist_ok=True)
    if (output/'inventory.csv').exists():
        raise ValueError('Audit already exists; use a new directory to preserve review records')
    rows = []
    hashes = defaultdict(list)
    for path in sorted(root.rglob('*')):
        if not path.is_file() or path.name.startswith('._'):
            continue
        if path.suffix.lower() not in {'.png','.jpg','.jpeg','.webp','.tif','.tiff','.bmp'}:
            continue
        row = {'file':path.relative_to(root).as_posix(), 'sha256':'', 'width':'', 'height':'',
               'readable':False, 'quality_flag':'', 'image_type':'unreviewed',
               'character':'', 'style':'', 'character_boxes':'',
               'human_verified':False, 'font_split':'unassigned', 'error':''}
        try:
            row['sha256'] = hashlib.sha256(path.read_bytes()).hexdigest()
            with Image.open(path) as image:
                image.load()
                row['width'], row['height'] = image.size
            row['readable'] = True
            row['quality_flag'] = 'short_edge_under_32_review_only' if min(row['width'],row['height']) < 32 else ''
            hashes[row['sha256']].append(row['file'])
        except (OSError,ValueError) as exc:
            row['error'] = type(exc).__name__ + ': ' + str(exc)
        rows.append(row)
    with (output/'inventory.csv').open('w',encoding='utf-8-sig',newline='') as stream:
        writer = csv.DictWriter(stream,fieldnames=list(rows[0]) if rows else [
            'file','sha256','width','height','readable','quality_flag','image_type',
            'character','style','character_boxes','human_verified','font_split','error'])
        writer.writeheader();writer.writerows(rows)
    duplicates = [files for files in hashes.values() if len(files)>1]
    report = {'task':'font_style_generation_material_inventory', 'root':str(root),
        'material_state':'uncurated_images', 'source_images_modified':False,
        'directory_names_interpreted_as_training_splits':False,
        'image_files':len(rows), 'readable_images':sum(r['readable'] for r in rows),
        'unreadable_images':sum(not r['readable'] for r in rows),
        'short_edge_under_32':sum(bool(r['quality_flag']) for r in rows),
        'byte_duplicate_groups':len(duplicates),
        'byte_duplicate_extra_copies':sum(len(g)-1 for g in duplicates),
        'character_labels_assigned':0,'style_labels_assigned':0,'font_split_assigned':False,
        'ready_for_seal_font_training':False,
        'next_required':['image-type review: whole seal / single character / other',
                         'select one coherent target style',
                         'single-character boxes and checked transcription',
                         'duplicate and character identity review before final split'],
        'limitations':['Byte hashes do not detect all visual duplicates',
                       'Readability does not establish historical character identity or training suitability',
                       'Old train/validation/test folder names are ignored for the font task']}
    (output/'summary.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    (output/'byte-duplicates.json').write_text(json.dumps(duplicates,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False,indent=2))


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',required=True)
    parser.add_argument('--out',required=True)
    args=parser.parse_args()
    inventory(args.root,args.out)
