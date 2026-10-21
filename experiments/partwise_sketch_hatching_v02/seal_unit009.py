"""Seal unit009 outputs and final sources; runtime stdout remains outside science."""
from common import *
import shutil,subprocess
from datetime import datetime,timezone
U=OUT.parent/'unit_009'
assert subprocess.check_output(['git','branch','--show-current'],text=True).strip()=='partwise-sketch-hatching-p1-v02'
assert not (U/'SEAL.json').exists()
status=json.loads((U/'STATUS.json').read_text());assert status['execution_state']=='complete'
assert not subprocess.check_output(['git','status','--porcelain'],text=True).strip()
for p,h in json.loads((U/'SOURCE_LOCK.json').read_text())['files'].items():assert sha(p)==h,p
required={'STATUS.json':['stage','execution_state','scientific_verdict','tests','artifacts','blockers','outline_milestone','p1_progress'],
          'NEXT.json':['action','recommended_next_step','hypothesis','fixed_controls','go_no_go','blockers','evidence_paths','p1_distance_reduced','estimated_next_minutes']}
for name,keys in required.items():
    record=json.loads((U/name).read_text());assert all(k in record for k in keys)
for name in status['artifacts']:assert (U/name).exists(),name
for name in ('EXECUTION_prepare.json','EXECUTION_prepare_recovery.json'):assert json.loads((U/name).read_text())['returncode']==1
names=['experiments/partwise_sketch_hatching_v02/finish_unit009.py','experiments/partwise_sketch_hatching_v02/seal_unit009.py','experiments/partwise_sketch_hatching_v02/prepare_unit009.py','docs/partwise_sketch_hatching_v02/DENSITY_CLI_ZH.md','docs/partwise_sketch_hatching_v02/REPORT_unit009_ZH.md','docs/partwise_sketch_hatching_v02/PROTOCOL_unit009.json','docs/partwise_sketch_hatching/experiment_outline_v1.md']
for name in names:
    dst=U/'source_snapshot_final'/name;dst.parent.mkdir(parents=True,exist_ok=True);assert not dst.exists();shutil.copyfile(WORK/name,dst)
shutil.copyfile(U.parent.parent/'orchestration/BRIEF.md',U/'BRIEF_SNAPSHOT.md')
commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
write_json(U/'FINAL_SOURCE.json',dict(commit=commit,branch='partwise-sketch-hatching-p1-v02',protocol_commit='6107be74',implementation_commit='dfac67e8',source_lock_sha256=sha(U/'SOURCE_LOCK.json')))
rootfree=shutil.disk_usage(WORK).free;hddfree=shutil.disk_usage(U).free;taskbytes=sum(p.stat().st_size for p in U.parent.rglob('*') if p.is_file())
assert rootfree>=2**30 and hddfree>=10*2**30 and taskbytes<20*2**30
write_json(U/'RESOURCES_SEAL.json',dict(root_free_bytes=rootfree,hdd_free_bytes=hddfree,task_output_bytes=taskbytes,cpu_affinity=sorted(os.sched_getaffinity(0)),numeric_threads=1,gpu=False))
files=[]
for p in sorted(U.rglob('*')):
    if not p.is_file() or 'runtime' in p.relative_to(U).parts or p.name in ('SEAL.json','SHA256_MANIFEST.json') and p.parent==U:continue
    files.append(dict(root='unit',path=str(p.relative_to(U)),sha256=sha(p),bytes=p.stat().st_size))
manifest=dict(roots={'unit':str(U)},files=files,source_commit=commit,excluded=['runtime/**','SEAL.json','SHA256_MANIFEST.json'],created_utc=datetime.now(timezone.utc).isoformat())
write_json(U/'SHA256_MANIFEST.json',manifest)
for item in files:assert sha(U/item['path'])==item['sha256'],item['path']
write_json(U/'SEAL.json',dict(manifest_path=str(U/'SHA256_MANIFEST.json'),manifest_sha256=sha(U/'SHA256_MANIFEST.json'),file_count=len(files),total_bytes=sum(r['bytes'] for r in files),source_commit=commit,protocol_source_commit='6107be74',implementation_commit='dfac67e8',scientific_verdict=status['scientific_verdict'],created_utc=datetime.now(timezone.utc).isoformat(),producer_manifest_recheck=dict(checked_files=len(files),all_exact=True),verification='Producer seal after independent saved-output/analytic-mask validation and root plus delegated actual image reviews; parent supervision is independent.',task_output_bytes=taskbytes))
print(json.dumps(dict(unit=str(U),files=len(files),source_commit=commit,manifest_sha256=sha(U/'SHA256_MANIFEST.json'))))
