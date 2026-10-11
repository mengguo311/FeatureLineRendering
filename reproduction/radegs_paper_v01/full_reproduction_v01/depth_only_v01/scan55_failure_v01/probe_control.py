"""Reuse existing shared GPU supervision; only a bounded diagnostic is enabled."""
import argparse,json,signal,sys,time
from pathlib import Path
P=Path(__file__).resolve().parent;sys.path.insert(0,str(P.parent/'runner_v02'))
import control
from probe_scope import validate
control.validate_scope=validate;control.runner.validate_config_scope=validate
class Probe(control.OfficialRunner):
 def pending_stage(self):
  validate(self.config)
  return None if control.safety.verify_seal(self.directory/'smoke.seal.json','smoke',self.config['inputs']) else 'smoke'
 def persist(self,**updates):
  if updates.get('status')=='PILOT_CHAIN_COMPLETE':updates.update(status='BOUNDED_REPLAY_COMPLETE',scientificdone=False,depth_package_verified=False,depth_review_passed=False,diagnostic_only=True)
  super().persist(**updates)
def main():
 p=argparse.ArgumentParser();p.add_argument('--config',required=True);a=p.parse_args();e=Probe(a.config)
 def stop(*a):e.shutdown=True
 signal.signal(signal.SIGTERM,stop);signal.signal(signal.SIGINT,stop)
 try:
  while True:
   try:e.tick(control.policy.query())
   except Exception as exc:
    if e.child:e.shutdown=True;e.request_own_stop()
    e.persist(status='ENGINEERING_NOT_READY',reason=repr(exc));control.safety.archive_failure(e.path,e.directory/'failed_stages');raise
   if e.state['status'] in ('ENGINEERING_NOT_READY','BOUNDED_REPLAY_COMPLETE'):break
   if e.shutdown and not e.child:break
   time.sleep(5 if e.child else e.config['poll_seconds'])
 finally:e.close()
if __name__=='__main__':main()
