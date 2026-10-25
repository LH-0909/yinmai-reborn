import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from PIL import Image
from training.audit_dataset import page_group, run


class AuditTests(unittest.TestCase):
    def test_page_group_keeps_all_crops_from_same_page_together(self):
        self.assertEqual(page_group(Path('tzsf_yt_p0001_01.png')), 'tzsf_yt_p0001')
        self.assertEqual(page_group(Path('tzsf_yt_p0001_99.png')), 'tzsf_yt_p0001')
        self.assertNotEqual(page_group(Path('tzsf_yt_p0002_01.png')), 'tzsf_yt_p0001')

    def test_audit_preserves_source_and_excludes_sidecars_duplicates_and_small(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder); source=root/'source';source.mkdir();out=root/'audit'
            Image.new('RGB',(64,64),'red').save(source/'book_p0001_01.png')
            Image.new('RGB',(64,64),'green').save(source/'book_p0001_02.png')
            Image.new('RGB',(64,64),'red').save(source/'book_p0002_01.png')
            Image.new('RGB',(10,10),'blue').save(source/'book_p0003_01.png')
            (source/'._book_p0001_01.png').write_bytes(b'AppleDouble')
            (source/'broken.png').write_bytes(b'not an image')
            before={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in source.iterdir()}
            run(source,out,workers=2)
            rows=[json.loads(line) for line in (out/'manifest.jsonl').read_text(encoding='utf-8').splitlines()]
            by_name={r['name']:r for r in rows}
            self.assertEqual(len(rows),5)
            self.assertEqual(by_name['book_p0002_01.png']['status'],'exact_duplicate')
            self.assertEqual(by_name['book_p0003_01.png']['split'],'excluded')
            self.assertEqual(by_name['broken.png']['status'],'decode_error')
            self.assertEqual(by_name['book_p0001_01.png']['split'],by_name['book_p0001_02.png']['split'])
            self.assertEqual(before,{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in source.iterdir()})

    def test_reject_output_inside_source(self):
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaises(ValueError):run(Path(folder),Path(folder)/'new')

    def test_training_manifest_relative_paths_are_portable_and_hash_checked(self):
        from training.train_denoiser import load_split
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);(root/'manifests').mkdir();(root/'images/train').mkdir(parents=True)
            image=root/'images/train/a.png';Image.new('RGB',(64,80),'red').save(image)
            row={'path':'../images/train/a.png','name':'a.png','sha256':hashlib.sha256(image.read_bytes()).hexdigest()}
            manifest=root/'manifests/train.jsonl';manifest.write_text(json.dumps(row)+'\n',encoding='utf-8')
            images,masks,rows=load_split(manifest,1,19,96)
            self.assertEqual(tuple(images.shape),(1,3,96,96));self.assertEqual(len(rows),1)
            self.assertGreater(float(masks.sum()),0)
            row['sha256']='0'*64;manifest.write_text(json.dumps(row)+'\n',encoding='utf-8')
            with self.assertRaises(ValueError):load_split(manifest,1,19,96)


if __name__=='__main__':unittest.main()
