"""Compact per-row score evidence; unchanged native original-kernel scan65 delivery."""
from scan65_relaxed_delivery import *
import scan65_relaxed_delivery as inherited
from runtime_io import *

def save_library(out,lib):
 out=Path(out);pack={};records=[]
 for i,r in enumerate(lib['records']):
  z={k:v for k,v in r.items() if k!='score_evidence'}
  if 'score_evidence' in r:
   z['score_evidence_file']='SCORE_EVIDENCE.npz';z['score_evidence_arrays']={}
   for key,value in r['score_evidence'].items():
    name=f'{i}_{key}';pack[name]=value;z['score_evidence_arrays'][key]=name
  records.append(z)
 nz(out/'SCORE_EVIDENCE.npz',**pack)
 inherited.save_library(out,dict(lib,records=records))
 js(out/'SCORE_COMPARISON.json',serial(lib['score_comparison']))

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
  first=next((e for e in events if e.get('score_comparison',{}).get('changed_choice')),None)
  if first is not None:selected.setdefault(first['sequence'],dict(event=first,rankings=[]))['rankings'].append(dict(metric='first_ranking_divergence',rank=1))
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
 js(scene/'WORST_EVENT_SELECTION.json',dict(method='top3 maximum member error and top3 group size plus first ranking divergence and pure_pooling/gap_exceeded/self_contact per arm; deterministic sequence ties',events=result,identity_error_is_not_certified_by_metric=True))
 return result
