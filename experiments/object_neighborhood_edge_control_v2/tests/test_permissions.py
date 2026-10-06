import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
import torch
from experiments import project_parameters,PARAMS
from renderer_adapter import small_model
class PermissionTests(unittest.TestCase):
    def test_covariance_permissions_bound_and_freeze(self):
        m=small_model([[0,0,0],[.1,0,0]],[.5,.5],[[.2,.2,.2],[.4,.4,.4]])
        original={n:getattr(m,n).detach().clone() for n in PARAMS};mask=torch.tensor([True,False],device='cuda')
        with torch.no_grad():
            for n in PARAMS:
                if getattr(m,n).numel():getattr(m,n).add_(1)
        project_parameters(m,original,mask,'cov')
        for n in PARAMS:
            self.assertTrue(torch.equal(getattr(m,n)[~mask],original[n][~mask]))
            if n not in ('_features_dc','_scaling','_rotation'):self.assertTrue(torch.equal(getattr(m,n),original[n]))
        self.assertLessEqual((m._scaling-original['_scaling']).abs().max().item(),.223144)
if __name__=='__main__':unittest.main()
