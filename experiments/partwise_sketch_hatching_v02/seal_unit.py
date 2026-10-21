from common import *
import subprocess
from datetime import datetime, timezone

assert not (OUT/'SEAL.json').exists(), 'sealed unit is immutable'
assert json.loads((OUT/'STATUS.json').read_text())['execution_state']=='complete'
assert json.loads((OUT/'INDEPENDENT_VALIDATION.json').read_text())['verdict']=='PASS'
commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
assert subprocess.check_output(['git','branch','--show-current'],text=True).strip()=='partwise-sketch-hatching-p1-v02'
files=[]
for p in sorted(OUT.rglob('*')):
    if p.is_file() and 'runtime' not in p.relative_to(OUT).parts and p.name not in ('SEAL.json','SHA256_MANIFEST.json'):
        files.append(dict(root='unit',path=str(p.relative_to(OUT)),bytes=p.stat().st_size,sha256=sha(p)))
for base in ('experiments/partwise_sketch_hatching_v02','docs/partwise_sketch_hatching_v02'):
    for p in sorted((WORK/base).rglob('*')):
        if p.is_file() and '__pycache__' not in p.parts:
            files.append(dict(root='worktree',path=str(p.relative_to(WORK)),bytes=p.stat().st_size,sha256=sha(p)))
manifest=dict(source_commit=commit,created_at_utc=datetime.now(timezone.utc).isoformat(),roots=dict(worktree=str(WORK),unit=str(OUT)),
              exclusions=['runtime stdout/stderr','manifest and seal self references'],files=files)
write_json(OUT/'SHA256_MANIFEST.json',manifest)
seal=dict(manifest_sha256=sha(OUT/'SHA256_MANIFEST.json'),manifest_path=str(OUT/'SHA256_MANIFEST.json'),file_count=len(files),
          total_bytes=sum(x['bytes'] for x in files),source_commit=commit,scientific_verdict=json.loads((OUT/'STATUS.json').read_text())['scientific_verdict'],
          verification='Producer seal only; independent execution/data verification stored separately in INDEPENDENT_VALIDATION.json',created_at_utc=datetime.now(timezone.utc).isoformat())
write_json(OUT/'SEAL.json',seal)
for row in files:
    assert sha(Path(manifest['roots'][row['root']])/row['path'])==row['sha256']
print(json.dumps(seal))
