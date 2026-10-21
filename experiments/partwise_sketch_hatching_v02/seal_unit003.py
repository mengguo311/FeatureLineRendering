"""Seal authorized unit003 artifacts and exact source provenance only."""
from common import *
from datetime import datetime, timezone
import subprocess

OUT=OUT.parent/'unit_003'
assert not (OUT/'SEAL.json').exists()
status=json.loads((OUT/'STATUS.json').read_text());assert status['execution_state']=='complete'
commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
for path,digest in json.loads((OUT/'SOURCE_LOCK.json').read_text())['files'].items():
    assert sha(path)==digest,path
files=[]
for path in sorted(OUT.rglob('*')):
    if not path.is_file() or 'runtime' in path.relative_to(OUT).parts or path.name in ('SEAL.json','SHA256_MANIFEST.json') and path.parent==OUT:
        continue
    files.append(dict(root='unit',path=str(path.relative_to(OUT)),bytes=path.stat().st_size,sha256=sha(path)))
sources=[WORK/'experiments/partwise_sketch_hatching_v02'/n for n in ('base_density.py','run_unit003.py','test_density_unit003.py','validate_unit003.py','receipt_unit003.py','finish_unit003.py','seal_unit003.py')]
sources+=list((WORK/'docs/partwise_sketch_hatching_v02').glob('*unit003*'))
for path in sorted(set(sources)):
    files.append(dict(root='worktree',path=str(path.relative_to(WORK)),bytes=path.stat().st_size,sha256=sha(path)))
manifest=dict(source_commit=commit,created_at_utc=datetime.now(timezone.utc).isoformat(),roots=dict(unit=str(OUT),worktree=str(WORK)),
              exclusions=['runtime stdout/stderr; immutable receipts bind log SHA','manifest/seal self references'],files=files)
write_json(OUT/'SHA256_MANIFEST.json',manifest)
seal=dict(manifest_path=str(OUT/'SHA256_MANIFEST.json'),manifest_sha256=sha(OUT/'SHA256_MANIFEST.json'),
          file_count=len(files),total_bytes=sum(f['bytes'] for f in files),source_commit=commit,
          protocol_source_commit=json.loads((OUT/'SOURCE_LOCK.json').read_text())['git_commit'],
          scientific_verdict=status['scientific_verdict'],verification='Producer seal; independent source/media/mask audit and separate actual-image review saved before sealing.',
          created_at_utc=datetime.now(timezone.utc).isoformat())
write_json(OUT/'SEAL.json',seal)
print(json.dumps(native(seal),ensure_ascii=False))
