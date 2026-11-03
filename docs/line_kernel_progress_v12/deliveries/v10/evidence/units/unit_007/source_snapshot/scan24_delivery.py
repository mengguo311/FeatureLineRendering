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
 neg=dict(np.load(c['negative_carriers'],allow_pickle=False));index={int(cid):i for i,cid in enumerate(neg['carrier_id'])}
 for pair in c['negative_pairs']:
  name='negative_'+'_'.join(map(str,pair));missing=[i for i in pair if i not in index]
  if missing:js(root/'diagnostics'/name/'SCOPE.json',dict(missing_carrier_ids=missing,visual_evidence_missing=True));continue
  rr=np.unique(np.concatenate([neg['rows'][neg['row_offsets'][index[i]]:neg['row_offsets'][index[i]+1]] for i in pair]));items.append((name,rr,rr,rr))
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
