import sys,subprocess,os,json,datetime,pathlib
label,phase,*target=sys.argv[1:]
root=pathlib.Path('/home/u00134/3dgs_line/tier1'); out=root/'out/multiscene_foundation'
command=['/home/u00134/bin/miniconda3/envs/vfsdgs/bin/python','-m','unittest','-v',*target]
env=dict(os.environ,PYTHONPATH=str(root)+':'+str(root/'tests'),CUDA_VISIBLE_DEVICES='1',OMP_NUM_THREADS='4',OPENBLAS_NUM_THREADS='4',PYTHONDONTWRITEBYTECODE='1')
start=datetime.datetime.now(datetime.timezone.utc).isoformat()
p=subprocess.run(command,cwd=root,env=env,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
log=out/'tdd'/f'{label}_{phase}.txt'; log.write_text(p.stdout)
record={'label':label,'phase':phase,'start_utc':start,'end_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'command':command,'env':{k:env[k] for k in ['PYTHONPATH','CUDA_VISIBLE_DEVICES','OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','PYTHONDONTWRITEBYTECODE']},'exit_code':p.returncode,'log':str(log.relative_to(out))}
with (out/'tdd/commands.jsonl').open('a') as f:f.write(json.dumps(record)+'\n')
with (out/'TDD_LEDGER.md').open('a') as f:f.write(f"\n- {label} **{phase}** {start}: `PYTHONPATH=.:tests CUDA_VISIBLE_DEVICES=1 OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 PYTHONDONTWRITEBYTECODE=1 {' '.join(command)}` → exit {p.returncode}; [{log.name}]({log.relative_to(out)}).\n")
print(p.stdout[-5000:]);print('exit',p.returncode)
if phase=='RED':sys.exit(0 if p.returncode else 2)
sys.exit(p.returncode)
