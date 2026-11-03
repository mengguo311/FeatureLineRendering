"""Verify and cold-load the delivered original/derived Gaussian archive."""
from pathlib import Path
import io,json,hashlib,zipfile,sys
import numpy as np
def load_bundle(path):
 with zipfile.ZipFile(path) as z:
  assert z.testzip() is None
  manifest=json.loads(z.read('MANIFEST.json'))
  for name,h in manifest['files'].items():assert hashlib.sha256(z.read(name)).hexdigest()==h,name
  original=dict(np.load(io.BytesIO(z.read(manifest['original_member'])),allow_pickle=False));derived=dict(np.load(io.BytesIO(z.read(manifest['preview_member'])),allow_pickle=False));target=np.load(io.BytesIO(z.read(manifest['target_rows_member'])),allow_pickle=False)['row_index']
 N=len(original['means']);mask=np.ones(N,bool);mask[target]=False;assert len(target)==596 and len(np.unique(target))==596
 assert set(original)==set(derived)
 for key in original:
  assert original[key].shape==derived[key].shape and original[key].dtype==derived[key].dtype,key
  assert original[key][mask].tobytes()==derived[key][mask].tobytes(),key
  if key not in ['means','covariance']:assert original[key].tobytes()==derived[key].tobytes(),key
 assert np.isfinite(derived['means']).all() and np.isfinite(derived['covariance']).all()
 assert (np.linalg.eigvalsh(derived['covariance'][target])>0).all()
 return original,derived,target
if __name__=='__main__':
 original,derived,target=load_bundle(sys.argv[1]);print(json.dumps(dict(cold_load_pass=True,total_rows=len(derived['means']),target_rows=len(target),non_target_rows=len(derived['means'])-len(target),target_means_changed=int(np.any(original['means'][target]!=derived['means'][target],axis=1).sum()),restorable_original=True)))
