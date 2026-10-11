"""Freeze one official-method scan24 chain after real numerical/restart gates."""
import json,os,sys,shutil,subprocess,time
from pathlib import Path
P=Path(__file__).resolve().parent;W=P.parents[3];sys.path.append(str(P.parents[1]/'stage2'))
from safety import atomic_json,sha256,verify_seal
H=Path('/mnt/hdd1/u00134/radegs_paper_reproduction_v01');O=H/'official_code_fix_v01';A=W/'artifacts/radegs_paper_reproduction_v01/full_reproduction_v01/official_code_fix_v01';D=O/'pilot';model=O/'models/scan24_official_half30k'
assert not D.exists() and not model.exists();assert shutil.disk_usage('/').free>=10*1024**3 and shutil.disk_usage(H).free>=50*1024**3
assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=W,text=True).strip()=='00bb67c4ae39157906bcda6abc8760cc37679414'
old=O/'runtime_validation_v02';c=json.loads((old/'state/runner_config.json').read_text());assert verify_seal(old/'state/smoke.seal.json','smoke',c['inputs'])
for p,h in c['immutable_files'].items():assert sha256(p)==h,p
D.mkdir();(D/'state').mkdir();files=dict(c['immutable_files'])
for directory in [P,O/'runtime_source_v02',O/'runtime_module_v02',O/'source/dtu_eval']:
 for p in directory.rglob('*.py'):files[str(p)]=sha256(p)
for p in [P.parent/'tsdf_touch.py',P.parent/'empty_mesh.py',O/'NATIVE_GPU_VERIFIED.json',old/'state/smoke.seal.json',O/'source/evaluate_dtu_mesh.py',O/'TRAIN_RUNTIME_PATCH.diff']:
 files[str(p)]=sha256(p)
for p in (O/'env/lib/python3.9/site-packages/simple_knn').glob('*.so'):files[str(p)]=sha256(p)
proto=json.loads((A/'FULL_SUITE_PROTOCOL.json').read_text());atomic_json(D/'PROTOCOL_PREVIOUS.json',proto);proto.update(status='READY_SINGLE_SCAN24_OFFICIAL_ROUTE',newbranchstage='NATIVE_AND_RUNTIME_GPU_VERIFIED',numeric_gate_pending=[],actual_counts={'train_started':0,'train_completed':0,'export_completed':0,'mesh_completed':0,'official_metrics':0},native_validation_seal=str(O/'gpu_validation_v02/state/smoke.seal.json'),runtime_validation_seal=str(old/'state/smoke.seal.json'),runtime_source=str(O/'runtime_source_v02'),runtime_module=str(O/'runtime_module_v02'),expansion_not_dispatched=True,utc=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()))
proto['independent_fixes_pending_scope']=['Independent Jn / eigen conditioning / exact coefficient-conic VJP: GPU fixtures passed; valid scope limited to documented fixtures','Zero-alpha quotient guard positive branch unchanged; CPU and GPU validated','Runtime mixed CPU/GPU finite predicates and owned-PID exit/adoption controls: engineering fixes only']
for entry in proto['entries']:entry['status']='READY_SINGLE_SCENE_AFTER_NUMERIC_GATES'
proto['next_action']='Execute scan24 chain, inspect 15k/30k alpha and actual geometry; no automatic scene expansion';proto['disk_budget_estimate']={'working_GiB':20,'basis':'existing scan24 model directory1.9GiB; additional fixed checkpoints/49-view exports and 50000*16^3*8byte TSDF allocation; engineering estimate not measured final size','root_min_GiB':10,'HDD_min_GiB':50}
atomic_json(D/'PROTOCOL.json',proto);atomic_json(A/'FULL_SUITE_PROTOCOL.json',proto);files[str(D/'PROTOCOL.json')]=sha256(D/'PROTOCOL.json')
c.update(method_variant='official_code_fix_v01',purpose='official_C24_scan24_half30k',state_dir=str(D/'state'),log_dir=str(D/'logs'),model=str(model),cwd=str(O/'source'),runtime_module=str(O/'runtime_module_v02'),runtime_source=str(O/'runtime_source_v02'),iterations=30000,resolution_divisor=2,wd=100,wn=.05,regularization_from_iter=15000,geometry_start_inclusive=True,optimizer_final_step=False,expected_scene={'views':49,'half_resolution':[777,581],'initial_colmap_points':31205},artifact_dir=str(A),tmux='radegs-official-scan24-pilot-v01',launch_script=str(D/'launch.sh'),preflight_report=str(D/'state/preflight.json'))
c.pop('validation_root',None);c['runtime_env']['PATH']=str(O/'env/bin')+':/usr/bin:/bin';c['inputs'].update(native_validated=sha256(O/'gpu_validation_v02/state/smoke.seal.json'),runtime_validated=sha256(old/'state/smoke.seal.json'),frozen_protocol=sha256(D/'PROTOCOL.json'),runtime=sha256(O/'runtime_module_v02/official_runtime.py'),runtime_train=sha256(O/'runtime_source_v02/train.py'))
c['reports']={s:str(D/'state'/(s+'.report.json')) for s in ('train','export','tsdf','eval')};c['stage_commands']={s:[str(O/'env/bin/python'),str(P/'stages.py'),'--config',str(D/'state/runner_config.json'),'--stage',s] for s in c['reports']};c['train_command']=[str(O/'env/bin/python'),str(P/'train_entry.py'),'--config',str(D/'state/runner_config.json')]
c['eval_command']=[str(O/'env/bin/python'),str(O/'source/evaluate_dtu_mesh.py'),'-s',c['data'],'-m',str(model),'-r','2','--iteration','30000','--DTU',str(H/'data/eval_gt/dtu_eval_scan24')];c['immutable_files']=files
from importlib.util import spec_from_file_location,module_from_spec
spec=spec_from_file_location('scope',P/'pipeline_v01/pipeline_scope.py');scope=module_from_spec(spec);spec.loader.exec_module(scope);scope.validate_scope(c)
atomic_json(D/'state/preflight.json',{'passed':True,'scope':'single official-loss C24 scan24, GPU native and actual restart verified','native_seal':c['inputs']['native_validated'],'runtime_seal':c['inputs']['runtime_validated'],'estimated_new_disk_GiB':20,'root_free_GiB':shutil.disk_usage('/').free/1024**3,'HDD_free_GiB':shutil.disk_usage(H).free/1024**3});atomic_json(D/'state/runner_config.json',c)
launch=D/'launch.sh';launch.write_text('#!/bin/bash\nset -eu\nexport PYTHONDONTWRITEBYTECODE=1\nexec '+str(O/'env/bin/python')+' '+str(P/'pipeline_v01/control.py')+' --config '+str(D/'state/runner_config.json')+' >> '+str(D/'supervisor.log')+' 2>&1\n');launch.chmod(0o700)
atomic_json(D/'LAUNCH.json',{'command':['tmux','new-session','-d','-s',c['tmux'],str(launch)],'config_sha256':sha256(D/'state/runner_config.json'),'immutable_files':len(files),'training_started':False,'scientificdone':False});print({'path':str(D),'config_sha256':sha256(D/'state/runner_config.json'),'immutable_files':len(files)})
