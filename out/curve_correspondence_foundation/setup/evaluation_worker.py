import datetime,json,os,pathlib,subprocess,sys,time
O=pathlib.Path(__file__).resolve().parents[1];R=O.parents[1];scene=sys.argv[1];key=scene+'_evaluation'
env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',PYTHONPYCACHEPREFIX=str(O/'setup/unused_pycache'),OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',OMP_WAIT_POLICY='PASSIVE',PYTHONPATH=str(O/'code')+':'+str(R))
command=['strace','-f','-qq','-yy','-e','trace=open,openat,openat2,creat','-o',str(O/'setup'/f'{key}.strace'),sys.executable,str(O/'code/cc_evaluate.py'),'--scene',scene]
start=time.monotonic();r=dict(command=command,start_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),env={k:env[k] for k in ['PYTHONDONTWRITEBYTECODE','PYTHONPYCACHEPREFIX','PYTHONPATH','OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS']})
with (O/'setup'/f'{key}.txt').open('xb') as f:p=subprocess.run(command,cwd=R,env=env,stdout=f,stderr=subprocess.STDOUT)
r.update(exit_code=p.returncode,elapsed_seconds=time.monotonic()-start,end_utc=datetime.datetime.now(datetime.timezone.utc).isoformat());(O/'setup'/f'{key}_exit.json').write_text(json.dumps(r,indent=2)+'\n');print(key,r['exit_code'],r['elapsed_seconds']);sys.exit(p.returncode)
