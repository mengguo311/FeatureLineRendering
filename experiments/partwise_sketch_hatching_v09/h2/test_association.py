import runtime
import unittest
import numpy as np
from geometry import mesh_data,orbit_camera
from association import SurfaceGuide,trim_paths,crossings,guided_field
from structure import raster_structure

def fixture(disjoint=False):
    v=np.array([[0.,0,0],[1.,0,0],[0.,1,0],[1.,1,0]])
    f=np.array([[0,1,2],[1,3,2]])
    if disjoint:
        v=np.r_[v,v+[0,0,.001]];f=np.r_[f,f+4]
    return mesh_data(v,f,np.full(len(f),5))
def path(mesh,face,bary,sid=1):
    b=np.asarray(bary,float).reshape(1,2,3)
    return dict(points=b@mesh['tri'][face],bary=b,face=np.array([face]),stroke_id=np.array([sid]),layer_id=np.array([0],np.uint8),visibility_mask=np.array([32],np.uint64))
class AssociationTest(unittest.TestCase):
    def test_crossing_trim_and_open_ends(self):
        m=fixture();g=path(m,0,[[.6,.2,.2],[.2,.6,.2]])
        p=path(m,0,[[.7,.3,0],[.3,.3,.4]])
        self.assertEqual(len(crossings(p,g)),1)
        metric=SurfaceGuide(m,g,m['regions']==5)
        q,rec=trim_paths(m,p,metric,.05)
        self.assertAlmostEqual(np.linalg.norm(q['points'][:,1]-q['points'][:,0],axis=1).sum(),.3,places=6)
        self.assertEqual(len(np.unique(q['stroke_id'])),1)
        self.assertAlmostEqual(metric.distance(0,np.array([[.8,.2,0]]))[0],.2,places=6)
        self.assertGreater(rec['trimmed_length'],0)
    def test_disjoint_sheet_and_shared_edge(self):
        m=fixture(True);g=path(m,0,[[.1,.45,.45],[.1,.55,.35]])
        metric=SurfaceGuide(m,g,m['regions']==5)
        self.assertTrue(np.isinf(metric.distance(2,np.array([[.45,.45,.001]])))[0])
        self.assertLess(metric.distance(1,np.array([[.5,.51,0]]))[0],.2)
        p=path(m,2,[[.7,.3,0],[.3,.3,.4]])
        q,r=trim_paths(m,p,metric,.1);np.testing.assert_array_equal(q['points'],p['points'])
    def test_direction_bounded_and_other_sheet_unchanged(self):
        m=fixture(True);g=path(m,0,[[.6,.2,.2],[.2,.6,.2]])
        metric=SurfaceGuide(m,g,m['regions']==5)
        raw=np.tile([0.,1,0],(4,1));d,report=guided_field(m,raw,metric,2.,30.)
        np.testing.assert_array_equal(d[2:],raw[2:])
        self.assertLessEqual(report['maximum_change_degrees'],30.+1e-8)
        self.assertGreater(report['maximum_change_degrees'],0)
    def test_actual_occluder_rejects_structure(self):
        m=fixture();g=path(m,0,[[.6,.2,.2],[.2,.6,.2]])
        g['curve_id']=g.pop('stroke_id')
        c=orbit_camera(180,89,3,64,target=(.5,.5,0))
        front=mesh_data(np.r_[m['vertices'],m['vertices']+[0,0,.2]],np.r_[m['faces'],m['faces']+4],np.full(4,5))
        own,_=raster_structure(m,g,c);hidden,_=raster_structure(front,g,c)
        self.assertGreater(own.sum(),0);self.assertEqual(hidden.sum(),0)
if __name__=='__main__':unittest.main()
