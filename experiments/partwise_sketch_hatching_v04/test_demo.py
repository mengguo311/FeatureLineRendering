import runtime
import unittest
import numpy as np
import geometry
from hatching import generate_region, validate_style

class DepthQualification(unittest.TestCase):
    def test_rejects_uncertain_and_jump_depths(self):
        z = np.full((11, 11), 3.)
        a = np.ones_like(z)
        center = z.copy()
        a[2, 2] = .4
        z[5, 5] = 4.
        z[8, 8] = np.nan
        good = geometry.depth_valid(z, a, center)
        self.assertFalse(good[2, 2], 'low-opacity depth must not become geometry')
        self.assertFalse(good[5, 5], 'depth jump must not bridge surfaces')
        self.assertFalse(good[8, 8])
        self.assertTrue(good[2, 8])

class CoordinatesAndPaths(unittest.TestCase):
    def test_nontrivial_camera_roundtrip(self):
        c=geometry.orbit_camera(37,25,4.6)
        points=np.array([[.3,.2,-.4],[-.2,.1,.6],[.1,-.5,.2]])
        uv,z=geometry.project(points,c)
        np.testing.assert_allclose(geometry.backproject(uv,z,c),points,atol=1e-12)

    def test_resize_keeps_pixel_centers(self):
        c=geometry.orbit_camera();d=geometry.resize_camera(c,1024)
        p=np.array([[.3,.2,-.4]])
        u,_=geometry.project(p,c);v,_=geometry.project(p,d)
        np.testing.assert_allclose(v,(u+.5)*2-.5)

    def test_fixed_anchors_and_length(self):
        vertices=np.array([[-.5,0,.3],[.5,0,.3],[.5,0,.9],[-.5,0,.9]])
        mesh=geometry.mesh_data(vertices,np.array([[0,1,2],[0,2,3]]))
        style=dict(angle=20.,spacing=.07,length=.22,width=1.)
        a,_=generate_region(mesh,3,style);b,_=generate_region(mesh,3,style)
        self.assertGreater(len(a['points']),5)
        for k in a:np.testing.assert_array_equal(a[k],b[k])
        np.testing.assert_allclose(a['points'],np.einsum('nij,njk->nik',a['bary'],mesh['tri'][a['face']]),atol=1e-12)
        self.assertTrue((a['bary']>=-1e-12).all())
        for id in np.unique(a['stroke_id']):
            points=a['points'][a['stroke_id']==id]
            self.assertLessEqual(np.linalg.norm(points[:,1]-points[:,0],axis=1).sum(),.22000001)

    def test_style_bounds(self):
        for bad in [dict(angle=0,spacing=0,length=.1,width=1),dict(angle=np.nan,spacing=.1,length=.1,width=1)]:
            with self.assertRaises(ValueError):validate_style(bad)

    def test_real_ray_occlusion(self):
        from render import render
        v=np.array([[-1,-1,2],[1,-1,2],[1,1,2],[-1,1,2],[-1,-1,3],[1,-1,3],[1,1,3],[-1,1,3]],float)
        m=geometry.mesh_data(v,np.array([[0,1,2],[0,2,3],[4,5,6],[4,6,7]]))
        m['regions']=np.array([1,1,2,2])
        c=dict(extrinsic=np.eye(4).tolist(),width=64,height=64,fx=60.,fy=60.,cx=31.5,cy=31.5)
        styles={str(i):dict(angle=0,spacing=.1,length=.2,width=2) for i in [1,2]}
        s={1:dict(points=np.array([[[-.3,0,2],[.3,0,2]]]),face=np.array([0])),
           2:dict(points=np.array([[[-.3,0,3],[.3,0,3]]]),face=np.array([2]))}
        r=render(m,s,styles,c)
        self.assertGreater(r['layers'][1].sum(),5)
        self.assertEqual(r['layers'][2].sum(),0)

    def test_missing_asset_is_error(self):
        from demo import load_asset
        with self.assertRaises(FileNotFoundError):load_asset('/nonexistent_demo_asset')

if __name__ == '__main__':
    unittest.main(verbosity=2)
