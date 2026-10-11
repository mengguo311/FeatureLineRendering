"""Publish actual CPU-audited scan40 negative result and suite counts."""
import csv,datetime,json,shutil,sys
from pathlib import Path
W=Path(__file__).resolve().parents[5];H=Path('/mnt/hdd1/u00134/radegs_paper_reproduction_v01');S=H/'full_reproduction_v01/suite_execution_v01';O=S/'scan40_result_v01';A=W/'artifacts/radegs_paper_reproduction_v01/full_reproduction_v01';P=A/'suite_execution_v01/scan40_result_v01'
sys.path.insert(0,str(W/'reproduction/radegs_paper_v01/stage2'));from safety import atomic_json,sha256
v=json.loads((O/'VERIFICATION.json').read_text());d=json.loads((O/'diagnosis/diagnosis.json').read_text());support=json.loads((O/'diagnosis/marching_cubes_support.json').read_text());camera=json.loads((O/'diagnosis/camera_and_scale_audit.json').read_text());native=json.loads((S/'scan40_v01/state/tsdf_attempts/1791527424817437409/result.json').read_text())
assert support['empty_surface_confirmed'] and native['vertices']==native['triangles']==0
assert all(r['integrated'] and r['mode']=='C24_NATIVE_STRIDE4' for r in native['view_records'])
assert all(not any(r['nonfinite_by_channel'].values()) for r in d['views'])
for f in (O/'diagnosis').iterdir():shutil.copy2(f,P/f.name)
shutil.copy2(O/'VERIFICATION.json',P/'VERIFICATION.json')
status={'scene':'scan40','status':'NEGATIVE_GEOMETRY_EMPTY_SURFACE_CONFIRMED','utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'train_verified':True,'export_verified':True,'gaussians':v['last_iteration']['points'],'views':49,'masked_valid_pixels':d['summary']['total_original_threshold_valid_pixels'],'mask_coverage':d['summary']['overall_GT_coverage_at_original_threshold'],'native_stride4_all_views_integrated':True,'sparse_allocation_fallback_used':False,'marching_cubes_support':{k:x for k,x in support.items() if k not in ['all_full_cubes','supported_crossings']},'official_eval_executed':False,'official_CD_mm':None,'paper_CD_mm':.33,'reason':'native original-threshold TSDF has zero fully supported cubes and zero surface; no finite mesh for official evaluation','boundary_checkpoint_15000_verified':True,'direct_failure_cause_confirmed':True,'historical_optimization_unique_cause_proven':False,'scientificdone':False,'full_suite_completed':False}
atomic_json(P/'STATUS.json',status);atomic_json(O/'STATUS.json',status)
p0,p1=v['parameters'];window={tuple(x['iterations']):x for x in d['training_windows']};a=window[(14001,15000)]['mean']['photo'];b=window[(29001,30000)]['mean']['photo']
report=f'''scan40 half30k：原阈值空表面负结果（2026-10-09）

1914个封存输入、smoke/train/export seals和15000步完整checkpoint重新通过hash核验。训练有30000条唯一迭代，15k/15k调度与wd100/wn5逐条核验；最终{v['last_iteration']['points']}个Gaussians、49份finite raw导出。

TSDF的49视图均原native stride4分配并积分；无空view、无稀疏fallback。保存的volume只有121个体素weight>3，**没有任何立方体八角都满足原提取条件，支持符号跨越为0**。原阈值表面为空；Open3D空表面错误被明确记录，runner按失败gate停止。不是depth_scale错误的证据，也没有降低alpha、mask、voxel或weight阈值，没有删帧。

| 检查 | 实测 |
|---|---:|
| raw数组非有限元素 | 0 |
| 原阈值有效深度像素 | 18392 |
| 有效深度 / 原RGBA mask | {status['mask_coverage']*100:.7f}% |
| TSDF顶点 / 三角形 | 0 / 0 |
| 官方CD | null，空mesh无法评价，未执行official eval |
| 论文Table1 scan40 half30k CD | .33 mm |

[逐view原始量](diagnosis.json)、[CSV](views.csv)、[体素支持](marching_cubes_support.json)、[训练及hash核验](VERIFICATION.json)。.33是[论文v2第7页Table1](https://arxiv.org/pdf/2406.01467v2#page=7)half30k对应值，仅用于事后对照，不用于训练或选参数。

相机world-to-camera与COLMAP一致至1e-6以内；分辨率777×581、焦距恰为原图一半。官方评价标定为{camera['evaluation_only_mm_per_scene_unit']:.10f} mm/scene-unit，.002体素为{camera['evaluation_equivalent_voxel_mm']:.10f}mm，相机中心对齐均误差{camera['camera_center_alignment_residual_mm']['mean']:.10f}mm。camera-z在重建scene单位，depth_scale1与C24一致。[相机审计](camera_and_scale_audit.json)。

| 训练观察 | 15k | 30k |
|---|---:|---:|
| Mip3D有效opacity中位数 | {p0['effective_opacity_quantiles'][3]:.9f} | {p1['effective_opacity_quantiles'][3]:.9f} |
| 有效opacity低于1/255 | {p0['effective_below_1_over_255_fraction']*100:.6f}% | {p1['effective_below_1_over_255_fraction']*100:.6f}% |
| photo末1000轮均值 | {a:.9f} | {b:.9f} |
| 非有限opacity logits | 155 | 155 |

其他PLY字段有限，激活后的opacity与导出数组有限。原C24 reset的float32逆sigmoid边界机制有先前独立CPU证据；155个异常logit不等于解释了68.37%的有效opacity下降。与scan24/37同样出现几何阶段退化，但唯一优化历史原因未证明。完整15k checkpoint已保留以便因果诊断。本次未修改renderer、loss、native或重训。

![固定五个训练视角的真实RGB、alpha、depth、normal](scan40_rgb_alpha_depth_normal.png)

![训练曲线与全部视图覆盖率](scan40_training_and_coverage.png)

![真实体素支持的三个方向；不是mesh](scan40_mesh_support.png)

图使用预定0000/0012/0024/0036/0048，不能称为held-out评价。RGB仅显示clip；raw npz不变。最后一图明确是volume支持，不补造不存在的mesh。TSDF depth_scale1、depthmax8、voxel.002、alpha和mask≥.5、weight严格>3均不变：[C24固定提交mesh代码](https://github.com/HKUST-SAIL/RaDe-GS/blob/2d4bc087f1b4bd62c96054fbe89d273490526b81/mesh_extract.py#L20-L107)，[Open3D固定提交权重前提](https://github.com/isl-org/Open3D/blob/0f06a149c4fb9406fd3e432a5cb0c024f38e2f0e/cpp/open3d/t/geometry/kernel/VoxelBlockGridImpl.h#L1385-L1403)。

[原失败完整manifest](ORIGINAL_FAILURE_MANIFEST.json)保留旧state/config/log/seals和volume原位hash。旧state仍ENGINEERING_NOT_READY，没有伪造TSDF/eval成功seal。新STATUS表示失败已诊断，不表示完整链成功。继续下一论文明确场景仍需独立数据hash和真实GPU smoke；完整suite未完成，不从这些负结果外推其他场景。用户冻结的paper-text公式、权重及全部旧证据保持不变。
'''
(P/'SCAN40_RESULT_REPORT_ZH.md').write_text(report);(O/'SCAN40_RESULT_REPORT_ZH.md').write_text(report)
review={'confirmed_negative_result':str(P/'STATUS.json'),'decision':'CONTINUE_SAME_FROZEN_METHOD_TO_NEXT_EXPLICIT_SCENE','direct_TSDF_failure_explained':True,'historical_optimization_unique_cause_proven':False,'new_renderer_or_method_patch':False,'previous_scene':'scan40','reason':'all49 native integrations have no fully supported crossing cube; preserve null metric and continue requested independent scene inventory without tuning; historical opacity collapse is not claimed uniquely explained','result_sha256':sha256(P/'STATUS.json'),'scientificdone':False};atomic_json(P/'NEGATIVE_RESULT_REVIEW.json',review)
e=A/'experiments/DTU_scan40_half30k_TSDF/STATUS.json';r=json.loads(e.read_text());r.update(status=status['status'],train_verified=True,export_verified=True,metric_value=None,delta=None,reason=status['reason'],diagnostic_review_completed=True,execution_chain_completed=False,result_report=str(P/'SCAN40_RESULT_REPORT_ZH.md'),utc=status['utc']);atomic_json(e,r)
protocol=json.loads((A/'FULL_SUITE_PROTOCOL.json').read_text());files=list((A/'experiments').glob('*/STATUS.json'));rows={json.loads(p.read_text())['id']:json.loads(p.read_text()) for p in files};ids=[e['id'] for e in protocol['entries']];assert len(files)==len(ids)==74 and set(rows)==set(ids)
keys=['id','dataset','scene','table','status','train_verified','export_verified','metric_value','paper_value','metric_unit','delta','scientificdone','reason'];tab=[{k:rows[i].get(k) for k in keys} for i in ids]
with (A/'METRICS.csv').open('w') as f:
 w=csv.DictWriter(f,fieldnames=keys);w.writeheader();w.writerows(tab)
atomic_json(A/'METRICS.json',{'all_complete':False,'protocol_sha256':sha256(A/'FULL_SUITE_PROTOCOL.json'),'rows':tab,'utc':status['utc']})
m=json.loads((A/'MASTER_STATUS.json').read_text());m.update(status='SCAN40_NEGATIVE_RESULT_REVIEWED',last_event='scan40 all49 views fused; no supported surface; official metric null; 1914 immutable inputs and train/export/boundary verified',next_action='Prepare scan55 using unchanged resolved paper-text method and mandatory GPU0 admission/smoke',utc=status['utc']);m['experiment_counts'].update(verified_train=4,verified_export=4,negative_terminal_attempts=3,empty_surface_attempts=2);m['blocked'].append({'stage':'scan40_official_eval','reason':'null metric: no original-threshold TSDF surface'});atomic_json(A/'MASTER_STATUS.json',m)
atomic_json(P/'EVIDENCE_MANIFEST.json',{'files':{str(p):sha256(p) for p in P.iterdir() if p.is_file()},'code':{str(p):sha256(p) for p in Path(__file__).parent.glob('*.py')},'scientificdone':False})
print(json.dumps({'status':status,'rows':len(tab)},indent=2))
