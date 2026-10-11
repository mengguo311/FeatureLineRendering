"""Two original C24 updates at most; capture bad native VJP before PyTorch chain.
No losses, gradients, parameters, view selection, or renderer branches changed.
"""
import argparse,json,os,sys,inspect,time
from pathlib import Path
P=Path(__file__).resolve().parent
from probe_scope import validate

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--config',required=True);a=ap.parse_args();c=json.loads(Path(a.config).read_text());validate(c)
 sys.path.insert(0,c['runtime_module']);sys.path.insert(0,c['runtime_source'])
 import torch,train,diff_gaussian_rasterization as raster
 from official_runtime import OfficialRuntime
 from checkpointing import PARAMETERS
 from safety import atomic_json,sha256
 from arguments import ModelParams,PipelineParams,OptimizationParams
 assert sha256(raster._C.__file__)==c['inputs']['native']
 assert os.environ['CUDA_VISIBLE_DEVICES']==c['allowed_gpu_uuids'][0]
 out=Path(c['capture_dir'])/os.environ['RADEGS_ATTEMPT'];out.mkdir(parents=True,exist_ok=False);events=[];active={};original_render=train.render;original_backward=raster._RasterizeGaussians.backward
 def render(camera,model,*args,**kw):
  active.update(camera=camera.image_name,model=model)
  return original_render(camera,model,*args,**kw)
 train.render=render
 names=['means3D','means2D','sh','colors_precomp','opacities','scales','rotations','cov3Ds_precomp','settings']
 def capture_backward(ctx,*grads):
  result=original_backward(ctx,*grads)
  bad={}
  for name,g in zip(names,result):
   if isinstance(g,torch.Tensor) and g.numel() and not bool(torch.isfinite(g).all()):
    bad[name]=(~torch.isfinite(g)).reshape(g.shape[0],-1).any(1).nonzero().flatten().cpu().tolist()
  event={'camera':active.get('camera'),'bad_native_gradient_rows':bad,'upstream':{name:{'maxabs':float(g.abs().max()),'finite':bool(torch.isfinite(g).all())} for name,g in zip(['rgb','radii','depth','median','alpha','normal','distortion'],grads) if isinstance(g,torch.Tensor) and g.numel()}}
  events.append(event);atomic_json(out/'NATIVE_EVENTS.json',events)
  if bad:
   data={'camera':active.get('camera'),'saved_tensors':[v.detach().cpu() for v in ctx.saved_tensors],'settings':{k:v.detach().cpu() if isinstance(v,torch.Tensor) else v for k,v in ctx.raster_settings._asdict().items()},'num_rendered':ctx.num_rendered,'upstream':[v.detach().cpu() if isinstance(v,torch.Tensor) else v for v in grads],'native_gradients':[v.detach().cpu() if isinstance(v,torch.Tensor) else v for v in result],'parameters':{k:getattr(active['model'],k).detach().cpu() for k in PARAMETERS},'filter_3D':active['model'].filter_3D.detach().cpu()}
   torch.save(data,out/('native_failure_'+str(len(events))+'.pt'))
  return result
 raster._RasterizeGaussians.backward=staticmethod(capture_backward)
 class Bounded(OfficialRuntime):
  def completed_step(self,iteration,*args,**kw):
   super().completed_step(iteration,*args,**kw)
   if iteration>=2:raise SystemExit(0)
 train.OfficialRuntime=Bounded
 p=argparse.ArgumentParser();mp=ModelParams(p);op=OptimizationParams(p);pp=PipelineParams(p);args=p.parse_args(['-s',c['data'],'-m',c['model'],'-r','2','--use_decoupled_appearance'])
 assert args.iterations==30000 and args.lambda_distortion==100 and args.lambda_depth_normal==.05
 train.safe_state(False)
 try:train.training(mp.extract(args),op.extract(args),pp.extract(args),[],[],[],None,-1,a.config)
 except FloatingPointError as exc:
  atomic_json(out/'REPLAY_RED.json',{'status':'ACTUAL_NONFINITE_REPRODUCED','error':repr(exc),'events':events,'scientificdone':False});raise
 except SystemExit as exc:
  if exc.code!=0:raise
  atomic_json(out/'REPLAY_NOT_REPRODUCED.json',{'status':'TWO_STEPS_FINITE_ONLY','events':events,'does_not_disprove_original_failure':True,'scientificdone':False})
  report={'status':'PASS','stage':'smoke','inputs':c['inputs'],'attempt':os.environ['RADEGS_ATTEMPT'],'outputs':{str(p):sha256(p) for p in out.iterdir() if p.is_file()},'details':{'bounded_steps':2,'not_full_training_validation':True}}
  atomic_json(c['reports']['smoke'],report)
if __name__=='__main__':main()
