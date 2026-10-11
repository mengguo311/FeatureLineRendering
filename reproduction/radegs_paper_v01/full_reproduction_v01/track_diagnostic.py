"""Passive CPU state mirror; never launches any scientific job."""
import datetime
import fcntl
import json
import os
from pathlib import Path
import sys
import time

def project(master,state,expected_path):
    if master.get('runner_state_path')!=expected_path:return None
    d=dict(master);status=state['status']
    d.update(status=status,childPIDs=[state['child_pid']] if state.get('child_pid') else [],
        runner_pid=state.get('runner_pid'),selected_gpu_uuid=state.get('selected_gpu_uuid'),
        scientificdone=False,full_suite_completed=False,
        runner_last_updated_unix=state.get('updated_unix'),utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
    if status=='DIAGNOSTIC_COMPLETE':
        d.update(status='DIAGNOSTIC_EVIDENCE_READY_REVIEW_REQUIRED',
            last_event='Read-only GPU checkpoint diagnostic sealed; not mesh/evaluation success',
            next_action='Verify diagnostic seal and inspect 15k/30k visuals and gradients; continue opacity-collapse diagnosis before another scene')
    elif status=='ENGINEERING_NOT_READY':
        d.update(last_event='Diagnostic stage failed: '+str(state.get('reason')),
            next_action='Inspect new failed stage/log and preserve before/after evidence; no automatic scientific retry')
    elif status=='RUNNING':d['last_event']='Read-only checkpoint diagnostic actually running under GPU0 shared gate'
    elif status.startswith('WAITING_'):d['last_event']='Diagnostic runner waiting; no GPU child; full reproduction still incomplete'
    return d

def main():
    hdd=Path('/mnt/hdd1/u00134/radegs_paper_reproduction_v01/full_reproduction_v01')
    root=Path(__file__).resolve().parents[3]
    master=root/'artifacts/radegs_paper_reproduction_v01/full_reproduction_v01/MASTER_STATUS.json'
    path=hdd/'checkpoint_diagnostic/state/runner_state.json'
    sys.path.insert(0,str(root/'reproduction/radegs_paper_v01/stage2'))
    from safety import atomic_json
    with (hdd/'checkpoint_diagnostic/state/tracker.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        previous=None
        while True:
            state=json.loads(path.read_text());m=json.loads(master.read_text())
            d=project(m,state,str(path))
            if d is None:return
            d['state_tracker_pid']=os.getpid()
            key=(state['status'],state.get('child_pid'),state.get('updated_unix'))
            if key!=previous:
                atomic_json(master,d);previous=key
            if state['status'] in ('DIAGNOSTIC_COMPLETE','ENGINEERING_NOT_READY'):
                print(json.dumps({'status':d['status'],'scientificdone':False}),flush=True);return
            if not Path('/proc',str(state['runner_pid'])).exists():
                d.update(status='DIAGNOSTIC_SUPERVISOR_EXITED_REVIEW_REQUIRED',next_action='Inspect process identity and state; do not infer task completion from exit')
                atomic_json(master,d);return
            time.sleep(5)

if __name__=='__main__':main()
