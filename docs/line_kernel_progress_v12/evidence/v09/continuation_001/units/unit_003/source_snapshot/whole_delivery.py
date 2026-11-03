"""Compact replayable topology stages and native original-kernel diagnostics."""
from runtime_io import *
from geometry_base import arc,project,union_intervals
from scene_render import render_arm,colors
import whole_core as core

def serial(v):
 if isinstance(v,dict):return {str(k):serial(x) for k,x in v.items()}
 if isinstance(v,(list,tuple)):return [serial(x) for x in v]
 if isinstance(v,np.ndarray):return v.tolist()
 if isinstance(v,np.generic):return v.item()
 return v

def mapping(d,objects):
 original=d['initial_membership'];m={k:v.copy() for k,v in original.items()};m['v09_previous_edge_id']=original['edge_id'].copy();m['source_carrier_id']=original['carrier_id'].copy();m['group_model_version']=np.full(len(m['edge_id']),-1,np.int64)
 for gid,o in objects.items():
  if gid<0:continue
  rows=o['rows'];m['edge_id'][rows]=gid;m['group_model_version'][rows]=o['version']
  changed=rows[original['edge_id'][rows]!=gid]
  if len(changed):
   if 'reason_code' in m:m['reason_code'][changed]=0
   if 'provisional' in m:m['provisional'][changed]=True
 assert not np.any((original['edge_id']>=0)&(m['edge_id']<0));return m

def save_stage(out,c,d,objects,events,next_version,binding,changed=None):
 out=Path(out);m=mapping(d,objects);nz(out/'MEMBERSHIP.npz',**m)
 # Full changed/active model bank relative to immutable original checkpoint.
 selected={gid:o for gid,o in objects.items() if o['seed_origins']};ids=sorted(selected);qs=[selected[i]['q'] for i in ids];rr=[selected[i]['rows'] for i in ids]
 nz(out/'MODELS.npz',group_id=np.asarray(ids,np.int64),version=np.asarray([selected[i]['version'] for i in ids]),knots_p=np.concatenate(qs) if qs else np.empty((0,3)),knot_offsets=np.r_[0,np.cumsum([len(q) for q in qs])],rows=np.concatenate(rr) if rr else np.empty(0,int),row_offsets=np.r_[0,np.cumsum([len(r) for r in rr])])
 groups=[dict(id=gid,version=o['version'],rows=o['rows'].tolist(),leaves=o['leaves'],seed_origins=o['seed_origins'],metrics=o.get('metrics'),geometry_available=o['available']) for gid,o in selected.items()]
 js(out/'GROUPS.json',dict(groups=groups,unchanged_background=c['initial_stage'],no_original_kernel_geometry_copy=True));js(out/'LINEAGE.json',dict(historical=d['historical_events'],events=events,next_version=next_version,changed=changed,checkpoint_replay='immutable initial state plus ordered whole-member donor deltas',original_kernel_ink_only=True))
 checkpoint(out,['MEMBERSHIP.npz','MODELS.npz','GROUPS.json','LINEAGE.json'],binding,'COMPLETE_MONOTONE_GROUP_UNION');verify_checkpoint(out,binding)
 cold=dict(np.load(out/'MEMBERSHIP.npz',allow_pickle=False))
 for key in m:np.testing.assert_array_equal(cold[key],m[key])
 return m

def save_library(out,lib):
 out=Path(out);pack={};records=[]
 for i,r in enumerate(lib['records']):
  z={k:serial(v) for k,v in r.items() if k not in ('q','template','local_movable')}
  for key in ('q','template','local_movable'):
   if key in r:pack[f'{i}_{key}']=r[key];z[key+'_array']=f'{i}_{key}'
  records.append(z)
 nz(out/'GEOMETRY.npz',**pack);js(out/'LIBRARY.json',dict(complete=lib['complete'],reason=lib['reason'],neighbors=lib['neighbors'],selected=lib['selected'],records=records,all_neighbors_queried=True,no_top_k=True,current_donor=lib.get('current_donor'),unattempted_donors=lib.get('unattempted_donors',[])))

def contingency(a,b):
 x=a['edge_id'];y=b['edge_id'];pairs,counts=np.unique(np.c_[x,y],axis=0,return_counts=True);old=pairs[:,0];split=0
 for gid in np.unique(old[old>=0]):split+=int(np.sum(old==gid)>1)
 return dict(gained=int(np.sum((x<0)&(y>=0))),lost=int(np.sum((x>=0)&(y<0))),label_changed_rows=int(np.sum(x!=y)),old_groups_split_including_unknown=split),pairs,counts

def statistics(out,c,d,objects,m,guard):
 out=Path(out);report={};refs=dict(c['external_memberships'],START=str(Path(c['initial_stage'])/'MEMBERSHIP.npz'),M5=c['membership'])
 for name,path in refs.items():
  guard();old=dict(np.load(path,allow_pickle=False));metrics,pairs,counts=contingency(old,m);report[name]=metrics;nz(out/(name+'_CROSS.npz'),pairs=pairs,counts=counts)
 rows=[];m4=dict(np.load(c['m4_membership'],allow_pickle=False));m4ids=m4.get('carrier_id',m4.get('edge_id'))
 for gid,o in objects.items():
  if not o['seed_origins']:continue
  guard();q=o['q'];sup=core.support(d,o['rows'],q);contrib=[]
  for oldid in np.unique(m4ids[o['rows']]):
   rr=o['rows'][m4ids[o['rows']]==oldid];sp=core.support(d,rr,q);contrib.append(dict(id=int(oldid),kernels=len(rr),support_p=sp['union'],substantial=len(rr)>=12 and sp['union']>=2))
  parents,pc=np.unique(d['asset']['primitive_id'][o['rows']],return_counts=True);outside=[]
  for sid in o['seed_origins']:
   q0=d['objects'][sid]['q'];dom=project(q0,q)[0];lo,hi=float(dom.min()),float(dom.max());ext=sum(max(0,min(b,lo)-a)+max(0,b-max(a,hi)) for a,b in sup['intervals']);outside.append(dict(seed=sid,support_outside_start_domain_p=float(ext),starting_kernels=len(d['objects'][sid]['rows'])))
  rows.append(dict(id=gid,kernels=len(o['rows']),seed_origins=o['seed_origins'],finite_length_p=float(arc(q)[-1]),support_union_p=sup['union'],longest_run_p=sup['run'],max_gap_p=sup['gap'],total_gap_p=sup['total_gap'],M4_contributions=contrib,source_parents=dict(zip(map(str,parents),map(int,pc))),outward=outside,physical_identity_verified=False))
 js(out/'METRICS.json',dict(assigned=int(np.sum(m['edge_id']>=0)),unknown=int(np.sum(m['edge_id']<0)),references=report,groups=rows,full_mapping_is_not_full_scene_search=True,support_union_is_not_continuous_observation=True));return rows

def native_full(out,c,d,m,render,cams,guard):return render_arm(out,c,d,m,[],[],render,cams,guard,full_only=True)

def diagnostics(root,c,d,maps,states,contexts,render,cams,guard):
 root=Path(root);asset=d['asset'];outputs=[]
 for sid in c['seed_ids']:
  target=set(d['objects'][sid]['rows'].tolist());context=set(target)
  for objects in states.values():
   for o in objects.values():
    if sid in o['seed_origins']:target.update(o['rows'].tolist())
  for gid in contexts.get(sid,set()):
   if gid in d['objects']:context.update(d['objects'][gid]['rows'].tolist())
  context.update(target);target=np.asarray(sorted(target),int);context=np.asarray(sorted(context),int);out=root/'diagnostics'/str(sid);nz(out/'ROWS.npz',target=target,context=context)
  js(out/'SCOPE.json',dict(all_queried_competitors=True,physical_context_complete=False,target_rows=len(target),context_rows=len(context),identical_rows_across_arms=True,native_full_resolution=True))
  for arm,m in maps.items():
   base=colors(m['edge_id']);highlight=np.full_like(base,.82);highlight[target]=base[target]
   for cam in cams:
    for kind,rows,cols in [('ISOLATED',target,base[target]),('CONTEXT',context,base[context]),('HIGHLIGHT',np.arange(len(base)),highlight)]:
     guard();a={k:asset[k][rows] for k in ('means','covariance','opacity')};a['colors']=cols;path=out/f'{arm}_{cam["view"]}_{kind}.png';save_image(path,render(a,cam,(1,1,1),.0144)['rgb']);outputs.append(str(path.relative_to(root)))
  crop_receipts=[]
  for cam in cams:
   paths=[out/f'{arm}_{cam["view"]}_ISOLATED.png' for arm in maps];mask=None
   for path in paths:
    rgb=np.asarray(Image.open(path).convert('RGB'));hit=np.any(rgb<249,axis=2);mask=hit if mask is None else mask|hit
   yy,xx=np.nonzero(mask)
   if not len(xx):crop_receipts.append(dict(view=cam['view'],empty=True));continue
   box=(max(0,int(xx.min())-12),max(0,int(yy.min())-12),min(mask.shape[1],int(xx.max())+13),min(mask.shape[0],int(yy.max())+13));crop_receipts.append(dict(view=cam['view'],box=box,ink_pixels=int(mask.sum()),upsampled=False,small_evidence=int(mask.sum())<16))
   for arm in maps:
    for kind in ('ISOLATED','CONTEXT'):
     guard();source=out/f'{arm}_{cam["view"]}_{kind}.png';target_path=out/f'{arm}_{cam["view"]}_{kind}_CROP.png';im=Image.open(source).crop(box);atomic(target_path,lambda f,img=im:img.save(f,format='PNG'));outputs.append(str(target_path.relative_to(root)))
  js(out/'CROP_RECEIPT.json',dict(fixed_union_box_across_arms=True,native_full_images_retained=True,views=crop_receipts))
 # Frozen historical negatives use original complete carrier rows, including UNKNOWN.
 neg=dict(np.load(c['negative_carriers'],allow_pickle=False));ni={int(cid):j for j,cid in enumerate(neg['carrier_id'])}
 for pair in c['negative_pairs']:
  out=root/'diagnostics'/('negative_'+'_'.join(map(str,pair)))
  if any(int(cid) not in ni for cid in pair):js(out/'SCOPE.json',dict(missing_carrier_ids=[int(cid) for cid in pair if int(cid) not in ni],visual_evidence_missing=True));continue
  rr=np.unique(np.concatenate([neg['rows'][neg['row_offsets'][ni[int(cid)]]:neg['row_offsets'][ni[int(cid)]+1]] for cid in pair]));nz(out/'ROWS.npz',rows=rr);js(out/'SCOPE.json',dict(fixed_full_original_M4_pair=True,physical_context_complete=False,identical_rows=True))
  for arm,m in maps.items():
   for cam in cams:
    guard();a={k:asset[k][rr] for k in ('means','covariance','opacity')};a['colors']=colors(m['edge_id'][rr]);path=out/f'{arm}_{cam["view"]}_CONTEXT.png';save_image(path,render(a,cam,(1,1,1),.0144)['rgb']);outputs.append(str(path.relative_to(root)))
 return outputs
