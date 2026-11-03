"""Original-kernel views; full-object cropped context is separate from query context."""
from whole_delivery import *

def union_box(images,pad=16):
 mask=None
 for im in images:
  hit=np.any(np.asarray(im.convert('RGB'))<249,axis=2);mask=hit if mask is None else mask|hit
 yy,xx=np.nonzero(mask)
 if not len(xx):return None,0
 return (max(0,int(xx.min())-pad),max(0,int(yy.min())-pad),min(mask.shape[1],int(xx.max())+pad+1),min(mask.shape[0],int(yy.max())+pad+1)),int(mask.sum())

def crop_full_context(full_path,out,box):
 # Crop the actual FULL object raster, never a query-selected or depth-filtered subset.
 with Image.open(full_path) as im:cropped=im.crop(box)
 atomic(out,lambda f:cropped.save(f,format='PNG'))

def stage_path(root,arm,c):
 if arm=='START':return root/'stages/START'
 if arm.endswith('_MID'):
  policy=arm[:-4];lineage=json.loads((root/'stages'/f'{policy}_FINAL/LINEAGE.json').read_text());n=(len(lineage['events'])+1)//2
  return root/'stages'/f'{policy}_{n:04d}'
 return root/'stages'/f'{arm}_FINAL'

def diagnostics(root,c,d,maps,states,contexts,render,cams,guard):
 root=Path(root);asset=d['asset'];outputs=[];n=len(d['initial_membership']['edge_id']);allrows=np.arange(n)
 items=[]
 for sid in c['seed_ids']:
  if sid not in d['objects']:
   js(root/'diagnostics'/str(sid)/'SCOPE.json',dict(visual_evidence_missing=True,reason='frozen_seed_not_ready'));continue
  start=set(map(int,d['objects'][sid]['rows']));target=set(start);query=set(start)
  for objects in states.values():
   for o in objects.values():
    if sid in o['seed_origins']:target.update(map(int,o['rows']))
  for gid in contexts.get(sid,set()):
   if gid in d['objects']:query.update(map(int,d['objects'][gid]['rows']))
  query.update(target);items.append((str(sid),np.array(sorted(target),int),np.array(sorted(query),int),np.array(sorted(start),int)))
 items.extend(reference_items(c,n))
 for name,target,query,start in items:
  out=root/'diagnostics'/name;nz(out/'ROWS.npz',target=target,query=query,start=start)
  js(out/'SCOPE.json',dict(all_queried_competitors=True,full_projected_context=True,full_context_source='complete original-kernel FULL raster',context_includes_all_depths_and_nonqueried_rows=True,source_surface_occlusion=False,target_rows=len(target),query_rows=len(query),original_rows=n,identical_target_rows_across_arms=True,added_rows_not_inherited=True))
  receipts=[]
  for cam in cams:
   view=cam['view'];isolated=[]
   for arm,m in maps.items():
    base=colors(m['edge_id']);highlight=np.full_like(base,.82);highlight[target]=base[target]
    labels=np.unique(m['edge_id'][start]);current=target[np.isin(m['edge_id'][target],labels[labels>=0])];added=np.setdiff1d(current,start)
    nz(out/f'{arm}_{view}_ROWS.npz',start=start,added=added,identical_target=target,query=query)
    kinds=[('ISOLATED',target,base[target]),('QUERY_CONTEXT',query,base[query]),('HIGHLIGHT',allrows,highlight),('START_MEMBERS',start,base[start]),('ADDED_MEMBERS',added,base[added])]
    for kind,rr,co in kinds:
     guard();path=out/f'{arm}_{view}_{kind}.png'
     if len(rr):
      a={k:asset[k][rr] for k in ('means','covariance','opacity')};a['colors']=co;rgb=render(a,cam,(1,1,1),.0144)['rgb']
     else:rgb=np.ones((cam['height'],cam['width'],3))
     save_image(path,rgb);outputs.append(str(path.relative_to(root)))
     if kind=='ISOLATED':isolated.append(Image.open(path).convert('RGB'))
   box,ink=union_box(isolated,16)
   for im in isolated:im.close()
   receipts.append(dict(view=view,box=box,ink_pixels=ink,empty=box is None,small_evidence=ink<16,upsampled=False,padding_pixels=16))
   if box is None:continue
   for arm in maps:
    guard();full=stage_path(root,arm,c)/(view+'_FULL.png');dest=out/f'{arm}_{view}_FULL_OBJECT_CONTEXT_CROP.png';crop_full_context(full,dest,box);outputs.append(str(dest.relative_to(root)))
    for kind in ['ISOLATED','QUERY_CONTEXT','HIGHLIGHT','START_MEMBERS','ADDED_MEMBERS']:
     source=out/f'{arm}_{view}_{kind}.png';dest=out/f'{arm}_{view}_{kind}_CROP.png';crop_full_context(source,dest,box);outputs.append(str(dest.relative_to(root)))
   js(out/f'{view}_CONTEXT_SOURCE.json',dict(all_original_rows=n,all_depths=True,box=box,full_rasters={arm:str((stage_path(root,arm,c)/(view+'_FULL.png')).relative_to(root)) for arm in maps}))
  js(out/'CROP_RECEIPT.json',dict(fixed_union_box_across_arms_and_stages=True,views=receipts,native_full_images_retained=True,physical_identity_unverified=True))
 return outputs

def reference_items(c,n):
 items=[]
 for rec in c['negative_contexts']:
  z=dict(np.load(rec['rows_path'],allow_pickle=False));rr=np.unique(z['rows']).astype(np.int64)
  assert len(rr) and rr.min()>=0 and rr.max()<n,'NEGATIVE_ROW_BINDING'
  items.append(('negative_'+rec['category'],rr,rr,rr))
 neg=dict(np.load(c['damage_carriers'],allow_pickle=False));index={int(cid):i for i,cid in enumerate(neg['carrier_id'])}
 for cid in c['damage_reference_ids']:
  assert cid in index,('MISSING_DAMAGE_REFERENCE',cid)
  i=index[cid];rr=np.unique(neg['rows'][neg['row_offsets'][i]:neg['row_offsets'][i+1]])
  assert len(rr) and rr.min()>=0 and rr.max()<n,'DAMAGE_ROW_BINDING'
  items.append(('damage_'+str(cid),rr,rr,rr))
 return items

def statistics(out,c,d,objects,m,guard):
 out=Path(out);report={};refs=dict(c['external_memberships'],START=str(Path(c['initial_stage'])/'MEMBERSHIP.npz'),M4=c['membership'])
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
 js(out/'METRICS.json',dict(assigned=int(np.sum(m['edge_id']>=0)),unknown=int(np.sum(m['edge_id']<0)),references=report,groups=rows,unavailable_references=c['unavailable_references'],full_mapping_is_not_full_scene_search=True,support_union_is_not_continuous_observation=True));return rows
