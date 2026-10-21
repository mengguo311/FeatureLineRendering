"""Seal unit008 only; runtime stdout/logs and self-referential seals excluded."""
from common import *
import shutil,subprocess
from datetime import datetime,timezone
U=OUT.parent/'unit_008'
assert subprocess.check_output(['git','branch','--show-current'],text=True).strip()=='partwise-sketch-hatching-p1-v02'
assert not (U/'SEAL.json').exists()
status=json.loads((U/'STATUS.json').read_text());assert status['execution_state']=='complete'
for p,h in json.loads((U/'SOURCE_LOCK.json').read_text())['files'].items():assert sha(p)==h,p
names=['experiments/partwise_sketch_hatching_v02/finish_unit008.py','experiments/partwise_sketch_hatching_v02/seal_unit008.py','experiments/partwise_sketch_hatching_v02/prepare_unit008.py','docs/partwise_sketch_hatching_v02/DIRECTION_CLI_ZH.md','docs/partwise_sketch_hatching_v02/REPORT_unit008_ZH.md','docs/partwise_sketch_hatching_v02/PROTOCOL_unit008.json','docs/partwise_sketch_hatching/experiment_outline_v1.md']
for name in names:
    dst=U/'source_snapshot_final'/name;dst.parent.mkdir(parents=True,exist_ok=True);assert not dst.exists();shutil.copyfile(WORK/name,dst)
shutil.copyfile(U.parent.parent/'orchestration/BRIEF.md',U/'BRIEF_SNAPSHOT.md')
commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
write_json(U/'FINAL_SOURCE.json',dict(commit=commit,branch='partwise-sketch-hatching-p1-v02',protocol_commit='8fbeb96a',implementation_commit='f90367eb',validation_refinement_commit='dbd9a27a',source_lock_sha256=sha(U/'SOURCE_LOCK.json')))
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
write_json(U/'SEAL.json',dict(manifest_path=str(U/'SHA256_MANIFEST.json'),manifest_sha256=sha(U/'SHA256_MANIFEST.json'),file_count=len(files),total_bytes=sum(r['bytes'] for r in files),source_commit=commit,protocol_source_commit='dbd9a27a',scientific_verdict=status['scientific_verdict'],created_utc=datetime.now(timezone.utc).isoformat(),producer_manifest_recheck=dict(checked_files=len(files),all_exact=True),verification='Producer seal following independent saved-image/analytic-mask validation and two actual visual inspections; parent supervision remains independent.',task_output_bytes=taskbytes))
print(json.dumps(dict(unit=str(U),files=len(files),source_commit=commit,manifest_sha256=sha(U/'SHA256_MANIFEST.json'))))
