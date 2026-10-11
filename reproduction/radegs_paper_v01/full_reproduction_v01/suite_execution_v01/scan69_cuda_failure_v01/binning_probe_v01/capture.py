"""Detached CPU copies for failure evidence; original arguments are returned unchanged by caller."""
import torch

def snapshot_args(args):
 result=[]
 for a in args:
  if isinstance(a,torch.Tensor):result.append(a.detach().cpu().clone())
  elif isinstance(a,(int,float,bool)):result.append(a)
  else:raise TypeError(type(a))
 return tuple(result)
