import runtime
import unittest
import numpy as np
from geometry import mesh_data
from hatching import generate_layers
from fixed_render import _coverage
from hybrid import compose
from line_field import fields, walk_field, regenerate, transport, DEFAULTS

def grid(curved=False, reverse=False, noisy=False):
    x=np.linspace(-.5,.5,9)
    v=np.array([[a,b,.25*a*a if curved else 0.] for b in x for a in x])
    if noisy:
        v[:,2]+=.009*np.array([(-1)**(i+j) for j in range(9) for i in range(9)])
    f=np.array([t for j in range(8) for i in range(8) for t in ([j*9+i,j*9+i+1,(j+1)*9+i+1],[j*9+i,(j+1)*9+i+1,(j+1)*9+i])])
    if reverse:f[::2]=f[::2,::-1]
    return mesh_data(v,f,np.full(len(f),4))

class FieldTests(unittest.TestCase):
    def test_flat_raw_and_regularized_identity(self):
        m=grid();q=np.array([[.7,.3,0.],[-.3,.7,0.]])
        a,b,d=fields(m,np.ones(len(m['faces']),int),q)
        for layer in range(2):
            expected=np.cross([0.,0.,1.],q[layer]);expected/=np.linalg.norm(expected)
            np.testing.assert_allclose(np.abs(a[:,layer]@expected),1.,atol=1e-12)
            np.testing.assert_allclose(np.abs(b[:,layer]@expected),1.,atol=1e-12)
        self.assertGreater(d['edge_pairs'],0)

    def test_curved_reversal_and_disconnected_sheets(self):
        q=np.array([[.7,.3,0.],[-.3,.7,0.]])
        m=grid(curved=True,noisy=True);r=grid(curved=True,noisy=True,reverse=True)
        a,b,d=fields(m,np.ones(len(m['faces']),int),q)
        ar,br,dr=fields(r,np.ones(len(r['faces']),int),q)
        np.testing.assert_allclose(np.abs(np.sum(a*ar,axis=2)),1.,atol=1e-10)
        np.testing.assert_allclose(np.abs(np.sum(b*br,axis=2)),1.,atol=1e-10)
        self.assertLess(d['regularized_connection_energy'],d['raw_connection_energy'])
        v=np.vstack([m['vertices'],m['vertices']+[0,0,.03]])
        f=np.vstack([m['faces'],m['faces']+len(m['vertices'])]);s=mesh_data(v,f,np.full(len(f),4))
        aa,bb,dd=fields(s,np.ones(len(f),int),q)
        np.testing.assert_allclose(np.abs(np.sum(bb[:len(a)]*b,axis=2)),1.,atol=1e-10)
        np.testing.assert_allclose(np.abs(np.sum(bb[len(a):]*b,axis=2)),1.,atol=1e-10)
        self.assertEqual(dd['edge_pairs'],2*d['edge_pairs'])

    def test_raw_reproduces_slices_and_boundaries(self):
        for curved in (False,True):
            m=grid(curved=curved);style=dict(angle=31.,spacing=.13,length=.17,width=1.,cross_enabled=False)
            old,_=generate_layers(m,4,style);angle=np.deg2rad(31);q=np.array([[np.cos(angle),np.sin(angle),0.]])
            a,b,d=fields(m,np.ones(len(m['faces']),int),q)
            new,records=regenerate(m,old,np.ones(len(m['faces']),bool),a,300_000_000_000)
            self.assertAlmostEqual(np.linalg.norm(new['points'][:,1]-new['points'][:,0],axis=1).sum(),np.linalg.norm(old['points'][:,1]-old['points'][:,0],axis=1).sum(),places=8)
            for rec in records:
                p=new['points'][new['stroke_id']==rec['stroke_id']];o=old['points'][old['stroke_id']==rec['parent_stroke_id']]
                np.testing.assert_allclose(p[0,0],o[0,0],atol=1e-8);np.testing.assert_allclose(p[-1,1],o[-1,1],atol=1e-8)
            np.testing.assert_allclose(new['points'],np.einsum('nij,njk->nik',new['bary'],m['tri'][new['face']]),atol=1e-12)
        p=np.where(m['tri'].mean(1)[:,0]<0,1,2)
        a,b,d=fields(m,p,q)
        self.assertEqual(d['cross_partition_pairs'],0)

    def test_real_foreground_and_zero_support(self):
        v=np.array([[-1,-1,4],[1,-1,4],[1,1,4],[-1,1,4],[-.2,-.4,3.4],[.2,-.4,3.4],[.2,.4,3.4],[-.2,.4,3.4]],float)
        f=np.array([[0,1,2],[0,2,3],[4,5,6],[4,6,7]]);m=mesh_data(v,f,np.full(4,4));gen=mesh_data(v,f,np.array([4,4,1,1]))
        style=dict(angle=90.,spacing=.13,length=.5,width=1.,cross_enabled=False)
        old,_=generate_layers(gen,4,style);a,b,d=fields(m,np.array([1,1,0,0]),np.array([[0,1.,0]]))
        cam=dict(extrinsic=np.eye(4).tolist(),width=96,height=96,fx=120.,fy=120.,cx=47.5,cy=47.5)
        for field in (a,b):
            new,_=regenerate(m,old,np.array([True,True,False,False]),field,300_000_000_000)
            r=_coverage(m,{4:new},{'4':style},cam,2)
            self.assertEqual(int(r['coverage'][4][0][90:102,90:102].sum()),0)
            self.assertGreater(int(r['coverage'][4][0].sum()),0)
            ink=r['coverage'][4][0].reshape(96,2,96,2).mean((1,3));paper=np.full((96,96,3),.95)
            im,alpha=compose(paper,ink,np.zeros_like(ink),True)
            np.testing.assert_array_equal(im,paper)

if __name__=='__main__':unittest.main(verbosity=2)
