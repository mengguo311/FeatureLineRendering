import tempfile,unittest
from pathlib import Path
import numpy as np
import cv2

class VerificationTests(unittest.TestCase):
    def test_compare_decodes_and_rejects_changed_scientific_outputs(self):
        from scripts.verify_topk_layered_probe import compare_runs
        with tempfile.TemporaryDirectory() as td:
            a,b=Path(td)/'a',Path(td)/'b';a.mkdir();b.mkdir()
            for d in [a,b]:
                np.savez_compressed(d/'data.npz',a=np.arange(3))
                cv2.imwrite(str(d/'view.png'),np.zeros((10,12,3),'u1'))
                (d/'metrics.json').write_text('{"passed": true}\n')
            r=compare_runs(a,b);self.assertTrue(r['passed']);self.assertEqual(r['decoded_pngs'],2)
            np.savez_compressed(b/'data.npz',a=np.arange(3)+1)
            self.assertFalse(compare_runs(a,b)['passed'])
            (b/'view.png').write_bytes(b'not PNG')
            self.assertFalse(compare_runs(a,b)['passed'])

    def test_npz_semantics_detect_weight_and_missing_tail_corruption(self):
        from scripts.verify_topk_layered_probe import npz_semantics
        ids=np.full((2,3,16),-1,'i8');ids[...,0]=0
        w=np.zeros_like(ids,dtype='f4');w[...,0]=.8
        T=np.zeros_like(w);T[...,0]=1
        z=np.zeros_like(w);z[...,0]=2
        data=dict(ids=ids,w=w,T=T,alpha=w.copy(),z=z,rgb=np.zeros((*ids.shape,3),'f4'),native_alpha=np.full((2,3),.8),final_T=np.full((2,3),.2),tail_alpha=np.zeros((2,3)),K=np.eye(3),w2c=np.eye(4))
        for k in [4,8,16]:data[f'A{k}']=w[...,:k].sum(-1);data[f'missing{k}']=data['native_alpha']-data[f'A{k}']
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'a.npz';np.savez_compressed(p,**data)
            self.assertTrue(npz_semantics(p,1)['passed'])
            data['w'][0,0,0]=.7;np.savez_compressed(p,**data)
            self.assertFalse(npz_semantics(p,1)['passed'])
            data['w'][0,0,0]=.8;data['missing8'][0,0]=.2;np.savez_compressed(p,**data)
            self.assertFalse(npz_semantics(p,1)['passed'])

    def test_verifier_cli_exposes_reached_stage_verification(self):
        import subprocess,sys
        script=Path(__file__).resolve().parents[1]/'scripts/verify_topk_layered_probe.py'
        r=subprocess.run([sys.executable,str(script),'--help'],capture_output=True,text=True)
        self.assertEqual(r.returncode,0,r.stderr);self.assertIn('--root',r.stdout)
