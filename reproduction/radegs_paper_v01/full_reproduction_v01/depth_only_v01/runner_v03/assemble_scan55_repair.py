"""Freeze a new scan55 run only after actual repair GPU/CPU seals verify."""
import sys,json,shutil,subprocess,ast,shlex
from pathlib import Path
P=Path(__file__).resolve().parent;W=P.parents[4];H=Path('/mnt/hdd1/u00134/radegs_paper_reproduction_v01');D=H/'depth_only_v01';O=H/'official_code_fix_v01';R=D/'scan55_failure_v01/repair_v01';S=D/'scan55_eigen_fix_v01'
sys.path.insert(0,str(W/'reproduction/radegs_paper_v01/stage2'))
from safety import atomic_json,sha256,verify_seal
from pipeline_scope import validate_scope
assert not S.exists() and not (D/'models/scan55_official_half30k_eigen_fallback_v01').exists()
assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=W,text=True).strip()=='00bb67c4ae39157906bcda6abc8760cc37679414'
assert shutil.disk_usage('/').free>10*2**30 and shutil.disk_usage(H).free>55*2**30
v=R/'validation_v01';vc=json.loads((v/'state/runner_config.json').read_text());receipt=json.loads((R/'VERIFIED_REPAIR.json').read_text());assert receipt['status']=='GPU_AND_CPU_GATES_VERIFIED';assert verify_seal(v/'state/smoke.seal.json','smoke',vc['inputs'])
for p,h in vc['immutable_files'].items():assert sha256(p)==h,p
assert json.loads((R/'cpu_regressions/RESULT_AFTER_HARNESS_FIX.json').read_text())['all_pass']
old=D/'scan55/state/runner_config.json';c=json.loads(old.read_text());files=c['immutable_files'].copy()
for p,h in files.items():assert sha256(p)==h,p
build_path=R/'build/MANIFEST.json';build=json.loads(build_path.read_text());files.update(build['source_files']);files[str(Path(build['native']))]=sha256(build['native'])
protocol={'workflow':'depth_only_v01','parent_protocol':str(D/'FULL_SUITE_PROTOCOL.json'),'parent_sha256':sha256(D/'FULL_SUITE_PROTOCOL.json'),'method_variant':'official_code_fix_v01','numerical_revision':'scan55_eigen_fallback_v01','current_scene':'scan55','scene_set_unchanged':True,'scope':'one fresh COLMAP half30k training then 15k/30k depth, numerical/visual review; no automatic next scene','changed_scientific_file':'paper_geometry_precision.cuh','patch':str(R/'SOURCE_PATCH.diff'),'source_manifest':str(build_path),'native_sha256':build['native_sha256'],'loss_schedule_data_unchanged':True,'former_failed_run_preserved':str(old),'old_completed_scenes_native':'de0986bbff4d6e74bff427abb036e74fa1646730bdf00e31a3b096b627817b08','no_mesh_eval':True,'acceptance':'finite training, original float depths + cameras/provenance, alpha>=.5 finite-positive validmask and visual review, not depth-GT accuracy'}
S.mkdir();(S/'state').mkdir();atomic_json(S/'NUMERICAL_REVISION_PROTOCOL.json',protocol)
model=D/'models/scan55_official_half30k_eigen_fallback_v01';cfg=S/'state/runner_config.json'
c.update(model=str(model),state_dir=str(S/'state'),log_dir=str(S/'logs'),config_path=str(cfg),preflight_report=str(S/'state/preflight.json'),tmux='radegs-depth-scan55-eigen-fix-v01',launch_script=str(S/'launch.sh'),delivery_dir=str(D/'deliveries/scan55_eigen_fallback_v01'),numerical_revision='scan55_eigen_fallback_v01',native_build_manifest=str(build_path),source_patch_manifest=str(R/'SOURCE_CHANGE.json'),active_protocol_addendum=str(S/'NUMERICAL_REVISION_PROTOCOL.json'),prior_failed_run=str(old),prior_failure_manifest=str(D/'scan55_failure_v01/ORIGINAL_FAILURE_MANIFEST.json'))
c['runtime_env']['PYTHONPATH']=str(P)+':'+str(R/'build/official_python')+':'+c['runtime_env']['PYTHONPATH']
for key in ['native_validated','native_validation_seal','runtime_validated','memcheck_receipt']:c['inputs']['parent_'+key]=c['inputs'].pop(key)
c['inputs'].update(native=build['native_sha256'],build_manifest=sha256(build_path),native_validated=sha256(v/'state/smoke.seal.json'),native_validation_seal=sha256(v/'state/smoke.seal.json'),runtime_validated=sha256(v/'state/smoke.seal.json'),numerical_revision='scan55_eigen_fallback_v01',repair_verification=sha256(R/'VERIFIED_REPAIR.json'),revision_protocol=sha256(S/'NUMERICAL_REVISION_PROTOCOL.json'),pipeline_revision=sha256(P/'control.py'))
c['reports']={s:str(S/'state'/(s+'.report.json')) for s in ('smoke','train','export','depth_review')}
c['stage_commands']={s:[str(O/'env/bin/python'),str(P/'stages.py'),'--config',str(cfg),'--stage',s] for s in c['reports']}
c['train_command']=[str(O/'env/bin/python'),str(P.parent.parent/'official_code_fix_v01/train_entry.py'),'--config',str(cfg)]
for p in [*P.glob('*.py'),R/'VERIFIED_REPAIR.json',R/'SOURCE_PATCH.diff',R/'SOURCE_CHANGE.json',build_path,S/'NUMERICAL_REVISION_PROTOCOL.json',v/'state/smoke.seal.json',R/'cpu_regressions/RESULT_AFTER_HARNESS_FIX.json',R/'REVISION_SCOPE_GREEN.log']:
 if p.suffix=='.py':ast.parse(p.read_text())
 files[str(p)]=sha256(p)
c['immutable_files']=files;validate_scope(c)
atomic_json(S/'state/preflight.json',{'passed':True,'actual_GPU_repair_seal':str(v/'state/smoke.seal.json'),'native_sha256':build['native_sha256'],'old_failure_preserved':True,'fresh_COLMAP_init':True,'model_path_unique':True,'training_files_verified':206,'root_free_bytes':shutil.disk_usage('/').free,'HDD_free_bytes':shutil.disk_usage(H).free,'estimated_working_GiB':20,'estimate_basis':'observed earlier scene checkpoints, 98 NPZ and complete tar; not timing claim','no_mesh_eval':True})
atomic_json(cfg,c);launch=S/'launch.sh';launch.write_text('#!/bin/bash\nset -euo pipefail\nexport PYTHONDONTWRITEBYTECODE=1\nexec '+shlex.join([str(O/'env/bin/python'),str(P/'control.py'),'--config',str(cfg)])+' > '+shlex.quote(str(S/'supervisor.log'))+' 2>&1\n')
atomic_json(S/'LAUNCH.json',{'config':str(cfg),'config_sha256':sha256(cfg),'native_sha256':build['native_sha256'],'parent_failed_config_sha256':sha256(old),'old_failure_not_erased':True,'numerical_revision':c['numerical_revision'],'immutable_files':len(files),'command':['tmux','new-session','-d','-s',c['tmux'],'bash',str(launch)],'stage_order':list(c['reports']),'automatic_next_scene':False,'scientificdone':False})
print(json.dumps({'config':str(cfg),'sha256':sha256(cfg),'immutable_files':len(files)}))
