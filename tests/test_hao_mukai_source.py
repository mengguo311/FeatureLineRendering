import unittest
import numpy as np
import torch
from src.raster_state import fragment_topk_attributes
from src.hao_mukai_source_2026 import compute_fields, smoothstep


class PosterSourceTests(unittest.TestCase):
    def test_topk_attributes_follow_weight_rank_not_depth_order(self):
        pix=torch.tensor([0,0,0]); ids=torch.tensor([7,2,9]); w=torch.tensor([.1,.5,.3],dtype=torch.float64)
        z=torch.tensor([1.,3.,2.]); n=torch.tensor([[1.,0.,0.],[0.,1.,0.],[0.,0.,1.]])
        topid,tw,mass,td,tn=fragment_topk_attributes(pix,w,ids,z,n,1,2)
        self.assertEqual(topid.tolist(),[[2,9]])
        self.assertTrue(torch.allclose(td,torch.tensor([[3.,2.]])))
        self.assertTrue(torch.allclose(tn[0],n[[1,2]]))
        self.assertAlmostEqual(mass.item(),.8)
        self.assertAlmostEqual(tw[0,0].item(),.625)

    def test_smoothstep_and_support_change_gate(self):
        self.assertEqual(float(smoothstep(np.array([-1.,0.,1.]),0.,1.)[0]),0.)
        self.assertEqual(float(smoothstep(np.array([-1.,0.,1.]),0.,1.)[-1]),1.)
        s=self._state()
        f=compute_fields(s)
        self.assertGreater(float(f['delta_G'][0,0]),0.)
        self.assertEqual(float(f['E_G'][0,0]),0.)  # without layer competition, support change is not a line

    def test_competing_layers_activate_visibility_term(self):
        s=self._state(); s['topk_w'][:]=[.6,.4,0,0]
        s['topk_depth'][:]=[1.,2.,0,0]
        f=compute_fields(s)
        self.assertGreater(float(f['E_V'][0,0]),0.)
        self.assertTrue(np.isfinite(f['S_L']).all())

    def _state(self):
        a=np.ones((2,2),np.float32)
        ids=np.array([[[1,2,-1,-1],[3,4,-1,-1]],[[1,2,-1,-1],[3,4,-1,-1]]])
        w=np.broadcast_to(np.array([1.,0,0,0],np.float32),(2,2,4)).copy()
        tn=np.zeros((2,2,4,3),np.float32);tn[:,:,:,2]=1
        return {'alpha':a,'depth':a.copy(),'normal':np.broadcast_to([0,0,1],(2,2,3)).copy().astype('float32'),
                'albedo':np.ones((2,2,3),np.float32)*.5,'topk_id':ids,'topk_w':w,
                'topk_depth':np.ones((2,2,4),np.float32),'topk_normal':tn,
                'depth_variance':np.zeros((2,2),np.float32),'normal_coherence':a.copy()}

if __name__=='__main__':unittest.main()
