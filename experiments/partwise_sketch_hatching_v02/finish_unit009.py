"""Evidence-based unit009 handoff, preserving all engineering and science limits."""
from common import *
from datetime import datetime,timezone
U=OUT.parent/'unit_009';P=U.parent/'unit_008'
m=json.loads((U/'METRICS.json').read_text());v=json.loads((U/'INDEPENDENT_VALIDATION.json').read_text());video=json.loads((U/'VIDEO_VALIDATION.json').read_text())
edit=json.loads((U/'outputs/edited/EDIT.json').read_text());history=json.loads((U/'HISTORICAL_SEAL_AUDIT.json').read_text())
assert v['verdict']=='VALID' and all(x['passed'] for x in v['checks'].values())
assert m['scientific_gates']['quantitative_go_four_stills'] and video['all_rgb_exact'] and video['decoded_frames']==24
assert json.loads((U/'EXECUTION_tests.json').read_text())['returncode']==0
for name in ('reject_existing','reject_historical'):
    assert json.loads((U/f'EXECUTION_{name}.json').read_text())['returncode']==1
    expected='FileExistsError' if name=='reject_existing' else 'ValueError'
    assert json.loads((U/'runtime'/f'{name}.log').read_text())['error_type']==expected
visual=dict(actual_image_tool_review=True,reviewer='root',images={str(U/'figures'/n):sha(U/'figures'/n) for n in ('full_lamp_comparison.png','stem_comparison.png','all_parts_comparison.png','edit_all_frames.png','edit_first_middle_last.png')},
    density_edit_visual='GO_BOUNDED_FOUR_EXPOSED_VIEWS',full_visual='NO_GO_RETAINED',
    observations=['All four before/after pairs show the full lamp in frame and distinguish circumferential shade, axial stem and crosshatched base.',
    'Stem selection visibly reduces packed internal bars in all four views. Enlarged views retain axial hatch marks throughout declared shaft intervals and continuous readable object shape.',
    'Spacing and grayscale endpoints remain uneven, with near-edge overlap in120/210 views; the selection is not a uniform spacing or polished pencil-style solution.',
    'Shade has parallel stacks and uneven empty patches. Base foreground has dark crossings and irregular short strokes. These full-object quality blockers remain unchanged.',
    'All24 source frames and first/middle/last sheets show the expected two states; decoded FFV1 frames are exact. A fixed-camera edit does not establish orbit/zoom stability.'],
    limitations=['One author-reviewed GT asset, four exposed views; no blinded user preference experiment.','Coverage concerns analytic visible shaft y=.20..1.20 only; hidden upper stem excluded,4.1546% visible stem pixels outside interval.'])
write_json(U/'VISUAL_REVIEW.json',visual)
initial=json.loads((U/'EXECUTION_prepare.json').read_text());retry=json.loads((U/'EXECUTION_prepare_recovery.json').read_text());recovered=json.loads((U/'EXECUTION_prepare_recovered.json').read_text())
write_json(U/'PRE_EVALUATION_FAILURES.json',dict(initial=initial,retry=retry,recovered=recovered,
    cause='Initial preparation expected unit008/INHERITED_FAILURES.json, but file is under unit008/previous_snapshot. First repair command used unavailable unqualified python, so no patch ran; next preparation refused already copied files.',
    extra_terminal_errors=[dict(command='unqualified python heredoc repair',message='python: command not found',separate_returncode='NOT_CAPTURED'),dict(command='git add protocol before preparation succeeded (twice)',returncode=128,reason='protocol path absent')],
    correction='Known explicit Python applied read-only previous_snapshot fallback and verified SHA equality on already copied files; remaining input staging succeeded before protocol lock/evaluation.',
    preserved_source='PREPARE_INITIAL.py.txt',science_evaluated_before_recovery=False,threshold_or_candidate_change=False))
write_json(U/'NEGATIVE_CLI_CONTROLS.json',dict(existing_output_rejected=True,historical_output_rejected=True,expected_returncode=1,
    receipts=['EXECUTION_reject_existing.json','EXECUTION_reject_historical.json']))
old=json.loads((P/'STATUS.json').read_text())
blockers=[
    'Fullvisual NO_GO remains: shade spacing/parallel stacking and base foreground dark crossings/uneven short strokes persist. Stem is cleaner on4views but not uniformly spaced.',
    'Selected434 asset has four exposed stills and one fixed-camera discrete edit video only; no new orbit/zoom visibility or temporal audit for this selected subset.',
    'Four fixed shaft bins cover analytic visible y=.20..1.20;4.154589% visible stem pixels excluded, hidden upper stem unmeasured. Nonempty image support is not complete surface coverage or spacing proof.',
    'No verified trained RaDe-GS lamp or reconstructed main proxy; CPU-only disallows training. Unit006 synthetic RGB/camera readiness is not reconstruction.',
    'Unit007 temporal audit sampled18/458 paths;10 IDs unmeasured, eligible world-length14.324% of all sampled and50.825% of raw-visible. One of six sampled shade IDs contributed eligible observations. No all-stroke stability claim.',
    'Inherited17 hidden-profile observations,359 raw-hidden supported observations before unit007 exclusions, and shade rim-depth outliers remain. Zero new edit leakage does not prove baseline hiding correctness.',
    'Unit004 orbit19 ink ratio0.7521462443170939>.75 remains NO_GO. Unit004/005 remain DIAGNOSTIC_PREVIEW_ONLY; current short-path subset does not revise that result.',
    'Density control reselects original48 paths; no new target curve generation. Length/crossing operations, composition across complete recipes and whole-object procedural regeneration remain incomplete.',
    'GT geometry,GT labels,manual directions remain diagnostic upper bounds. No real/click-assisted labels, reconstructed lamp,H1/H2 comparison,LOD or24FPS claim.',
    'Unit006 signed-RGB reader failure and uint8 adapter recovery retained. Historical round001 rc143/PythonUNKNOWN,round002 stdout rc1,round004/012/013 NO_GO and original validationUNKNOWN retained.',
    'Old round016 planar width1->2 audit remains NOT_RUN and dispensable for the chosen whole-object surface-capsule route; not claimed passed.'
]
progress='完整GT台灯新增可执行支杆疏密控制：对原48条短轴向路径确定性选择24条，整灯458→434条；410条非目标路径和24条保留支杆路径逐字段字节保持。四视角支杆墨量为原38.8%–58.2%，16个冻结高度区间全部有真实排线支持，远其他部件/背景新增变化均为0；完整形体和三部件可辨，支杆密集条纹明显减少。冷配方重新选择与保存路径重放复现四幅输出，24帧编辑视频完整精确解码。P1新增可操作密度参数并减轻一个实际外观阻塞；完整视觉、动态覆盖和重建缺口仍未关闭。'
status=dict(stage='completed_target_only_stem_density_cli',execution_state='complete',scientific_verdict='STEM_DENSITY_EDIT_GO_FULL_P1_PARTIAL',
    tests=dict(algorithm_tests_passed=5,independent_checks_passed=len(v['checks']),views=4,axial_bin_view_checks_passed=16,original_stem_paths=48,selected_stem_paths=24,unchanged_non_target_paths=410,retained_all_paths_per_field_bytes_exact=True,cold_reselection_png_exact=True,cold_saved_path_replay_png_exact=True,decoded_frames=24,distinct_video_states=2,historical_manifest_files=sum(r['files'] for r in history['checks']),actual_visual_review=True,negative_cli_controls_passed=2),
    artifacts=['PROTOCOL.json','SOURCE_LOCK.json','METRICS.json','INDEPENDENT_VALIDATION.json','outputs/edited/asset.json','outputs/edited/recipe.json','cold_request/','references/','figures/full_lamp_comparison.png','figures/stem_comparison.png','figures/all_parts_comparison.png','videos/edit.mkv','VIDEO_VALIDATION.json','VISUAL_REVIEW.json','DELEGATED_VISUAL_REVIEW.json','PRE_EVALUATION_FAILURES.json','HISTORICAL_SEAL_AUDIT.json','REPORT_ZH.md'],
    blockers=blockers,outline_milestone='P1/W3/W4/W9; outline5.6,7.2,9.2,9.6,9.7,11.1,14.3',p1_progress=progress,
    claim_status=dict(coding='COMPLETE_FOR_FROZEN_STEM_DENSITY',software='GO',density_edit_visual='GO_BOUNDED_FOUR_EXPOSED_VIEWS',full_visual='NO_GO_RETAINED',reconstructed_input='BLOCKED_NOT_TESTED',full_P1='PARTIAL_NOT_COMPLETE',H1_H2='NOT_TESTED',selected_subset_temporal='NOT_NEWLY_TESTED'),
    protocol_commit='6107be74',implementation_commit='dfac67e8',session_start_jst='2026-10-21T19:00:46.063748+09:00',completed_utc=datetime.now(timezone.utc).isoformat())
write_json(U/'STATUS.json',status)
delegated=json.loads((U/'DELEGATED_VISUAL_REVIEW.json').read_text())
next_step=dict(action='continue',recommended_next_step='Implement ONE base-only length CLI control on unit009 outputs/edited asset434: freeze length_world .18->.12, same75 selected base seed pairs/150 paths and two direction layers, same260shade+24stem. Regenerate only selected base paths with original seed/ink identity and explicit recipe; freeze independent base coverage regions and both-layer support before evaluation. Show whole lamp and base crops, fixed edit plus bounded orbit/zoom of the resulting named asset, cold recipe regeneration and latency. No density retry or threshold-closing sweep.',
    hypothesis='Shortening existing selected base hatches can reduce the strongest remaining foreground crossing clutter and add the missing length operation, while retaining a readable crosshatched base and the cleaner stem.',
    fixed_controls=['Use current434 asset: shade0deg260, stem density0.5/24, selected75 base pairs150; preserve separate unit008+15deg recipe. Mesh, renderer, widths, inks, light, labels, retained284 non-target paths fixed.',
    'Exactly oneDEV candidate .18->.12 length; no density/count/crossing changes or sweep. Freeze coverage gates before outputs; no retries to meet oldunit004 .75 ratio.',
    'Independent analytic target3 masks, fixed2px band, targetL1>10 and farother/background<=.02; predeclare radial/visible-region denominators and both-layer support so shortening cannot win by emptying base. Report ink ratio descriptively.',
    'Freeze four views30/120/210/300,512square,2xAA and full-object framing. For resulting named asset freeze orbit24 azimuth15*k, zoom16 ataz30 distance4.8-.8*cos(2*pi*k/15), edit24 switch12, elevation20 and12fps; all decode and all-frame/first-middle-last contacts. Do not call contacts an independent temporal audit.',
    'Cold target regeneration from selected-seed recipe+mesh+retained284, independent saved-path replay, local edit latency including regenerate/render; unchanged inputs/IDs are secondary application checks.',
    'CPU<=2,noGPU,serial compute,invocation<=10min,unit<=45min; new authorized unit only. Preserve any coverage/visual failure and historical results.'],
    go_no_go=dict(go='Visibly less tangled base that remains crosshatched and readable in complete-object views/trajectories, all frozen support/isolation gates and cold recipe pass; preserve fullvisual NO_GO if shade/stem quality still insufficient.',no_go='Empty/fragmented/unreadable base, lost direction layer, no-op/leakage, cold mismatch or loss of non-target identity; retain failure without changing length/coverage thresholds.'),
    blockers=blockers,evidence_paths=['STATUS.json','METRICS.json','INDEPENDENT_VALIDATION.json','figures/all_parts_comparison.png','figures/stem_comparison.png','outputs/edited/asset.json','outputs/edited/recipe.json','VISUAL_REVIEW.json','DELEGATED_VISUAL_REVIEW.json','videos/edit.mkv'],
    p1_distance_reduced=progress+' 下一步将处理最突出的剩余底座交叉杂乱并新增长度操作，同时为更新后的完整资产补齐三类展示视频；不重复平面数值证明。',estimated_next_minutes=35,estimated_range_minutes=[30,40])
write_json(U/'NEXT.json',next_step)
write_json(U/'INHERITED_FAILURES.json',dict(previous_status_sha256=sha(P/'STATUS.json'),previous_blockers_verbatim=old['blockers'],preserved_evidence_directory='inherited_failures/',current_blockers=blockers,prior_negative_results_unchanged=True))
rows=[]
for r in m['stills']:
    coverage=r['candidate_axial_coverage'];bins=coverage['bins']
    rows.append(f"| {r['azimuth']}° | {r['edit']['inside_delta']:.6f} | {r['stem_hatch_ink_ratio']:.6f} | "+'/'.join(str(b['support_pixels']) for b in bins)+f" | {100*min(b['support_fraction'] for b in bins):.2f}% | 0 / 0 |")
report=f'''# Unit009：支杆嵌套疏密操作

**结论：支杆密度编辑的软件与四视角局部视觉 GO；完整视觉 P1 仍为 NO_GO/PARTIAL。** 本轮只执行 unit008 NEXT 的一个工作包，未开始新的平面审计、H2、重建训练或参数搜索。

先完整读 BRIEF、大纲851行及旧 round001/002/016 报告、原参数和 NEXT，再冻结协议 `6107be74`；实现与独立验证器提交 `dfac67e8`，随后源码/输入 SHA 锁定才执行测试及图像评价。GT 网格868顶点1728面、GT三部件和人工方向仍是诊断上限；旧视角全部标为已曝光，不是盲测。

唯一变量为支杆密度1→0.5。输入是 unit008 的原0°灯罩 selected458 基线，保留 unit008 的+15°灯罩配方为独立资产。本轮没有使用被拒绝的 unit004 八条长支杆路径。面积采样重放原48个种子，按三维欧氏最远种子次序选前24个；不是均匀几何间距。保留路径及墨色不变，灯罩260和底座150保持；整灯输出434条。

512²、2倍采样、1px屏幕线宽、0.006深度容差和原 renderer 不变，固定世界光照、无LOD。先查看DEV0°，只做一次预定候选的可读性检查，没有调参；随后30/120/210/300°，仰角20°、距离4.5、焦距600px。渲染仍是网格深度测试的采样 capsule 近似，有owner平面宽度近似及无近裁剪等限制。

| 方位 | 支杆内PNG L1变化 | 支杆墨量新/旧 | 四段支持像素 | 最小段支持比例 | 远其他/背景变化比例 |
|---|---:|---:|---|---:|---|
{chr(10).join(rows)}

独立连续解析射线掩码不读取候选深度/标签，仍与网格共享人工剖面。固定2px外部边界带比例分别为0.04435%、0.06972%、0.12487%、0.23859%，未扩大带宽。所有视角目标L1>10，远其他部件和背景变化均0；无编辑控制失败于非零门槛，远部件16亮像素黑化控制的泄漏比例为1，3px栅格漂移有非零响应。

覆盖门槛在评估前固定：世界y=[.20,.45,.70,.95,1.20]四区间，独立可见stem像素，无额外腐蚀；每段可见像素至少1、实际hatch>.1支持至少3像素且比例≥1%。四段分母为524/553/573/334像素，16项全部通过。零hatch负控制全部失败。四段合计覆盖95.8454%的解析可见支杆像素；4.1546%可见像素在区间外，隐藏上部不计入分母。该门槛防止清空支杆，不能证明均匀间距、完整表面覆盖或目标暗度准确。

实际查看整灯四组、放大支杆、三部件局部以及编辑全帧/首中末接触图。支杆密集内线减少，形体仍连续可读；120/210°仍有近边缘叠线与不均匀灰阶端点。灯罩平行堆叠、底座前缘深色交叉与不规则短线仍在，完整视觉不晋级。接触图放大采用最近邻，未平滑美化。

5项算法测试通过；独立保存输出审计16项通过。410条非目标和24条保留支杆路径的ID/part/ink/face/bary逐字段字节一致，仅作为辅助工程契约。冷请求只包含配方、mesh、原458路径和配置，重新计算选择，不含已选434路径缓存；冷选择与独立保存路径重放均复现四幅PNG和分层数组。没有曲线重生成或全对象过程式生成的声称。

实际密度选择耗时{edit['selection_seconds']:.6f}s；模块启动到首次预览{edit['command_to_first_preview_seconds']:.6f}s，到四幅输出{edit['command_to_all_previews_seconds']:.6f}s；外部命令wall={json.loads((U/'EXECUTION_edited.json').read_text())['wall_seconds']:.6f}s。延迟包含读取/校验/选择/保存/重绘，不是仅参数赋值。CPU affinity[0,1]，数值与ffmpeg各单线程、串行计算、无GPU；无实时或24FPS结论。

编辑视频512²、12fps、24帧FFV1：前12帧原48条、后12帧选24条，固定相机的两种真实状态，无插值。全24帧完整解码且RGB逐帧等于源图。此视频不提供新转台、缩放或无闪烁证据。

准备阶段的两次原rc1保留：首次错误地从unit008根读取继承失败摘要；修复命令使用未配置的裸python未执行修改，重试又因已复制输入被拒。改用明确解释器、幂等SHA核对和previous_snapshot回退后rc0，在协议冻结前完成。两个过早git add的rc128也记录。原始脚本快照和日志未删除，阈值与候选未变。另两个CLI覆盖/历史输出负控制预期返回1；FFmpeg仅输入头检查预期rc1，编码/完整解码均rc0。它们没有混同科学NO_GO。

历史unit003–008合计{sum(r['files'] for r in history['checks'])}份seal文件重新核验相同。旧unit004 orbit19 ink ratio0.7521462443>.75失败、unit004/005诊断预览标签、17隐藏支持观测、unit007有限覆盖、上缘深度离群，以及round001 rc143/PythonUNKNOWN、round002 stdout rc1、round004/012/013 NO_GO全部保留。旧round016宽度审计仍NOT_RUN且非当前路线前置条件。

{progress}

可操作说明见 `DENSITY_CLI_ZH.md`；精确执行命令与原返回码见unit目录 `EXECUTION_*.json` 和 `REPRODUCE.md`。完整定量结果见 `METRICS.json`、独立审计 `INDEPENDENT_VALIDATION.json`；图像/视频及STATUS/NEXT/SEAL在当前unit009。下一步仅按 `NEXT.json` 推荐执行；本轮未执行下一步。
'''
write_json(U/'SUMMARY_NUMERIC.json',dict(views=m['stills'],edit_latency=edit['command_to_first_preview_seconds'],selection_seconds=edit['selection_seconds']))
(U/'REPORT_ZH.md').write_text(report);(WORK/'docs/partwise_sketch_hatching_v02/REPORT_unit009_ZH.md').write_text(report)
import shlex
commands=['# Unit009 exact execution receipts','', 'Commands below were executed serially. Original return codes are retained; expected rejection controls are not successes.','']
for p in sorted(U.glob('EXECUTION_*.json')):
    if p.stem.endswith('_START'):continue
    r=json.loads(p.read_text());commands += [f"## {p.name}",f"Return code: {r['returncode']}; wall seconds: {r['wall_seconds']}",'```bash',shlex.join(r['command']),'```','']
(U/'REPRODUCE.md').write_text('\n'.join(commands))
print(json.dumps(dict(verdict=status['scientific_verdict'],status='complete',checks=len(v['checks']))))
