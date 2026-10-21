"""Read-only previous producer seal verification; evidence goes only to unit004."""
from common import *
from datetime import datetime, timezone

CURRENT=OUT.parent/'unit_004'
PREVIOUS=OUT.parent/'unit_003'
manifest=json.loads((PREVIOUS/'SHA256_MANIFEST.json').read_text())
seal=json.loads((PREVIOUS/'SEAL.json').read_text())
failures=[]
if sha(PREVIOUS/'SHA256_MANIFEST.json')!=seal['manifest_sha256']:
    failures.append(dict(path='SHA256_MANIFEST.json',reason='seal digest mismatch'))
for row in manifest['files']:
    path=Path(manifest['roots'][row['root']])/row['path']
    if not path.is_file() or path.stat().st_size!=row['bytes'] or sha(path)!=row['sha256']:
        failures.append(dict(path=str(path),reason='missing/size/digest mismatch'))
result=dict(scope='Read-only complete unit003 manifest, including previous worktree sources; no historical writes',
    files_checked=len(manifest['files']),failures=failures,valid=not failures,
    previous_seal_sha256=sha(PREVIOUS/'SEAL.json'),checked_utc=datetime.now(timezone.utc).isoformat())
write_json(CURRENT/'HISTORICAL_SEAL_AUDIT.json',result)
print(json.dumps(native(result)));sys.exit(0 if not failures else 1)
