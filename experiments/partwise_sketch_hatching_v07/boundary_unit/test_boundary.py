import runtime
import unittest
import numpy as np
from geometry import mesh_data
from hatching import generate_layers
from boundary import paired_gaps
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

def length(p):return float(np.linalg.norm(p['points'][:,1]-p['points'][:,0],axis=1).sum())

class BoundaryTests(unittest.TestCase):
    def test_flat_empty_edges_and_short_path_remain_exact(self):
        _,p,_,_=fixture();b,c,r=paired_gaps(p,np.empty((0,2),int))
        for key in p:
            np.testing.assert_array_equal(p[key],b[key]);np.testing.assert_array_equal(p[key],c[key])
        self.assertFalse(r[0]['eligible']);self.assertEqual(r[0]['reason'],'no_excluded_crossing')
        short={k:v[:2] for k,v in p.items()};_,_,rr=paired_gaps(short,np.array([[short['face'][0],short['face'][1]]]))
        self.assertFalse(rr[0]['eligible'])

    def test_flat_fold_curve_equal_cuts_anchors_and_subsets(self):
        for shape in ('flat','fold','curve'):
            m,p,_,edges=fixture(shape);b,c,records=paired_gaps(p,edges)
            r=records[0];self.assertTrue(r['eligible']);self.assertAlmostEqual(length(p)-length(b),.035,12)
            self.assertAlmostEqual(length(b),length(c),12)
            self.assertEqual(len(np.unique(b['stroke_id'])),2);self.assertEqual(len(np.unique(c['stroke_id'])),2)
            self.assertGreaterEqual(r['C_interval'][0]-r['B_interval'][1],-1e-12) if r['C_interval'][0]>=r['B_interval'][0] else self.assertLessEqual(r['C_interval'][1],r['B_interval'][0]+1e-12)
            for arm,out in [('B',b),('C',c)]:
                np.testing.assert_allclose(out['points'],np.einsum('nij,njk->nik',out['bary'],m['tri'][out['face']]),atol=1e-12)
                for sid in np.unique(out['stroke_id']):
                    q=out['points'][out['stroke_id']==sid];np.testing.assert_allclose(q[:-1,1],q[1:,0],atol=1e-12)
                np.testing.assert_array_equal(out['points'][0,0],p['points'][0,0]);np.testing.assert_array_equal(out['points'][-1,1],p['points'][-1,1])
                self.assertTrue(set(out['face'])<=set(p['face']))
            b2,c2,r2=paired_gaps(p,edges)
            self.assertEqual(records,r2)
            for key in b:np.testing.assert_array_equal(b[key],b2[key]);np.testing.assert_array_equal(c[key],c2[key])

    def test_real_occluder_and_zero_S(self):
        m,p,style,edges=fixture('fold');b,c,_=paired_gaps(p,edges)
        # Separate foreground with the SAME region label; it must still occlude.
        fg=np.array([[-.035,-.1,3.5],[.035,-.1,3.5],[.035,.1,3.5],[-.035,.1,3.5]])
        nv=len(m['vertices']);both=mesh_data(np.vstack([m['vertices'],fg]),np.vstack([m['faces'],np.array([[0,1,2],[0,2,3]])+nv]),np.full(len(m['faces'])+2,4))
        cam=dict(extrinsic=np.eye(4).tolist(),width=96,height=96,fx=500.,fy=500.,cx=47.5,cy=47.5)
        for paths in (p,b,c):
            self.assertTrue((paths['face']<len(m['faces'])).all())
            raster=_coverage(both,{4:paths},{'4':style},cam,2);ink=raster['coverage'][4][0]
            self.assertEqual(int(ink[80:112,90:102].sum()),0);self.assertGreater(int(ink.sum()),0)
            alpha=ink.reshape(96,2,96,2).mean((1,3));paper=np.full((96,96,3),.95)
            im,_=compose(paper,alpha,np.zeros_like(alpha),True);np.testing.assert_array_equal(im,paper)

if __name__=='__main__':unittest.main(verbosity=2)
