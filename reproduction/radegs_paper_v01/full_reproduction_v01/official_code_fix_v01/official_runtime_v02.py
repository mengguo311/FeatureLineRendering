"""C24 scientific ordering, durable owned checkpoints and finite gates.

Opacity logits +/-Inf are explicit sigmoid endpoints, never silently clamped.
NaN logits, nonfinite gradients/Adam, and nonfinite activated inputs are errors.
No losses or optimizer schedules are supplied/changed by this engineering layer.
"""
import json,os,signal,time
from pathlib import Path
import torch
from checkpointing import PARAMETERS,BUFFERS,save_checkpoint,restore_checkpoint
from safety import atomic_json

def phase(iteration):return iteration>=15000,iteration<30000

def finite_tree(obj,label='value'):
 values=[]
 def walk(x,name):
  if isinstance(x,torch.Tensor):values.append((name,x))
  elif isinstance(x,dict):
   for k,v in x.items():walk(v,name+'/'+str(k))
  elif isinstance(x,(list,tuple)):
   for k,v in enumerate(x):walk(v,name+'/'+str(k))
 walk(obj,label)
 groups={}
 for _,v in values:groups.setdefault(v.device,[]).append(torch.isfinite(v).all())
 if any(not bool(torch.stack(predicates).all()) for predicates in groups.values()):
  raise FloatingPointError('nonfinite '+','.join(n for n,v in values if not torch.isfinite(v).all()))

def finite_model(m,gradients=False):
 values={k:getattr(m,k).grad if gradients else getattr(m,k) for k in PARAMETERS}
 if not gradients:
  opacity=values.pop('_opacity');finite_tree(torch.where(torch.isinf(opacity),torch.sigmoid(opacity),opacity),'opacity_logit_or_endpoint')
  values.update({k:getattr(m,k) for k in BUFFERS});values['appearance']=m.appearance_network.state_dict();values['Adam']=m.optimizer.state_dict()
  for k in ('get_scaling','get_rotation','get_opacity_with_3D_filter'):
   if hasattr(m,k):values[k]=getattr(m,k)
 else:values['appearance_grad']={k:v.grad for k,v in m.appearance_network.named_parameters()}
 finite_tree(values,'model_grad' if gradients else 'model')

def reconcile_log(path,iteration):
 path=Path(path)
 if not path.exists():
  if iteration:raise ValueError('checkpoint without iteration log')
  return
 raw=path.read_text();lines=raw.splitlines();rows=[];partial=False
 for line in lines:
  try:rows.append(json.loads(line))
  except json.JSONDecodeError:partial=True;break
 keep=[r for r in rows if r['iteration']<=iteration]
 if [r['iteration'] for r in keep]!=list(range(1,iteration+1)):raise ValueError('iteration history gaps/duplicates/order mismatch')
 if len(rows)!=iteration or partial:
  backup=path.with_name(path.name+'.uncommitted-'+str(time.time_ns()));backup.write_text(raw)
  tmp=path.with_suffix('.tmp');tmp.write_text(''.join(json.dumps(x,allow_nan=False)+'\n' for x in keep));os.replace(tmp,path)

class OfficialRuntime:
 def __init__(self,config,cuda=True):
  self.config=json.loads(Path(config).read_text());self.provenance=self.config['inputs'];self.model_path=Path(self.config['model']);self.model_path.mkdir(parents=True,exist_ok=True);self.checkpoint=self.model_path/'restart.json';self.cuda=cuda;self.stop_requested=False;self.last=0;self.log=None
  signal.signal(signal.SIGTERM,self.request_stop);signal.signal(signal.SIGINT,self.request_stop)
 def request_stop(self,signum=None,frame=None):self.stop_requested=True
 def failure(self,phase,model,exception):
  name='finite_failure_'+str(time.time_ns());atomic_json(self.model_path/(name+'.json'),{'phase':phase,'after_completed':self.last,'error':repr(exception),'scientificdone':False})
  # This diagnostic snapshot is explicitly NOT a verified restart checkpoint.
  torch.save({'phase':phase,'parameters':{k:getattr(model,k).detach().cpu() for k in PARAMETERS},'parameter_grads':{k:None if getattr(model,k).grad is None else getattr(model,k).grad.detach().cpu() for k in PARAMETERS},'optimizer':model.optimizer.state_dict()},self.model_path/(name+'.unverified.pt'))
 def guard(self,model,phase,gradients=False):
  try:finite_model(model,gradients)
  except FloatingPointError as exc:self.failure(phase,model,exc);raise
 def restore(self,model,options,cameras):
  it,names=(restore_checkpoint(self.checkpoint,model,options,self.provenance,cuda=self.cuda) if self.checkpoint.exists() else (0,None));self.last=it
  self.guard(model,'initialization_or_restore');reconcile_log(self.model_path/'iteration_loss.jsonl',it);self.log=open(self.model_path/'iteration_loss.jsonl','a',buffering=1)
  byname={c.image_name:c for c in cameras};return it,None if names is None else [byname[n] for n in names]
 def completed_step(self,iteration,model,stack,losses,rendered_mask):
  if iteration!=self.last+1:raise ValueError('nonsequential completed iteration')
  self.guard(model,'after_optimizer');geometry,update=phase(iteration)
  record={'iteration':iteration,'geometry_active':geometry,'optimizer_updated':update,'wd':100 if geometry else 0,'wn':.05 if geometry else 0,'unix':time.time(),'points':len(model._xyz),**{k:float(v.detach()) for k,v in losses.items()},'opacity_logit_posinf':int(torch.isposinf(model._opacity).sum()),'opacity_logit_neginf':int(torch.isneginf(model._opacity).sum()),'opacity_reset_after_forward':iteration in (3000,6000,9000,12000)}
  if rendered_mask is not None:record.update(alpha_mean=float(rendered_mask.mean()),alpha_positive=int((rendered_mask>0).sum()),alpha_ge_half=int((rendered_mask>=.5).sum()),pixels=rendered_mask.numel())
  self.log.write(json.dumps(record,allow_nan=False)+'\n');self.last=iteration
  if iteration%500==0 or iteration in (14999,15000,30000) or self.stop_requested:
   self.log.flush();os.fsync(self.log.fileno());names=None if stack is None else [x.image_name for x in stack]
   desc=save_checkpoint(self.checkpoint,model,iteration,names,self.provenance,cuda=self.cuda)
   if iteration in (14999,15000,30000):
    save_checkpoint(self.model_path/('checkpoint_'+str(iteration)+'.json'),model,iteration,names,self.provenance,cuda=self.cuda)
    # Stored after the completed optimizer step, separate from C24's pre-step scene.save.
    model.save_ply(str(self.model_path/'completed_step_ply'/str(iteration)/'point_cloud.ply'))
   atomic_json(self.model_path/'training_progress.json',{'completed_iteration':iteration,'checkpoint':desc,'loss':record,'state':'PREEMPTED' if self.stop_requested else 'RUNNING','scientificdone':False})
  if self.stop_requested:self.log.close();raise SystemExit(75)
 def finished(self,model):
  assert self.last==30000;self.guard(model,'final');model.save_ply(str(self.model_path/'point_cloud/iteration_30000/point_cloud.ply'))
  atomic_json(self.model_path/'train_complete.json',{'iterations':30000,'photo_only_records':14999,'geometry_records':15001,'optimizer_updates':29999,'inputs':self.provenance,'scientificdone':False,'unix':time.time()});self.log.close()
