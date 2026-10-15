"""Standard-library-only verified reassembly. No overwrite; no extraction."""
import argparse,hashlib,json
from pathlib import Path,PurePosixPath
def safe(name):
 p=PurePosixPath(name);return not p.is_absolute() and '..' not in p.parts and len(p.parts)==1
def rebuild(manifest,output=None):
 manifest=Path(manifest);d=json.loads(manifest.read_text());whole=hashlib.sha256();size=0;out=None
 if output is not None:out=open(output,'xb')
 try:
  for rec in d['parts']:
   assert safe(rec['file']);p=manifest.parent/rec['file'];assert not p.is_symlink();h=hashlib.sha256();n=0
   with p.open('rb') as f:
    for b in iter(lambda:f.read(2**20),b''):
     h.update(b);whole.update(b);n+=len(b);size+=len(b)
     if out is not None:out.write(b)
   assert n==rec['bytes'] and h.hexdigest()==rec['sha256'],rec['file']
  assert size==d['original_bytes'] and whole.hexdigest()==d['original_sha256']
 finally:
  if out is not None:out.close()
 return dict(bytes=size,sha256=whole.hexdigest(),parts=len(d['parts']),reassembled_file=str(output) if output is not None else None)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('manifest');p.add_argument('--output');a=p.parse_args();print(json.dumps(rebuild(a.manifest,a.output)))
