"""Read-only full merged-format audit; optional in-memory one-view-per-scene replay."""
from common import *
from format import *
from produce import errors,load_model
from renderer import render
import argparse
def verify(replay=False):
 manifest=json.loads((ROOT/'SOURCE_MANIFEST.json').read_text())['files']
 for p,h in manifest.items():assert sha(p)==h,('source changed',p)
 rows=[]
 for scene in SCENES:
  p=ROOT/'scenes'/scene/'model';reg=registry()[scene];s=read_ply(reg['model']);l=read_ply(line_dir(scene)/'gaussians.ply');m=read_ply(p/'merged_native.ply');b=read_ply(p/'merged_portable.ply');n=len(s);nl=len(l)
  assert len(m)==len(b)==n+nl
  for k in s.dtype.names:assert s[k].tobytes()==m[k][:n].tobytes(),(scene,k)
  for k in l.dtype.names:assert l[k].tobytes()==m[k][n:].tobytes(),(scene,k)
  for k in [x for x in s.dtype.names if x.startswith(('f_dc_','f_rest_'))]:assert b[k][:n].tobytes()==s[k].tobytes()
  assert len([x for x in m.dtype.names if x.startswith('f_rest_')])==45
  if 'filter_3D' in m.dtype.names:assert (m['filter_3D'][n:]==0).all()
  with np.load(p/'GROUP_MAPPING.npz') as g:
   assert (g['group_id'][:n]==0).all() and (g['group_id'][n:]==1).all();np.testing.assert_array_equal(g['source_index'][:n],np.arange(n));np.testing.assert_array_equal(g['line_index'][n:],np.arange(nl))
   with np.load(line_dir(scene)/'gaussians.npz') as a:
    for k in ['primitive_id','internal_piece_id','arc_t']:np.testing.assert_array_equal(g[k][n:],a[k])
  aa,bb=activate(m),activate(b);e=errors(aa,bb);assert e['means_max_abs']==0 and e['covariance_max_relative_frobenius']<3e-6 and e['opacity_max_abs']<2e-7
  for folder in [p]+[ROOT/'scenes'/scene/'views'/v for v in reg['display_views']]:
   seal=json.loads((folder/'SEAL.json').read_text())
   for name,h in seal['files'].items():assert sha(folder/name)==h,(scene,folder,name)
  r=dict(scene=scene,source_count=n,line_count=nl,total=n+nl,field_exact=True,portable_error=e,static_views=len(reg['display_views']))
  del m,b,aa,bb,s,l
  if replay:
   a,source,ink,floors=load_model(scene);v=reg['display_views'][0];c=next(c for c in reg['cameras'] if c['view']==v);bg=[1]*3 if scene=='ficus' else [0]*3
   new=render(a,c,bg,floors)['rgb']
   with np.load(ROOT/'scenes'/scene/'views'/v/'RENDER_ARRAYS.npz') as d:assert np.array_equal(new,d['joint']),('replay mismatch',scene)
   r['joint_from_reloaded_asset_bitexact']=True;del a,source,ink
  video=ROOT/'scenes'/scene/'media/VALIDATION.json'
  if video.exists():
   vv=json.loads(video.read_text());assert vv['full_decoded_frames']==33 and vv['independent_return_bitexact'];assert sha(Path(vv['video']))==vv['sha256'];r['video_frames']=33
  rows.append(r)
 result=dict(status='PASS',readonly=True,scenes=rows,source_hashes_unchanged=len(manifest),rollback=rollback())
 if (ROOT/'RESULTS_MANIFEST.json').exists():
  fs=json.loads((ROOT/'RESULTS_MANIFEST.json').read_text())['files']
  for rel,entry in fs.items():assert sha(ROOT/rel)==entry['sha256'],rel
  result['output_manifest_files']=len(fs)
 return result
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--readonly',action='store_true',required=True);p.add_argument('--replay',action='store_true');a=p.parse_args();print(json.dumps(verify(a.replay),ensure_ascii=False))
