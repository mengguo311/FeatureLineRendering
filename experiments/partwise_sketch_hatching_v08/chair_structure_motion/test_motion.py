import runtime
import unittest
import numpy as np
from structure_motion import trajectory,select_curve_samples,compose_pair,observe_curve
from geometry import mesh_data

class MotionTests(unittest.TestCase):
    def test_fixed_trajectory(self):
        p=trajectory();self.assertEqual(len(p['frames']),61);self.assertEqual(p['fps'],12)
        for i,a,e in [(0,241,24),(15,196,36),(30,151,36),(60,61,24)]:
            row=p['frames'][i];self.assertEqual((row['azimuth'],row['elevation'],row['distance']),(a,e,5.1))
        self.assertEqual(len({r['camera']['view'] for r in p['frames']}),61)

    def test_pair_hides_old_regions_and_preserves_aa_union(self):
        paper=np.full((2,2,3),.95);s=np.ones((2,2));contour=np.zeros((4,4),np.float32)
        layers={r:np.zeros((4,4),np.float32) for r in range(1,6)}
        layers[1][:]=1;layers[4][0:2,0:2]=.5;layers[5][0:2,2:4]=.4
        structure=np.zeros((4,4),np.float32);structure[2:4,2:4]=.85
        off,on=compose_pair(paper,layers,contour,s,structure)
        np.testing.assert_array_equal(off['layer_1'],0)
        self.assertEqual(float(off['combined_ink'][1,0]),0.)
        self.assertEqual(float(off['structure'][1,1]),0.)
        self.assertAlmostEqual(float(on['combined_ink'][1,1]),.85,places=6)
        np.testing.assert_array_equal(off['hybrid'][0],on['hybrid'][0])
        np.testing.assert_allclose(on['hybrid'][1,1],.95*(1-.85)+.03*.85,atol=1e-7)

    def test_samples_never_bridge_gaps_and_visibility_ignores_regions(self):
        curve=dict(points=np.array([[[0,0,0],[1,0,0]],[[10,0,0],[11,0,0]]],float),face=np.array([0,0]),
            bary=np.array([[[1,0,0],[0,1,0]],[[1,0,0],[0,1,0]]],float),curve_id=np.array([42,42]))
        samples=select_curve_samples(curve)
        self.assertEqual(len(samples['anchors']),64)
        self.assertTrue(all(a['point'][0]<1 or a['point'][0]>10 for a in samples['anchors']))
        mesh=mesh_data(np.array([[-5,-5,2],[5,-5,2],[0,5,2]],float),np.array([[0,1,2]]),np.array([7]))
        c=dict(width=4,height=4,fx=1.,fy=1.,cx=1.5,cy=1.5,extrinsic=np.eye(4).tolist())
        sam=dict(anchors=[dict(point=[0,0,2]),dict(point=[0,0,3])])
        obs=observe_curve(mesh,sam,c,np.zeros((4,4)),np.zeros((4,4,3)))
        self.assertEqual(obs['status'].tolist(),['visible','depth_rejected'])
        np.testing.assert_array_equal(obs['own_ink'],[0,0])
        np.testing.assert_array_equal(obs['increment'],[0,0])

if __name__=='__main__':unittest.main()
