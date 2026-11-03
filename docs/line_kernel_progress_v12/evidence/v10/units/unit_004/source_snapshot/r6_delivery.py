from runtime_io import *
import gzip
import whole_delivery as old
from whole_delivery import serial,native_full
from scan24_delivery import diagnostics
from whole_delivery import statistics

def save_library(out,lib):
 out=Path(out)
 js(out/'SHADOW_CHOICES.json',serial(dict(choices=lib.get('shadow_choices',{}),records=lib.get('shadow_records',{}),fit_calls=lib.get('fit_calls'),evaluate_calls=lib.get('evaluate_calls'))))
 witnesses={str(i):serial(z.get('branch_diagnostic',{'status':'NOT_REACHED'})) for i,z in enumerate(lib['records'])}
 atomic(out/'BRANCH_WITNESSES.json.gz',lambda f:f.write(gzip.compress(json.dumps(witnesses,ensure_ascii=False,allow_nan=False,separators=(',',':')).encode(),mtime=0)))
 records=[dict({k:v for k,v in z.items() if k!='branch_diagnostic'},branch_witness_file='BRANCH_WITNESSES.json.gz',branch_witness_index=i) for i,z in enumerate(lib['records'])]
 old.save_library(out,dict(lib,records=records))

def scientific(lib):
 records=[{k:serial(v) for k,v in z.items() if k not in ['branch_diagnostic','q','template','local_movable','q_array','template_array','local_movable_array','branch_witness_file','branch_witness_index']} for z in lib['records']]
 return dict(complete=lib['complete'],reason=lib['reason'],neighbors=serial(lib['neighbors']),selected=lib['selected'],records=records)

def save_stage(out,c,d,objects,events,next_version,binding,changed=None):
 out=Path(out);m=({k:v.copy() for k,v in d['initial_membership'].items()} if not events else old.mapping(d,objects));nz(out/'MEMBERSHIP.npz',**m)
 # Full changed/active model bank relative to immutable original checkpoint.
 selected={gid:o for gid,o in objects.items() if o['seed_origins']};ids=sorted(selected);qs=[selected[i]['q'] for i in ids];rr=[selected[i]['rows'] for i in ids]
 nz(out/'MODELS.npz',group_id=np.asarray(ids,np.int64),version=np.asarray([selected[i]['version'] for i in ids]),knots_p=np.concatenate(qs) if qs else np.empty((0,3)),knot_offsets=np.r_[0,np.cumsum([len(q) for q in qs])],rows=np.concatenate(rr) if rr else np.empty(0,int),row_offsets=np.r_[0,np.cumsum([len(r) for r in rr])])
 groups=[dict(id=gid,version=o['version'],rows=o['rows'].tolist(),leaves=o['leaves'],seed_origins=o['seed_origins'],metrics=o.get('metrics'),geometry_available=o['available']) for gid,o in selected.items()]
 js(out/'GROUPS.json',dict(groups=groups,unchanged_background=c['initial_stage'],no_original_kernel_geometry_copy=True));js(out/'LINEAGE.json',dict(historical=d['historical_events'],events=events,next_version=next_version,changed=changed,checkpoint_replay='immutable initial state plus ordered whole-member donor deltas',original_kernel_ink_only=True))
 checkpoint(out,['MEMBERSHIP.npz','MODELS.npz','GROUPS.json','LINEAGE.json'],binding,'COMPLETE_MONOTONE_GROUP_UNION');verify_checkpoint(out,binding)
 cold=dict(np.load(out/'MEMBERSHIP.npz',allow_pickle=False))
 for key in m:np.testing.assert_array_equal(cold[key],m[key])
 return m

def worst_events(scene,c,d,states,contexts,render,cams,guard):
 from scan24_delivery import union_box,crop_full_context
 result=[];asset=d['asset']
 for policy in c['arms']:
  lin=json.loads((scene/'stages'/f'{policy}_FINAL/LINEAGE.json').read_text());events=lin['events'];selected={}
  for metric in ['max_distance_p','kernels']:
   ordered=sorted(events,key=lambda e:(-e['metrics'][metric],e['sequence']))[:3]
   for rank,e in enumerate(ordered,1):selected.setdefault(e['sequence'],dict(event=e,rankings=[]))['rankings'].append(dict(metric=metric,rank=rank))
  for flag in ['pure_pooling','gap_exceeded','self_contact']:
   first=next((e for e in events if e['metrics'].get('rule6',{}).get(flag)),None)
   if first is not None:selected.setdefault(first['sequence'],dict(event=first,rankings=[]))['rankings'].append(dict(metric='first_'+flag,rank=1))
  for seq,item in sorted(selected.items()):
   guard();e=item['event'];stage=scene/'stages'/f'{policy}_{seq:04d}';m=dict(np.load(stage/'MEMBERSHIP.npz',allow_pickle=False));rr=np.flatnonzero(m['edge_id']==e['group']);added=np.asarray(e['added_rows'],int)
   out=scene/'worst_events'/policy/f'{seq:04d}';js(out/'EVENT.json',item);nz(out/'ROWS.npz',members=rr,added=added)
   images=native_full(stage,c,d,m,render,cams,guard) if not (stage/(c['views'][0]+'_FULL.png')).exists() else []
   base=colors(m['edge_id'])
   for cam in cams:
    view=cam['view'];isolated=[]
    for kind,rows in [('ISOLATED',rr),('ADDED',added)]:
     guard();a={k:asset[k][rows] for k in ('means','covariance','opacity')};a['colors']=base[rows];path=out/f'{view}_{kind}.png';save_image(path,render(a,cam,(1,1,1),.0144)['rgb']);isolated.append(Image.open(path).convert('RGB'))
    box,ink=union_box(isolated,16)
    for im in isolated:im.close()
    js(out/f'{view}_VIEW.json',dict(box=box,ink_pixels=ink,small_evidence=ink<16,source_surface_occlusion=False))
    if box:
     crop_full_context(stage/f'{view}_FULL.png',out/f'{view}_FULL_OBJECT_CONTEXT.png',box)
     crop_full_context(out/f'{view}_ISOLATED.png',out/f'{view}_ISOLATED_CROP.png',box)
     crop_full_context(out/f'{view}_ADDED.png',out/f'{view}_ADDED_CROP.png',box)
   result.append(dict(policy=policy,sequence=seq,path=str(out.relative_to(scene)),rankings=item['rankings']))
 js(scene/'WORST_EVENT_SELECTION.json',dict(method='top3 maximum member error and top3 group size plus first pure_pooling/gap_exceeded/self_contact per arm; deterministic sequence ties',events=result,identity_error_is_not_certified_by_metric=True))
 return result
