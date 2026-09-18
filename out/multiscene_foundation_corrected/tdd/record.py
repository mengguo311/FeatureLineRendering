"""Record real test commands, statuses and source identities without overwriting."""
import datetime, hashlib, json, os
from pathlib import Path
import subprocess, sys, time
root=Path(__file__).resolve().parents[1]
label,phase,*tests=sys.argv[1:]
log=root/'tdd'/f'{label}_{phase}.txt'
env=os.environ.copy();env.update(PYTHONPATH='.:tests',CUDA_VISIBLE_DEVICES='1',OMP_NUM_THREADS='4',OPENBLAS_NUM_THREADS='4',MKL_NUM_THREADS='4',PYTHONDONTWRITEBYTECODE='1')
command=[sys.executable,'-m','unittest',*tests]
start=datetime.datetime.now(datetime.timezone.utc).isoformat();tick=time.monotonic()
with log.open('xb') as stream:r=subprocess.run(command,env=env,stdout=stream,stderr=subprocess.STDOUT)
record=dict(label=label,phase=phase,command=command,env={k:env[k] for k in ['PYTHONPATH','CUDA_VISIBLE_DEVICES','OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','PYTHONDONTWRITEBYTECODE']},start_utc=start,elapsed_seconds=time.monotonic()-tick,exit_code=r.returncode,log=str(log.relative_to(root)),source_hashes={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for pattern in ['src/corrected*','tests/test_corrected*'] for p in Path('.').glob(pattern) if p.is_file()})
with (root/'tdd/commands.jsonl').open('a') as f:f.write(json.dumps(record,sort_keys=True)+'\n')
with (root/'TDD_LEDGER.md').open('a') as f:f.write(f"\n- {label} {phase}, {start}, exit {r.returncode}: `{command}`; [{log.name}]({record['log']}).\n")
print(log.read_text());sys.exit(r.returncode)
