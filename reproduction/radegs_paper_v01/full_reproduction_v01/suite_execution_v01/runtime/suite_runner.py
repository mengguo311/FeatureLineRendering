"""One frozen DTU half30k entry with actual-free shared GPU0 admission and 50-GiB reserve.

Reuses the existing verified stage/checkpoint/seal machine. A failed scientific
stage stops at ENGINEERING_NOT_READY; resource preemption preserves checkpoints.
"""
import argparse
from pathlib import Path
import shutil
import signal
import sys
import time
sys.path.insert(0,str(Path(__file__).resolve().parent))
sys.path.append(str(Path(__file__).resolve().parents[3]/'stage2'))
sys.path.append(str(Path(__file__).resolve().parents[2]/'precision_v01'))
import runner
import shared_runner
import runner
import safety
import strict_shared_policy as policy

shared_runner.can_start=policy.can_start
shared_runner.conflict=policy.conflict
shared_runner.query=policy.query
safety.is_idle=policy.can_start
runner.is_idle=policy.can_start
runner.query_gpus=policy.query


class PilotRunner(shared_runner.SharedRunner):
    def __init__(self,config,*args,**kwargs):
        kwargs.setdefault('space_check',lambda:shutil.disk_usage('/').free>=10*1024**3
                          and shutil.disk_usage('/mnt/hdd1/u00134/radegs_paper_reproduction_v01').free>=50*1024**3)
        super().__init__(config,*args,**kwargs)


def main():
    p=argparse.ArgumentParser();p.add_argument('--config',required=True);args=p.parse_args()
    e=PilotRunner(args.config,query=policy.query)
    assert e.config['allowed_gpu_uuids']==[policy.GPU]
    def stop(signum,frame):e.shutdown=True
    signal.signal(signal.SIGTERM,stop);signal.signal(signal.SIGINT,stop)
    try:
        while True:
            try:e.tick(policy.query())
            except Exception as exc:
                if e.child:e.shutdown=True;e.request_own_stop()
                e.persist(status='ENGINEERING_NOT_READY',reason=repr(exc))
                safety.archive_failure(e.path,e.directory/'failed_stages');raise
            if e.state['status'] in ('PILOT_CHAIN_COMPLETE','ENGINEERING_NOT_READY'):break
            if e.shutdown and e.child is None:break
            time.sleep(5 if e.child else e.config['poll_seconds'])
    finally:e.close()


if __name__=='__main__':main()
