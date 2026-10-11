import json,shutil,shlex,sys,ast
from pathlib import Path
P=Path(__file__).resolve().parent;sys.path.insert(0,str(P.parent));from replay_runner import ReplayRunner
from safety import sha256,atomic_json
H=Path('/mnt/hdd1/u00134/radegs_paper_reproduction_v01');O=H/'full_reproduction_v01/suite_execution_v01/scan69_cuda_failure_v01';D=O/'vjp_contract_v01';STATE=D/'state';oldpath=O/'initcheck_v01/state/runner_config.json';assert sha256(oldpath)=='acd46e15fec70e25ccf955fdeeed9e523fe02a6f723409065855a69edd59dc3f';c=json.loads(oldpath.read_text())
for p,h in c['immutable_files'].items():assert sha256(p)==h,p
s=json.loads((oldpath.parent/'runner_state.json').read_text());assert s['child_pid'] is None and not Path('/proc',str(s['runner_pid'])).exists()
assert shutil.disk_usage('/').free>=10*1024**3 and shutil.disk_usage(H).free>=55*1024**3;assert not STATE.exists();model=H/'models/scan69_vjp_contract_v01';assert not model.exists();model.mkdir()
path=STATE/'runner_config.json';c.update(model=str(model),state_dir=str(STATE),log_dir=str(D/'logs'),preflight_report=str(STATE/'preflight.json'),diagnostic_output=str(D/'outputs'),diagnostic_variant='RGB single-Gaussian VJP linearity/FD, no optimizer, no scene training',scientific_scope='diagnostic only; original native; test backward argument contract')
c['stage_commands']={'smoke':[str(H/'envs/c24_py39/bin/python'),str(P/'worker.py'),'--config',str(path)]};c['reports']={'smoke':str(STATE/'smoke.report.json')}
for f in P.glob('*.py'):ast.parse(f.read_text())
files=[*P.glob('*.py'),oldpath,oldpath.parent/'runner_state.json'];extra={str(p.resolve()):sha256(p) for p in files};m={'files':extra,'original_native_unchanged':True,'fixture_parameters_fixed_before_GPU':True,'scientificdone':False};atomic_json(STATE/'source_manifest.json',m);c['immutable_files'].update(extra);c['immutable_files'][str(STATE/'source_manifest.json')]=sha256(STATE/'source_manifest.json');c['inputs']['vjp_contract']=sha256(STATE/'source_manifest.json');atomic_json(STATE/'preflight.json',{'passed':True,'scope':'actual GPU VJP/FD expected RED; no source math implementation change; no optimizer','scientificdone':False});c['immutable_files'][str(STATE/'preflight.json')]=sha256(STATE/'preflight.json');atomic_json(path,c)
e=ReplayRunner(path,query=lambda:None)
try:e.tick(None);assert e.child is None and e.state['status']=='WAITING_FOR_LOW_LOAD_GPU'
finally:e.close()
run=[str(H/'envs/c24_py39/bin/python'),str(P.parent/'replay_runner.py'),'--config',str(path)];launch=D/'launch.sh';launch.write_text('#!/bin/bash\nset -eu\nexport PYTHONDONTWRITEBYTECODE=1\nexport TMPDIR='+shlex.quote(str(H/'tmp'))+'\nexec '+shlex.join(run)+' >> '+shlex.quote(str(D/'supervisor.log'))+' 2>&1\n');launch.chmod(0o700);r={'config':str(path),'sha256':sha256(path),'immutable_files':len(c['immutable_files']),'command':run,'launch':str(launch),'tmux':'radegs-scan69-vjp-contract-v01','scientificdone':False};atomic_json(D/'LAUNCH.json',r);print(json.dumps(r,indent=2))
