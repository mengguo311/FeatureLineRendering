"""Artifact verification must detect actual corruption, not just existence."""
from pathlib import Path
import tempfile
import unittest
from PIL import Image


class VerifyTests(unittest.TestCase):
    def test_inventory_detects_changed_deleted_and_unlisted_outputs(self):
        from src.multiscene_verify import inventory,verify_inventory
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'ignored.npz').write_bytes(b'array')
            (root/'report.json').write_text('{}\n')
            records=inventory(root,exclude=['report.json'])
            self.assertEqual(len(records),1)
            self.assertEqual(records[0]['bytes'],5)
            self.assertTrue(verify_inventory(root,records,exclude=['report.json']))
            (root/'ignored.npz').write_bytes(b'other')
            with self.assertRaisesRegex(ValueError,'hash'):verify_inventory(root,records,exclude=['report.json'])
            (root/'ignored.npz').write_bytes(b'array');(root/'extra').write_bytes(b'x')
            with self.assertRaisesRegex(ValueError,'file set'):verify_inventory(root,records,exclude=['report.json'])
            (root/'extra').unlink();(root/'ignored.npz').unlink()
            with self.assertRaisesRegex(ValueError,'file set'):verify_inventory(root,records,exclude=['report.json'])

    def test_png_verification_decodes_pixels_and_rejects_truncated_data(self):
        from src.multiscene_verify import verify_png
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'actual.png'
            Image.new('RGB',(12,7),(20,30,40)).save(path)
            self.assertEqual(verify_png(path)['size'],[12,7])
            path.write_bytes(path.read_bytes()[:45])
            with self.assertRaises(Exception):verify_png(path)


if __name__=='__main__':unittest.main()
