"""Fresh 0..1000 real scan69 finite trace under compute-sanitizer, candidate native. Not proof of original NaN cause; no scientific training dispatch."""
import argparse,json,os,sys,time,traceback
from pathlib import Path
P=Path(__file__).resolve().parent;sys.path.insert(0,str(P.parent));sys.path.insert(0,str(P.parent/'binning_probe_v01'));sys.path.insert(0,str(P.parent/'first_nonfinite_v01'))
from replay_limit import ReplayLimit,ReplayComplete
from capture import snapshot_args
from finite import bad_tensors

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--config',required=True);args=ap.parse_args();c=json.loads(Path(args.config).read_text());assert os.environ['CUDA_VISIBLE_DEVICES']==c['allowed_gpu_uuids'][0] and os.environ['CUDA_LAUNCH_BLOCKING']=='1'
 import torch,train,diff_gaussian_rasterization as raster
 from safety import atomic_json,sha256
 from pilot_runtime import PilotRuntime
 from checkpointing import PARAMETERS
 from arguments import ModelParams,PipelineParams,OptimizationParams
 parent=json.loads(Path(c['parent_config']).read_text());assert Path(train.__file__).resolve()==Path(parent['cwd'])/'train.py'
 out=Path(c['diagnostic_output'])/os.environ['RADEGS_ATTEMPT'];out.mkdir(parents=True,exist_ok=False);limit=ReplayLimit(0,1000);event={'iteration':1,'phase':'initializing'};cache={};model_ref=[None]
 def snapshot_model(model):
  return {'parameters':{k:getattr(model,k).detach().cpu().clone() for k in PARAMETERS},'parameter_grads':{k:None if getattr(model,k).grad is None else getattr(model,k).grad.detach().cpu().clone() for k in PARAMETERS},'filter_3D':model.filter_3D.detach().cpu().clone()}
 def fail(phase,bad):
  event.update(phase=phase,bad=bad);atomic_json(out/'first_nonfinite.json',event)
  payload={'event':dict(event),'forward_args':cache.get('forward_args'),'model':snapshot_model(model_ref[0]) if model_ref[0] is not None else None}
  if 'backward_args' in cache:payload.update(backward_args=snapshot_args(cache['backward_args']),backward_outputs=snapshot_args(cache['backward_outputs']))
  torch.save(payload,out/'first_nonfinite.pt');raise FloatingPointError('first nonfinite: '+phase+' '+json.dumps(bad))
 class Runtime(PilotRuntime):
  def restore(self,model,options,cameras):
   model_ref[0]=model;iteration,stack=super().restore(model,options,cameras);limit.resume(iteration)
   bad=bad_tensors({k:getattr(model,k) for k in PARAMETERS})
   if bad:fail('parameters_at_initialization_or_resume',bad)
   return iteration,stack
  def completed_step(self,iteration,model,stack,losses):
   bad=bad_tensors({k:getattr(model,k) for k in PARAMETERS})
   if bad:fail('parameters_after_optimizer',bad)
   super().completed_step(iteration,model,stack,losses);limit.completed(iteration)
 train.PilotRuntime=Runtime
 native_fw=raster._C.rasterize_gaussians;native_bw=raster._C.rasterize_gaussians_backward;original_render=train.render
 def forward(*a):
  cache['forward_args']=snapshot_args(a);bad=bad_tensors({str(i):x for i,x in enumerate(a)})
  if bad:fail('native_forward_input',bad)
  result=native_fw(*a);torch.cuda.synchronize();return result
 def backward(*a):
  result=native_bw(*a);torch.cuda.synchronize();cache.update(backward_args=a,backward_outputs=result)
  bad=bad_tensors({str(i):x for i,x in enumerate(result)})
  if bad:fail('native_backward_output',bad)
  return result
 def render(*a,**kw):
  event.update(view=a[0].image_name,phase='render',points=len(a[1]._xyz));return original_render(*a,**kw)
 raster._C.rasterize_gaussians=forward;raster._C.rasterize_gaussians_backward=backward;train.render=render
 after_backward=next(i for i,line in enumerate(Path(train.__file__).read_text().splitlines(),1) if line.strip()=='iter_end.record()')
 def trace(frame,what,arg):
  if frame.f_code.co_name=='training' and frame.f_code.co_filename==train.__file__ and what=='line':
   if 'iteration' in frame.f_locals:event['iteration']=frame.f_locals['iteration']
   event['source_line']=frame.f_lineno
   if frame.f_lineno==after_backward:
    model=frame.f_locals['gaussians'];bad=bad_tensors({k:getattr(model,k).grad for k in PARAMETERS})
    if bad:fail('parameter_grad_before_optimizer',bad)
  return trace
 p=argparse.ArgumentParser();mp=ModelParams(p);op=OptimizationParams(p);pp=PipelineParams(p);optargs,_=p.parse_known_args(parent['train_command'][2:]);assert optargs.iterations==30000 and optargs.resolution==2
 optargs.model_path=c['model'];train.safe_state(False);error=None
 try:
  sys.settrace(trace);train.training(mp.extract(optargs),op.extract(optargs),pp.extract(optargs),[],[],[],None,-1,c['replay_pilot_config']);raise RuntimeError('bound bypassed')
 except ReplayComplete:status='NO_NONFINITE_FOUND_THROUGH1000'
 except Exception as exc:status='FIRST_FAILURE_CAPTURED';error={'type':type(exc).__name__,'message':str(exc),'traceback':traceback.format_exc()};print(error['traceback'],flush=True)
 finally:sys.settrace(None)
 original={r['iteration']:r for r in map(json.loads,(Path(parent['model'])/'iteration_loss.jsonl').read_text().splitlines())};rows=[json.loads(l) for l in (Path(c['model'])/'iteration_loss.jsonl').read_text().splitlines()];common=[r for r in rows if r['iteration'] in original]
 result={'status':status,'error':error,'last_event':event,'last_completed':limit.last,'prefix_completed':len(rows),'max_abs_photo_prefix_difference':max([abs(r['photo']-original[r['iteration']]['photo']) for r in common],default=None),'points_prefix_identical':all(r['points']==original[r['iteration']]['points'] for r in common),'bitexact_claim':False,'scientificdone':False,'source_train_sha256':sha256(train.__file__),'native_sha256':sha256(raster._C.__file__),'diagnostic_only':True}
 rf=out/'result.json';atomic_json(rf,result);outputs={str(p):sha256(p) for p in out.iterdir() if p.is_file()}
 if status!='NO_NONFINITE_FOUND_THROUGH1000':raise RuntimeError('candidate bounded finite/memcheck validation failed; result retained at '+str(rf))
 atomic_json(c['reports']['smoke'],{'status':'PASS','stage':'smoke','attempt':os.environ['RADEGS_ATTEMPT'],'inputs':c['inputs'],'outputs':outputs,'details':{'diagnostic_only':True,'actual_training_success':False,'result':str(rf)},'unix':time.time(),'scientificdone':False});print(json.dumps(result,indent=2),flush=True)
if __name__=='__main__':main()
