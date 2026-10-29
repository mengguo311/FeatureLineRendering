from runtime import *
import subprocess, signal
label=sys.argv[1]; script=CODE/sys.argv[2];args=[sys.executable,'-B',str(script),*sys.argv[3:]]
log=OUT/'logs'/f'{label}.log'; receipt=log.with_suffix('.json');log.parent.mkdir(exist_ok=True)
assert not log.exists(), 'Never overwrite previous exits'
start=time.monotonic();r=dict(label=label,command=args,start_utc=now(),returncode=None,status='RUNNING')
r['code_sha256']={p.name:sha(p) for p in sorted(CODE.glob('*.py'))}
js(receipt,r)
with log.open('w') as f:
    child=subprocess.Popen(args,stdout=f,stderr=subprocess.STDOUT,cwd=CODE)
    r['child_pid']=child.pid;js(receipt,r)
    def interrupted(signum,frame):
        r.update(status='WRAPPER_SIGNALLED',wrapper_signal=signum,returncode=child.poll(),end_utc=now(),seconds=time.monotonic()-start)
        js(receipt,r)
        raise SystemExit(128+signum)
    signal.signal(signal.SIGTERM,interrupted)
    signal.signal(signal.SIGINT,interrupted)
    try:
        code=child.wait(timeout=max(1,DEADLINE-time.time()))
    except subprocess.TimeoutExpired:
        child.terminate()
        try: code=child.wait(timeout=5)
        except subprocess.TimeoutExpired: child.kill(); code=child.wait()
        r['time_bound_termination']=True
    except BaseException:
        if 'wrapper_signal' not in r:r.update(status='PARENT_INTERRUPTED_CHILD_STATUS_UNKNOWN',end_utc=now())
        js(receipt,r);raise
r.update(returncode=code,status='EXITED',end_utc=now(),seconds=time.monotonic()-start);js(receipt,r)
print(log.read_text()[-12000:]); print('CHILD_RETURN_CODE',code,flush=True)
sys.exit(code if code>=0 else 128-code)
