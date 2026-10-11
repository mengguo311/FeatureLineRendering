import unittest
import numpy as np
from line_core import focus_center,focus_weight,world_points,trace
from test_line_core import cam
class FocusTests(unittest.TestCase):
    def test_camera_axis_intersection(self):
        cams=[]
        for pos in [[0,0,-3],[3,0,0],[0,3,0]]:
            pos=np.array(pos,dtype=float);f=-pos/np.linalg.norm(pos);up=np.array([0,1,0]) if abs(f[1])<.9 else np.array([1,0,0])
            x=np.cross(up,f);x/=np.linalg.norm(x);y=np.cross(f,x);R=np.stack([x,y,f]);E=np.eye(4);E[:3,:3]=R;E[:3,3]=-R@pos;c=cam();c['extrinsic']=E.tolist();cams.append(c)
        np.testing.assert_allclose(focus_center(cams),0,atol=1e-12)
    def test_same_world_point_different_camera_depth(self):
        c1=cam(1,1);c2=cam(1,1);E=np.eye(4);E[2,3]=1;c2['extrinsic']=E.tolist()
        w1=focus_weight(np.array([[2.]]),c1,np.array([0,0,2]),1)
        w2=focus_weight(np.array([[3.]]),c2,np.array([0,0,2]),1)
        np.testing.assert_allclose(w1,w2,atol=1e-12)
        self.assertGreater(w1[0,0],.99)
    def test_whole_object_depth_extent_not_cut(self):
        c=cam(1,1);weights=[focus_weight(np.array([[z]]),c,np.array([0,0,2]),1)[0,0] for z in [1.3,2.,2.7]]
        self.assertTrue(min(weights)>.8)
    def test_soft_attention_has_no_edge(self):
        c=cam();z=np.full((96,128),2.);w=focus_weight(z,c,np.array([0,0,2]),.2)
        self.assertTrue((w>=.05).all());self.assertFalse(trace(np.zeros_like(z),np.zeros_like(z),np.ones_like(z,bool),w).any())
    def test_junction_does_not_lend_strength_to_bad_branch(self):
        r=np.zeros((61,81));r[30,10:71]=.08;r[10:31,40]=.08
        d=np.full_like(r,np.pi/2);d[:30,40]=0
        c=np.ones_like(r);c[:29,40]=.05
        lines=trace(r,d,np.ones_like(r,bool),c)
        self.assertFalse(lines[10:27,40].any())
        self.assertTrue(lines[30,10:71].all())
