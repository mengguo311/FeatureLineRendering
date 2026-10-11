import unittest,torch
from math_vjp import backward
class TestMath(unittest.TestCase):
 def test_scalar_forward_autograd(self):
  for values in [[.006404,.000004,.003604],[.04,.005,.06],[.5,-.03,.3]]:
   abc=torch.tensor(values,dtype=torch.float64,requires_grad=True);a,b,c=abc;dx=.1;dy=.1;opacity=.8;u=.9;det=a*c-b*b
   coef=torch.sqrt(det/(det+1e-6)+1e-6);invcov=torch.linalg.inv(torch.stack([torch.stack([a,b]),torch.stack([b,c])]))
   delta=torch.tensor([dx,dy],dtype=torch.float64);loss=u*opacity*coef*torch.exp(-.5*(delta@invcov@delta));ref=torch.autograd.grad(loss,abc)[0]
   torch.testing.assert_close(backward(a,b,c,dx,dy,opacity,u),ref,rtol=1e-10,atol=1e-10)
 def test_vjp_is_linear(self):
  a,b,c=[torch.tensor(v,dtype=torch.float64) for v in [.006404,.000004,.003604]]
  torch.testing.assert_close(backward(a,b,c,.1,.1,.8,1.8),2*backward(a,b,c,.1,.1,.8,.9),rtol=1e-12,atol=1e-12)
if __name__=='__main__':unittest.main()
