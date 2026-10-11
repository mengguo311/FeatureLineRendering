"""Passive per-scene state mirror, never dispatches another scene."""
import argparse,datetime,fcntl,json,os,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[4]
sys.path.append(str(ROOT/'reproduction/radegs_paper_v01/stage2'))
from safety import atomic_json,sha256,verify_seal

def project(master,state,verified,iteration):
 if master.get('runner_config_path')!=state.get('config'):return None
 r=dict(master);r.update(status=state['status'],childPIDs=[state['child_pid']] if state.get('child_pid') else [],runner_pid=state.get('runner_pid'),selected_gpu_uuid=state.get('selected_gpu_uuid'),verified_stages=verified,completed_iteration_observed=iteration,runner_last_updated_unix=state.get('updated_unix'),scientificdone=False,full_suite_completed=False,utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
 if state['status']=='PILOT_CHAIN_COMPLETE':
  if verified==['smoke','train','export','tsdf','eval']:r.update(status='SCENE_CHAIN_SEALED_REVIEW_REQUIRED',last_event='All scene stage seals verified; metrics, visuals and paper comparison need review',next_action='Audit actual official result and visuals, update suite metric/counts, then prepare next frozen entry')
  else:r.update(status='ENGINEERING_NOT_READY',last_event='Completion state does not match verified seals',next_action='Inspect hash/seal discrepancy; do not advance scene')
 elif state['status']=='ENGINEERING_NOT_READY':r.update(last_event='Scene stage failed: '+str(state.get('reason')),next_action='Preserve failure evidence, diagnose; no automatic scientific retry')
 elif state['status']=='RUNNING':r['last_event']='Actual scene stage running: '+str(state.get('stage'))
 elif state['status'].startswith('WAITING_'):r['last_event']='GPU0 admission pending; no new scene or alternate method dispatched'
 return r

def last_iteration(model):
 p=Path(model)/'iteration_loss.jsonl'
 if not p.exists():return 0
 with p.open('rb') as f:f.seek(0,2);end=f.tell();f.seek(max(0,end-65536));lines=f.read().split(b'\n')[:-1]
 for line in reversed(lines):
  try:return int(json.loads(line)['iteration'])
  except (ValueError,KeyError,TypeError):continue
 return 0

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--config',required=True);args=ap.parse_args();path=Path(args.config);c=json.loads(path.read_text());digest=sha256(path)
 directory=Path(c['state_dir']);master=ROOT/'artifacts/radegs_paper_reproduction_v01/full_reproduction_v01/MASTER_STATUS.json';scene_status=master.parent/'experiments'/c['entry_id']/'STATUS.json';cached={}
 with (directory/'tracker.lock').open('a') as lock:
  fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
  while True:
   state_path=directory/'runner_state.json'
   if not state_path.exists():time.sleep(1);continue
   s=json.loads(state_path.read_text());m=json.loads(master.read_text());verified=[]
   for stage in ['smoke','train','export','tsdf','eval']:
    seal=directory/(stage+'.seal.json')
    if seal.exists():
     stamp=seal.stat().st_mtime_ns
     if cached.get(stage,(None,False))[0]!=stamp:cached[stage]=(stamp,verify_seal(seal,stage,c['inputs']))
     if cached[stage][1]:verified.append(stage)
   r=project(m,s,verified,last_iteration(c['model']))
   if r is None:return
   r['state_tracker_pid']=os.getpid()
   if sha256(path)!=digest:r.update(status='ENGINEERING_NOT_READY',last_event='Config changed during observation')
   atomic_json(master,r)
   row=json.loads(scene_status.read_text());row.update(status=r['status'],verified_stages=verified,completed_iteration_observed=r['completed_iteration_observed'],runner_state_path=str(state_path),scientificdone=False,execution_chain_completed=False,utc=r['utc']);atomic_json(scene_status,row)
   if r['status'] in ['SCENE_CHAIN_SEALED_REVIEW_REQUIRED','ENGINEERING_NOT_READY']:return
   if not Path('/proc',str(s['runner_pid'])).exists():
    r.update(status='SUPERVISOR_EXITED_REVIEW_REQUIRED',next_action='Inspect own process identity/state; resume only verified configuration');atomic_json(master,r);return
   time.sleep(5)
if __name__=='__main__':main()
