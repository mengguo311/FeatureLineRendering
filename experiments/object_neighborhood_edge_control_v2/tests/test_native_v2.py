import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
import torch,numpy as np
from renderer_adapter import small_model,make_camera,rgb
from color_operator import ColorOperator
class NativeV2Tests(unittest.TestCase):
    def setUp(self):
        self.m=small_model([[0,0,0],[.1,0,-.2]],[.8,.7],[[1.2,.1,.2],[-.1,.8,.4]])
        for p in (self.m._xyz,self.m._scaling,self.m._rotation,self.m._opacity,self.m._features_dc):p.requires_grad_(False)
        cam=make_camera({'transform_matrix':[[1,0,0,0],[0,1,0,0],[0,0,1,3],[0,0,0,1]]},65)
        self.v={'camera':cam,'band':torch.ones((65,65),dtype=torch.bool,device='cuda'),'target':rgb(self.m,cam).detach()}
    def test_all_selected_operator_with_clamp_and_non_candidate_gt_one(self):
        for mask in (torch.tensor([False,True],device='cuda'),torch.tensor([True,True],device='cuda')):
            a=ColorOperator(self.m,[self.v],mask);d=a.validate();self.assertLess(d['adjoint_relative_error'],2e-5)
            c=a.original[mask].clamp(0,1);cert,g=a.certificate(c,3e-7);self.assertLessEqual(cert['D'],cert['P']+1e-6)
    def test_continuous_coverage_loss_backpropagates_covariance(self):
        self.m._scaling.requires_grad_(True)
        alpha=rgb(self.m,self.v['camera'],torch.ones((2,3),device='cuda'))[0]
        reliable=alpha.detach()>.2
        loss=(.95-alpha[reliable]).clamp_min(0).square().mean();g=torch.autograd.grad(loss,self.m._scaling)[0]
        self.assertGreater(g.abs().sum().item(),1e-8)
if __name__=='__main__':unittest.main()
