"""Independent official-route control, shared GPU0 and original common own lock.

Reuse proven core seal/identity/checkpoint supervision; preserve exact resource
preemption cause, and reject changed foreign contexts at immediate launch query.
"""
import argparse,json,signal,sys,time
from pathlib import Path
P=Path(__file__).resolve().parent
sys.path.insert(0,str(P));sys.path.append(str(P.parents[2]/'stage2'));sys.path.append(str(P.parents[1]/'precision_v01'))
import runner
import safety
import strict_shared_policy as policy
from pipeline_scope import validate_scope
safety.is_idle=runner.is_idle=policy.can_start

def identities(samples):
 if samples is None:return None
 return {c['pid']:runner.process_identity(c['pid']) for g in samples for c in g['contexts']}

class OfficialRunner(runner.Runner):
 def __init__(self,path,*args,query=policy.query,**kw):
  self.raw_query=query;self.baseline_identities=None
  saved_path=Path(json.loads(Path(path).read_text())['state_dir'])/'runner_state.json'
  if saved_path.exists():
   previous=json.loads(saved_path.read_text())
   if previous.get('child_pid'):self.baseline_identities={int(k):v for k,v in (previous.get('baseline_identities') or {}).items()}
  super().__init__(path,*args,query=self.recheck,**kw)
  if self.child:self.baseline_identities={int(k):v for k,v in (self.state.get('baseline_identities') or {}).items()}
 def recheck(self):
  samples=self.raw_query()
  return samples if identities(samples)==self.baseline_identities else None
 def pending_stage(self):
  validate_scope(self.config)
  return next((s for s in ('train','export','tsdf','eval') if not safety.verify_seal(self.directory/(s+'.seal.json'),s,self.config['inputs'])),None)
 def persist(self,**updates):
  if updates.get('status')=='PILOT_CHAIN_COMPLETE':updates.update(status='OFFICIAL_PILOT_EVALUATED_REVIEW_REQUIRED',pilot_evaluation_verified=True,scientificdone=False)
  if updates.get('status')=='WAITING_FOR_IDLE_GPU':updates['status']='WAITING_FOR_LOW_LOAD_GPU'
  updates.update(method_variant='official_code_fix_v01',baseline_identities=self.baseline_identities)
  super().persist(**updates)
 def tick(self,samples,now=None):
  if not self.child:
   eligible=samples if samples and len(samples)==1 and policy.can_start(samples[0]) else None
   ids=identities(eligible)
   if ids!=self.baseline_identities:self.gate=runner.IdleGate(self.config['stable_seconds'])
   self.baseline_identities=ids
  def conflict(gs,selected,owned):
   # NVIDIA may retain a just-exited own context after poll() observed alive.
   # Ignore only this run's identity-recorded dead/zombie members. A live PID
   # with a different start time remains a foreign context and triggers stop.
   owned=set(owned)
   recorded=dict(self.known_owned)
   if self.child is not None and self.identity is not None:recorded[self.child.pid]=self.identity
   for pid in recorded:
    if runner.process_identity(pid) is None:owned.add(pid)
   baseline=set(self.baseline_identities or {})
   changed=any(runner.process_identity(pid)!=ident for pid,ident in (self.baseline_identities or {}).items() if pid in (identities(gs) or {}))
   bad=policy.conflict(gs,selected,owned,baseline) or changed
   if bad and self.stop_time is None:
    cause='QUERY_FAILED' if gs is None else 'LOW_FREE_MEMORY' if gs[0].get('free_mib',0)<2048 else 'NEW_OR_CHANGED_FOREIGN_CONTEXT'
    self.persist(preemption_event={'cause':cause,'utc_unix':time.time(),'snapshot':gs})
   return bad
  runner.stage_conflict=conflict
  super().tick(samples,now)

def main():
 p=argparse.ArgumentParser();p.add_argument('--config',required=True);a=p.parse_args();e=OfficialRunner(a.config)
 def stop(signum,frame):e.shutdown=True
 signal.signal(signal.SIGTERM,stop);signal.signal(signal.SIGINT,stop)
 try:
  while True:
   try:e.tick(policy.query())
   except Exception as exc:
    if e.child:e.shutdown=True;e.request_own_stop()
    e.persist(status='ENGINEERING_NOT_READY',reason=repr(exc));safety.archive_failure(e.path,e.directory/'failed_stages');raise
   if e.state['status'] in ('OFFICIAL_PILOT_EVALUATED_REVIEW_REQUIRED','ENGINEERING_NOT_READY'):break
   if e.shutdown and e.child is None:break
   time.sleep(5 if e.child else e.config['poll_seconds'])
 finally:e.close()
if __name__=='__main__':main()
