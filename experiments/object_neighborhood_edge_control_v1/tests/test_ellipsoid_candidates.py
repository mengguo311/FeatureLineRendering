import unittest
import numpy as np
from adjacency import center_pairs, ellipsoid_distance, ellipsoid_pairs, surface_relation

class SpatialTests(unittest.TestCase):
    def test_spheres_tangent_separated(self):
        I=np.eye(3)
        self.assertLess(ellipsoid_distance([0,0,0],I,[2,0,0],I,1),1e-5)
        self.assertAlmostEqual(ellipsoid_distance([0,0,0],I,[3,0,0],I,1),1,delta=1e-5)
    def test_large_rotated_not_center_prefiltered(self):
        a=np.pi/4; R=np.array([[np.cos(a),-np.sin(a),0],[np.sin(a),np.cos(a),0],[0,0,1]])
        L=R@np.diag([2,.1,.1]);mu=np.array([[0,0,0],[2,2,0]])
        self.assertEqual(len(center_pairs(mu,[1,2],.2)),0)
        self.assertEqual(len(ellipsoid_pairs(mu,[L,L],[1,2],1,.05)),1)
    def test_far_negative_and_near_noncontact(self):
        mu=np.array([[0,0,0],[0,0,8]])
        self.assertEqual(len(center_pairs(mu,[1,2],.1)),0)
        self.assertEqual(len(ellipsoid_pairs(mu,[np.eye(3)*.1]*2,[1,2],3,.1)),0)
        self.assertEqual(surface_relation(.02,.001,.05),'near_noncontact')
        self.assertEqual(surface_relation(0,.001,.05),'contact_GT')
