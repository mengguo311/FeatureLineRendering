"""Read-only verification. No output file, repair, render cache or manifest modification."""
from env import *
from support_graph import aggregate_roles,pair_sides,load_node
from measure import query_case
from responsibility import ProjectedSource
def equal(a,b):return np.array_equal(a,b,equal_nan=True)
def run(replay=False):
 guard();result=dict(source_files=0,sealed_units=0,scenes={},replay=replay);before=json.loads((ROOT/'SOURCE_MANIFEST.json').read_text())['files']
 for p,h in before.items():assert sha(p)==h,p;result['source_files']+=1
 result['rollback']=rollback()
 for p in ROOT.glob('scenes/**/SEAL.json'):checkseal(p.parent);result['sealed_units']+=1
 if (ROOT/'summary/SEAL.json').exists():checkseal(ROOT/'summary');result['sealed_units']+=1
 cfg=json.loads((ROOT/'GRAPH_CONFIG.json').read_text());frozen=json.loads((ROOT/'CASE_FREEZE.json').read_text())['cases']
 for s in SCENES:
  source=read_ply(registry()[s]['model']);a=activate(source);joint=read_ply(JOINT/'scenes'/s/'model/merged_native.ply')
  for k in source.dtype.names:assert equal(source[k],joint[k][:len(source)]),(s,k,'source_prefix')
  del joint
  out=ROOT/'scenes'/s/'graph';g=json.loads((out/'PATCH_GRAPH.json').read_text());m=npz(out/'PATCH_MEMBERSHIPS.npz');r=npz(out/'SOURCE_ROLE_SCORES.npz');assert np.array_equal(r['source_index'],np.arange(len(source))) and len(r['scores'])==len(source);assert np.all((m['source_index']>=0)&(m['source_index']<len(source)));records=[];byid={}
  for n in g['nodes']:
   q=load_node(Path(n['measurement']),n['side'],n['node_id']);byid[n['node_id']]=q;i=n['node_id'];lo,hi=m['offsets'][i:i+2];assert equal(m['source_index'][lo:hi],q['ids']) and equal(m['weight'][lo:hi],q['mass'])
   if n['arm']=='line':records.append((q['ids'],q['mass'],q['scores']))
  ar=aggregate_roles(len(source),records)
  for k in ar:assert equal(ar[k],r[k]),(s,k)
  for edge in g['edges']:
   x=pair_sides([byid[i] for i in edge['node_ids_a']],[byid[i] for i in edge['node_ids_b']],cfg)
   for k in x:assert x[k]==edge[k],(s,k,'graph_edge')
  d=read_ply(out/'SOURCE_ROLE_DIAGNOSTIC.ply');ids=d['source_index'];assert equal(ids,np.flatnonzero(r['queried']))
  for k in ['x','y','z']:assert equal(d[k],source[k][ids]),(s,k,'no_source_motion')
  assert equal(d['role_index'],r['role_index'][ids]);nresults=0
  for p in (ROOT/'scenes'/s/'stage1').glob('*/*/*/RESULT.json'):
   x=json.loads(p.read_text());e=npz(p.parent/'EVIDENCE.npz');assert x['source_only'] and x['all_participants_kept'] and not x['physical_primitive_reconstructed'];assert (e['source_index']<len(source)).all();assert np.allclose(e['weight'],e['alpha_i']*e['T'],rtol=0,atol=0);assert len(e['csr_offsets'])==len(e['query_uv'])+1 and e['csr_offsets'][-1]==len(e['weight']);nresults+=1
  cals=[]
  for v in VIEWS[s]:
   x=json.loads((ROOT/'scenes'/s/'stage1'/v/'reference/CALIBRATION.json').read_text());assert x['engineering_go'] and x['all_N_max_error']<=2e-12 and x['renderer_query_max_abs']<=5e-7;cals.append(x)
  detail=dict(measurements=nresults,source_count=len(source),queried_count=int(r['queried'].sum()),calibrated_cameras=len(cals))
  if replay:
   case=next(c for c in frozen if c['scene']==s and c['selection_valid']);v=DEV[s];camera=cam(s,v);raw=npz(rawpath(s,v));proj=ProjectedSource.from_asset(a,camera,s);x,e=query_case(case,'line',camera,raw,proj,a);original=npz(ROOT/'scenes'/s/'stage1'/v/case['case']/'line/EVIDENCE.npz')
   for k in e:assert equal(e[k],original[k]),(s,k,'evidence_replay')
   rr=json.loads((ROOT/'scenes'/s/'stage1'/v/case['case']/'line/RESULT.json').read_text());assert x==rr,(s,'result_replay')
   allN=[]
   for xy in e['query_uv'][e['inside']][::max(1,len(e['query_uv'])//3)]:
    q=proj.query(xy);full=proj.query(xy,all_N=True);assert equal(q['ids'],full['ids']) and np.allclose(q['weight'],full['weight'],atol=2e-12,rtol=0);allN.append(xy.tolist())
   ref=render(a,camera,[1]*3 if s=='ficus' else [0]*3,.3 if s=='ficus' else .0144);oldref=npz(ROOT/'scenes'/s/'stage1'/v/'reference/REFERENCE.npz')
   for k in ref:assert equal(ref[k],oldref[k]),(s,k,'source_render_replay')
   detail.update(replayed_case=case['case'],bitexact_measurement=True,bitexact_source_render=True,real_case_allN_pixels=allN)
  result['scenes'][s]=detail
 if (ROOT/'RESULTS_MANIFEST.json').exists():
  manifest=json.loads((ROOT/'RESULTS_MANIFEST.json').read_text())
  for rel,x in manifest['members'].items():
   p=Path(rel);assert not p.is_absolute() and '..' not in p.parts and not (ROOT/p).is_symlink();assert sha(ROOT/p)==x['sha256'],rel
  result['manifest_files']=len(manifest['members'])
 if (ROOT/'CODE_FREEZE.json').exists():
  for rel,h in json.loads((ROOT/'CODE_FREEZE.json').read_text())['files'].items():assert sha(CODE/rel)==h,rel
 result['status']='PASS';return result
if __name__=='__main__':
 import argparse;p=argparse.ArgumentParser();p.add_argument('--readonly',required=True,action='store_true');p.add_argument('--replay',action='store_true');a=p.parse_args();print(json.dumps(run(a.replay),indent=2))
