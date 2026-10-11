"""Passive exact15k checkpoint retention; stdlib only, no CUDA or train mutation."""
import argparse,fcntl,json,os,shutil,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[4];sys.path.append(str(ROOT/'reproduction/radegs_paper_v01/stage2'))
from safety import atomic_json,sha256,verify_seal

def preserve(desc,out,provenance):
 if desc['completed_iteration']!=15000 or desc['provenance']!=provenance:raise ValueError('wrong boundary or provenance')
 out=Path(out);out.mkdir(parents=True,exist_ok=True);seal=out/'checkpoint_15000.seal.json';receipt=out/'receipt.json'
 if seal.exists():
  if not verify_seal(seal,'boundary_checkpoint',provenance):raise ValueError('existing snapshot seal mismatch')
  return json.loads(receipt.read_text())
 src=Path(desc['path']);dest=out/'checkpoint_15000.pt';temp=out/'checkpoint_15000.partial'
 if dest.exists() or temp.exists():raise ValueError('unsealed prior copy requires explicit review')
 # Opening first retains an immutable generation even if the training writer
 # subsequently unlinks its old pathname. Never write to the training model.
 with src.open('rb') as source,temp.open('xb') as target:
  shutil.copyfileobj(source,target,8*1024**2);target.flush();os.fsync(target.fileno())
 if sha256(temp)!=desc['sha256']:raise ValueError('checkpoint hash mismatch; partial retained, no seal')
 os.replace(temp,dest)
 r={'completed_iteration':15000,'original_descriptor':desc,'retained_file':str(dest),'sha256':sha256(dest),'operation':'byte-for-byte copy only; no torch load or optimizer step','scientificdone':False}
 atomic_json(receipt,r)
 # A separate observational seal; never a training-stage completion seal.
 atomic_json(seal,{'schema':1,'stage':'boundary_checkpoint','inputs':provenance,'outputs':{str(p.resolve()):sha256(p) for p in [dest,receipt]},'sealed_unix':time.time()})
 return r

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--config',required=True);args=ap.parse_args();cp=Path(args.config);c=json.loads(cp.read_text());configsha=sha256(cp)
 state=Path(c['state_dir']);out=state.parent/'boundary_checkpoint';out.mkdir(exist_ok=True);status=out/'status.json';checkpoint=Path(c['model'])/'restart.json'
 with (out/'observer.lock').open('a') as lock:
  fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
  if (out/'checkpoint_15000.seal.json').exists():
   if not verify_seal(out/'checkpoint_15000.seal.json','boundary_checkpoint',c['inputs']):raise ValueError('retained boundary seal changed')
   atomic_json(status,{'status':'BOUNDARY_CHECKPOINT_SEALED','pid':os.getpid(),'config_sha256':configsha,'scientificdone':False});return
  while True:
   if sha256(cp)!=configsha:raise ValueError('config changed')
   desc=json.loads(checkpoint.read_text()) if checkpoint.exists() else None
   if desc and desc['completed_iteration']==15000:
    src=Path(desc['path']).resolve()
    if src.parent!=Path(c['model']).resolve() or not src.name.startswith('restart.json.generation-'):raise ValueError('unexpected checkpoint source')
    if shutil.disk_usage('/').free<10*1024**3 or shutil.disk_usage(out).free-src.stat().st_size<50*1024**3:raise ValueError('snapshot disk reserve failed')
    preserve(desc,out,c['inputs']);atomic_json(status,{'status':'BOUNDARY_CHECKPOINT_SEALED','pid':os.getpid(),'config_sha256':configsha,'scientificdone':False});return
   if desc and desc['completed_iteration']>15000:
    atomic_json(status,{'status':'MISSED_BOUNDARY_REVIEW_REQUIRED','pid':os.getpid(),'last_iteration':desc['completed_iteration'],'scientificdone':False});return
   s=json.loads((state/'runner_state.json').read_text());atomic_json(status,{'status':'WAITING_FOR_15000_CHECKPOINT','pid':os.getpid(),'last_iteration':desc['completed_iteration'] if desc else 0,'config_sha256':configsha,'training_unchanged':True,'scientificdone':False})
   if s['status']=='ENGINEERING_NOT_READY':return
   if not Path('/proc',str(s['runner_pid'])).exists():return
   time.sleep(2)
if __name__=='__main__':
 try:main()
 except Exception as exc:
  # Preserve an explicit observer failure independently of the scientific run.
  if '--config' in sys.argv:
   c=json.loads(Path(sys.argv[sys.argv.index('--config')+1]).read_text())
   atomic_json(Path(c['state_dir']).parent/'boundary_checkpoint/status.json',{'status':'SNAPSHOT_FAILED_REVIEW_REQUIRED','error':repr(exc),'pid':os.getpid(),'scientificdone':False})
  raise
