"""Safe deterministic-member archives, independent SHA schema, no linked members."""
from env import *
import tarfile,io
EXCLUDE={'AGENT_LAUNCH.json','ASTRA_RUNTIME_FINAL.md','stdout.log','stderr.log','PROMPT.txt','launch.py','setup_remote.py','RESULTS_MANIFEST.json','PACKAGE_RECEIPTS.json'}
def safe_name(n):
 p=Path(n);return not p.is_absolute() and '..' not in p.parts and n not in ['', '.']
def members():
 d={}
 for p in ROOT.rglob('*'):
  if not p.is_file() or p.is_symlink() or p.name in EXCLUDE or 'mplconfig' in p.parts or p.suffix in ['.gz','.sha256'] or p.name.endswith('.MEMBERS.json'):continue
  rel=str(p.relative_to(ROOT));assert safe_name(rel);d[rel]=p
 return d
def build(name,files):
 path=ROOT/(name+'.tar.gz');assert not path.exists();m={rel:dict(sha256=sha(p)) for rel,p in sorted(files.items())};side=ROOT/(name+'.MEMBERS.json');js(side,dict(members=m))
 with tarfile.open(path,'w:gz',compresslevel=6) as t:
  for rel,p in sorted(files.items()):
   assert safe_name(rel) and p.is_file() and not p.is_symlink();inf=t.gettarinfo(str(p),arcname=rel);inf.uid=inf.gid=0;inf.uname=inf.gname='';inf.mtime=0
   with p.open('rb') as f:t.addfile(inf,f)
  buf=json.dumps(dict(members=m),indent=2).encode();info=tarfile.TarInfo('MEMBERS.json');info.size=len(buf);info.mtime=0;t.addfile(info,io.BytesIO(buf))
 with tarfile.open(path,'r:gz') as t:
  seen=set()
  for info in t:
   assert info.isfile() and safe_name(info.name) and not info.issym() and not info.islnk();seen.add(info.name);data=t.extractfile(info).read()
   if info.name=='MEMBERS.json':assert json.loads(data)==dict(members=m)
   else:assert hashlib.sha256(data).hexdigest()==m[info.name]['sha256'],info.name
  assert seen==set(m)|{'MEMBERS.json'}
 digest=sha(path);(ROOT/(name+'.tar.gz.sha256')).write_text(digest+'  '+path.name+'\n');return dict(path=str(path),bytes=path.stat().st_size,sha256=digest,members=len(m),members_sha256=sha(side),safe_member_verified=True)
if __name__=='__main__':
 guard();files=members();js(ROOT/'RESULTS_MANIFEST.json',dict(members={n:dict(sha256=sha(p)) for n,p in sorted(files.items())},mutable_excluded=sorted(EXCLUDE),source_manifest_sha256=sha(ROOT/'SOURCE_MANIFEST.json')));files['RESULTS_MANIFEST.json']=ROOT/'RESULTS_MANIFEST.json'
 preview={n:p for n,p in files.items() if n.startswith('summary/') and p.suffix in ['.jpg','.png'] or n.endswith('/figures/CASE.jpg') or n in ['REPORT_ZH.md','ASTRA_FINAL.md','COUNTS.json','ASSET_FORMAT_ZH.md','TEST_RESULTS.json']}
 for s,c in [('scan24','roof_wall_eave'),('scan65','socket_rim'),('ficus','thin_leaf_edge')]:
  n=f'scenes/{s}/stage1/{DEV[s]}/{c}/figures/CONTROLS.jpg';preview[n]=ROOT/n
 for p in CODE.iterdir():
  if p.is_file() and p.suffix in ['.py','.md']:files['code/'+p.name]=p
 out=[build('PREVIEWS',preview),build('DELIVERABLE',files)];guard();js(ROOT/'PACKAGE_RECEIPTS.json',dict(packages=out));print(json.dumps(out,indent=2))
