"""Read-only predecessor seal verification; current-unit evidence only."""
from common import *
U=OUT.parent/'unit_006';P=U.parent/'unit_005'
s=json.loads((P/'SEAL.json').read_text());m=json.loads((P/'SHA256_MANIFEST.json').read_text())
failed=[]
if sha(P/'SHA256_MANIFEST.json')!=s['manifest_sha256']:failed.append('manifest digest')
for row in m['files']:
 p=Path(m['roots'][row['root']])/row['path']
 if not p.is_file() or p.stat().st_size!=row['bytes'] or sha(p)!=row['sha256']:failed.append(str(p))
write_json(U/'HISTORICAL_SEAL_AUDIT.json',dict(previous='unit005',files_checked=len(m['files']),failures=failed,valid=not failed,previous_seal_sha256=sha(P/'SEAL.json')))
print(json.dumps(native({'files':len(m['files']),'valid':not failed})));sys.exit(bool(failed))
