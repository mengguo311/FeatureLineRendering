import unittest
import numpy as np
from line_core import optimize
from test_line_core import cam
class ImageBoundaryTests(unittest.TestCase):
    def test_finite_analytic_plane_has_no_frame_contour(self):
        u=np.indices((96,128))[1]
        # Exactly planar in perspective. No true line anywhere in the image.
        z=1/(.4+.003*u)
        r=optimize(z,np.ones_like(z),cam())
        self.assertFalse(r['lines'].any(),'Gaussian border extension must not be interpreted as geometry')
