"""Report existing frozen evidence; no rendering or scientific retuning."""
from common import *
from datetime import datetime, timezone
import statistics
import subprocess
import shutil

OUT=Path('/mnt/hdd1/u00134/partwise_sketch_hatching_p1_v02/units/unit_002')
def read(name):return json.loads((OUT/name).read_text())
validation=read('INDEPENDENT_VALIDATION.json');audit=read('AUDIT_UNIT002.json');replay=read('COLD_REPLAY.json')
assert validation['verdict']=='VALID' and audit['verdict']=='VALID' and replay['all_exact']
assert audit['scientific_gates']['all_frozen_contour_gates'] and validation['scientific_gates']['local_edit_go']
for lockname in ('SOURCE_LOCK.json','VALIDATION_LOCK.json'):
    for p,h in read(lockname)['files'].items():assert sha(p)==h,p
views=validation['evidence']['actual_stills_layers_masks_and_metrics']['views']
observations=audit['details']['all_still_and_orbit_contour_metrics']['observations']
times=sorted(r['render_seconds'] for r in read('TRAJECTORY_orbit.json'))
metric={
 'verdict':'WHOLE_LAMP_CONTOUR_REPAIR_GO_FULL_VISUAL_NO_GO',
 'scope':'One exposed GT lamp, frozen four views and24-frame fixed-distance orbit; no new zoom/LOD or reconstruction claim.',
 'contour':{'evaluated_view_frame_observations':len(observations),
  'per_part':{p:{'coverage_min':min(r['candidate']['per_part'][p]['coverage'] for r in observations),
                  'p95_support_distance_max_px':max(r['candidate']['per_part'][p]['support_distance_p95_px'] for r in observations),
                  'max_connected_missing_pixels':max(r['candidate']['per_part'][p]['max_connected_missing_pixels'] for r in observations)} for p in ('1','2','3')},
  'all_fixed_gates_pass':audit['scientific_gates']['all_frozen_contour_gates'],
  'far_external_support_pixels_max':max(r['candidate']['far_external_support_pixels'] for r in observations),
  'still_before_after':[{ 'azimuth':v['azimuth'],'legacy':v['legacy_contour'],'candidate':v['candidate_contour']} for v in views]},
 'edit':{kind:{'target_delta_min':min(v[kind]['inside_delta'] for v in views),'target_delta_max':max(v[kind]['inside_delta'] for v in views),
                  'far_other_fraction_max':max(v[kind]['far_other_parts_fraction'] for v in views),
                  'far_background_fraction_max':max(v[kind]['far_background_fraction'] for v in views),
                  'boundary_band_fraction_max':max(v[kind]['boundary_band_fraction'] for v in views)} for kind in ('angle','width')},
 'non_target_paths':audit['details']['part_local_edit_paths'],
 'video':validation['evidence']['complete_orbit_video_decode'],
 'cold_replay':replay,
 'performance':{'render_frames':24,'median_seconds':statistics.median(times),'p95_seconds':statistics.quantiles(times,n=100,method='inclusive')[94],
                'scope':'Single CPU offline run, includes render only; no regeneration or interactive FPS claim.'},
 'historical_unit_files_verified':audit['details']['unit001_sealed_unit_files']['unit_files_checked'],
 'retained_hidden_profile_hits':read('HIDDEN_PROFILE_REVIEW.json')['count'],
 'execution_interruption':read('EXECUTION_orbit_INTERRUPTED.json'),
 'resources':{'cpu_affinity':[0,1],'numeric_threads':1,'gpu':False,'root_free_bytes':shutil.disk_usage(WORK).free,
              'hdd_free_bytes':shutil.disk_usage(OUT).free,'task_bytes':sum(p.stat().st_size for p in OUT.parent.rglob('*') if p.is_file())}}
write_json(OUT/'metrics.json',metric)
visual={
 'contour_verdict':'GO_BOUNDED_WHOLE_LAMP_CONTOUR_REPAIR','whole_object_verdict':'NO_GO',
 'reviewers':'Root actual-image review and delegated read-only review; no user preference study.',
 'inspected':['figures/dev_comparison.png','figures/full_lamp_comparison.png','figures/contour_comparison.png',
              'stills/base_030.png','stills/base_120.png','stills/base_210.png','stills/base_300.png',
              'figures/orbit_all_frames.png','figures/orbit_first_middle_last.png','figures/base_crop_stem.png',
              'figures/base_crop_base.png','figures/hidden_profiles_all.png'],
 'observations':['Complete three-part lamp is visible; shade side outlines and lower ellipse, stem silhouette and base outer edge are continuous/readable.',
                 'Both local shade edits are visible; no conspicuous newly exposed rear contour observed in fixed views/contact frames.',
                 'Stem has densely adjacent vertical strokes; base short-cross strokes remain tangled/uneven with dark intersections.',
                 'Top-rim/subpixel tonal variation remains. Contact sheets and support metrics are not a flicker or smooth-AA proof.'],
 'hidden_profile_review':{'status':'UNRESOLVED_RETAINED','observations':17,'stroke_ids':2,'frame_id_groups':3,
     'observed':'Tiny one/few-pixel ink islands near sample-normal profiles;11 shade observations and6 base observations.',
     'inference':'May repeatedly sample support from a nearby visible fragment, but attribution is unproven; not cleared leakage or17 independent failures.'},
 'limits':['Exposed axisymmetric authored GT; not new research TEST.','Contour centerline visibility emits round caps up to.4px beyond an occlusion endpoint.',
           'New candidate was evaluated at distance4.5, not a new zoom sequence.','No reconstructed input or H1/H2 claim.']}
write_json(OUT/'VISUAL_REVIEW.json',visual)
blockers=['Whole-object visual NO_GO: dense stem bars and tangled/uneven base crosshatching remain.',
          '17 inherited hidden-profile observations remain unresolved; prior nine-ID coverage limitations retained.',
          '2x contour sampling and .4px centerline cap endpoint extension; no new zoom/LOD or universal visibility claim.',
          'No verified reconstructed lamp; GT geometry, labels and manual directions remain diagnostic upper bound.',
          'Old CLI/common OUT still points to unit001 and renderer legacy default remains for backward compatibility; use explicit contour_visibility=visible_centerline API in a newly authorized output runner.']
status={'stage':'sealed_whole_lamp_contour_repair','execution_state':'complete','scientific_verdict':metric['verdict'],
 'tests':{'red':{'returncode':1,'tests':3,'failed':1,'passed':2},'green':{'returncode':0,'tests':3,'passed':3},
          'inherited_renderer':{'returncode':0,'tests':6,'passed':6},'artifact_validation':validation['verdict'],
          'all_frame_audit':audit['verdict'],'cold_snapshot_replay':replay['all_exact'],'edit_gates':True,'contour_gates':True},
 'artifacts':['PROTOCOL.json','SOURCE_LOCK.json','VALIDATION_LOCK.json','metrics.json','INDEPENDENT_VALIDATION.json','AUDIT_UNIT002.json',
              'COLD_REPLAY.json','VISUAL_REVIEW.json','HIDDEN_PROFILE_REVIEW.json','figures/full_lamp_comparison.png','figures/orbit_all_frames.png',
              'videos/orbit.mkv','EXECUTION_orbit_INTERRUPTED.json','REPORT_ZH.md'],
 'blockers':blockers,'outline_milestone':'P1 GT complete-object engineering slice; contour readability repaired; full visual and reconstructed input pending.',
 'p1_progress':'Removed actual full-object silhouette discontinuity across all3 parts/28 view-frame observations while retaining local angle/width edits and unchanged non-target paths; moves P1 from broken object outline to readable complete silhouette.',
 'claim_status':{'coding':'COMPLETE_FOR_FROZEN_SCOPE','software':'GO_FINITE_CONTRACT','contour_visual':'GO_BOUNDED','whole_object_visual':'NO_GO','reconstructed_input':'BLOCKED','H1_H2':'NOT_TESTED'},
 'original_failure':{'orbit_wrapper_returncode':143,'scientific_child_returncode':'UNKNOWN','independent_artifact_validation':'VALID','all24_video_frames_exact':True},
 'historical_failures':'unit001 visual NO_GO and143/UNKNOWN; round001/002 stdout failures; round004/012/013 NO_GO and rim depth outliers all retained.',
 'completed_utc':datetime.now(timezone.utc).isoformat()}
write_json(OUT/'STATUS.json',status)
next_item={'action':'continue','recommended_next_step':'One base-only visual density/spacing cleanup unit: on DEV azimuth0 choose one deterministic nested selection of existing base seed pairs, preserving both cross layers for every retained seed. Freeze that single setting before four exposed full-lamp views and a short fixed orbit. Keep shade/stem paths, current visible_centerline contours, geometry, light and depth tolerance unchanged. Report changed base ink/coverage explicitly and validate actual nonzero base edit plus independent-mask leakage and fixed non-target IDs. Do not claim H2 or physical Poisson spacing from simple thinning.',
 'hypothesis':'Stable selection of paired short-cross base strokes can reduce crowded intersections while retaining visible base style and shape, without changing other parts or reintroducing broken contours.',
 'fixed_controls':['unit002 protocol/renderer and explicit visible_centerline mode','unit001 mesh/608 source strokes; only selected base pair subset changes','shade/stem IDs/coordinates/ink unchanged','512x512,2x sampling,.006 depth tolerance,.8px contours,1px hatches','independent masks and fixed2px band','all exposed views and all previous failures remain exposed/retained'],
 'go_no_go':{'go':'Cleaner readable base in actual complete-lamp outputs, nonzero local edit and low far-part/background leakage, paired cross style retained, base ink/coverage and selected-stroke count disclosed, unchanged shade/stem and contours.',
             'no_go':'Apparent cleanliness comes only from near-empty base, clipping, hidden leakage or failed edit controls; preserve NO_GO without post-test threshold/setting changes.'},
 'blockers':blockers,'evidence_paths':['VISUAL_REVIEW.json','figures/base_crop_base.png','figures/base_crop_stem.png','figures/full_lamp_comparison.png','metrics.json','AUDIT_UNIT002.json'],
 'p1_distance_reduced':'This unit repaired readable whole-lamp contours and kept actual local edits. The next base-only change addresses the most visible remaining full-object hatch clutter, moving toward three clean controllable styles instead of another planar proof.',
 'estimated_next_minutes':30,'estimated_range_minutes':[25,35],'updated_at_utc':datetime.now(timezone.utc).isoformat()}
write_json(OUT/'NEXT.json',next_item)
report=f'''**本轮完成一个实质步骤：完整台灯轮廓覆盖修复。结论为轮廓修复 GO，完整台灯视觉仍 NO_GO。**

完整阅读 BRIEF 和原大纲851行，并继承 round001/002/016 报告、参数、NEXT 与 unit001 负结果。按 unit001 NEXT，仅改变轮廓可见性／覆盖规则；608条持久笔触、868顶点／1728面 GT 网格、人工部件ID与方向、1px排线、0.8px轮廓、0.006深度容差、2px评价带全部固定。没有平面证明链、GPU、训练、下载、push或merge。

原规则对每个轮廓覆盖样本要求同部件表面和 owner-plane 深度一致，背景半侧必被丢弃；掠射处的 owner-plane 比较也可能加重缺口，后者为实现推断，未单独消融。候选只对轮廓：在每个覆盖样本最近的投影中心线点上查询精确网格射线深度，以透视正确的线深度判断可见，再绘制完整对称屏幕胶囊。排线和固定剖面环仍用原规则。该屏幕轮廓在遮挡端点可能外延最多0.4px，不宣称严格片元遮挡或精确解析面积。

协议／实现提交 `e4d2e985` 先于评价；DEV0只看一个预定候选，无参数搜索。随后 `ef405d73` 绑定源与输入，再执行四视角和24帧转台。`d580c784` 仅冻结额外的独立全帧核验和冷重放，无候选／阈值改变。所有几何及视角族已曝光，不是盲测；GT及解析参考共享人工形状定义，不是重建精度或统计泛化证据。

| 独立外轮廓指标（四固定视角） | 旧规则 | 修复后 |
|---|---:|---:|
| 灯罩支持率 | 73.6128% | 100% |
| 支杆支持率 | 12.0000% | 100% |
| 底座支持率 | 99.5360% | 100% |
| 灯罩最长缺失连通像素数 | 13 | 0 |
| 支杆最长缺失连通像素数 | 43 | 0 |

四静帧加全部24转台帧，共28个视图／帧观察中，每个部件支持率均100%，支持距离P95最大1px，缺失连通像素数0，固定2px带外轮廓支持像素0。定义为独立连续旋转曲面前景的3×3内边界、轮廓层墨量阈值0.1、支持距离≤1.5px；不是连续弧长、内部遮挡证明或抗锯齿／闪烁指标。轴对称对象的多视角不构成独立对象样本。

四视角灯罩角度+35°目标L1变化1732.8902–3337.8706；宽度1→2px为862.0745–1759.6824。两种编辑的远区其他部件、远背景及外部2px带变化占比均0；no-edit与黑块泄漏注入控制均通过。348条非目标笔触ID、face、重心坐标、墨量不变；260条灯罩路径确实改变。12张实际排线层与unit001一致，环层也不变。这些是限定变更的回归证据，主要应用门槛仍是完整台灯实图与轮廓可读性。

轮廓测试旧规则3项中1失败（覆盖0.46，不满足>0.8）、2通过，rc=1；新规则3通过，rc=0，包括同部件／不同部件遮挡。既有6项渲染测试通过。独立文件／掩码核验 rc=0；另一个边界实现重算全部28观察并检查显式带外零支持门槛，rc=0。历史unit001封存目录359项文件及其中源码快照保持原SHA；可变worktree20项另列跳过，未假称旧worktree仍全同。

转台24帧，512²、2×采样、12fps、FFV1，azimuth=15i、elevation20°、distance4.5；全部RGB解码与源PNG相同。渲染中位数{metric['performance']['median_seconds']:.4f}s、P95 {metric['performance']['p95_seconds']:.4f}s。冷进程从冻结source_snapshot重绘az30，实际PNG及保存层完全复现，加载加渲染{replay['load_and_render_seconds']:.4f}s。没有重生成原路径，不声称交互24FPS；新轮廓未重做缩放／编辑视频，unit001旧三视频仅为继承证据。

**执行异常保留：** 转台包装进程返回143，科学子进程最终退出码UNKNOWN；24帧、轨迹、视频与编码rc=0记录在终止前已写出。`EXECUTION_orbit_INTERRUPTED.json`与原日志保留；没有改写原退出码或重渲染掩盖异常。后续完整解码、源锁核验、全帧指标重算均独立通过，最终execution_state表示数据核验完成。初次git add因稀疏检出返回1，后用明确路径`--sparse`完成，未修改稀疏规则。

实际查看DEV、四视角前后／编辑、独立轮廓层、全部24帧接触图与首中末、原尺寸部件裁图。灯罩侧边／下缘、支杆边缘及底座外轮廓连续可读，未看到明显新增背后轮廓；支杆密集平行黑条、底座交叉线纠缠及暗交点仍明显，顶部环还有亚像素深浅变化。因此完整对象视觉仍NO_GO，不以指标全绿替代可用性。

此前17个隐藏样点剖面有墨命中全部保存并查看，集中在两个笔触／三个帧组：灯罩11观察、底座6观察。局部一至数像素墨岛与附近法向剖面相交，可能来自附近可见片段，但来源未经确认；保留UNRESOLVED，不解释为已排除泄漏，也不是17个独立故障。unit001九ID的1352/4428有效观察、两个全不合格ID、旧深度离群及round004/012/013 NO_GO仍保留。

当前新规则需显式配置 `cfg['renderer']['contour_visibility']='visible_centerline'`；默认仍为旧规则以兼容历史调用。`common.OUT`／旧编辑CLI仍绑定unit001，不能在封存后调用写入；本轮实际命令使用独立unit002 runner，源码与执行收据完整保留。没有把API集成误写成新的通用编辑UI完成。

这一步把P1从“整灯外形断线”推进到“三部件外轮廓可读且真实局部编辑仍隔离”。下一步仅建议底座局部密度整理：在DEV0选择一个确定、嵌套的种子对筛选，保留每个入选种子的交叉两层，冻结后比较实际整灯、墨量／覆盖和局部编辑泄漏；灯罩／支杆与当前轮廓保持不变，预计25–35分钟。不要把简单抽稀称为物理最小间距保证或H2。

科学目录：`{OUT}`。主要证据为 `metrics.json`、`AUDIT_UNIT002.json`、`INDEPENDENT_VALIDATION.json`、`VISUAL_REVIEW.json`、`figures/full_lamp_comparison.png`、`videos/orbit.mkv`。当前只是GT P1工程切片；重建输入BLOCKED，H1/H2未测试，完整P1未验收。
'''
(OUT/'REPORT_ZH.md').write_text(report)
(WORK/'docs/partwise_sketch_hatching_v02/REPORT_unit002_ZH.md').write_text(report)
receipts=[read(p.name) for p in sorted(OUT.glob('EXECUTION_*.json')) if p.name!='EXECUTION_orbit_INTERRUPTED.json']
reproduce='''# Unit002 execution record

Commands below are the exact completed attempts, not instructions to overwrite sealed output.
All computations were serial, CPU affinity 0,1; CUDA_VISIBLE_DEVICES empty;
OMP/OPENBLAS/MKL/NUMEXPR threads1, PYTHONDONTWRITEBYTECODE1, and
TMPDIR=/mnt/hdd1/u00134/partwise_sketch_hatching_p1_v02/orchestration/scratch.
The receipt wrapper adds a590s timeout and retains original return codes.
Do not invoke old producers/common.OUT/CLI: they target unit001. Future replay
requires a newly authorized output directory, with historical files read-only.

'''
for rec in receipts:
    reproduce+='```text\n'+' '.join(rec['command'])+'\n```\n\nReturn code: '+str(rec['returncode'])+'; seconds: '+str(rec['wall_seconds'])+'\n\n'
reproduce+='Orbit original command and wrapper rc143/child UNKNOWN are in EXECUTION_orbit_INTERRUPTED.json. No science output was rewritten during recovery.\n'
reproduce+='Source replay used source_snapshot in a fresh process and wrote only replay/base_030.png. It reproduced the actual PNG and six saved layers.\n'
(OUT/'REPRODUCE.md').write_text(reproduce)
(WORK/'docs/partwise_sketch_hatching_v02/REPRODUCE_unit002.md').write_text(reproduce)
print(json.dumps(native({'verdict':metric['verdict'],'outline':'P1 contour readability improved; whole visual NO_GO','next_minutes':30}),ensure_ascii=False))
