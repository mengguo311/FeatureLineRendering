"""Single read-only checkpoint diagnosis; no training or suite dispatch."""
import sys
import argparse
import signal
import time
import shutil
from pathlib import Path
sys.path.insert(0,'/mnt/hdd1/u00134/radegs_paper_reproduction_v01/stage2/shared')
from shared_runner import SharedRunner,can_start,query,GPU
import runner
import safety
# Register a distinct evidence type in this diagnostic process only. The frozen
# five-stage runner files and old seals are unchanged.
safety.STAGES=tuple(safety.STAGES)+('checkpoint_diagnostic',)

class DiagnosticRunner(SharedRunner):
    def pending_stage(self):
        if set(self.config['stage_commands'])!={'checkpoint_diagnostic'}:
            raise ValueError('read-only diagnostic scope only')
        return None if safety.verify_seal(self.directory/'checkpoint_diagnostic.seal.json',
            'checkpoint_diagnostic',self.config['inputs']) else 'checkpoint_diagnostic'

    def persist(self,**updates):
        if updates.get('status')=='PILOT_CHAIN_COMPLETE':
            updates.update(status='DIAGNOSTIC_COMPLETE',pilot_evaluation_verified=False,
                           diagnostic_only=True,scientificdone=False)
        super().persist(**updates)

def main():
    p=argparse.ArgumentParser();p.add_argument('--config',required=True);args=p.parse_args()
    safety.is_idle=can_start;runner.is_idle=can_start;runner.query_gpus=query
    hdd=Path('/mnt/hdd1/u00134/radegs_paper_reproduction_v01')
    e=DiagnosticRunner(args.config,query=query,space_check=lambda:shutil.disk_usage('/').free>=10*1024**3
        and shutil.disk_usage(hdd).free>=50*1024**3)
    assert e.config['allowed_gpu_uuids']==[GPU]
    def stop(signum,frame):e.shutdown=True
    signal.signal(signal.SIGTERM,stop);signal.signal(signal.SIGINT,stop)
    try:
        while True:
            try:e.tick(query())
            except Exception as exc:
                if e.child:e.shutdown=True;e.request_own_stop()
                e.persist(status='ENGINEERING_NOT_READY',reason=repr(exc))
                safety.archive_failure(e.path,e.directory/'failed_stages');raise
            if e.state['status'] in ('DIAGNOSTIC_COMPLETE','ENGINEERING_NOT_READY'):break
            if e.shutdown and e.child is None:break
            time.sleep(5 if e.child else e.config['poll_seconds'])
    finally:e.close()

if __name__=='__main__':main()
