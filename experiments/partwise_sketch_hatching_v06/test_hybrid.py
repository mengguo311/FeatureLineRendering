import runtime
from runtime import ACTIVE_UNIT
import unittest
import numpy as np
from hybrid import region_strength, compose, paper_copy
from link_renderer import Renderer
import base_model as base

class HybridTests(unittest.TestCase):
    def test_unknown_and_row_order(self):
        b = dict(source_index=np.arange(4), membership=np.eye(6)[[4,4,2,0]], region_id=np.array([4,4,2,0]), unknown=np.array([False,True,False,True]))
        np.testing.assert_array_equal(region_strength(b), [1,0,0,0])
        b['source_index'] = np.array([1,0,2,3])
        with self.assertRaises(ValueError): region_strength(b)

    def test_zero_support_cannot_leave_proxy_ink(self):
        paper=np.full((4,5,3), .7); ink=np.ones((4,5))*.8
        out, alpha=compose(paper,ink,np.zeros((4,5)),True)
        np.testing.assert_array_equal(out,paper)
        self.assertEqual(float(alpha.sum()),0.)

    def test_actual_original_kernel_fixture(self):
        import json
        from pathlib import Path
        old=Path('/mnt/hdd1/u00134/partwise_sketch_hatching_gaussian_link_v05/units/unit_005')
        p=json.loads((old/'PROTOCOL.json').read_text())['scenes']['chair']
        original=base.load_source(p['source']['original_ply'],p['source']['sha256'])
        with np.load(old/'results/chair/SOURCE_BINDING.npz') as z:
            good=np.flatnonzero((z['region_id']==4)&~z['unknown'])
        ids=good[np.linspace(0,len(good)-1,24,dtype=int)]
        a={k:original[k][ids].copy() for k in ('means','covariance','precision','opacity','SH')}
        a['source_index']=ids.copy()
        before={k:v.copy() for k,v in a.items()}
        c=p['cameras'][2]; r=Renderer(ACTIVE_UNIT/'fixture_build')
        zeros=np.zeros(len(ids)); ones=np.ones(len(ids))
        f,_=r.render(a,c,strength=zeros)
        no_op,_=r.render(paper_copy(a,c,zeros,[.95]*3),c,strength=zeros)
        np.testing.assert_array_equal(f['rgb'],no_op['rgb'])
        selected=np.arange(len(ids))%2==0
        x,_=r.render(paper_copy(a,c,selected.astype(float),[.95]*3),c,strength=selected)
        y,_=r.render(paper_copy(a,c,(~selected).astype(float),[.95]*3),c,strength=~selected)
        self.assertGreater(float(np.abs(x['rgb']-y['rgb']).sum()),.01)
        self.assertGreater(float(np.abs(x['contribution']-y['contribution']).sum()),.01)
        _,ix=compose(x['rgb'],np.ones_like(x['alpha']),x['contribution'],True)
        _,iy=compose(y['rgb'],np.ones_like(y['alpha']),y['contribution'],True)
        self.assertGreater(float(np.abs(ix-iy).sum()),.01)
        for k in before: np.testing.assert_array_equal(a[k],before[k])
        np.testing.assert_array_equal(x['alpha'],f['alpha'])

if __name__=='__main__': unittest.main(verbosity=2)
