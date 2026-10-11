"""Create a NEW sealed diagnostic config; no old state/seal/config rewriting."""
import json,hashlib,os,shutil,shlex,fcntl,ast,subprocess,datetime
from pathlib import Path
H=Path('/mnt/hdd1/u00134/radegs_paper_reproduction_v01');F=H/'depth_only_v01/scan55_failure_v01';R=F/'repair_v01';V=R/'validation_v01';C=Path(__file__).resolve().parent
assert not V.exists();assert shutil.disk_usage(H).free>55*2**30 and shutil.disk_usage('/').free>10*2**30
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
old=F/'replay_v01/state/runner_config.json';c=json.loads(old.read_text());build=json.loads((R/'build/MANIFEST.json').read_text())
for p,digest in c['immutable_files'].items():assert sha(p)==digest,p
for p,digest in build['source_files'].items():assert sha(p)==digest,p
for p in C.glob('*.py'):ast.parse(p.read_text())
for k,v in {'purpose':'scan55_eigen_fallback_validation','config_path':str(V/'state/runner_config.json'),'state_dir':str(V/'state'),'log_dir':str(V/'logs'),'model':str(V/'bounded_model'),'capture_dir':str(V/'captures'),'validation_root':str(V/'results'),'failure_root':str(F),'native_capture':str(F/'replay_v01/captures/1791579160907311673/native_failure_2.pt'),'preflight_report':str(V/'state/preflight.json'),'tmux':'radegs-depth-scan55-repair-validation-v01','launch_script':str(V/'launch.sh'),'numerical_revision':'scan55_eigen_fallback_v01'}.items():c[k]=v
c['runtime_env']['PYTHONPATH']=str(R/'build/official_python')+os.pathsep+c['runtime_env']['PYTHONPATH']
c['reports']={'smoke':str(V/'state/smoke.report.json')};c['stage_commands']={'smoke':[str(H/'official_code_fix_v01/env/bin/python'),str(C/'repair_validation.py'),'--config',c['config_path']]}
for key in ['native_validated','native_validation_seal','runtime_validated','memcheck_receipt']:c['inputs']['parent_'+key]=c['inputs'].pop(key)
c['inputs'].update(native=build['native_sha256'],build_manifest=sha(R/'build/MANIFEST.json'),numerical_revision='scan55_eigen_fallback_v01',repair_source=sha(R/'SOURCE_PATCH.diff'),diagnostic_scope='new_native_all_regressions_and_two_steps_only')
c['immutable_files'].update(build['source_files']);c['immutable_files'].update({str(p):sha(p) for p in [Path(build['native']),R/'build/MANIFEST.json',R/'SOURCE_PATCH.diff',Path(c['native_capture']),F/'captured_covariance.txt',F/'eigen_gpu_old',F/'eigen_gpu_candidate',*C.glob('*.py'),C/'eigen_capture_gpu.cu',C/'test_eigen_fallback.cpp']})
from repair_scope import validate
validate(c)
for p in [V/'state',V/'logs']:p.mkdir(parents=True)
def put(p,x):p.write_text(json.dumps(x,indent=2,ensure_ascii=False)+'\n')
put(V/'state/preflight.json',{'passed':True,'diagnostic_only':True,'engineering_ready_means_diagnostic_dispatch_only':True,'candidate_GPU_verified':False,'source_files_rehashed':len(c['immutable_files']),'parent_config_sha256':sha(old),'root_free':shutil.disk_usage('/').free,'hdd_free':shutil.disk_usage(H).free})
put(Path(c['config_path']),c)
cmd=['/usr/bin/python3',str(C/'repair_control.py'),'--config',c['config_path']]
(V/'launch.sh').write_text('#!/bin/bash\nset -euo pipefail\nexport PYTHONDONTWRITEBYTECODE=1\nexec '+shlex.join(cmd)+' > '+shlex.quote(str(V/'supervisor.log'))+' 2>&1\n')
put(V/'LAUNCH.json',{'config':c['config_path'],'config_sha256':sha(c['config_path']),'command':cmd,'tmux':c['tmux'],'candidate_native':build['native'],'native_sha256':build['native_sha256'],'stage_order':['smoke'],'no_formal_training':True,'no_mesh_eval':True,'scientificdone':False})
print(json.dumps({'config':c['config_path'],'sha256':sha(c['config_path']),'native':build['native_sha256']}))
