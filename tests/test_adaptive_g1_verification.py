import unittest
import numpy as np


class G1VerificationTests(unittest.TestCase):
    def test_camera_audit_rejects_valid_matrix_from_wrong_frozen_view(self):
        from scripts.verify_adaptive_g1 import camera_semantics
        camera=dict(native_K=[[40,0,3.5],[0,50,2.5],[0,0,1]],w2c=np.eye(4).tolist(),native_height=6,native_width=8)
        source=dict(camera_K=np.array(camera['native_K']),w2c=np.eye(4),native_alpha=np.ones((6,8)))
        self.assertTrue(camera_semantics(source,camera))
        source['camera_K'][0,2]+=1
        self.assertFalse(camera_semantics(source,camera))
        source['camera_K']=np.array(camera['native_K']);source['w2c'][0,3]=1
        self.assertFalse(camera_semantics(source,camera))

    def test_layout_verifier_rejects_changed_science_bytes(self):
        import tempfile,json,hashlib
        from pathlib import Path
        from scripts.verify_adaptive_g1 import layout_semantics
        with tempfile.TemporaryDirectory() as tmp:
            run=Path(tmp);(run/'diagnostics').mkdir();p=run/'science.npz';p.write_bytes(b'original')
            manifest=dict(science_unchanged=True,science_sha256={'science.npz':hashlib.sha256(p.read_bytes()).hexdigest()},png_sha256={})
            (run/'diagnostics/LAYOUT.json').write_text(json.dumps(manifest))
            self.assertTrue(layout_semantics(run))
            p.write_bytes(b'changed')
            self.assertFalse(layout_semantics(run))

    def test_layer_verifier_rejects_wrong_assignment_and_lost_overflow(self):
        from scripts.verify_adaptive_g1 import layer_semantics
        from src.adaptive_layers import compress_layers
        e=dict(offsets=np.array([0,5]),ids=np.arange(5),z=np.array([2.,3,4,5,6]),w=np.ones(5)*.15,
               rgb=np.ones((5,3)),tail_alpha=np.array([[.2]]),tail_rgb=np.ones((1,1,3))*.2)
        l=compress_layers(e,np.array([[.95]]));data={'events.'+k:v for k,v in e.items() if k!='rgb'};data.update({'layers.'+k:v for k,v in l.items()})
        self.assertTrue(layer_semantics(data)['passed'])
        bad={k:v.copy() for k,v in data.items()};bad['layers.assignment'][2]=1
        self.assertFalse(layer_semantics(bad)['passed'])
        bad={k:v.copy() for k,v in data.items()};bad['layers.overflow_mass'][:]=0
        self.assertFalse(layer_semantics(bad)['passed'])

    def test_band_verifier_rejects_below_threshold_ink_and_changed_soft_field(self):
        from scripts.verify_adaptive_g1 import band_semantics
        response=np.array([[.1,.5,.9,1.]])
        field=dict(response=response,normalized_soft=response/2,thresholds=np.array([np.percentile(response,[95,70]),np.percentile(response,[90,60])]))
        for grid in ['95_70','90_60']:
            field['band_'+grid]=np.array([[0,0,grid=='90_60',1]],bool);field['center_'+grid]=field['band_'+grid].copy()
            field['nms_'+grid]=np.ones((1,4),bool);field['anchors_'+grid]=np.array([[0,0,0,1]],bool)
        self.assertTrue(band_semantics(response,field,2)['passed'])
        bad={k:v.copy() for k,v in field.items()};bad['band_95_70'][0,0]=True
        self.assertFalse(band_semantics(response,bad,2)['passed'])
        bad={k:v.copy() for k,v in field.items()};bad['normalized_soft'][:]=1
        self.assertFalse(band_semantics(response,bad,2)['passed'])

    def test_g1_verifier_cli_exposes_reached_stage_audit(self):
        import subprocess,sys
        from pathlib import Path
        p=Path(__file__).resolve().parents[1]/'scripts/verify_adaptive_g1.py'
        r=subprocess.run([sys.executable,str(p),'--help'],capture_output=True,text=True)
        self.assertEqual(r.returncode,0,r.stderr);self.assertIn('--root',r.stdout)
