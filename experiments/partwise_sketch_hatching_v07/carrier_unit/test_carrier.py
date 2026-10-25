import runtime
import unittest
import numpy as np
from geometry import mesh_data
from hatching import generate_layers
from render import _coverage as original_coverage
from hybrid import compose
from carrier import denoise,DEFAULTS
from fixed_render import _coverage

def grid(curved=False,noise=False,hole=False,fold=False):
    n=9;x=np.linspace(-.4,.4,n)
    v=np.array([[a,b,.12*(a*a+b*b) if curved else .8*abs(a) if fold else 0.] for b in x for a in x])
    clean=v.copy()
    if noise:
        for j in range(1,n-1):
            for i in range(1,n-1):v[j*n+i,2]+=.008*(-1)**(i+j)
    f=np.array([t for j in range(n-1) for i in range(n-1) if not(hole and i==3 and j==3)
        for t in ([j*n+i,j*n+i+1,(j+1)*n+i+1],[j*n+i,(j+1)*n+i+1,(j+1)*n+i])])
    return mesh_data(v,f,np.full(len(f),4)),clean

class CarrierTests(unittest.TestCase):
    def test_known_noisy_flat_and_curved(self):
        for curved in (False,True):
            m,clean=grid(curved=curved,noise=True);p=np.ones(len(m['faces']),int)
            c,d=denoise(m,p)
            movable=~d['protected'];self.assertGreater(movable.sum(),0)
            before=np.mean((m['vertices'][movable,2]-clean[movable,2])**2)
            after=np.mean((c['vertices'][movable,2]-clean[movable,2])**2)
            self.assertLess(after,before)
            self.assertLessEqual(np.linalg.norm(c['vertices']-m['vertices'],axis=1).max(),DEFAULTS['max_displacement']+1e-12)
            np.testing.assert_array_equal(c['faces'],m['faces'])
            np.testing.assert_array_equal(c['vertices'][d['protected']],m['vertices'][d['protected']])
    def test_flat_identity_sharp_fold_hole_disjoint_partitions(self):
        m,_=grid();c,d=denoise(m,np.ones(len(m['faces']),int))
        np.testing.assert_allclose(c['vertices'],m['vertices'],atol=1e-14,rtol=0)
        m,_=grid(fold=True);c,d=denoise(m,np.ones(len(m['faces']),int))
        ridge=np.abs(m['vertices'][:,0])<1e-10
        self.assertTrue(d['protected'][ridge].all())
        np.testing.assert_array_equal(c['vertices'][ridge],m['vertices'][ridge])
        m,_=grid(noise=True,hole=True)
        v=np.vstack([m['vertices'],m['vertices']+[0,0,.03]])
        f=np.vstack([m['faces'],m['faces']+len(m['vertices'])])
        sheets=mesh_data(v,f,np.full(len(f),4));p=np.r_[np.ones(len(m['faces']),int),np.full(len(m['faces']),2)]
        c,d=denoise(sheets,p)
        np.testing.assert_array_equal(c['faces'],f)
        np.testing.assert_array_equal(c['vertices'][d['protected']],v[d['protected']])
        np.testing.assert_allclose(c['vertices'][len(m['vertices']):]-c['vertices'][:len(m['vertices'])],np.broadcast_to([0,0,.03],m['vertices'].shape),atol=1e-12)
        split=np.where(m['tri'].mean(1)[:,0]<0,1,2);c,d=denoise(m,split)
        boundary=np.abs(m['vertices'][:,0])<1e-10
        self.assertTrue(d['protected'][boundary].all())
    def test_separate_carrier_depth_and_true_foreground(self):
        v=np.array([[-1,-1,4],[1,-1,4],[1,1,4],[-1,1,4],[-.2,-.4,3.4],[.2,-.4,3.4],[.2,.4,3.4],[-.2,.4,3.4]],float)
        f=np.array([[0,1,2],[0,2,3],[4,5,6],[4,6,7]]);ref=mesh_data(v,f,np.full(4,4))
        style=dict(angle=90.,spacing=.13,length=.5,width=1.,cross_enabled=False)
        gen=mesh_data(v,f,np.array([4,4,1,1]));paths,_=generate_layers(gen,4,style)
        cam=dict(extrinsic=np.eye(4).tolist(),width=96,height=96,fx=120.,fy=120.,cx=47.5,cy=47.5)
        a=original_coverage(ref,{4:paths},{'4':style},cam,2)
        b=_coverage(ref,{4:paths},{'4':style},cam,2,occluder=ref)
        np.testing.assert_array_equal(a['coverage'][4][0],b['coverage'][4][0])
        self.assertEqual(int(b['coverage'][4][0][90:102,90:102].sum()),0)
        shifted=v.copy();shifted[:4,2]+=.02;carrier=mesh_data(shifted,f,ref['regions'])
        moved={k:x.copy() for k,x in paths.items()};moved['points']=np.einsum('nij,njk->nik',moved['bary'],carrier['tri'][moved['face']])
        c=_coverage(carrier,{4:moved},{'4':style},cam,2,occluder=ref)
        self.assertEqual(int(c['coverage'][4][0].sum()),0)
        own=_coverage(carrier,{4:moved},{'4':style},cam,2,occluder=carrier)
        self.assertGreater(int(own['coverage'][4][0].sum()),0)
        ink=b['coverage'][4][0].reshape(96,2,96,2).mean((1,3));paper=np.full((96,96,3),.95)
        im,alpha=compose(paper,ink,np.zeros_like(ink),True)
        np.testing.assert_array_equal(im,paper);self.assertEqual(float(alpha.sum()),0)

if __name__=='__main__':unittest.main(verbosity=2)
