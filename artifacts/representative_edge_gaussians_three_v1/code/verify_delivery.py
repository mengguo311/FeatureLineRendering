"""Verify immutable S0, new A historical rule, all147 poses and actual full media."""
from io_utils import *
def stage():
 verify_s0();verify(OUT/'F_SELECTION_SEAL');verify(OUT/'BUDGET_SEAL');ledger=json.loads((ART/'SOURCE_MAP.json').read_text())
 for p,v in ledger['files'].items():assert sha(p)==v['sha256'],p
 f=json.loads((ART/'FINAL.json').read_text());assert f['actual_pose_count']==147 and f['engineering_GO'];assert f['source_map_sha256']==sha(ART/'SOURCE_MAP.json') and f['report_sha256']==sha(ART/'REPORT_ZH.md')
 counts={}
 for scene in CFG['scenes']:
  new=load(OUT/scene/'assets/scorebank.npz');old=load(OUT/scene/'baseline_A/assets/selection.npz')
  for pct,b in zip((1,3,10),CFG['budgets'][scene]):assert np.array_equal(new['A_ordered_ids'][:b],old['baseline_union_'+str(pct).zfill(2)])
  count=dict(F=0,C=0,arc=0)
  for spec in INPUTS['scenes'][scene]['frames']:
   d=OUT/scene/'evaluation'/spec['key'];verify(d);m=json.loads((d/'METRICS.json').read_text());count[m['phase']]+=1;assert m['camera_hash']==spec['camera_hash'] and m['camera_json_sha256']==spec['camera_json_sha256'] and m['raw_sha256']==spec['raw_sha256'];assert m['attributes_alpha_depth_exact'] and m['allones_alpha_max_abs']<=CFG['calibration']['attribute_alpha_atol']
  assert count==dict(F=8,C=8,arc=33);counts[scene]=count
  for key in ('video_native','video_telegram1600'):
   v=f['media'][scene][key];assert sha(v['path'])==v['sha256'];assert v['decoded_frame_count']==33 and all(v['checks'].values());assert v['content_audit']['distinct_RGB_content_without_labels']==33 and len(set(v['camera_hashes']))==33;assert v['dimensions']==([4000,1768] if key=='video_native' else [1600,708])
 assert len(list((ART/'figures').glob('*')))==18
 atomic(OUT/'DELIVERY_VERIFICATION.json',dict(utc=utc(),pass_status=True,checked_generated_files=len(ledger['files']),actual_counts=counts,A_baselines='same historical algorithm newly computed; all frozen tier prefixes exact',FINAL_sha256=sha(ART/'FINAL.json'),SOURCE_MAP_sha256=sha(ART/'SOURCE_MAP.json'),REPORT_sha256=sha(ART/'REPORT_ZH.md'),space=guard()));event('DELIVERY_VERIFIED',counts=counts,all147=True)
if __name__=='__main__':stage()
