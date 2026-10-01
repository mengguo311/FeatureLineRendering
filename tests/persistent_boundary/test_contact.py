"""F-only contact-sheet access guard; synthetic fixture is not scene evidence."""
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from PIL import Image
from src.persistent_boundary.contact import build_f_contact_sheet, F_INDICES


class ContactSheetTest(unittest.TestCase):
    def test_reads_only_declared_construction_frames(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            images = root / 'data/full/lego/train'
            images.mkdir(parents=True)
            meta = root / 'data/full/lego/transforms_train.json'
            meta.write_text(json.dumps({'camera_angle_x': 1.0, 'frames': [
                {'file_path': f'./train/r_{i}'} for i in range(100)]}))
            for index in F_INDICES:
                Image.new('RGBA', (16, 16), (index, 0, 0, 255)).save(images / f'r_{index}.png')
            # Other indexed images do not exist; an accidental C/DEV/TEST open fails.
            output = root / 'sheet.png'
            report = build_f_contact_sheet(root, 'lego', output, tile_width=16, columns=4)
            self.assertEqual(report['frame_indices'], list(F_INDICES))
            self.assertEqual(len(report['sources']), 8)
            with Image.open(output) as sheet:
                self.assertEqual(sheet.size, (64, 80))
            self.assertTrue(all(Path(p).name in {f'r_{i}.png' for i in F_INDICES}
                                for p in report['sources']))


if __name__ == '__main__':
    unittest.main()
