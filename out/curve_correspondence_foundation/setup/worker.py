"""Administrative traced subprocess scheduler; science is confined in the child."""
import datetime,json,os,pathlib,subprocess,sys,time
O=pathlib.Path(__file__).resolve().parents[1];R=O.parents[1];scene=sys.argv[1]
env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',PYTHONPYCACHEPREFIX=str(O/'setup/unused_pycache'),OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',OMP_WAIT_POLICY='PASSIVE',PYTHONPATH=str(O/'code')+':'+str(R),CUDA_CACHE_DISABLE='1')
cfg=json.loads((O/'config.json').read_text())
commands=[('primary','seed_1729'),('cross','seed_1729')]+[('repeat',a) for a in cfg['scenes'][scene]['assets'] if a!='seed_1729']
if len(sys.argv)>2 and sys.argv[2]=='primary':commands=commands[:1]
if len(sys.argv)>2 and sys.argv[2]=='remaining':commands=commands[1:]
for task,asset in commands:
 key=f'{scene}_{task}_{asset}';log=O/'setup'/f'{key}.txt';trace=O/'setup'/f'{key}.strace';status=O/'setup'/f'{key}_exit.json'
 if status.exists():raise FileExistsError(status)
 command=['strace','-f','-qq','-yy','-e','trace=open,openat,openat2,creat','-o',str(trace),sys.executable,str(O/'code/cc_runner.py'),'--scene',scene,'--task',task,'--asset',asset]
 start=time.monotonic();record=dict(command=command,start_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),env={k:env[k] for k in ['PYTHONDONTWRITEBYTECODE','PYTHONPYCACHEPREFIX','PYTHONPATH','OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS']})
 with log.open('xb') as stream:p=subprocess.run(command,cwd=R,env=env,stdout=stream,stderr=subprocess.STDOUT)
 record.update(exit_code=p.returncode,elapsed_seconds=time.monotonic()-start,end_utc=datetime.datetime.now(datetime.timezone.utc).isoformat());status.write_text(json.dumps(record,indent=2)+'\n')
 print(key,p.returncode,record['elapsed_seconds'],flush=True)
 if p.returncode:sys.exit(p.returncode)
