"""CPU oracle: decomposed diagnostic VJPs must add to unchanged full Eq24."""
import sys,unittest
from pathlib import Path
import torch
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'stage2'))
from gradient_decomposition import eq24_diagnostic_parts
class Decomposition(unittest.TestCase):
 def test_chain_rule_all_paths(self):
  x=torch.tensor([.2,.3,.8],dtype=torch.double,requires_grad=True)
  y,z=torch.meshgrid(torch.arange(7,dtype=torch.double),torch.arange(9,dtype=torch.double),indexing='ij')
  depth=(2+x[0]*y*.01+x[1]*z*.02).unsqueeze(0)
  alpha=torch.sigmoid(x[0]+x[1]*y*.1).unsqueeze(0)
  mix=torch.stack([alpha[0]*x[0],alpha[0]*x[1],-alpha[0]*torch.sigmoid(x[2])])
  parts=eq24_diagnostic_parts(alpha,mix,depth,10.,12.)
  grads={k:torch.autograd.grad(v,x,retain_graph=True)[0] for k,v in parts.items()}
  torch.testing.assert_close(grads['full'],grads['alpha']+grads['normal']+grads['depth'],rtol=1e-12,atol=1e-12)
  self.assertGreater(float(grads['depth'].abs().max()),0)
 def test_values_are_not_summed_as_loss(self):
  d=torch.ones((1,7,9),dtype=torch.double,requires_grad=True)*2
  a=torch.full_like(d,.6,requires_grad=True);n=torch.cat([d*0,d*0,-a],0)
  parts=eq24_diagnostic_parts(a,n,d,10.,12.)
  self.assertGreater(abs(float(sum(parts[k] for k in ['alpha','normal','depth'])-parts['full'])),.1)
if __name__=='__main__':unittest.main()
