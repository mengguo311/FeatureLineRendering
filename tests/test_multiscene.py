"""Synthetic foundation contracts; no measured scene values define these tests."""
import copy
import json
import tempfile
from pathlib import Path
import unittest
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
CFG=json.loads((ROOT/'out/multiscene_foundation/config.json').read_text())


def asset_fixture():
    return dict(mu=np.array([[0.,0.,3.],[.1,.2,3.2],[-.2,.1,2.8],[.3,-.1,3.1]],'f4'),
        scale=np.array([[.2,.1,.04]]*4,'f4'),quat=np.array([[1.,0,0,0]]*4,'f4'),
        opacity=np.array([[.8],[.4],[.7],[.5]],'f4'),sh=np.zeros((4,16,3),'f4'))


class MultisceneTests(unittest.TestCase):
    def test_renderer_aware_redistribution_and_moment_ladder(self):
        from src.multiscene import perturbation_specs,controlled_asset
        specs=perturbation_specs(CFG); self.assertEqual(len(specs),9)
        a=asset_fixture(); original=copy.deepcopy(a); selections=[]
        for spec in specs:
            child,parents,selected,minor=controlled_asset(a,spec,CFG)
            selections.append(selected)
            self.assertEqual(len(child['mu']),6);self.assertEqual(selected.sum(),2)
            self.assertEqual(minor.sum(),2)
            self.assertTrue(np.all(child['opacity']>0));self.assertTrue(np.all(child['opacity']<1))
            for i in np.flatnonzero(selected):
                idx=np.flatnonzero(parents==i); w=child['opacity'][idx,0].astype(float); w/=w.sum()
                center=np.sum(child['mu'][idx]*w[:,None],axis=0)
                np.testing.assert_allclose(center,a['mu'][i],atol=1e-7)
                covariance=np.zeros((3,3))
                for k,j in enumerate(idx):
                    d=child['mu'][j]-center
                    covariance+=w[k]*(np.diag(child['scale'][j].astype(float)**2)+np.outer(d,d))
                np.testing.assert_allclose(covariance,np.diag(a['scale'][i].astype(float)**2),atol=1e-8)
                if spec['family']=='redistribute':
                    c,b=child['opacity'][idx,0].astype(float); alpha=float(a['opacity'][i,0])
                    # Analytic derivative of the radial integrated error vanishes.
                    self.assertAlmostEqual((c+b-alpha)/2-(2*c*b+b*b-alpha*b)/3+c*b*b/4,0,places=7)
            for k in a: np.testing.assert_array_equal(a[k],original[k])
        for s in selections[1:]: np.testing.assert_array_equal(s,selections[0])

    def test_independent_eligibility_is_separate_and_requires_every_view(self):
        from src.multiscene import seed_eligibility,independent_eligibility
        rows=[dict(split=split,view=i,background=bg,valid=True,psnr_db=30.,ssim=.95,mse=.001,
                   passed=False) for split in ['train','val'] for i in CFG['splits']['TRAIN'] for bg in [0,1]]
        self.assertTrue(seed_eligibility(rows,CFG)['passed'])
        pairs=[dict(r,rmse_seed0=.03,rmse_seed1=.04,rmse_pair=.05) for r in rows]
        self.assertTrue(independent_eligibility([rows,copy.deepcopy(rows)],pairs,CFG)['passed'])
        self.assertFalse(seed_eligibility(rows[:-1],CFG)['passed'])
        bad=copy.deepcopy(rows);bad[0]['psnr_db']=19.99
        self.assertFalse(seed_eligibility(bad,CFG)['passed'])
        bad=copy.deepcopy(pairs);bad[0]['rmse_pair']=.061
        self.assertFalse(independent_eligibility([rows,rows],bad,CFG)['passed'])
        bad=copy.deepcopy(rows)
        for r in bad:r['psnr_db']=33.
        self.assertFalse(independent_eligibility([rows,bad],pairs,CFG)['passed'])

    def test_controlled_qualification_rejects_missing_views_and_trivial_children(self):
        from src.multiscene import controlled_eligibility
        rows=[dict(view=i,background=bg,valid=True,passed=True) for i in CFG['splits']['TRAIN'] for bg in [0,1]]
        cov=[dict(view=i,selected=.4,minor=.01) for i in CFG['splits']['TRAIN']]
        self.assertTrue(controlled_eligibility(rows,cov,CFG)['passed'])
        self.assertFalse(controlled_eligibility(rows[:-1],cov,CFG)['passed'])
        bad=copy.deepcopy(cov);bad[0]['minor']=.0049
        self.assertFalse(controlled_eligibility(rows,bad,CFG)['passed'])
        bad=copy.deepcopy(rows);bad[-1]['passed']=False
        self.assertFalse(controlled_eligibility(bad,cov,CFG)['passed'])

    def test_qualification_runner_keeps_all_doses_and_stock_calibration(self):
        from src.multiscene_qualification import qualify_parent
        cfg=copy.deepcopy(CFG); cfg['splits']['TRAIN']=[0]
        camera=dict(index=0,split='train',K=[[60,0,31.5],[0,60,31.5],[0,0,1]],w2c=np.eye(4).tolist())
        with tempfile.TemporaryDirectory() as tmp:
            report=qualify_parent(asset_fixture(),[camera],cfg,Path(tmp),size=64)
            self.assertTrue(report['calibration'][0]['passed'])
            self.assertEqual(len(report['variants']),9)
            self.assertEqual(sum(len(v['rows']) for v in report['variants']),18)
            self.assertTrue(all('coverage' in v and 'eligibility' in v for v in report['variants']))
            self.assertTrue((Path(tmp)/'parent_frozen.json').exists())
            self.assertTrue((Path(tmp)/'qualification.json').exists())
            self.assertEqual(len(list(Path(tmp).glob('*.png'))),9)
            with self.assertRaises(FileExistsError):qualify_parent(asset_fixture(),[camera],cfg,Path(tmp),size=64)

    def test_grid_png_decodes_and_is_deterministic(self):
        from src.multiscene_qualification import save_grid
        import cv2
        with tempfile.TemporaryDirectory() as tmp:
            a,b=Path(tmp)/'a.png',Path(tmp)/'b.png'
            panels=[(str(i),np.full((12,16,3),i/5)) for i in range(6)]
            save_grid(a,panels,3);save_grid(b,panels,3)
            self.assertEqual(a.read_bytes(),b.read_bytes())
            self.assertEqual(cv2.imread(str(a)).shape,(80,48,3))

    def test_quality_renders_compare_both_backgrounds_to_frozen_rgba(self):
        from src.multiscene_qualification import measure_quality
        from src.foundation import native_render
        import cv2,hashlib
        a=asset_fixture();K=np.array([[60,0,31.5],[0,60,31.5],[0,0,1]])
        state=native_render(a,K,np.eye(4),64,64,1)
        with tempfile.TemporaryDirectory() as tmp:
            tmp=Path(tmp);p=tmp/'photo.png'
            rgba=np.concatenate([np.full((64,64,3),.5),(1-state['final_T'])[:,:,None]],axis=2)
            cv2.imwrite(str(p),np.round(rgba*255).astype('u1'))
            cam=dict(index=0,K=K.tolist(),w2c=np.eye(4).tolist(),path=str(p),
                sha256=hashlib.sha256(p.read_bytes()).hexdigest())
            cfg=copy.deepcopy(CFG);cfg['splits']['TRAIN']=[0]
            report=measure_quality(a,[dict(cam,split='train'),dict(cam,split='val')],cfg,tmp/'quality',size=64)
            self.assertEqual(len(report['rows']),4)
            self.assertTrue(report['eligibility']['passed'])
            self.assertTrue(report['calibration'][0]['passed'])
            self.assertTrue((tmp/'quality/quality.json').exists())

    def test_resolution_diagnosis_has_no_eligibility_override(self):
        from src.multiscene_diagnostic import resolution_diagnostic
        from src.foundation import native_render
        import cv2,hashlib
        a=asset_fixture();K=np.array([[60.,0,32],[0,60.,32],[0,0,1]])
        high=K.copy();high[:2]*=2;high[:2,2]=63.5
        rendered=native_render(a,high,np.eye(4),128,128,1)
        with tempfile.TemporaryDirectory() as tmp:
            tmp=Path(tmp);p=tmp/'photo.png'
            rgba=np.concatenate([np.full((128,128,3),.5),(1-rendered['final_T'])[:,:,None]],axis=2)
            cv2.imwrite(str(p),np.round(rgba*255).astype('u1'))
            cam=dict(index=0,split='train',K=K.tolist(),w2c=np.eye(4).tolist(),path=str(p),sha256=hashlib.sha256(p.read_bytes()).hexdigest())
            result=resolution_diagnostic(a,[cam],tmp/'result',base_size=64,source_size=128)
            self.assertEqual(len(result['rows']),2)
            self.assertNotIn('eligibility',result)
            self.assertNotIn('passed',result['rows'][0]['native_metrics'])
            self.assertGreater(result['rows'][0]['native_metrics']['psnr_db'],45)


if __name__=='__main__':unittest.main()
