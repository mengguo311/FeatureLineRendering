"""New read-only diagnostic state; keep failed production eval/config immutable."""
import ast,json,shutil,subprocess,sys,shlex
from pathlib import Path
P=Path(__file__).resolve().parent;W=P.parents[4];H=Path('/mnt/hdd1/u00134/radegs_paper_reproduction_v01');S=H/'full_reproduction_v01/suite_execution_v01';O=S/'scan63_result_v01';STATE=O/'gpu_cull/state'
sys.path.insert(0,str(P));from cull_runner import CullDiagnosticRunner
from safety import atomic_json,sha256,verify_seal
parent=S/'scan63_v01/state/runner_config.json';assert sha256(parent)=='76e495e4f2b924e88d05a3a8f97e10a320c1a44c5811315f40b679054278758a';c=json.loads(parent.read_text())
for p,d in c['immutable_files'].items():assert sha256(p)==d,p
for stage in ['smoke','train','export','tsdf']:assert verify_seal(parent.parent/(stage+'.seal.json'),stage,c['inputs'])
r=json.loads((parent.parent/'runner_state.json').read_text());assert r['child_pid'] is None and not Path('/proc',str(r['runner_pid'])).exists()
assert shutil.disk_usage('/').free>=10*1024**3 and shutil.disk_usage(H).free>=51*1024**3
assert not STATE.exists();config=STATE/'runner_config.json'
c.update(state_dir=str(STATE),log_dir=str(STATE.parent/'logs'),preflight_report=str(STATE/'preflight.json'),parent_config=str(parent),parent_config_sha256=sha256(parent),cull_diagnostic_only=True,diagnostic_output=str(STATE.parent/'outputs'),scientific_scope='read-only literal author cull on scan63 raw TSDF mesh; no train/export or metrics')
for k in ['train_command','eval_command','tsdf_command']:c.pop(k,None)
c['stage_commands']={'smoke':[str(H/'envs/c24_py39/bin/python'),str(P/'cull_gpu_worker.py'),'--config',str(config)]};c['reports']={'smoke':str(STATE/'smoke.report.json')}
files=[*P.glob('*.py'),O/'logs/TEST_RED.log',O/'logs/TEST_GREEN.log',O/'diagnosis/cull_cpu_arrays.npz',O/'diagnosis/cull_cpu_reproduction.json',Path(c['model'])/'recon.ply',parent]
assert 'Ran 8 tests' in (O/'logs/TEST_GREEN.log').read_text() and '\nOK\n' in (O/'logs/TEST_GREEN.log').read_text()
manifest={'parent_config_sha256':sha256(parent),'files':{str(p.resolve()):sha256(p) for p in files},'scientific_source_native_unchanged':True,'diagnostic_only':True,'scientificdone':False};atomic_json(STATE/'manifest.json',manifest)
c['immutable_files'].update(manifest['files']);c['immutable_files'][str(STATE/'manifest.json')]=sha256(STATE/'manifest.json');c['inputs']['cull_gpu_diagnostic']=sha256(STATE/'manifest.json')
atomic_json(STATE/'preflight.json',{'passed':True,'scope':'CPU controls and original artifact hashes passed; GPU negative-outcome verification pending','root_free_bytes':shutil.disk_usage('/').free,'HDD_free_bytes':shutil.disk_usage(H).free,'scientificdone':False});c['immutable_files'][str(STATE/'preflight.json')]=sha256(STATE/'preflight.json');atomic_json(config,c)
e=CullDiagnosticRunner(config,query=lambda:None)
try:e.tick(None);assert e.child is None and e.state['status']=='WAITING_FOR_LOW_LOAD_GPU'
finally:e.close()
cmd=[str(H/'envs/c24_py39/bin/python'),str(P/'cull_runner.py'),'--config',str(config)]
launch=STATE.parent/'launch.sh';launch.write_text('#!/bin/bash\nset -eu\nexport PYTHONDONTWRITEBYTECODE=1\nexport TMPDIR='+shlex.quote(str(H/'tmp'))+'\nexec '+shlex.join(cmd)+' >> '+shlex.quote(str(STATE.parent/'supervisor.log'))+' 2>&1\n');launch.chmod(0o700)
receipt={'config':str(config),'sha256':sha256(config),'command':cmd,'tmux':'radegs-scan63-cull-diagnostic-v01','launch':str(launch),'immutable_files':len(c['immutable_files']),'scientificdone':False};atomic_json(STATE.parent/'LAUNCH.json',receipt);print(json.dumps(receipt,indent=2))
