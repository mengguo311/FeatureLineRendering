"""Record observed base-length result and one actionable P1 handoff."""
from common import *
from datetime import datetime,timezone
import shlex
U=OUT.parent/'unit_010';P=U.parent/'unit_009'
m=json.loads((U/'METRICS.json').read_text());v=json.loads((U/'INDEPENDENT_VALIDATION.json').read_text());videos=json.loads((U/'VIDEO_VALIDATION.json').read_text());edit=json.loads((U/'outputs/edited/EDIT.json').read_text())
assert v['verdict']=='VALID' and all(x['passed'] for x in v['checks'].values())
assert m['scientific_gates']['quantitative_go_four_stills'] and m['scientific_gates']['quantitative_go_all40_frames']
assert sum(x['decoded_frames'] for x in videos.values())==64 and all(x['all_rgb_exact'] for x in videos.values())
assert json.loads((U/'EXECUTION_tests.json').read_text())['returncode']==0
for name,error in [('reject_existing','FileExistsError'),('reject_historical','ValueError')]:
    assert json.loads((U/f'EXECUTION_{name}.json').read_text())['returncode']==1
    assert json.loads((U/'runtime'/f'{name}.log').read_text())['error_type']==error
assert not (P/'forbidden_unit010_write').exists()
assert (U/'DELEGATED_VISUAL_REVIEW.json').exists()
reviewed=['dev_comparison.png','full_lamp_comparison.png','base_comparison.png','all_parts_comparison.png']+[f'{n}_{s}.png' for n in ('orbit','zoom','edit') for s in ('all_frames','first_middle_last')]
visual=dict(actual_image_tool_review=True,reviewer='root',images={str(U/'figures'/n):sha(U/'figures'/n) for n in reviewed},
    base_length_visual='GO_BOUNDED_EXPOSED_GT_STILLS_AND_TRAJECTORY_CONTACTS',full_visual='NO_GO_RETAINED',
    observations=['Complete lamp, shade, stem and base remain recognizable and fully in frame in four still pairs and all64 trajectory source-frame contacts.',
        'Shortening reduces long connected crossing chains at the base front rim. Most visible at30/120; the shape remains crosshatched, with both directions appearing as separated short X marks.',
        'Base retains uneven gaps and clustered left/rear/right patches depending on view, plus some rim overlaps. Shorter marks are a sparse X texture, not calibrated tonal pencil shading.',
        'Shade parallel stacks and uneven horizontal bands are unchanged; stem remains uneven with near-edge overlaps. Whole-object visual quality is not promoted.',
        'Orbit24 and cosine zoom16 show the same named434 asset in all frames; edit24 shows two discrete actual states. Contacts and exact video decode do not prove per-stroke temporal stability.'],
    limitations=['One procedural GT object and exposed view family; no blinded preference experiment.','Both-layer raster support separately measured only at4stills;40movingframes have combined hatch coverage only.','All visible analytic base pixels enter four geometry cells; physically hidden surfaces remain unmeasured.'])
write_json(U/'VISUAL_REVIEW.json',visual)
write_json(U/'NEGATIVE_CLI_CONTROLS.json',dict(existing_output_rejected=True,historical_output_rejected=True,expected_returncode=1,receipts=['EXECUTION_reject_existing.json','EXECUTION_reject_historical.json']))
old=json.loads((P/'STATUS.json').read_text())
blockers=[
    'Fullvisual NO_GO retained: shade parallel stacking/uneven bands and stem uneven axial spacing remain; shortened base still has sparse X texture, residual rim overlaps and uneven gaps.',
    'Current434 length.12 asset has64frames of fully decoded orbit/zoom/edit media and44view combined coverage, but no new independent per-stroke temporal correspondence or hiding audit; both-layer raster support measured on4stills only.',
    'Coverage partitions all analytic visible base pixels into4cells with no erosion/exclusions; hidden surfaces and within-cell uniformity remain unmeasured. Shared authored analytic geometry is diagnostic, not reconstructed accuracy.',
    'No verified trained RaDe-GS lamp or reconstructed main proxy; CPU-only disallows training. Unit006 synthetic RGB/camera readiness is not reconstruction.',
    'Unit007 sampled18/458 paths,10 IDs unmeasured; eligible length14.324% of sampled and50.825% raw-visible. Only one of six sampled shade IDs eligible. No all-stroke stability claim.',
    'Inherited17 hidden-profile observations,359 raw-hidden supported observations before unit007 exclusions and shade rim-depth outliers remain. Zero local-edit leakage does not prove baseline hiding correctness.',
    'Unit004 orbit19 ink ratio0.7521462443170939>.75 remains NO_GO; unit004/005 remain DIAGNOSTIC_PREVIEW_ONLY. Current length/ink ratios do not revise the old threshold result.',
    'Base length CLI is bounded to selected434 GT domain; direction/density/width recipes are separate historical operations. Crossing control, general recipe composition and whole-object procedural regeneration remain incomplete.',
    'GT labels and manual directions remain diagnostic upper bounds; no click-assisted/automatic segmentation,H1/H2 comparison,LOD,calibrated tone or24FPS claim.',
    'Current outer batch rc143 after completed layers/orbit/zoom childrc0 is retained; cause undetermined, resumed unstarted media/validation without rerender. Unit006 signed-RGB reader failure/recovery, unit009 preparation failures and historical round001 rc143/PythonUNKNOWN,round002 stdout rc1,round004/012/013 NO_GO and validationUNKNOWN retained.',
    'Old round016 planar width1->2 audit remains NOT_RUN and dispensable for selected whole-object surface-capsule route; never claimed passed.'
]
mincell=min(c['support_fraction'] for r in m['frames'] for c in r['base_coverage']['cells'].values())
progress='完整GT台灯新增可重放的底座长度操作：同75对种子/150条双层路径从请求0.18缩短至0.12，仅重生成底座，保留260灯罩+24支杆。四视角底座墨量降至原66.67%–67.64%，前缘长交叉纠缠减少，仍有可读双层短交叉；目标L1=146.08–191.89，远其他部件/背景新增变化均0。44个静态/轨迹视图的176个冻结覆盖单元通过，8个独立方向层支持通过；冷配方重生成与路径重放复现四视图。更新434路径资产首次补齐24旋转+16缩放+24编辑共64帧并完整精确解码。P1减少一个外观阻塞、补上可操作长度参数和该资产三类演示证据；完整视觉、独立时序与真实重建仍未完成。'
status=dict(stage='completed_base_only_length_cli_and_whole_object_media',execution_state='complete',scientific_verdict='BASE_LENGTH_EDIT_GO_FULL_P1_PARTIAL',
    tests=dict(algorithm_tests_passed=8,independent_checks_passed=len(v['checks']),stills=4,moving_frames=40,combined_base_cells_passed=176,isolated_layer_view_checks_passed=8,unchanged_non_target_paths=284,retained_target_seed_layer_ids=150,cold_target_regeneration_png_exact=True,cold_saved_path_replay_png_exact=True,actual_length018_noop_png_exact=True,decoded_frames=64,actual_visual_review=True,negative_cli_controls_passed=2),
    artifacts=['PROTOCOL.json','SOURCE_LOCK.json','METRICS.json','INDEPENDENT_VALIDATION.json','outputs/edited/asset.json','outputs/edited/recipe.json','cold_request/','references/','layers/','figures/full_lamp_comparison.png','figures/base_comparison.png','figures/all_parts_comparison.png','videos/orbit.mkv','videos/zoom.mkv','videos/edit.mkv','VIDEO_VALIDATION.json','VISUAL_REVIEW.json','DELEGATED_VISUAL_REVIEW.json','EXECUTION_BATCH_INTERRUPTION.json','PRE_EVALUATION_REVIEW.json','HISTORY_REVIEW.json','HISTORICAL_SEAL_AUDIT.json','REPORT_ZH.md'],
    blockers=blockers,outline_milestone='P1/W3/W4/W9; outline5.6,7.1,7.2,7.3,9.2,9.5,9.6,9.7,11.1,14.3',p1_progress=progress,
    claim_status=dict(coding='COMPLETE_FOR_FROZEN_BASE_LENGTH_SCOPE',software='GO',base_length_visual='GO_BOUNDED_EXPOSED_GT',full_visual='NO_GO_RETAINED',reconstructed_input='BLOCKED_NOT_TESTED',full_P1='PARTIAL_NOT_COMPLETE',H1_H2='NOT_TESTED',updated_asset_temporal='NOT_INDEPENDENTLY_AUDITED'),
    protocol_commit='3f4c95f1',implementation_commit='222d2a1e',session_start_jst='2026-10-21T19:15:35.381311+09:00',completed_utc=datetime.now(timezone.utc).isoformat())
write_json(U/'STATUS.json',status)
next_step=dict(action='continue',
    recommended_next_step='ONE shade-only spacing/seed-placement candidate on unit010 outputs/edited named434 asset. Preserve24stem and150length.12base, shade direction0deg/count260/length.32/width/ink/light. Before evaluation freeze deterministic spatially dispersed shade seed placement within each original connected profile-surface band (separate inner/outer/rim bands; preserve original per-band counts), then regenerate only260shade paths with explicit recipe and new geometry revision. Use a bounded candidate-pool/farthest-seed method or equally explicit stratified rule selected before output; exactly oneDEV candidate and no sweep. Freeze analytic shade coverage cells, nonzero isolated edit, rendered overlap/spacing diagnostic with coverage/ink accounting, and full-lamp/crop/orbit/zoom visuals. Keep current accepted base untouched; cold regenerate and record end-to-end latency.',
    hypothesis='Remaining full-object visual blocker is dense parallel shade stacks and uneven bands; redistributing shade seeds at fixed count/length/ink can reduce clustering without emptying the shade or disturbing the now-cleaner stem/base.',
    fixed_controls=['Start explicit unit010434 length.12 asset; preserve174non-target paths/IDs/inks and GT mesh/labels, renderer/depth tolerance/cameras/AA/light unchanged.',
        'One frozen shade-placement candidate only; shade count260, circumferential0deg direction,length.32,width1 and assigned ink fixed. New shade paths are geometry revisions, not same-coordinate claims. No base density/length retry.',
        'Freeze band-specific seed candidate count/order/selection and independent visible-shade height/angular coverage cells before outputs; never let opposite thin inner/outer surfaces compete as one Euclidean neighborhood.',
        'Application gate: visibly reduced stacks in full-lamp views while shape/coverage remain; independent target1 mask2px band,targetL1>10,farother/background<=.02. Report actual ink/support and overlap diagnostic; seed distance alone is not curve spacing proof.',
        'Use exposed DEV0 and diagnostic30/120/210/300,512square2xAA. Freeze bounded24orbit16zoom24edit for chosen named asset, all decode/contacts, no new temporal stability claim without independent correspondence.',
        'Freeze recipe and source/input SHA; cold target regenerate+retained174, saved-path replay, actual latency; CPU<=2/noGPU,serial compute,unit<=45min and scheduling cutoffs. Preserve all old/currentNO_GO and interrupted exit records.'],
    go_no_go=dict(go='Cleaner readable shade with unchanged base/stem, all frozen coverage/isolation/cold gates and complete media; report fullvisual independently.',no_go='Sparse/empty band, new surface-branch errors, visible piles remain, leak or cold mismatch: retain one candidate failure, no threshold/placement sweep.'),
    blockers=blockers,evidence_paths=['STATUS.json','METRICS.json','INDEPENDENT_VALIDATION.json','VISUAL_REVIEW.json','DELEGATED_VISUAL_REVIEW.json','figures/base_comparison.png','figures/all_parts_comparison.png','figures/orbit_all_frames.png','outputs/edited/asset.json','outputs/edited/recipe.json','videos/orbit.mkv','videos/zoom.mkv','videos/edit.mkv'],
    p1_distance_reduced=progress+' 下一步针对占整灯最大面积的灯罩堆叠，直接缩短完整P1的视觉距离，而非继续平面数值证明或底座参数扫选。',estimated_next_minutes=35,estimated_range_minutes=[30,40])
write_json(U/'NEXT.json',next_step)
write_json(U/'INHERITED_FAILURES.json',dict(previous_status_sha256=sha(P/'STATUS.json'),previous_blockers_verbatim=old['blockers'],current_blockers=blockers,preserved_directories=['previous_snapshot/','inherited_failures/'],current_interruption='EXECUTION_BATCH_INTERRUPTION.json',prior_negative_results_unchanged=True))
rows=[]
for r in m['stills']:
    cov=r['candidate_base_coverage'];rows.append(f"| {r['azimuth']}° | {r['edit']['inside_delta']:.6f} | {r['base_hatch_ink_ratio']:.6f} | {100*min(c['support_fraction'] for c in cov['cells'].values()):.2f}% | {100*cov['layers']['0']['whole_base']['support_fraction']:.2f}% / {100*cov['layers']['1']['whole_base']['support_fraction']:.2f}% | 0 / 0 |")
contract=v['evidence']['target_only_length_config_retained284_and_cold_arrays'];history=json.loads((U/'HISTORICAL_SEAL_AUDIT.json').read_text())
report=f'''# Unit010：底座长度控制与更新整灯的三类视频

**底座长度编辑的软件与有限视觉GO；完整视觉P1仍为NO_GO/PARTIAL。** 本轮执行unit009 NEXT的唯一实质步骤：保留同75对种子/150条双层排线，将请求世界长度0.18缩短至0.12。底座前缘长交叉减少，双层短交叉仍可辨；不是重建输入或H1/H2成功。

完整读取BRIEF、851行原大纲及round001/002/016报告/参数/NEXT。协议提交`3f4c95f1`先于任何评价；生成器/8项测试提交`f1f9b58d`，测试rc0；源码审查在评价前修复16帧视频解码接口`96f751f1`，独立验证器`222d2a1e`。随后SOURCE_LOCK冻结所有依赖与输入才渲染。源输入unit009 outputs/edited，868顶点/1728面GT灯、GT三部件和手工方向。所有对象/视角已有曝光，无盲测、训练或数据下载。

CLI只重放原150个面积种子抽样，走其中选定75对/150条曲线，实际300个半路径行走；不生成其余未选曲线。260灯罩+24支杆保留，整灯仍434条。选中seed/layer ID和原墨色不变；目标几何发生版本变化。150条中{contract['changed_target_count']}条实际改变，受提前停止限制的短路径不伪称都达到请求长度。总实际底座弧长{contract['total_target_lengths_world']['baseline']:.9f}→{contract['total_target_lengths_world']['edited']:.9f}世界单位。配置唯一变化为base length。1px线宽、固定世界光照、512²、2xAA、0.006深度容差和原surface-capsule后端不变，无LOD。

| 方位 | 底座内PNG L1 | 底座墨量新/旧 | 四区最低支持 | 两方向层支持 | 远其他/背景变化比例 |
|---|---:|---:|---:|---:|---:|
{chr(10).join(rows)}

主要验收是实际图像和几何覆盖：独立连续解析射线定义base mask、固定2px外带；远其他部件/背景新增变化均0，边界带分别0.05545%、0.15711%、0%、0.20361%。参考实现独立于三角网格渲染，但共享人工几何定义，不代表真实重建精度。

覆盖在结果前冻结：半径0.29划分内/外圈，再按camera眼点的xz投影划分前/后半区，四格分母来自全部可见解析base像素，无腐蚀或候选决定的排除。四静态视角分母1073/656/5099/1932，共8760像素；可见像素排除0。每格至少3个hatch>.1像素且比例≥1%，四静态及40轨迹画面共176格全过；轨迹最低{100*mincell:.2f}%。在四静态视角另分别渲染两个方向层，每层whole-base支持门槛1%，8项通过。层内每格结果仅描述；移动帧只验证合并排线，不能声称每层逐帧覆盖。物理隐藏表面不在可见分母，仍未测。

实际检查整灯四组、放大底座、全部部件、DEV及三类视频全部帧和首中末接触表。底座30/120°的长连接和前缘纠缠减少；210/300°仍有边缘聚集与不均匀空隙，短线更像分散X纹理，未校准色调。灯罩平行堆叠和不均匀带、支杆近边缘叠线仍在，故完整视觉不晋级。独立视觉复核见DELEGATED_VISUAL_REVIEW.json。没有盲偏好实验。

8项必要算法测试、18项独立保存输出审计通过。实际length0.18无操作重生成复现原图，不能误判为有效编辑；16个远部件亮像素黑化控制、3px平移、清空hatch和移除单方向层控制都有预期响应。284条非目标路径逐字段字节相同只作为辅助软件契约。冷请求只有recipe/mesh/retained284/config，配方携带所选种子和墨色、代码及NumPy版本哈希，不依赖目标路径缓存；冷重生成和独立保存路径重放均复现四幅PNG与分层数据。

更新后同一named434资产输出orbit24、zoom16、edit24，512²/12fps/FFV1，共64帧全部解码RGB精确。orbit有24种图像；zoom的对称往返只有8种图像；edit是12帧前态+12帧后态的两个真实状态，无插值。首中末和全帧接触图是视觉检查，不是逐笔触时序对应。当前遮挡/时序质量仍继承unit007的有限覆盖与失败说明。

底座重生成{edit['regeneration_seconds']:.6f}s；模块启动到首幅完整预览{edit['command_to_first_preview_seconds']:.6f}s，到四幅{edit['command_to_all_previews_seconds']:.6f}s；外部命令wall={json.loads((U/'EXECUTION_edited.json').read_text())['wall_seconds']:.6f}s，含校验/读取/重生成/保存/CPU重绘。CPU affinity[0,1]、数值和FFmpeg单线程，串行计算，无GPU；不声称24FPS。

外层批处理在layers/orbit/zoom子进程均rc0完成后返回143；当时media START和log尚不存在，终止原因未确定。EXECUTION_BATCH_INTERRUPTION保留原143，后续单独执行未开始的media/validate/history均rc0，没有重绘或改候选。两项输出保护负控制按预期rc1，历史目标目录没有产生。准备读取路径猜错rc1及账本裸python rc127也保留。unit009 seal的{sum(r['files'] for r in history['checks'])}份文件重新核验相同，历史科学失败和原退出码未覆盖。

{progress}

下一步仅推荐一次灯罩空间分布改进：保持当前支杆和底座配方，固定灯罩数量/长度/方向/墨色，对原surface-band分别冻结分散种子规则后重生成灯罩；用实际间距/重叠、覆盖、整灯图和冷配方判断，不做参数扫选。预算约35分钟，具体冻结约束见NEXT.json。本轮未执行下一步。

可运行命令见工作树LENGTH_CLI_ZH.md，实际精确命令及返回码见REPRODUCE.md。STATUS/NEXT/SEAL与原始图像、掩码、路径、三视频位于当前unit010。真实RaDe-GS灯重建、点击分部、一般操作组合、独立全路径时序和H1/H2仍未完成；旧round016平面宽度审计NOT_RUN且不作为当前路线前置。
'''
(U/'REPORT_ZH.md').write_text(report);(WORK/'docs/partwise_sketch_hatching_v02/REPORT_unit010_ZH.md').write_text(report)
commands=['# Unit010 exact execution receipts','','All compute stages run serially on CPU. Negative controls retain rc1; the outer batch interruption143 is retained separately.','']
for p in sorted(U.glob('EXECUTION_*.json')):
    if p.stem.endswith('_START'):continue
    r=json.loads(p.read_text())
    if 'command' not in r:continue
    commands += [f"## {p.name}",f"Return code: {r['returncode']}; wall seconds: {r['wall_seconds']}",'```bash',shlex.join(r['command']),'```','']
commands += ['The final handoff script only summarizes saved validated outputs. Sealing runs after the report/source commit; runtime stdout is outside the science manifest.']
(U/'REPRODUCE.md').write_text('\n'.join(commands))
print(json.dumps(dict(verdict=status['scientific_verdict'],execution_state='complete',independent_checks=len(v['checks']),decoded_frames=64)))
