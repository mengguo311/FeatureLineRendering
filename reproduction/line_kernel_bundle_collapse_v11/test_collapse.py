"""Small synthetic Gaussian fixtures only; no real-asset science in BUILD."""
import limits
import unittest
import json
import tempfile
import hashlib
from pathlib import Path
import numpy as np
from core import collapse, evaluate_model
from io_tools import load_asset, save_npz, write_json, same_bytes, preservation_audit
from rendering import load_renderer, crop_box, deliver_images

UNIT = Path('/mnt/hdd1/u00134/radegs_paper_reproduction_v01/line_kernel_bundle_collapse_v11_20261103/units/unit_001')

def fixture():
    s = np.repeat(np.linspace(-5., 5., 25), 3)
    offsets = np.tile(np.array([-.3, 0., .3]), 25)
    means = np.column_stack([s, .09*s*s + offsets, .02*s*s*s + offsets*.3])
    means = np.vstack([means, [30., 30., 30.], [-30., 30., 30.]])
    n = len(means)
    asset = dict(means=means.astype(np.float64), covariance=np.tile(np.diag([.64, .16, .09]), (n, 1, 1)),
                 opacity=np.linspace(.1, .2, n), colors=np.zeros((n, 3)),
                 primitive_id=np.arange(n, dtype=np.int32), internal_piece_id=np.zeros(n, dtype=np.int32),
                 arc_t=np.linspace(0., 1., n))
    return asset, np.arange(n-2, dtype=np.int64)

class CollapseTests(unittest.TestCase):
    def test_01_curved_bundle_changes_real_gaussians(self):
        asset, rows = fixture()
        before = {k: v.copy() for k, v in asset.items()}
        result = collapse(asset, rows, 1.)
        derived = result['derived']
        self.assertGreater(np.linalg.norm(derived['means'][rows]-asset['means'][rows]), .1)
        self.assertGreater(np.linalg.norm(derived['covariance'][rows]-asset['covariance'][rows]), .1)
        for k in asset:
            self.assertEqual(asset[k].tobytes(), before[k].tobytes())
            self.assertEqual(derived[k][-2:].tobytes(), asset[k][-2:].tobytes())
        self.assertEqual(result['position_only']['covariance'].tobytes(), asset['covariance'].tobytes())

    def test_02_curve_is_monotone_curved_and_covariance_aligned(self):
        asset,rows=fixture();r=collapse(asset,rows,1.);m=r['model']
        s=np.linspace(m['s_min'],m['s_max'],101);q,t=evaluate_model(m,s)
        np.testing.assert_allclose((q-m['center'])@m['axis'],s,atol=1e-12)
        self.assertTrue(np.all(np.diff(q@m['axis'])>0))
        self.assertGreater(np.linalg.norm(q[50]-(q[0]+q[-1])/2),.2)
        self.assertGreater(np.ptp(t[:,1]),.1)
        eig,axes=np.linalg.eigh(r['derived']['covariance'][rows])
        np.testing.assert_allclose(eig[:,:2],.15**2,atol=1e-14)
        np.testing.assert_allclose(np.sqrt(eig[:,-1]),.8,atol=1e-14)
        np.testing.assert_allclose(np.abs(np.sum(axes[:,:,-1]*r['delta']['tangent'],axis=1)),1.,atol=1e-13)
        np.testing.assert_allclose((r['derived']['means'][rows]-m['center'])@m['axis'],r['delta']['s'],atol=1e-12)
        with self.assertRaises(ValueError):evaluate_model(m,np.array([m['s_max']+1]))

    def test_03_empty_degenerate_invalid_and_no_source_mutation(self):
        asset,rows=fixture()
        with self.assertRaises(ValueError):collapse(asset,np.array([],dtype=np.int64),1.)
        with self.assertRaises(ValueError):collapse(asset,np.array([0,0]),1.)
        with self.assertRaises(ValueError):collapse(asset,np.array([len(asset['means'])]),1.)
        for change in ('constant','nan','not_spd'):
            a={k:v.copy() for k,v in asset.items()}
            if change=='constant':a['means'][rows]=0
            elif change=='nan':a['means'][0,0]=np.nan
            else:a['covariance'][0,0,0]=-1
            with self.assertRaises(ValueError):collapse(a,rows,1.)

    def test_04_real_loader_callback_cold_fields_identity_safe_json(self):
        asset,rows=fixture();r=collapse(asset,rows,1.)
        with tempfile.TemporaryDirectory(dir=UNIT,prefix='fixture_') as td:
            path=Path(td)/'asset.npz';save_npz(path,r['derived']);phases=[]
            cold=load_asset(path,lambda phase:phases.append(phase),len(asset['means']))
            self.assertIn('load_asset_covariance',phases)
            self.assertEqual(phases[-1],'load_asset_end')
            for key in cold:self.assertTrue(same_bytes(cold[key],r['derived'][key]))
            audit=preservation_audit(asset,cold,rows)
            self.assertTrue(audit['non_target_all_fields_bitwise'])
            write_json(Path(td)/'test.json',{'integer':np.int64(3),'bool':np.bool_(True),'model':r['model']})
            self.assertIs(json.loads((Path(td)/'test.json').read_text())['bool'],True)
            corrupted={k:v.copy() for k,v in cold.items()};corrupted['opacity'][-1]=.9
            with self.assertRaises(ValueError):preservation_audit(asset,corrupted,rows)

    def test_05_native_gaussian_renderer_two_cameras_and_cold_replay(self):
        renderer_path=Path('/home/u00134/3dgs_line/gaer_c2l50_8build_joint_gs_v01/reproduction/radegs_c2l50_8build_joint_gs_v01/renderer.py')
        helpers=[renderer_path,renderer_path.with_name('common.py'),
                 Path('/mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_8build_joint_gs_v01/build/libjoint.so'),
                 Path('/mnt/hdd1/u00134/radegs_paper_reproduction_v01/official_code_fix_v01/source/utils/sh_utils.py')]
        renderer=load_renderer(renderer_path,{str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in helpers})
        asset,rows=fixture();r=collapse(asset,rows,1.);derived={k:v[rows] for k,v in r['derived'].items()}
        before={k:v.copy() for k,v in derived.items()}
        with tempfile.TemporaryDirectory(dir=UNIT,prefix='render_fixture_') as td:
            path=Path(td)/'derived.npz';save_npz(path,derived);cold=load_asset(path,lambda phase:None,len(rows))
            images=[]
            for angle in (0.,.6):
                E=np.eye(4);E[:3,:3]=[[np.cos(angle),-np.sin(angle),0],[np.sin(angle),np.cos(angle),0],[0,0,1]];E[2,3]=20
                camera=dict(extrinsic=E.tolist(),width=32,height=24,fx=30.,fy=30.,cx=15.5,cy=11.5,view=str(angle))
                native=renderer.render(derived,camera);reloaded=renderer.render(cold,camera)
                for key in native:self.assertTrue(same_bytes(native[key],reloaded[key]))
                self.assertEqual(native['rgb'].shape,(24,32,3));self.assertGreater(native['alpha'].max(),0)
                images.append(native['rgb'])
                box,receipt=crop_box(renderer,{'DERIVED':cold},np.arange(len(rows)),camera)
                self.assertIsNotNone(box)
            self.assertFalse(same_bytes(images[0],images[1]))
            for key in derived:self.assertTrue(same_bytes(before[key],derived[key]))

    def test_06_small_complete_delivery_uses_saved_gaussian_assets(self):
        renderer_path=Path('/home/u00134/3dgs_line/gaer_c2l50_8build_joint_gs_v01/reproduction/radegs_c2l50_8build_joint_gs_v01/renderer.py')
        renderer=load_renderer(renderer_path,{str(renderer_path):hashlib.sha256(renderer_path.read_bytes()).hexdigest()})
        a,rows=fixture();r=collapse(a,rows,1.)
        assets={'ORIGINAL':a,'POSITION_ONLY':r['position_only'],'DERIVED':r['derived']}
        with tempfile.TemporaryDirectory(dir=UNIT,prefix='delivery_fixture_') as td:
            directory=Path(td);paths={k:directory/(k+'.npz') for k in assets}
            for k,v in assets.items():save_npz(paths[k],v)
            cold={k:load_asset(paths[k],lambda phase:None,len(a['means'])) for k in assets}
            cameras=[]
            for view,shift in [('fixtureA',0.),('fixtureB',1.)]:
                E=np.eye(4);E[0,3]=shift;E[2,3]=20
                cameras.append(dict(view=view,extrinsic=E.tolist(),width=32,height=24,fx=30.,fy=30.,cx=15.5,cy=11.5))
            receipt=deliver_images(directory,renderer,cold,assets,rows,cameras,paths,lambda phase:None)
            self.assertEqual(receipt['saved_native_count'],12)
            self.assertFalse(receipt['partial'])
            self.assertTrue((directory/'BEFORE_AFTER_TWO_VIEWS.png').is_file())
            for item in receipt['images']:
                self.assertTrue((directory/item['path']).is_file())
                self.assertEqual(item['asset_sha256'],hashlib.sha256(paths[item['stage']].read_bytes()).hexdigest())
            for item in receipt['cold_render_checks']:self.assertTrue(all(item['fields_bitwise'].values()))

    def test_07_relocated_sh_matches_unmodified_renderer(self):
        import importlib.util
        path=Path('/home/u00134/3dgs_line/gaer_c2l50_8build_joint_gs_v01/reproduction/radegs_c2l50_8build_joint_gs_v01/renderer.py')
        relocated=load_renderer(path,{str(path):hashlib.sha256(path.read_bytes()).hexdigest()})
        spec=importlib.util.spec_from_file_location('unchanged_renderer_reference',path)
        reference=importlib.util.module_from_spec(spec);spec.loader.exec_module(reference)
        a,rows=fixture();a={k:v[rows] for k,v in a.items()}
        E=np.eye(4);E[2,3]=20
        camera=dict(extrinsic=E.tolist(),width=32,height=24,fx=30.,fy=30.,cx=15.5,cy=11.5)
        for asset in [a,{**a,'SH':np.full((len(rows),3,1),.1)}]:
            before=reference.render(asset,camera);after=relocated.render(asset,camera)
            for field in before:self.assertTrue(same_bytes(before[field],after[field]))

if __name__ == '__main__':
    unittest.main(verbosity=2)
