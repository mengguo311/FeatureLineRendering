import runtime
from runtime import ACTIVE_UNIT
import json
from pathlib import Path
import unittest
import numpy as np
from saturation import saturate, decompose_residual
from hybrid import paper_copy
from appearance_completion import apply_fixed_ink
from link_renderer import Renderer
import base_model as base

OLD=Path('/mnt/hdd1/u00134/partwise_sketch_hatching_gaussian_link_v06/units/unit_008')

class SaturationTests(unittest.TestCase):
    def test_same_support_and_invalid_strength(self):
        s=np.array([0.,.7,1.,.93,0.]);before=s.copy()
        np.testing.assert_array_equal(saturate(s),[0,1,1,1,0])
        np.testing.assert_array_equal(s,before)
        for bad in ([np.nan],[1.01],[-.1],[[.8]]):
            with self.assertRaises(ValueError):saturate(bad)

    def test_signed_cancellation_and_background(self):
        colors=np.array([[0.,0.,0.],[1.5,1.5,1.5],[.2,.2,.2],[.5,.5,.5]])
        strength=np.array([.8,0.,0.,1.])
        tr=dict(sample_index=np.array([0,0,1]),source_index=np.array([0,1,3]),weight=np.array([.4,.4,.6]))
        d=decompose_residual(colors,strength,tr,3,[.95]*3)
        np.testing.assert_allclose(d['licensed_unreplaced'][0],[-.076]*3)
        np.testing.assert_allclose(d['unlicensed'][0],[.22]*3)
        np.testing.assert_allclose(d['background'][0],[.01]*3)
        np.testing.assert_allclose(d['old_residual'][0],[.154]*3)
        np.testing.assert_allclose(d['saturated_residual'][0],[.23]*3)
        np.testing.assert_allclose(d['saturated_residual'][2],[.05]*3)
        self.assertGreater(np.abs(d['licensed_unreplaced'][0]).sum()+np.abs(d['unlicensed'][0]).sum(),np.abs(d['old_residual'][0]).sum())

    def test_real_original_rows_saturation_and_zero_controls(self):
        p=json.loads((OLD/'PROTOCOL.json').read_text());s=p['scene']['source']
        a=base.load_source(s['original_ply'],s['sha256'])
        with np.load(OLD/'SELECTION.npz',allow_pickle=False) as z:strength=z['completed_strength'].copy()
        saturated=saturate(strength);self.assertEqual(int((saturated>0).sum()),41058)
        ids=np.flatnonzero(strength>0)[::300][::-1].copy()
        small={k:a[k][ids].copy() for k in ('means','covariance','precision','opacity','SH')};small['source_index']=ids
        before={k:v.copy() for k,v in small.items()}
        views=json.loads((OLD/'CAMERAS.json').read_text())['views']
        c=next(v['camera'] for v in views if v['kind']=='dev' and v['camera']['azimuth']==241 and v['camera']['elevation']==24)
        c=dict(c,width=64,height=64,fx=c['fx']/6,fy=c['fy']/6,cx=(c['cx']+.5)/6-.5,cy=(c['cy']+.5)/6-.5)
        yy,xx=np.mgrid[:64,:64];xy=np.column_stack([xx.ravel(),yy.ravel()]);r=Renderer(ACTIVE_UNIT/'fixture_build')
        source,tr=r.render(small,c,xy);old,_=r.render(paper_copy(small,c,strength[ids],[.95]*3),c)
        new,_=r.render(paper_copy(small,c,saturated[ids],[.95]*3),c)
        d=decompose_residual(base.source_colors(a,c),strength,tr,len(xy),[.95]*3)
        np.testing.assert_allclose(d['old_residual']+.95,old['rgb'].reshape(-1,3),rtol=0,atol=1e-6)
        np.testing.assert_allclose(d['saturated_residual']+.95,new['rgb'].reshape(-1,3),rtol=0,atol=1e-6)
        zero,_=r.render(paper_copy(small,c,np.zeros(len(ids)),[.95]*3),c)
        np.testing.assert_array_equal(zero['rgb'],source['rgb'])
        np.testing.assert_array_equal(apply_fixed_ink(new['rgb'],np.zeros((64,64))),new['rgb'])
        self.assertGreater(float(np.abs(new['rgb']-old['rgb']).sum()),0.)
        for k in before:np.testing.assert_array_equal(small[k],before[k])

if __name__=='__main__':unittest.main(verbosity=2)
