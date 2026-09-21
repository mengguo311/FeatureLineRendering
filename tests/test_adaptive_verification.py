import tempfile
import unittest
from pathlib import Path
import numpy as np


class AdaptiveVerificationTests(unittest.TestCase):
    def test_saved_csr_semantics_detect_tail_and_diagnostic_corruption(self):
        from scripts.verify_adaptive_mass_probe import verify_npz
        e=dict(offsets=np.array([0,2,2]),ids=np.array([1,0]),stream_position=np.array([0,1]),
               z=np.array([2,2]),alpha=np.array([.5,.5]),T=np.array([1,.5]),w=np.array([.5,.25]),
               rgb=np.ones((2,3))*.2,tail_rgb=np.zeros((1,2,3)),tail_alpha=np.zeros((1,2)),
               final_T=np.array([[.25,1]]),native_final_T=np.array([[.25,1]]),count=np.array([[2,0]]),
               native_depths=np.array([2,2]),native_point_list=np.array([1,0]),native_ranges=np.array([[0,2]]),
               stock_white=np.array([[[.4]*3,[1]*3]]),stock_black=np.array([[[.15]*3,[0]*3]]),
               camera_K=np.eye(3),w2c=np.eye(4),A=np.array([[.75,0]]),missing=np.zeros((1,2)))
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'fixture.npz';np.savez_compressed(p,**e)
            self.assertTrue(verify_npz(p,.9,32)['passed'])
            e['tail_alpha'][0,0]=.2;np.savez_compressed(p,**e)
            self.assertFalse(verify_npz(p,.9,32)['passed'])
            e['tail_alpha'][0,0]=0;e['missing'][0,0]=.1;np.savez_compressed(p,**e)
            self.assertFalse(verify_npz(p,.9,32)['passed'])

    def test_comparison_requires_equal_inventory_bytes_and_png_decode(self):
        from scripts.verify_adaptive_mass_probe import compare_outputs
        import cv2
        with tempfile.TemporaryDirectory() as td:
            a,b=Path(td)/'a',Path(td)/'b';a.mkdir();b.mkdir()
            for p in [a,b]:
                np.savez_compressed(p/'x.npz',x=np.arange(3))
                cv2.imwrite(str(p/'x.png'),np.zeros((5,5,3),'u1'))
                (p/'x.json').write_text('{}\n')
            self.assertTrue(compare_outputs(a,b)['passed'])
            (b/'x.png').write_bytes(b'invalid')
            self.assertFalse(compare_outputs(a,b)['passed'])
            (b/'x.json').unlink()
            self.assertFalse(compare_outputs(a,b)['passed'])

    def test_verifier_cli_exposes_isolated_root(self):
        import subprocess,sys
        p=Path(__file__).resolve().parents[1]/'scripts/verify_adaptive_mass_probe.py'
        result=subprocess.run([sys.executable,str(p),'--help'],capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr);self.assertIn('--root',result.stdout)
