import runtime
import unittest
import numpy as np
from geometry import mesh_data
from hatching import generate_layers
from line_field import regenerate,walk_field,transport
from global_field import global_fields
from fixed_render import _coverage
from hybrid import compose

def grid(curved=False,reverse=False,noisy=False):
    x=np.linspace(-.5,.5,9)
    v=np.array([[np.sin(a),b,1-np.cos(a)] if curved else [a,b,0.] for b in x for a in x])
    if noisy:v[:,2]+=.009*np.array([(-1)**(i+j) for j in range(9) for i in range(9)])
    f=np.array([t for j in range(8) for i in range(8) for t in ([j*9+i,j*9+i+1,(j+1)*9+i+1],[j*9+i,(j+1)*9+i+1,(j+1)*9+i])])
    if reverse:f[::2]=f[::2,::-1]
    return mesh_data(v,f,np.full(len(f),4))

class GlobalTests(unittest.TestCase):
    def test_flat_identity_and_fixed_anchor(self):
        m=grid();q=np.array([[.7,.3,0.],[-.3,.7,0.]])
        a,b,d,s=global_fields(m,np.ones(len(m['faces']),int),q)
        np.testing.assert_allclose(np.abs(np.sum(a*b,axis=2)),1.,atol=1e-12)
        np.testing.assert_allclose(s['amplitude'],1.,atol=1e-12)
        self.assertEqual(len(s['anchors']),1)
        np.testing.assert_allclose(d['free_residual_max'],0.,atol=1e-12)
        self.assertEqual(d['fallback_selected_face_layers'],0)

    def test_developable_transport_and_winding(self):
        q=np.array([[.7,.3,.1],[-.3,.7,.1]])
        m=grid(True);r=grid(True,True)
        a,b,d,s=global_fields(m,np.ones(len(m['faces']),int),q)
        ar,br,dr,sr=global_fields(r,np.ones(len(r['faces']),int),q)
        np.testing.assert_allclose(np.abs(np.sum(b*br,axis=2)),1.,atol=1e-10)
        np.testing.assert_allclose(s['amplitude'],1.,atol=1e-10)
        self.assertLess(d['normalized_graph_energy_H'],1e-12)
        for i,j in s['graph_pairs']:
            edge=tuple(sorted(set(m['faces'][i])&set(m['faces'][j])))
            t=transport(m,int(i),int(j),edge)@b[j,0]
            self.assertAlmostEqual(abs(t@b[i,0]),1.,places=10)

    def test_noise_disconnected_partition_and_isolated(self):
        m=grid(False,False,True);q=np.array([[.7,.3,0.],[-.3,.7,0.]])
        a,b,d,s=global_fields(m,np.ones(len(m['faces']),int),q)
        np.testing.assert_allclose(np.sum(b*m['normals'][:,None,:],axis=2),0.,atol=1e-12)
        self.assertTrue(np.isfinite(b).all());self.assertLess(d['free_residual_max'],1e-10)
        v=np.vstack([m['vertices'],m['vertices']+[0,0,.03]])
        f=np.vstack([m['faces'],m['faces']+len(m['vertices'])]);both=mesh_data(v,f,np.full(len(f),4))
        aa,bb,dd,ss=global_fields(both,np.ones(len(f),int),q)
        np.testing.assert_allclose(np.abs(np.sum(bb[:len(b)]*b,axis=2)),1.,atol=1e-10)
        self.assertEqual(dd['components'],2)
        walk=walk_field(both,50,np.array([.2,.3,.5]),bb[50,0],3.,np.ones(len(f),bool),bb[:,0])
        self.assertTrue((walk['face']<len(m['faces'])).all())
        labels=np.arange(1,len(m['faces'])+1)
        aa,bb,dd,ss=global_fields(m,labels,q)
        self.assertEqual(dd['components'],len(labels))
        np.testing.assert_allclose(np.abs(np.sum(aa*bb,axis=2)),1.,atol=1e-12)

    def test_path_recovery_and_original_stops(self):
        m=grid(True);style=dict(angle=31.,spacing=.13,length=.17,width=1.,cross_enabled=False)
        old,_=generate_layers(m,4,style);angle=np.deg2rad(31);q=np.array([[np.cos(angle),np.sin(angle),0.]])
        a,b,d,s=global_fields(m,np.ones(len(m['faces']),int),q)
        for field,offset in [(a,900_000_000_000),(b,1_000_000_000_000)]:
            new,records=regenerate(m,old,np.ones(len(m['faces']),bool),field,offset)
            np.testing.assert_allclose(new['points'],np.einsum('nij,njk->nik',new['bary'],m['tri'][new['face']]),atol=1e-12)
            for rec in records:
                self.assertLessEqual(rec['actual_length'],rec['requested_length']+1e-10)
                if field is a:
                    pp=new['points'][new['stroke_id']==rec['stroke_id']];op=old['points'][old['stroke_id']==rec['parent_stroke_id']]
                    np.testing.assert_allclose(pp[[0,-1],[0,1]],op[[0,-1],[0,1]],atol=1e-8)
        allowed=np.zeros(len(m['faces']),bool);allowed[50]=True
        w=walk_field(m,50,np.array([.2,.3,.5]),b[50,0],3.,allowed,b[:,0])
        self.assertEqual(w['reason'],'authored_region_boundary')

    def test_real_occluder_and_zero_S(self):
        v=np.array([[-1,-1,4],[1,-1,4],[1,1,4],[-1,1,4],[-.2,-.4,3.4],[.2,-.4,3.4],[.2,.4,3.4],[-.2,.4,3.4]],float)
        f=np.array([[0,1,2],[0,2,3],[4,5,6],[4,6,7]]);m=mesh_data(v,f,np.full(4,4));gen=mesh_data(v,f,np.array([4,4,1,1]))
        style=dict(angle=90.,spacing=.13,length=.5,width=1.,cross_enabled=False);old,_=generate_layers(gen,4,style)
        a,b,d,s=global_fields(m,np.array([1,1,0,0]),np.array([[0,1.,0]]))
        cam=dict(extrinsic=np.eye(4).tolist(),width=96,height=96,fx=120.,fy=120.,cx=47.5,cy=47.5)
        for field in (a,b):
            new,_=regenerate(m,old,np.array([True,True,False,False]),field,1_000_000_000_000)
            r=_coverage(m,{4:new},{'4':style},cam,2)
            self.assertEqual(int(r['coverage'][4][0][90:102,90:102].sum()),0)
            self.assertGreater(int(r['coverage'][4][0].sum()),0)
            ink=r['coverage'][4][0].reshape(96,2,96,2).mean((1,3));paper=np.full((96,96,3),.95)
            im,alpha=compose(paper,ink,np.zeros_like(ink),True);np.testing.assert_array_equal(im,paper)

if __name__=='__main__':unittest.main(verbosity=2)
