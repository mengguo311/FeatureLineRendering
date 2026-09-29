"""Administrative command journal; not scientific behavior."""
import os,sys,time,json,hashlib,subprocess
from pathlib import Path
root=Path(__file__).resolve().parent
label=sys.argv[1];cmd=sys.argv[2:];n=len(list(root.glob('logs/*.log')))+1
(root/'logs').mkdir(exist_ok=True);p=root/'logs'/f'{n:03d}_{label}.log'
start=time.time()
source_before={str(x):hashlib.sha256(x.read_bytes()).hexdigest() for pattern in ['src/direct_curve*','scripts/*direct_curve*.py','tests/test_direct_curve*.py'] for x in Path('.').glob(pattern) if x.is_file()}
with p.open('wb') as f:r=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
row=dict(source_before=source_before,label=label,argv=cmd,environment={k:os.environ.get(k) for k in ['CUDA_VISIBLE_DEVICES','PYTHONPATH','OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','CUBLAS_WORKSPACE_CONFIG']},start=start,seconds=time.time()-start,exit=r.returncode,log=str(p),log_sha256=sha(p),sources={str(x):sha(x) for pattern in ['src/direct_curve*.py','src/direct_curve*.cpp','scripts/*direct_curve*.py','tests/test_direct_curve*.py'] for x in Path('.').glob(pattern)})
with (root/'JOURNAL.jsonl').open('a') as f:f.write(json.dumps(row,sort_keys=True)+'\n')
print(json.dumps(row));print(p.read_text()[-5000:]);sys.exit(r.returncode)
