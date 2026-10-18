"""Package only task-owned files; independently stream-verify safe members."""
from env import *
import tarfile,io,stat
EXCLUDE={'AGENT_LAUNCH.json','ASTRA_RUNTIME_FINAL.md','STATUS.json','stdout.log','stderr.log','PROMPT.txt','launch.py','setup_remote.py','RESULTS_MANIFEST.json','PACKAGE_INDEX.json','PACKAGE_VERIFY.json','FINAL_READONLY_VERIFY.log','PACKAGE_EXECUTION.log'}

def archive(name,entries):
 path=ROOT/(name+'.tar.gz');assert not path.exists();entries=sorted(entries,key=lambda t:t[0]);assert len({n for n,p in entries})==len(entries)
 members={}
 for n,p in entries:
  assert not Path(n).is_absolute() and '..' not in Path(n).parts and not p.is_symlink() and p.is_file();members[n]=dict(sha256=sha(p))
 data=json.dumps(dict(members=members),indent=2).encode();js(ROOT/(name+'.MEMBERS.json'),dict(members=members))
 with tarfile.open(path,'w:gz',compresslevel=6) as tf:
  for n,p in entries:
   info=tf.gettarinfo(str(p),arcname=n);assert info.isfile();
   with open(p,'rb') as f:tf.addfile(info,f)
  info=tarfile.TarInfo('MEMBERS.json');info.size=len(data);tf.addfile(info,io.BytesIO(data))
 assert path.stat().st_size<12*2**30;digest=sha(path);(ROOT/(name+'.tar.gz.sha256')).write_text(digest+'  '+path.name+'\n');checked=0
 with tarfile.open(path,'r:gz') as tf:
  names=[]
  for member in tf:
   assert member.isfile() and not member.issym() and not member.islnk();n=member.name;assert not Path(n).is_absolute() and '..' not in Path(n).parts;names.append(n);f=tf.extractfile(member)
   if n=='MEMBERS.json':assert json.load(f)==dict(members=members);continue
   h=hashlib.sha256()
   for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
   assert h.hexdigest()==members[n]['sha256'],n;checked+=1
  assert len(names)==len(set(names))==len(members)+1
 return dict(path=str(path),sha256=digest,bytes=path.stat().st_size,verified_members=checked,safe_members=True)

def chosen_results():
 out=[]
 for p in ROOT.rglob('*'):
  rel=p.relative_to(ROOT)
  if not p.is_file() or p.is_symlink():continue
  if rel.parts[0] in {'mplconfig','runtime'} or p.name in EXCLUDE:continue
  if p.name.endswith(('.tar.gz','.tar.gz.sha256','.MEMBERS.json')):continue
  out.append(('results/'+str(rel),p))
 return out
if __name__=='__main__':
 guard();state('PACKAGING',completed_rounds=3,status='RUNNING_DELIVERY_ONLY',children=[os.getpid()]);code=[('code/'+p.name,p) for p in CODE.iterdir() if p.is_file() and p.suffix in {'.py','.md','.json'}];data=chosen_results();pre=[]
 preview_names={'REPORT_ZH.md','ASTRA_FINAL.md','ASSET_FORMAT_ZH.md','OVERVIEW.jpg','COUNTS.json','METHOD_FREEZE_ZH.md','ROUND1_REPORT_ZH.md','ROUND2_REPORT_ZH.md','ROUND3_REPORT_ZH.md','ERRATA_TEST_COUNT.md'}
 case_names={'roof_wall_eave','cap_seam','thin_leaf_edge'}
 for n,p in data:
  if p.name in preview_names:pre.append((n,p))
  elif p.name=='CASE.jpg' and any(part in case_names for part in p.parts):
   rel=p.relative_to(ROOT)
   if rel.parts[0]=='round1' or rel.parts[0]=='round2' or ('0036' in rel.parts or 'test_r_14' in rel.parts):pre.append((n,p))
  elif p.name=='ZOOM.jpg' and 'round2/figures/ficus/top_spike' in str(p):pre.append((n,p))
  elif p.name.startswith('DECISIONS_'):pre.append((n,p))
 results=[]
 for name,entries in [('PREVIEWS',pre),('DELIVERABLE',data+code)]:
  result=archive(name,entries);results.append(result);guard();print(json.dumps(result),flush=True)
 js(ROOT/'PACKAGE_INDEX.json',dict(packages=results));js(ROOT/'PACKAGE_VERIFY.json',dict(verified=True,packages=results,independent_stream_hash=True,member_schema={'members':{'relative_path':{'sha256':'...'}}},no_source_checkpoint_or_environment_packaged=True))
 state('COMPLETE',completed_rounds=3,status='HONEST_NEGATIVE',children=[],no_automatic_continuation=True,round4_started=False)
 js(ROOT/'STATUS_SEALED.json',json.loads((ROOT/'STATUS.json').read_text()))
 # Final output manifest deliberately excludes mutable launcher output and itself. No stale hash is rewritten.
 files={}
 for p in sorted(ROOT.rglob('*')):
  rel=p.relative_to(ROOT)
  if p.is_file() and not p.is_symlink() and p.name not in EXCLUDE and rel.parts[0] not in {'mplconfig','runtime'}:files[str(rel)]=dict(sha256=sha(p),bytes=p.stat().st_size)
 js(ROOT/'RESULTS_MANIFEST.json',dict(members=files,source_manifest=sha(ROOT/'SOURCE_MANIFEST.json'),source_extra=sha(ROOT/'SOURCE_IMPLEMENTATION_AUDIT.json'),excluded_mutable=sorted(EXCLUDE),code={str(p.relative_to(CODE)):sha(p) for p in CODE.iterdir() if p.is_file()},rounds=3,no_automatic_continuation=True))
