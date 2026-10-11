"""Independent Torch reference for C24 mapped unordered pairs and normal loss.

Not the old paper-text Eq23/Eq24. Weight stop-gradients follow C24 native; no
Gaussian-count normalization. Positive support denominator is applied outside.
"""
import torch
import torch.nn.functional as F

def mapped_pairs(depths,weights):
 m=(100*depths-20)/(99.8*depths);w=weights.detach()
 return sum(w[i]*w[j]*(m[i]-m[j]).square() for i in range(len(w)) for j in range(i))

def depth_normal(depth,fx,fy):
 h,w=depth.shape[-2:];y,x=torch.meshgrid(torch.arange(h,dtype=depth.dtype,device=depth.device),torch.arange(w,dtype=depth.dtype,device=depth.device),indexing='ij')
 points=depth[0,...,None]*torch.stack(((x+.5-w/2)/fx,(y+.5-h/2)/fy,torch.ones_like(x)),dim=-1)
 dx=points[2:,1:-1]-points[:-2,1:-1];dy=points[1:-1,2:]-points[1:-1,:-2]
 n=F.normalize(torch.cross(dx,dy,dim=-1),dim=-1)
 return F.pad(n.permute(2,0,1),(1,1,1,1)).permute(1,2,0)

def normal_consistency(mixed,expected,median,fx,fy):
 n=F.normalize(mixed,dim=0).permute(1,2,0)
 return .4*(1-(n*depth_normal(expected,fx,fy)).sum(-1))+.6*(1-(n*depth_normal(median,fx,fy)).sum(-1))
