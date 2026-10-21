"""Necessary regeneration/attachment/isolation contracts on the actual lamp."""
from common import *
from stem_style import STYLE, regenerate_stem
import unittest

class StemTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mesh, _, cls.cfg = load_inputs()
        cls.old = load_strokes(OUT.parent/'unit_003/inputs/selected.npz')

    def test_axial_extent_attachment_and_nonempty(self):
        new, _ = regenerate_stem(self.mesh, self.old, self.cfg)
        stem = [s for s in new if s['part']==2]
        self.assertEqual(len(stem), 8)
        for s in stem:
            points = core.anchor_points(self.mesh, s)
            self.assertTrue(np.all(self.mesh['parts'][s['faces']]==2))
            self.assertGreaterEqual(s['bary'].min(), -1e-12)
            np.testing.assert_allclose(s['bary'].sum(axis=1), 1., atol=1e-12)
            np.testing.assert_allclose([points[:,1].min(),points[:,1].max()], [.2,1.55], atol=1e-10)
            np.testing.assert_allclose(np.ptp(points[:,[0,2]],axis=0), 0., atol=1e-10)
            self.assertAlmostEqual(np.linalg.norm(np.diff(points,axis=0),axis=1).sum(),1.35,places=10)

    def test_deterministic_replacement_and_non_target_identity(self):
        a, _ = regenerate_stem(self.mesh,self.old,self.cfg)
        b, _ = regenerate_stem(self.mesh,self.old[::-1],self.cfg)
        c, _ = regenerate_stem(self.mesh,a,self.cfg)
        self.assertEqual(core.stroke_digest(a),core.stroke_digest(b))
        self.assertEqual(core.stroke_digest(a),core.stroke_digest(c))
        other=lambda v:[s for s in v if s['part']!=2]
        self.assertEqual(core.stroke_digest(other(a)),core.stroke_digest(other(self.old)))
        self.assertEqual(len(other(a)),410)
        self.assertTrue(set(s['id'] for s in a if s['part']==2).isdisjoint(s['id'] for s in self.old))

    def test_out_of_scope_style_rejected(self):
        for key,value in [('count',0),('y_min',-.1),('sector_fraction',1.)]:
            style=dict(STYLE);style[key]=value
            with self.assertRaises(ValueError):regenerate_stem(self.mesh,self.old,self.cfg,style)

if __name__=='__main__':unittest.main(verbosity=2)
