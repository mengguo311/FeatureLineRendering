from runtime_io import *
from geometry_base import *
from frontier_core import chain_q
from scene_render import geometry_fingerprint,enrich_groups,render_arm

def serial(state):
 return {k:({str(i):v for i,v in x.items()} if isinstance(x,dict) else sorted(x) if isinstance(x,set) else x) for k,x in state.items()}

def save_stage(out,c,d,state,oracle,binding):
 old=d['membership'];m={k:v.copy() for k,v in old.items()};m['previous_edge_id']=old['edge_id'].copy();m['composite_version']=np.full(len(m['edge_id']),-1,np.int64);groups=[]
 for seed,chain in sorted(state['chains'].items()):
  ok,why,met=oracle(chain)
  if not ok:
   # Failed seed is a saved unmodified reference, never promoted.
   groups.append(dict(edge_id=seed,seed_status=why,leaves=[dict(carrier_id=i,version=d['leaves'][i].version,reverse=r) for i,r in chain]));continue
  rows=np.concatenate([d['leaves'][i].rows for i,_ in chain]);activate=met['seedlets']>=3 and len(rows)>=6 and met['supported_length_p']>=4-EPS
  if len(chain)>1:
   selected=(m['edge_id'][rows]>=0)|activate;rr=rows[selected];m['edge_id'][rr]=seed;m['reason_code'][rr]=0;m['composite_version'][rr]=state['versions'][seed];m['provisional'][rr]=True
  groups.append(dict(edge_id=seed,version=state['versions'][seed],seed_status='valid',leaves=[dict(carrier_id=i,version=d['leaves'][i].version,reverse=r) for i,r in chain],**met))
 # Explicit protected-leaf tracer invariant; not a general v08 scientific gate.
 assert not np.any((old['edge_id']>=0)&(m['edge_id']<0))
 for seed,chain in state['chains'].items():
  for i,_ in chain:
   rr=d['leaves'][i].rows
   if np.any(old['edge_id'][rr]>=0):assert len(np.unique(m['edge_id'][rr]))==1
 out=Path(out);out.mkdir(parents=True,exist_ok=True)
 nz(out/'MEMBERSHIP.npz',**m);js(out/'GROWTH_STATE.json',serial(state));js(out/'GROUPS.json',dict(groups=groups,background_reference=c['membership'],scope='four protected M5 seed prefixes; complete rows are not complete search'))
 js(out/'LINEAGE.json',dict(events=state['events'],leaf_reference=c['carriers'],accepted_merge_is_ground_truth=False))
 ids=sorted({i for ch in state['chains'].values() for i,_ in ch});offset=[0];knots=[]
 for i in ids:knots.extend(d['leaves'][i].q*d['p']);offset.append(len(knots))
 nz(out/'CARRIERS.npz',carrier_id=np.asarray(ids),version=np.array([d['leaves'][i].version for i in ids]),knot_offsets=np.asarray(offset),knots=np.asarray(knots))
 js(out/'CARRIER_SCHEMA.json',dict(meaning='unchanged finite leaves in seed paths; all background leaves in bound reference',reference=c['carriers'],reference_sha256=c['input_files'][c['carriers']],ordered_composite_carriers='GROWTH_STATE.json',connectors_observed=False))
 checkpoint(out,['MEMBERSHIP.npz','GROWTH_STATE.json','GROUPS.json','LINEAGE.json','CARRIERS.npz','CARRIER_SCHEMA.json'],binding,'COMPLETE_MEMBERSHIP_TOPOLOGY')
 verify_checkpoint(out,binding)
 cold=dict(np.load(out/'MEMBERSHIP.npz',allow_pickle=False))
 for k,v in m.items():np.testing.assert_array_equal(cold[k],v)
 return cold,groups

def cross_accounting(reference,current):
 old=np.asarray(reference);new=np.asarray(current);mask=old>=0
 pairs=np.unique(np.stack([old[mask],new[mask]],1),axis=0);splits=sum(np.sum(pairs[:,0]==i)>1 for i in np.unique(pairs[:,0]))
 return dict(reference_assigned=int(np.sum(old>=0)),assigned=int(np.sum(new>=0)),unknown=int(np.sum(new<0)),gained=int(np.sum((old<0)&(new>=0))),lost=int(np.sum((old>=0)&(new<0))),label_changed_rows=int(np.sum(old!=new)),old_groups_split_including_unknown=int(splits),note='ID changes alone are not gains; pair intersections saved separately')

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
  js(out/'SCOPE.json',dict(member_rows=len(rr),context_rows=len(hr),all_incident_frontier_endpoint_carriers=True,physical_context_complete=False,negative_truth='UNKNOWN'))
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

def statistics(out,c,d,m,gs,guard):
 valid=[g for g in gs if g.get('seed_status')=='valid'];enriched=enrich_groups(d,valid,guard)
 oldm4=np.load(c['m4_membership'],allow_pickle=False)['carrier_id']
 for g in enriched:
  seed=g['edge_id'];seed_dom=next(v for v in g['leaf_domains_p'] if v['carrier_id']==seed)
  g['support_outside_seed_domain_p']=sum(max(0,min(b,seed_dom['start'])-a)+max(0,b-max(a,seed_dom['end'])) for a,b in g['supported_intervals']);g['M4_contributions']=[]
  rr=np.concatenate([d['leaves'][z['carrier_id']].rows for z in g['leaves']]);ids,counts=np.unique(oldm4[rr],return_counts=True)
  for cid,count in zip(ids,counts):
   intervals=[]
   for z,dom in zip(g['leaves'],g['leaf_domains_p']):
    leaf=d['leaves'][z['carrier_id']];reps=leaf.reps[oldm4[d['representatives']['mid'][leaf.reps]]==cid]
    if len(reps):
     iv=project(d['representatives']['endpoints'][reps].reshape(-1,3)/d['p'],leaf.q)[0].reshape(-1,2)
     if dom['reverse']:iv=arc(leaf.q)[-1]-iv
     intervals.extend((iv+dom['start']).tolist())
   support=union_intervals(intervals)[1];g['M4_contributions'].append(dict(carrier_id=int(cid),kernels=int(count),support_proxy_p=support,substantial=bool(count>=12 and support>=2-EPS)))
  g['proxy_growth_gate']=g['support_outside_seed_domain_p']>=4-EPS and sum(x['substantial'] for x in g['M4_contributions'])>=3
 js(Path(out)/'GROUP_STATISTICS.json',dict(groups=enriched,physical_identity=False,interval_union_not_continuous_length=True))
 refs={'M5':d['membership']['edge_id']}
 for name,path in c['external_memberships'].items():refs[name]=np.load(path,allow_pickle=False)['edge_id']
 metrics={}
 for name,ids in refs.items():
  guard();metrics[name]=cross_accounting(ids,m['edge_id']);pairs,counts=np.unique(np.stack([ids,m['edge_id']],1),axis=0,return_counts=True);nz(Path(out)/f'{name}_CROSS.npz',pairs=pairs,counts=counts)
 js(Path(out)/'METRICS.json',metrics)
