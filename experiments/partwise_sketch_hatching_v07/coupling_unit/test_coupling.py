import runtime
import unittest
import numpy as np
from geometry import mesh_data
from hatching import generate_layers
from line_field import regenerate,walk_field
from coupling import restore_crossing,replace_second_layer
from fixed_render import _coverage
from hybrid import compose

def grid(curved=False,reverse=False):
    x=np.linspace(-.5,.5,9)
    v=np.array([[np.sin(a),b,1-np.cos(a)] if curved else [a,b,0.] for b in x for a in x])
    f=np.array([t for j in range(8) for i in range(8) for t in ([j*9+i,j*9+i+1,(j+1)*9+i+1],[j*9+i,(j+1)*9+i+1,(j+1)*9+i])])
    if reverse:f[::2]=f[::2,::-1]
    return mesh_data(v,f,np.full(len(f),4))

def fields(m):
    n=m['normals'];q=np.array([[.7,.3,.1],[-.3,.7,.1]])
    f=np.cross(n[:,None,:],q[None,:,:]);f/=np.linalg.norm(f,axis=2,keepdims=True)
    # Independent prescribed primary tangent, with collapsed secondary layer.
    c=np.cross(n,np.array([.2,.8,.3]));c/=np.linalg.norm(c,axis=1,keepdims=True)
    return f,np.stack([c,c],axis=1)

class CouplingTests(unittest.TestCase):
    def test_known_flat_rotation(self):
        n=np.array([[0.,0.,1.]])
        f=np.array([[[1.,0.,0.],[.5,np.sqrt(3)/2,0.]]])
        h=np.array([[[0.,1.,0.],[0.,1.,0.]]])
        j=restore_crossing(n,f,h,np.array([True]))
        np.testing.assert_array_equal(j[:,0],h[:,0])
        np.testing.assert_allclose(j[0,1],[-np.sqrt(3)/2,.5,0.],atol=1e-12)
        np.testing.assert_allclose(restore_crossing(n,f,f,np.array([True])),f,atol=1e-12)

    def test_curved_signed_relation_and_line_signs(self):
        m=grid(True);f,h=fields(m);sel=np.ones(len(f),bool)
        j=restore_crossing(m['normals'],f,h,sel)
        np.testing.assert_allclose(np.sum(j[:,0]*j[:,1],axis=1),np.sum(f[:,0]*f[:,1],axis=1),atol=1e-12)
        np.testing.assert_allclose(np.sum(np.cross(j[:,0],j[:,1])*m['normals'],axis=1),np.sum(np.cross(f[:,0],f[:,1])*m['normals'],axis=1),atol=1e-12)
        np.testing.assert_allclose(np.linalg.norm(j,axis=2),1.,atol=1e-12)
        for flip in ('a','b','c','n'):
            ff=f.copy();hh=h.copy();nn=m['normals'].copy()
            if flip=='a':ff[::2,0]*=-1
            if flip=='b':ff[::2,1]*=-1
            if flip=='c':hh[::2,0]*=-1
            if flip=='n':nn[::2]*=-1
            jj=restore_crossing(nn,ff,hh,sel)
            np.testing.assert_allclose(np.abs(np.sum(j*jj,axis=2)),1.,atol=1e-12)
        mr=grid(True,True);fr,hr=fields(mr);jr=restore_crossing(mr['normals'],fr,hr,sel)
        np.testing.assert_allclose(np.abs(np.sum(j*jr,axis=2)),1.,atol=1e-12)

    def test_frozen_primary_original_seed_and_anchors(self):
        m=grid(True);f,h=fields(m);allowed=np.ones(len(f),bool);j=restore_crossing(m['normals'],f,h,allowed)
        style=dict(angle=31.,spacing=.13,length=.17,width=1.,cross_enabled=True,cross_spacing=.13)
        original,_=generate_layers(m,4,style);hp,hr=regenerate(m,original,allowed,h,1_000_000_000_000)
        jp,jr=replace_second_layer(m,original,hp,hr,allowed,j,1_100_000_000_000)
        for key in hp:np.testing.assert_array_equal(jp[key][jp['layer_id']==0],hp[key][hp['layer_id']==0])
        expected,er=regenerate(m,{k:v[original['layer_id']==1] for k,v in original.items()},allowed,j,1_100_000_000_000)
        for key in expected:np.testing.assert_array_equal(jp[key][jp['layer_id']==1],expected[key])
        self.assertEqual([r for r in jr if r['layer_id']==1],er)
        np.testing.assert_allclose(jp['points'],np.einsum('nij,njk->nik',jp['bary'],m['tri'][jp['face']]),atol=1e-12)
        for r in jr:self.assertLessEqual(r['actual_length'],r['requested_length']+1e-10)
        # A disconnected nearby sheet must never become a walker neighbor.
        both=mesh_data(np.vstack([m['vertices'],m['vertices']+[0,0,.03]]),np.vstack([m['faces'],m['faces']+len(m['vertices'])]),np.full(2*len(f),4))
        w=walk_field(both,50,np.array([.2,.3,.5]),j[50,1],3.,np.ones(2*len(f),bool),np.vstack([j[:,1],j[:,1]]))
        self.assertTrue((w['face']<len(f)).all())
        one=np.zeros(len(f),bool);one[50]=True
        w=walk_field(m,50,np.array([.2,.3,.5]),j[50,1],3.,one,j[:,1])
        self.assertEqual(w['reason'],'authored_region_boundary')

    def test_same_label_real_occluder_and_zero_support(self):
        v=np.array([[-1,-1,4],[1,-1,4],[1,1,4],[-1,1,4],[-.2,-.4,3.4],[.2,-.4,3.4],[.2,.4,3.4],[-.2,.4,3.4]],float)
        faces=np.array([[0,1,2],[0,2,3],[4,5,6],[4,6,7]])
        m=mesh_data(v,faces,np.full(4,4));gen=mesh_data(v,faces,np.array([4,4,1,1]));allowed=np.array([True,True,False,False])
        style=dict(angle=90.,spacing=.13,length=.5,width=1.,cross_enabled=True,cross_spacing=.13)
        old,_=generate_layers(gen,4,style);f,h=fields(m);j=restore_crossing(m['normals'],f,h,allowed)
        hp,hr=regenerate(m,old,allowed,h,1_000_000_000_000);jp,_=replace_second_layer(m,old,hp,hr,allowed,j,1_100_000_000_000)
        cam=dict(extrinsic=np.eye(4).tolist(),width=96,height=96,fx=120.,fy=120.,cx=47.5,cy=47.5)
        r=_coverage(m,{4:jp},{'4':style},cam,2)
        for mask in r['coverage'][4].values():
            self.assertEqual(int(mask[90:102,90:102].sum()),0);self.assertGreater(int(mask.sum()),0)
        ink=np.maximum.reduce(list(r['coverage'][4].values())).reshape(96,2,96,2).mean((1,3));paper=np.full((96,96,3),.95)
        im,_=compose(paper,ink,np.zeros_like(ink),True);np.testing.assert_array_equal(im,paper)

if __name__=='__main__':unittest.main(verbosity=2)
