"""Execute the preregistered supplemental diagnostic on already frozen samples."""
import datetime,json,os,pathlib,subprocess,sys,time
O=pathlib.Path(__file__).resolve().parents[1];R=O.parents[1];scene=sys.argv[1]
if len(sys.argv)==2:
 key=scene+'_visibility';env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',PYTHONPATH=str(O/'code')+':'+str(R))
 command=['strace','-f','-qq','-yy','-e','trace=open,openat,openat2,creat','-o',str(O/'setup'/f'{key}.strace'),sys.executable,str(pathlib.Path(__file__).resolve()),scene,'--scene',scene]
 start=time.monotonic();r=dict(command=command,start_utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
 with (O/'setup'/f'{key}.txt').open('xb') as f:p=subprocess.run(command,cwd=R,env=env,stdout=f,stderr=subprocess.STDOUT)
 r.update(exit_code=p.returncode,elapsed_seconds=time.monotonic()-start,end_utc=datetime.datetime.now(datetime.timezone.utc).isoformat());(O/'setup'/f'{key}_exit.json').write_text(json.dumps(r,indent=2)+'\n');print(key,r['exit_code'],r['elapsed_seconds']);sys.exit(p.returncode)
sys.path[:0]=[str(O/'code'),str(R)]
import numpy as np
import cc,cc_visibility
from cc_io import read_json,write_json,sha,seal,verify_seal,scene_inputs
from cc_runner import P,confine,BINARIES,primary_arm_names
from src.corrected_layers import AreaLayers
cfg=read_json(O/'config.json');base=O/'scenes'/scene;ev=O/'evaluation'/scene
assert verify_seal(ev,read_json(ev/'frozen.json'))
output=O/'visibility'/scene;output.mkdir(parents=True,exist_ok=False)
paths={v:P/f'local/{scene}/layers/seed_1729/view_{v:03d}.npz' for s in ['F','C'] for v in cfg['splits'][s]}
paths.update({v:P/f'evaluation/{scene}/visual/native/dev_layers_{v:03d}.npz' for v in cfg['splits']['DEV']})
prior=read_json(P/'MANIFEST.json');entries=prior['files']
expected={str(P/x['path']):x['sha256'] for x in entries}
observed={str(p):sha(p) for p in paths.values()};assert all(expected[k]==v for k,v in observed.items())
sources=[*list((O/'code').glob('*.py')),*list((R/'src').glob('*.py')),pathlib.Path(__file__).resolve()]
inputs=[*paths.values(),*BINARIES,*sources,*list((base/'F').glob('*.json.gz')),*list(ev.glob('*_samples.json.gz'))]
policy=dict(task='visibility',scene=scene,readonly=[str(p.resolve()) for p in inputs]+[str(pathlib.Path(sys.prefix).resolve()),'/usr','/lib','/lib64','/etc','/proc','/sys'],writable=[str(output),'/dev'],photo_inputs=[],input_hashes=observed,config_sha256=sha(O/'config.json'),created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
write_json(output/'allowlist.json',policy);confine(inputs,output)
delta=cfg['scenes'][scene]['eligibility']['delta'];names=primary_arm_names(cfg)
geometry={n:cc.sample_geometry(read_json(base/f'F/{n}.json.gz')['accepted'],delta)[0] for n in names}
results={n:{} for n in names}
for split in ['F','C','DEV']:
 cameras=scene_inputs(cfg,scene,split)['cameras'];samples={n:read_json(ev/f'{n}_{split}_samples.json.gz') for n in names}
 for n in names:results[n][split]={}
 for view,camera in cameras.items():
  layer=AreaLayers.load(paths[view])
  for n in names:
   sample=next(s for s in samples[n] if s['view']==view);uv,z,_=cc.project_jacobian(geometry[n],camera['K'],camera['w2c'])
   report=cc_visibility.stratify(sample,z,layer,delta);results[n][split][str(view)]=report
  del layer
write_json(output/'strata.json.gz',results)
summary={n:{s:{v:{k:val for k,val in row.items() if k!='classifications'} for v,row in views.items()} for s,views in splits.items()} for n,splits in results.items()}
write_json(output/'summary.json',dict(scene=scene,posterior='seed_1729',diagnostic_only=True,all_in_frame_metrics_unchanged=True,arms=summary))
write_json(output/'complete.json',dict(scene=scene,created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),arms=len(names),views=20));write_json(output/'frozen.json',seal(output))
print('VISIBILITY SEALED',scene,flush=True)
