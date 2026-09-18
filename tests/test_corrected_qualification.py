import copy,json,tempfile,unittest,hashlib
from pathlib import Path
import numpy as np
import cv2
from test_multiscene import CFG,asset_fixture

class CorrectedQualificationTests(unittest.TestCase):
    def test_quality_and_all_doses_use_native_area_and_preserve_thresholds(self):
        from src.corrected_qualification import measure_quality,qualify_parent
        from src.corrected_sampling import stock_intrinsics,resize_intrinsics,render_measurement
        a=asset_fixture();cfg=copy.deepcopy(CFG);cfg['splits']['TRAIN']=[1]
        cfg['visuals']['fixed_train']=[1]
        K=stock_intrinsics(.72,.72);small=resize_intrinsics(K,(800,800),(400,400))
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);photo=root/'ref.png';im=np.full((800,800,4),255,'u1');cv2.imwrite(str(photo),im)
            camera=dict(index=1,K=small.tolist(),native_K=K.tolist(),w2c=np.eye(4).tolist(),FoVx=.72,FoVy=.72,path=str(photo),sha256=hashlib.sha256(photo.read_bytes()).hexdigest())
            cameras=[dict(camera,split=s) for s in ['train','val']]
            report=measure_quality(a,cameras,cfg,root/'quality')
            self.assertEqual(len(report['rows']),4);self.assertEqual(len(report['calibration']),2)
            self.assertTrue(all(r['passed'] for r in report['calibration']))
            with np.load(root/'quality/native/train_001.npz') as data:
                np.testing.assert_array_equal(data['rgb_1'],render_measurement(a,K,np.eye(4),1))
            controlled=qualify_parent(a,cameras[:1],cfg,root/'controlled')
            self.assertEqual(len(controlled['variants']),9)
            self.assertEqual(sum(len(v['rows']) for v in controlled['variants']),18)
            self.assertTrue(all(r['passed'] for v in controlled['variants'] for r in v['calibration']))
            self.assertGreater(controlled['delta'],0)
            self.assertEqual(cfg['eligibility'],CFG['eligibility'])
            self.assertEqual(report['sampling'],'native800_area400')
            # Existing paths cannot silently overwrite results.
            with self.assertRaises(FileExistsError):measure_quality(a,cameras,cfg,root/'quality')
