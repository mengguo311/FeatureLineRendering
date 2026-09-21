"""Operational command journal, independent of scientific code."""
import datetime,hashlib,json,os,subprocess,sys
from pathlib import Path
root=Path(__file__).resolve().parents[2]
a=root/'artifacts/topk_layered_probe'
phase,label,*command=sys.argv[1:]
assert phase in ['RED','GREEN','CHECK','RUN']
log=a/'logs';log.mkdir(exist_ok=True)
seq=sum(1 for _ in (a/'TDD.jsonl').open()) if (a/'TDD.jsonl').exists() else 0
path=log/f'{seq:03d}_{phase}_{label}.log'
env=dict(os.environ,PYTHONPATH='.:tests',PYTHONDONTWRITEBYTECODE='1',OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',OMP_WAIT_POLICY='PASSIVE',CUDA_VISIBLE_DEVICES='0')
start=datetime.datetime.now(datetime.timezone.utc).isoformat()
with path.open('xb') as f:r=subprocess.run(command,cwd=root,env=env,stdout=f,stderr=subprocess.STDOUT)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
record=dict(sequence=seq,phase=phase,label=label,command=command,command_sha256=hashlib.sha256(json.dumps(command).encode()).hexdigest(),exit_code=r.returncode,output=str(path.relative_to(root)),output_sha256=sha(path),started_utc=start,finished_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),environment={k:env[k] for k in ['PYTHONPATH','PYTHONDONTWRITEBYTECODE','OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','CUDA_VISIBLE_DEVICES']},sources={str(p.relative_to(root)):sha(p) for folder in ['src','scripts','tests'] for p in (root/folder).glob('*topk*') if p.is_file()},protocol_sha256=sha(a/'PROTOCOL.md'))
with (a/'TDD.jsonl').open('a') as f:f.write(json.dumps(record,sort_keys=True)+'\n')
print(path.read_text()[-12000:]);print(json.dumps({k:record[k] for k in ['sequence','phase','exit_code','output_sha256']}))
if phase=='RED':sys.exit(0 if r.returncode!=0 else 1)
sys.exit(r.returncode)
