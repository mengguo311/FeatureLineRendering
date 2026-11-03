import limits
import unittest, tempfile
import json
from unittest.mock import patch
from pathlib import Path
import numpy as np
from batching import transform, Journal
from core import collapse
from io_tools import load_asset, save_npz, same_bytes

def fixture():
    s=np.linspace(-2,2,15); a=np.column_stack([s,.2*s*s+.05*np.sin(9*s),3+.1*s])
    b=a+np.array([8.,4.,1.]); x=np.vstack([a, np.ones((3,3))*4, b, [[99.,99.,99.]]])
    n=len(x); asset=dict(means=x,covariance=np.tile(np.eye(3)*.3,(n,1,1)),opacity=np.full(n,.8),colors=np.zeros((n,3)),primitive_id=np.arange(n,dtype=np.int32),internal_piece_id=np.arange(n,dtype=np.int32),arc_t=np.linspace(0,1,n))
    edge=np.r_[np.full(15,10),np.full(3,20),np.full(15,30),-1].astype(np.int64)
    member=dict(line_kernel_id=np.arange(n,dtype=np.int64),edge_id=edge,primitive_id=asset['primitive_id'].copy())
    return asset,member

class Vertical(unittest.TestCase):
    def test_real_multigroup_transform(self):
        a,m=fixture(); before={k:v.copy() for k,v in a.items()}; phases=[]
        r=transform(a,m,1.,phases.append)
        self.assertGreater(np.max(np.abs(r['asset']['means'][:15]-a['means'][:15])),.001)
        self.assertGreater(np.max(np.abs(r['asset']['means'][18:33]-a['means'][18:33])),.001)
        self.assertEqual([x['status'] for x in r['ledger']],['SUCCESS','SKIPPED_NUMERICAL','SUCCESS'])
        self.assertTrue(r['complete'])
        for k in a: np.testing.assert_array_equal(a[k],before[k])
        for k in a:
            if k!='means':np.testing.assert_array_equal(a[k],r['asset'][k])
        np.testing.assert_array_equal(a['means'][15:18],r['asset']['means'][15:18])
        np.testing.assert_array_equal(a['means'][-1],r['asset']['means'][-1])
        self.assertTrue(phases)

class Regressions(unittest.TestCase):
    def test_v11_local_math_and_allocation(self):
        a,m=fixture();r=transform(a,m,1.,lambda phase:None)
        for gid in [10,30]:
            rows=np.flatnonzero(m['edge_id']==gid)
            ref=collapse(a,rows,1.)['position_only']['means'][rows]
            np.testing.assert_array_equal(ref,r['asset']['means'][rows])
        self.assertEqual(r['allocation']['max_local_input_rows'],15)
        self.assertEqual(r['allocation']['local_input_rows'],33)
        self.assertEqual(r['allocation']['global_means_copies'],1)
        for k in a:
            if k!='means':self.assertIs(a[k],r['asset'][k])

    def test_real_loader_cold_and_json(self):
        a,m=fixture();phases=[]
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'asset.npz';save_npz(p,a)
            loaded=load_asset(p,phases.append,len(a['means']))
            r=transform(loaded,m,1.,phases.append);save_npz(p,r['asset'])
            cold=load_asset(p,phases.append,len(a['means']))
            for k in a:self.assertTrue(same_bytes(cold[k],r['asset'][k]))
        self.assertIn('load_asset_begin',phases);self.assertIn('load_asset_covariance',phases)

    def test_checkpoint_restore_after_interruption(self):
        a,m=fixture()
        def guard(phase):
            if phase=='group_30':raise TimeoutError('fixture interruption')
        with tempfile.TemporaryDirectory() as td:
            interrupted=transform(a,m,1.,guard,Journal(td,'fixture',interval=1))
            self.assertFalse(interrupted['complete']);self.assertEqual(interrupted['ledger'][-1]['status'],'NOT_RUN')
            np.testing.assert_array_equal(interrupted['asset']['means'][18:],a['means'][18:])
            restored=transform(a,m,1.,lambda phase:None,Journal(td,'fixture',interval=1))
            direct=transform(a,m,1.,lambda phase:None)
            self.assertTrue(restored['complete']);self.assertEqual(restored['allocation']['local_call_count'],1)
            np.testing.assert_array_equal(restored['asset']['means'],direct['asset']['means'])
            self.assertEqual(len(json.loads((Path(td)/'MANIFEST.json').read_text())['chunks']),3)

    def test_unexpected_failure_is_not_numerical_skip(self):
        a,m=fixture()
        with patch('batching.collapse',side_effect=RuntimeError('injected engineering failure')):
            r=transform(a,m,1.,lambda phase:None)
        self.assertFalse(r['complete']);self.assertEqual([x['status'] for x in r['ledger']],['FAILED','NOT_RUN','NOT_RUN'])
        np.testing.assert_array_equal(a['means'],r['asset']['means'])

    def test_nonfinite_group_preserved_next_group_runs(self):
        a,m=fixture();a['means'][0,0]=np.nan
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/'x.npz';save_npz(path,a)
            loaded=load_asset(path,lambda phase:None,len(a['means']),allow_nonfinite_geometry=True)
            r=transform(loaded,m,1.,lambda phase:None)
        self.assertTrue(r['complete']);self.assertEqual(r['ledger'][0]['status'],'SKIPPED_NUMERICAL')
        self.assertEqual(r['ledger'][2]['status'],'SUCCESS')
        self.assertTrue(same_bytes(a['means'][:15],r['asset']['means'][:15]))

    def test_failed_checkpoint_does_not_promote_orphan_chunk(self):
        from io_tools import write_json
        a,m=fixture()
        def injected(path,value):
            if Path(path).name=='MANIFEST.json':raise OSError('fixture manifest failure')
            return write_json(path,value)
        with tempfile.TemporaryDirectory() as td:
            with patch('batching.write_json',side_effect=injected):
                r=transform(a,m,1.,lambda phase:None,Journal(td,'fixture',interval=1))
            self.assertFalse(r['complete']);self.assertEqual(r['ledger'][0]['status'],'FAILED')
            np.testing.assert_array_equal(r['asset']['means'],a['means'])
            recovered=transform(a,m,1.,lambda phase:None,Journal(td,'fixture',interval=1))
            self.assertTrue(recovered['complete'])

    def test_fixed_quadrants_cover_every_pixel(self):
        from delivery import quadrants
        masks=np.zeros((581,777),dtype=np.uint8)
        for x0,y0,x1,y1 in quadrants(777,581):masks[y0:y1,x0:x1]+=1
        self.assertTrue(np.all(masks==1))
        self.assertEqual(quadrants(777,581),[(0,0,388,290),(388,0,777,290),(0,290,388,581),(388,290,777,581)])

    def test_real_renderer_two_views_and_complete_context(self):
        from rendering import load_renderer
        from delivery import deliver
        from io_tools import sha
        from runner import load_membership
        renderer_path=Path('/home/u00134/3dgs_line/gaer_c2l50_8build_joint_gs_v01/reproduction/radegs_c2l50_8build_joint_gs_v01/renderer.py')
        helpers=[renderer_path,renderer_path.with_name('common.py'),Path('/mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_8build_joint_gs_v01/build/libjoint.so')]
        renderer=load_renderer(renderer_path,{str(p):sha(p) for p in helpers})
        a,m=fixture();a['means']=a['means']*.04+np.array([0,0,2.]);a['covariance']*=.001
        r=transform(a,m,.04,lambda phase:None);memory={'ORIGINAL':a,'FULL_POSITION_ONLY':r['asset']}
        cams=[]
        for view,tx in [('0012',0.),('0036',.03)]:
            E=np.eye(4);E[0,3]=tx
            cams.append(dict(view=view,width=32,height=24,fx=30.,fy=30.,cx=16.,cy=12.,extrinsic=E.tolist()))
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);save_npz(root/'MEMBERSHIP.npz',m)
            phases=[];loaded_m=load_membership(root/'MEMBERSHIP.npz',phases.append)
            for k in m:self.assertTrue(same_bytes(m[k],loaded_m[k]))
            paths={s:root/(s+'.npz') for s in memory}
            for s in memory:save_npz(paths[s],memory[s])
            cold={s:load_asset(paths[s],phases.append,len(a['means'])) for s in memory}
            rec=deliver(root,renderer,cold,memory,cams,paths,r['ledger'],phases.append)
            self.assertEqual(len(rec['images']),4);self.assertEqual(len(rec['quadrants']),16)
            self.assertTrue(all(x['rows']==34 for x in rec['images']))
            self.assertTrue(all(x['alpha_sum']>0 for x in rec['images']))
            self.assertTrue((root/'FULL_MODEL_BEFORE_AFTER_TWO_VIEWS.png').exists())
            self.assertTrue(all(all(x['fields_bitwise'].values()) for x in rec['cold_checks']))

if __name__=='__main__':unittest.main(verbosity=2)
