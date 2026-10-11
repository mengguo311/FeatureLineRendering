"""Read-only finite checks for first-failure evidence; no clamps or gradient changes."""
import torch

def bad_tensors(values):
 result={}
 for k,v in values.items():
  if v is None or not isinstance(v,torch.Tensor) or not v.numel():continue
  bad=~torch.isfinite(v)
  if bool(bad.any()):
   ids=bad.reshape(v.shape[0] if v.ndim else 1,-1).any(1).nonzero().flatten().cpu().tolist()
   result[k]={'nonfinite':int(bad.sum()),'point_ids':ids}
 return result
