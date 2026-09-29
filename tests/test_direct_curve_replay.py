"""Cutoff regression independent of final_T and of any fit/evidence arrays."""
import unittest
import numpy as np
from src.direct_curve import native_quantiles

class ReplayArithmeticTests(unittest.TestCase):
    def test_anisotropic_cutoff_regression(self):
        # Native float32 cancellation case; CUDA stock independently accepts it.
        state=dict(means2D=np.array([[-50.9010009765625,-46.81329345703125]],'f4'),
            conic=np.array([[1.5362168550491333,-1.660949468612671,1.7971111536026,.01738426461815834]],'f4'),
            rgb=np.array([[.2,.4,.6]],'f4'),depths=np.array([2.],'f4'),
            point_list=np.array([0],'u4'),ranges=np.array([[0,1]],'u4'))
        result=native_quantiles(state,1,1)
        self.assertEqual(float(result['alpha'][0,0]),.003921806812286377)
        np.testing.assert_array_equal(result['quantiles'][0,0],[2.,2.,2.])
        self.assertEqual(float(result['front'][0,0]),2.)
        # The public replay input deliberately has no final_T or stock RGB.

    def test_independent_stock_oracle_synthetic_tiles(self):
        import ctypes
        lib=ctypes.CDLL('out/direct_curve_global_fit_probe/setup/stock_oracle_v1.so')
        fn=lib.stock_oracle;fn.argtypes=[ctypes.c_int]*4+[ctypes.c_void_p]*7;fn.restype=ctypes.c_int
        rng=np.random.default_rng(90210)
        for h,w in [(1,1),(19,23)]:
            n=300;xy=rng.uniform(-15,30,(n,2)).astype('f4')
            angle=rng.uniform(-np.pi,np.pi,n);u=np.stack([np.cos(angle),np.sin(angle)],1)
            eig=rng.uniform(.001,2,(n,2))
            co=np.c_[eig[:,0]*u[:,0]**2+eig[:,1]*u[:,1]**2,
                     (eig[:,0]-eig[:,1])*u[:,0]*u[:,1],
                     eig[:,0]*u[:,1]**2+eig[:,1]*u[:,0]**2,rng.uniform(.003,1,n)].astype('f4')
            xy[:4]=0;co[:4]=[[1,0,1,np.nextafter(np.float32(1/255),np.float32(0))],
                            [1,0,1,1/255],[1,0,1,.99],[1,0,1,.99]]
            color=rng.uniform(0,1,(n,3)).astype('f4');ids=np.arange(n,dtype='u4')
            ranges=np.tile(np.array([[0,n]],'u4'),(((w+15)//16)*((h+15)//16),1))
            rgb=np.zeros((3,h,w),'f4');trans=np.zeros((h,w),'f4')
            arrays=[xy,co,color,ids,ranges,rgb,trans]
            self.assertEqual(fn(h,w,n,n,*[a.ctypes.data for a in arrays]),0)
            state=dict(means2D=xy,conic=co,rgb=color,depths=np.arange(1,n+1,dtype='f4'),point_list=ids,ranges=ranges)
            result=native_quantiles(state,h,w)
            np.testing.assert_array_equal(result['alpha'],1-trans)
            np.testing.assert_array_equal(result['rgb'],rgb.transpose(1,2,0))
            state.update(final_T=np.full((h,w),np.nan,'f4'),stock_rgb=np.full((h,w,3),np.nan,'f4'))
            again=native_quantiles(state,h,w)
            for k in result:np.testing.assert_array_equal(result[k],again[k])

if __name__=='__main__':unittest.main()
