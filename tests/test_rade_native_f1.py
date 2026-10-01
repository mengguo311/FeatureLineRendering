import unittest
import numpy as np
from types import SimpleNamespace
from src.rade_native_f1 import render_native_f1, build_source_state

class NativeF1Test(unittest.TestCase):
    def test_single_splat_preserves_original_id_and_blend(self):
        cam=SimpleNamespace(H=32,W=32,w2c=np.eye(4),K=np.array([[32.,0,16.],[0,32.,16.],[0,0,1.]]),center=np.zeros(3))
        g={'mu':np.array([[100.,0.,3.],[0.,0.,3.]]), 'quat':np.tile([1.,0.,0.,0.],(2,1)),
           'scale':np.full((2,3),.3), 'opacity':np.array([.9,.8]), 'albedo':np.array([[0.,1.,0.],[1.,0.,0.]])}
        raw=render_native_f1(g,cam)
        y=x=16
        self.assertEqual(raw['topk_id'][y,x,0],1)
        self.assertTrue(np.all(raw['topk_id'][y,x,1:]==-1))
        self.assertAlmostEqual(float(raw['topk_w'][y,x,0]),float(raw['alpha'][y,x]),places=5)
        self.assertGreater(raw['topk_depth'][y,x,0],2.)
        self.assertAlmostEqual(np.linalg.norm(raw['topk_normal'][y,x,0]),1.,places=4)
        self.assertEqual(raw['topk_id'][0,0,0],-1)
        state=build_source_state(raw)
        self.assertAlmostEqual(float(state['topk_w'][y,x,0]),1.,places=5)
        self.assertAlmostEqual(float(state['topk_mass'][y,x]),1.,places=5)
        self.assertTrue(np.isfinite(state['depth_variance']).all())

    def test_two_splats_rank_by_actual_weight_not_original_id(self):
        cam=SimpleNamespace(H=32,W=32,w2c=np.eye(4),K=np.array([[32.,0,16.],[0,32.,16.],[0,0,1.]]),center=np.zeros(3))
        g={'mu':np.array([[0.,0.,3.5],[0.,0.,3.]]), 'quat':np.tile([1.,0.,0.,0.],(2,1)),
           'scale':np.full((2,3),.3), 'opacity':np.array([.8,.12]), 'albedo':np.array([[0.,1.,0.],[1.,0.,0.]])}
        r=render_native_f1(g,cam)
        y=x=16
        self.assertEqual(r['topk_id'][y,x,0],0)
        self.assertEqual(r['topk_id'][y,x,1],1)
        self.assertGreater(r['topk_w'][y,x,0],r['topk_w'][y,x,1])
        self.assertAlmostEqual(float(r['topk_w'][y,x].sum()),float(r['alpha'][y,x]),places=5)
        self.assertGreaterEqual(build_source_state(r)['depth_variance'][y,x],0.)

if __name__=='__main__': unittest.main()
