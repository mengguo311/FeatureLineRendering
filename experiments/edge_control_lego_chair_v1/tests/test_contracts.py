import sys, unittest, tempfile
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from adapter import inspect_ply, stable_uids, dc_project, permission_audit

class Contracts(unittest.TestCase):
    def test_full_sh_header_before_load(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/'m.ply'
            p.write_text('ply\nformat ascii 1.0\nelement vertex 2\n'+''.join('property float f_rest_%d\n'%i for i in range(45))+'end_header\n')
            self.assertEqual(inspect_ply(p,3)['degree'],3)
            with self.assertRaises(ValueError):inspect_ply(p,0)
    def test_uid_sha_and_row(self):
        a=stable_uids('abc',4); self.assertEqual(len(set(a)),4)
        self.assertEqual(a[3],'abc:3'); self.assertNotEqual(a,stable_uids('def',4))
    def test_projection_selected_only(self):
        import torch
        c=torch.tensor([[-.2,.4,1.4],[.3,.5,.7]])
        d=(c-.5)/.28209479177387814
        p=dc_project(d,[0]);np.testing.assert_allclose((.5+.28209479177387814*p).numpy(),[[0,.4,1],[.3,.5,.7]],atol=1e-6)
        self.assertTrue(torch.equal(p[1],d[1]))
    def test_freeze_fail(self):
        a={'xyz':np.zeros((2,3)), 'rest':np.ones((2,15,3)), 'dc':np.zeros((2,1,3)), 'scale':np.zeros((2,3)), 'rotation':np.zeros((2,4)), 'opacity':np.zeros((2,1))}
        b={k:v.copy() for k,v in a.items()}; b['dc'][0]=1
        self.assertTrue(permission_audit(a,b,[0],False)['pass'])
        b['rest'][0,0,0]=2
        self.assertFalse(permission_audit(a,b,[0],False)['pass'])
    def test_holdout_needs_real_freeze_not_existing_path(self):
        from data import load_reference
        entry={'role':'edit-holdout','original_path':'/home/u00134/cglib/data/full/chair/train/r_0.png'}
        with self.assertRaises(PermissionError):load_reference(entry)
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/'fake.json';p.write_text('{}')
            with self.assertRaises(PermissionError):load_reference(entry,p)

if __name__=='__main__':unittest.main()
