"""Seal a single validation-only official-native run. Never starts CUDA."""
import hashlib,json,os,subprocess,time
from pathlib import Path
P=Path(__file__).resolve().parent;W=P.parents[3];H=Path('/mnt/hdd1/u00134/radegs_paper_reproduction_v01');O=H/'official_code_fix_v01';D=O/'gpu_validation_v01';D.mkdir(exist_ok=False);(D/'state').mkdir()
def sha(p):
 h=hashlib.sha256()
 with open(p,'rb') as f:
  for b in iter(lambda:f.read(8*1024**2),b''):h.update(b)
 return h.hexdigest()
def save(p,v):p.write_text(json.dumps(v,indent=2,sort_keys=True)+'\n')
assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=W,text=True).strip()=='00bb67c4ae39157906bcda6abc8760cc37679414'
build=json.loads((O/'build/MANIFEST.json').read_text());old=json.loads((H/'gradient_fix_v01/pilot/state/runner_config.json').read_text());files={k:v for k,v in old['immutable_files'].items() if '/data/' in k};files.update(build['source_files']);files[build['native']]=build['native_sha256']
paths=[O/'ENVIRONMENT_LOCK.json',O/'MEMCHECK_VERIFIED.json',O/'build/MANIFEST.json',P/'official_control.py',P/'runner.py',P/'official_scope.py',P/'masked_division.py',P/'loss_reference.py',P/'gpu_loss_check.py',P/'gpu_validation.py']
stage2=P.parents[1]/'stage2';fix=P.parents[1]/'gradient_fix_v01';rgb=P.parent/'suite_execution_v01/scan69_cuda_failure_v01/rgb_vjp_validation_v02'
paths += list(stage2.glob('*.py'))+list(fix.glob('*.py'))+list(rgb.glob('*.py'))+[P.parent/'precision_v01/strict_shared_policy.py',H/'stage2/shared/shared_runner.py']
paths += list((O/'source').glob('*.py'))
for sub in ['arguments','scene','utils','gaussian_renderer']:
 paths+=list((O/'source'/sub).rglob('*.py'))
paths+=list((O/'build/official_python/diff_gaussian_rasterization').glob('*.py'))+list((H/'build/baseline_python/diff_gaussian_rasterization').glob('*'))
for p in paths:
 if p.is_file():files[str(p)]=sha(p)
for p,h in files.items():assert sha(p)==h,p
c={'method_variant':'official_code_fix_v01','scene':'scan24','automatic_scene_limit':1,'engineering_ready':True,'purpose':'native_validation','allowed_gpu_uuids':['GPU-d2d1e4fd-e246-0633-3343-ccc0a0bd981a'],'stable_seconds':60,'poll_seconds':60,'state_dir':str(D/'state'),'log_dir':str(D/'logs'),'cwd':str(O/'source'),'validation_root':str(D/'outputs'),'model':str(O/'models/scan24_official_half30k'),'data':old['data'],'baseline_python':old['baseline_python'],'immutable_files':files,'inputs':{'method':'official_code_fix_v01','native':build['native_sha256'],'environment_lock':sha(O/'ENVIRONMENT_LOCK.json'),'build_manifest':sha(O/'build/MANIFEST.json'),'memcheck_receipt':sha(O/'MEMCHECK_VERIFIED.json')},'preflight_report':str(D/'state/preflight.json'),'reports':{'smoke':str(D/'state/smoke.report.json')},'stage_commands':{'smoke':[str(O/'env/bin/python'),str(P/'gpu_validation.py'),'--config',str(D/'state/runner_config.json')]},'runtime_env':{'CUDA_DEVICE_ORDER':'PCI_BUS_ID','CUDA_LAUNCH_BLOCKING':'1','PYTHONDONTWRITEBYTECODE':'1','PYTHONPATH':os.pathsep.join(map(str,[O/'build/official_python',P,stage2,fix,rgb,O/'source'])),'OMP_NUM_THREADS':'2','OPENBLAS_NUM_THREADS':'2','MKL_NUM_THREADS':'2','TMPDIR':str(H/'tmp'),'TORCH_HOME':str(O/'cache/torch'),'XDG_CACHE_HOME':str(O/'cache'),'MPLCONFIGDIR':str(O/'cache/matplotlib')}}
save(D/'state/preflight.json',{'passed':True,'scope':'CPU/source/data/environment prepared; GPU numerical readiness pending','native_gpu_passed':False,'formal_train_permitted':False});save(D/'state/runner_config.json',c)
launch=D/'launch.sh';launch.write_text('#!/bin/bash\nset -eu\nexport PYTHONDONTWRITEBYTECODE=1\nexec '+str(O/'env/bin/python')+' '+str(P/'official_control.py')+' --config '+str(D/'state/runner_config.json')+' >> '+str(D/'supervisor.log')+' 2>&1\n');launch.chmod(0o700)
save(D/'LAUNCH.json',{'config_sha256':sha(D/'state/runner_config.json'),'immutable_files':len(files),'tmux':'radegs-official-native-validation-v01','command':['tmux','new-session','-d','-s','radegs-official-native-validation-v01',str(launch)],'scientificdone':False});print(json.dumps({'root':str(D),'immutable_files':len(files),'config_sha256':sha(D/'state/runner_config.json')}))
