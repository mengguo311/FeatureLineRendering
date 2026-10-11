"""Publish only measured scan65 negative geometry; no scene or method retries."""
import csv,datetime,json,shutil,sys
from pathlib import Path
W=Path(__file__).resolve().parents[5];H=Path('/mnt/hdd1/u00134/radegs_paper_reproduction_v01');S=H/'full_reproduction_v01/suite_execution_v01';O=S/'scan65_result_v01';A=W/'artifacts/radegs_paper_reproduction_v01/full_reproduction_v01';P=A/'suite_execution_v01/scan65_result_v01'
sys.path.insert(0,str(W/'reproduction/radegs_paper_v01/stage2'));from safety import atomic_json,sha256
v=json.loads((O/'VERIFICATION.json').read_text());d=json.loads((O/'diagnosis/diagnosis.json').read_text());support=json.loads((O/'diagnosis/marching_cubes_support.json').read_text());camera=json.loads((O/'diagnosis/camera_and_scale_audit.json').read_text());native=json.loads((S/'scan65_v01/state/tsdf_attempts/1791538333636037671/result.json').read_text())
assert support['empty_surface_confirmed'] and native['vertices']==native['triangles']==0 and support['voxels_weight_gt_3']==0
assert v['immutable_inputs_verified']==2701 and all(x['nonfinite_fields']=={'opacity':732} for x in v['parameters'])
raw={r['view']:r for r in d['views']};records=native['view_records'];assert len(records)==49 and set(raw)=={r['view'] for r in records}
for r in records:
 assert r['valid_pixels']==raw[r['view']]['masked_finite_positive_lt8']
 assert r['integrated']==(r['valid_pixels']>0)
 assert not any(raw[r['view']]['nonfinite_by_channel'].values())
modes={k:[r['view'] for r in records if r['mode']==k] for k in sorted({r['mode'] for r in records})}
assert {k:len(x) for k,x in modes.items()}=={'C24_NATIVE_STRIDE4':25,'EMPTY_VALID_DEPTH_NO_CONTRIBUTION':16,'SPARSE_VALID_DEPTH_STRIDE1_FALLBACK':8}
for f in (O/'diagnosis').iterdir():shutil.copy2(f,P/f.name)
shutil.copy2(O/'VERIFICATION.json',P/'VERIFICATION.json');atomic_json(P/'VIEW_CONTRIBUTION_POLICY_AUDIT.json',{'view_modes':modes,'every_view_record_matches_raw_npz_audit':True,'empty_views_only_when_zero_original_threshold_valid_depth':True,'empty_view_rule_frozen_before_this_scene':str(W/'reproduction/radegs_paper_v01/full_reproduction_v01/tsdf_touch.py'),'rule_sha256':sha256(W/'reproduction/radegs_paper_v01/full_reproduction_v01/tsdf_touch.py'),'valid_views_discarded':0,'threshold_changes':False})
protocol=json.loads((A/'FULL_SUITE_PROTOCOL.json').read_text());entry=next(e for e in protocol['entries'] if e['id']=='DTU_scan65_half30k_TSDF');paper=entry['metric']['paper_value']
status={'scene':'scan65','status':'NEGATIVE_GEOMETRY_EMPTY_SURFACE_CONFIRMED','utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'train_verified':True,'export_verified':True,'gaussians':v['last_iteration']['points'],'views':49,'masked_valid_pixels':d['summary']['total_original_threshold_valid_pixels'],'mask_coverage':d['summary']['overall_GT_coverage_at_original_threshold'],'view_mode_counts':{k:len(x) for k,x in modes.items()},'marching_cubes_support':{k:x for k,x in support.items() if k not in ['all_full_cubes','supported_crossings']},'official_eval_executed':False,'official_CD_mm':None,'paper_CD_mm':paper,'reason':'no voxel has weight>3 after all valid contributions; zero original-threshold TSDF surface; official CD undefined','boundary_checkpoint_15000_verified':True,'direct_failure_cause_confirmed':True,'historical_optimization_unique_cause_proven':False,'scientificdone':False,'full_suite_completed':False}
atomic_json(P/'STATUS.json',status);atomic_json(O/'STATUS.json',status)
p0,p1=v['parameters'];window={tuple(x['iterations']):x for x in d['training_windows']};a=window[(14001,15000)]['mean']['photo'];b=window[(29001,30000)]['mean']['photo']
report=f'''scan65 half30k：空视角与空表面的真实负结果（2026-10-09）

2701个封存输入和smoke/train/export seals已重核验；30000条唯一迭代、15k/15k schedule、wd100/wn5均逐项核对。最终{v['last_iteration']['points']}个Gaussians，49个raw导出全finite。完整15k checkpoint独立seal有效。

本场景49view中25个采用native stride4融合，8个有稀疏有效像素但stride4采不到，按预先封存桥接以stride1分配后积分；16个在原alpha≥.5与RGBA mask≥.5、0<depth<8下完全无有效深度。每个空view均显式记录EMPTY_VALID_DEPTH_NO_CONTRIBUTION，与raw npz逐view计数一致，没有静默删帧或丢弃有效view。[逐view贡献规则核验](VIEW_CONTRIBUTION_POLICY_AUDIT.json)。

空view不贡献TSDF是因为没有满足原规则的测量，不是按GT几何或质量挑帧；C24原API对零block会抛异常，已在scan24阶段记录的工程桥接显式保留零贡献。稀疏桥接只改变候选block分配采样，未改depth值、camera、积分公式或alpha/voxel阈值。不能把16个空view掩盖为成功重建。

| 项目 | 实测 |
|---|---:|
| 原阈值有效深度像素总量 | {status['masked_valid_pixels']} |
| 有效深度 / 原RGBA mask | {status['mask_coverage']*100:.8f}% |
| 实际积分view / 显式零贡献view | 33 / 16 |
| weight>3体素 / 八角支持cube / 符号跨越 | 0 / 0 / 0 |
| mesh顶点 / 三角形 | 0 / 0 |
| 官方DTU CD | null，空mesh不可评价，未执行official eval |
| 论文Table1 scan65 half30k | {paper} mm |

保存volume没有任何体素满足Open3D原mesh权重门槛，空表面的直接原因已证明。没有降低weight3、alpha.5、mask.5、voxel.002或depthmax8，没有改depth_scale1。该负结果不是PLY存在就称科学复现成功。参考[论文v2第7页Table1](https://arxiv.org/pdf/2406.01467v2#page=7)仅作事后对照。

[相机审计](camera_and_scale_audit.json)显示world-to-camera与COLMAP至1e-6一致、777×581与焦距正确。评价标定{camera['evaluation_only_mm_per_scene_unit']:.9f}mm/scene-unit，体素为{camera['evaluation_equivalent_voxel_mm']:.9f}mm，相机中心对齐均误差{camera['camera_center_alignment_residual_mm']['mean']:.10f}mm。没有depth_scale单位错误证据。

| 优化观察 | 15k | 30k |
|---|---:|---:|
| 有效opacity中位数 | {p0['effective_opacity_quantiles'][3]:.9f} | {p1['effective_opacity_quantiles'][3]:.9f} |
| 有效opacity低于1/255 | {p0['effective_below_1_over_255_fraction']*100:.6f}% | {p1['effective_below_1_over_255_fraction']*100:.6f}% |
| photo末1000轮均值 | {a:.9f} | {b:.9f} |
| 非有限opacity logits | 732 | 732 |

其他PLY字段和激活后的opacity有限。float32 reset边界机制有此前CPU证据，但732个非有限logit不证明68.31%有效opacity下降的唯一原因。几何阶段退化与此前场景相近，唯一优化历史因果仍未证明；本轮没有据此改loss或重训。保持用户明确的Eq23 camera-z双重sum且detach alphaT权重、Eq24未归一化alphaT法线、median、Mip3Dfilter、GOFdensification、DTUappearance。

![固定五个训练视角的真实RGB alpha depth normal](scan65_rgb_alpha_depth_normal.png)

![实际训练曲线与全部视角覆盖率](scan65_training_and_coverage.png)

![原阈值体素支持为空：不是mesh](scan65_mesh_support.png)

固定0000/0012/0024/0036/0048训练视角，不是held-out指标。raw未修改，RGB仅显示clip。空支持图没有伪造表面。[原失败manifest](ORIGINAL_FAILURE_MANIFEST.json)、[训练与checkpoint验证](VERIFICATION.json)、[全部raw计数](diagnosis.json)。旧runner_state保留ENGINEERING_NOT_READY，无TSDF/eval成功seal。

规则来源：[C24 mesh固定源码](https://github.com/HKUST-SAIL/RaDe-GS/blob/2d4bc087f1b4bd62c96054fbe89d273490526b81/mesh_extract.py#L20-L107)、[Open3D固定提取条件](https://github.com/isl-org/Open3D/blob/0f06a149c4fb9406fd3e432a5cb0c024f38e2f0e/cpp/open3d/t/geometry/kernel/VoxelBlockGridImpl.h#L1385-L1403)。下一实验独立保留配置与真实GPU gate，完整suite继续，不能从此负结果替未跑场景填数。
''';(P/'SCAN65_RESULT_REPORT_ZH.md').write_text(report);(O/'SCAN65_RESULT_REPORT_ZH.md').write_text(report)
review={'confirmed_negative_result':str(P/'STATUS.json'),'result_sha256':sha256(P/'STATUS.json'),'decision':'CONTINUE_SAME_FROZEN_METHOD_TO_NEXT_EXPLICIT_SCENE','direct_TSDF_failure_explained':True,'previous_scene':'scan65','historical_optimization_unique_cause_proven':False,'new_renderer_or_method_patch':False,'reason':'all original-threshold valid contributions checked; no supported voxels/surface; retain null and continue independent frozen paper entries without parameter changes','scientificdone':False};atomic_json(P/'NEGATIVE_RESULT_REVIEW.json',review)
e=A/'experiments'/entry['id']/'STATUS.json';r=json.loads(e.read_text());r.update(status=status['status'],train_verified=True,export_verified=True,metric_value=None,delta=None,reason=status['reason'],diagnostic_review_completed=True,execution_chain_completed=False,result_report=str(P/'SCAN65_RESULT_REPORT_ZH.md'),utc=status['utc']);atomic_json(e,r)
m=json.loads((A/'MASTER_STATUS.json').read_text());m.update(status='SCAN65_NEGATIVE_RESULT_REVIEWED',last_event='scan65 all49 views audited,16 empty contributions and no weight>3 voxels; official metric null; immutable inputs and train/export/15k checkpoint verified',next_action='Seal independent scan69 configuration after frozen review; same method, mandatory real GPU0 smoke before train',utc=status['utc']);m['experiment_counts'].update(verified_train=7,verified_export=7,negative_terminal_attempts=6,empty_surface_attempts=4);m['blocked'].append({'stage':'scan65_official_eval','reason':'null metric: no original-threshold TSDF surface'});atomic_json(A/'MASTER_STATUS.json',m)
metrics=json.loads((A/'METRICS.json').read_text())
for row in metrics['rows']:
 if row['id']==entry['id']:row.update(status=status['status'],train_verified=True,export_verified=True,metric_value=None,delta=None,reason=status['reason'])
atomic_json(A/'METRICS.json',metrics)
with (A/'METRICS.csv').open('w',newline='') as f:
 fields=list(dict.fromkeys(k for row in metrics['rows'] for k in row));writer=csv.DictWriter(f,fieldnames=fields,lineterminator='\n');writer.writeheader();writer.writerows(metrics['rows'])
atomic_json(P/'EVIDENCE_MANIFEST.json',{'files':{str(p):sha256(p) for p in P.iterdir() if p.is_file()},'code':{str(p):sha256(p) for p in Path(__file__).parent.glob('*.py')},'scientificdone':False});print(json.dumps(status,indent=2))
