"""Mirror unchanged source bytes so the legacy suite cannot rebuild old binaries."""
import os,pathlib,shutil,json,hashlib
O=pathlib.Path(__file__).resolve().parents[1];R=O.parents[1];S=O/'setup/repository_suite';S.mkdir(exist_ok=False)
for name in ['src','tests','scripts']:
 shutil.copytree(R/name,S/name,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
(S/'out').mkdir()
for p in (R/'out').iterdir():
 if p.name in ['curve_correspondence_foundation','point_feature_foundation']:continue
 (S/'out'/p.name).symlink_to(p,target_is_directory=p.is_dir())
fp=S/'out/point_feature_foundation';fp.mkdir()
for p in (R/'out/point_feature_foundation').iterdir():
 if p.name!='setup':(fp/p.name).symlink_to(p,target_is_directory=p.is_dir())
(fp/'setup').mkdir()
for p in (R/'out/point_feature_foundation/setup').iterdir():
 target=fp/'setup'/p.name
 if p.name=='composite.so':shutil.copy2(p,target)
 else:target.symlink_to(p,target_is_directory=p.is_dir())
(S/'tmp').mkdir();pairs=[]
for name in ['src','tests','scripts']:
 for p in (S/name).rglob('*'):
  if p.is_file():
   rel=p.relative_to(S);a=hashlib.sha256(p.read_bytes()).hexdigest();b=hashlib.sha256((R/rel).read_bytes()).hexdigest();assert a==b;pairs.append(dict(path=str(rel),sha256=a))
(O/'setup/repository_suite_source_hashes.json').write_text(json.dumps(pairs,indent=2)+'\n')
print('Exact source mirror',len(pairs),'files; original composite.so will not be overwritten')
