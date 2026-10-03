"""Publish exact root-relative paths and hashes after full independent verification."""
import hashlib,json,os
from pathlib import Path
CONT=Path(__file__).resolve().parent
ROOT=CONT.parents[2]
ART=CONT.parent/'transport'
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(1<<20),b''):h.update(b)
 return h.hexdigest()
report_path=CONT/'independent_review/PRODUCTION.json'
r=json.loads(report_path.read_text())
assert r['passed'] and r['verified_frames']==196 and r['verified_videos']==24
result={'schema':1,'scope':'Exact paths are scene.root / files key; hashes copied from independently reverified seals, seal JSON reread and hash matched to checker; no raw payload duplication.','verification':{'path':str(report_path),'sha256':sha(report_path)},'scenes':{}}
for scene,entry in r['scenes'].items():
 root=Path(entry['root']);files={}
 for kind in ('frames','raw'):
  for key,verified in entry['frames'].items():
   folder=root/kind/scene/key;p=folder/'SEAL.json';expected=verified['seal_sha256' if kind=='frames' else 'raw_seal_sha256'];assert sha(p)==expected
   seal=json.loads(p.read_text())
   for name,digest in seal['files'].items():files[str((folder/name).relative_to(root))]={'sha256':digest,'bytes':(folder/name).stat().st_size}
   for name in ('SEAL.json','SEAL.sha256'):files[str((folder/name).relative_to(root))]={'sha256':sha(folder/name),'bytes':(folder/name).stat().st_size}
 folder=root/'media'/scene;p=folder/'SEAL.json';assert sha(p)==entry['media']['seal_sha256'];seal=json.loads(p.read_text())
 for name,digest in seal['files'].items():files[str((folder/name).relative_to(root))]={'sha256':digest,'bytes':(folder/name).stat().st_size}
 for name in ('SEAL.json','SEAL.sha256'):files[str((folder/name).relative_to(root))]={'sha256':sha(folder/name),'bytes':(folder/name).stat().st_size}
 p=root/'calibration'/scene/'CALIBRATION.json';cal=json.loads(p.read_text());assert sha(p)==entry['calibration']['sha256']
 files[str(p.relative_to(root))]={'sha256':sha(p),'bytes':p.stat().st_size}
 for row in cal['frames']:
  for field,digest in [('path','sha256'),('unpatched_path','unpatched_sha256')]:
   p=Path(row[field]);files[str(p.relative_to(root))]={'sha256':row[digest],'bytes':p.stat().st_size}
 meta={name:{'path':str(ART/scene/name),'sha256':sha(ART/scene/name)} for name in ('CAMERAS.json','CALIBRATION.json','FRAMES.json','MEDIA.json')}
 result['scenes'][scene]={'root':str(root),'files':dict(sorted(files.items())),'metadata':meta,'files_count':len(files),'bytes_sum_includes_hardlinks':sum(x['bytes'] for x in files.values())}
result['total_indexed_files']=sum(x['files_count'] for x in result['scenes'].values())
p=CONT/'ARTIFACT_PATH_SHA256.json';q=p.with_suffix('.partial');q.write_text(json.dumps(result,indent=2)+'\n');os.replace(q,p)
print(json.dumps({'indexed_files':result['total_indexed_files'],'manifest_bytes':p.stat().st_size,'sha256':sha(p)}))
