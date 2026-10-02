"""Synthetic production-integrity checks; no scene or CUDA access."""
import json
import tempfile
import unittest
from pathlib import Path

import numpy as np
from PIL import Image

from src.hybrid_raster_io import (
    atomic_json, canonical_hash, encode_video, hash_file, overlay_ink, panel,
    save_contact_sheet, seal_frame, valid_seal, validate_video, white_ink,
)

ROOT = Path(__file__).resolve().parents[1]
TMP = ROOT / 'out/hybrid_raster_evidence_v2/test_tmp'


class ProductionIOTests(unittest.TestCase):
    def setUp(self):
        TMP.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=TMP)
        self.base = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def test_vertical_frame_white_overlay_panel_atomic_seal(self):
        staging = self.base / 'staging'; staging.mkdir()
        ink = np.zeros((9, 11), np.float32); ink[4, 2:9] = .25
        rgb = np.full((9, 11, 3), .8, np.float32)
        white = white_ink(ink); over = overlay_ink(rgb, ink)
        self.assertEqual(white.shape, rgb.shape)
        self.assertTrue(np.array_equal(over[0, 0], [204, 204, 204]))
        self.assertTrue(np.array_equal(over[4, 4], [153, 153, 153]))
        self.assertTrue(np.array_equal(white[4, 4], [191, 191, 191]))
        sheet = panel([white, over], ['white', 'overlay'], columns=2, header=32)
        self.assertEqual(sheet.size, (22, 41))
        sheet.save(staging / 'panel.png')
        np.savez_compressed(staging / 'arrays.npz', ink=ink)
        context = {'config': canonical_hash({'p': 1}), 'camera': 'actual-camera'}
        result = seal_frame(staging, self.base / 'frame', context)
        self.assertEqual(set(result['files']), {'panel.png', 'arrays.npz'})
        self.assertTrue(valid_seal(self.base / 'frame', context))
        self.assertFalse(staging.exists())
        self.assertFalse(valid_seal(self.base / 'absent', context))

    def test_atomic_json_default_is_immutable_and_status_can_replace(self):
        p = self.base / 'status.json'
        atomic_json(p, {'state': 'first'})
        before = hash_file(p)
        with self.assertRaises(FileExistsError): atomic_json(p, {'state': 'second'})
        self.assertEqual(hash_file(p), before)
        atomic_json(p, {'state': 'second'}, replace=True)
        self.assertEqual(json.loads(p.read_text()), {'state': 'second'})
        self.assertEqual(canonical_hash({'b': 2, 'a': 1}), canonical_hash({'a': 1, 'b': 2}))
        with self.assertRaises(ValueError): canonical_hash({'bad': float('nan')})

    def test_restart_rejects_partial_corrupt_context_extra_and_existing_output(self):
        partial = self.base / 'partial'; partial.mkdir()
        (partial / 'data').write_bytes(b'incomplete')
        with self.assertRaises(ValueError): valid_seal(partial, {'p': 1})
        staging = self.base / 'staging'; staging.mkdir()
        (staging / 'data').write_bytes(b'complete')
        final = self.base / 'frame'; seal_frame(staging, final, {'p': 1})
        with self.assertRaises(ValueError): valid_seal(final, {'p': 2})
        (final / 'extra').write_bytes(b'unknown')
        with self.assertRaises(ValueError): valid_seal(final, {'p': 1})
        (final / 'extra').unlink()
        (final / 'data').write_bytes(b'corrupt')
        with self.assertRaises(ValueError): valid_seal(final, {'p': 1})
        other = self.base / 'other'; other.mkdir(); (other / 'data').write_bytes(b'new')
        with self.assertRaises(FileExistsError): seal_frame(other, final, {'p': 1})
        self.assertTrue(other.exists())

    def test_overlay_shape_and_invalid_values_rejected(self):
        with self.assertRaises(ValueError): overlay_ink(np.zeros((5, 7, 3)), np.zeros((7, 5)))
        with self.assertRaises(ValueError): white_ink(np.array([[np.nan]]))
        with self.assertRaises(ValueError): white_ink(np.array([[1.1]]))
        with self.assertRaises(ValueError): panel([np.zeros((5, 7, 3), np.uint8)], [])

    def test_contact_sheet_preserves_entire_native_tiles(self):
        paths = []
        for i in range(3):
            p = self.base / f'{i}.png'
            im = np.full((8, 10, 3), i * 70, np.uint8)
            im[7, 9] = [240, 20, i]
            Image.fromarray(im).save(p); paths.append(p)
        target = self.base / 'contact.png'
        info = save_contact_sheet(paths, target, labels=['0', '1', '2'], columns=2, header=32)
        with Image.open(target) as im:
            self.assertEqual(im.size, (20, 80))
            self.assertEqual(im.getpixel((9, 39)), (240, 20, 0))
            self.assertEqual(im.getpixel((9, 79)), (240, 20, 2))
        self.assertEqual(info['sha256'], hash_file(target))

    def _frames(self):
        return [np.full((16, 20, 3), [25 + i * 50, 20, 210 - i * 30], np.uint8) for i in range(3)]

    def test_video_promotes_only_after_complete_distinct_decode(self):
        target = self.base / 'valid.mp4'
        result = encode_video(self._frames(), target, fps=12, expected_frames=3)
        self.assertEqual(result['frames'], 3)
        self.assertEqual(result['distinct_frames'], 3)
        self.assertEqual(result['size'], [20, 16])
        self.assertEqual(result['sha256'], hash_file(target))
        with self.assertRaises(FileExistsError): encode_video(self._frames(), target, expected_frames=3)
        with self.assertRaises(ValueError): validate_video(target, expected_frames=4, expected_size=(20, 16))
        with self.assertRaises(ValueError): validate_video(target, expected_frames=3, expected_size=(18, 16))

    def test_repeated_corrupt_and_changed_dimension_video_are_not_promoted(self):
        target = self.base / 'repeat.mp4'
        with self.assertRaises(ValueError): encode_video([self._frames()[0]] * 3, target, expected_frames=3)
        self.assertFalse(target.exists())
        target = self.base / 'shape.mp4'
        with self.assertRaises(ValueError): encode_video([self._frames()[0], np.zeros((18, 20, 3), np.uint8)], target, expected_frames=2)
        self.assertFalse(target.exists())
        corrupt = self.base / 'corrupt.mp4'; corrupt.write_bytes(b'not a video')
        with self.assertRaises(ValueError): validate_video(corrupt, expected_frames=3, expected_size=(20, 16))


if __name__ == '__main__': unittest.main()
