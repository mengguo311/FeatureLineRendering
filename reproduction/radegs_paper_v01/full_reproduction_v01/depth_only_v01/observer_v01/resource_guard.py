"""Independent own-run disk guard; no CUDA imports or foreign process signals."""
import argparse,json,os,shutil,signal,time
from pathlib import Path
G=1024**3

def reserve_ok(root_free,hdd_free):
 return isinstance(root_free,int) and isinstance(hdd_free,int) and root_free>=10*G and hdd_free>=50*G

def same_owner_identity(now,expected,uid):
 return now is not None and now==expected and now['uid']==uid

def identity(pid):
 try:
  p=Path('/proc')/str(pid);s=(p/'stat').read_text().rsplit(')',1)[1].split()
  if s[0]=='Z':return None
  return {'uid':p.stat().st_uid,'start_ticks':s[19],'pgid':int(s[2])}
 except (OSError,IndexError,ValueError):return None

def atomic(path,value):
 path=Path(path);tmp=path.with_suffix('.tmp')
 with tmp.open('w') as f:json.dump(value,f,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
 os.replace(tmp,path)

def monitor(config):
 c=json.loads(Path(config).read_text());out=Path(c['output']);expected=c['runner_identity'];uid=os.getuid();pid=c['runner_pid']
 assert expected['uid']==uid
 while True:
  now=identity(pid)
  if not same_owner_identity(now,expected,uid):
   atomic(out,{'status':'OWN_RUNNER_EXITED_OR_IDENTITY_CHANGED','no_signal':True,'runner_pid':pid,'utc_unix':time.time()});return
  error=None
  try:root_free=shutil.disk_usage('/').free;hdd_free=shutil.disk_usage(c['hdd_path']).free
  except OSError as exc:root_free=hdd_free=None;error=repr(exc)
  state={'status':'MONITORING','runner_pid':pid,'runner_identity':expected,'root_free_bytes':root_free,'hdd_free_bytes':hdd_free,'utc_unix':time.time(),'query_error':error,'only_owned_supervisor_signal':True,'guard_pid':os.getpid()}
  if not reserve_ok(root_free,hdd_free):
   state.update(status='LOW_DISK_STOP_REQUESTED',cause='SPACE_QUERY_FAILED' if error else 'DISK_RESERVE_VIOLATION')
   atomic(out,state)
   # Recheck kernel start ticks and UID immediately before signalling only our
   # supervisor. Its proven shutdown path checkpoints its own stage group.
   if same_owner_identity(identity(pid),expected,uid):
    try:os.kill(pid,signal.SIGTERM)
    except ProcessLookupError:pass
   return
  atomic(out,state);time.sleep(15)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--config',required=True);a=p.parse_args();monitor(a.config)
