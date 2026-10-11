"""Validate emitted artifacts and immutable inputs; does not evaluate visual quality."""
import argparse,hashlib,json
from pathlib import Path
import numpy as np
from PIL import Image

def sha(p):
 h=hashlib.sha256()
 with open(p,'rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
def main():
 a=argparse.ArgumentParser();a.add_argument('run');a.add_argument('--count',type=int,default=18);args=a.parse_args();root=Path(args.run);m=json.loads((root/'RUN_MANIFEST.json').read_text())
 assert len(m['records'])==args.count
 assert len({(r['scene'],r['view']) for r in m['records']})==args.count
 assert m['code_sha256']==sha(Path(__file__).with_name('line_core.py'))
 counts={'views':0,'native_binary_images':0,'sha256_verified_inputs':0,'source_response_npz':0}
 for path,v in m['source_ledger'].items():
  assert sha(path)==v['sha256'],path;counts['sha256_verified_inputs']+=1
 for r in m['records']:
  d=Path(r['native_dir']);counts['views']+=1
  for name in ['D','hardcut','S1','S2']:
   im=np.array(Image.open(d/(name+'.png')));assert im.shape==(r['height'],r['width']);assert set(np.unique(im)).issubset({0,255});counts['native_binary_images']+=1
  with np.load(d/'responses_weights.npz') as n:
   for k in n.files:assert np.isfinite(n[k]).all(),(d,k)
   valid=np.array(Image.open(d/'valid.png'))>0;support=np.array(Image.open(d/'support.png'))>0
   for k in ['S1','S2']:
    lines=np.array(Image.open(d/(k+'.png')))==0
    assert not (lines&~valid).any();assert not (lines&~support).any()
    assert (n['response'][lines]>=.014-1e-7).all(), 'lines must have direct current-view geometric response'
   counts['source_response_npz']+=1
  assert r['same_camera_recompute_identical']
  for name in ['comparison','support']:assert Path(r[name]).is_file()
 print(json.dumps({'validation':'PASS','counts':counts,'visual_quality_not_inferred_from_tests':True},indent=2))
if __name__=='__main__':main()
