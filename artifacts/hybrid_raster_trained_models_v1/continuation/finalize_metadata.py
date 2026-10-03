"""Finalize small metadata only after independent196-frame/24-video PASS."""
import copy,datetime,hashlib,json,os,shutil
from pathlib import Path
CONT=Path(__file__).resolve().parent;ART=CONT.parent;ROOT=ART.parents[1]
EXTERNAL=Path('/mnt/hdd1/u00134/hybrid_raster_trained_models_v1')
def read(p):return json.loads(Path(p).read_text())
def rec(p):
 p=Path(p);return {'path':str(p.resolve()),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
def write(p,v):
 p=Path(p);q=p.with_suffix('.final.partial');q.write_text(json.dumps(v,indent=2,ensure_ascii=False,sort_keys=True)+'\n');os.replace(q,p)
p=CONT/'independent_review/PRODUCTION.json';v=read(p)
assert v['passed'] and (v['verified_frames'],v['verified_videos'],v['verified_contacts'],v['verified_first_mid_last'])==(196,24,60,36)
access=read(CONT/'independent_review/FULL_VERIFIER_ACCESS.json')
assert access['passed'] and access['completed'] and access['normal_exit'] and access['exit_code']==0
assert access['production_report']['sha256']==rec(p)['sha256']
old=read(CONT/'historical_607b908/FINAL.json');final=copy.deepcopy(old)
now=datetime.datetime.now(datetime.timezone.utc);ledger=read(EXTERNAL/'SUPERVISOR_RUNTIME.json');clock=read(EXTERNAL/'CONTINUATION_CLOCK.json')
final.update(schema='trained-vanilla-frozen-npr-storage-continuation-final-v2',status='ARTIFACTS_COMPLETE_HISTORICAL_AUDIT_GAP_RETAINED',production_complete=True,independent_artifact_integrity=True,execution_audit_complete=False,scientific_GO=False,human_review='PENDING',created_utc=now.isoformat(),historical_final=rec(CONT/'historical_607b908/FINAL.json'))
final.pop('experiment_complete',None)
final['scope']='Complete planned artifact production and posthoc integrity only; historical Hotdog execution audit remains incomplete; training/scientific success never upgraded by images.'
final['historical_storage_blocker']=final.pop('storage_blocker')
final['counts'].update(actual_frames=196,new_frames=147,missing_frames=0,contacts=60,first_mid_last_panels=36,five_column_line_overlay_matched_panels=588,frame_seals=196,raw_seals=196,media_seals=4,response_panels=196,videos=24,new_videos=18)
final['historical_budgets']=final['budgets'];final['budgets']={'continuation_gpu_phase_seconds':sum(x.get('elapsed_seconds',0) for x in ledger if x['phase']=='render'),'continuation_all_launch_seconds':sum(x.get('elapsed_seconds',0) for x in ledger),'gpu_limit_seconds':14400,'wall_limit_seconds':28800,'wall_seconds_to_record':now.timestamp()-clock['started_epoch'],'clock':rec(EXTERNAL/'CONTINUATION_CLOCK.json'),'runtime':rec(EXTERNAL/'SUPERVISOR_RUNTIME.json'),'engineering':rec(CONT/'REPAIR_LOG.json')}
final['commits']['storage_code_freeze']=read(CONT/'STORAGE_FREEZE.json')['commit'];final['commits']['encoder_binding_freeze']=read(CONT/'ENCODER_BINDING_RELEASE.json')['binding_commit']
final['independent_verification']['historical_production']=final['independent_verification']['production'];final['independent_verification'].update(production=rec(p),overall_exit_code=0,overall_exit_reason='196frames24videos60contacts36representatives verified across both roots; historical execution gap retained')
final['independent_verification']['historical_conclusion']=final['independent_verification'].pop('conclusion')
final['independent_verification']['continuation_checker_access']=rec(CONT/'independent_review/FULL_VERIFIER_ACCESS.json')
final['paths'].update(authorized_external_root=str(EXTERNAL),scene_transport_roots=v['scene_roots'],storage_mapping=rec(CONT/'STORAGE_MAP.json'),artifact_path_sha_manifest=rec(CONT/'ARTIFACT_PATH_SHA256.json'))
final['paths'].pop('large_local_output_root',None)
final['tests']={'unit_tests_passed':124,'real_media_integration_cases_passed':1,'index':rec(CONT/'TEST_INDEX.json'),'historical_tests_unchanged':old['tests'],'counting':'124 selected unique unit tests +1 real media integration separately; RED/failed/repeat runs excluded; historical92 not added'}
for scene,row in final['scenes'].items():
 row.update(actual_NPR_frames=49,NPR_calibration='PASS: all8 patched/unpatchedF independently recomputed',NPR_payload_media_integrity='PASS',scientific_qualification='REQUIRES_HUMAN_REVIEW; no visual upgrade to training/scientific success',transport_root=v['scene_roots'][scene],NPR_frames_manifest=rec(ART/'transport'/scene/'FRAMES.json'),NPR_media_manifest=rec(ART/'transport'/scene/'MEDIA.json'))
for name in ('calibration','payload_manifest','media_manifest','video_full_decode'):
 if name in final['NPR']:final['NPR']['historical_hotdog_only_'+name]=final['NPR'].pop(name)
final['NPR']['per_scene']={s:{'root':v['scene_roots'][s],'frames':49,'calibration':v['scenes'][s]['calibration'],'video_full_decode':v['scenes'][s]['media']['videos']} for s in v['scene_roots']}
final['NPR']['diagnostic_summary']=rec(CONT/'DIAGNOSTIC_SUMMARY.json');final['NPR']['storage_source_delta']=rec(CONT/'SOURCE_DELTA.json')
final['NPR']['continuation_visual_limitations']={'reviewer':'model; human scientific GO pending','ship':'Frozen arc middle severely crops the ship/display below the image; arc016 native RGB confirms this. No camera rescue. B/C have dense water/hull texture; matched ink does not remove its spatial pattern.','mic':'Arc middle/late crops stand/cable and sometimes microphone head; B/C dense interior/grille texture persists under ink matching.','materials':'B/C granular gray fill can obscure sphere/base details; A also fragments on reflective spheres; crop and common RGB irregularities retained.','claims_not_established':['More ink means better lines','Fixed 3D line identity','Temporal stability or improvement','Blind C generalization','Human GO']}
final['access_audit']['new_successful_phases']={s+'_'+ph:rec(CONT/'independent_review'/f'{s.upper()}_{ph.upper()}_ACCESS.json') for s in ('materials','mic','ship') for ph in ('render','media')}
final['access_audit']['failed_materials_media_attempt']=rec(CONT/'independent_review/MATERIALS_MEDIA_ATTEMPT001_ACCESS.json');final['access_audit']['historical_gap_recheck']=rec(CONT/'HISTORICAL_GAP_RECHECK.json')
final['visual_reviews'] += [rec(CONT/(s.upper()+'_MODEL_REVIEW.json')) for s in ('materials','mic','ship')]
final['publication']={'delivery':rec(CONT/'DELIVERY.json'),'scope':'Only explicitly listed tracked small review assets uploaded; huge raw/native artifacts remain at indexed roots','remote_readback':rec(CONT/'GITHUB_READBACK.json')}
final['remaining']=['Human scientific review/GO pending across five columns, matched controls, overlays and raw fields','Historical firstHotdog143 execution trace gap and firstchecker143 invalid evidence remain unresolved; new traces do not repair them']
write(ART/'FINAL.json',final)
status={'phase':'ARTIFACTS_COMPLETE_HISTORICAL_AUDIT_GAP_RETAINED','utc':now.isoformat(),'actual_frames':196,'expected_frames':196,'new_frames':147,'missing_frames':0,'complete_scenes':list(v['scene_roots']),'verified_videos':24,'expected_videos':24,'verified_contacts':60,'expected_contacts':60,'verified_first_mid_last':36,'expected_first_mid_last':36,'independent_production':rec(p),'scene_roots':v['scene_roots'],'initial_render_access':'INCOMPLETE_INVALID','first_checker_access':'INCOMPLETE_INVALID','scientific_GO':False,'human_review':'PENDING'}
write(ART/'transport/STATUS.json',status)
s=read(ART/'STATUS.json');s.update(phase=status['phase'],transport=status,actual_npr_frames=196,missing_npr_frames=0,unrun_NPR_scenes=[],active_NPR_scene=None,independent_verification='PASS_ARTIFACT_INTEGRITY; HISTORICAL_EXECUTION_GAP_RETAINED',updated_utc=now.isoformat(),producer_complete_frame_counts={x:49 for x in v['scene_roots']},count_scope='Independent actual full196/24 validation',storage_free_bytes=shutil.disk_usage(ROOT).free)
s['storage'].update(repo_free_bytes=shutil.disk_usage(ROOT).free,external_free_bytes=shutil.disk_usage(EXTERNAL).free,observed_utc=now.isoformat());write(ART/'STATUS.json',s)
print(json.dumps({'status':final['status'],'counts':final['counts'],'budgets':final['budgets']}))
