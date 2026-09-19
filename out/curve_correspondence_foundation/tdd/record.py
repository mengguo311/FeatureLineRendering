"""Administrative command recorder, preserving every RED/GREEN attempt."""
import datetime,hashlib,json,os,pathlib,subprocess,sys,time
O=pathlib.Path(__file__).resolve().parents[1];R=O.parents[1]
label,phase,*command=sys.argv[1:]
env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',OMP_WAIT_POLICY='PASSIVE',PYTHONPATH=str(O/'code')+':'+str(O/'tests')+':'+str(R)+':'+str(R/'tests'))
files=[*list((O/'code').glob('*.py')),*list((O/'tests').glob('*.py'))]
record=dict(label=label,phase=phase,command=command,start_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),source_hashes={str(p.relative_to(R)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files},environment={k:env[k] for k in ['PYTHONDONTWRITEBYTECODE','OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','PYTHONPATH']})
start=time.monotonic();p=subprocess.run(command,cwd=R,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT);record.update(exit_code=p.returncode,elapsed_seconds=time.monotonic()-start)
base=O/'tdd'/f'{label}_{phase}';base.with_suffix('.txt').write_bytes(p.stdout);base.with_suffix('.json').write_text(json.dumps(record,indent=2)+'\n');print(p.stdout.decode(),end='');print('RECORDED',base, 'EXIT',p.returncode)
ledger=O/'TDD_LEDGER.md'
if not ledger.exists():ledger.write_text('# Observed RED–GREEN–REFACTOR ledger\n\nRaw logs and command/source hashes are retained in tdd/. No scene result is a test fixture.\n\n')
with ledger.open('a') as f:f.write(f'- {record["start_utc"]} **{label} / {phase}**: exit {p.returncode}; `{command}`; [log](tdd/{base.name}.txt), [record](tdd/{base.name}.json).\n')
sys.exit(0 if (phase=='RED' and p.returncode!=0) or (phase!='RED' and p.returncode==0) else 1)
