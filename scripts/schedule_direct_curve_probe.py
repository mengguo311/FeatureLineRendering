#!/usr/bin/env python3
"""Durable scene-stage runner. No retries/refits of partial or sealed fits."""
import argparse,datetime,fcntl,hashlib,json,os,signal,subprocess,sys,tempfile,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
OUT=ROOT/'out/direct_curve_global_fit_probe';ART=ROOT/'artifacts/direct_curve_global_fit_probe'
PYTHON='/home/u00134/bin/miniconda3/envs/vfsdgs/bin/python'

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()

def atomic_json(path,value):
    """Publish a complete immutable file atomically; never replace an existing seal."""
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    fd,tmp=tempfile.mkstemp(prefix='.'+path.name+'.',dir=path.parent)
    try:
        with os.fdopen(fd,'w') as f:
            json.dump(value,f,sort_keys=True,indent=2,allow_nan=False);f.write('\n');f.flush();os.fsync(f.fileno())
        os.link(tmp,path)
        d=os.open(path.parent,os.O_DIRECTORY);os.fsync(d);os.close(d)
    finally:os.unlink(tmp)

def fit_state(path):
    path=Path(path)
    if not path.exists() or not any(path.iterdir()):return 'empty'
    seal=path/'SEAL.json';digest=path/'SEAL.json.sha256'
    if not seal.exists() or not digest.exists():return 'partial'
    value=json.loads(seal.read_text())
    if sha(seal)!=digest.read_text().strip() or len(value['assets'])!=18 or not all(sha(path/(k+'.npz'))==h for k,h in value['assets'].items()):raise ValueError('invalid fit seal')
    return 'sealed'

def schedule(scenes,stage):
    result={s:{} for s in scenes}
    for kind in ['fit','evaluate']:
        for scene in scenes:
            if kind=='evaluate' and not result[scene]['fit']:
                result[scene][kind]=False;continue
            try:result[scene][kind]=bool(stage(scene,kind))
            except Exception as e:
                print(now(),scene,kind,type(e).__name__,str(e),flush=True);result[scene][kind]=False
    return result

class Runner:
    def __init__(self,args):
        self.args=args;self.base=OUT/'scheduler'/args.session/args.run;self.base.mkdir(parents=True,exist_ok=False)
        self.env=dict(os.environ,PYTHONPATH='.:tests',PYTHONDONTWRITEBYTECODE='1',CUDA_VISIBLE_DEVICES=str(args.gpu),CUBLAS_WORKSPACE_CONFIG=':4096:8',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1')
        self.manifest=json.loads((ART/'RESUME_IMPLEMENTATION_V2.json').read_text())
        self.uuid=subprocess.check_output(['nvidia-smi','-i',str(args.gpu),'--query-gpu=uuid','--format=csv,noheader'],text=True).strip()
        atomic_json(self.base/'PROCESS.json',dict(pid=os.getpid(),gpu=args.gpu,uuid=self.uuid,started=now(),run=args.run,session=args.session))
    def status(self,**kw):
        row=dict(time=now(),pid=os.getpid(),run=self.args.run,**kw)
        with (self.base/'EVENTS.jsonl').open('a') as f:f.write(json.dumps(row,sort_keys=True)+'\n');f.flush();os.fsync(f.fileno())
        path=self.base/'STATUS.json';tmp=self.base/'STATUS.pending';tmp.write_text(json.dumps(row,indent=2)+'\n');os.replace(tmp,path)
        print(json.dumps(row),flush=True)
    def verify_sources(self):
        for p,h in self.manifest['files'].items():
            if sha(ROOT/p)!=h:raise RuntimeError('source changed: '+p)
    def remaining(self,scene):
        baseline=json.loads((ART/'RESUME_BUDGET_BASELINE.json').read_text())[scene]
        spent=baseline['charged_seconds'];t=time.time()
        for p in (OUT/'scheduler').glob('*/*/jobs/*/START.json'):
            start=json.loads(p.read_text())
            if start['scene']!=scene:continue
            end=p.parent/'END.json'
            spent+=json.loads(end.read_text())['seconds'] if end.exists() else t-start['epoch']
        return 43200-spent
    def wait_gpu(self):
        while True:
            rows=subprocess.check_output(['nvidia-smi','--query-compute-apps=gpu_uuid,pid','--format=csv,noheader'],text=True)
            if not any(row.split(',')[0].strip()==self.uuid for row in rows.splitlines()):return
            self.status(state='WAIT_GPU',jobs=rows.strip());time.sleep(30)
    def audit(self,trace,output):
        from src.corrected_audit import audit_policy,bootstrap_reads_before_policy
        policy_path=output/'allowlist.json';policy=json.loads(policy_path.read_text());text=trace.read_text();exceptions=[str(ROOT),str(ROOT/'tests')]
        result=audit_policy(text,policy,output,exceptions);result['bootstrap_before_policy']=bootstrap_reads_before_policy(text,policy_path,exceptions)
        result['passed'] &= result['bootstrap_before_policy'];result['trace_sha256']=sha(trace)
        return result
    def execute(self,scene,kind,argv,output,cap):
        self.verify_sources();self.wait_gpu()
        remaining=self.remaining(scene)
        if remaining<=0:raise RuntimeError('COMPUTE_BUDGET_EXHAUSTED '+scene)
        job=self.base/'jobs'/f'{scene}_{kind}';job.mkdir(parents=True,exist_ok=False)
        trace=job/'access.strace';cmd=['strace','-f','-yy','-e','trace=open,openat,openat2,creat','-o',str(trace),PYTHON,*argv]
        started=time.time();atomic_json(job/'START.json',dict(scene=scene,kind=kind,epoch=started,command=cmd,output=str(output),budget_before=remaining))
        with (job/'stdout.log').open('xb') as log:
            proc=subprocess.Popen(cmd,cwd=ROOT,env=self.env,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
            self.status(state='RUNNING',scene=scene,stage=kind,child_pid=proc.pid,job=str(job));timed_out=False
            while proc.poll() is None:
                elapsed=time.time()-started
                # Shared ledger charges concurrent run/rerun wall time together.
                if elapsed>=cap or self.remaining(scene)<=0:
                    timed_out=True;os.killpg(proc.pid,signal.SIGTERM)
                    try:proc.wait(timeout=20)
                    except subprocess.TimeoutExpired:os.killpg(proc.pid,signal.SIGKILL);proc.wait()
                    break
                memory=subprocess.check_output(['nvidia-smi','--query-compute-apps=pid,gpu_uuid,used_memory','--format=csv,noheader,nounits'],text=True).strip()
                self.status(state='RUNNING',scene=scene,stage=kind,child_pid=proc.pid,elapsed_seconds=elapsed,gpu_processes=memory)
                time.sleep(15)
        end=dict(scene=scene,kind=kind,seconds=time.time()-started,exit=proc.returncode,timed_out=timed_out,log_sha256=sha(job/'stdout.log'))
        atomic_json(job/'END.json',end)
        try:audit=self.audit(trace,output)
        except Exception as e:audit=dict(passed=False,error=repr(e))
        atomic_json(job/'AUDIT.json',audit)
        passed=proc.returncode==0 and not timed_out and audit['passed']
        self.status(state='STAGE_COMPLETE' if passed else 'STAGE_FAILED',stage=kind,**end)
        if not passed:return False
        self.verify_sources();return True
    def calibration(self,scene,domain):
        output=self.base/'calibration'/f'{scene}_{domain}'
        ok=self.execute(scene,'calibrate_'+domain,['scripts/calibrate_direct_curve_replay.py','--scene',scene,'--run',self.args.run,'--domain',domain,'--output',str(output)],output,10800)
        return ok and json.loads((output/'RESULT.json').read_text())['passed']
    def stage(self,scene,kind):
        base=OUT/self.args.run/scene;fitdir=base/'fit';output=base/kind
        if kind=='fit':
            state=fit_state(fitdir)
            if state=='sealed':self.status(state='PRESERVED_SEALED_FIT',scene=scene,seal_sha256=sha(fitdir/'SEAL.json'));return True
            if state=='partial':self.status(state='BLOCKED_PARTIAL_FIT_NO_REFIT',scene=scene);return False
            if not self.calibration(scene,'F'):return False
        else:
            if fit_state(fitdir)!='sealed':return False
            if not self.calibration(scene,'all'):return False
            if output.exists() and any(output.iterdir()):
                if (output/'RESULTS.json').exists():raise RuntimeError('existing evaluation requires verification, not overwrite')
                archive=OUT/'engineering'/self.args.session/self.args.run/scene/'evaluate_previous'
                archive.parent.mkdir(parents=True,exist_ok=True)
                if archive.exists():raise FileExistsError(archive)
                inventory={str(p.relative_to(output)):sha(p) for p in output.rglob('*') if p.is_file()}
                atomic_json(archive.parent/'EVALUATION_ARCHIVE.json',dict(original=str(output),files=inventory));output.rename(archive)
                self.status(state='ARCHIVED_PARTIAL_EVALUATION',scene=scene,archive=str(archive))
        ok=self.execute(scene,kind,['scripts/run_direct_curve_probe.py','--scene',scene,'--run',self.args.run,'--stage',kind],output,43200 if kind=='fit' else 10800)
        if not ok:return False
        if kind=='fit':
            if fit_state(fitdir)!='sealed':return False
        else:
            results=json.loads((output/'RESULTS.json').read_text())
            if len(results['arcs'])!=2 or any(a['frames']!=33 for a in results['arcs']):return False
            from scripts.verify_direct_curve_probe import decode_media
            media=decode_media(output,33);atomic_json(self.base/f'{scene}_MEDIA.json',media)
            if not media['passed'] or len(media['videos'])!=2:return False
        inventory={str(p.relative_to(output)):sha(p) for p in output.rglob('*') if p.is_file()}
        atomic_json(self.base/f'{scene}_{kind}_SEAL.json',dict(scene=scene,stage=kind,completed=now(),files=inventory))
        return True

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--run',choices=['run','rerun'],required=True);ap.add_argument('--gpu',type=int,required=True);ap.add_argument('--session',required=True);args=ap.parse_args()
    os.chdir(ROOT);(OUT/'scheduler').mkdir(exist_ok=True)
    with (OUT/'scheduler'/f'gpu{args.gpu}.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        runner=Runner(args);result=schedule(['lego','chair','drums','ficus'],runner.stage)
        atomic_json(runner.base/'COMPLETE.json',dict(passed=all(all(r.values()) for r in result.values()),results=result,completed=now()))
        runner.status(state='COMPLETE',results=result)
        return 0 if all(all(r.values()) for r in result.values()) else 1
if __name__=='__main__':raise SystemExit(main())
