"""Passive CPU observer. Never dispatches, imports CUDA, or increments fake counts."""
import argparse,json,os,sys,time
from pathlib import Path
P=Path(__file__).resolve().parent;sys.path.append(str(P.parents[1]/'stage2'))
from safety import atomic_json,sha256,verify_seal
from pilot_progress import progress
from runner import process_identity

def main():
 p=argparse.ArgumentParser();p.add_argument('--config',required=True);p.add_argument('--once',action='store_true');a=p.parse_args();c=json.loads(Path(a.config).read_text());directory=Path(c['state_dir']);A=Path(c['artifact_dir']);master=A.parent/'MASTER_STATUS.json';cache={}
 while True:
  if not (directory/'runner_state.json').exists():time.sleep(5);continue
  state=json.loads((directory/'runner_state.json').read_text());verified=set()
  for s in ('train','export','tsdf','eval'):
   path=directory/(s+'.seal.json')
   if path.exists():
    digest=sha256(path)
    if cache.get(s)!=digest:
     if not verify_seal(path,s,c['inputs']):continue
     cache[s]=digest
    verified.add(s)
  log=Path(c['model'])/'iteration_loss.jsonl';last=None
  if log.exists():
   with open(log,'rb') as f:
    f.seek(0,2);size=f.tell();f.seek(max(0,size-32768));lines=f.read().splitlines()
   for line in reversed(lines):
    try:last=json.loads(line);break
    except ValueError:continue
  value=progress(state,last['iteration'] if last else 0,verified);now=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime());pids=[]
  if state.get('child_pid'):
   pids.append(state['child_pid'])
   for g in state.get('gpu_snapshot') or []:
    for context in g['contexts']:
     ident=process_identity(context['pid'])
     if ident and ident['uid']==os.getuid() and ident['pgid']==state['child_pid']:pids.append(context['pid'])
  details=dict(value,method_variant='official_code_fix_v01',phase='official_scan24_'+str(state.get('stage')),newbranchstage='OFFICIAL_C24_PILOT',currentdataset='DTU',currentscene='scan24',runner_state_path=str(directory/'runner_state.json'),runner_config_path=a.config,runner_pid=state.get('runner_pid'),selected_gpu_uuid=state.get('selected_gpu_uuid'),childPIDs=sorted(set(pids)),tmux=c['tmux'],last_iteration=last,utc=now,last_event='Passive observer read actual state/iteration and verified new seals',resume_entry=c['launch_script'],observer_tmux='radegs-official-scan24-observer-v02',remaining=['scan24 chain and quality review unless verified','other frozen paper scenes not dispatched','ambiguous protocols/data remain unresolved'])
  atomic_json(A/'STATUS.json',details);atomic_json(Path(c['model']).parent/'PILOT_STATUS.json',details)
  old=json.loads(master.read_text());old.update(details);old['experiment_counts']=value['actual_counts'];atomic_json(master,old)
  for f in A.glob('experiments/*/STATUS.json'):
   e=json.loads(f.read_text());e.update(status=state['status'],train_started=value['actual_counts']['train_started']>0,verified_stages=sorted(verified),actual_counts=value['actual_counts'],scientificdone=False,utc=now);atomic_json(f,e)
  if a.once or state['status'] in ('ENGINEERING_NOT_READY','OFFICIAL_PILOT_EVALUATED_REVIEW_REQUIRED'):break
  time.sleep(30)
if __name__=='__main__':main()
