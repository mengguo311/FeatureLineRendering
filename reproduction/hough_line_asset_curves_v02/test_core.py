from runtime import *
import unittest
from core import hough_axis,corner_mask,fidelity,eval_curve
from assetio import update_geometry

class Correctness(unittest.TestCase):
    def test_axial_and_local_support(self):
        x=np.c_[np.linspace(0,5,40),np.zeros((40,2))]; t=np.tile([1.,0,0],(40,1)); piece=np.repeat(np.arange(8),5)
        a=hough_axis(x,t,piece,.2,np.array([1.,0,0])); b=hough_axis(x,-t,piece,.2,np.array([-1.,0,0]))
        self.assertIsNotNone(a['axis']); self.assertEqual(a['support_count'],40)
        self.assertAlmostEqual(abs(a['axis']@b['axis']),1.,12)
        self.assertLessEqual(a['max_mass'],1.+1e-12)
        c=hough_axis(x[:5],t[:5],piece[:5],.2,np.array([1.,0,0])); self.assertIsNone(c['axis'])
    def test_corner_guard(self):
        p=np.array([[0.,0,0],[1,0,0],[2,0,0],[2,1,0],[2,2,0]])
        node,piece=corner_mask(p,False)
        self.assertTrue(node[2]); self.assertTrue(piece[1]); self.assertTrue(piece[2])
    def test_curve_flattening_rejected(self):
        p=np.array([[0.,0,0],[1,1,0],[2,0,0]])
        t=np.linspace(0,1,17); x=np.c_[2*t,1-np.abs(2*t-1),np.zeros(17)]
        oldt=unit(np.c_[np.ones(17),np.where(t<.5,1.,-1.),np.zeros(17)])
        flat=np.array([[0.,0,0],[2/3,0,0],[4/3,0,0],[2.,0,0]])
        ok,reason,_=fidelity(flat,p,t,x,oldt,np.full(17,.2),.2)
        self.assertFalse(ok); self.assertNotEqual(reason,'accepted')
    def test_export_roundtrip_fixed_fields(self):
        fmt,_=renderer_modules(); n=4
        fields=['x','y','z','nx','ny','nz','f_dc_0','f_dc_1','f_dc_2','opacity','scale_0','scale_1','scale_2','rot_0','rot_1','rot_2','rot_3']
        raw=np.zeros(n,[(k,'f4') for k in fields]+[('primitive_id','i4'),('arc_t','f4')]); raw['rot_0']=1
        for j,v in enumerate([.2,.1,.1]): raw['scale_'+str(j)]=np.log(v)
        raw['x']=np.arange(n); a=fmt.activate(raw); x=a['means'].copy();x[:,1]+=.02
        old=np.tile([1.,0,0],(n,1));new=np.tile(unit([1.,.1,0]),(n,1))
        rec,cov=update_geometry(raw,a['covariance'],old,x,new,np.ones(n,bool))
        d=OUT/'fixtures';d.mkdir(exist_ok=True);path=d/'roundtrip.ply';fmt.write_ply(path,rec); back=fmt.read_ply(path); act=fmt.activate(back)
        for k in raw.dtype.names:
            if k not in ['x','y','z','rot_0','rot_1','rot_2','rot_3']: np.testing.assert_array_equal(back[k],raw[k])
        np.testing.assert_allclose(act['means'],x,atol=1e-7)
        np.testing.assert_allclose(act['covariance'],cov,rtol=3e-6,atol=1e-10)

if __name__=='__main__': unittest.main()
