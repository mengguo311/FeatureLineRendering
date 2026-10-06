"""Independent saved-artifact audit; scalar ID maps, no production rerender."""
import importlib.util,json
import numpy as np
from pathlib import Path
from plyfile import PlyData
from runtime import *

def scalar_sample(pixelmaps,point):
 y,x=point;y0=int(np.floor(y));x0=int(np.floor(x));fy=y-y0;fx=x-x0;d={}
 for dy,dx,b in ((0,0,(1-fy)*(1-fx)),(0,1,(1-fy)*fx),(1,0,fy*(1-fx)),(1,1,fy*fx)):
  if b<=0:continue
  for i,w in pixelmaps[(y0+dy,x0+dx)].items():d[i]=d.get(i,0.)+b*w
 return d

def audit_rois(P):
 output={};newtests=0
 official=NATIVE/'vendor/gaussian-splatting/utils/sh_utils.py';spec=importlib.util.spec_from_file_location('official_cpu_sh',official);shmodule=importlib.util.module_from_spec(spec);spec.loader.exec_module(shmodule)
 for scene,record in P['scenes'].items():
  output[scene]={};ply=PlyData.read(record['model'])['vertex'];xyz=np.stack([ply[n] for n in ('x','y','z')],1);dc=np.stack([ply[f'f_dc_{i}'] for i in range(3)],1)[:,:,None];rest=np.stack([ply[f'f_rest_{i}'] for i in range(45)],1).reshape(len(ply),3,15);sh=np.concatenate([dc,rest],2)
  for key in P['roi_views']:
   d=np.load(ART/'downloads'/scene/f'{key}_ROI_full_CSR.npz');rec=json.loads((ART/'results'/f'{scene}_roi_{key}.json').read_text());pixels=d['query_pixels_yx'];offset=d['accepted_offsets'];ids=d['accepted_original_ids'];w=d['accepted_weights'];T=d['final_T'];colors=d['effective_SH3_colors'];maps={};
   for j,p in enumerate(pixels):maps[tuple(p)]={int(i):float(v) for i,v in zip(ids[offset[j]:offset[j+1]],w[offset[j]:offset[j+1]])}
   v=next(v for v in record['views'] if v['key']==key);a=np.load(v['source']);oldassign=np.load(OLD/f'artifacts/gaer_rgb_union_voting_v01/downloads/{scene}/{key}/assignment.npz');points=d['sample_points_yx'];rows=[];corr=[];rank_stats=[];allselected=np.unique(ids);c2w=np.linalg.inv(np.asarray(v['camera']['w2c']));direction=xyz[allselected]-c2w[:3,3].astype(np.float32);direction/=np.linalg.norm(direction,axis=1,keepdims=True);cpu_color=np.maximum(shmodule.eval_sh(3,sh[allselected],direction)+.5,0);sherr=float(np.abs(cpu_color-colors[allselected]).max());assert sherr<2e-5;newtests+=1
   for j,p in enumerate(points):
    center=scalar_sample(maps,p);minus=scalar_sample(maps,d['minus_yx'][j]);plus=scalar_sample(maps,d['plus_yx'][j]);dw={i:minus.get(i,0)-plus.get(i,0) for i in set(minus)|set(plus)};Ds={i:abs(dw.get(i,0)) for i in center if center[i]>0};cid=min(center,key=lambda i:(-center[i],i)) if center else -1;did=min(Ds,key=lambda i:(-Ds[i],i)) if Ds else -1;reason=0 if did>=0 and Ds[did]>2e-6 else 2
    if not d['normal_ok'][j]:reason=1
    if cid<0:reason=5
    winner=did if reason==0 else cid;assert winner==d['Kfull_winner'][j] and reason==d['Kfull_reason'][j];newtests+=2
    terms=np.array([(colors[i].astype(np.float64)-1)*value for i,value in dw.items()]);signed=terms.sum(0) if len(terms) else np.zeros(3);normsum=float(np.linalg.norm(terms,axis=1).sum()) if len(terms) else 0;valid=normsum>3e-5;cancellation=float(1-np.linalg.norm(signed)/normsum) if valid else None
    if valid:assert -1e-10<=cancellation<=1+1e-10;newtests+=1
    corrected_rgb=np.zeros(3)
    for i,delta in dw.items():corrected_rgb+=colors[i]*delta
    corrected_rgb+=float(d['background_delta_T'][j]);assert np.abs(corrected_rgb-d['delta_RGB'][j]).max()<3e-5;newtests+=1
    marked=bool(a['line_binary'][tuple(p)]);oldreason=int(oldassign['fallback_map'][tuple(p)]);oldwinner=int(oldassign['winner_map'][tuple(p)]);rows.append(dict(sample=j,point_yx=p.tolist(),marked=marked,old_fallback_reason=oldreason,old_winner=oldwinner,full_reason=reason,full_winner=winner,old_fallback_becomes_valid_full=marked and oldreason not in (0,255) and reason==0,color_abs_normalizer=normsum,color_cancellation_valid=valid,color_cancellation=cancellation))
    if marked:assert oldreason==int(d['K8_reason'][j]) and oldwinner==int(d['K8_winner'][j]);newtests+=2
    corr.append(cancellation if valid else np.nan)
   for ri,r in enumerate(record['rois'][key]):
    sl=slice(ri*25,(ri+1)*25);cs=[q for q in rows[sl] if q['color_cancellation_valid']];rank_stats.append(dict(roi=ri,category=r['category'],fragment=r['fragment'],corrected_cancellation_mean=float(np.mean([q['color_cancellation'] for q in cs])) if cs else None,valid_cancellation_samples=len(cs),insufficient_numeric_signal_samples=25-len(cs)))
   counts=dict(total_samples=len(rows),marked_samples=sum(q['marked'] for q in rows),old_fallback_to_valid_full=sum(q['old_fallback_becomes_valid_full'] for q in rows),marked_K8_winner_changes=sum(q['marked'] and int(d['K8_winner'][q['sample']])!=q['full_winner'] for q in rows),all_K8_winner_changes=int((d['K8_winner']!=d['Kfull_winner']).sum()),all_K32_winner_changes=int((d['K32_winner']!=d['Kfull_winner']).sum()))
   output[scene][key]=dict(counts=counts,official_CPU_SH3_native_color_max_abs=sherr,SH_direction='normalize(original means3D - native camera center)',SH_clamp='max(eval_sh(3)+.5,0) each channel; no upper clamp; native colors used for actual decomposition',ROI=rank_stats,samples=rows)
   npz(ART/'downloads'/scene/f'{key}_ROI_audit_normalizers.npz',color_cancellation=np.array(corr),valid_signal=np.isfinite(corr),old_reason=np.array([q['old_fallback_reason'] for q in rows],np.uint8),marked=np.array([q['marked'] for q in rows]))
 atomic_json(ART/'tests/ROI_INDEPENDENT_AUDIT.json',dict(passed=True,checks=newtests,corrects='first-run near-zero cancellation presentation only; old sealed results retained',scenes=output));return output,newtests

def main():
 guard('artifact_audit',gpu=False);P=json.loads((ART/'PROTOCOL.json').read_text());results={};checks=0
 for scene in P['scenes']:
  a=np.load(ART/'downloads'/scene/'fullN_linear_oracles.npz');sets=np.load(ART/'downloads'/scene/'oracle_original_ID_sets.npz');assert a['per_view_fullT_line_b'].shape==(10,P['scenes'][scene]['count']);assert a['per_view_fullT_line_b'].min()>=0;checks+=2
  for B in P['budgets']:
   for name,b in (('source8_oracle',a['source8_b']),('diagnostic2_pooled_oracle',a['diagnostic2_b'])):
    independently=np.lexsort((np.arange(len(b)),-b))[:B];assert np.array_equal(independently,sets[f'{name}_{B}']);checks+=1
  p=ART/'results'/f'{scene}_capacity.json'
  if p.exists():
   c=json.loads(p.read_text());fits=[]
   for f in c['fits']:
    cert=f['independent_FP64_certificate'];assert cert['dual_lower_bound']<=cert['primal_feasible_objective']+1e-10;assert cert['bounds_min']>=0 and cert['bounds_max']<=1;assert max(cert['native_vs_FP64_accepted_weight_A_max_abs'])<3e-6;checks+=3;fits.append(dict(view=f.get('view','shared'),certificate=cert))
   strengths=np.load(ART/'downloads'/scene/'shared_strengths.npz')['strength'];assert strengths.shape==(P['scenes'][scene]['count'],) and np.isfinite(strengths).all();checks+=1;results[scene]=fits
 seals={}
 for p in (ART/'seals').glob('*.json'):
  d=json.loads(p.read_text())
  for q,h in d['files'].items():assert sha(ROOT/q)==h;checks+=1
  seals[p.name]=d['status']
 roi,ct=audit_rois(P);checks+=ct;before=json.loads((ART/'PROTECTED_BEFORE.json').read_text())['files'];changed=[p for p,h in before.items() if sha(p)!=h];atomic_json(ART/'tests/PROTECTED_AFTER.json',dict(passed=not changed,checked_files=len(before),changed=changed));assert not changed;checks+=len(before)
 atomic_json(ART/'tests/INDEPENDENT_ARTIFACT_AUDIT.json',dict(passed=True,checks=checks,seals=seals,capacity_certificates=results,protocol_sha256=sha(ART/'PROTOCOL.json'),old_files_preserved=len(before),scope='parent saved-artifact inspection, scalar original-ID decomposition, CPU official SH3 calibration, all-N oracle ranking, strengths bounds/certificates and unit SHA seals; no old test campaign'))
 print('INDEPENDENT_AUDIT_PASS',checks)
if __name__=='__main__':main()
