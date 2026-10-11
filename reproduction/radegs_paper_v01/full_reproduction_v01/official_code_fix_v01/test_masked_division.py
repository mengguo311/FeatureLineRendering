import unittest
import torch
from masked_division import distortion_quotient,expected_depth_quotient

class QuotientTests(unittest.TestCase):
    def test_distortion_inactive_gradient_finite_zero(self):
        n=torch.tensor([0.,2.],dtype=torch.double,requires_grad=True)
        a=torch.tensor([0.,.5],dtype=torch.double,requires_grad=True)
        out=distortion_quotient(n,a);self.assertEqual(out.tolist(),[0.,8.])
        gn,ga=torch.autograd.grad(out.sum(),(n,a),allow_unused=True)
        self.assertTrue(torch.isfinite(gn).all());self.assertEqual(gn.tolist(),[0.,4.])
        self.assertIsNone(ga)

    def test_expected_depth_inactive_gradients_finite_zero(self):
        n=torch.tensor([0.,2.],dtype=torch.double,requires_grad=True)
        a=torch.tensor([0.,.5],dtype=torch.double,requires_grad=True)
        out=expected_depth_quotient(n,a);self.assertEqual(out.tolist(),[0.,4.])
        gn,ga=torch.autograd.grad(out.sum(),(n,a))
        self.assertTrue(torch.isfinite(gn).all() and torch.isfinite(ga).all())
        self.assertEqual(gn.tolist(),[0.,2.]);self.assertEqual(ga.tolist(),[0.,-8.])

    def test_positive_domain_exact_forward_and_gradient(self):
        for fun,power,detached in [(distortion_quotient,2,True),(expected_depth_quotient,1,False)]:
            n=torch.tensor([1.,2.,.2],dtype=torch.double,requires_grad=True)
            a=torch.tensor([.1,.5,.9],dtype=torch.double,requires_grad=True)
            d=a**power;d=d.detach() if detached else d
            expected=n/d;actual=fun(n,a);self.assertTrue(torch.equal(actual,expected))
            ga=torch.autograd.grad(actual.sum(),(n,a),allow_unused=True,retain_graph=True)
            ge=torch.autograd.grad(expected.sum(),(n,a),allow_unused=True)
            for x,y in zip(ga,ge):self.assertTrue(x is None and y is None or torch.equal(x,y))

if __name__=='__main__':unittest.main()
