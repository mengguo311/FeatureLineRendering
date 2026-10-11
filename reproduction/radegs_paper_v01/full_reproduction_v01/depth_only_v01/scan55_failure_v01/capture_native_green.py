"""Single GPU subprocess; captured RGB-only context with no altered cotangents."""
import argparse,json,os
from pathlib import Path
import torch,diff_gaussian_rasterization as raster
from safety import atomic_json,sha256

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--config',required=True);ap.add_argument('--output',required=True);a=ap.parse_args();c=json.loads(Path(a.config).read_text());out=Path(a.output)
 assert os.environ['CUDA_VISIBLE_DEVICES']==c['allowed_gpu_uuids'][0]
 assert sha256(raster._C.__file__)==c['inputs']['native']
 # Real captured native context, RGB upstream only: previously NaN in cov/scales/rotations.
 from types import SimpleNamespace
 d=torch.load(c['native_capture'],map_location='cpu',weights_only=False)
 settings=raster.GaussianRasterizationSettings(**{k:v.cuda() if isinstance(v,torch.Tensor) else v for k,v in d['settings'].items()})
 ctx=SimpleNamespace(saved_tensors=tuple(v.cuda() for v in d['saved_tensors']),raster_settings=settings,num_rendered=d['num_rendered'])
 result=raster._RasterizeGaussians.backward(ctx,*[v.cuda() if isinstance(v,torch.Tensor) else v for v in d['upstream']])
 detail={};row=45961
 for i,v in enumerate(result):
  if isinstance(v,torch.Tensor) and v.numel():
   assert torch.isfinite(v).all(),('captured gradient',i)
   detail[str(i)]={'maxabs':float(v.abs().max()),'row45961':v[row].detach().cpu().tolist()}
 atomic_json(out/'CAPTURE_NATIVE_GREEN.json',{'status':'PASS','gradients':detail,'old_bad_native_indices':[5,6,7],'scope':'same captured context with RGB-only upstream; no gradient masking'})

if __name__=='__main__':main()
