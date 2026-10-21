"""Seal unit010 only; preserve frozen sources, science failures and runtime receipts."""
from common import *
import shutil,subprocess
from datetime import datetime,timezone
U=OUT.parent/'unit_010'
assert subprocess.check_output(['git','branch','--show-current'],text=True).strip()=='partwise-sketch-hatching-p1-v02'
assert not (U/'SEAL.json').exists()
assert not subprocess.check_output(['git','status','--porcelain'],text=True).strip()
status=json.loads((U/'STATUS.json').read_text());assert status['execution_state']=='complete'
for p,h in json.loads((U/'SOURCE_LOCK.json').read_text())['files'].items():assert sha(p)==h,p
for name,keys in {'STATUS.json':['stage','execution_state','scientific_verdict','tests','artifacts','blockers','outline_milestone','p1_progress'],'NEXT.json':['action','recommended_next_step','hypothesis','fixed_controls','go_no_go','blockers','evidence_paths','p1_distance_reduced','estimated_next_minutes']}.items():
    record=json.loads((U/name).read_text());assert all(k in record for k in keys)
for name in status['artifacts']:assert (U/name).exists(),name
for p in sorted((WORK/'experiments/partwise_sketch_hatching_v02').glob('*unit010.py')):
    dest=U/'source_snapshot_final'/p.relative_to(WORK);dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,dest)
for name in ('docs/partwise_sketch_hatching_v02/LENGTH_CLI_ZH.md','docs/partwise_sketch_hatching_v02/REPORT_unit010_ZH.md','docs/partwise_sketch_hatching_v02/PROTOCOL_unit010.json','docs/partwise_sketch_hatching/experiment_outline_v1.md'):
    dest=U/'source_snapshot_final'/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(WORK/name,dest)
commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
write_json(U/'FINAL_SOURCE.json',dict(commit=commit,branch='partwise-sketch-hatching-p1-v02',protocol_commit='3f4c95f1',implementation_commit='222d2a1e',source_lock_sha256=sha(U/'SOURCE_LOCK.json')))
root=shutil.disk_usage(WORK).free;hdd=shutil.disk_usage(U).free;total=sum(p.stat().st_size for p in U.parent.rglob('*') if p.is_file())
assert root>=2**30 and hdd>=10*2**30 and total<20*2**30
write_json(U/'RESOURCES_SEAL.json',dict(root_free_bytes=root,hdd_free_bytes=hdd,task_output_bytes=total,cpu_affinity=sorted(os.sched_getaffinity(0)),numeric_threads=1,gpu=False))
files=[]
for p in sorted(U.rglob('*')):
    if not p.is_file() or 'runtime' in p.relative_to(U).parts or p.parent==U and p.name in ('SEAL.json','SHA256_MANIFEST.json'):continue
    files.append(dict(root='unit',path=str(p.relative_to(U)),sha256=sha(p),bytes=p.stat().st_size))
write_json(U/'SHA256_MANIFEST.json',dict(roots={'unit':str(U)},files=files,source_commit=commit,excluded=['runtime/**','SEAL.json','SHA256_MANIFEST.json'],created_utc=datetime.now(timezone.utc).isoformat()))
for row in files:assert sha(U/row['path'])==row['sha256']
write_json(U/'SEAL.json',dict(manifest_path=str(U/'SHA256_MANIFEST.json'),manifest_sha256=sha(U/'SHA256_MANIFEST.json'),file_count=len(files),total_bytes=sum(r['bytes'] for r in files),source_commit=commit,protocol_source_commit='3f4c95f1',implementation_commit='222d2a1e',scientific_verdict=status['scientific_verdict'],created_utc=datetime.now(timezone.utc).isoformat(),producer_manifest_recheck=dict(checked_files=len(files),all_exact=True),verification='Producer seal after independent output/mask audit and actual image review. Parent review remains independent.',task_output_bytes=total))
print(json.dumps(dict(unit=str(U),files=len(files),source_commit=commit,manifest_sha256=sha(U/'SHA256_MANIFEST.json'))))
