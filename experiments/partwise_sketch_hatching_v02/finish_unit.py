"""Summarize measured results and explicitly separate software from visual GO."""
from common import *
from datetime import datetime, timezone
from PIL import Image

def read(name): return json.loads((OUT/name).read_text())

assert not (OUT/'SEAL.json').exists(), 'sealed units are immutable'
validation=read('INDEPENDENT_VALIDATION.json')
assert validation['verdict']=='PASS'
edit=read('EDIT_METRICS.json');assets=read('ASSET_VALIDATION.json');probes=read('TEMPORAL_PROBES.json')
videos={name:read(f'VIDEO_{name}.json') for name in ('orbit','zoom','edit')}
cli={name:read(f'cli/{name}/EDIT.json') for name in ('angle35','width2')}
cli_exact={name:np.array_equal(np.asarray(Image.open(OUT/f'cli/{name}/image.png')),np.asarray(Image.open(OUT/f'stills/{stem}_030.png'))) for name,stem in [('angle35','angle'),('width2','width')]}
assert all(cli_exact.values())
timings=[]
for p in (OUT/'stills').glob('*.json'): timings.append(json.loads(p.read_text())['seconds'])
unique_renders={}
for name in videos:
    trajectory=read(f'TRAJECTORY_{name}.json')
    timings += [x['render_seconds'] for x in trajectory if not x['reused_identical_scene']]
    unique_renders[name]=sum(not x['reused_identical_scene'] for x in trajectory)
unmeasured=[sid for sid,r in probes['summary']['per_stroke'].items() if r['status']=='UNMEASURED']
hidden_hits=sum(x['summary']['hidden_profile_present'] for x in probes['rows'])
allcounts=probes['summary']['all']['class_counts']
metrics=dict(software_contract='GO_FOR_FROZEN_ENGINEERING_SCOPE',visual_verdict='NO_GO',
             reconstructed_input='BLOCKED_NOT_EXECUTED',H1='NOT_TESTED',H2='NOT_TESTED',
             assets=assets['gates'],edit_all_gates=edit['all_gates'],selected_probe_status=probes['summary']['status'],
             selected_probe_counts=allcounts,selected_probe_eligible_fraction=allcounts['visible']/sum(allcounts.values()),
             selected_probe_unmeasured_ids=unmeasured,hidden_profile_present_observations=hidden_hits,
             temporal_limits='Per-ID localization/support at 30-degree probe spacing, not consecutive 10-degree video frames or universal temporal/occlusion GO. Profiles at 17 hidden samples contain ink; these may include nearby visible same-ID segments and same-part depth discontinuities.',
             controls=probes['controls'],videos={name:{key:v[key] for key in ['decoded_frames','all_rgb_exact','distinct_frames']} for name,v in videos.items()},
             actual_sequence_render_calls=unique_renders,cli=cli,cli_images_exact=cli_exact,
             full_lamp_render_timing=dict(calls=len(timings),median_seconds=float(np.median(timings)),p95_seconds=float(np.percentile(timings,95)),
                                          scope='12 new stills + unique orbit/zoom/edit scenes; excludes old backend, isolated probes, startup and I/O'),
             independent_validation='PASS',resources=check_resources())
write_json(OUT/'metrics.json',metrics)
visual=dict(verdict='NO_GO',review_type='Actual images inspected by root and read-only assistant; no user preference study',
            inspected=['figures/full_lamp_comparison.png','stills/base_030.png','figures/orbit_all_frames.png','figures/zoom_all_frames.png','figures/edit_all_frames.png',
                       'figures/probes_first_middle_last.png','figures/crop_stem.png','figures/crop_base.png'],
            observations=['Complete lamp and all three parts visible in the frozen full-object images.',
                          'Shade angle and width edits are visible while stem/base are unchanged.',
                          'New shade side silhouettes are dotted or faint compared with inherited output.',
                          'Stem has crowded parallel bars; base crosshatching remains tangled and uneven.',
                          'Two prespecified probe IDs have no eligible observations; their blank views remain shown.'],
            inference='Foreground clipping of a 0.8px centered silhouette capsule at 2x sampling may remove about half its support; not yet causally tested.',
            nonclaims=['No finished P1 visual acceptance','No whole-object temporal stability claim','No H1/H2 or reconstruction claim'])
write_json(OUT/'VISUAL_REVIEW.json',visual)
blockers=['Visual NO_GO: fragmented shade outline, crowded stem, tangled base.',
          'Nine fixed probe IDs cover only 1352/4428 frame/sample observations; two IDs entirely ineligible.',
          '17 hidden-sample normal profiles contain ink; profile support is not equivalent to centerline leakage and needs local review.',
          'Same-part analytic depth interpolation and owner-plane extension remain approximations.',
          'No verified reconstructed lamp input; inherited bounded inventory only, no new training or inventory in this unit.',
          'CLI spacing is seed-density scaling, not guaranteed spacing; length/spacing/cross controls implemented but not validated this unit.']
status=dict(stage='sealed_whole_lamp_integration',execution_state='complete',scientific_verdict='WHOLE_LAMP_SOFTWARE_SLICE_GO_VISUAL_NO_GO',
            tests=dict(old_renderer=dict(returncode=1,tests=6,failed=2,preserved=True),new_renderer=dict(returncode=0,tests=6,passed=6),
                       cold_regeneration=assets['gates'],edit=edit['all_gates'],selected_probe=probes['summary']['status'],
                       independent_validation=dict(returncode=0,verdict='PASS',checks=7),cli_images_exact=cli_exact),
            artifacts=['PROTOCOL.json','SOURCE_LOCK.json','metrics.json','ASSET_VALIDATION.json','EDIT_METRICS.json','TEMPORAL_PROBES.json',
                       'INDEPENDENT_VALIDATION.json','VISUAL_REVIEW.json','figures/full_lamp_comparison.png','videos/orbit.mkv','videos/zoom.mkv','videos/edit.mkv',
                       'EXECUTION_stills_INTERRUPTED.json','REPORT_ZH.md'],
            blockers=blockers,outline_milestone='P1 GT full-object engineering slice; full P1 acceptance pending visual and reconstruction work',
            p1_progress='Integrated all three parts and 608 persistent barycentric strokes into per-fragment depth-tested rendering; actual local angle/width CLI, three videos, finite independent-geometry rendered probes and cold replay completed.',
            claim_status=dict(coding='COMPLETE_FOR_FROZEN_SCOPE',software='GO_FINITE_CONTRACT',visual='NO_GO',reconstructed_input='BLOCKED',research_H1_H2='NOT_TESTED'),
            original_failure=dict(stills_wrapper_returncode=143,scientific_child_returncode='UNKNOWN',outputs_independently_validated=True),
            historical_failures='round001/002 stdout failures, round004/012/013 NO_GO, rim depth outliers and original scope restrictions remain unchanged.',
            updated_at_utc=datetime.now(timezone.utc).isoformat())
if not (OUT/'STATUS_INITIAL.json').exists(): (OUT/'STATUS_INITIAL.json').write_bytes((OUT/'STATUS.json').read_bytes())
write_json(OUT/'STATUS.json',status)
nextstep=dict(action='continue',recommended_next_step='One bounded whole-lamp visual repair unit: diagnose and repair shade silhouette coverage using azimuth0 DEV, then freeze a single contour candidate before the same four complete-lamp diagnostic views and a short fixed orbit. Keep hatches, anchors, light, part IDs and .006 depth tolerance unchanged. Inspect retained 17 hidden-profile hits as local diagnostic crops without changing eligibility to improve scores. Preserve unit001 visual NO_GO. After contour readability, address base/stem density as separate part-local DEV work; no planar-only proof unit.',
              hypothesis='A contour-specific screen coverage rule can restore readable continuous lamp outlines without undoing per-fragment hatch hiding or local edit isolation; present half-clipped thin contours are a suspected cause.',
              fixed_controls=['unit001 mesh and 608 baseline paths','part IDs/ink/style and 1px hatch widths','512x512,2x sampling, .006 depth tolerance','angle35 and shade width1->2 edit controls','2px independent-mask boundary band','all unit001 negative evidence and source hashes; exposed views remain exposed','CPU<=2,noGPU,one unit<=45min'],
              go_no_go=dict(go='Clear full-lamp contours on fixed views and orbit, no new hidden lines or edit leakage; retain nonzero target and all frozen baseline evidence.',
                            no_go='Retain visible discontinuity/overdraw or unsupported metric claims; do not enlarge depth/boundary tolerances or select best test frames.'),
              blockers=blockers,evidence_paths=['VISUAL_REVIEW.json','figures/full_lamp_comparison.png','figures/orbit_all_frames.png','metrics.json','TEMPORAL_PROBES.json','INDEPENDENT_VALIDATION.json'],
              p1_distance_reduced='Moved from isolated planar renderer evidence to an executable complete three-part lamp, real edits and all three videos. Next work directly removes the visible whole-lamp failure rather than adding planar proofs.',
              estimated_next_minutes=35,estimated_range_minutes=[30,35],updated_at_utc=datetime.now(timezone.utc).isoformat())
write_json(OUT/'NEXT.json',nextstep)
lines=['# unit_001：完整台灯 P1 集成报告','',
'本轮已实际完成完整三部件 GT 台灯的新渲染后端集成、局部角度／线宽编辑、三类视频与独立数据复核。**冻结软件契约 GO，视觉 NO_GO；尚未完成完整 P1，更没有 RaDe-GS 重建或 H1/H2 研究结论。** 没有启动新的平面证明链。', '',
'原大纲、BRIEF、round_001/002/016 的报告、参数与 NEXT 已完整读取。路线见 `P1_ROADMAP_ZH.md`，历史映射见 `INHERITED_AUDIT_ZH.md`。旧 round016 的单平面 width1→2 审计不属于本路线前置条件，标记 NOT_RUN，绝不记作通过。', '',
'协议提交 `7dff4ce4`，实现 `cb1ea0b3`，评价前源码／资产锁 `7ee407e8`；独立复核实现 `b77d35ab`、锁 `9c1c81fc`。原授权 base 47792c93 的后代 95c82bd 是起始 HEAD；只在授权分支写新文件。', '',
'## 实际完整物体切片','',
'868 顶点、1728 面沿用 round002 原字节，part 1=灯罩、2=支杆、3=底座。608 条固定重心路径：260/48/300，分别周向、轴向、短交叉；人工 GT 几何／标签／方向，不是重建或自动分部。冷重生成与历史路径摘要完全一致；灯罩 +35° 只重生成目标部件，348 条非目标路径的 ID、面、重心和墨量逐值不变。线宽 1→2px 不重生成任何路径。', '',
'新后端采用屏幕圆头线段覆盖、同像素射线的面平面深度与部件检查，2× 超采样后 box 覆盖平均；固定容差 .006，禁止先判中心再膨胀。面平面横向延伸、离散超采样与轮廓覆盖仍为近似。旧／新对比没有匹配实际墨量或标定有效线宽，不能据此宣称 H4 或视觉优势。', '',
'六项相同回归：旧后端真实 rc=1、两项遮挡失败；新后端 rc=0、六项通过。两个旧失败的最大前景泄漏墨量均为 0.85490196，新后端满足冻结零泄漏阈值。原日志和退出码均保留。', '',
'## 编辑与输出','',
'| 方位 | 角度编辑目标内 L1 | 角度外部边界带 | 线宽编辑目标内 L1 | 线宽外部边界带 |','|---|---:|---:|---:|---:|']
for v in edit['views']:
    lines.append(f"| {v['azimuth']}° | {v['angle']['inside_delta']:.3f} | {100*v['angle']['boundary_band_fraction']:.4f}% | {v['width']['inside_delta']:.3f} | {100*v['width']['boundary_band_fraction']:.4f}% |")
lines += ['', '上述每种编辑的远区其他部件与远背景泄漏均为 0；使用独立连续旋转曲面射线掩码和预先固定的 2px 外部边界带。目标变化均非零；no-edit 控制为零且不满足非零门槛；向支杆注入黑块使泄漏指标上升。旧灯罩上缘深度最大误差约 0.130758 仍保留，未扩大排除带。','',
'| 视频 | 解码帧数 | 不同图像 | 实际场景渲染调用 |','|---|---:|---:|---:|']
for name,v in videos.items(): lines.append(f"| {name} | {v['decoded_frames']} | {v['distinct_frames']} | {unique_renders[name]} |")
lines += ['', '512×512、12fps，FFV1 无损；全部84帧完整解码并与源PNG逐像素一致。缩放为真实相机距离4.0–约5.6往返；相同场景缓存复用已在轨迹逐帧注明。编辑视频只有两个真实配置，前后各12帧，无淡入淡出。全帧接触图和首／中／末原分辨率接触图均保存。', '',
f"实际 CLI 灯罩 +35° 的重生成 {cli['angle35']['regeneration_seconds']:.3f}s，含渲染 {cli['angle35']['regeneration_and_render_seconds']:.3f}s；线宽编辑含渲染 {cli['width2']['regeneration_and_render_seconds']:.3f}s。两张CLI输出与冻结静帧逐像素相同。spacing-scale 只是种子密度代理，不保证最小间距；长度／密度／交叉开关已实现但本轮未验证，不能称全部交互任务完成。", '',
f"{len(timings)} 次完整新后端场景渲染的时间中位数 {np.median(timings):.3f}s、P95 {np.percentile(timings,95):.3f}s，不含启动、读盘和隔离探针；不作实时24FPS或独立性能基准结论。", '',
'## 实际渲染探针及覆盖限制','',
'预先选择每部件 seed0/12/24 的 layer0，共九个ID；12个30°间隔方位、每笔41个等弧长位置（含端点）。独立解析深度／部件图插值定义有效区，在实际隔离笔触PNG上量测 ±2px 法向墨量剖面；不是最近任意笔触匹配。','',
'| 部件 | 有效观察/全部观察 | 位置绝对误差 P95 | 有效观察缺失 |','|---|---:|---:|---:|']
for p,r in probes['summary']['per_part'].items(): lines.append(f"| {p} | {r['class_counts']['visible']}/1476 | {r['centroid_abs_px']['p95']:.6f}px | {r['missing_visible']} |")
lines += ['',f"合计1352/4428观察有效（{1352/4428:.2%}），其余1934隐藏、1142边界；unique visible-ever 277/369 个采样身份。`{unmeasured[0]}` 与 `{unmeasured[1]}` 无有效观察，明确 UNMEASURED，没有重新挑选替代ID。故有效证据来自七个ID，不是608条笔触的完整稳定性。三像素平移注入最大平均支持距离增量3px；整笔删墨使全部有效样点判为缺失。", '',
f"隐藏类仍有 {hidden_hits} 个法向剖面含墨，可能来自同一笔触邻近可见片段或同部件深度分支插值；不是已确认的中心线泄漏，也不能据此宣布完美遮挡。逐观察数据保留。相邻探针不是10°转台的相邻视频帧，帧间残差只作描述，无全物体时序GO。共享人工形状定义、解析深度插值与边界排除均限制外推。", '',
'## 视觉、故障与复核','',
'已查看实际完整四视角对比、三个视频所有帧接触图、九个探针首中末（包括空图），以及原尺寸支杆和底座裁图。完整台灯可辨，三种部件风格与目标编辑可辨；但新灯罩侧轮廓断续／过淡，支杆竖线拥挤，底座交叉线杂乱，**视觉 NO_GO**。不能用通过数值指标覆盖此失败。薄轮廓被前景裁剪损失覆盖是待验证推断，未据此在冻结结果上调参。', '',
'静帧科学文件全部写完且 stdout 为 all_gates=true 后，包装进程实际返回143，最终收据缺失；科学子进程原始退出码 UNKNOWN，见 `EXECUTION_stills_INTERRUPTED.json`。未伪写为0，也未重渲染覆盖原文件。独立验证随后真实 rc=0，七组核验全部通过：源码快照、数组盘点、路径身份、四视角PNG指标与重新解析掩码、84帧全解码、冷重绘、108个隔离输出及216个注入控制重算。它证明工件一致，不替代科学或视觉结论。', '',
'历史 round001/002 stdout 失败、round004/012/013 NO_GO、上缘深度离群与短路径终止均未改写。本轮未做新 RaDe-GS 盘点或训练；继承的有界搜索未找到灯具重建，不扩大为全机不存在。', '',
'## 交付与下一步','',
f'科学目录：`{OUT}`。`STATUS.json`、`NEXT.json`、`SEAL.json` 与 SHA256 清单提供可恢复交接；源码和文档只在新命名空间。CPU affinity [0,1]，数值与视频线程各限1且串行，无GPU、无下载、无push/merge。运行日志不进入科学文件清单，由执行收据绑定。', '',
'下一单元建议30–35分钟，直接修复完整台灯轮廓覆盖：在方位0 DEV定位，冻结一个轮廓候选后检查同四视角与短转台；保持排线、路径和深度容差不变，保留17个隐藏剖面命中的局部诊断。轮廓可读后，再单独做支杆／底座密度清理。本轮已把P1距离从孤立平面证据推进到可执行整灯、真实编辑、三视频及有限实际输出核验；尚不能宣布整体P1验收。', '']
report='\n'.join(lines)
(OUT/'REPORT_ZH.md').write_text(report)
(WORK/'docs/partwise_sketch_hatching_v02/REPORT_unit001_ZH.md').write_text(report)
print(json.dumps(native(dict(verdict=status['scientific_verdict'],metrics=metrics['full_lamp_render_timing'],resources=check_resources()))))
