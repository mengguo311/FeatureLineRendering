from common import *
import zipfile,tarfile
from pathlib import PurePosixPath
from reassemble import rebuild
def valid(n):
 p=PurePosixPath(n);return not p.is_absolute() and '..' not in p.parts and len(p.parts)>0
def streamsha(f):
 h=hashlib.sha256()
 for b in iter(lambda:f.read(2**20),b''):h.update(b)
 return h.hexdigest()
def check(path,side):
 members=json.loads(Path(side).read_text())['members'];seen=set()
 if str(path).endswith('.zip'):
  with zipfile.ZipFile(path) as z:
   for m in z.infolist():
    assert valid(m.filename) and not m.is_dir() and m.filename not in seen and ((m.external_attr>>16)&0o170000)!=0o120000
    seen.add(m.filename)
    with z.open(m) as f:assert streamsha(f)==members[m.filename]['sha256']
 else:
  with tarfile.open(path,'r:gz') as t:
   for m in t:
    assert valid(m.name) and m.isfile() and m.name not in seen;seen.add(m.name)
    assert streamsha(t.extractfile(m))==members[m.name]['sha256']
 assert seen==set(members)
 return dict(file=str(path),bytes=Path(path).stat().st_size,sha256=sha(path),members=len(seen),safe_members=True,all_member_hashes_verified=True)
def bundle(path,files):
 path=Path(path);assert not path.exists();files=sorted(set(files));members={}
 for p in files:
  assert p.is_file() and not p.is_symlink();rel=p.relative_to(ROOT).as_posix();assert valid(rel);members[rel]={'sha256':sha(p)}
 side=path.with_name(path.name+'.MEMBERS.json');js(side,dict(members=members))
 if path.suffix=='.zip':
  with zipfile.ZipFile(path,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=4,allowZip64=True) as z:
   for p in files:z.write(p,p.relative_to(ROOT).as_posix())
 else:
  with tarfile.open(path,'w:gz',compresslevel=6,dereference=False) as t:
   for p in files:t.add(p,arcname=p.relative_to(ROOT).as_posix(),recursive=False)
 r=check(path,side);path.with_name(path.name+'.sha256').write_text(r['sha256']+'  '+path.name+'\n');guard();return r
def split_verify(path):
 path=Path(path);parts=[]
 with path.open('rb') as f:
  i=0
  while True:
   b=f.read(40*2**20)
   if not b:break
   i+=1;p=path.with_name(path.name+f'.part{i:03d}');assert not p.exists();p.write_bytes(b);parts.append(dict(file=p.name,bytes=len(b),sha256=sha(p)))
 m=path.with_name(path.name+'.SPLIT.json');js(m,dict(original_file=path.name,original_sha256=sha(path),original_bytes=path.stat().st_size,max_part_bytes=40*2**20,parts=parts));tmp=ROOT/'scratch'/('reassembled_'+path.name);tmp.parent.mkdir(exist_ok=True);rec=rebuild(m,tmp);assert sha(tmp)==sha(path);tmp.unlink() # Only this task's verified redundant reassembly temporary.
 js(path.with_name(path.name+'.REASSEMBLY_VERIFIED.json'),rec);return dict(manifest=str(m),parts=len(parts),each_below_45MiB=all(p['bytes']<45*2**20 for p in parts),actual_file_reassembled_and_hash_verified=True)
def main():
 guard();out=ROOT/'downloads';out.mkdir(exist_ok=True);co=ROOT/'code';co.mkdir(exist_ok=True)
 for p in CODE.iterdir():
  if p.is_file() and p.suffix in ['.py','.cpp','.md']:shutil.copyfile(p,co/p.name)
 js(ROOT/'CODE_FREEZE.json',dict(files={str(p):sha(p) for p in CODE.iterdir() if p.is_file()},copy={str(p.relative_to(ROOT)):sha(p) for p in co.iterdir() if p.is_file()}))
 records=[]
 for s in SCENES:
  files=list((ROOT/'scenes'/s/'model').glob('*'))+[ROOT/'FORMAT_ZH.md',ROOT/'SOURCE_MANIFEST.json',ROOT/'CONFIG.json',co/'reassemble.py'];p=out/f'{s}_C2L50_8BUILD_JOINT_MODELS.zip';r=bundle(p,files)
  if r['bytes']>45*2**20:r['split']=split_verify(p)
  records.append(r);js(ROOT/'MODEL_PACKAGE_PROGRESS.json',records)
 codefiles=[p for d in ['code','reviews','logs','failures'] for p in (ROOT/d).rglob('*') if p.is_file()]
 state('DONE_WITH_LIMITATIONS',status='DONE_WITH_LIMITATIONS',completed_scenes=3,expected_scenes=3,static_views=15,video_frames=99,distinct_video_poses_per_scene=17,tests_passed=17,source_unchanged=True,children=[],worker_pid=None,no_automatic_continuation=True,scientific_visual_status='MERGE_COMPLETE_INHERITED_SPIKES_UNFIXED',model_package_count=len(records))
 rootnames=['REPORT_ZH.md','FORMAT_ZH.md','RUN_COMMANDS.md','ASTRA_FINAL.md','STATUS.json','COUNTS.json','REGISTRY.json','SOURCE_MANIFEST.json','SOURCE_BEFOREAFTER.json','INPUT_AUDIT.json','CONFIG.json','GATES.json','BUILD_RECEIPT.json','RENDERER_AUDIT.json','TEST_RESULTS.json','VERIFY_REPLAY.json','ROLLBACK_RECEIPT.json','OLD_BEFORE.json','CODE_FREEZE.json','LOCAL_CHECKPOINT.json','VIDEO_PROGRESS.json','VISUAL_REVIEW.json','SECRET_PATTERN_CHECK.json']
 stable=[ROOT/x for x in rootnames if (ROOT/x).exists()]
 for d in ['scenes','delivery','code','reviews','logs','failures','build']:
  stable.extend(p for p in (ROOT/d).rglob('*') if p.is_file())
 assert all(not p.is_symlink() for p in stable)
 js(ROOT/'RESULTS_MANIFEST.json',dict(source_manifest_sha256=sha(ROOT/'SOURCE_MANIFEST.json'),selected_arm='C 8BUILD only',files={p.relative_to(ROOT).as_posix():dict(sha256=sha(p),bytes=p.stat().st_size) for p in sorted(set(stable))},excluded='External launcher stdout/stderr and ASTRA_RUNTIME_FINAL; download archives have independent MEMBERS/SHA and PACKAGE_RECEIPTS to avoid circular hashes.'))
 rootnames.append('RESULTS_MANIFEST.json')
 codefiles.extend(ROOT/x for x in rootnames if (ROOT/x).exists())
 for s in SCENES:
  codefiles.extend(p for p in (ROOT/'scenes'/s).rglob('*.json') if 'frames' not in p.parts)
 preview=[ROOT/'REPORT_ZH.md',ROOT/'ASTRA_FINAL.md',ROOT/'delivery/OVERVIEW.jpg']+list((ROOT/'delivery').glob('*_FIVE_VIEWS.jpg'))
 for s in SCENES:
  preview.extend((ROOT/'scenes'/s/'views').glob('*/COMPARISON.jpg'));v=ROOT/'scenes'/s/'media/CONTACT_FIRST_EXTREMES_MIDDLE_RETURN.jpg'
  if v.exists():preview.append(v)
 records.append(bundle(out/'PREVIEWS.tar.gz',preview));records.append(bundle(out/'DELIVERABLE_CODE.tar.gz',codefiles));js(ROOT/'PACKAGE_RECEIPTS.json',dict(packages=records,resources=guard()));print(json.dumps(records),flush=True)
if __name__=='__main__':
 try:main()
 except Exception as e:
  state('PACKAGING_FAILED',status='ENGINEERING_NOT_READY',error=repr(e),children=[],worker_pid=None,no_automatic_continuation=True)
  raise
