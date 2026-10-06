import unittest
import numpy as np
from contribution import composite, visibility_state

class AlphaTests(unittest.TestCase):
    def test_front_back_no_opacity_twice(self):
        rgb, w, alpha = composite([0.5,0.8], [[1,0,0],[0,0,1]], [0,0,0])
        np.testing.assert_allclose(w, [0.5,0.4])
        np.testing.assert_allclose(rgb, [0.5,0,0.4])
        self.assertAlmostEqual(alpha, 0.9)
    def test_cut_recomputes_transmittance(self):
        _, w, _ = composite([0,0.8], [[1,0,0],[0,0,1]], [0,0,0])
        self.assertAlmostEqual(w[1],0.8)
    def test_hidden_unknown(self):
        self.assertEqual(visibility_state(True,0),'hidden')
        self.assertEqual(visibility_state(False,1),'unknown')

