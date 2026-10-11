"""Passive state mirror for this precision diagnostic; no scientific dispatch."""
import fcntl
import json
import os
from pathlib import Path
import sys
import time

ROOT=Path(__file__).resolve().parents[4]
sys.path.insert(0,str(ROOT/'reproduction/radegs_paper_v01/full_reproduction_v01'))
sys.path.insert(0,str(ROOT/'reproduction/radegs_paper_v01/stage2'))
from track_diagnostic import project
from safety import atomic_json


def main():
    base=Path('/mnt/hdd1/u00134/radegs_paper_reproduction_v01/full_reproduction_v01/precision_v01/corrected_result_audit_v01/gradient_audit_v02/state')
    state=base/'runner_state.json'
    master=ROOT/'artifacts/radegs_paper_reproduction_v01/full_reproduction_v01/MASTER_STATUS.json'
    with (base/'mirror.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        previous=None
        while True:
            s=json.loads(state.read_text());m=json.loads(master.read_text());d=project(m,s,str(state))
            if d is None:return
            d['state_tracker_pid']=os.getpid()
            if s['status']=='ENGINEERING_NOT_READY':
                d['last_event']='All-view upstream/VJP diagnostic failed; preserve exact tensor evidence, do not infer full reproduction completion'
                d['next_action']='Verify probe.json and preserved gradients; keep production/native unchanged unless a real defect is demonstrated'
            key=(s['status'],s.get('child_pid'),s.get('updated_unix'))
            if key!=previous:atomic_json(master,d);previous=key
            if s['status'] in ['ENGINEERING_NOT_READY','DIAGNOSTIC_COMPLETE']:return
            if not Path('/proc',str(s['runner_pid'])).exists():
                d.update(status='SUPERVISOR_EXITED_REVIEW_REQUIRED',next_action='Inspect state/process; do not infer completion')
                atomic_json(master,d);return
            time.sleep(5)

if __name__=='__main__':main()
