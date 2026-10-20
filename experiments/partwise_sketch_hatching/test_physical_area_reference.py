"""Independent area/control tests; --center-gated retains old approximation RED."""
import round012_common
import sys,unittest
import numpy as np
import physical_area_reference as ref
CENTER='--center-gated' in sys.argv
if CENTER:sys.argv.remove('--center-gated')

def visible(path,size,width,owner,extra=None):
    clean,raw,_=ref.reference(path,size,width,owner,4,extra)
    if not CENTER:return clean['visible']
    yy,xx=np.mgrid[:size,:size];x0,y0,x1,y1=owner
    gate=(xx>=x0)&(xx<=x1)&(yy>=y0)&(yy<=y1)
    if extra is not None and extra['z']<4:
        x0,y0,x1,y1=extra['bounds_high_xyxy'];gate&=~((xx>=x0)&(xx<=x1)&(yy>=y0)&(yy<=y1))
    return clean['ribbon']*gate

class ReferenceTests(unittest.TestCase):
    def test_axial_owner_half_area(self):
        a=visible([[2.,4.],[6.,4.]],10,2.,[0,4,9,9])
        self.assertAlmostEqual(float(a.sum()),4.)
        self.assertAlmostEqual(a[4,4],.5)
    def test_axial_occluder_half_pixels(self):
        a=visible([[2.,4.],[6.,4.]],10,2.,[0,0,9,9],{'z':3,'bounds_high_xyxy':[4,0,5,9]})
        self.assertAlmostEqual(float(a.sum()),6.)
        self.assertAlmostEqual(a[4,4],.5)
    def test_diagonal_diamond_known_area(self):
        p=[[2.,2.],[6.,6.]];w=np.sqrt(2.)
        a=ref.area_map(p,10,w)
        self.assertAlmostEqual(float(a.sum()),8.)
        half=ref.area_map(p,10,w,[0,0,4,10]);self.assertAlmostEqual(float(half.sum()),4.)
    def test_axis_cross_section_agrees_with_interval(self):
        for p in [[[2.,3.],[7.,3.]],[[3.,2.],[3.,7.]]]:
            a=ref.area_map(p,11,2.,[2.3,2.7,6.4,6.8]);b=ref.area_map(p,11,2.,[2.3,2.7,6.4,6.8],True)
            np.testing.assert_allclose(a,b,atol=1e-12,rtol=0)
    def test_reversal_and_transpose(self):
        p=np.array([[2.2,3.1],[7.2,6.1]]);a=ref.area_map(p,12,1.7,[1,1,6,9])
        np.testing.assert_allclose(a,ref.area_map(p[::-1],12,1.7,[1,1,6,9]),atol=1e-12,rtol=0)
        np.testing.assert_allclose(a.T,ref.area_map(p[:,::-1],12,1.7,[1,1,9,6]),atol=1e-12,rtol=0)
    def test_partition_and_strict_depth(self):
        p=[[2.,4.],[6.,4.]];owner=[0,4,9,9]
        for depth,expected in [(3,2.),(4,4.),(5,4.)]:
            a,raw,g=ref.reference(p,10,2.,owner,4,{'z':depth,'bounds_high_xyxy':[4,0,6,9]})
            np.testing.assert_allclose(raw['ribbon'],raw['visible']+raw['unsupported']+raw['occluded'],atol=1e-12,rtol=0)
            self.assertAlmostEqual(a['visible'].sum(),expected)
            for k in raw:self.assertAlmostEqual(float(raw[k].sum()),g[k])
    def test_disjoint_samepart_foreground(self):
        a,_,_=ref.reference([[2.,4.],[6.,4.]],10,2.,[0,4,9,9],4,{'z':3,'bounds_high_xyxy':[0,1,9,3],'part_id':1})
        self.assertEqual(a['occluded'].sum(),0);self.assertEqual(a['visible'].sum(),4)
    def test_empty_and_subsets(self):
        a,_,_=ref.reference([[2.,4.],[6.,4.]],10,2.,[0,4,9,9],4)
        masks=ref.subsets(a);names=['physical_boundary','visible_interior','hidden_interior','unsupported_interior','outside_ribbon']
        np.testing.assert_array_equal(sum(masks[n].astype(int) for n in names),np.ones((10,10),int))
        self.assertTrue(masks['physical_boundary'].any());self.assertTrue(masks['unsupported_interior'].any())
        self.assertEqual(ref.area_map([[2.,4.],[6.,4.]],10,2.,[8,8,9,9]).sum(),0)

if __name__=='__main__':unittest.main()
