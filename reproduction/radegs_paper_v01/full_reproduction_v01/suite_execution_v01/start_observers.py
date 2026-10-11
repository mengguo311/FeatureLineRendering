"""Start passive observers only after actual own supervisor publishes its PID."""
import argparse,json,os,shlex,subprocess,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent/'runtime'))
sys.path.append(str(Path(__file__).resolve().parents[2]/'stage2'))
from runner import process_identity
from safety import atomic_json,sha256

def ready(state,digest,uid,identity):
 p=identity(state.get('runner_pid')) if state.get('runner_pid') else None
 return bool(p and p['uid']==uid and state.get('config_sha256')==digest and state.get('status') in ['WAITING_FOR_LOW_LOAD_GPU','RUNNING','STAGE_SEALED','ADOPTED_OWN_STAGE'])

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--config',type=Path,required=True);args=ap.parse_args();c=json.loads(args.config.read_text());directory=Path(c['state_dir']).parent
 s=json.loads((directory/'state/runner_state.json').read_text());assert ready(s,sha256(args.config),os.getuid(),process_identity),'wait for actual own live runner; do not launch passive observers yet'
 sessions={}
 for key in ['tracker','boundary_observer']:
  name='radegs-'+c['scene']+'-'+key.replace('_','-')+'-ready-v01';script=directory/'launch'/(key+'.sh');assert script.exists()
  assert subprocess.run(['tmux','has-session','-t',name],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL).returncode!=0
  subprocess.run(['tmux','new-session','-d','-s',name,'exec /bin/bash '+shlex.quote(str(script))],check=True);sessions[key]=name
 atomic_json(directory/'launch/OBSERVERS_ADMITTED.json',{'config_sha256':sha256(args.config),'actual_supervisor_pid':s['runner_pid'],'actual_supervisor_identity':process_identity(s['runner_pid']),'sessions':sessions,'scientificdone':False})
if __name__=='__main__':main()
