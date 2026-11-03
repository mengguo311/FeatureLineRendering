"""Saved original-kernel views and honest support/partition diagnostics."""
from free_io import *
from free_core import arc,union,project,EPS
from scipy.spatial import cKDTree
from seed_coverage import context_rows
import merge_core as merge
import free_core as core

def compare(old,new):
 assigned_old=old>=0;assigned_new=new>=0;gained=int(np.sum(~assigned_old&assigned_new));lost=int(np.sum(assigned_old&~assigned_new));splits=[]
 order=np.argsort(old,kind='stable');vals,starts,counts=np.unique(old[order],return_index=True,return_counts=True)
 for gid,start,count in zip(vals,starts,counts):
  if gid<0:continue
  rr=order[start:start+count];children,num=np.unique(new[rr],return_counts=True);active=children>=0
  if active.sum()>1 or np.any(children<0):splits.append(dict(old_id=int(gid),rows=int(count),unknown=int(num[children<0].sum()),new_groups=int(active.sum()),children=children.tolist(),counts=num.tolist()))
 return dict(old_assigned=int(assigned_old.sum()),new_assigned=int(assigned_new.sum()),assigned_gained=gained,assigned_lost=lost,new_UNKNOWN=int((~assigned_new).sum()),old_groups_split=int(sum(z['new_groups']>1 for z in splits)),revoked_or_split_groups=splits,numeric_id_changes_not_identity_accuracy=int(np.sum(old!=new)))

def groups(d,m,a,old,guard):
 result=[]
 for mid,q in sorted(m.items()):
  guard();rr=np.flatnonzero(a['edge_id']==mid)
  if not len(rr):continue
  ss=a['s'][rr];L=arc(q)[-1];it=np.c_[np.maximum(0,ss-d['half'][rr]),np.minimum(L,ss+d['half'][rr])];iv,support,longest,totalgap,maxgap=union(it);v=np.diff(q,axis=0);t=v/np.linalg.norm(v,axis=1)[:,None];angles=np.degrees(np.arccos(np.clip(np.sum(t[:-1]*t[1:],axis=1),-1,1)))
  z=dict(edge_id=int(mid),kernels=len(rr),knots=len(q),finite_length_p=float(L),bbox_world=[d['asset']['means'][rr].min(0).tolist(),d['asset']['means'][rr].max(0).tolist()],support_intervals_proxy_p=iv,support_union_proxy_p=support,longest_run_proxy_p=longest,total_gap_proxy_p=totalgap,max_gap_proxy_p=maxgap,cumulative_turn_deg=float(angles.sum()),curved_selection_proxy=bool(angles.sum()>30),physical_identity_verified=False,auxiliary_geometry_rendered=False)
  for name,labels in [('parents',d['asset']['primitive_id']),('M4_fragments',old)]:
   contrib=[]
   for gid in np.unique(labels[rr]):
    take=labels[rr]==gid;su=union(it[take])[1];contrib.append(dict(id=int(gid),kernels=int(take.sum()),support_proxy_p=su,substantial=bool(gid>=0 and take.sum()>=12 and su>=4-EPS)))
   z[name]=sorted(contrib,key=lambda r:(-r['support_proxy_p'],r['id']));z['substantial_'+name]=sum(r['substantial'] for r in contrib)
  result.append(z)
 return result


def enrich(c,d,models,a,gg,binding,guard):
 root=Path(c['unit_root']);history=json.loads((root/'MERGE_HISTORY.json').read_text())['accepted'];events={child:e for e in history for child in e['surviving_children']}
 for g in gg:
  guard();mid=g['edge_id'];g['new_model_merge']=mid in events;g['outward_largest_input_domain_proxy_p']=0.
  if mid not in events:continue
  e=events[mid];mm,aa,_=cold_stage(root/'scenes'/c['scene']/'stages'/e['input_stage'],binding);rr=np.flatnonzero(a['edge_id']==mid);q=models[mid];L=arc(q)[-1];ss=project(d['x'][rr],q)[1];ints=np.c_[np.maximum(0,ss-d['half'][rr]),np.minimum(L,ss+d['half'][rr])];iv=union(ints)[0];parts=[]
  for parent in e['inputs']:
   mask=aa['edge_id'][rr]==parent;su=union(ints[mask])[1];domain=project(mm[parent],q)[1];lo=float(domain.min());hi=float(domain.max());outward=sum(max(0,min(b,lo)-a)+max(0,b-max(a,hi)) for a,b in iv);parts.append(dict(model=parent,retained_kernels=int(mask.sum()),support_proxy_p=su,finite_domain_on_child=[lo,hi],outward_proxy_p=outward))
  largest=min(parts,key=lambda z:(-z['support_proxy_p'],z['model']));g.update(merge_inputs=parts,largest_input_model=largest['model'],outward_largest_input_domain_proxy_p=largest['outward_proxy_p'],support_gain_over_largest_input_proxy_p=g['support_union_proxy_p']-largest['support_proxy_p'],trial=e['trial'],support_is_projection_not_observation=True)

def deliver(c,d,stages,binding,guard):
 render=renderer(c);cams=[x for x in json.loads(Path(c['cameras']).read_text())[c['scene']] if x['view'] in c['views']];assert {x['view'] for x in cams}==set(c['views'])
 refs={}
 for name,path in c['reference_memberships'].items():
  guard();z=np.load(path,allow_pickle=False);assert np.array_equal(z['line_kernel_id'],np.arange(c['kernel_count']));refs[name]=z['edge_id'].copy();z.close()
 final=stages[-1];selected=[stages[0]]+([final] if final!=stages[0] else []);allarms={};grouplists={};old=refs['v05_M4'];root=Path(c['unit_root']);fig=root/'figures';fig.mkdir(exist_ok=True)
 # Full views take priority over any statistics or group render.
 for name in selected:
  guard();out=root/'scenes'/c['scene']/'stages'/name;m,a,_=cold_stage(out,binding);allarms[name]=a['edge_id'];cols=colors(a['edge_id']);nz(out/'DISPLAY_COLORS.npz',colors=cols);js(out/'DISPLAY_SOURCE.json',dict(gaussians=c['gaussians'],sha256=c['input_files'][c['gaussians']],colors='DISPLAY_COLORS.npz',cameras=c['cameras'],camera_sha256=c['input_files'][c['cameras']],floor=.0144,background=[1,1,1],original_rows='ALL',auxiliary_geometry_rendered=False))
  asset={k:d['asset'][k] for k in ('means','covariance','opacity')};asset['colors']=cols
  for cam in cams:guard();image(out/(cam['view']+'_FULL.png'),render(asset,cam,(1,1,1),.0144)['rgb'])
  js(out/'FULL_VIEWS.json',dict(images=[cam['view']+'_FULL.png' for cam in cams],complete=True))
 for name in selected:
  out=root/'scenes'/c['scene']/'stages'/name;m,a,_=cold_stage(out,binding);gg=groups(d,m,a,old,guard);enrich(c,d,m,a,gg,binding,guard);grouplists[name]=gg;js(out/'GROUPS.json',dict(groups=gg,support_is_covariance_projection_proxy=True,physical_truth=False));js(out/'COMPARISONS.json',{r:compare(ids,a['edge_id']) for r,ids in refs.items()})
 if len(selected)==2:js(root/'NO_MERGE_COMPARISON.json',compare(allarms[selected[0]],allarms[final]))
 # Actual changed-member cases; inherited shape alone is not a new result.
 cases=[];finalids=allarms[final];static=allarms[selected[0]];gg=grouplists[final];seen=set()
 for curved in (True,False):
  eligible=[]
  for g in gg:
   rr=np.flatnonzero(finalids==g['edge_id']);oldids=np.unique(static[rr]);same=len(oldids)==1 and oldids[0]>=0 and np.array_equal(np.flatnonzero(static==oldids[0]),rr)
   if not same and g['curved_selection_proxy']==curved:eligible.append(g)
  for g in sorted(eligible,key=lambda z:(-z.get('outward_largest_input_domain_proxy_p',0),-z['support_union_proxy_p'],z['edge_id']))[:3]:
   rr=np.flatnonzero(finalids==g['edge_id']);cases.append((('CURVED' if curved else 'STRAIGHT')+'_'+str(g['edge_id']),rr));seen.add(g['edge_id'])
 damage=compare(static,finalids)['revoked_or_split_groups'];damage=sorted(damage,key=lambda z:(-z['unknown'],-z['new_groups'],-z['rows'],z['old_id']))[:3]
 for z in damage:cases.append(('DAMAGED_'+str(z['old_id']),np.flatnonzero(static==z['old_id'])))
 for i,pair in enumerate(c['fixed_contexts']):cases.append(('FIXED_'+str(i)+'_'+'_'.join(map(str,pair)),context_rows(d['seed_carriers'],pair)))
 for name,path in c.get('prior_case_rows',{}).items():
  with np.load(path,allow_pickle=False) as z:rr=z['identical_member_rows'].copy()
  assert np.all((rr>=0)&(rr<len(d['x'])))
  cases.append(('PRIOR_'+name,rr))
 js(fig/'CASE_SELECTION.json',dict(cases=[dict(name=n,rows=len(r)) for n,r in cases],curved_label_is_turn_proxy_not_visual_success=True,missing_new_curve=not any(n.startswith('CURVED') for n,r in cases),missing_substantial_straight=not any(n.startswith('STRAIGHT') for n,r in cases),selection_requires_actual_member_change=True,physical_growth_requires_three_substantial_fragments=True,negative_contexts_include_UNKNOWN_source_rows=True,fixed_context_sources=[dict(ids=pair,found=[int(z) for z in pair if z in set(d['seed_carriers']['carrier_id'].tolist())],missing=[int(z) for z in pair if z not in set(d['seed_carriers']['carrier_id'].tolist())],rows=len(context_rows(d['seed_carriers'],pair))) for pair in c['fixed_contexts']]))
 tree=cKDTree(d['x']);displayarms={**refs,**allarms};camreports=[]
 for name,rr in cases:
  guard()
  if not len(rr):camreports.append(dict(case=name,status='EMPTY_REFERENCE_ROWS'));continue
  # Complete spatial1p assignment competitors plus complete associated identities.
  parts=tree.query_ball_point(d['x'][rr],2,workers=1);ctx=np.unique(np.r_[rr,np.concatenate(parts) if len(parts) else []]).astype(int)
  for labels in displayarms.values():
   touched=np.unique(labels[rr]);touched=touched[touched>=0];ctx=np.union1d(ctx,np.flatnonzero(np.isin(labels,touched)))
  # Include complete primary supports of EVERY finite competing model, not just top-two alternatives.
  competitors={}
  for arm in selected:
   mm,aa,_=cold_stage(root/'scenes'/c['scene']/'stages'/arm,binding);touched=[]
   for mid,q in mm.items():
    guard()
    if np.any(np.isfinite(merge.row_cost(d['x'][rr],d['t'][rr],q))):touched.append(mid)
   competitors[arm]=touched;ctx=np.union1d(ctx,np.flatnonzero(np.isin(aa['edge_id'],touched)))
  out=fig/name;out.mkdir(exist_ok=True);nz(out/'ROWS.npz',identical_member_rows=rr,complete_context_rows=ctx);js(out/'CONTEXT.json',dict(competing_models=competitors,scope='All finite current models compatible with target rows; their full primary support plus2p original-kernel neighborhood and full touched reference identities',physical_alternatives_complete=False))
  # Isolated same-row images for every reference; whole context highlight per new arm.
  for cam in cams:
   images=[];paths=[]
   for arm,labels in displayarms.items():
    guard();cols=colors(labels[rr]);asset={k:d['asset'][k][rr] for k in ('means','covariance','opacity')};asset['colors']=cols;rgb=render(asset,cam,(1,1,1),.0144)['rgb'];path=out/(arm+'_'+cam['view']+'_GROUP.png');image(path,rgb);images.append(np.uint8(np.rint(np.clip(rgb,0,1)*255)));paths.append(path)
   mask=np.any(np.stack(images)<254,axis=(0,3));yx=np.argwhere(mask)
   if len(yx):
    y0,x0=np.maximum(yx.min(0)-16,0);y1,x1=np.minimum(yx.max(0)+17,[cam['height'],cam['width']]);bbox=[int(x0),int(y0),int(x1),int(y1)]
    for path,rgb in zip(paths,images):
     crop=Image.fromarray(rgb[y0:y1,x0:x1]).resize(((x1-x0)*4,(y1-y0)*4),Image.Resampling.NEAREST);atomic(path.with_name(path.stem+'_CROP4.png'),lambda f,im=crop:im.save(f,format='PNG'))
   else:bbox=None
   camreports.append(dict(case=name,view=cam['view'],bbox=bbox,empty=bbox is None,rows=len(rr),context_rows=len(ctx)))
   for arm in selected:
    guard();cols=colors(allarms[arm][ctx]);asset={k:d['asset'][k][ctx] for k in ('means','covariance','opacity')};asset['colors']=cols;image(out/(arm+'_'+cam['view']+'_CONTEXT.png'),render(asset,cam,(1,1,1),.0144)['rgb'])
    # All original kernels retained, target rows highlighted, every other row gray.
    cols=np.full((len(d['x']),3),.68);cols[rr]=colors(allarms[arm][rr]);asset={k:d['asset'][k] for k in ('means','covariance','opacity')};asset['colors']=cols;image(out/(arm+'_'+cam['view']+'_WHOLE_HIGHLIGHT.png'),render(asset,cam,(1,1,1),.0144)['rgb'])
 js(fig/'VISIBILITY.json',camreports)
 assert fingerprints(d['asset'])==d['fingerprint']
 return dict(full_view_stages=selected,group_cases=len(cases),diagnostics_complete=True)
