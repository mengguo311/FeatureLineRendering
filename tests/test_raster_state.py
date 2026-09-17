import unittest
import numpy as np
import torch
from src.common import Camera
from src.raster_state import remap_ids,fragment_topk,render_state,exact_n,overlap_field,channel_fields,numpy_state

class RasterTest(unittest.TestCase):
    def test_three_level_original_id_remap(self):
        keep=np.array([0,1,0,1,1,1,0,1],bool);frustum=np.array([1,0,1,1,1],bool);bucket=np.array([0,1,0,1],bool)
        np.testing.assert_array_equal(remap_ids(keep,frustum,bucket,[1,0]),[7,4])

    def test_topk_weight_not_front_and_tie(self):
        ids,w,m=fragment_topk(torch.tensor([0,0,0,0]),torch.tensor([.01,.2,.7,.2]),torch.tensor([9,8,7,6]),2,3)
        self.assertEqual(ids[0].tolist(),[7,6,8]);self.assertTrue((ids[1]==-1).all())
        self.assertAlmostEqual(float(w[0].sum()),1.,places=6)

    def test_exact_n_ties_and_empty(self):
        x=np.ones((3,4));m=exact_n(x,np.ones_like(x,bool),5)
        self.assertEqual(m.sum(),5);self.assertEqual(np.flatnonzero(m).tolist(),list(range(5)))
        self.assertFalse(exact_n(x,np.zeros_like(x,bool),5).any())

    def test_empty_empty_and_k_sensitivity(self):
        ids=np.full((3,3,8),-1);weights=np.zeros((3,3,8));cov=np.zeros((3,3),bool)
        self.assertEqual(overlap_field(ids,weights,cov,8)[0].max(),0)
        ids[:]=np.arange(8);weights[:]=.125;cov[:]=True
        ids[:,1:,:4]=np.arange(10,14)
        f4=overlap_field(ids,weights,cov,4)[0];f8=overlap_field(ids,weights,cov,8)[0]
        self.assertGreater(f4.max(),f8.max())

    def test_cpu_render_full_K_original_ids_and_determinism(self):
        g=dict(mu=np.array([[9,9,-1],[0,.2,2],[0,.2,2.2]]),opacity=np.array([.9,.1,.9]),
               normal=np.tile([0.,0.,1.],(3,1)),scale_max=np.full(3,.03),albedo=np.ones((3,3))*.4)
        cam=Camera([[20,0,10],[0,40,8],[0,0,1]],np.eye(4),24,24)
        a=numpy_state(render_state(g,np.array([0,1,1],bool),cam,device='cpu'))
        b=numpy_state(render_state(g,np.array([0,1,1],bool),cam,device='cpu'))
        np.testing.assert_array_equal(a['topk_id'],b['topk_id'])
        self.assertEqual(a['topk_id'][12,10,0],2)
        self.assertFalse(a['coverage'][10,10])
        self.assertGreater(a['depth_median'][12,10],2.)

if __name__=='__main__':unittest.main()
