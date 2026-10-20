"""Development checks separate from frozen acceptance; point mask is RED control."""
import round011_common
import sys
import unittest
import numpy as np
import area_coverage as candidate
import centered_coverage
import round011_oracle as oracle
RED='--point' in sys.argv
if RED:sys.argv.remove('--point')
def cov(p,size=32):
    return centered_coverage.ribbon_mask(p,size).astype(float) if RED else candidate.ribbon_area(p,size)
class AreaTests(unittest.TestCase):
    def test_axial_exact_fraction(self):
        expected=np.zeros((32,32));expected[15:18,10:23]=np.array([.5,1.,.5])[:,None]*np.array([.5]+[1.]*11+[.5])[None,:]
        np.testing.assert_array_equal(cov([[10.,16.],[22.,16.]]),expected)
    def test_vertical_exact_mass(self):
        self.assertAlmostEqual(float(cov([[16.25,7.25],[16.25,24.25]]).sum()),34.,places=10)
    def test_oblique_integral(self):
        p=[[6.25,8.75],[24.75,20.25]];expected,raw=oracle.area_reference(p,32)
        np.testing.assert_allclose(cov(p),expected,atol=1e-10,rtol=0)
        self.assertAlmostEqual(float(raw.sum()),2*np.linalg.norm(np.subtract(p[1],p[0])),places=9)
    def test_order_and_waypoint(self):
        p=[[6.25,8.75],[15.5,14.5],[24.75,20.25]]
        np.testing.assert_array_equal(cov(p),cov(p[::-1]));np.testing.assert_array_equal(cov(p),cov([p[0],p[-1]]))
    def test_full_pixel_and_zero_contact(self):
        a=cov([[10.5,16.5],[22.5,16.5]])
        self.assertEqual(a[16,12],1.);self.assertEqual(a[15,12],0.);self.assertEqual(a[:,10].sum(),0.)
    def test_invalid_geometry(self):
        for p in ([[1.,1.],[1.,1.]],[[1.,1.],[2.,3.],[3.,1.]],[[1.,1.],[3.,1.],[2.,1.]],[[1.,1.],[np.nan,2.]]):
            with self.assertRaises(ValueError):candidate.ribbon_area(p,32)
        with self.assertRaises(ValueError):candidate.ribbon_area([[1.,1.],[2.,2.]],32,0.)
if __name__=='__main__':unittest.main(verbosity=2)
