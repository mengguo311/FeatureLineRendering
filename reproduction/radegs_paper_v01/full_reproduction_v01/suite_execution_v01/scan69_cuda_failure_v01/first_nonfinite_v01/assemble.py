import json,shutil,shlex,sys
from pathlib import Path
P=Path(__file__).resolve().parent;sys.path.insert(0,str(P.parent));from replay_runner import ReplayRunner
from safety import sha256,atomic_json
H=Path('/mnt/hdd1/u00134/radegs_paper_reproduction_v01');O=H/'full_reproduction_v01/suite_execution_v01/scan69_cuda_failure_v01';D=O/'first_nonfinite_v01';STATE=D/'state';oldpath=O/'memcheck/state/runner_config.json';assert sha256(oldpath)=='81fe48a037b5ed16418174668f9edea1f2fa5bc41a0177cff80021fe4a95689e';c=json.loads(oldpath.read_text())
for p,h in c['immutable_files'].items():assert sha256(p)==h,p
s=json.loads((oldpath.parent/'runner_state.json').read_text());assert s['returncode']==86 and s['child_pid'] is None and not Path('/proc',str(s['runner_pid'])).exists()
assert shutil.disk_usage('/').free>=10*1024**3 and shutil.disk_usage(H).free>=55*1024**3;assert not STATE.exists()
model=H/'models/scan69_first_nonfinite_v01';assert not model.exists();model.mkdir();parent=json.loads(Path(c['parent_config']).read_text());# Fresh initialization; original500 checkpoint already has NaN, never resume it here.
pilotfile=STATE/'replay_pilot_config.json';atomic_json(pilotfile,dict(parent,model=str(model)))
path=STATE/'runner_config.json';c.update(model=str(model),state_dir=str(STATE),log_dir=str(D/'logs/runner'),preflight_report=str(STATE/'preflight.json'),diagnostic_output=str(D/'outputs'),replay_pilot_config=str(pilotfile),diagnostic_variant='first nonfinite from fresh initialization, at most500 iterations; stop before bad optimizer step; no native/method patch')
c['stage_commands']={'smoke':[str(H/'envs/c24_py39/bin/python'),str(P/'worker.py'),'--config',str(path)]};c['reports']={'smoke':str(STATE/'smoke.report.json')}
extra={}
for p in [*P.glob('*.py'),*list((D/'logs').glob('*.log')),pilotfile,O/'CHECKPOINT500_FINITE_AUDIT.json',O/'binning_probe_v01/state/smoke.seal.json',O/'binning_probe_v01/state/runner_config.json',P.parent/'binning_probe_v01/capture.py']:
 extra[str(p.resolve())]=sha256(p)
assert 'OK' in (D/'logs/CPU_GREEN.log').read_text()
m={'files':extra,'before_native_sha256':'8e30fca654f14cc9b79ca987828ad01f2a27604744c057d00e2496f5f192bd10','diagnostic_only':True,'scientificdone':False};atomic_json(STATE/'source_manifest.json',m);c['immutable_files'].update(extra);c['immutable_files'][str(STATE/'source_manifest.json')]=sha256(STATE/'source_manifest.json');c['inputs']['binning_probe']=sha256(STATE/'source_manifest.json');atomic_json(STATE/'preflight.json',{'passed':True,'scope':'first finite failure diagnostic only; original native unchanged; fresh initialization; actual GPU pending','scientificdone':False});c['immutable_files'][str(STATE/'preflight.json')]=sha256(STATE/'preflight.json');atomic_json(path,c)
e=ReplayRunner(path,query=lambda:None)
try:e.tick(None);assert e.child is None and e.state['status']=='WAITING_FOR_LOW_LOAD_GPU'
finally:e.close()
run=[str(H/'envs/c24_py39/bin/python'),str(P.parent/'replay_runner.py'),'--config',str(path)];launch=D/'launch.sh';launch.write_text('#!/bin/bash\nset -eu\nexport PYTHONDONTWRITEBYTECODE=1\nexport TMPDIR='+shlex.quote(str(H/'tmp'))+'\nexec '+shlex.join(run)+' >> '+shlex.quote(str(D/'supervisor.log'))+' 2>&1\n');launch.chmod(0o700);r={'config':str(path),'sha256':sha256(path),'immutable_files':len(c['immutable_files']),'command':run,'launch':str(launch),'tmux':'radegs-scan69-first-nonfinite-v01','scientificdone':False};atomic_json(D/'LAUNCH.json',r);print(json.dumps(r,indent=2))
