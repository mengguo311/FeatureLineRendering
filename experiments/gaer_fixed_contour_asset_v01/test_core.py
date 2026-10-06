import unittest
import numpy as np
import core

class CoreTests(unittest.TestCase):
    def test_camera_rays_return_world_points(self):
        p=core.ray_points(np.array([[0.,0.],[1.,0.]]), np.array([2.,3.]), np.eye(3),np.eye(4))
        np.testing.assert_allclose(p, [[0.,0.,2.],[3.,0.,3.]],atol=1e-12)

    def test_tubes_have_fixed_geometry_not_camera_state(self):
        c=np.array([[0.,0.,0.],[0.,0.,1.],[0.,0.,2.]])
        v,f=core.tube_mesh([c],.02)
        self.assertGreater(len(v),0)
        self.assertGreater(len(f),0)
        self.assertTrue(np.isfinite(v).all())
        self.assertLess(int(f.max()),len(v))
        v2,f2=core.tube_mesh([c],.02)
        np.testing.assert_array_equal(v,v2)
        np.testing.assert_array_equal(f,f2)

    def test_glb_contains_static_mesh(self):
        import struct,json
        v,f=core.tube_mesh([np.array([[0.,0.,0.],[0.,0.,1.]])],.02)
        b=core.glb_bytes(v,f)
        self.assertEqual(b[:4],b"glTF")
        magic,version,length=struct.unpack("<III",b[:12])
        self.assertEqual(version,2)
        self.assertEqual(length,len(b))
        n,tag=struct.unpack("<II",b[12:20]);doc=json.loads(b[20:20+n])
        self.assertNotIn("animations",doc)
        self.assertEqual(doc["accessors"][0]["count"],len(v))
        self.assertEqual(doc["accessors"][1]["count"],f.size)

    def test_depth_uses_actual_contribution_and_style_support(self):
        d=core.supported_depth(np.array([[2.,4.],[2.,4.]]),np.array([[.75,.25],[.75,.25]]),np.array([[0.,1.],[0.,0.]]))
        np.testing.assert_allclose(d,[4.,2.5])

if __name__=="__main__":unittest.main()
