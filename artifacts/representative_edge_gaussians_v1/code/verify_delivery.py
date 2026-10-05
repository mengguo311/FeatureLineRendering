"""Final checks of stable ledger, counts, native controls and preserved old baseline."""
from io_utils import *
import json,numpy as np

def stage():
 verify_s0();verify(OUT/'F_SELECTION_SEAL');ledger=json.loads((ART/'SOURCE_MAP.json').read_text());bad=[]
 for path,v in ledger['files'].items():
  if sha(path)!=v['sha256']:bad.append(path)
 if bad:raise RuntimeError('HASH_MISMATCH '+str(bad))
 f=json.loads((ART/'FINAL.json').read_text());assert f['source_map_sha256']==sha(ART/'SOURCE_MAP.json') and f['report_sha256']==sha(ART/'REPORT_ZH.md');assert f['actual_pose_count']==98 and f['engineering_GO']
 oldbaselines={};counts={}
 for scene in CFG['scenes']:
  s=load(OUT/scene/'assets/scorebank.npz');old=load(SRC/'artifacts/gaussian_edge_attribution_v1/assets'/scene/'selection.npz');selection=json.loads((OUT/scene/'assets/selected_ids.json').read_text());
  for pct,b in zip([1,3,10],CFG['budgets'][scene]):
   key='baseline_union_'+str(pct).zfill(2);assert np.array_equal(s['A_ordered_ids'][:b],old[key])
  oldbaselines[scene]='all historical baseline_union 1/3/10 percent original IDs exactly preserved'
  count={p:0 for p in ['F','C','arc']}
  for spec in INPUTS['scenes'][scene]['frames']:
   d=OUT/scene/'evaluation'/spec['key'];verify(d);m=json.loads((d/'METRICS.json').read_text());count[m['phase']]+=1;assert m['camera_hash']==spec['camera_hash'] and m['raw_sha256']==spec['raw_sha256'];assert m['attributes_alpha_depth_exact'] and m['allones_alpha_max_abs']<=CFG['calibration']['attribute_alpha_atol']
  assert count==dict(F=8,C=8,arc=33);counts[scene]=count
  for key in ['video_native','video_telegram1600']:
   v=f['media'][scene][key];assert sha(v['path'])==v['sha256'];assert v['decoded_frame_count']==33 and all(v['checks'].values());assert v['content_audit']['distinct_RGB_content_without_labels']==33;assert len(set(v['camera_hashes']))==33
   assert v['dimensions']==([4000,1768] if key=='video_native' else [1600,708])
 assert len(list((ART/'figures').glob('*')))==12
 red=json.loads((ART/'logs/LEDGER_RED.json').read_text())
 atomic(ART/'logs/LEDGER_GREEN.json',dict(pass_status=True,checked_generated_files=len(ledger['files']),corrected_issue='self-written live LEDGER.log excluded, no scientific data or configuration changed',prior_mismatches=red['mismatches'],counts=counts,old_baseline_checks=oldbaselines))
 atomic(OUT/'DELIVERY_VERIFICATION.json',dict(utc=utc(),pass_status=True,checked_generated_files=len(ledger['files']),actual_counts=counts,old_baselines=oldbaselines,FINAL_sha256=sha(ART/'FINAL.json'),SOURCE_MAP_sha256=sha(ART/'SOURCE_MAP.json'),REPORT_sha256=sha(ART/'REPORT_ZH.md'),space=guard()))
 print(json.dumps(dict(pass_status=True,files_checked=len(ledger['files']),counts=counts,old_baselines=oldbaselines)))
if __name__=='__main__':stage()
