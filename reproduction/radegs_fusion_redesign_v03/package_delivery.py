from pathlib import Path
import json,hashlib,tarfile,shutil,time,ast
T=Path('/mnt/hdd1/u00134/radegs_paper_reproduction_v01/fusion_redesign_v03');W=Path(__file__).resolve().parent;B=T.parent/'balanced_multiview_v02';OW=W.parent/'radegs_balanced_multiview_v02'
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for x in iter(lambda:f.read(2**20),b''):h.update(x)
 return h.hexdigest()
assert shutil.disk_usage('/').free>2**30 and shutil.disk_usage(T).free>10*2**30
assert sum(p.stat().st_size for p in T.rglob('*') if p.is_file())<10*2**30
assert not (T/'DELIVERABLE.tar.gz').exists(),'Do not overwrite an already sealed package'
exclude={'RESULTS_MANIFEST.json','DELIVERABLE.tar.gz','DELIVERABLE.tar.gz.sha256','PACKAGE_MANIFEST.json','prototype.lock','AGENT_LAUNCH.json','stdout.log','stderr.log','wrapper.log','launch.py','PROMPT.txt'}
files=[p for p in sorted(T.rglob('*')) if p.is_file() and p.name not in exclude and 'packaging_attempts' not in p.relative_to(T).parts]
code=[p for p in sorted(W.glob('*.py'))]
vendor=[(OW/'core.py','vendor/core.py'),(OW/'demo.py','vendor/demo.py'),(OW/'ewa.cpp','vendor/ewa.cpp'),(B/'evidence/boundary.py','vendor/boundary.py'),(B/'build/libewa.so','vendor/libewa.so')]
for p in files:
 if p.suffix=='.json':json.loads(p.read_text())
for p in code:ast.parse(p.read_text())
rows=[{'path':str(p),'relative_path':str(p.relative_to(T)),'bytes':p.stat().st_size,'sha256':sha(p)} for p in files]+[{'path':str(p),'relative_path':'code/'+p.name,'bytes':p.stat().st_size,'sha256':sha(p)} for p in code]+[{'path':str(p),'relative_path':name,'bytes':p.stat().st_size,'sha256':sha(p),'role':'read-only verified reference dependency'} for p,name in vendor]
manifest={'utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'status':'HONEST_NEGATIVE','method':'bounded fusion redesign diagnosis; six fixed control/local Gaussian assets, NOT complete new fusion','source_manifest':str(T/'EVIDENCE_MANIFEST.json'),'source_manifest_sha256':sha(T/'EVIDENCE_MANIFEST.json'),'boundary_sha256':'11bbb41a762f252d9eeb4ea3f0a8399ed026139d9490bb8cf161bc815e05dd30','files':rows,'excluded_from_package':['original RGB/depth large NPZ','all environments','old full assets','old 47-view production caches','live launcher operational files and prompt','preserved packaging_attempts'],'reproduction_note':'Commands target existing dss9 absolute paths. vendor holds exact small read-only source/native dependencies for inspection; cross-machine rerun requires explicit path adaptation and original input access.'}
(T/'RESULTS_MANIFEST.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2))
manifestrow={'path':str(T/'RESULTS_MANIFEST.json'),'relative_path':'RESULTS_MANIFEST.json','sha256':sha(T/'RESULTS_MANIFEST.json')};allrows=rows+[manifestrow]
package=T/'DELIVERABLE.tar.gz'
with tarfile.open(package,'w:gz',compresslevel=6) as tf:
 for r in allrows:tf.add(r['path'],arcname='fusion_redesign_v03/'+r['relative_path'],recursive=False)
expected={'fusion_redesign_v03/'+r['relative_path']:r['sha256'] for r in allrows}
with tarfile.open(package,'r:gz') as tf:
 members=tf.getmembers();assert len(members)==len(expected)
 for m in members:
  assert m.isfile() and not m.name.startswith('/') and '..' not in Path(m.name).parts
  h=hashlib.sha256()
  with tf.extractfile(m) as f:
   for b in iter(lambda:f.read(2**20),b''):h.update(b)
  assert h.hexdigest()==expected[m.name],m.name
s=sha(package);(T/'DELIVERABLE.tar.gz.sha256').write_text(s+'  DELIVERABLE.tar.gz\n')
record={'path':str(package),'bytes':package.stat().st_size,'sha256':s,'members_verified_by_full_stream_hash':len(expected),'results_manifest_sha256':sha(T/'RESULTS_MANIFEST.json'),'task_bytes_with_package':sum(p.stat().st_size for p in T.rglob('*') if p.is_file()),'utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())}
(T/'PACKAGE_MANIFEST.json').write_text(json.dumps(record,indent=2));print(json.dumps(record),flush=True)
