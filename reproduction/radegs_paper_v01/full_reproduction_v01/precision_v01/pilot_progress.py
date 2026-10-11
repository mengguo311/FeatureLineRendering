"""Passive corrected-pilot progress. Never dispatches or claims full replication."""
import argparse
import fcntl
import json
import os
import sys
import time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
from track_diagnostic import project as previous_project
ROOT=Path(__file__).resolve().parents[4]
sys.path.insert(0,str(ROOT/'reproduction/radegs_paper_v01/stage2'))
from safety import atomic_json,verify_seal,sha256


def project(master,state,expected_path,verified,iteration):
    result=previous_project(master,state,expected_path)
    if result is None:return None
    result.update(verified_stages=verified,completed_iteration_observed=iteration,
                  scientificdone=False,full_suite_completed=False)
    if state['status']=='PILOT_CHAIN_COMPLETE':
        if verified==['smoke','train','export','tsdf','eval']:
            result.update(status='PILOT_CHAIN_SEALED_REVIEW_REQUIRED',last_event='Corrected scan24 stages sealed; actual metrics/visuals need review',
                          next_action='Verify official metrics/units/visuals, compare with paper, then advance frozen full-suite protocol')
        else:
            result.update(status='ENGINEERING_NOT_READY',last_event='Runner claimed pilot completion but output seals do not verify',
                          next_action='Inspect evidence mismatch; do not advance suite')
    elif state['status']=='RUNNING':
        result['last_event']='Corrected scan24 stage actually running: '+str(state.get('stage'))
    elif state['status'].startswith('WAITING_'):
        result['last_event']='Corrected scan24 waiting for actual-free GPU0 admission; verified checkpoint retained'
    return result


def last_iteration(model):
    path=Path(model)/'iteration_loss.jsonl'
    if not path.exists():return 0
    with path.open('rb') as f:
        f.seek(0,2);end=f.tell();f.seek(max(0,end-65536));data=f.read()
    lines=data.split(b'\n')[:-1]
    for line in reversed(lines):
        try:return int(json.loads(line)['iteration'])
        except (ValueError,KeyError,TypeError):continue
    return 0


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--config',required=True);args=ap.parse_args()
    config_path=Path(args.config);c=json.loads(config_path.read_text());digest=sha256(config_path)
    state_path=Path(c['state_dir'])/'runner_state.json'
    master=ROOT/'artifacts/radegs_paper_reproduction_v01/full_reproduction_v01/MASTER_STATUS.json'
    cached={}
    with (Path(c['state_dir'])/'progress_mirror.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        while True:
            s=json.loads(state_path.read_text());m=json.loads(master.read_text())
            verified=[]
            for stage in ['smoke','train','export','tsdf','eval']:
                seal=Path(c['state_dir'])/(stage+'.seal.json')
                if seal.exists():
                    stamp=seal.stat().st_mtime_ns
                    if cached.get(stage,(None,False))[0]!=stamp:
                        cached[stage]=(stamp,verify_seal(seal,stage,c['inputs']))
                    if cached[stage][1]:verified.append(stage)
            result=project(m,s,str(state_path),verified,last_iteration(c['model']))
            if result is None:return
            result['state_tracker_pid']=os.getpid()
            if sha256(config_path)!=digest:
                result.update(status='ENGINEERING_NOT_READY',last_event='Pilot config changed during passive observation')
            atomic_json(master,result)
            if result['status'] in ['ENGINEERING_NOT_READY','PILOT_CHAIN_SEALED_REVIEW_REQUIRED']:return
            if not Path('/proc',str(s['runner_pid'])).exists():
                result.update(status='SUPERVISOR_EXITED_REVIEW_REQUIRED',next_action='Inspect own state/checkpoint and resume only verified inputs')
                atomic_json(master,result);return
            time.sleep(5)


if __name__=='__main__':main()
