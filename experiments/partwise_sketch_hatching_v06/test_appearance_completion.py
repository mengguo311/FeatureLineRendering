import runtime
from runtime import ACTIVE_UNIT
import json
import unittest
from pathlib import Path
import numpy as np
from appearance_completion import RegionFootprintRenderer, completion_selection, categories, apply_fixed_ink
from hybrid import region_strength, paper_copy
from membership import load_binding
from link_renderer import Renderer, validate_trace
import base_model as base


class CompletionTests(unittest.TestCase):
    def test_completion_keeps_unknown_and_existing_strength(self):
        n=7
        b=dict(source_index=np.arange(n),membership=np.zeros((n,6)),
               unknown=np.array([False,True,True,True,True,True,False]),
               conflict=np.array([False,False,True,False,False,False,False]),
               region_id=np.array([4,0,0,0,0,0,2]))
        b['membership'][:,0]=1.;b['membership'][0]=[.2,0,0,0,.8,0]
        before={k:v.copy() for k,v in b.items()}
        pv=np.zeros((2,n,5));pv[:,:,0]=1.;pv[:,:,1]=1.
        pv[:,3,1]=.94;pv[:,3,3]=.06
        pv[:,4,1]=.6;pv[:,4,2]=.4
        pv[1,5]=0.
        s=completion_selection(pv,b)
        np.testing.assert_array_equal(s['appearance_completion_strength'],[0,1,0,0,0,0,0])
        np.testing.assert_array_equal(s['completed_strength'],[.8,1,0,0,0,0,0])
        for k,v in before.items():np.testing.assert_array_equal(b[k],v)
        self.assertTrue(b['unknown'][1])
        bad=pv.copy();bad[0,0,0]=2
        with self.assertRaises(ValueError):completion_selection(bad,b)

    def test_fixed_ink_and_empty_completion(self):
        paper=np.full((3,4,3),.7,np.float32);alpha=np.full((3,4),.25,np.float32)
        expected=paper*(1-alpha[:,:,None])+.03*alpha[:,:,None]
        np.testing.assert_array_equal(apply_fixed_ink(paper,alpha),expected)
        np.testing.assert_array_equal(apply_fixed_ink(paper,np.zeros_like(alpha)),paper)
        reg=np.zeros((9,9),int);reg[4,4]=4
        cat=categories(reg)
        self.assertEqual(cat[4,4],0);self.assertEqual(cat[4,6],1);self.assertEqual(cat[4,7],2)

    def test_real_original_rows_full_footprint_and_no_op(self):
        old=Path('/mnt/hdd1/u00134/partwise_sketch_hatching_gaussian_link_v05/units/unit_005')
        s=json.loads((old/'PROTOCOL.json').read_text())['scenes']['lego']
        original=base.load_source(s['source']['original_ply'],s['source']['sha256'])
        b,_=load_binding(old/'results/lego/SOURCE_BINDING.npz',s['source']['sha256'],len(original['means']))
        selected=np.flatnonzero((b['region_id']==4)&~b['unknown'])
        ids=selected[np.linspace(0,len(selected)-1,96,dtype=int)][::-1].copy()
        a={k:original[k][ids].copy() for k in ('means','covariance','precision','opacity','SH')};a['source_index']=ids
        before={k:v.copy() for k,v in a.items()}
        c=dict(s['cameras'][1],width=64,height=64,fx=s['cameras'][1]['fx']/6,fy=s['cameras'][1]['fy']/6,
               cx=(s['cameras'][1]['cx']+.5)/6-.5,cy=(s['cameras'][1]['cy']+.5)/6-.5)
        yy,xx=np.mgrid[:64,:64];xy=np.column_stack([xx.ravel(),yy.ravel()])
        reg=np.where(xx<32,4,0);cat=categories(reg);depth=np.full((64,64),5.)
        plain=Renderer(ACTIVE_UNIT/'fixture_build');f,tr=plain.render(a,c,xy)
        r=RegionFootprintRenderer(ACTIVE_UNIT/'fixture_build')
        g,t,m=r.footprint(a,c,cat,depth,np.ones((64,64),bool),xy)
        for k in ('rgb','alpha'):np.testing.assert_array_equal(f[k],g[k])
        np.testing.assert_allclose(m[:,1:4].sum(1),m[:,0],rtol=1e-13,atol=1e-13)
        id_to_row={int(i):j for j,i in enumerate(ids)}
        rows=np.array([id_to_row[int(i)] for i in t['source_index']]);cc=cat.ravel()[t['sample_index']]
        for channel in range(3):
            mass=np.bincount(rows[cc==channel],t['weight'][cc==channel],minlength=len(ids))
            np.testing.assert_allclose(m[:,1+channel],mass,rtol=1e-13,atol=1e-13)
        self.assertGreater(m.sum(),0.)
        zero=np.zeros(len(ids));same,_=r.render(paper_copy(a,c,zero,[.95]*3),c)
        np.testing.assert_array_equal(f['rgb'],same['rgb'])
        strength=(np.arange(len(ids))%2==0).astype(float)
        edited,_=r.render(paper_copy(a,c,strength,[.95]*3),c)
        swapped,_=r.render(paper_copy(a,c,1-strength,[.95]*3),c)
        self.assertGreater(float(np.abs(edited['rgb']-swapped['rgb']).sum()),.01)
        for k,v in before.items():np.testing.assert_array_equal(a[k],v)


if __name__=='__main__':unittest.main(verbosity=2)
