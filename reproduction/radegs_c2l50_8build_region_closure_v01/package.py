from env import *
import tarfile,hashlib
from pathlib import PurePosixPath

MUTABLE={'AGENT_LAUNCH.json','ASTRA_RUNTIME_FINAL.md','stdout.log','stderr.log','STATUS.json','PACKAGES.json','PACKAGE_RUN.log','FINAL_READONLY.log','FINAL_READONLY.stderr','launch.py','setup_remote.py'}
def safe_name(n):
 p=PurePosixPath(n);return bool(n and not p.is_absolute() and '..' not in p.parts)
def pack(name,paths):
 target=ROOT/(name+'.tar.gz');assert not target.exists();members={}
 with tarfile.open(target,'w:gz',compresslevel=6) as tar:
  for p in sorted(set(paths)):
   assert p.is_file() and not p.is_symlink();n=str(p.relative_to(ROOT));assert safe_name(n);members[n]=dict(sha256=sha(p));tar.add(p,arcname=n,recursive=False)
 js(ROOT/(name+'.MEMBERS.json'),dict(members=members));(ROOT/(name+'.tar.gz.sha256')).write_text(sha(target)+'  '+target.name+'\n')
 got={}
 with tarfile.open(target,'r:gz') as tar:
  for m in tar:
   assert m.isfile() and safe_name(m.name) and not m.issym() and not m.islnk();f=tar.extractfile(m);h=hashlib.sha256()
   while True:
    b=f.read(2**20)
    if not b:break
    h.update(b)
   got[m.name]=dict(sha256=h.hexdigest())
 assert got==members;return dict(path=str(target),bytes=target.stat().st_size,sha256=sha(target),members=len(members),independent_member_verification=True)
def main():
 guard();code=ROOT/'code';code.mkdir(exist_ok=True)
 for p in CODE.iterdir():
  if p.is_file() and p.suffix in ['.py','.md']:shutil.copyfile(p,code/p.name)
 science=[]
 for p in sorted(ROOT.rglob('*')):
  if not p.is_file() or p.is_symlink() or p.name in MUTABLE or p.name=='RESULTS_MANIFEST.json':continue
  if 'mplconfig' in p.parts or p.name.endswith(('.tar.gz','.sha256','.MEMBERS.json')):continue
  science.append(p)
 js(ROOT/'RESULTS_MANIFEST.json',dict(members={str(p.relative_to(ROOT)):dict(sha256=sha(p)) for p in science},excluded_runtime=sorted(MUTABLE),scientific_status='NO_GO',new_ink_models=0))
 science.append(ROOT/'RESULTS_MANIFEST.json')
 previews=[ROOT/n for n in ['REPORT_ZH.md','ASTRA_FINAL.md','FORMAT_ZH.md','OVERVIEW.jpg','COUNTS.json','TEST_RESULTS.json','GATE_ERRATA_ZH.md']]
 for s in SCENES:
  for v in [DEV[s],RESERVED[s][1 if s!='ficus' else 0]]:previews.append(ROOT/'diagnostics'/s/v/'FULL_FRAME.jpg')
 for s,v,k in [('scan24','0000','window_frame'),('scan65','0036','socket_rim'),('ficus','test_r_14','thin_leaf_edge'),('ficus','train_r_80','top_spike')]:previews.append(ROOT/'diagnostics'/s/v/k/'EXPLANATION.jpg')
 previews+=list((ROOT/'crossview_figures').glob('*DETAIL.jpg'))
 r=[pack('PREVIEWS',previews),pack('DELIVERABLE',science)];js(ROOT/'PACKAGES.json',dict(packages=r,resources=guard()));print(json.dumps(r,indent=2))
 if r[0]['bytes']>20*2**20:raise RuntimeError('Preview above20MiB; preserve package and report, no silent replacement')
if __name__=='__main__':main()
