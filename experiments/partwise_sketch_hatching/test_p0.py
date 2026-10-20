"""P0 algorithm contracts. Run with unittest; no GPU dependencies."""
import json
import unittest
from pathlib import Path
import numpy as np
import core

PROTOCOL = Path(__file__).resolve().parents[2] / "docs/partwise_sketch_hatching/round_001/PROTOCOL.json"


class P0Tests(unittest.TestCase):
    def test_projection_backprojection_optical_depth(self):
        c = core.camera(31, 22, 4.5, 128, 150)
        x = np.array([[.2, .4, -.3], [-.3, 1.2, .2], [.5, 2.1, .1]])
        uv, z = core.project(x, c)
        np.testing.assert_allclose(core.backproject(uv, z, c), x, atol=1e-12)

    def test_ray_distance_is_not_z(self):
        c = core.camera(0, 0, 4.5, 128, 150)
        uv = np.array([[20., 30.], [110., 120.]])
        z = np.array([3., 4.])
        d = np.column_stack(((uv-c["center"])/c["focal"], np.ones(2)))
        t = z*np.linalg.norm(d, axis=1)
        np.testing.assert_allclose(core.backproject(uv,t,c,"ray"), core.backproject(uv,z,c), atol=1e-12)
        self.assertGreater(np.linalg.norm(core.backproject(uv,t,c)-core.backproject(uv,z,c)), .1)

    def test_tangent_degeneracy_fallback(self):
        t = core.tangent(np.array([0.,1.,0.]), np.array([0.,1.,0.]))
        self.assertTrue(np.isfinite(t).all())
        self.assertAlmostEqual(np.linalg.norm(t), 1.)
        self.assertAlmostEqual(t[1], 0.)

    def test_sign_invariant_line_field(self):
        a = np.array([1.,0.,0.])
        result = core.line_mean(np.array([a,-a,a,-a]), np.array([0.,0.,1.]))
        self.assertAlmostEqual(abs(result @ a), 1.)

    def test_mesh_anchor_determinism_and_part_isolation(self):
        cfg=json.loads(PROTOCOL.read_text())
        mesh=core.make_lamp(cfg["asset"])
        counts={"1":8,"2":4,"3":6}
        a=core.generate_strokes(mesh,cfg,"mixed",counts=counts)
        b=core.generate_strokes(mesh,cfg,"mixed",counts=counts)
        self.assertEqual(core.stroke_digest(a),core.stroke_digest(b))
        edited=core.edit_part(mesh,a,cfg,1,35,counts=counts)
        self.assertNotEqual(core.stroke_digest([s for s in a if s["part"]==1]),
                            core.stroke_digest([s for s in edited if s["part"]==1]))
        self.assertEqual(core.stroke_digest([s for s in a if s["part"]!=1]),
                         core.stroke_digest([s for s in edited if s["part"]!=1]))
        crossed=0
        for s in a:
            self.assertTrue(np.all(mesh["parts"][s["faces"]]==s["part"]))
            np.testing.assert_allclose(s["bary"].sum(axis=1),1,atol=1e-12)
            self.assertGreaterEqual(s["bary"].min(),-1e-8)
            self.assertGreater(len(s["faces"]),1)
            crossed+=int(len(np.unique(s["faces"]))>1)
        self.assertGreater(crossed,0)

    def test_analytic_frustum_depth_and_part(self):
        cfg=json.loads(PROTOCOL.read_text())
        c=core.camera(0,0,4.5,128,150)
        depth,parts=core.analytic_reference(cfg["asset"],c)
        # Center ray hits stem front at world y=1.17.
        self.assertEqual(parts[64,64],2)
        self.assertAlmostEqual(depth[64,64],4.425,places=6)

    def test_triangle_depth_occludes_back_layer(self):
        # Orthogonal front and back planes, camera centered at y=1.17.
        c=core.camera(0,0,4.5,64,75)
        v=np.array([[-1,0,0],[1,0,0],[0,2.5,0],
                    [-1,0,-1],[1,0,-1],[0,2.5,-1]],float)
        mesh=core.finalize_mesh(v,np.array([[0,1,2],[3,4,5]]),np.array([1,2]))
        d,p=core.raster_surface(mesh,c)
        self.assertEqual(p[32,32],1)
        self.assertAlmostEqual(d[32,32],4.5,places=6)
        self.assertFalse(core.visible_points(np.array([[0,1.17,-1.]]),c,d,.006)[0])
        self.assertTrue(core.visible_points(np.array([[0,1.17,0.]]),c,d,.006)[0])

    def test_edit_metric_rejects_noop_and_detects_leak(self):
        mask=np.zeros((40,40),bool);mask[5:25,5:25]=True
        parts=mask.astype(np.int32)
        before=np.ones((40,40));after=before.copy();after[10:20,10:20]=0
        m=core.edit_metrics(before,after,parts,1,2)
        self.assertEqual(m["outside_fraction"],0)
        self.assertGreater(m["inside_delta"],0)
        leaked=after.copy();leaked[30:35,30:35]=0
        self.assertGreater(core.edit_metrics(before,leaked,parts,1,2)["outside_fraction"],m["outside_fraction"])
        self.assertFalse(core.edit_metrics(before,before,parts,1,2)["nonzero_edit"])

    def test_actual_raster_drift_response(self):
        ink=np.zeros((40,40),bool);ink[5:35,10]=True
        samples=np.column_stack((np.full(30,10),np.arange(5,35)))
        base=core.support_error(ink,samples)
        drift=core.support_error(np.roll(ink,6,axis=1),samples)
        self.assertEqual(base["p95_px"],0)
        self.assertEqual(drift["p95_px"],6)


if __name__ == "__main__":
    unittest.main(verbosity=2)
