import json
import unittest
from pathlib import Path
import numpy as np
from transfer import camera_from_transform, best_axis_null, original_row_labels

class TransferTests(unittest.TestCase):
    def test_camera_convention_matches_frozen_ficus_registry(self):
        base=Path('/home/u00134/3dgs_line/tier1/out/multiscene_foundation')
        t=json.loads((base/'inputs/ficus/seed_1729/transforms_train.json').read_text())
        f=next(f for f in t['frames'] if f['file_path'].endswith('/r_80'))
        c=camera_from_transform(f,t['camera_angle_x'],800,'train_r_80')
        registry=json.loads(Path('/mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_multiview05_v01/REGISTRY.json').read_text())
        old=next(c for c in registry['scenes']['ficus']['cameras'] if c['view']=='train_r_80')
        np.testing.assert_allclose(c['extrinsic'],old['extrinsic'],atol=1e-11)
        self.assertAlmostEqual(c['fx'],old['fx'],places=7)
        self.assertEqual(c['cx'],old['cx'])
    def test_axis_oracle_is_same_count_and_exact_original_rows(self):
        xyz=np.array([[4,0,1],[1,4,2],[3,1,3],[0,3,4],[2,2,5]],float)
        chosen=np.array([True,True,False,False,False])
        null=best_axis_null(xyz,chosen)
        self.assertEqual(null['intersection'],2)
        self.assertEqual(null['axis'],'z')
        self.assertEqual(null['side'],'low')
        self.assertEqual(null['mask'].sum(),chosen.sum())
    def test_unknown_not_forced_into_cluster(self):
        labels=original_row_labels(np.array([0,2],dtype=np.uint8),np.array([True,False,True]))
        self.assertEqual(labels.tolist(),[0,255,2])
    def test_bad_label_lengths_are_rejected(self):
        with self.assertRaises(ValueError): original_row_labels(np.array([0],dtype=np.uint8),np.array([True,False,True]))

if __name__=='__main__':unittest.main()
