import json,shutil,shlex,sys,ast
from pathlib import Path
P=Path(__file__).resolve().parent;sys.path.insert(0,str(P.parent));from replay_runner import ReplayRunner
from safety import sha256,atomic_json
H=Path('/mnt/hdd1/u00134/radegs_paper_reproduction_v01');O=H/'full_reproduction_v01/suite_execution_v01/scan69_cuda_failure_v01';D=O/'rgb_vjp_fix_v01';STATE=D/'state';oldpath=O/'vjp_contract_v01/state/runner_config.json';assert sha256(oldpath)=='7b51fc325b6ce05e2687e9fd4a6ecacb5550287253af6a74dae395d75986bd68';c=json.loads(oldpath.read_text())
for p,h in c['immutable_files'].items():assert sha256(p)==h,p
s=json.loads((oldpath.parent/'runner_state.json').read_text());assert s['returncode']==1 and s['child_pid'] is None and not Path('/proc',str(s['runner_pid'])).exists()
assert shutil.disk_usage('/').free>=10*1024**3 and shutil.disk_usage(H).free>=55*1024**3;assert not STATE.exists();model=H/'models/scan69_rgb_vjp_fix_v01';assert not model.exists();model.mkdir()
path=STATE/'runner_config.json';c.update(model=str(model),state_dir=str(STATE),log_dir=str(D/'logs/runner'),preflight_report=str(STATE/'preflight.json'),diagnostic_output=str(D/'outputs'),diagnostic_variant='RGB backward candidate; unchanged exact original RED test and tolerances; no optimizer',scientific_scope='GPU-only derivative validation, production not approved')
c['stage_commands']={'smoke':[str(H/'envs/c24_py39/bin/python'),str(P.parent/'vjp_contract_v01/worker.py'),'--config',str(path)]};c['reports']={'smoke':str(STATE/'smoke.report.json')}
old_prefix=str(H/'full_reproduction_v01/precision_v01/build/variant_python');assert c['runtime_env']['PYTHONPATH'].startswith(old_prefix+':');c['runtime_env']['PYTHONPATH']=str(D/'build/variant_python')+c['runtime_env']['PYTHONPATH'][len(old_prefix):]
extra=json.loads((D/'build/MANIFEST.json').read_text())['files']
files=[*P.glob('*.py'),*list((D/'logs').glob('*.log')),D/'build/MANIFEST.json',D/'build/COMMAND.json',D/'SOURCE_PATCH.diff',D/'math_vjp_legacy_RED.py',O/'VJP_CPU_REFERENCE.json',P.parent/'vjp_cpu_reference.py',*list((D/'build/variant_python').rglob('*.py')),oldpath,oldpath.parent/'runner_state.json',O/'vjp_contract_v01/outputs/1791543295378690047/result.json']
for p in files:extra[str(p.resolve())]=sha256(p)
assert 'FAILED (failures=2)' in (D/'logs/CPU_MATH_RED.log').read_text() and 'OK' in (D/'logs/CPU_MATH_GREEN.log').read_text()
m={'files':extra,'source_before':str(H/'sources/paper_text_precision_v01'),'original_native_sha256':'8e30fca654f14cc9b79ca987828ad01f2a27604744c057d00e2496f5f192bd10','forward_loss_schedule_unchanged':True,'backward_candidate':True,'original_NaN_cause_unproven':True,'production_approved':False};atomic_json(STATE/'source_manifest.json',m);c['immutable_files'].update(extra);c['immutable_files'][str(STATE/'source_manifest.json')]=sha256(STATE/'source_manifest.json');c['inputs']['rgb_vjp_candidate']=sha256(STATE/'source_manifest.json');atomic_json(STATE/'preflight.json',{'passed':True,'scope':'GPU candidate only; actual original GPU RED and CPU RED/GREEN preserved; unchanged test next','scientificdone':False});c['immutable_files'][str(STATE/'preflight.json')]=sha256(STATE/'preflight.json');atomic_json(path,c)
e=ReplayRunner(path,query=lambda:None)
try:e.tick(None);assert e.child is None and e.state['status']=='WAITING_FOR_LOW_LOAD_GPU'
finally:e.close()
run=[str(H/'envs/c24_py39/bin/python'),str(P.parent/'replay_runner.py'),'--config',str(path)];launch=D/'launch.sh';launch.write_text('#!/bin/bash\nset -eu\nexport PYTHONDONTWRITEBYTECODE=1\nexport TMPDIR='+shlex.quote(str(H/'tmp'))+'\nexec '+shlex.join(run)+' >> '+shlex.quote(str(D/'supervisor.log'))+' 2>&1\n');launch.chmod(0o700);r={'config':str(path),'sha256':sha256(path),'immutable_files':len(c['immutable_files']),'command':run,'launch':str(launch),'tmux':'radegs-scan69-rgb-vjp-fix-v01','scientificdone':False};atomic_json(D/'LAUNCH.json',r);print(json.dumps(r,indent=2))
