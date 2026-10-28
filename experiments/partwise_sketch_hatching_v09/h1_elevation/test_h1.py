import runtime
import unittest
import numpy as np
from screen_hatch import integrate, raster, generate
from temporal import correspondence, sample

class Tests(unittest.TestCase):
    def data(self):
        d=np.ones((32,32))*3;mask=np.zeros((32,32),bool);mask[2:30,2:30]=True
        field=np.zeros((32,32,2));field[:,:,0]=1
        return d,mask,field
    def test_constant_field_mask_and_gap(self):
        d,m,f=self.data();m[:,16]=False
        p,why=integrate(np.array([8.,10.]),1,40,f,m,d,.25,.035)
        self.assertLess(p[:,0].max(),16);self.assertEqual(why,'mask_boundary')
        ink=raster([p],m,1.,2)
        self.assertFalse(ink[~np.repeat(np.repeat(m,2,0),2,1)].any())
    def test_disjoint_sheet_stop_and_sign(self):
        d,m,f=self.data();d[:,16:]=2;f[:,10:]*=-1
        p,why=integrate(np.array([8.,10.]),1,40,f,m,d,.25,.035)
        self.assertLess(p[:,0].max(),16);self.assertEqual(why,'depth_discontinuity')
        self.assertGreater(p[-1,0],14)
    def test_deterministic_screen_seeds(self):
        d,m,f=self.data();cfg=dict(spacing_px=6.,length_px=12.,gap_px=2.,phase=[.1732050807568877,.3819660112501051],step_px=.5,depth_jump=.035)
        a,ra=generate(f,m,d,[16,16],[1,0],cfg);b,rb=generate(f,m,d,[16,16],[1,0],cfg)
        self.assertEqual(ra,rb);self.assertGreater(len(a),0)
        for x,y in zip(a,b):np.testing.assert_array_equal(x,y)
    def test_correspondence_translation_and_occluder(self):
        c=dict(width=16,height=16,fx=10.,fy=10.,cx=7.5,cy=7.5,extrinsic=np.eye(4).tolist())
        c2=dict(c);e=np.eye(4);e[0,3]=.2;c2['extrinsic']=e.tolist()
        d=np.full((16,16),2.);m=np.ones((16,16),bool)
        uv,ok,diag=correspondence(d,m,c,d,m,c2)
        self.assertTrue(ok[:,:-1].all());self.assertFalse(ok[:,-1].any())
        np.testing.assert_allclose(uv[5,5],[6,5])
        occ=d.copy();occ[:,8]=1
        _,ok2,_=correspondence(d,m,c,occ,m,c2)
        self.assertFalse(ok2[:,7].any())
        a=np.zeros((16,16));a[:,5]=1;b=np.zeros_like(a);b[:,6]=1
        np.testing.assert_allclose(sample(b,uv)[ok],a[ok])

if __name__=='__main__':unittest.main()
