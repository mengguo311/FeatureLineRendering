"""Seal a single next resolved paper entry, with unchanged trained method/native."""
import ast,datetime,difflib,json,shutil,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[4];CODE=Path(__file__).resolve().parent
BASE=ROOT/'reproduction/radegs_paper_v01/stage2';sys.path.insert(0,str(BASE));sys.path.insert(0,str(CODE/'runtime'))
from safety import atomic_json,sha256,verify_seal
from suite_scope import validate_config_scope
H=Path('/mnt/hdd1/u00134/radegs_paper_reproduction_v01');OUT=H/'full_reproduction_v01/suite_execution_v01';ART=ROOT/'artifacts/radegs_paper_reproduction_v01/full_reproduction_v01/suite_execution_v01'

def main():
 parent=H/'full_reproduction_v01/precision_v01/pilot_v02/state/runner_config.json';c=json.loads(parent.read_text());old=json.loads(parent.read_text())
 assert sha256(parent)=='9d2205f4aec4fa23dd582a31919996caab45f3be944cbcda754f513c2def810a'
 assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()=='00bb67c4ae39157906bcda6abc8760cc37679414'
 assert not subprocess.check_output(['git','status','--porcelain'],cwd=H/'sources/RaDe-GS',text=True).strip()
 for p,d in c['immutable_files'].items():assert sha256(p)==d,p
 for stage in ['smoke','train','export']:assert verify_seal(Path(c['state_dir'])/(stage+'.seal.json'),stage,c['inputs'])
 tests=json.loads((OUT/'cpu_tests/SUMMARY.json').read_text());assert tests['all_passed']
 data=json.loads((OUT/'SCAN37_DATA.json').read_text())
 assert data['images']==data['camera_views']==49 and data['initial_COLMAP_points']==50807 and data['raw_copy_hashes_equal']
 for p,d in {**data['training_hashes'],**data['evaluation_hashes']}.items():assert sha256(p)==d,p
 assert shutil.disk_usage('/').free>=10*1024**3 and shutil.disk_usage(H).free-12*1024**3>=50*1024**3
 state=OUT/'scan37_v01/state';state.mkdir(parents=True,exist_ok=False);path=state/'runner_config.json'
 model=H/'models/scan37_paper_text_precision_v01_half_30k';assert not model.exists(),'do not reuse trained model'
 protocol=ART.parent/'FULL_SUITE_PROTOCOL.json'
 c.update(scene='scan37',dataset='DTU',entry_id='DTU_scan37_half30k_TSDF',iterations=30000,resolution_divisor=2,full_suite_protocol=str(protocol),full_suite_protocol_sha256=sha256(protocol),data=data['prepared'],gt=data['evaluation_GT'],model=str(model),state_dir=str(state),log_dir=str(state.parent/'logs'),preflight_report=str(state/'preflight.json'),expected_scene={'views':data['images'],'initial_colmap_points':data['initial_COLMAP_points'],'half_resolution':data['half_resolution']},scientific_scope='Single resolved DTU scan37 half30k paper-text entry; no automatic later scene. Full suite still pending.',suite_parent_config=str(parent),suite_parent_config_sha256=sha256(parent),negative_result_review=str(OUT/'NEGATIVE_RESULT_REVIEW.json'))
 c['runtime_env']['PYTHONPATH']=str(H/'full_reproduction_v01/precision_v01/build/variant_python')+':'+str(CODE/'runtime')+':'+str(BASE)+':'+c['cwd']
 c['runtime_env']['OMP_NUM_THREADS']='2';c['runtime_env']['OPENBLAS_NUM_THREADS']='2';c['runtime_env']['MKL_NUM_THREADS']='2'
 # No changing scientific flags: only data/model/config pointers vary.
 replacements={old['data']:c['data'],old['model']:c['model'],old['gt']:c['gt'],str(parent):str(path)}
 c['train_command']=[replacements.get(x,x) for x in c['train_command']]
 c['eval_command']=[replacements.get(x,x) for x in c['eval_command']]
 c.pop('tsdf_command');c['tsdf_implementation']='sealed cached export, CPU C24 values plus frozen sparse allocation adapter'
 python=c['train_command'][0]
 c['stage_commands']={s:[python,str(CODE/'runtime/gpu_stages.py'),'--config',str(path),'--stage',s] for s in ['smoke','train','export','tsdf','eval']}
 c['reports']={s:str(state/(s+'.report.json')) for s in c['stage_commands']}
 validate_config_scope(c)
 mapping={'runner.py':BASE/'runner.py','pilot_runtime.py':BASE/'pilot_runtime.py','gpu_stages.py':BASE/'gpu_stages.py','shared_runner.py':H/'stage2/shared/shared_runner.py','suite_runner.py':CODE.parent/'precision_v01/strict_pilot_runner.py'}
 diff=''.join(''.join(difflib.unified_diff(oldpath.read_text().splitlines(True),(CODE/'runtime'/name).read_text().splitlines(True),fromfile=str(oldpath),tofile=str(CODE/'runtime'/name))) for name,oldpath in mapping.items())
 (ART/'RUNTIME_FORK.diff').write_text(diff)
 sourcefiles=list(CODE.rglob('*.py'))+[CODE.parent/'tsdf_touch.py',CODE.parent/'empty_mesh.py',protocol,OUT/'SCAN37_DATA.json',OUT/'SCAN37_GT_ARCHIVE_RECEIPT.json',OUT/'NEGATIVE_RESULT_REVIEW.json',OUT/'cpu_tests/SUMMARY.json',ART/'RUNTIME_FORK.diff']
 for p in CODE.rglob('*.py'):ast.parse(p.read_text(),filename=str(p))
 manifest={'files':{str(p):sha256(p) for p in sourcefiles},'runtime_parent_files':{str(p):sha256(p) for p in mapping.values()},'native_unchanged':c['inputs']['candidate_native'],'training_source_unchanged':c['cwd'],'method_flags_unchanged_except_paths':True,'scientificdone':False}
 atomic_json(OUT/'RUNTIME_MANIFEST.json',manifest);shutil.copy2(OUT/'RUNTIME_MANIFEST.json',ART/'RUNTIME_MANIFEST.json')
 c['immutable_files'].update(manifest['files']);c['immutable_files'].update(data['training_hashes']);c['immutable_files'].update(data['evaluation_hashes']);c['immutable_files'][str(OUT/'RUNTIME_MANIFEST.json')]=sha256(OUT/'RUNTIME_MANIFEST.json')
 c['inputs'].update(data_manifest=sha256(OUT/'SCAN37_DATA.json'),suite_protocol=sha256(protocol),scene_entry=c['entry_id'],runtime_manifest=sha256(OUT/'RUNTIME_MANIFEST.json'),negative_result_review=sha256(OUT/'NEGATIVE_RESULT_REVIEW.json'))
 preflight={'passed':True,'meaning':'CPU/data/source/environment/native checks; real GPU smoke remains mandatory before train','parent_config_sha256':sha256(parent),'parent_immutable_count':len(old['immutable_files']),'new_immutable_count':len(c['immutable_files'])+1,'CPU_tests':tests['tests'],'from_scratch_COLMAP_points':50807,'candidate_native':c['inputs']['candidate_native'],'method_source_changed':False,'fresh_model':str(model),'root_free_bytes':shutil.disk_usage('/').free,'HDD_free_bytes':shutil.disk_usage(H).free,'estimated_next_scene_increment_GiB':12,'estimate_basis':'prior scan24 model/export/log footprint with reserve; not training-time prediction','scientificdone':False,'utc':datetime.datetime.now(datetime.timezone.utc).isoformat()}
 atomic_json(state/'preflight.json',preflight);c['immutable_files'][str(state/'preflight.json')]=sha256(state/'preflight.json');atomic_json(path,c)
 receipt={'config':str(path),'sha256':sha256(path),'immutable_files':len(c['immutable_files']),'command':[python,str(CODE/'runtime/suite_runner.py'),'--config',str(path)],'tracker_command':[python,str(CODE/'suite_progress.py'),'--config',str(path)],'train_command':c['train_command'],'CPU_tests':tests['tests'],'scientificdone':False}
 atomic_json(OUT/'SCAN37_LAUNCH.json',receipt);atomic_json(ART/'SCAN37_LAUNCH.json',receipt);print(json.dumps(receipt,indent=2))
if __name__=='__main__':main()
