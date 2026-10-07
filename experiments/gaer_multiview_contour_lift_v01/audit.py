"""Independent readback/lineage audit. Adds evidence only; never edits sealed geometry."""
import runtime as rt
import json,struct,ast,hashlib,subprocess,collections
from pathlib import Path
import numpy as np
from scipy.spatial import cKDTree
from plyfile import PlyData
import pipeline as pp
from core import project,geometry_hash

def require(x,msg):
 if not x:raise AssertionError(msg)
def glb(path):
 b=path.read_bytes();magic,version,total=struct.unpack_from('<III',b);require((magic,version,total)==(0x46546c67,2,len(b)),'GLB header');nj=struct.unpack_from('<I',b,12)[0];j=json.loads(b[20:20+nj]);require('animations' not in j,'animation prohibited');start=28+nj;blob=b[start:];a=j['accessors'];bv=j['bufferViews'];v=np.frombuffer(blob,dtype='<f4',count=a[0]['count']*3,offset=bv[0].get('byteOffset',0)).reshape(-1,3);f=np.frombuffer(blob,dtype='<u4',count=a[1]['count'],offset=bv[1].get('byteOffset',0)).reshape(-1,3);return v,f

def contract_scene(n):
 rt.guard(n+'_contract_audit');keys,src,off,d=pp.collect(n);f=dict(np.load(rt.ART/'fusion'/n/'fused.npz'));prov=json.loads((rt.ART/'fusion'/n/'fused.json').read_text());edgeoff=np.r_[0,np.cumsum([len(a['edges']) for a in src])];cams=[pp.camera(n,k) for k in keys];rec=json.loads((rt.ART/'results'/(n+'_asset.json')).read_text());files=[]
 # Explicit namespaces fix interpretive ambiguity without rewriting original sealed bytes.
 ns=dict(node_namespace='global raw source point index in construction order',node_offsets=off.tolist(),edge_offsets=edgeoff.tolist(),source_cameras=keys,rawunion_edge_namespace='global raw edge index',fused_edge_namespace='global raw edge index',single_edge_namespace='local r_33 edge index; add edge_offsets[r33] for global',per_source_edge_namespace='local camera edge index; add edge_offsets[camera] for global',depth='conditional accepted alphaT weighted median original center-z PROXY; source CSR stores all accepted IDs/weights/center-z',raw_edge_table=[dict(camera=k,local_start=0,global_start=int(edgeoff[i]),count=int(edgeoff[i+1]-edgeoff[i])) for i,k in enumerate(keys)])
 path=rt.ART/'assets'/n/'PROVENANCE_NAMESPACES.json';rt.atomic_json(path,ns);files.append(path)
 scene_result=dict(assets=[],source_track={},depth={},edge={},limitations=[])
 # No contribution is silently top-k truncated; finite source data and source reprojection.
 for k,s,c in zip(keys,src,cams):
  require(rt.resume(n+'_source_'+k),'source seal');require(np.isfinite(s['xyz']).all(),'source nonfinite');require(np.isfinite(s['depth_summary']).all(),'depth nonfinite');require(s['accepted_offsets'][-1]==len(s['accepted_ids'])==len(s['accepted_weights']),'CSR shape');require(np.all(s['accepted_ids']>=0) and np.all(s['accepted_ids']<pp.scene(n)['count']),'kernel IDs')
  uv,z=project(s['xyz'],c);require(np.max(np.linalg.norm(uv-s['pixels'],axis=1))<1e-3,'source ray reprojection')
  sums=np.add.reduceat(s['accepted_weights'].astype(float),s['accepted_offsets'][:-1]);require(np.max(abs(sums-s['depth_summary'][:,4]))<1e-6,'accepted weight sum')
  scene_result['depth'][k]=dict(points=len(z),min_depth=float(z.min()),max_source_reprojection=float(np.linalg.norm(uv-s['pixels'],axis=1).max()),accepted_entries=len(s['accepted_ids']),finite=True)
 require(rt.resume(n+'_fusion'),'fusion seal');require(rt.resume(n+'_asset'),'asset seal');maxerr=0;maxdisp=0
 for i,ids in enumerate(prov['node_sources']):
  require(len(set(d['view'][ids].tolist()))==len(ids)>=2,'distinct multiview nodes')
  for j in ids:
   c=cams[d['view'][j]];uv,z=project([f['xyz'][i]],c);err=np.linalg.norm(uv[0]-d['pixels'][j]);disp=np.linalg.norm(f['xyz'][i]-d['xyz'][j])/d['world_pixel'][j];maxerr=max(maxerr,float(err));maxdisp=max(maxdisp,float(disp));require(z[0]>0 and err<2.0001 and disp<2.5001,'allsource bounds')
 scene_result['source_track'].update(max_reprojection_px=maxerr,max_displacement_wpp=maxdisp,all_sources_checked=True)
 usedmap={int(c):i for i,c in enumerate(f['used_clusters'])};ehist=collections.Counter();angles=[];ratios=[];length_wpp=[];segment_reprojections=[];edge_rows=[]
 for ei,(uv,rawids) in enumerate(zip(f['edges'],prov['edge_sources'])):
  u,v=map(int,uv);q0,q1=f['xyz'][uv];edgeviews=set();maxshift=0;mincos=1;maxratio=0
  for j in rawids:
   a,b=map(int,d['edges'][j]);mu=usedmap[int(f['raw_to_cluster'][a])];mv=usedmap[int(f['raw_to_cluster'][b])];require({mu,mv}=={u,v},'edge provenance topology');require(d['view'][a]==d['view'][b],'source edge spans cameras');edgeviews.add(int(d['view'][a]));qa,qb=f['xyz'][[mu,mv]];raw=d['xyz'][b]-d['xyz'][a];new=qb-qa;rl=np.linalg.norm(raw);nl=np.linalg.norm(new);cos=float(new@raw/max(rl*nl,1e-20));ratio=float(nl/max(rl,1e-20));angles.append(float(np.degrees(np.arccos(np.clip(cos,-1,1)))));ratios.append(ratio);mincos=min(mincos,cos);maxratio=max(maxratio,ratio)
   c=cams[d['view'][a]];projected,_=project([qa,qb],c);err=np.linalg.norm(projected-d['pixels'][[a,b]],axis=1).max();maxshift=max(maxshift,float(err));segment_reprojections.append(float(err))
  ehist[len(edgeviews)]+=1;wp=float(np.mean([d['world_pixel'][j] for j in prov['node_sources'][u]+prov['node_sources'][v]]));length_wpp.append(float(np.linalg.norm(q1-q0)/wp));edge_rows.append(dict(fused_edge=ei,distinct_source_edges=len(rawids),distinct_source_cameras=len(edgeviews),source_camera_indices=sorted(edgeviews),max_source_endpoint_error_px=maxshift,min_direction_cos=mincos,max_length_ratio=maxratio,world_pixel_length=length_wpp[-1]))
 scene_result['edge']=dict(source_camera_histogram=dict(ehist),direction_change_deg_quantiles=np.quantile(angles,[.5,.95,.99,1]).tolist(),raw_source_direction_reversals=int(np.sum(np.array(angles)>90)),length_ratio_quantiles=np.quantile(ratios,[.5,.95,.99,1]).tolist(),final_length_wpp_quantiles=np.quantile(length_wpp,[.5,.95,.99,1]).tolist(),over_initial_6wpp_limit=int(np.sum(np.array(length_wpp)>6)),source_endpoint_reprojection_max=max(segment_reprojections),no_new_cross_chain_edges=True)
 ep=rt.ART/'results'/(n+'_EDGE_AUDIT.json');rt.atomic_json(ep,dict(summary=scene_result['edge'],edges=edge_rows));files.append(ep)
 # Characterize actual accepted-track ordering (the frozen window vote is not strict monotonic).
 groups=collections.defaultdict(list)
 for pair in prov['pair_records']:
  if pair['reason']!='track_accepted':continue
  a,b=pair['a'],pair['b'];key=(int(d['view'][a]),int(d['view'][b]),int(d['chain'][a]),int(d['chain'][b]));groups[key].append((int(d['local'][a]),int(d['local'][b])))
 flips=0;weak=0;total=0
 for pairs in groups.values():
  pairs=sorted(pairs);last=0
  for a,b in zip(pairs,pairs[1:]):
   if a[0]==b[0] or max(abs(b[0]-a[0]),abs(b[1]-a[1]))>4:last=0;continue
   sign=int(np.sign(b[1]-a[1]));flips+=int(last!=0 and sign!=last);last=sign
  for a,b in pairs:
   local=[(x,y) for x,y in pairs if abs(x-a)<=4 and abs(y-b)<=4];vote=max(sum((x-a)*(y-b)>=0 for x,y in local),sum((x-a)*(y-b)<=0 for x,y in local));weak+=int(vote<3);total+=1
 scene_result['source_track'].update(accepted_pair_count=total,local_direction_sign_changes=flips,accepted_pairs_with_fewer_than3_final_local_votes=weak,strict_monotonic_certification=False)
 folders=[rt.ART/'assets'/n/a for a in ('single','rawunion','fused')]+[rt.ART/'assets'/n/'sources'/k for k in keys]
 for folder in folders:
  a=dict(np.load(folder/'tubes.npz'));cent=dict(np.load(folder/'centerlines.npz'));j=json.loads((folder/'CENTERLINES.json').read_text());v,fm=glb(folder/'tubes.glb');require(np.array_equal(a['vertices'],v) and np.array_equal(a['faces'],fm),'GLB mismatch')
  ovs=[];ofs=[]
  with (folder/'tubes.obj').open() as obj:
   for line in obj:
    if line.startswith('v '):ovs.append([float(x) for x in line.split()[1:]])
    elif line.startswith('f '):ofs.append([int(x)-1 for x in line.split()[1:]])
  require(np.array_equal(np.asarray(ovs,np.float32),v),'OBJ vertex mismatch');require(np.array_equal(np.asarray(ofs,np.int32),fm),'OBJ face mismatch')
  require(j['geometry_sha256']==geometry_hash(cent['xyz'],cent['edges'],float(cent['radius'])),'geometry hash');require(np.array_equal(np.asarray(j['xyz'],np.float32),cent['xyz']),'JSON centers');require(np.array_equal(np.asarray(j['edges'],np.int32),cent['edges']),'JSON edges')
  pe=PlyData.read(str(folder/'control_points.ply'))['vertex'];require(np.array_equal(np.c_[pe['x'],pe['y'],pe['z']],cent['xyz']),'PLY centers')
  paths=collections.Counter(tuple(sorted((a,b))) for p in j['paths'] for a,b in zip(p,p[1:]));expected=collections.Counter(tuple(sorted(e)) for e in cent['edges'].tolist());require(paths==expected,'path edges incomplete')
  rings=v.reshape(-1,2,8,3);axis=cent['xyz'][cent['edges']];rad=np.linalg.norm(rings-axis[:,:,None,:],axis=3);require(np.max(abs(rad-float(cent['radius'])))<2e-7,'world radius not actual tube')
  scene_result['assets'].append(dict(path=str(folder.relative_to(rt.ROOT)),vertices=len(v),faces=len(fm),geometry_sha256=j['geometry_sha256'],world_radius=float(cent['radius']),world_radius_max_error=float(np.max(abs(rad-float(cent['radius'])))),paths=len(j['paths'])))
 scene_result['limitations']=['Frozen local order rule is anchor-window sign voting, not globally monotonic track certification.','Only endpoints require multiview identity candidate; individual edges can have one source camera.','Fused endpoint bounds do not guarantee unchanged source edge direction/length; measured above.','Source +/-3 tangent may cross a rejected depth discontinuity. All remain candidates.','No physical surface depth or original GS opaque occlusion calibrated.']
 pp.seal(n+'_contract_audit',files,dict(status='PASS_EXPORT_AND_DECLARED_NODE_BOUNDS',**scene_result));print('AUDIT',n,json.dumps(scene_result['edge']),flush=True)

def lineage():
 old=Path('/home/u00134/3dgs_line/gaer_multiview_contour_regions_v01/experiments/gaer_multiview_contour_regions_v01/cpu_native.py');new=rt.EXP/'cpu_native.py'
 def cpp(p):
  tree=ast.parse(p.read_text());return next(ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='CPP' for t in n.targets))
 require(cpp(old)==cpp(new),'inherited forward changed');results=[]
 for p in sorted((pp.OLDART/'tdd').glob('native_calibration_*.json')):
  j=json.loads(p.read_text());results.append(dict(path=str(p),sha256=rt.sha(p),status=j['status'],scene=j['scene'],camera=j['camera'],rgb_mae=j['rgb_mae'],mass_l1_relative=j['mass_l1_relative']))
 require(len(results)==4 and all(r['status']=='PASS' for r in results),'four historical calibrations')
 rt.atomic_json(rt.ART/'CPU_CALIBRATION_LINEAGE.json',dict(inherited_forward_cpp_identical=True,cpp_sha256=hashlib.sha256(cpp(new).encode()).hexdigest(),historical_four_results=results,new_sparse_query='analytic fixtures plus all construction sample accepted-sum versus sealed alpha; not surface depth calibration',cuda_executed=False,bit_exact_cuda_claim=False))

def protection():
 f=pp.frozen();bad=[]
 for p,h in f['protected_before'].items():
  if rt.sha(p)!=h:bad.append(p)
 require(not bad,'protected files changed: '+str(bad))
 heads=dict(x.split(' ',1) for x in subprocess.check_output(['git','for-each-ref','--format=%(refname) %(objectname)','refs/heads'],text=True).splitlines());changed={k:[v,heads.get(k)] for k,v in f['heads_before'].items() if k!='refs/heads/gaer-multiview-contour-lift-v01' and heads.get(k)!=v};require(not changed,'old branch heads changed')
 seals=0;refs=0
 for p in (rt.ART/'seals').glob('*.json'):
  j=json.loads(p.read_text())
  for k,h in j['files'].items():require(rt.sha(rt.ROOT/k)==h,'seal referenced file changed '+k);refs+=1
  seals+=1
 require(json.loads((rt.ART/'FUSION_FREEZE.json').read_text())['code']==rt.method_hashes(),'producer code differs freeze')
 rt.atomic_json(rt.ART/'PROTECTION_AUDIT.json',dict(status='PASS',protected_file_count=len(f['protected_before']),historical_branches_verified=len(f['heads_before'])-1,seals=seals,file_hash_references=refs,producer_code_equals_pre_extraction_freeze=True,resource=rt.guard('protection_audit')))
 print('PROTECTION_PASS',seals,refs,flush=True)
if __name__=='__main__':
 import sys
 if '--protection-only' not in sys.argv:
  lineage()
  for n in ('lego','chair'):contract_scene(n)
 protection()
