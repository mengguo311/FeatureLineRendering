"""Bounded actual C24 train/restart control test. Never more than five steps."""
import argparse,json,os,subprocess,sys
from pathlib import Path
from safety import atomic_json,sha256

def bounded(config,limit):
 c=json.loads(Path(config).read_text());sys.path.insert(0,c["runtime_module"])
 import train,torch
 from official_runtime import OfficialRuntime,finite_tree
 from argparse import ArgumentParser
 from arguments import ModelParams,PipelineParams,OptimizationParams
 # Real GPU RED/GREEN for mixed-device Adam step scalars and model tensors.
 finite_tree({'cpu_optimizer_step':torch.ones(1),'cuda_parameter':torch.ones(1,device='cuda')})
 c=json.loads(Path(config).read_text());assert c['purpose']=='native_validation' and limit in (3,5)
 p=ArgumentParser();mp=ModelParams(p);op=OptimizationParams(p);pp=PipelineParams(p)
 a=p.parse_args(['-s',c['data'],'-m',c['model'],'-r','2','--use_decoupled_appearance']);assert a.iterations==30000 and a.regularization_from_iter==15000 and a.lambda_distortion==100 and a.lambda_depth_normal==.05
 class Bounded(OfficialRuntime):
  def restore(self,m,o,cams):
   it,stack=super().restore(m,o,cams)
   assert it==(0 if limit==3 else 3);return it,stack
  def completed_step(self,iteration,*args,**kw):
   assert iteration<=limit
   if iteration==limit:self.stop_requested=True
   super().completed_step(iteration,*args,**kw)
 train.OfficialRuntime=Bounded;train.safe_state(False)
 try:train.training(mp.extract(a),op.extract(a),pp.extract(a),[],[],[],None,-1,config)
 except SystemExit as exc:
  if exc.code!=75:raise
  d=json.loads((Path(c['model'])/'restart.json').read_text());assert d['completed_iteration']==limit
 else:raise RuntimeError('bounded runtime bypassed stop')

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--config',required=True);ap.add_argument('--bound',type=int);a=ap.parse_args()
 if a.bound:return bounded(a.config,a.bound)
 c=json.loads(Path(a.config).read_text());assert os.environ['CUDA_VISIBLE_DEVICES']==c['allowed_gpu_uuids'][0]
 for n in (3,5):subprocess.run([sys.executable,__file__,'--config',a.config,'--bound',str(n)],check=True)
 import torch
 from checkpointing import checkpoint_descriptor
 model=Path(c['model']);d=checkpoint_descriptor(model/'restart.json',c['inputs']);payload=torch.load(d['path'],map_location='cpu');assert payload['completed_iteration']==5
 rows=[json.loads(x) for x in (model/'iteration_loss.jsonl').read_text().splitlines()];assert [x['iteration'] for x in rows]==[1,2,3,4,5]
 for x in rows:assert x['geometry_active'] is False and x['optimizer_updated'] is True and x['wn']==0
 outputs=[model/'restart.json',Path(d['path']),model/'iteration_loss.jsonl'];detail={'status':'PASS','diagnostic_only':True,'completed_steps':5,'resume_at':3,'same_C24_30k_schedule':True,'camera_stack_count':len(payload['camera_stack']),'not_numerical_trajectory_equivalence_claim':True,'scientificdone':False}
 atomic_json(c['reports']['smoke'],{'status':'PASS','stage':'smoke','attempt':os.environ['RADEGS_ATTEMPT'],'inputs':c['inputs'],'outputs':{str(p):sha256(p) for p in outputs},'details':detail,'scientificdone':False});print(json.dumps(detail),flush=True)
if __name__=='__main__':main()
