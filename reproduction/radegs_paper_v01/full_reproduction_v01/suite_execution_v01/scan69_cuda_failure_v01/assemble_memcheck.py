"""Independent memcheck RED replay; no binary/source changes or old-state rewrites."""
import json,shutil,shlex,sys
from pathlib import Path
P=Path(__file__).resolve().parent;H=Path('/mnt/hdd1/u00134/radegs_paper_reproduction_v01');O=H/'full_reproduction_v01/suite_execution_v01/scan69_cuda_failure_v01';STATE=O/'memcheck/state';sys.path.insert(0,str(P));from replay_runner import ReplayRunner
from safety import sha256,verify_seal,atomic_json
oldpath=O/'replay/state/runner_config.json';assert sha256(oldpath)=='14abe8be95ef0b956ce613f2514d7ca664996fa2917a5af8285090097c6a5314';c=json.loads(oldpath.read_text())
for p,h in c['immutable_files'].items():assert sha256(p)==h,p
assert verify_seal(oldpath.parent/'smoke.seal.json','smoke',c['inputs']);st=json.loads((oldpath.parent/'runner_state.json').read_text());assert st['child_pid'] is None and not Path('/proc',str(st['runner_pid'])).exists()
assert shutil.disk_usage('/').free>=10*1024**3 and shutil.disk_usage(H).free>=55*1024**3;assert not STATE.exists()
model=H/'models/scan69_cuda_memcheck_v01';assert not model.exists();model.mkdir()
parent=json.loads(Path(c['parent_config']).read_text());snap=json.loads((O/'original_failure/MANIFEST.json').read_text());desc=json.loads((Path(parent['model'])/'restart.json').read_text());saved=next(x['copy'] for x in snap['files'] if x['original']==desc['path']);assert sha256(saved)==desc['sha256'];atomic_json(model/'restart.json',dict(desc,path=saved));pilot=dict(parent,model=str(model));pilotfile=STATE/'replay_pilot_config.json';atomic_json(pilotfile,pilot)
path=STATE/'runner_config.json';c.update(model=str(model),state_dir=str(STATE),log_dir=str(STATE.parent/'logs'),preflight_report=str(STATE/'preflight.json'),diagnostic_output=str(STATE.parent/'outputs'),replay_pilot_config=str(pilotfile),synchronous_parent_config=str(oldpath),synchronous_parent_config_sha256=sha256(oldpath),scientific_scope='bounded500..1000 diagnostic under Compute Sanitizer memcheck; expected RED86 on device error, no full training')
exe=O/'tools/compute-sanitizer-12.6/compute-sanitizer';cmd=[str(exe),'--tool','memcheck','--error-exitcode','86','--target-processes','application-only','--destroy-on-device-error','context','--print-limit','20','--log-file',str(STATE.parent/'memcheck.log'),str(H/'envs/c24_py39/bin/python'),str(P/'replay_worker.py'),'--config',str(path)]
c['stage_commands']={'smoke':cmd};c['reports']={'smoke':str(STATE/'smoke.report.json')}
copy=json.loads((O/'tools/SANITIZER_COPY_MANIFEST.json').read_text());extra={x['copy']:x['sha256'] for x in copy['files']}
for p in [Path(__file__),pilotfile,O/'tools/SANITIZER_COPY_MANIFEST.json',O/'tools/VERSION.txt',O/'tools/HELP.txt']:extra[str(p)]=sha256(p)
manifest={'files':extra,'source_native_environment_unchanged':True,'instrumentation':'runtime memcheck only; private copied tool12.6, native stays12.1-compiled original digest','expected_error_exitcode':86,'previous_diagnostic_config_sha256':sha256(oldpath),'scientificdone':False};atomic_json(STATE/'source_manifest.json',manifest);c['immutable_files'].update(extra);c['immutable_files'][str(STATE/'source_manifest.json')]=sha256(STATE/'source_manifest.json');c['inputs']['memcheck_diagnostic']=sha256(STATE/'source_manifest.json')
atomic_json(STATE/'preflight.json',{'passed':True,'meaning':'previous actual GPU RED and inputs verified; sanitizer binary copied/hash verified; same tested runner scope and500..1000 bound','scientificdone':False});c['immutable_files'][str(STATE/'preflight.json')]=sha256(STATE/'preflight.json');atomic_json(path,c)
e=ReplayRunner(path,query=lambda:None)
try:e.tick(None);assert e.child is None and e.state['status']=='WAITING_FOR_LOW_LOAD_GPU'
finally:e.close()
launch=STATE.parent/'launch.sh';run=[str(H/'envs/c24_py39/bin/python'),str(P/'replay_runner.py'),'--config',str(path)];launch.write_text('#!/bin/bash\nset -eu\nexport PYTHONDONTWRITEBYTECODE=1\nexport TMPDIR='+shlex.quote(str(H/'tmp'))+'\nexec '+shlex.join(run)+' >> '+shlex.quote(str(STATE.parent/'supervisor.log'))+' 2>&1\n');launch.chmod(0o700)
r={'config':str(path),'sha256':sha256(path),'immutable_files':len(c['immutable_files']),'command':run,'stage_command':cmd,'launch':str(launch),'tmux':'radegs-scan69-memcheck-v01','scientificdone':False};atomic_json(STATE.parent/'LAUNCH.json',r);print(json.dumps(r,indent=2))
