"""Bounded exact-checkpoint diagnostic in a new model directory; no method patch."""
import argparse,json,os,sys,time,traceback
from pathlib import Path
from replay_limit import ReplayLimit,ReplayComplete

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--config',required=True);args=ap.parse_args();c=json.loads(Path(args.config).read_text());assert os.environ['CUDA_VISIBLE_DEVICES']==c['allowed_gpu_uuids'][0] and os.environ['CUDA_LAUNCH_BLOCKING']=='1'
 import torch,train
 from safety import atomic_json,sha256
 from pilot_runtime import PilotRuntime
 from arguments import ModelParams,PipelineParams,OptimizationParams
 parent=json.loads(Path(c['parent_config']).read_text());assert Path(train.__file__).resolve()==Path(parent['cwd'])/'train.py'
 out=Path(c['diagnostic_output'])/os.environ['RADEGS_ATTEMPT'];out.mkdir(parents=True,exist_ok=False);limit=ReplayLimit(500,1000);event={'iteration':501,'phase':'initializing'}
 class Runtime(PilotRuntime):
  def restore(self,model,options,cameras):
   iteration,stack=super().restore(model,options,cameras);limit.resume(iteration);return iteration,stack
  def completed_step(self,iteration,model,stack,losses):
   super().completed_step(iteration,model,stack,losses);limit.completed(iteration)
 train.PilotRuntime=Runtime
 original_render=train.render;original_appearance=train.L1_loss_appearance;original_ssim=train.ssim
 def wrap(name,fn):
  def call(*a,**kw):
   event.update(phase=name+'_begin');atomic_json(out/'last_operation.json',event)
   if name=='render':event['view']=a[0].image_name;event['points']=len(a[1]._xyz);atomic_json(out/'last_operation.json',event)
   value=fn(*a,**kw);torch.cuda.synchronize();event['phase']=name+'_end';atomic_json(out/'last_operation.json',event);return value
  return call
 train.render=wrap('render',original_render);train.L1_loss_appearance=wrap('appearance',original_appearance);train.ssim=wrap('ssim',original_ssim)
 def trace(frame,what,arg):
  if frame.f_code.co_name=='training' and frame.f_code.co_filename==train.__file__ and what=='line':
   event['source_line']=frame.f_lineno
   if 'iteration' in frame.f_locals:event['iteration']=frame.f_locals['iteration']
  return trace
 p=argparse.ArgumentParser();mp=ModelParams(p);op=OptimizationParams(p);pp=PipelineParams(p);optargs,_=p.parse_known_args(parent['train_command'][2:]);assert optargs.iterations==30000 and optargs.resolution==2
 optargs.model_path=c['model'];train.safe_state(False);error=None;status=None
 try:
  sys.settrace(trace)
  train.training(mp.extract(optargs),op.extract(optargs),pp.extract(optargs),[],[],[],None,-1,c['replay_pilot_config'])
  raise RuntimeError('diagnostic bound unexpectedly bypassed')
 except ReplayComplete:status='NOT_REPRODUCED_IN_SYNCHRONOUS_PREFIX'
 except Exception as exc:
  status='FAILURE_REPRODUCED_IN_SYNCHRONOUS_PREFIX';error={'type':type(exc).__name__,'message':str(exc),'traceback':traceback.format_exc()};print(error['traceback'],flush=True)
 finally:sys.settrace(None)
 assert limit.last<=1000
 original={r['iteration']:r for r in map(json.loads,(Path(parent['model'])/'iteration_loss.jsonl').read_text().splitlines())}
 replay=[json.loads(l) for l in (Path(c['model'])/'iteration_loss.jsonl').read_text().splitlines()];common=[r for r in replay if r['iteration'] in original]
 result={'status':status,'error':error,'last_event':event,'last_completed':limit.last,'replayed_records':len(replay),'overlap_records':len(common),'max_abs_photo_prefix_difference':max([abs(r['photo']-original[r['iteration']]['photo']) for r in common],default=None),'points_prefix_identical':all(r['points']==original[r['iteration']]['points'] for r in common),'CPU_GPU_bitexact_claim':False,'CUDA_LAUNCH_BLOCKING':1,'isolated_model':c['model'],'source_train_sha256':sha256(train.__file__),'parent_config_sha256':sha256(c['parent_config']),'original_production_model_unchanged':True,'actual_training_success':False,'scientificdone':False}
 resultfile=out/'replay_result.json';atomic_json(resultfile,result)
 atomic_json(c['reports']['smoke'],{'status':'PASS','stage':'smoke','attempt':os.environ['RADEGS_ATTEMPT'],'inputs':c['inputs'],'outputs':{str(resultfile):sha256(resultfile),str(out/'last_operation.json'):sha256(out/'last_operation.json')},'details':{'diagnostic_only':True,'actual_training_success':False,'result':str(resultfile)},'unix':time.time(),'scientificdone':False});print(json.dumps(result,indent=2),flush=True)
if __name__=='__main__':main()
