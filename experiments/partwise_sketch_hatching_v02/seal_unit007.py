"""Seal current unit only, after completed independent tests and real visuals."""
from common import *
import subprocess,shutil
from datetime import datetime,timezone
U=OUT.parent/'unit_007'
def main():
 assert subprocess.check_output(['git','branch','--show-current'],text=True).strip()=='partwise-sketch-hatching-p1-v02'
 assert subprocess.run(['git','diff','--quiet','HEAD'],cwd=WORK).returncode==0
 status=json.loads((U/'STATUS.json').read_text());assert status['execution_state']=='complete'
 assert json.loads((U/'INDEPENDENT_VALIDATION.json').read_text())['verdict']=='VALID'
 for p,d in json.loads((U/'SOURCE_LOCK.json').read_text())['files'].items():assert sha(p)==d,p
 for name in ('NEXT.json','VISUAL_REVIEW.json','DELEGATED_VISUAL_REVIEW.json','REPORT_ZH.md','VIDEO_VALIDATION.json'):assert (U/name).is_file()
 assert not (U/'SEAL.json').exists() and not (U/'SHA256_MANIFEST.json').exists()
 commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
 entries=[]
 for p in sorted(U.rglob('*')):
  if p.is_file() and p.relative_to(U).parts[0]!='runtime' and p.name not in ('SEAL.json','SHA256_MANIFEST.json'):
   entries.append(dict(root='unit',path=str(p.relative_to(U)),bytes=p.stat().st_size,sha256=sha(p)))
 paths=sorted((WORK/'experiments/partwise_sketch_hatching_v02').glob('*unit007.py'))
 paths+=sorted((WORK/'docs/partwise_sketch_hatching_v02').glob('*unit007*'))
 for p in paths:
  if p.is_file():entries.append(dict(root='worktree',path=str(p.relative_to(WORK)),bytes=p.stat().st_size,sha256=sha(p)))
 task_bytes=sum(p.stat().st_size for p in U.parent.rglob('*') if p.is_file())
 assert task_bytes<20*2**30 and shutil.disk_usage(WORK).free>=2**30 and shutil.disk_usage(U).free>=10*2**30
 manifest=dict(source_commit=commit,created_utc=datetime.now(timezone.utc).isoformat(),roots=dict(unit=str(U),worktree=str(WORK)),files=entries,exclusions=['runtime stdout/stderr; execution receipts bind their hashes','manifest and seal self references'])
 write_json(U/'SHA256_MANIFEST.json',manifest)
 for entry in entries:
  p=(U if entry['root']=='unit' else WORK)/entry['path'];assert p.stat().st_size==entry['bytes'] and sha(p)==entry['sha256'],p
 seal=dict(manifest_path=str(U/'SHA256_MANIFEST.json'),manifest_sha256=sha(U/'SHA256_MANIFEST.json'),file_count=len(entries),total_bytes=sum(e['bytes'] for e in entries),source_commit=commit,protocol_source_commit=json.loads((U/'SOURCE_LOCK.json').read_text())['commit'],scientific_verdict=status['scientific_verdict'],created_utc=datetime.now(timezone.utc).isoformat(),producer_manifest_recheck=dict(checked_files=len(entries),all_exact=True),verification='Producer seal after independent saved-output validation and actual image review; parent supervision remains independent.',task_output_bytes=task_bytes)
 write_json(U/'SEAL.json',seal);print(json.dumps(native(seal)))
if __name__=='__main__':main()
