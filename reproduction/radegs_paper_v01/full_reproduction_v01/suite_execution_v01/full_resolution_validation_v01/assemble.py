"""Seal an independently gated full-resolution smoke; never train/eval."""
import ast,datetime,json,shutil,subprocess,sys
from pathlib import Path
CODE=Path(__file__).resolve().parent;ROOT=CODE.parents[4];SCOPE=CODE.parent
sys.path.insert(0,str(SCOPE/'full_resolution_runtime_v01'));sys.path.append(str(ROOT/'reproduction/radegs_paper_v01/stage2'))
from safety import atomic_json,sha256,verify_seal
from smoke_runner import FullResolutionSmokeRunner,validate_probe
H=Path('/mnt/hdd1/u00134/radegs_paper_reproduction_v01');S=H/'full_reproduction_v01/suite_execution_v01';OUT=S/'full_resolution_validation_v01';STATE=OUT/'state';ART=ROOT/'artifacts/radegs_paper_reproduction_v01/full_reproduction_v01/suite_execution_v01/full_resolution_validation_v01'
parent=S/'scan55_v01/state/runner_config.json';assert sha256(parent)=='ed7b4c9613887c2642d4c8c2c5778bb7d23dbcbf798502721b42d1b8372e5b27';c=json.loads(parent.read_text())
for p,h in c['immutable_files'].items():assert sha256(p)==h,p
for stage in ['smoke','train','export']:assert verify_seal(parent.parent/(stage+'.seal.json'),stage,c['inputs'])
old_state=json.loads((parent.parent/'runner_state.json').read_text());assert old_state['child_pid'] is None and not Path('/proc',str(old_state['runner_pid'])).exists()
assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()=='00bb67c4ae39157906bcda6abc8760cc37679414'
assert not subprocess.check_output(['git','status','--porcelain'],cwd=H/'sources/RaDe-GS',text=True).strip()
assert shutil.disk_usage('/').free>=10*1024**3 and shutil.disk_usage(H).free-2*1024**3>=50*1024**3
assert not STATE.exists() and 'OK' in (OUT/'logs/GREEN.log').read_text()
oldruntime=SCOPE/'runtime';runtime=SCOPE/'full_resolution_runtime_v01';config=STATE/'runner_config.json'
c.update(entry_id='DTU_scan55_full30k_TSDF',resolution_divisor=1,full_resolution_validation_only=True,model=str(H/'models/scan55_full_resolution_validation_v01'),state_dir=str(STATE),log_dir=str(OUT/'logs'),preflight_report=str(STATE/'preflight.json'),parent_config=str(parent),parent_config_sha256=sha256(parent),scientific_scope='One initial-COLMAP full-resolution GPU smoke only; no optimizer/train/export/mesh/eval')
assert not Path(c['model']).exists();c['expected_scene'].pop('half_resolution');c['expected_scene']['image_resolution']=[1554,1162]
c['runtime_env']['PYTHONPATH']=c['runtime_env']['PYTHONPATH'].replace(str(oldruntime),str(runtime))
for k in ['train_command','eval_command','tsdf_command']:c.pop(k,None)
c['stage_commands']={'smoke':[str(H/'envs/c24_py39/bin/python'),str(CODE/'smoke_worker.py'),'--config',str(config)]};c['reports']={'smoke':str(STATE/'smoke.report.json')};validate_probe(c)
files=[*runtime.glob('*.py'),*CODE.glob('*.py'),OUT/'logs/RED.log',OUT/'logs/GREEN.log',S/'full_resolution_runtime_v01/CPU_ISOLATED_SUMMARY.json']
for p in files:
 if p.suffix=='.py':ast.parse(p.read_text())
manifest={'parent_config':str(parent),'parent_sha256':sha256(parent),'native_unchanged':c['inputs']['candidate_native'],'files':{str(p):sha256(p) for p in files},'resolution_only_engineering_changes':True,'zero_optimizer_steps':True,'production_scan55_state_unchanged':True,'scientificdone':False};atomic_json(STATE/'source_manifest.json',manifest)
c['immutable_files'].update(manifest['files']);c['immutable_files'][str(STATE/'source_manifest.json')]=sha256(STATE/'source_manifest.json');c['inputs']=dict(c['inputs'],scene_entry=c['entry_id'],full_resolution_smoke=sha256(STATE/'source_manifest.json'))
atomic_json(STATE/'preflight.json',{'passed':True,'meaning':'CPU controls and source/data/native verified; actual full-resolution GPU smoke not yet run','root_free_bytes':shutil.disk_usage('/').free,'HDD_free_bytes':shutil.disk_usage(H).free,'estimated_disk_increment_GiB':2,'estimate_basis':'diagnostic tensors/logs without model training','scientificdone':False});c['immutable_files'][str(STATE/'preflight.json')]=sha256(STATE/'preflight.json');atomic_json(config,c)
e=FullResolutionSmokeRunner(config,query=lambda:None)
try:e.tick(None);assert e.child is None and e.state['status']=='WAITING_FOR_LOW_LOAD_GPU'
finally:e.close()
receipt={'config':str(config),'sha256':sha256(config),'immutable_files':len(c['immutable_files']),'command':[str(H/'envs/c24_py39/bin/python'),str(CODE/'smoke_runner.py'),'--config',str(config)],'training_dispatch_permitted':False,'UTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'scientificdone':False};atomic_json(OUT/'LAUNCH.json',receipt);ART.mkdir();atomic_json(ART/'LAUNCH.json',receipt);shutil.copy2(STATE/'source_manifest.json',ART/'SOURCE_MANIFEST.json');print(json.dumps(receipt,indent=2))
