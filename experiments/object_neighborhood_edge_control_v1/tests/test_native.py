import unittest
import numpy as np
from renderer_adapter import audit_native

class NativeTests(unittest.TestCase):
    def test_stock_rgb_occlusion_backward(self):
        r=audit_native()
        self.assertLess(r['rgb_calibration_max_abs'],1e-7)
        self.assertLess(r['compositing_max_abs'],2e-6)
        self.assertLess(r['color_grad_max_abs'],2e-6)
        self.assertLess(r['geometry_grad_relative_error'],.03)
        self.assertEqual(r['hidden_tail_mass'],0)
        self.assertGreater(r['front_mass'],0)
