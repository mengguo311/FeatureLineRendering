import unittest
import numpy as np
from src.common import Camera
from src.stroke_graph import geometry_graph,measure_view,whole_path_witness

CFG=dict(neighbors=12,samples=9,min_col=.4,endpoint_gap=2.,tube_radius=1.25,gap_units=4.,dt_px=2.,min_visible_samples=4,layer_px=2.,layer_rel=.02)

class GraphTest(unittest.TestCase):
    def test_parallel_neighbors_not_linked(self):
        p=np.array([[0,0,2],[0,.1,2]],float);t=np.tile([1.,0,0],(2,1))
        r=geometry_graph(p,t,np.full(2,.1),CFG)
        self.assertFalse(r['allowed'][0]);self.assertEqual(r['reason'][0],'parallel_or_sideways')

    def test_cross_depth_layer_rejected(self):
        cam=Camera([[100,0,50],[0,100,50],[0,0,1]],np.eye(4),100,100)
        p=np.array([[0,0,2.],[0,0,2.2]])
        f=(np.zeros((100,100)),np.tile([1.,0.],(100,100,1)),np.ones((100,100),bool))
        ev,su,layer,lp=measure_view(p,np.array([[0,1]]),cam,np.full((100,100),2.),np.ones((100,100)),f,CFG)
        self.assertTrue(layer[0])

    def test_hidden_is_unevaluable_and_common_witness_matters(self):
        ev=np.array([[1,1,1],[1,1,1],[1,1,1],[0,0,0]],bool)
        su=ev.astype(float);length=np.ones_like(su)
        value,witness,q=whole_path_witness([0,1,2],ev,su,length)
        self.assertEqual(witness,[0,1,2]);self.assertEqual(value,1.)
        patchwork=np.eye(3,dtype=bool)
        value,witness,q=whole_path_witness([0,1,2],np.ones((3,3),bool),patchwork.astype(float),np.ones((3,3)))
        self.assertEqual(witness,[]);self.assertEqual(value,0.)

    def test_corner_and_determinism(self):
        p=np.array([[0,0,0],[.1,.1,0],[.2,.1,0]])
        t=np.array([[0,1.,0],[1.,0,0],[1.,0,0]])
        a=geometry_graph(p,t,np.ones(3)*.1,CFG);b=geometry_graph(p,t,np.ones(3)*.1,CFG)
        np.testing.assert_array_equal(a['pairs'],b['pairs']);np.testing.assert_array_equal(a['allowed'],b['allowed'])
        ix=np.flatnonzero(np.all(a['pairs']==[0,1],axis=1))[0]
        self.assertTrue(a['allowed'][ix]);self.assertTrue(a['corner'][ix])

if __name__=='__main__':unittest.main()
