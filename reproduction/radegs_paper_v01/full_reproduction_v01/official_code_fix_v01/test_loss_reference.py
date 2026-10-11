import unittest,torch
from loss_reference import mapped_pairs,normal_consistency
class Tests(unittest.TestCase):
 def test_mapped_unordered_pairs_and_detach(self):
  z=torch.tensor([1.,2.,4.],dtype=torch.double,requires_grad=True);w=torch.tensor([.2,.3,.1],dtype=torch.double,requires_grad=True)
  a=mapped_pairs(z,w);m=(100*z-20)/(99.8*z)
  b=sum(w[i].detach()*w[j].detach()*(m[i]-m[j])**2 for i in range(3) for j in range(i))
  self.assertTrue(torch.equal(a,b));g=torch.autograd.grad(a,(z,w),allow_unused=True);self.assertIsNone(g[1]);self.assertTrue(torch.isfinite(g[0]).all())
  self.assertTrue(torch.allclose(mapped_pairs(z,w*2),a*4))
 def test_normal_is_normalized_and_expected_median_mix(self):
  normal=torch.zeros(3,5,5,dtype=torch.double);normal[2]=-2;d=torch.ones(1,5,5,dtype=torch.double)*2
  expected=normal_consistency(normal,d,d,10,11);self.assertAlmostEqual(float(expected[2,2]),0,12)
  self.assertTrue(torch.equal(expected,normal_consistency(normal*3,d,d,10,11)))
 def test_depth_gradcheck(self):
  d=torch.full((1,5,5),2.,dtype=torch.double,requires_grad=True);n=torch.zeros(3,5,5,dtype=torch.double);n[2]=-1
  self.assertTrue(torch.autograd.gradcheck(lambda x:normal_consistency(n,x,d.detach(),10.,11.),(d,)))
if __name__=='__main__':unittest.main(verbosity=2)
