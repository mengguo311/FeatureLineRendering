"""Local measurement memberships, not a global scene segmentation or new surface."""
from env import *
from geometry_roles import ROLES,PALETTE
def overlap(a,b):
 ids=np.union1d(a['ids'],b['ids']);x=np.zeros(len(ids));y=x.copy()
 for n,z in [(a,x),(b,y)]:
  if len(n['ids']):np.add.at(z,np.searchsorted(ids,n['ids']),n['mass'])
 if x.sum()<=0 or y.sum()<=0:return 0.
 return float(np.minimum(x/x.sum(),y/y.sum()).sum())
def pair_sides(a,b,cfg):
 M=np.array([[overlap(x,y) for y in b] for x in a]);direct=M[0,0]+M[1,1];reverse=M[0,1]+M[1,0];rev=reverse>direct;margin=float(abs(direct-reverse));out=dict(pairing='reversed' if rev else 'direct',overlap_matrix=M.tolist(),pairing_margin=margin,accepted=[],checks=[],reason='checked')
 if margin<cfg['min_pairing_margin']:out['reason']='pairing_ambiguous';return out
 for i,j in [(0,1 if rev else 0),(1,0 if rev else 1)]:
  x,y=a[i],b[j];r=dict(i=i,j=j,overlap=float(M[i,j]),accepted=False)
  if not(x['valid'] and y['valid']) or x['role_index'] not in [0,1,2] or y['role_index'] not in [0,1,2]:r['reason']='unqualified_local_role_or_patch'
  else:
   p=max(x['pixel'],y['pixel']);d=np.asarray(y['center'])-np.asarray(x['center']);nx=np.asarray(x['normal']);ny=np.asarray(y['normal']);angle=float(np.degrees(np.arccos(np.clip(abs(nx@ny),0,1))));plane=float(max(abs(d@nx),abs(d@ny))/p);distance=float(np.linalg.norm(d)/p);ok=M[i,j]>=cfg['min_weighted_ID_overlap'] and angle<=cfg['max_normal_deg'] and plane<=cfg['max_symmetric_plane_pixels'] and distance<=cfg['max_center_distance_pixels'];r.update(angle_deg=angle,symmetric_plane_pixels=plane,center_distance_pixels=distance,accepted=bool(ok),reason='compatible_measured_support_ONLY' if ok else 'ID_or_geometry_incompatible')
   if ok:out['accepted'].append([i,j])
  out['checks'].append(r)
 return out
def aggregate_roles(n,records):
 scores=np.zeros((n,5));mass=np.zeros(n);visits=np.zeros(n,np.int32)
 for ids,w,s in records:
  ids=np.asarray(ids,dtype=int);w=np.asarray(w,float);s=np.asarray(s,float)
  if np.any(ids<0) or np.any(ids>=n):raise ValueError('Source-only index outside original source count')
  if not(np.isfinite(w).all() and np.all(w>=0) and np.isfinite(s).all()):raise ValueError('Invalid responsibility or role score')
  np.add.at(mass,ids,w);np.add.at(scores,ids,w[:,None]*s);np.add.at(visits,ids,(w>0).astype(np.int32))
 good=mass>0;scores[good]/=mass[good,None];scores[~good,4]=1
 return dict(source_index=np.arange(n,dtype=np.int32),scores=scores,role_index=scores.argmax(1).astype(np.uint8),queried=good,weight_mass=mass,membership_count=visits)
def diagnostic_vertices(source,a,ids):
 ids=np.asarray(ids,int);d=np.zeros(len(ids),dtype=[('x','f4'),('y','f4'),('z','f4'),('source_index','i4'),('role_index','u1'),('red','u1'),('green','u1'),('blue','u1')])
 for k in ['x','y','z']:d[k]=source[k][ids]
 d['source_index']=ids;d['role_index']=a['role_index'][ids];co=np.rint(PALETTE[d['role_index']]*255).astype('uint8')
 for i,k in enumerate(['red','green','blue']):d[k]=co[:,i]
 return d
def load_node(path,side,node_id):
 r=json.loads((path/'RESULT.json').read_text());e=npz(path/'EVIDENCE.npz');p=r[side+'_patch'];m=e[side+'_mass'];sel=m>0
 return dict(node_id=node_id,scene=r['scene'],case=r['case'],view=r['view'],arm=r['arm'],side=side,role_index=r['role']['role_index'],role=r['role']['role'],reason=r['role']['reason'],valid=bool(p.get('valid')),ids=e['participant_ids'][sel],mass=m[sel],center=np.array(p.get('center',[0,0,0.])),normal=np.array(p.get('normal',[0,0,0.])),pixel=r['info']['pixel_world_proxy'],measurement=str(path),scores=np.array(r['role']['soft_role_scores']),depth_patch=p)
def serial_node(n):
 return {k:(v.tolist() if isinstance(v,np.ndarray) else v) for k,v in n.items() if k not in ['ids','mass','scores']}
def build(s):
 from plyfile import PlyData,PlyElement
 import csv,itertools
 out=ROOT/'scenes'/s/'graph';out.mkdir(exist_ok=True);assert not (out/'SEAL.json').exists();cfg=json.loads((ROOT/'GRAPH_CONFIG.json').read_text());case=json.loads((ROOT/'CASE_FREEZE.json').read_text())['cases'];source=read_ply(registry()[s]['model']);nodes=[];edges=[];records=[];primary=[];cases=[]
 for ca in case:
  if ca['scene']!=s or not ca['selection_valid']:continue
  for arm in ['line','shifted_12px','source_geometry_axis']:
   byview={}
   for v in VIEWS[s]:
    p=ROOT/'scenes'/s/'stage1'/v/ca['case']/arm
    if not (p/'RESULT.json').exists():continue
    pair=[]
    for side in ['left','right']:
     n=load_node(p,side,len(nodes));nodes.append(n);pair.append(n)
     if arm=='line':records.append((n['ids'],n['mass'],n['scores']));primary.append(n)
    byview[v]=pair
   for va,vb in itertools.combinations(byview,2):
    result=pair_sides(byview[va],byview[vb],cfg);result.update(case=ca['case'],arm=arm,view_a=va,view_b=vb,node_ids_a=[n['node_id'] for n in byview[va]],node_ids_b=[n['node_id'] for n in byview[vb]])
    edges.append(result)
 a=aggregate_roles(len(source),records);ids=np.flatnonzero(a['queried']);np.savez_compressed(out/'SOURCE_ROLE_SCORES.npz',**a)
 starts=np.r_[0,np.cumsum([len(n['ids']) for n in nodes])];np.savez_compressed(out/'PATCH_MEMBERSHIPS.npz',offsets=starts,source_index=np.concatenate([n['ids'] for n in nodes]),weight=np.concatenate([n['mass'] for n in nodes]),node_id=np.arange(len(nodes)))
 js(out/'PATCH_GRAPH.json',dict(nodes=[serial_node(n) for n in nodes],edges=edges,scope='local measurement support only; no surfaces reconstructed; controls never votes in source roles',original_source_count=len(source),original_source_sha256=sha(registry()[s]['model']),physical_primitives=0))
 d=diagnostic_vertices(source,a,ids);PlyData([PlyElement.describe(d,'vertex')],text=False,byte_order='<',comments=['Original SOURCE positions only; diagnostic point labels, NOT a replacement Gaussian model. No ink IDs.']).write(out/'SOURCE_ROLE_DIAGNOSTIC.ply')
 with (out/'SOURCE_ROLE_DIAGNOSTIC.csv').open('w') as f:
  w=csv.writer(f);w.writerow(['source_index','role','responsibility_mass','membership_count']+ROLES)
  for i in ids:w.writerow([int(i),ROLES[a['role_index'][i]],float(a['weight_mass'][i]),int(a['membership_count'][i])]+a['scores'][i].tolist())
 stats=dict(original_source_count=len(source),queried_source_count=len(ids),unqueried_unknown_count=len(source)-len(ids),patch_measurement_nodes=len(nodes),line_nodes=len(primary),physical_primitives_reconstructed=0,accepted_crossview_links_by_arm={arm:sum(len(e['accepted']) for e in edges if e['arm']==arm) for arm in ['line','shifted_12px','source_geometry_axis']},node_counts_by_local_role={r:sum(n['role']==r for n in primary) for r in ROLES},source_scores_are_uncalibrated=True)
 js(out/'COUNTS.json',stats);seal(out);return stats
if __name__=='__main__':
 failed=[]
 for s in SCENES:
  try:state('GRAPH_EXPORT',scene=s,status='RUNNING',children=[os.getpid()]);r=build(s);state('GRAPH_READY',scene=s,status='READY_FOR_REVIEW',children=[],graph_counts=r)
  except Exception as e:js(ROOT/f'GRAPH_FAILURE_{s}.json',dict(error=repr(e)));failed.append(s)
 if failed:state('GRAPH_FAILURE',status='ENGINEERING_NOT_READY',children=[],failed=failed);raise SystemExit(1)
