"""User-authorized GPU0 shared launch; frozen scientific code/config unchanged."""
import sys,subprocess,json,signal,time
from pathlib import Path
CODE=Path('/home/u00134/3dgs_line/gaer_rade_depth_lift_v01/reproduction/radegs_paper_v01/stage2')
sys.path.append(str(CODE))
import runner,safety
GPU='GPU-d2d1e4fd-e246-0633-3343-ccc0a0bd981a'
MIN_FREE=12288
STOP_FREE=2048
MAX_UTIL=10

def can_start(g):
 return (g['uuid']==GPU and g['util_percent']<=MAX_UTIL
         and g.get('total_mib',0)-g['memory_mib']>=MIN_FREE)

def conflict(samples,selected,owned,baseline):
 if samples is None:return True
 g=next((g for g in samples if g['uuid']==selected),None)
 return (g is None or selected!=GPU or g.get('total_mib',0)-g['memory_mib']<STOP_FREE
         or any(c['pid'] not in owned|baseline for c in g['contexts']))

def query():
 gs=safety.query_gpus()
 if gs is None:return None
 try:
  raw=subprocess.check_output(['nvidia-smi','--query-gpu=uuid,memory.total','--format=csv,noheader,nounits'],text=True,timeout=20)
  totals={row.split(',')[0].strip():int(row.split(',')[1].strip()) for row in raw.splitlines()}
  for g in gs:g['total_mib']=totals[g['uuid']]
  return gs
 except (OSError,ValueError,KeyError,subprocess.SubprocessError):return None

class SharedRunner(runner.Runner):
 def __init__(self,config_path,*args,**kwargs):
  c=json.loads(Path(config_path).read_text());state=Path(c['state_dir'])/'runner_state.json'
  previous=json.loads(state.read_text()) if state.exists() else {}
  saved=previous.get('shared_baseline_identities')
  self.baseline_identities=None if saved is None else {int(k):v for k,v in saved.items()}
  self.baseline=set(self.baseline_identities or {})
  super().__init__(config_path,*args,**kwargs)
  raw_query=self.query
  def stable_recheck():
   samples=raw_query()
   eligible=next((g for g in samples or [] if can_start(g)),None)
   ids={c['pid']:runner.process_identity(c['pid']) for c in eligible['contexts']} if eligible else None
   return samples if eligible and ids==self.baseline_identities else None
  self.query=stable_recheck
 def tick(self,samples,now=None):
  if not self.child:
   eligible=next((g for g in samples or [] if can_start(g)),None)
   ids={c['pid']:runner.process_identity(c['pid']) for c in eligible['contexts']} if eligible else None
   if ids!=getattr(self,'baseline_identities',None):
    self.gate=runner.IdleGate(self.config['stable_seconds'])
   self.baseline_identities=ids
   self.baseline=set(ids or {})
  runner.stage_conflict=lambda gs,u,owned:conflict(gs,u,owned,self.baseline) or any(
    runner.process_identity(pid)!=ident for pid,ident in (self.baseline_identities or {}).items()
    if any(c['pid']==pid for g in gs or [] for c in g['contexts']))
  super().tick(samples,now)
  if self.state['status']=='WAITING_FOR_IDLE_GPU':
   self.persist(status='WAITING_FOR_LOW_LOAD_GPU')
 def persist(self,**updates):
  updates['shared_baseline_identities']=self.baseline_identities
  updates['sharing_policy']={'mode':'USER_AUTHORIZED_SHARED_GPU0','max_launch_util_percent':MAX_UTIL,
   'min_launch_free_mib':MIN_FREE,'stop_below_free_mib':STOP_FREE,'stable_seconds':60,
   'stop_on_new_foreign_context':True,'other_processes_never_signalled':True}
  super().persist(**updates)

# Keep all original preflight/stage seals/checkpointing; change only GPU admission.
def main():
 safety.is_idle=can_start
 runner.is_idle=can_start
 runner.query_gpus=query
 import argparse
 p=argparse.ArgumentParser();p.add_argument('--config',required=True);args=p.parse_args()
 e=SharedRunner(args.config,query=query)
 e.config['allowed_gpu_uuids']=[GPU]
 def stop(signum,frame):e.shutdown=True
 signal.signal(signal.SIGTERM,stop);signal.signal(signal.SIGINT,stop)
 try:
  while True:
   try:e.tick(query())
   except Exception as exc:
    if e.child:e.shutdown=True;e.request_own_stop()
    e.persist(status='ENGINEERING_NOT_READY',reason=type(exc).__name__+': '+str(exc))
    safety.archive_failure(e.path,e.directory/'failed_stages');raise
   if e.state['status'] in ('PILOT_CHAIN_COMPLETE','ENGINEERING_NOT_READY'):break
   if e.shutdown and e.child is None:break
   time.sleep(5 if e.child else e.config['poll_seconds'])
 finally:e.close()
if __name__=='__main__':main()
