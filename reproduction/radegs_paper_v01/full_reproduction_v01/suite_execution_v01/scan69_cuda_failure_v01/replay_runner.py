"""Shared GPU0, common own lock, bounded synchronous replay only; never dispatch training."""
import argparse,json,signal,sys,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent.parent/'runtime'))
import suite_runner
from safety import verify_seal,archive_failure
from suite_scope import validate_config_scope

def validate_probe(c):
 validate_config_scope(c)
 if c['inputs'].get('scene_entry')!=c['entry_id']:raise ValueError('resolution entry provenance mismatch')
 if c.get('synchronous_replay_only') is not True or c['resolution_divisor']!=2 or set(c['stage_commands'])!={'smoke'} or any(k in c for k in ['train_command','eval_command','tsdf_command']):raise ValueError('one bounded synchronous replay only; no training or evaluation dispatch')

class ReplayRunner(suite_runner.PilotRunner):
 def __init__(self,path,*args,**kwargs):
  validate_probe(json.loads(Path(path).read_text()));super().__init__(path,*args,**kwargs)
 def pending_stage(self):
  validate_probe(self.config)
  return None if verify_seal(self.directory/'smoke.seal.json','smoke',self.config['inputs']) else 'smoke'
 def persist(self,**updates):
  if updates.get('status')=='PILOT_CHAIN_COMPLETE':updates.update(status='CUDA_REPLAY_DIAGNOSTIC_COMPLETE',pilot_evaluation_verified=False,synchronous_replay_only=True,scientificdone=False)
  super().persist(**updates)

def main():
 p=argparse.ArgumentParser();p.add_argument('--config',required=True);args=p.parse_args();e=ReplayRunner(args.config,query=suite_runner.policy.query)
 assert e.config['allowed_gpu_uuids']==[suite_runner.policy.GPU]
 def stop(signum,frame):e.shutdown=True
 signal.signal(signal.SIGTERM,stop);signal.signal(signal.SIGINT,stop)
 try:
  while True:
   try:e.tick(suite_runner.policy.query())
   except Exception as exc:
    if e.child:e.shutdown=True;e.request_own_stop()
    e.persist(status='ENGINEERING_NOT_READY',reason=repr(exc));archive_failure(e.path,e.directory/'failed_stages');raise
   if e.state['status'] in ['CUDA_REPLAY_DIAGNOSTIC_COMPLETE','ENGINEERING_NOT_READY']:break
   if e.shutdown and e.child is None:break
   time.sleep(5 if e.child else e.config['poll_seconds'])
 finally:e.close()
if __name__=='__main__':main()
