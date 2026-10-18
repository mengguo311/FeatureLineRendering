from env import *
import unittest
from texture import describe,block_shuffle
class Texture(unittest.TestCase):
 def test_constant(self):
  f=describe(np.full((64,64,3),.4),1);np.testing.assert_allclose(f,np.broadcast_to([.5,.5,0],f.shape),atol=1e-12)
 def test_same_colors_different_layout(self):
  y,x=np.mgrid[:64,:64];a=np.repeat(((x%8)<4)[...,None],3,axis=2).astype(float);b=np.swapaxes(a,0,1);fa=describe(a,1);fb=describe(b,1);assert fa[16:-16,16:-16,0].mean()>.95 and fb[16:-16,16:-16,0].mean()<.05;np.testing.assert_array_equal(np.sort(a.reshape(-1,3),axis=0),np.sort(b.reshape(-1,3),axis=0))
 def test_rotation_covariant(self):
  a=np.random.default_rng(3).random((65,65,3));f=describe(a,1);g=describe(np.rot90(a),1);r=np.rot90(f);np.testing.assert_allclose(g[...,:2],1-r[...,:2],atol=1e-10);np.testing.assert_allclose(g[...,2],r[...,2],atol=1e-10)
 def test_crossed_is_not_single_direction(self):
  y,x=np.mgrid[:65,:65];a=np.repeat((((x%8)<4).astype(float)+((y%8)<4))[...,None]/2,3,axis=2);f=describe(a,1);coh=np.linalg.norm(2*f[...,:2]-1,axis=2);assert coh[16:-16,16:-16].mean()<.2
 def test_finite_bounded_and_unchanged(self):
  a=np.random.default_rng(7).random((31,42,3));b=a.copy();f=describe(a,1);assert np.isfinite(f).all() and f.min()>=0 and f.max()<=1;np.testing.assert_array_equal(a,b)
 def test_nan_refused(self):
  a=np.zeros((12,12,3));a[1,1]=np.nan
  with self.assertRaises(ValueError):describe(a,1)
 def test_shuffle_multiset_block_exact(self):
  a=np.arange(17*23*3).reshape(17,23,3).astype(float);b=block_shuffle(a,9)
  for y in range(0,17,9):
   for x in range(0,23,9):
    aa=a[y:y+9,x:x+9].reshape(-1,3);bb=b[y:y+9,x:x+9].reshape(-1,3);np.testing.assert_array_equal(aa[np.argsort(aa[:,0])],bb[np.argsort(bb[:,0])])
 def test_shuffle_deterministic_not_identity(self):
  a=np.arange(18*18*3).reshape(18,18,3);b=block_shuffle(a,9);np.testing.assert_array_equal(b,block_shuffle(a,9));assert not np.array_equal(a,b)
 def test_shuffle_no_mutation(self):
  a=np.arange(18*18*3).reshape(18,18,3);b=a.copy();block_shuffle(a,9);np.testing.assert_array_equal(a,b)
 def test_single_channel_wrong_shape_refused(self):
  with self.assertRaises(ValueError):describe(np.zeros((10,10)),1)
if __name__=='__main__':unittest.main()
