import runtime
import unittest
from pathlib import Path
import numpy as np
from geometry import mesh_data
from structure import project_curve,validate_curve,raster_structure,combine_structure

def camera():
    return dict(extrinsic=np.eye(4).tolist(),width=64,height=64,fx=32.,fy=32.,cx=31.5,cy=31.5,view='test')
def plane(z=2.):
    return mesh_data(np.array([[-1,-1,z],[1,-1,z],[1,1,z],[-1,1,z]],float),np.array([[0,1,2],[0,2,3]]),np.array([1,1]))

class StructureTests(unittest.TestCase):
    def test_triangle_split_and_gap(self):
        m=plane();p,report=project_curve(m,camera(),[[20,25],[44,37]],9123)
        validate_curve(m,p)
        self.assertEqual(set(p['face']),{0,1})
        np.testing.assert_allclose(p['points'][:,:,2],2.,atol=1e-12)
        self.assertAlmostEqual(report['unsupported_screen_length'],0.,places=8)
        self.assertLess(report['max_endpoint_gap_world'],1e-10)
        # No face exists in the middle: preserve the missing interval, no bridge.
        v=np.array([[-1,-1,2],[-.3,-1,2],[-.3,1,2],[-1,1,2],[.3,-1,2],[1,-1,2],[1,1,2],[.3,1,2]])
        m=mesh_data(v,np.array([[0,1,2],[0,2,3],[4,5,6],[4,6,7]]),np.ones(4,int))
        p,r=project_curve(m,camera(),[[18,31.5],[45,31.5]],9124)
        validate_curve(m,p);self.assertGreater(r['unsupported_screen_length'],9.)
        self.assertTrue(all((x[:,0]<=-.3+1e-9).all() or (x[:,0]>=.3-1e-9).all() for x in p['points']))

    def test_frontmost_and_occlusion(self):
        m=plane();p,r=project_curve(m,camera(),[[22,31.5],[42,31.5]],9125)
        visible,d=raster_structure(m,p,camera());self.assertGreater(visible.sum(),0)
        # Put a separate foreground surface in front of an already saved curve.
        f=plane(1.5)
        merged=mesh_data(np.concatenate([m['vertices'],f['vertices']]),np.concatenate([m['faces'],f['faces']+4]),np.ones(4,int))
        hidden,d=raster_structure(merged,p,camera());self.assertEqual(hidden.sum(),0)
        # Authoring must also choose first hit, not the more distant surface.
        q,r=project_curve(merged,camera(),[[22,31.5],[42,31.5]],9126)
        np.testing.assert_allclose(q['points'][:,:,2],1.5,atol=1e-12)
        broken={**p,'bary':p['bary'].copy()};broken['bary'][0,0]=[-1,1,1]
        with self.assertRaises(ValueError):validate_curve(m,broken)

    def test_switch_composition(self):
        paper=np.ones((2,2,3),np.float32)*.95
        base=np.array([[0,.2,0,0],[0,0,0,0],[0,0,.7,0],[0,0,0,0]],np.float32)
        structure=np.ones((4,4),np.float32)*.85
        low=lambda a:a.reshape(2,2,2,2).mean((1,3))
        off=combine_structure(paper,base,structure,False)
        np.testing.assert_array_equal(off['combined_ink'],low(base))
        on=combine_structure(paper,base,structure,True)
        np.testing.assert_array_equal(on['combined_ink'],low(np.maximum(base,structure)))
        np.testing.assert_array_equal(off['structure'],np.zeros((2,2)))
        self.assertTrue((on['hybrid']<=off['hybrid']).all())

if __name__=='__main__':unittest.main()
