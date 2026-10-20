"""Known analytic controls, metric sensitivity, and inherited stencil tests; no lamp."""
import round005_common
import argparse
import unittest
import numpy as np
P = argparse.ArgumentParser(); P.add_argument('--backend', choices=['broken','new'], default='new')
ARGS = P.parse_args()
if ARGS.backend == 'new':
    import coverage_fixture as f
else:
    class Broken:
        # Intentional wrong diagnostic oracle, NOT a modified renderer.
        @staticmethod
        def plane_depth(uv, plane, camera): return np.ones(len(uv))
        @staticmethod
        def first_hit(uv, planes, camera): return np.ones(len(uv)), np.ones(len(uv),dtype=int)
        @staticmethod
        def ribbon_coverage(uv, ends, width): return np.ones(len(uv),dtype=bool)
        @staticmethod
        def aa_centers(size, scale): return np.arange(size)*scale
    f = Broken()

def cam():
    return {'size':128,'focal':128.,'center':np.array([64.,64.]),'R':np.eye(3),'t':np.zeros(3),'eye':np.zeros(3)}

def plane(z=3., sx=0., bounds=(8.,8.,120.,120.), pid=1):
    return {'z0':z,'sx':sx,'sy':0.,'bounds':list(bounds),'id':pid}

class OracleTests(unittest.TestCase):
    def test_known_slanted_depth(self):
        actual = f.plane_depth(np.array([[64.,64.],[80.,64.],[48.,64.]]),plane(sx=1.5),cam())
        np.testing.assert_allclose(actual,[3.,48./13.,48./19.],atol=1e-12,rtol=0)

    def test_finite_patch_no_extrapolation(self):
        z=f.plane_depth(np.array([[0.,64.],[64.,64.],[128.,64.]]),plane(),cam())
        self.assertTrue(np.isinf(z[0]) and np.isinf(z[2])); self.assertEqual(z[1],3.)

    def test_front_rear_order_and_uncovered(self):
        back=plane(); front=plane(2.,bounds=(32.,48.,96.,80.),pid=2)
        uv=np.array([[64.,64.],[64.,40.],[1.,1.]])
        z,p=f.first_hit(uv,[back,front],cam()); z2,p2=f.first_hit(uv,[front,back],cam())
        np.testing.assert_array_equal(p,[2,1,0]);np.testing.assert_array_equal(p,p2)
        np.testing.assert_array_equal(z,z2);np.testing.assert_allclose(z[:2],[2,3]); self.assertTrue(np.isinf(z[2]))

    def test_finite_width_butt_caps(self):
        ends=np.array([[64.25,24.25],[64.25,104.25]])
        uv=np.array([[64.,30.],[65.,30.],[63.,30.],[64.,24.],[64.,105.],[63.25,24.25]])
        np.testing.assert_array_equal(f.ribbon_coverage(uv,ends,2.),[True,True,False,False,False,True])

    def test_resize_sample_center_phase(self):
        np.testing.assert_array_equal(f.aa_centers(4,2),[.5,2.5,4.5,6.5])

    @unittest.skipIf(ARGS.backend=='broken','Requires real diagnostic implementation')
    def test_even_stencil_is_asymmetric(self):
        from scipy.ndimage import maximum_filter
        a=np.zeros((8,8));a[3,3]=.8
        yy,xx=np.nonzero(maximum_filter(a,size=2))
        self.assertEqual(set(zip(xx,yy)),{(3,3),(4,3),(3,4),(4,4)})

    @unittest.skipIf(ARGS.backend=='broken','Requires real diagnostic implementation')
    def test_plane_raster_and_ray_agree(self):
        import core
        import stage_attribution as sa
        planes=[plane(sx=1.5),plane(2.,bounds=(32.,48.,96.,80.),pid=2)]
        mesh=f.make_mesh(planes,cam());depth,parts=core.raster_surface(mesh,cam())
        uv=np.array([[64.,64.],[64.,40.],[80.,40.],[1.,1.]])
        z,p=f.first_hit(uv,planes,cam());tz,tp,_=sa.exact_mesh_rays(mesh,cam(),uv)
        np.testing.assert_allclose(z,tz,atol=1e-9);np.testing.assert_array_equal(p,tp)
        np.testing.assert_allclose(depth[uv[:,1].astype(int),uv[:,0].astype(int)],z,atol=1e-9)
        np.testing.assert_array_equal(parts[uv[:,1].astype(int),uv[:,0].astype(int)],p)

    @unittest.skipIf(ARGS.backend=='broken','Requires real diagnostic implementation')
    def test_point_depth_mismatch_vs_true_occlusion(self):
        import core
        uv=np.array([[64.25,40.],[64.25,64.]])
        rear=plane(sx=1.5);planes=[rear,plane(2.,bounds=(32.,48.,96.,80.),pid=2)]
        x=f.points_on_plane(uv,rear,cam());depth,parts=core.raster_surface(f.make_mesh(planes,cam()),cam())
        actual=core.visible_points(x,cam(),depth,.006)
        np.testing.assert_array_equal(actual,[False,False])
        _,owner=f.first_hit(np.rint(uv),planes,cam())
        np.testing.assert_array_equal(owner,[1,2])
        # First rejection has visible owning surface at rounded sample; second is genuinely hidden.
        self.assertGreater(x[0,2]-depth[40,64],.006)

    @unittest.skipIf(ARGS.backend=='broken','Requires real diagnostic implementation')
    def test_metric_response_to_missing_and_rear_ink(self):
        visible=np.array([[1,1,0,0]],bool);hidden=np.array([[0,0,1,1]],bool)
        good=np.array([[.8,.8,0,0]]);bad=np.array([[.8,0,.8,0]])
        a=f.coverage_counts(good,visible,hidden);b=f.coverage_counts(bad,visible,hidden)
        self.assertEqual(a['visible_retained_fraction'],1.);self.assertEqual(a['hidden_ink_sites'],0)
        self.assertEqual(b['visible_retained_fraction'],.5);self.assertEqual(b['visible_missing_sites'],1)
        self.assertEqual(b['hidden_ink_sites'],1)

if __name__=='__main__': unittest.main(argv=['test_coverage_fixture'],verbosity=2)
