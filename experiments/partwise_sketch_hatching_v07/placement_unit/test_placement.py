import runtime
import unittest
import numpy as np
from geometry import mesh_data
from hatching import generate_layers
from line_field import fields,regenerate
from fixed_render import _coverage
from hybrid import compose
from test_field import grid
from placement import PortalMetric,place,DEFAULTS

def triangle_strokes(ys):
    m=mesh_data(np.array([[-1.,-1,0],[1,-1,0],[0,1,0]]),np.array([[0,1,2]]),np.array([4]))
    points=np.array([[[-.1,y,0],[.1,y,0]] for y in ys]);matrix=np.vstack([m['tri'][0,:,:2].T,np.ones(3)])
    bary=np.array([[np.linalg.solve(matrix,np.r_[p[:2],1.]) for p in pp] for pp in points])
    return m,dict(points=points,bary=bary,face=np.zeros(len(ys),np.int32),stroke_id=np.arange(len(ys),dtype=np.int64)+1,layer_id=np.zeros(len(ys),np.uint8))

class PlacementTests(unittest.TestCase):
    def test_whole_path_clearance_and_clustering(self):
        m,old=triangle_strokes([0.,.01,.02]);metric=PortalMetric(m,np.ones(1,bool))
        other={k:v[1:] for k,v in old.items()};one={k:v[:1] for k,v in old.items()}
        d,w=metric.clearance(one,metric.distance_field(other),other)
        np.testing.assert_allclose(d,.01,atol=1e-12)
        f=np.array([[[1.,0,0]]]);new,rec,diag=place(m,old,np.ones(1,bool),f,500_000_000_000)
        self.assertGreater(diag['moved_strokes'],0)
        self.assertGreater(diag['after']['weighted_mean_capped_distance'],diag['before']['weighted_mean_capped_distance'])
        for r in rec:self.assertAlmostEqual(r['actual_length'],.2,places=10)
        # Same-face crossing must give zero clearance at a sampled intersection.
        crossing=dict(one);crossing['points']=np.array([[[0,-.1,0],[0,.1,0]]])
        d,_=metric.clearance(crossing,metric.distance_field(one),one)
        self.assertAlmostEqual(float(d.min()),0.,places=12)

    def test_components_partition_hole_and_vertex_contact(self):
        m=grid();allowed=np.ones(len(m['faces']),bool);allowed[40:48]=False
        metric=PortalMetric(m,allowed)
        for edge,faces in metric.portal_faces:
            self.assertEqual(len(faces),2);self.assertTrue(allowed[faces].all())
        v=np.vstack([m['vertices'],m['vertices']+[0,0,.001]])
        f=np.vstack([m['faces'],m['faces']+len(m['vertices'])]);s=mesh_data(v,f,np.full(len(f),4))
        metric=PortalMetric(s,np.ones(len(f),bool))
        self.assertNotEqual(metric.components[0],metric.components[len(m['faces'])])
        # Two faces sharing only a vertex cannot transfer surface distance.
        v=np.array([[0.,0,0],[1,0,0],[0,1,0],[-1,0,0],[0,-1,0]])
        s=mesh_data(v,np.array([[0,1,2],[0,3,4]]),np.array([4,4]));p=PortalMetric(s,np.ones(2,bool))
        self.assertNotEqual(p.components[0],p.components[1])
        s=mesh_data(v,np.array([[0,1,2],[0,1,3],[0,1,4]]),np.full(3,4));p=PortalMetric(s,np.ones(3,bool))
        self.assertEqual(len(p.portal_faces),0)

    def test_curved_lengths_anchors_determinism_and_boundary_fallback(self):
        m=grid(curved=True);style=dict(angle=31.,spacing=.17,length=.17,width=1.,cross_enabled=False)
        old,_=generate_layers(m,4,style);q=np.array([[np.cos(np.deg2rad(31)),np.sin(np.deg2rad(31)),0.]])
        field,_,_=fields(m,np.ones(len(m['faces']),int),q);allowed=np.ones(len(m['faces']),bool)
        a,rec,d=place(m,old,allowed,field,500_000_000_000)
        b,rr,dd=place(m,old,allowed,field,500_000_000_000)
        for key in a:np.testing.assert_array_equal(a[key],b[key])
        self.assertEqual(len(rec),len(np.unique(old['stroke_id'])))
        for r in rec:self.assertAlmostEqual(r['actual_length'],r['requested_length'],places=9)
        np.testing.assert_allclose(a['points'],np.einsum('nij,njk->nik',a['bary'],m['tri'][a['face']]),atol=1e-12)
        self.assertTrue((a['bary']>=-1e-10).all())
        # One isolated stroke has no spacing gain and must retain its feasible seed.
        m,old=triangle_strokes([.8]);a,rec,d=place(m,old,np.ones(1,bool),np.array([[[1.,0,0]]]),500_000_000_000)
        self.assertEqual(d['moved_strokes'],0);self.assertEqual(rec[0]['chosen_candidate'],0)

    def test_same_label_foreground_and_zero_S(self):
        v=np.array([[-1,-1,4],[1,-1,4],[1,1,4],[-1,1,4],[-.2,-.4,3.4],[.2,-.4,3.4],[.2,.4,3.4],[-.2,.4,3.4]],float)
        f=np.array([[0,1,2],[0,2,3],[4,5,6],[4,6,7]]);m=mesh_data(v,f,np.full(4,4));gen=mesh_data(v,f,np.array([4,4,1,1]))
        style=dict(angle=90.,spacing=.13,length=.5,width=1.,cross_enabled=False)
        old,_=generate_layers(gen,4,style);field,_,_=fields(m,np.array([1,1,0,0]),np.array([[0,1.,0]]))
        new,_,_=place(m,old,np.array([True,True,False,False]),field,500_000_000_000)
        cam=dict(extrinsic=np.eye(4).tolist(),width=96,height=96,fx=120.,fy=120.,cx=47.5,cy=47.5)
        r=_coverage(m,{4:new},{'4':style},cam,2);mask=r['coverage'][4][0]
        self.assertEqual(int(mask[90:102,90:102].sum()),0);self.assertGreater(int(mask.sum()),0)
        ink=mask.reshape(96,2,96,2).mean((1,3));paper=np.full((96,96,3),.95)
        im,_=compose(paper,ink,np.zeros_like(ink),True);np.testing.assert_array_equal(im,paper)

if __name__=='__main__':unittest.main(verbosity=2)
