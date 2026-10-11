"""Freeze verified actual negative outcome; no fake evaluation seal or metric."""
import collections,csv,datetime,json,shutil,sys
from pathlib import Path
P=Path(__file__).resolve().parent;W=P.parents[4];H=Path('/mnt/hdd1/u00134/radegs_paper_reproduction_v01');S=H/'full_reproduction_v01/suite_execution_v01';O=S/'scan63_result_v01';A=W/'artifacts/radegs_paper_reproduction_v01/full_reproduction_v01';R=A/'suite_execution_v01/scan63_result_v01'
sys.path.insert(0,str(W/'reproduction/radegs_paper_v01/stage2'));from safety import atomic_json,sha256,verify_seal
state=O/'gpu_cull/state';c=json.loads((state/'runner_config.json').read_text());rs=json.loads((state/'runner_state.json').read_text())
for p,d in c['immutable_files'].items():assert sha256(p)==d,p
assert verify_seal(state/'smoke.seal.json','smoke',c['inputs'])
assert rs['child_pid'] is None and rs['returncode']==0 and rs['status'] in ['STAGE_SEALED','CULL_DIAGNOSTIC_COMPLETE']
report=json.loads((state/'smoke.report.json').read_text());gpu=json.loads(Path(report['details']['result']).read_text());assert gpu['CPU_GPU_sampled_masks_identical'] and gpu['classification']['kept_faces']==0
v=json.loads((O/'VERIFICATION.json').read_text());d=json.loads((O/'diagnosis/diagnosis.json').read_text());mc=json.loads((O/'diagnosis/marching_cubes_support.json').read_text());cam=json.loads((O/'diagnosis/camera_and_scale_audit.json').read_text())
progress=json.loads((S/'scan63_v01/state/tsdf_attempts/1791534394279816132/progress.json').read_text());counts=dict(collections.Counter(x['mode'] for x in progress['views']));views={x['view']:x for x in d['views']}
for x in progress['views']:
 y=views[x['view']];assert x['valid_pixels']==y['masked_finite_positive_lt8'];assert (x['mode']=='EMPTY_VALID_DEPTH_NO_CONTRIBUTION')==(x['valid_pixels']==0)
proto=json.loads((A/'FULL_SUITE_PROTOCOL.json').read_text());entry=next(e for e in proto['entries'] if e['id']=='DTU_scan63_half30k_TSDF');paper=entry['metric']['paper_value'];assert paper==.79
utc=datetime.datetime.now(datetime.timezone.utc).isoformat()
result={'status':'NEGATIVE_GEOMETRY_EMPTY_AFTER_AUTHOR_MASK_CONFIRMED','scene':'scan63','verified_stages':['smoke','train','export','tsdf'],'GPU_original_cull_verified':True,'train_verified':True,'export_verified':True,'gaussians':v['last_iteration']['points'],'views':49,'unique_iteration_records':v['unique_iteration_records'],'boundary_checkpoint_15000_verified':v['boundary_checkpoint_verified'],'raw_mesh_vertices':gpu['raw_vertices'],'raw_mesh_faces':gpu['raw_faces'],'author_mask_kept_vertices':0,'author_mask_kept_faces':0,'official_outer_eval_attempted':True,'official_inner_metric_executed':False,'official_metric':None,'official_CD_mm':None,'paper_CD_mm':paper,'direct_failure_cause_confirmed':True,'historical_optimization_unique_cause_proven':False,'masked_valid_pixels':d['summary']['total_original_threshold_valid_pixels'],'mask_coverage':d['summary']['overall_GT_coverage_at_original_threshold'],'view_mode_counts':counts,'marching_cubes_support':{k:x for k,x in mc.items() if not isinstance(x,list)},'reason':'raw TSDF29v22f exists; unchanged C24 all-view mask removes all; Trimesh empty-vertex early return leaves invalid faces and causes IndexError; no valid official evaluation input','scientificdone':False,'full_suite_completed':False,'utc':utc}
assert not (R/'STATUS.json').exists();atomic_json(R/'STATUS.json',result);atomic_json(O/'STATUS.json',result)
review={'decision':'CONTINUE_SAME_FROZEN_METHOD_TO_NEXT_EXPLICIT_SCENE','direct_failure_explained':True,'failure_stage':'eval','previous_scene':'scan63','confirmed_negative_result':str(R/'STATUS.json'),'result_sha256':sha256(R/'STATUS.json'),'historical_optimization_unique_cause_proven':False,'new_renderer_or_method_patch':False,'reason':'direct original cull failure reproduced CPU/GPU; actual negative geometry retained as null; same frozen independent paper entries continue','scientificdone':False};atomic_json(R/'NEGATIVE_RESULT_REVIEW.json',review);atomic_json(O/'NEGATIVE_RESULT_REVIEW.json',review)
for name in ['VERIFICATION.json']:shutil.copy2(O/name,R/name)
for name in ['diagnosis.json','views.csv','camera_and_scale_audit.json','marching_cubes_support.json','cull_cpu_reproduction.json','cull_margin_and_visuals.json','scan63_rgb_alpha_depth_normal.png','scan63_training_and_coverage.png','scan63_mesh_support.png','scan63_mesh_mask_projections.png','scan63_actual_raw_mesh_three_views.png']:shutil.copy2(O/'diagnosis'/name,R/name)
shutil.copy2(Path(report['details']['result']),R/'CULL_GPU_RESULT.json');shutil.copy2(state/'smoke.seal.json',R/'CULL_GPU_DIAGNOSTIC.seal.json')
atomic_json(R/'GPU_DIAGNOSTIC_VERIFICATION.json',{'config':str(state/'runner_config.json'),'config_sha256':sha256(state/'runner_config.json'),'immutable_inputs_verified':len(c['immutable_files']),'diagnostic_seal_verified':True,'GPU':c['allowed_gpu_uuids'][0],'attempt':rs['attempt'],'original_eval_success':False,'original_production_failure_state_unchanged':True,'scientificdone':False})
atomic_json(R/'VIEW_CONTRIBUTION_POLICY_AUDIT.json',{'all49_views_audited':True,'counts':counts,'empty_views':d['summary']['empty_full_resolution_valid_views'],'each_progress_count_matches_raw':True,'thresholds_unchanged':d['protocol_unchanged'],'scientificdone':False})
# Current result state, not a modification of the original failed runner or seals.
sp=A/'experiments'/entry['id']/'STATUS.json';status=json.loads(sp.read_text());status.update(result,metric_value=None,metric_unit='mm',paper_value=paper,reason=result['reason'],result_report=str(R/'SCAN63_RESULT_REPORT_ZH.md'));atomic_json(sp,status)
metrics=json.loads((A/'METRICS.json').read_text())
for row in metrics['rows']:
 if row['id']==entry['id']:row.update(status=result['status'],train_verified=True,export_verified=True,metric_value=None,delta=None,reason=result['reason'])
metrics.update(utc=utc,all_complete=False);atomic_json(A/'METRICS.json',metrics)
with (A/'METRICS.csv').open('w') as out:
 fields=list(dict.fromkeys(k for row in metrics['rows'] for k in row));writer=csv.DictWriter(out,fieldnames=fields);writer.writeheader();writer.writerows(metrics['rows'])
m=json.loads((A/'MASTER_STATUS.json').read_text());m.update(status='SCAN63_NEGATIVE_AUTHOR_CULL_CONFIRMED',phase='DTU_SCAN65_PREPARATION',last_event='scan63 original author cull CPU/GPU agree all29 vertices removed; null metric, no evaluator-success claim',next_action='seal next scan65 config using explicit eval-stage negative-result review; mandatory GPU0 smoke before training',verified_stages=result['verified_stages'],utc=utc)
m['experiment_counts'].update(verified_train=6,verified_export=6,negative_terminal_attempts=5,empty_after_author_mask_attempts=1)
m['blocked'].append({'stage':'scan63_official_eval','reason':'original author mask removes all raw TSDF geometry; inner official metric undefined'})
ids={e['id'] for e in proto['entries']};statusfiles=list((A/'experiments').glob('*/STATUS.json'));assert ids=={p.parent.name for p in statusfiles}=={r['id'] for r in metrics['rows']};m['experiment_counts'].update(experiment_status_files_actual=len(statusfiles),metrics_rows_written=len(metrics['rows']),status_file_ids_exact_match=True);atomic_json(A/'MASTER_STATUS.json',m)
print(json.dumps(result,indent=2))
