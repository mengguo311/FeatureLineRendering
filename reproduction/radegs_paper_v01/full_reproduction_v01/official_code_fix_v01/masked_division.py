"""C24 quotients with explicit zero-support derivative domain.

Independent engineering guard, not an official upstream patch. Positive-alpha
values/gradients are unchanged; C24's intended zero background no longer sends
0/0 through autograd. Raw render inputs must pass the separate finite gate.
"""
import torch

def distortion_quotient(distortion,alpha):
    active=alpha>0
    denominator=torch.where(active,alpha*alpha,torch.ones_like(alpha)).detach()
    return torch.where(active,distortion/denominator,torch.zeros_like(distortion))

def expected_depth_quotient(depth_sum,alpha):
    active=alpha>0
    denominator=torch.where(active,alpha,torch.ones_like(alpha))
    return torch.where(active,depth_sum/denominator,torch.zeros_like(depth_sum))
