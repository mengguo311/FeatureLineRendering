"""Seal isolated synchronous diagnostic; preserve original failed model/state."""
import json,shutil,shlex,sys
from pathlib import Path
P=Path(__file__).resolve().parent;W=P.parents[4];H=Path('/mnt/hdd1/u00134/radegs_paper_reproduction_v01');S=H/'full_reproduction_v01/suite_execution_v01';O=S/'scan69_cuda_failure_v01';STATE=O/'replay/state';sys.path.insert(0,str(P));from replay_runner import ReplayRunner
from safety import atomic_json,sha256,verify_seal
parent=S/'scan69_v01/state/runner_config.json';assert sha256(parent)=='1f98695bdc8fa2f726141dbc6278e1e83b2ad31788b4f3e956b7224a9fafda9c';c=json.loads(parent.read_text());pilot=json.loads(parent.read_text())
for p,h in c['immutable_files'].items():assert sha256(p)==h,p
assert verify_seal(parent.parent/'smoke.seal.json','smoke',c['inputs'])
s=json.loads((parent.parent/'runner_state.json').read_text());assert s['child_pid'] is None and not Path('/proc',str(s['runner_pid'])).exists()
assert shutil.disk_usage('/').free>=10*1024**3 and shutil.disk_usage(H).free>=55*1024**3
assert not STATE.exists();model=H/'models/scan69_cuda_replay_v01';assert not model.exists();model.mkdir()
manifest0=json.loads((O/'original_failure/MANIFEST.json').read_text());old=json.loads((Path(c['model'])/'restart.json').read_text());assert old['completed_iteration']==500
copy=next(x['copy'] for x in manifest0['files'] if x['original']==old['path']);assert sha256(copy)==old['sha256'];pointer=dict(old,path=copy);atomic_json(model/'restart.json',pointer)
pilot.update(model=str(model));pilotpath=STATE/'replay_pilot_config.json';atomic_json(pilotpath,pilot)
path=STATE/'runner_config.json';c.update(model=str(model),state_dir=str(STATE),log_dir=str(STATE.parent/'logs'),preflight_report=str(STATE/'preflight.json'),parent_config=str(parent),parent_config_sha256=sha256(parent),synchronous_replay_only=True,diagnostic_output=str(STATE.parent/'outputs'),replay_pilot_config=str(pilotpath),scientific_scope='read-only original500 checkpoint; new diagnostic model; exact training method prefix only, sync and hard stop1000; no scientific retry or full training')
for k in ['train_command','eval_command','tsdf_command']:c.pop(k,None)
c['runtime_env']['CUDA_LAUNCH_BLOCKING']='1';c['stage_commands']={'smoke':[str(H/'envs/c24_py39/bin/python'),str(P/'replay_worker.py'),'--config',str(path)]};c['reports']={'smoke':str(STATE/'smoke.report.json')}
assert 'Ran 8 tests' in (O/'logs/CPU_RESUME_GREEN.log').read_text() and '\nOK\n' in (O/'logs/CPU_RESUME_GREEN.log').read_text()
files=[*P.glob('*.py'),O/'logs/CPU_RED.log',O/'logs/CPU_GREEN.log',O/'logs/CPU_RESUME_RED.log',O/'logs/CPU_RESUME_GREEN.log',Path(copy),pilotpath,O/'original_failure/MANIFEST.json',parent]
m={'files':{str(p.resolve()):sha256(p) for p in files},'checkpoint_path_only_relocated':{'old_path':old['path'],'new_path':copy,'sha256':old['sha256'],'payload_provenance_unchanged':True},'scientific_source_native_unchanged':True,'training_inputs_provenance_preserved_in_pilot':True,'diagnostic_inputs_separately_sealed':True,'hard_max_completed_iteration':1000,'scientificdone':False};atomic_json(STATE/'source_manifest.json',m);c['immutable_files'].update(m['files']);c['immutable_files'][str(STATE/'source_manifest.json')]=sha256(STATE/'source_manifest.json');c['inputs']['synchronous_replay_diagnostic']=sha256(STATE/'source_manifest.json')
atomic_json(STATE/'preflight.json',{'passed':True,'meaning':'original source/native/checkpoint verified;8CPU controls pass; actual synchronous GPU diagnostic pending','root_free_bytes':shutil.disk_usage('/').free,'HDD_free_bytes':shutil.disk_usage(H).free,'scientificdone':False});c['immutable_files'][str(STATE/'preflight.json')]=sha256(STATE/'preflight.json');atomic_json(path,c)
e=ReplayRunner(path,query=lambda:None)
try:e.tick(None);assert e.child is None and e.state['status']=='WAITING_FOR_LOW_LOAD_GPU'
finally:e.close()
cmd=[str(H/'envs/c24_py39/bin/python'),str(P/'replay_runner.py'),'--config',str(path)];launch=STATE.parent/'launch.sh';launch.write_text('#!/bin/bash\nset -eu\nexport PYTHONDONTWRITEBYTECODE=1\nexport TMPDIR='+shlex.quote(str(H/'tmp'))+'\nexec '+shlex.join(cmd)+' >> '+shlex.quote(str(STATE.parent/'supervisor.log'))+' 2>&1\n');launch.chmod(0o700)
receipt={'config':str(path),'sha256':sha256(path),'command':cmd,'launch':str(launch),'tmux':'radegs-scan69-sync-replay-v01','immutable_files':len(c['immutable_files']),'original_production_failure_preserved':True,'scientificdone':False};atomic_json(STATE.parent/'LAUNCH.json',receipt);print(json.dumps(receipt,indent=2))
