"""Explicit pre-launch reseal; preserve old config/source, no scientific seal rewrite."""
from pathlib import Path
import json,sys,shutil,datetime
CODE=Path(__file__).resolve().parent;ROOT=CODE.parents[4];H=Path('/mnt/hdd1/u00134/radegs_paper_reproduction_v01/full_reproduction_v01/suite_execution_v01/full_resolution_validation_v01');A=ROOT/'artifacts/radegs_paper_reproduction_v01/full_reproduction_v01/suite_execution_v01/full_resolution_validation_v01';sys.path.insert(0,str(CODE.parent/'full_resolution_runtime_v01'));sys.path.append(str(ROOT/'reproduction/radegs_paper_v01/stage2'))
from safety import sha256,atomic_json
from smoke_runner import FullResolutionSmokeRunner
cp=H/'state/runner_config.json';c=json.loads(cp.read_text());oldsha=sha256(cp);assert sha256(H/'unlaunched_provenance_correction_before/runner_config.json')==oldsha
assert not list((H/'state').glob('*.seal.json')) and not (H/'state/smoke.report.json').exists();s=json.loads((H/'state/runner_state.json').read_text());assert s.get('child_pid') is None and not Path('/proc',str(s['runner_pid'])).exists()
changed={str(CODE/n) for n in ['smoke_runner.py','test_smoke_runner.py','assemble.py']}
for p,d in c['immutable_files'].items():
 if p in changed:assert sha256(H/'unlaunched_provenance_correction_before'/Path(p).name)==d
 else:assert sha256(p)==d,p
assert 'OK' in (H/'logs/PROVENANCE_GREEN.log').read_text()
manifest=json.loads((H/'state/source_manifest.json').read_text());files=[*map(Path,changed),Path(__file__),H/'logs/PROVENANCE_RED.log',H/'logs/PROVENANCE_GREEN.log'];manifest['files'].update({str(p):sha256(p) for p in files});manifest['unlaunched_correction']={'before_config_sha256':oldsha,'reason':'full-resolution top-level entry had stale inherited half-resolution inputs.scene_entry; caught by new CPU guard before any GPU launch','before_archive':str(H/'unlaunched_provenance_correction_before'),'GPU_executions_before_correction':0};atomic_json(H/'state/source_manifest.json',manifest)
c['inputs']['scene_entry']=c['entry_id'];c['inputs']['full_resolution_smoke']=sha256(H/'state/source_manifest.json');c['immutable_files'].update(manifest['files']);c['immutable_files'][str(H/'state/source_manifest.json')]=sha256(H/'state/source_manifest.json');atomic_json(cp,c)
e=FullResolutionSmokeRunner(cp,query=lambda:None)
try:e.tick(None);assert e.child is None and e.state['status']=='WAITING_FOR_LOW_LOAD_GPU'
finally:e.close()
r=json.loads((H/'LAUNCH.json').read_text());r.update(sha256=sha256(cp),immutable_files=len(c['immutable_files']),prelaunch_correction_before_sha256=oldsha);atomic_json(H/'LAUNCH.json',r);atomic_json(A/'LAUNCH.json',r);shutil.copy2(H/'state/source_manifest.json',A/'SOURCE_MANIFEST.json');atomic_json(A/'PRELAUNCH_PROVENANCE_CORRECTION.json',{'before':oldsha,'after':sha256(cp),'source_manifest':sha256(H/'state/source_manifest.json'),'TDD_RED':str(H/'logs/PROVENANCE_RED.log'),'TDD_GREEN':str(H/'logs/PROVENANCE_GREEN.log'),'old_config_used_for_GPU':False,'scientificdone':False});print(json.dumps(r,indent=2))
