"""Projection sanity checks independent of the evaluated fixture/output."""
import round016_common
import sys,unittest
import numpy as np
from planar_axial_reference import project_prescribed
if '--broken' in sys.argv:
    sys.argv.remove('--broken')
    good=project_prescribed
    def project_prescribed(p,d,e):
        good(p,d,e)
        return np.asarray(p,float) # intentionally ignores axial translation
class AxialProjection(unittest.TestCase):
    def test_identity(self):
        p=np.array([[49.,94.],[64.,64.]])
        np.testing.assert_array_equal(project_prescribed(p,4.,0.),p)
    def test_owner_approach(self):
        np.testing.assert_allclose(project_prescribed([[49.,94.]],4.,.25),[[48.,96.]],rtol=0,atol=1e-13)
    def test_owner_retreat(self):
        np.testing.assert_allclose(project_prescribed([[47.,98.]],4.,-.25),[[48.,96.]],rtol=0,atol=1e-13)
    def test_foreground_distinct_depth(self):
        np.testing.assert_allclose(project_prescribed([[53.,86.]],3.,.25),[[52.,88.]],rtol=0,atol=1e-13)
        self.assertGreater(abs(project_prescribed([[53.,86.]],3.,.25)-project_prescribed([[53.,86.]],4.,.25)).max(),.1)
    def test_optical_axis_and_input_immutable(self):
        p=np.array([[64.,64.],[49.,94.]]);before=p.copy()
        q=project_prescribed(p,4.,.25)
        np.testing.assert_array_equal(q[0],[64.,64.]);np.testing.assert_array_equal(p,before)
    def test_bad_depth_rejected(self):
        for depth,eye in [(0.,0.),(3.,3.),(3.,4.)]:
            with self.assertRaises(ValueError):project_prescribed([[64.,64.]],depth,eye)
if __name__=='__main__':unittest.main(verbosity=2)
