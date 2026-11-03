"""Atomic whole-row overlap checkpoints and common-coordinate support accounting."""
from frontier_delivery import *
from overlap_core import map_intervals
import copy

def save_stage(out,c,d,state,binding):
 out=Path(out);old=d['membership'];m={k:v.copy() for k,v in old.items()};m['previous_edge_id']=old['edge_id'].copy();m['composite_version']=np.full(len(m['edge_id']),-1,np.int64);groups=[]
 aliases={cid:sid for sid,ch in state['chains'].items() for cid,_ in ch}
 if 'auxiliary_carrier_id' in m:
  raw=m['auxiliary_carrier_id'];aux=raw.copy();owner=d['owner'].copy()
  for cid,sid in aliases.items():aux[raw==cid]=sid;owner[d['owner']==cid]=sid
  aux[aux==owner[:,None]]=-1
  if aux.shape[1]==2:
   aux[:,1][aux[:,0]==aux[:,1]]=-1;move=(aux[:,0]<0)&(aux[:,1]>=0);aux[move,0]=aux[move,1];aux[move,1]=-1
  m['auxiliary_composite_id']=aux
 for sid,ch in sorted(state['chains'].items()):
  met=state['metrics'][sid];rows=np.concatenate([d['leaves'][cid].rows for cid,_ in ch]);activate=met.get('seedlets',0)>=3 and len(rows)>=6 and met.get('supported_length_p',0)>=4-EPS
  if len(ch)>1:
   assert met['seed_status']=='valid';sel=(old['edge_id'][rows]>=0)|activate;rr=rows[sel];m['edge_id'][rr]=sid;m['reason_code'][rr]=0;m['provisional'][rr]=True;m['composite_version'][rr]=state['versions'][sid]
  groups.append(dict(edge_id=sid,version=state['versions'][sid],leaves=[dict(carrier_id=cid,version=d['leaves'][cid].version,reverse=rev) for cid,rev in ch],**met))
 assert not np.any((old['edge_id']>=0)&(m['edge_id']<0))
 for sid,ch in state['chains'].items():
  for cid,_ in ch:
   rows=d['leaves'][cid].rows
   if np.any(old['edge_id'][rows]>=0):assert len(np.unique(m['edge_id'][rows]))==1
 nz(out/'MEMBERSHIP.npz',**m);js(out/'GROWTH_STATE.json',serial(state));js(out/'GROUPS.json',dict(groups=groups,background_reference=c['membership'],scope='four protected M5 seeds; finite overlap-only frontier search'))
 js(out/'LINEAGE.json',dict(events=state['events'],leaf_reference=c['carriers'],accepted_merge_is_ground_truth=False))
 ids=sorted(state['curves']);ko=[0];knots=[]
 for sid in ids:knots.extend(np.asarray(state['curves'][sid])*d['p']);ko.append(len(knots))
 nz(out/'CARRIERS.npz',carrier_id=np.array(ids),version=np.array([state['versions'][sid] for sid in ids]),knot_offsets=np.array(ko),knots=np.asarray(knots),geometry_kind=np.asarray('finite_overlap_auxiliary_composite'))
 leafids=sorted(aliases);ko=[0];knots=[]
 for cid in leafids:knots.extend(d['original_leaves'][cid].q*d['p']);ko.append(len(knots))
 nz(out/'ORIGINAL_LEAF_CARRIERS.npz',carrier_id=np.array(leafids),version=np.array([d['original_leaves'][i].version for i in leafids]),knot_offsets=np.array(ko),knots=np.asarray(knots))
 js(out/'CARRIER_SCHEMA.json',dict(auxiliary_curve_replaced=True,original_leaf_q_unchanged=True,all_original_members_retained=True,no_auxiliary_ink=True,support_coordinate='current auxiliary arc; mapped original support, not new observations',reference=c['carriers'],reference_sha256=c['input_files'][c['carriers']]))
 files=['MEMBERSHIP.npz','GROWTH_STATE.json','GROUPS.json','LINEAGE.json','CARRIERS.npz','ORIGINAL_LEAF_CARRIERS.npz','CARRIER_SCHEMA.json']
 checkpoint(out,files,binding,'COMPLETE_OVERLAP_MEMBERSHIP_TOPOLOGY');verify_checkpoint(out,binding)
 cold=dict(np.load(out/'MEMBERSHIP.npz',allow_pickle=False))
 for k in m:np.testing.assert_array_equal(cold[k],m[k])
 return cold,groups

def statistics_overlap(out,c,d,m,groups,state,guard):
 enriched=copy.deepcopy(groups);m4=np.load(c['m4_membership'],allow_pickle=False)['carrier_id']
 for g in enriched:
  guard();sid=g['edge_id'];q=np.asarray(state['curves'][sid]);rows=np.concatenate([d['leaves'][z['carrier_id']].rows for z in g['leaves']]);reps=np.unique(np.concatenate([d['leaves'][z['carrier_id']].reps for z in g['leaves']]))
  if g.get('seed_status')!='valid':continue
  seedpts=d['leaves'][sid].q;seeddom=project(seedpts,q)[0];lo=float(min(seeddom));hi=float(max(seeddom));ivs=g['supported_intervals']
  g['support_outside_seed_domain_p']=sum(max(0.,min(b,lo)-a)+max(0.,b-max(a,hi)) for a,b in ivs)
  g['seed_projected_domain_p']=[lo,hi];seediv=union_intervals(map_intervals(d['leaves'][sid],q)[0])[1];g['support_union_gain_over_mapped_seed_p']=g['supported_length_p']-seediv
  g['internal_fill_or_pooling_proxy_p']=g['support_union_gain_over_mapped_seed_p']-g['support_outside_seed_domain_p']
  for key,labels,field in [('M4_contributions',m4,'carrier_id'),('parent_contributions',d['asset']['primitive_id'],'parent')]:
   items=[];ids,counts=np.unique(labels[rows],return_counts=True)
   for cid,count in zip(ids,counts):
    rep=reps[labels[d['representatives']['mid'][reps]]==cid];iv=project(d['representatives']['endpoints'][rep].reshape(-1,3)/d['p'],q)[0].reshape(-1,2) if len(rep) else []
    support=union_intervals(iv)[1];items.append({field:int(cid),'kernels':int(count),'support_proxy_p':support,'substantial':bool(count>=12 and support>=2-EPS)})
   g[key]=items
  g['proxy_growth_gate']=g['support_outside_seed_domain_p']>=4-EPS and sum(x['substantial'] for x in g['M4_contributions'])>=3;g['physical_identity_verified']=False;g['provisional']=True;g['support_note']='Projected proxy union, not continuous observation; overlap counted once. Original seed and donor q retained separately.'
 js(Path(out)/'GROUP_STATISTICS.json',dict(groups=enriched,physical_identity=False,interval_union_not_continuous_length=True))
 refs={'M5':d['membership']['edge_id']}
 for name,path in c['external_memberships'].items():refs[name]=np.load(path,allow_pickle=False)['edge_id']
 metrics={}
 for name,ids in refs.items():
  guard();metrics[name]=cross_accounting(ids,m['edge_id']);pairs,counts=np.unique(np.stack([ids,m['edge_id']],1),axis=0,return_counts=True);nz(Path(out)/f'{name}_CROSS.npz',pairs=pairs,counts=counts)
 js(Path(out)/'METRICS.json',metrics)

def diagnostics(unit,c,d,saved,contexts,render,cams,guard):
 root=Path(unit)/'scenes'/c['scene']/'diagnostics';root.mkdir(parents=True,exist_ok=True);a=d['asset'];images=[];cases=[]
 for seed in sorted(c['seeds'],key=lambda x:x[0]):
  sid=seed[0];members=set(d['leaves'][sid].rows.tolist());halo=set(contexts[sid])
  for m,gs in saved.values():
   for g in gs:
    if g['edge_id']==sid:
     for z in g['leaves']:members.update(d['leaves'][z['carrier_id']].rows.tolist());halo.add(z['carrier_id'])
  rr=np.array(sorted(members),np.int64);hr=np.unique(np.concatenate([d['leaves'][i].rows for i in sorted(halo)]))
  cases.append((str(sid),rr,hr))
 with np.load(c['negative_carriers'],allow_pickle=False) as z:
  lookup={int(i):j for j,i in enumerate(z['carrier_id'])}
  for aa,bb in c['negative_pairs']:
   rs=[z['rows'][z['row_offsets'][lookup[i]]:z['row_offsets'][lookup[i]+1]] for i in (aa,bb) if i in lookup]
   rr=np.unique(np.concatenate(rs)) if rs else np.empty(0,np.int64)
   halo=set(d['owner'][rr].tolist())-{-1};hr=np.unique(np.concatenate([d['leaves'][i].rows for i in halo])) if halo else rr
   cases.append((f'negative_{aa}_{bb}',rr,hr))
 for tag,rr,hr in cases:
  guard();out=root/tag;out.mkdir(exist_ok=True);nz(out/'ROWS.npz',members=rr,context=hr)
  js(out/'SCOPE.json',dict(member_rows=len(rr),context_rows=len(hr),all_queried_finite_segment_carriers=True,old_endpoint_context_included=True,physical_context_complete=False,negative_truth='UNKNOWN'))
  for cam in cams:
   for mode,rows in [('ISOLATED',rr),('CONTEXT',hr)]:
    pics=[]
    for arm,(m,_) in saved.items():
     guard();cols=colors(m['edge_id'][rows]);sub={k:a[k][rows] for k in ('means','covariance','opacity')};sub['colors']=cols
     rgb=render(sub,cam,(1,1,1),.0144)['rgb'] if len(rows) else np.ones((cam['height'],cam['width'],3))
     name=f'{arm}_{cam["view"]}_{mode}.png';save_image(out/name,rgb);images.append(str((out/name).relative_to(unit)));pics.append((arm,rgb))
    union=np.any(np.stack([np.any(np.rint(np.clip(rgb,0,1)*255)<254,axis=2) for _,rgb in pics]),axis=0);yx=np.argwhere(union)
    bbox=None
    if len(yx):
     y0,x0=np.maximum(yx.min(0)-16,0);y1,x1=np.minimum(yx.max(0)+17,union.shape);bbox=[int(x0),int(y0),int(x1),int(y1)]
     for arm,rgb in pics:
      crop=Image.fromarray(np.uint8(np.rint(np.clip(rgb[y0:y1,x0:x1],0,1)*255)));crop=crop.resize((crop.width*4,crop.height*4),Image.Resampling.NEAREST)
      fn=out/f'{arm}_{cam["view"]}_{mode}_CROP.png';atomic(fn,lambda f:crop.save(f,format='PNG'));images.append(str(fn.relative_to(unit)))
    js(out/f'{cam["view"]}_{mode}_BBOX.json',dict(bbox=bbox,empty=bbox is None,pad=16,scale=4,clipped_to_frame=True))
   if not tag.startswith('negative'):
    for arm,(m,_) in saved.items():
     guard();cols=np.full((len(a['means']),3),.82);cols[rr]=colors(m['edge_id'][rr]);sub={k:a[k] for k in ('means','covariance','opacity')};sub['colors']=cols
     fn=out/f'{arm}_{cam["view"]}_HIGHLIGHT.png';save_image(fn,render(sub,cam,(1,1,1),.0144)['rgb']);images.append(str(fn.relative_to(unit)))
 return images
