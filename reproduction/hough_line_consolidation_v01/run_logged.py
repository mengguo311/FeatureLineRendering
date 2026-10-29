"""Usage: python -B run_logged.py LABEL SCRIPT [ARGS...]."""
from pilotio import *
import subprocess
label=sys.argv[1]; args=[sys.executable,'-B',str(CODE/sys.argv[2]),*sys.argv[3:]]
log=OUT/'logs'/f'{label}.log'; log.parent.mkdir(exist_ok=True)
assert not log.exists(), 'Never overwrite an earlier run receipt'
start=time.monotonic(); utc=now()
with log.open('w') as f:
    p=subprocess.run(args,stdout=f,stderr=subprocess.STDOUT,cwd=CODE)
js(OUT/'logs'/f'{label}.json',dict(command=args,cwd=str(CODE),start_utc=utc,end_utc=now(),seconds=time.monotonic()-start,returncode=p.returncode,log=str(log),affinity=sorted(os.sched_getaffinity(0))))
print(log.read_text()[-14000:]); print('RETURN_CODE',p.returncode,flush=True)
sys.exit(p.returncode)
