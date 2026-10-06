import unittest
import numpy as np
import core

class Contracts(unittest.TestCase):
    def test_projection_actual_convention(self):
        camera=dict(width=800,height=800,FoVx=2*np.arctan(.4),FoVy=2*np.arctan(.4),w2c=np.eye(4).tolist())
        uv,z=core.project(np.array([[0,0,2],[.2,-.4,2],[0,0,-1.]]),camera)
        np.testing.assert_allclose(uv[:2],[[399.5,399.5],[499.5,199.5]],atol=1e-9)
        self.assertLess(z[-1],0)
        camera['w2c'][0][3]=1
        uv,_=core.project(np.array([[0.,0,2]]),camera)
        self.assertAlmostEqual(uv[0,0],899.5,places=10)
    def test_id_union_exact_rows(self):
        model=np.arange(30,dtype=np.float32).reshape(10,3)
        ids,xyz,mask=core.selected_rows(model,[np.array([7,2,3]),np.array([3,1,7])])
        np.testing.assert_array_equal(ids,[1,2,3,7])
        np.testing.assert_array_equal(xyz,model[ids])
        np.testing.assert_array_equal(mask,[2,1,3,3])
        self.assertEqual(xyz.dtype,np.float32)
        with self.assertRaises(ValueError):core.selected_rows(model,[np.array([-1]),np.array([0])])
    def test_line_degree_mutual_locality(self):
        xyz=np.column_stack([np.arange(30),np.zeros((30,2))]).astype(np.float32)
        ids=np.arange(30)*13+5
        g=core.build_graph(xyz,ids)
        self.assertEqual(len(g['B']),29)
        self.assertTrue(np.all(np.bincount(g['B'].ravel(),minlength=30)<=2))
        self.assertTrue(np.all(np.diff(g['B'],axis=1)==1))
        np.testing.assert_array_equal(g['xyz'],xyz)
        self.assertTrue(np.all(g['linearity']>.99))
    def test_rigid_and_scale_invariance(self):
        xyz=np.column_stack([np.arange(24),np.zeros((24,2))]).astype(np.float32)
        ids=np.arange(24)
        rotation=np.array([[0,1,0],[0,0,1],[1,0,0]])
        g=core.build_graph(xyz,ids);h=core.build_graph(xyz@rotation*7+np.array([2,4,6]),ids)
        for arm in ['A','B']:np.testing.assert_array_equal(g[arm],h[arm])
        self.assertAlmostEqual(h['radius']/g['radius'],7)
    def test_no_forced_bridge_and_empty(self):
        xyz=np.column_stack([np.r_[np.arange(16),100+np.arange(16)],np.zeros((32,2))])
        g=core.build_graph(xyz,np.arange(32))
        for arm in ['A','B']:
            self.assertTrue(np.all(np.linalg.norm(xyz[g[arm][:,0]]-xyz[g[arm][:,1]],axis=1)<=3))
        tetra=np.array([[1,1,1],[1,-1,-1],[-1,1,-1],[-1,-1,1]],dtype=np.float32)
        self.assertEqual(len(core.build_graph(tetra,np.arange(4))['B']),0)
        v,f,b=core.mesh_and_glb(tetra,np.empty((0,2),int),.01)
        vv,ff,d=core.parse_glb(b)
        self.assertEqual(len(vv),0);self.assertEqual(len(ff),0)
        self.assertNotIn('animations',d)
    def test_glb_independent_read_and_tube_endpoints(self):
        xyz=np.array([[0,0,0],[1,0,0],[1,1,0]],dtype=np.float32)
        edges=np.array([[0,1],[1,2]])
        v,f,b=core.mesh_and_glb(xyz,edges,.02)
        vv,ff,d=core.parse_glb(b)
        np.testing.assert_array_equal(vv,v);np.testing.assert_array_equal(ff,f)
        for q,(a,c) in enumerate(edges):
            np.testing.assert_allclose(v[q*16:q*16+8].mean(0),xyz[a],atol=2e-7)
            np.testing.assert_allclose(v[q*16+8:q*16+16].mean(0),xyz[c],atol=2e-7)
        self.assertNotIn('animations',d)
        self.assertTrue(all('matrix' not in n and 'translation' not in n for n in d['nodes']))
        with self.assertRaises(ValueError):core.parse_glb(b[:-4])
    def test_tie_duplicate_and_rejection_audit(self):
        xyz=np.array([[0,0,0],[0,0,0],[1,0,0],[2,0,0],[3,0,0]],np.float32)
        g=core.build_graph(xyz,np.array([2,7,11,13,19]))
        self.assertTrue(np.isfinite(g['tangent']).all())
        self.assertEqual(len(g['candidate_pairs']),len(g['reason_B']))
        self.assertTrue(np.all(g['distance'][g['reason_B']==0]>0))
        h=core.build_graph(xyz,np.array([2,7,11,13,19]))
        for arm in ['A','B']:np.testing.assert_array_equal(g[arm],h[arm])

if __name__=='__main__':unittest.main(verbosity=2)
