import runtime
import unittest
import numpy as np
from geometry import mesh_data
from hatching import generate_layers
from embedding import migrate
from fixed_render import _coverage
from hybrid import compose

def fixture(shape='flat'):
    xs=np.linspace(-.12,.12,13)
    z=lambda x: 0. if shape=='flat' else (abs(x)*.7 if shape=='fold' else 1-np.cos(3*x))
    v=np.array([[x,y,4+z(x)] for x in xs for y in (-.2,.2)])
    f=np.array([t for i in range(12) for t in ([2*i,2*i+2,2*i+3],[2*i,2*i+3,2*i+1])])
    m=mesh_data(v,f,np.full(len(f),4));style=dict(angle=90.,spacing=.2,length=.4,width=1.,cross_enabled=False)
    p,_=generate_layers(m,4,style)
    sid=np.unique(p['stroke_id'])[0];p={k:a[p['stroke_id']==sid] for k,a in p.items()}
    p['layer_id']=np.zeros(len(p['face']),np.uint8);p['visibility_mask']=np.full(len(p['face']),16,np.uint64)
    p['parent_stroke_id']=p['stroke_id'].copy()
    lengths=np.linalg.norm(p['points'][:,1]-p['points'][:,0],axis=1);cs=np.cumsum(lengths)
    idx=int(np.argmin(abs(cs[:-1]-cs[-1]*.45)))
    edge=[int(p['face'][idx]),int(p['face'][idx+1])]
    return m,p,style,np.array([edge])


class EmbeddingTests(unittest.TestCase):
    def test_identity_and_known_affine_shared_edge(self):
        for shape in ('flat','fold','curve'):
            m,p,style,_=fixture(shape)
            same,record=migrate(p,m,m,4_000_000_000_000)
            np.testing.assert_allclose(same['points'],p['points'],atol=1e-14,rtol=0)
            v=m['vertices'].copy();v[:,0]*=1.03;v[:,2]+=.001*(v[:,0]+.12)
            target=mesh_data(v,m['faces'],m['regions']);q,rec=migrate(p,m,target,4_000_000_000_000)
            expected=p['points'].copy();expected[:,:,0]*=1.03;expected[:,:,2]+=.001*(expected[:,:,0]+.12)
            np.testing.assert_allclose(q['points'],expected,atol=1e-13,rtol=0)
            for k in p:
                if k not in ('points','stroke_id'):np.testing.assert_array_equal(q[k],p[k])
            np.testing.assert_allclose(q['points'][:-1,1],q['points'][1:,0],atol=1e-13,rtol=0)
            self.assertEqual(len(q['face']),len(p['face']));self.assertEqual(len(rec),1)
            self.assertFalse(set(q['stroke_id'])&set(p['stroke_id']))
            again,_=migrate(p,m,target,4_000_000_000_000)
            for key in q:np.testing.assert_array_equal(q[key],again[key])

    def test_topology_labels_rejected_and_boundary_anchors_preserved(self):
        m,p,_,_=fixture('fold');bad=dict(m,faces=m['faces'][::-1])
        with self.assertRaises(ValueError):migrate(p,m,bad,4_000_000_000_000)
        bad=dict(m,regions=m['regions'].copy());bad['regions'][0]=3
        with self.assertRaises(ValueError):migrate(p,m,bad,4_000_000_000_000)
        v=m['vertices'].copy();free=(abs(v[:,0])>.001)&(abs(v[:,0])<.119);v[free,2]+=.001
        q,_=migrate(p,m,mesh_data(v,m['faces'],m['regions']),4_000_000_000_000)
        np.testing.assert_allclose(q['points'][[0,-1],[0,1]],p['points'][[0,-1],[0,1]],atol=1e-13)

    def test_original_occluder_owner_plane_and_zero_S(self):
        m,p,style,_=fixture('curve')
        fg=np.array([[-.035,-.1,3.5],[.035,-.1,3.5],[.035,.1,3.5],[-.035,.1,3.5]])
        nv=len(m['vertices']);both=mesh_data(np.vstack([m['vertices'],fg]),np.vstack([m['faces'],np.array([[0,1,2],[0,2,3]])+nv]),np.full(len(m['faces'])+2,4))
        vertices=both['vertices'].copy();vertices[:nv,2]+=.001
        moved=mesh_data(vertices,both['faces'],both['regions']);q,_=migrate(p,both,moved,4_000_000_000_000)
        cam=dict(extrinsic=np.eye(4).tolist(),width=96,height=96,fx=500.,fy=500.,cx=47.5,cy=47.5)
        r=_coverage(moved,{4:q},{'4':style},cam,2,occluder=both);ink=r['coverage'][4][0]
        self.assertEqual(int(ink[80:112,90:102].sum()),0);self.assertGreater(int(ink.sum()),0)
        alpha=ink.reshape(96,2,96,2).mean((1,3));paper=np.full((96,96,3),.95)
        im,_=compose(paper,alpha,np.zeros_like(alpha),True);np.testing.assert_array_equal(im,paper)
        # A displaced owner beyond the fixed tolerance must not use the old face plane.
        vertices[:nv,2]+=.02;far=mesh_data(vertices,both['faces'],both['regions']);qq,_=migrate(p,both,far,4_000_000_000_000)
        rr=_coverage(far,{4:qq},{'4':style},cam,2,occluder=both)
        self.assertEqual(int(rr['coverage'][4][0].sum()),0)

if __name__=='__main__':unittest.main(verbosity=2)
