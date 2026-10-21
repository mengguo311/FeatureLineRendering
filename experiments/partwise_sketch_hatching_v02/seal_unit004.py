"""Seal current unit only; never alter a historical manifest or output."""
from common import *
from datetime import datetime, timezone
import subprocess

OUT=OUT.parent/'unit_004'
assert not (OUT/'SEAL.json').exists()
status=json.loads((OUT/'STATUS.json').read_text())
assert status['execution_state'] in ('complete','failed','invalid')
assert subprocess.check_output(['git','branch','--show-current'],text=True).strip()=='partwise-sketch-hatching-p1-v02'
assert Path.cwd().resolve()==WORK.resolve()
for path,digest in json.loads((OUT/'SOURCE_LOCK.json').read_text())['files'].items():assert sha(path)==digest,path
commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
files=[]
for path in sorted(OUT.rglob('*')):
    if not path.is_file() or 'runtime' in path.relative_to(OUT).parts:
        continue
    if path.parent==OUT and path.name in ('SEAL.json','SHA256_MANIFEST.json'):
        continue
    files.append(dict(root='unit',path=str(path.relative_to(OUT)),bytes=path.stat().st_size,sha256=sha(path)))
sources=list((WORK/'experiments/partwise_sketch_hatching_v02').glob('*unit004.py'))
sources+=[WORK/'experiments/partwise_sketch_hatching_v02/stem_style.py']
sources+=list((WORK/'docs/partwise_sketch_hatching_v02').glob('*unit004*'))
for path in sorted(sources):
    files.append(dict(root='worktree',path=str(path.relative_to(WORK)),bytes=path.stat().st_size,sha256=sha(path)))
manifest=dict(source_commit=commit,created_utc=datetime.now(timezone.utc).isoformat(),
    roots=dict(unit=str(OUT),worktree=str(WORK)),files=files,
    exclusions=['runtime stdout/stderr (bound by execution receipt SHA)','manifest/seal self references'])
write_json(OUT/'SHA256_MANIFEST.json',manifest)
seal=dict(manifest_path=str(OUT/'SHA256_MANIFEST.json'),manifest_sha256=sha(OUT/'SHA256_MANIFEST.json'),
    file_count=len(files),total_bytes=sum(f['bytes'] for f in files),source_commit=commit,
    protocol_source_commit=json.loads((OUT/'SOURCE_LOCK.json').read_text())['git_commit'],
    scientific_verdict=status['scientific_verdict'],created_utc=datetime.now(timezone.utc).isoformat(),
    verification='Producer seal. Separate image/mask/media audit and delegated actual visual review precede seal; parent monitor remains independent.')
write_json(OUT/'SEAL.json',seal)
print(json.dumps(native(seal),ensure_ascii=False))
