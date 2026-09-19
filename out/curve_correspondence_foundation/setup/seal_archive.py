"""Administrative exact inventory with explicit self-reference exclusions."""
import collections,datetime,json,pathlib,subprocess,sys
O=pathlib.Path(__file__).resolve().parents[1];R=O.parents[1];sys.path[:0]=[str(O/'code'),str(R)]
from cc_io import sha,read_json,write_json
from cc_verify import inventory,verify_inventory
EXCLUDE=['MANIFEST.json','MANIFEST.json.sha256','FINAL_SEAL.json']
def check_manifest():
 manifest=read_json(O/'MANIFEST.json');records=[{k:v for k,v in row.items() if k!='storage'} for row in manifest['files']]
 ok=sha(O/'MANIFEST.json')==(O/'MANIFEST.json.sha256').read_text().strip() and verify_inventory(O,records,EXCLUDE)
 return ok,manifest
if '--verify' in sys.argv:
 ok,m=check_manifest();s=read_json(O/'FINAL_SEAL.json')
 ok=ok and s['passed'] and s['manifest_sha256']==sha(O/'MANIFEST.json') and s['verification_sha256']==sha(O/'VERIFICATION.json') and s['results_sha256']==sha(O/'results.json')
 tracked=set(subprocess.check_output(['git','ls-files','-z','out/curve_correspondence_foundation'],cwd=R).decode().split('\0'))
 ok=ok and all((str((O/r['path']).relative_to(R)) in tracked)==(r['storage']=='git') for r in m['files'])
 print(json.dumps(dict(passed=ok,files=m['file_count'],bytes=m['bytes'],storage=m['storage']),indent=2));sys.exit(not ok)
records=inventory(O,EXCLUDE)
paths=[str((O/r['path']).relative_to(R)) for r in records]
q=subprocess.run(['git','check-ignore','--no-index','-z','--stdin'],cwd=R,input=('\0'.join(paths)+'\0').encode(),stdout=subprocess.PIPE,check=False)
if q.returncode not in [0,1]:raise RuntimeError('git ignore classification failed')
ignored=set(q.stdout.decode().split('\0'))
for row,p in zip(records,paths):row['storage']='server-only' if p in ignored else 'git'
storage={k:dict(files=sum(r['storage']==k for r in records),bytes=sum(r['bytes'] for r in records if r['storage']==k)) for k in ['git','server-only']}
m=dict(created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),file_count=len(records),bytes=sum(r['bytes'] for r in records),storage=storage,excluded_self_references=EXCLUDE,files=records,external_dependencies=['input_hashes.json','PRESERVED_INPUT_VERIFICATION.json'],symlink_policy='Hash literal target bytes; do not follow or decode linked archived data.')
write_json(O/'MANIFEST.json',m)
with (O/'MANIFEST.json.sha256').open('x') as f:f.write(sha(O/'MANIFEST.json')+'\n')
ok,_=check_manifest();assert ok
write_json(O/'FINAL_SEAL.json',dict(created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),passed=ok,manifest_sha256=sha(O/'MANIFEST.json'),verification_sha256=sha(O/'VERIFICATION.json'),results_sha256=sha(O/'results.json'),file_count=m['file_count'],bytes=m['bytes'],scope='All non-self-referential files checked exactly. Git local/upstream/remote equality and clean status recorded in the external report after final push.'))
print(json.dumps(dict(passed=ok,files=m['file_count'],bytes=m['bytes'],storage=storage),indent=2))
