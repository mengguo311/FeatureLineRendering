import unittest
import torch
from reference import pixel, parameters, FIXTURES

class ReferenceTests(unittest.TestCase):
    def test_double_all_input_gradcheck_and_z_difference(self):
        for f in FIXTURES[:2]:
            p=parameters(f)
            keys=tuple(p)
            self.assertTrue(torch.autograd.gradcheck(lambda *x:pixel(dict(zip(keys,x)))[0],tuple(p.values()),eps=1e-6,atol=1e-6,rtol=1e-5))
            loss,_=pixel(p);g=torch.autograd.grad(loss,p['means'])[0][0,2]
            vals=[]
            for sign in [-1,1]:
                pp={k:v.detach().clone() for k,v in p.items()};pp['means'][0,2]+=sign*3e-4
                vals.append(pixel(pp)[0])
            self.assertLess(abs(float((vals[1]-vals[0])/6e-4-g)),1e-6)

    def test_clamped_covariance_is_zero_opacity_not_sqrt_half(self):
        p=parameters(FIXTURES[2]);loss,m=pixel(p)
        self.assertLess(m['det'],1e-6);self.assertEqual(m['coef'],0.)
        self.assertEqual(m['alpha'],0.);self.assertAlmostEqual(float(loss),.6,12)
        grads=torch.autograd.grad(loss,tuple(p.values()))
        self.assertTrue(all(torch.equal(g,torch.zeros_like(g)) for g in grads))

if __name__=='__main__':unittest.main()
