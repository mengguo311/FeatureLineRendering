"""Read-only independent artifact, mathematical replay and protected-input verification."""
from env import *
import argparse

def verify(replay=False):
 source=json.loads((ROOT/'SOURCE_MANIFEST.json').read_text())['files'];extra=ROOT/'SOURCE_IMPLEMENTATION_AUDIT.json'
 if extra.exists():source.update(json.loads(extra.read_text())['files'])
 for p,h in source.items():assert sha(p)==h,('source_changed',p)
 protected=rollback();unit_count=0
 for p in sorted(ROOT.glob('round*/**/SEAL.json')):checkseal(p.parent);unit_count+=1
 for entry in json.loads((ROOT/'GATES.json').read_text())['reviews']:assert sha(entry['path'])==entry['sha256']
 for rd in ['round1','round2','round3']:
  f=json.loads((ROOT/rd/'CODE_CONFIG_FREEZE.json').read_text());assert sha(ROOT/'PROTOCOL_FREEZE.json')==f['protocol']
  for name,h in f['code'].items():assert sha(CODE/name)==h,('production_code_changed',rd,name)
 assert json.loads((ROOT/'round1/COUNTS.json').read_text())['measurements']==44
 assert json.loads((ROOT/'round2/COUNTS.json').read_text())['model_comparisons']==88
 assert json.loads((ROOT/'round3/COUNTS.json').read_text())['measurements']==88
 roles=0;graph_cases=0;replays=[]
 from conditional import enrich
 from partition import make_partition
 from validation import ordering_diagnostic,alln_roi
 from responsibility import ProjectedSource
 for s in SCENES:
  rawsource=read_ply(registry()[s]['model']);a=activate(rawsource);assert len(a['means'])=={'scan24':596467,'scan65':317817,'ficus':284835}[s]
  for p in (ROOT/'round2/models'/s).glob('*/*/*/SOURCE_ROLES.npz'):
   z=npz(p);ids=z['source_index'];np.testing.assert_array_equal(z['original_xyz'],a['means'][ids]);assert np.all((ids>=0)&(ids<len(a['means'])));assert np.all(z['soft_patch']>=0);np.testing.assert_allclose(z['soft_patch'].sum(1)+z['unknown'],1,rtol=0,atol=2e-12);assert z['all_scene_source_count']==len(a['means']);roles+=1
  for p in (ROOT/'round2/models'/s).glob('*/*/*/SOURCE_PIXEL_GRAPH.npz'):
   z=npz(p);assert np.all((z['source_index']>=0)&(z['source_index']<len(a['means'])));assert np.all(z['query_row']<len(z['query_uv']));graph_cases+=1
  if replay:
   case=next(c for c in cases(s) if c['selection_valid']);v=DEV[s];d=ROOT/'round1/scenes'/s/v/case['case']/'line';e=npz(d/'EVIDENCE.npz');q=enrich(e,a,cam(s,v))
   for k in q:np.testing.assert_allclose(q[k],e[k],atol=0,rtol=0,equal_nan=True)
   base=json.loads((d/'CENTER_BASELINE.json').read_text());r,g=make_partition(e,base,cam(s,v));stored=json.loads((ROOT/'round2/models'/s/v/case['case']/'line/RESULT.json').read_text());assert r['model']==stored['model'];st=npz(ROOT/'round2/models'/s/v/case['case']/'line/CONDITIONAL_GRAPH.npz')
   for k,val in g.items():
    if isinstance(val,np.ndarray):np.testing.assert_array_equal(val,st[k])
   c=cam(s,v);image=render(a,c,[1]*3 if s=='ficus' else [0]*3,.3 if s=='ficus' else .0144);ref=npz(ROOT/'round1/scenes'/s/v/'reference/REFERENCE.npz')
   for k in image:np.testing.assert_array_equal(image[k],ref[k])
   v=RESERVED[s][0];d=ROOT/'round3/evidence'/s/v/case['case']/'line';e=npz(d/'EVIDENCE.npz');p=json.loads((d/'CENTER_BASELINE.json').read_text())['info']['pixel_world_proxy'];proj=ProjectedSource.from_asset(a,cam(s,v),s);arr,result=ordering_diagnostic(e,a,proj,p);st=npz(ROOT/'round3/validation'/s/v/case['case']/'line/ORDERING_COUNTERFACTUAL.npz')
   for k in arr:np.testing.assert_allclose(arr[k],st[k],atol=0,rtol=0,equal_nan=True) if arr[k].dtype.kind not in 'US' else np.testing.assert_array_equal(arr[k],st[k])
   alln=alln_roi(proj,e);assert alln['all_N_max']<=2e-12;replays.append(dict(scene=s,conditional_bitexact=True,partition_bitexact=True,source_render_arrays_bitexact=True,ordering_bitexact=True,all_N=alln))
  del a,rawsource
 return dict(ok=True,readonly=True,source_hashes=len(source),sealed_units=unit_count,source_role_assets=roles,graphs=graph_cases,protected_worktrees=protected,replays=replays,rounds=3,new_GS_models=0)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--readonly',required=True,action='store_true');p.add_argument('--replay',action='store_true');args=p.parse_args();print(json.dumps(verify(args.replay),indent=2))
