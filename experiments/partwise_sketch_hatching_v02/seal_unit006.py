"""Seal only authorized unit006 after actual software and visual evidence."""
from common import *
from datetime import datetime,timezone
import subprocess
U=OUT.parent/'unit_006';assert not (U/'SEAL.json').exists()
s=json.loads((U/'STATUS.json').read_text());assert s['execution_state'] in ('complete','failed','invalid')
assert subprocess.check_output(['git','branch','--show-current'],text=True).strip()=='partwise-sketch-hatching-p1-v02'
for row in json.loads((U/'SOURCE_LOCK.json').read_text())['files']:assert sha(row['path'])==row['sha256'],row['path']
for row in json.loads((U/'RECOVERY_LOCK.json').read_text())['files']:assert sha(row['path'])==row['sha256'],row['path']
commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip();rows=[]
for p in sorted(U.rglob('*')):
 if not p.is_file() or 'runtime' in p.relative_to(U).parts or p.name in ('SEAL.json','SHA256_MANIFEST.json') and p.parent==U:continue
 rows.append(dict(root='unit',path=str(p.relative_to(U)),bytes=p.stat().st_size,sha256=sha(p)))
paths=list((WORK/'experiments/partwise_sketch_hatching_v02').glob('*unit006.py'))+[WORK/'experiments/partwise_sketch_hatching_v02/reconstruction_dataset.py',WORK/'experiments/partwise_sketch_hatching_v02/radegs_camera_compat.py']
paths+=list((WORK/'docs/partwise_sketch_hatching_v02').glob('*unit006*'))+[WORK/'docs/partwise_sketch_hatching_v02/RECONSTRUCTION_INPUT_ZH.md']
for p in sorted(paths):rows.append(dict(root='worktree',path=str(p.relative_to(WORK)),bytes=p.stat().st_size,sha256=sha(p)))
m=dict(source_commit=commit,created_utc=datetime.now(timezone.utc).isoformat(),roots=dict(unit=str(U),worktree=str(WORK)),files=rows,exclusions=['runtime logs; receipt SHA binds content','manifest/seal self references'])
write_json(U/'SHA256_MANIFEST.json',m)
seal=dict(manifest_path=str(U/'SHA256_MANIFEST.json'),manifest_sha256=sha(U/'SHA256_MANIFEST.json'),file_count=len(rows),total_bytes=sum(x['bytes'] for x in rows),source_commit=commit,protocol_source_commit=json.loads((U/'SOURCE_LOCK.json').read_text())['git_commit'],scientific_verdict=s['scientific_verdict'],created_utc=datetime.now(timezone.utc).isoformat(),verification='Producer seal after independent RGB/camera/isolation and actual visual checks; parent monitor remains independent')
write_json(U/'SEAL.json',seal);print(json.dumps(native(seal)))
