import runtime
import unittest
import numpy as np
from geometry import mesh_data
from surface_walk import walk, regenerate
from render import _coverage
from hybrid import compose

def square(reverse=False):
    vertices=np.array([[0,0,0],[1,0,0],[1,1,0],[0,1,0]],float)
    faces=np.array([[0,1,2],[0,2,3] if not reverse else [3,2,0]])
    return mesh_data(vertices,faces,np.full(2,4))

class WalkTests(unittest.TestCase):
    def test_flat_shared_edge_and_winding(self):
        for reverse in (False,True):
            mesh=square(reverse)
            result=walk(mesh,0,np.array([.2,.4,.4]),np.array([-1.,0,0]),.6)
            self.assertEqual(result['reason'],'requested_length')
            self.assertEqual(len(set(result['face'])),2)
            np.testing.assert_allclose(result['points'][-1,1],[.2,.4,0],atol=1e-10)
            np.testing.assert_allclose(result['points'][:,:,1],.4,atol=1e-10)
            self.assertAlmostEqual(result['length'],.6)
    def test_curved_cylinder_unfolds_to_straight_line(self):
        angles=np.arange(5)*.3
        vertices=np.array([[np.sin(a),1-np.cos(a),z] for a in angles for z in (0.,1.)])
        faces=np.array([f for i in range(4) for f in ([2*i,2*i+2,2*i+3],[2*i,2*i+3,2*i+1])])
        mesh=mesh_data(vertices,faces,np.full(len(faces),4))
        tangent=vertices[2]-vertices[0]; tangent/=np.linalg.norm(tangent)
        result=walk(mesh,0,np.array([.5,.1,.4]),tangent,.7)
        self.assertEqual(result['reason'],'requested_length')
        np.testing.assert_allclose(result['points'][:,:,2],.4,atol=1e-10)
        chord=2*np.sin(.15); end=result['points'][-1,1]; panel=int(result['face'][-1])//2
        u=vertices[2*panel+2]-vertices[2*panel]
        unfolded=panel*chord+np.dot(end-vertices[2*panel],u)/chord
        self.assertAlmostEqual(unfolded,.5*chord+.7,places=9)
        self.assertAlmostEqual(result['length'],.7)
    def test_authored_boundary_and_disconnected_sheet(self):
        mesh=square(); r=walk(mesh,0,np.array([.2,.4,.4]),np.array([-1.,0,0]),.6,np.array([True,False]))
        self.assertEqual(r['reason'],'authored_region_boundary'); self.assertAlmostEqual(r['length'],.4)
        v=np.vstack([mesh['vertices'],mesh['vertices']+[1.05,0,0]])
        f=np.vstack([mesh['faces'],mesh['faces']+4]); mesh=mesh_data(v,f,np.full(4,4))
        r=walk(mesh,0,np.array([.2,.4,.4]),np.array([1.,0,0]),.6)
        self.assertEqual(r['reason'],'mesh_boundary'); self.assertAlmostEqual(r['length'],.2)
        self.assertLessEqual(int(r['face'].max()),1)
    def test_real_foreground_occluder_and_zero_support(self):
        v=np.array([[-1,-1,4],[1,-1,4],[1,1,4],[-1,1,4],[-.2,-.4,3.4],[.2,-.4,3.4],[.2,.4,3.4],[-.2,.4,3.4]],float)
        f=np.array([[0,1,2],[0,2,3],[4,5,6],[4,6,7]])
        mesh=mesh_data(v,f,np.full(4,4))
        r=walk(mesh,1,np.array([.5,.2,.3]),np.array([1.,0,0]),1.2)
        paths={k:r[k] for k in ('points','bary','face')}
        paths.update(stroke_id=np.ones(len(r['face']),np.int64),layer_id=np.zeros(len(r['face']),np.uint8))
        c=dict(extrinsic=np.eye(4).tolist(),width=96,height=96,fx=120.,fy=120.,cx=47.5,cy=47.5)
        styles={'4':dict(angle=35.,spacing=.06,length=.12,width=1.,cross_enabled=True,ink_strength=.8)}
        cov=_coverage(mesh,{4:paths},styles,c,2)['coverage'][4][0]
        self.assertEqual(int(cov[:,90:102].sum()),0)
        self.assertGreater(int(cov.sum()),0)
        ink=cov.reshape(96,2,96,2).mean((1,3))
        paper=np.full((96,96,3),.95); image,alpha=compose(paper,ink,np.zeros_like(ink),True)
        np.testing.assert_array_equal(image,paper); self.assertEqual(float(alpha.sum()),0.)
    def test_real_seeds_anchors_and_identity(self):
        root=runtime.OUTPUT_ROOT/'replay_package/data/lego'
        with np.load(root/'unit_008_asset/TARGET.npz') as z: mesh=mesh_data(z['vertices'],z['faces'],z['old_face_regions'])
        with np.load(root/'unit_010_asset/LOCAL_OLD_PARTITION.npz') as z: old={k:z[k] for k in z.files}
        use=np.isin(old['stroke_id'],np.unique(old['stroke_id'])[:12]); old={k:v[use].copy() for k,v in old.items()}
        before={k:v.copy() for k,v in old.items()}; new,records=regenerate(mesh,old,mesh['regions']==4)
        self.assertEqual(len(records),12)
        for key in old: np.testing.assert_array_equal(old[key],before[key])
        self.assertFalse(np.isin(new['stroke_id'],old['stroke_id']).any())
        self.assertTrue((mesh['regions'][new['face']]==4).all())
        np.testing.assert_allclose(new['points'],np.einsum('nij,njk->nik',new['bary'],mesh['tri'][new['face']]),atol=1e-10)
        self.assertTrue((new['bary']>=-1e-9).all())
        for rec in records: self.assertLessEqual(rec['actual_length'],rec['requested_length']+1e-9)

if __name__=='__main__': unittest.main(verbosity=2)
