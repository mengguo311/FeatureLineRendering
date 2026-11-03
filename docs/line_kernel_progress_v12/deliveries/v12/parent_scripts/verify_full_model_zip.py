from pathlib import Path
import io,json,sys,zipfile,hashlib
import numpy as np
from PIL import Image
path=Path(sys.argv[1])
with zipfile.ZipFile(path) as z:
 assert z.testzip() is None
 names=z.namelist();assert len(names)==len(set(names))==len({n.casefold() for n in names})
 manifest=json.loads(z.read('MANIFEST.json'));assert set(names)==set(manifest['files'])|{'MANIFEST.json'}
 for n,h in manifest['files'].items():assert hashlib.sha256(z.read(n)).hexdigest()==h,n
 def load(n):
  with np.load(io.BytesIO(z.read(n)),allow_pickle=False) as a:return {k:a[k].copy() for k in a.files}
 def same(a,b):return a.shape==b.shape and a.dtype==b.dtype and a.tobytes()==b.tobytes()
 a=load(manifest['original_member']);b=load(manifest['derived_member']);m=load(manifest['membership_member']);edge=m['edge_id'];n=manifest['row_count'];assert len(edge)==len(a['means'])==len(b['means'])==n;assert set(a)==set(b);assert np.array_equal(m['line_kernel_id'],np.arange(n));assert np.isfinite(b['means']).all()
 frozen={k:same(a[k],b[k]) for k in a if k!='means'};assert all(frozen.values());unknown=edge<0;assert same(a['means'][unknown],b['means'][unknown]);assert int(unknown.sum())==manifest['unknown_rows']
 ledger=json.loads(z.read('unit/GROUP_LEDGER.json'));groups=ledger['groups'];assert len(groups)==manifest['existing_groups'];rows=[]
 for g in groups:
  ids=np.asarray(g['rows'],dtype=np.int64);assert g['status']=='SUCCESS' and len(ids)==g['row_count'] and np.all(edge[ids]==g['group_id']);rows.append(ids)
 rows=np.concatenate(rows);assert len(np.unique(rows))==len(rows)==manifest['assigned_rows'];assert np.array_equal(np.sort(rows),np.flatnonzero(edge>=0));assert len({g['group_id'] for g in groups})==len(groups)
 images=[n for n in manifest['files'] if n.lower().endswith('.png')]
 for name in images:
  with Image.open(io.BytesIO(z.read(name))) as im:im.verify()
 changed=int(np.any(a['means'].view(np.uint64)!=b['means'].view(np.uint64),axis=1).sum());assert changed==manifest['changed_mean_rows'];assert hashlib.sha256(z.read(manifest['original_member'])).hexdigest()==manifest['canonical_npz_sha256']
 print(json.dumps(dict(actual_zip_members=len(names),payload_members=len(manifest['files']),crc_pass=True,all_member_sha256_match=True,cold_loaded_from_actual_zip_member_bytes=True,rows=n,assigned_rows=len(rows),unknown_rows=int(unknown.sum()),all_existing_groups=len(groups),changed_mean_rows=changed,nonmean_fields_bitwise=frozen,unknown_means_bitwise_unchanged=True,all_pngs_decoded=len(images),rollback_canonical_sha256_match=True)))
