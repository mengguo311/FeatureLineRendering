import runtime
import unittest
import numpy as np
from geometry import mesh_data
from hatching import generate_layers
from fixed_render import _coverage
from hybrid import compose
from line_field import regenerate, walk_field
from projection_field import projected_fields

def grid(curved=False, reverse=False, noisy=False):
    x=np.linspace(-.5,.5,9)
    v=np.array([[a,b,.25*a*a if curved else 0.] for b in x for a in x])
    if noisy:v[:,2]+=.009*np.array([(-1)**(i+j) for j in range(9) for i in range(9)])
    f=np.array([t for j in range(8) for i in range(8) for t in ([j*9+i,j*9+i+1,(j+1)*9+i+1],[j*9+i,(j+1)*9+i+1,(j+1)*9+i])])
    if reverse:f[::2]=f[::2,::-1]
    return mesh_data(v,f,np.full(len(f),4))

class ProjectionTests(unittest.TestCase):
    def test_flat_reference_identity_and_tilted_projection(self):
        m=grid();q=np.array([[.7,.3,0.],[-.3,.7,0.]])
        a,b,d=projected_fields(m,np.ones(len(m['faces']),int),q,[0,0,1])
        np.testing.assert_allclose(a,b,atol=1e-12)
        self.assertEqual(d['fallback_selected_face_layers'],0)
        v=m['vertices'].copy();v[:,2]=.6*v[:,0]+.2*v[:,1]
        tilted=mesh_data(v,m['faces'],m['regions'])
        a,b,d=projected_fields(tilted,np.ones(len(m['faces']),int),q,[0,0,1])
        n=np.array([-.6,-.2,1.]);n/=np.linalg.norm(n)
        for k in range(2):
            guide=np.array([-q[k,1],q[k,0],0.]);guide/=np.linalg.norm(guide)
            expected=guide-(guide@n)*n;expected/=np.linalg.norm(expected)
            np.testing.assert_allclose(b[:,k],np.broadcast_to(expected,b[:,k].shape),atol=1e-12)
        self.assertGreater(float(np.max(np.abs(a-b))),.01)

    def test_curve_winding_and_disconnected_sheets(self):
        q=np.array([[.7,.3,0.],[-.3,.7,0.]])
        m=grid(True,False,True);r=grid(True,True,True)
        a,b,d=projected_fields(m,np.ones(len(m['faces']),int),q,[0,0,1])
        ar,br,dr=projected_fields(r,np.ones(len(r['faces']),int),q,[0,0,1])
        np.testing.assert_allclose(np.abs(np.sum(a*ar,axis=2)),1.,atol=1e-12)
        np.testing.assert_allclose(b,br,atol=1e-12)
        np.testing.assert_allclose(np.sum(b*m['normals'][:,None,:],axis=2),0.,atol=1e-12)
        v=np.vstack([m['vertices'],m['vertices']+[0,0,.03]])
        f=np.vstack([m['faces'],m['faces']+len(m['vertices'])]);s=mesh_data(v,f,np.full(len(f),4))
        aa,bb,dd=projected_fields(s,np.ones(len(f),int),q,[0,0,1])
        np.testing.assert_allclose(bb[:len(b)],b,atol=1e-12)
        walked=walk_field(s,50,np.array([.2,.3,.5]),bb[50,0],3.,np.ones(len(f),bool),bb[:,0])
        self.assertTrue((walked['face']<len(m['faces'])).all())
        self.assertEqual(walked['reason'],'mesh_boundary')

    def test_degenerate_projection_explicit_same_face_fallback(self):
        v=np.array([[0,0,0],[1,0,0],[0,0,1]],float)
        m=mesh_data(v,np.array([[0,1,2]]),np.array([4]))
        a,b,d=projected_fields(m,np.ones(1,int),np.array([[1.,0,0]]),[0,0,1])
        np.testing.assert_array_equal(a,b)
        self.assertEqual(d['fallback_selected_face_layers'],1)
        self.assertEqual(d['layers'][0]['fallback_selected_faces'],1)

    def test_path_recovery_anchors_and_partition_stops(self):
        for curved in (False,True):
            m=grid(curved);style=dict(angle=31.,spacing=.13,length=.17,width=1.,cross_enabled=False)
            old,_=generate_layers(m,4,style);angle=np.deg2rad(31);q=np.array([[np.cos(angle),np.sin(angle),0.]])
            a,b,d=projected_fields(m,np.ones(len(m['faces']),int),q,[0,0,1])
            for field,offset in [(a,700_000_000_000),(b,800_000_000_000)]:
                new,records=regenerate(m,old,np.ones(len(m['faces']),bool),field,offset)
                np.testing.assert_allclose(new['points'],np.einsum('nij,njk->nik',new['bary'],m['tri'][new['face']]),atol=1e-12)
                for rec in records:
                    self.assertLessEqual(rec['actual_length'],rec['requested_length']+1e-10)
                    if field is a:
                        p=new['points'][new['stroke_id']==rec['stroke_id']];o=old['points'][old['stroke_id']==rec['parent_stroke_id']]
                        np.testing.assert_allclose(p[[0,-1],[0,1]],o[[0,-1],[0,1]],atol=1e-8)
        allowed=np.zeros(len(m['faces']),bool);allowed[50]=True
        walked=walk_field(m,50,np.array([.2,.3,.5]),b[50,0],3.,allowed,b[:,0])
        self.assertEqual(walked['reason'],'authored_region_boundary')
        self.assertTrue((walked['face']==50).all())

    def test_real_foreground_and_zero_support(self):
        v=np.array([[-1,-1,4],[1,-1,4],[1,1,4],[-1,1,4],[-.2,-.4,3.4],[.2,-.4,3.4],[.2,.4,3.4],[-.2,.4,3.4]],float)
        f=np.array([[0,1,2],[0,2,3],[4,5,6],[4,6,7]]);m=mesh_data(v,f,np.full(4,4));gen=mesh_data(v,f,np.array([4,4,1,1]))
        style=dict(angle=90.,spacing=.13,length=.5,width=1.,cross_enabled=False)
        old,_=generate_layers(gen,4,style)
        a,b,d=projected_fields(m,np.array([1,1,0,0]),np.array([[0,1.,0]]),[0,0,1])
        cam=dict(extrinsic=np.eye(4).tolist(),width=96,height=96,fx=120.,fy=120.,cx=47.5,cy=47.5)
        for field in (a,b):
            new,_=regenerate(m,old,np.array([True,True,False,False]),field,800_000_000_000)
            r=_coverage(m,{4:new},{'4':style},cam,2)
            self.assertEqual(int(r['coverage'][4][0][90:102,90:102].sum()),0)
            self.assertGreater(int(r['coverage'][4][0].sum()),0)
            ink=r['coverage'][4][0].reshape(96,2,96,2).mean((1,3));paper=np.full((96,96,3),.95)
            im,alpha=compose(paper,ink,np.zeros_like(ink),True)
            np.testing.assert_array_equal(im,paper)

if __name__=='__main__':unittest.main(verbosity=2)
