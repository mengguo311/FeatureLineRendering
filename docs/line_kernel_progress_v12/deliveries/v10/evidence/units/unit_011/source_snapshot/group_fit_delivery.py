"""Separate fitted libraries, compact fit/score evidence; original-kernel native delivery."""
from scan65_relaxed_delivery import *
import scan65_relaxed_delivery as inherited
from runtime_io import *

def save_library(out,lib):
 out=Path(out)
 if 'fit_control_library' in lib:save_library(out/'ROW_FIT_CONTROL',lib['fit_control_library'])
 pack={};fitpack={};records=[]
 for i,r in enumerate(lib['records']):
  z={k:v for k,v in r.items() if k not in ['score_evidence','fit_evidence']}
  for field,dest,filename in [('score_evidence',pack,'SCORE_EVIDENCE.npz'),('fit_evidence',fitpack,'FIT_EVIDENCE.npz')]:
   if field not in r:continue
   z[field+'_file']=filename;z[field+'_arrays']={}
   for key,value in r[field].items():
    name=f'{i}_{key}';dest[name]=value;z[field+'_arrays'][key]=name
  records.append(z)
 nz(out/'SCORE_EVIDENCE.npz',**pack);nz(out/'FIT_EVIDENCE.npz',**fitpack)
 clean={k:v for k,v in lib.items() if k!='fit_control_library'}
 inherited.save_library(out,dict(clean,records=records));js(out/'SCORE_COMPARISON.json',serial(lib['score_comparison']))

def compare_library(current,path):
 path=Path(path);old=json.loads(path.read_text())
 assert current['complete'] and old['complete'],'CONTROL_REPLAY_INCOMPLETE'
 assert current['selected']==old['selected'],'CONTROL_REPLAY_SELECTION_MISMATCH'
 ignored={'branch_diagnostic','q','template','local_movable','q_array','template_array','local_movable_array','branch_witness_file','branch_witness_index','score_evidence','score_evidence_file','score_evidence_arrays','fit_evidence','fit_evidence_file','fit_evidence_arrays'}
 def normalize(lib):return dict(complete=lib['complete'],reason=lib['reason'],neighbors=serial(lib['neighbors']),selected=lib['selected'],records=[{k:serial(v) for k,v in r.items() if k not in ignored} for r in lib['records']])
 assert normalize(current)==normalize(old),'CONTROL_REPLAY_SCIENTIFIC_RECORD_MISMATCH '+str(path)
 pack=dict(np.load(path.parent/'GEOMETRY.npz',allow_pickle=False));count=0
 for rec,prev in zip(current['records'],old['records']):
  for key in ['q','template','local_movable']:
   if key+'_array' in prev:np.testing.assert_array_equal(rec[key],pack[prev[key+'_array']]);count+=1
 return dict(complete=True,source=str(path),source_sha256=sha(path),neighbors=len(old['neighbors']),records=len(old['records']),geometry_arrays=count,selected=old['selected'],comparison='exact previous scoring records and original fit q/template/masks; added array diagnostics excluded')

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
  first=next((e for e in events if e.get('score_comparison',{}).get('selected_geometry_changed')),None)
  if first is not None:selected.setdefault(first['sequence'],dict(event=first,rankings=[]))['rankings'].append(dict(metric='first_fit_divergence',rank=1))
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
