"""Record the completed bounded audit without promoting excluded coverage."""
from common import *
import shutil,subprocess
from datetime import datetime,timezone
U=OUT.parent/'unit_007'
def read(n):return json.loads((U/n).read_text())
def main():
 s=read('TEMPORAL_SUMMARY.json');v=read('INDEPENDENT_VALIDATION.json');video=read('VIDEO_VALIDATION.json');a=s['all']
 assert v['verdict']=='VALID' and s['status']=='GO'
 for p,d in read('SOURCE_LOCK.json')['files'].items():assert sha(p)==d,p
 assert read('INSTRUMENTATION_TEST.json')['go']
 assert (U/'DELEGATED_VISUAL_REVIEW.json').exists()
 inspected=['frames/orbit/0000.png','figures/orbit_all_frames.png','figures/zoom_all_frames.png','figures/zoom_first_middle_last.png','figures/orbit_0012_all_probes.png','figures/orbit_stem_all.png','figures/orbit_base_all.png','figures/controls_part1.png','figures/controls_part2.png','figures/controls_part3.png','figures/coverage_limits_enlarged.png']
 write_json(U/'VISUAL_REVIEW.json',dict(method='Actual view_image review; complete contact sheets plus native frame and detailed crops. No movie playback claim.',inspected=[dict(path=n,sha256=sha(U/n)) for n in inspected],
  findings=['Full lamp and all three parts fit all displayed orbit/zoom frames; silhouette and distinct hatch families are readable.',
   'Shade has unequal spacing and fragments, stem has tightly packed dark axial bars, base has dark crossed intersections at foreground rim. Full-quality NO_GO retained.',
   'Three actual raster fault panels show shifted stroke positions and completely absent ink after drop; normal-direction shift sensitivity is visible.',
   'Enlarged low-shade/high-stem/shortest-base examples expose hidden, boundary and ambiguous exclusions. White isolated output is not counted as success when excluded.',
   'Sample markers can obscure thin ink; separate actual plain crop shown. Display nearest enlargement does not measure stroke width.'],
  verdicts=dict(readable_three_part_demonstration='GO',full_visual_quality='NO_GO_RETAINED',all_stroke_temporal_quality='UNPROVEN',playback_flicker='NOT_REVIEWED')))
 unmeasured=[sid for sid,x in s['per_stroke'].items() if x['status']=='UNMEASURED']
 blockers=[
 'No verified trained RaDe-GS lamp or reconstructed main proxy. CPU-only disallows training; unit006 synthetic RGB/camera input readiness is not reconstruction.',
 'Only18/458 fixed paths were sampled. Ten sampled IDs are UNMEASURED; only one of six sampled shade IDs contributes eligible observations. Eligible time-summed world path length is14.324% of all sampled length,50.825% of raw-visible length. No all-stroke stability claim.',
 'Inherited17 hidden-profile observations and rim-depth outliers unresolved; current359 raw-hidden supported profiles occur before boundary/ambiguity exclusions. Zero retained-hidden support is not a hiding-success verdict.',
 'unit003 dense uneven stem and base foreground crossing clutter retain full visual NO_GO. unit004 orbit19 density0.7521462443170939>0.75 remains NO_GO; unit004/005 preview not promoted.',
 'Current asset CLI only exposes width and saved-path replay. Direction/spacing/length/crossing target-only generators and cold configuration regeneration remain incomplete.',
 'GT geometry/parts and authored directions are diagnostic upper bounds; no real/click-assisted labels, reconstructed lamp, H1/H2 comparison, LOD or24FPS evidence.',
 'unit006 official signed-RGB camera-reader failure remains preserved; full reader/training requires disclosed uint8 adapter in authorized source copy.'
 ]
 progress='已在明确的unit003完整458路径台灯上，完成24帧转台＋12帧缩放、18条分层笔触的真实独立墨迹导出、直接解析可见性、长度计权对应和故障注入。有效子集无异常缺失，遮挡/边界/歧义和10条未测量ID均公开。P1从锚点不变推进到有覆盖边界的真实输出时序证据；未改善本轮外观，也未完成全灯时序或真实重建。'
 verdict='BOUNDED_VISIBLE_SUBSET_TEMPORAL_GO_FULL_P1_PARTIAL'
 claims=dict(coding='COMPLETE',software='GO',temporal_eligible_subset='GO',full_temporal='PARTIAL_LOW_COVERAGE',readable_three_parts='GO',full_visual='NO_GO_RETAINED',reconstructed_input='BLOCKED_NOT_TESTED',full_P1='PARTIAL_NOT_COMPLETE',H1_H2='NOT_TESTED')
 status=dict(stage='completed_whole_lamp_rendered_temporal_audit',execution_state='complete',scientific_verdict=verdict,
  tests=dict(metric_tests_passed=8,instrumentation_checks_passed=9,independent_validation_checks_passed=len(v['checks']),metric_rows=648,sampled_ids=18,unmeasured_ids=unmeasured,eligible_observations=4079,total_observations=28548,missing_eligible_observations=0,eligible_over_all_world=a['eligible_over_all_world'],eligible_over_raw_visible_world=a['eligible_over_raw_visible_world'],decoded_frames=36,historical_manifest_files=916,visual_review=True),
  artifacts=['PROTOCOL.json','SOURCE_LOCK.json','SOURCE_LOCK_INITIAL.json','PRE_EVALUATION_REFINEMENT.json','SAMPLE_SELECTION.json','TRAJECTORIES.json','TEMPORAL_SUMMARY.json','METRIC_ROWS.json','raw/','isolated/','frames/','videos/orbit.mkv','videos/zoom.mkv','INDEPENDENT_VALIDATION.json','INSTRUMENTATION_TEST.json','VIDEO_VALIDATION.json','VISUAL_REVIEW.json','DELEGATED_VISUAL_REVIEW.json','INHERITED_FAILURES.json','figures/coverage_limits_enlarged.png','REPORT_ZH.md'],
  blockers=blockers,outline_milestone='P1/W4/W9; outline5.8,9.5,11.1,14.3',p1_progress=progress,claim_status=claims,
  protocol_commit='25f2993c',implementation_commit=read('SOURCE_LOCK.json')['commit'],completed_utc=datetime.now(timezone.utc).isoformat(),session_start_jst='2026-10-21T18:23:25.382290+09:00')
 write_json(U/'STATUS.json',status)
 next_step='Implement ONE usable part-direction edit CLI extension on the named unit003 selected458 asset: regenerate only shade from an explicit deterministic generator recipe and record parent asset/path revision lineage, while preserving stem48 and selected base150 paths/IDs/inks byte-for-byte. Freeze one modest direction change on DEV before evaluation, then show actual full-lamp before/after and edit video, independent-mask nonzero target/leakage and nonempty coverage, cold config regeneration/replay, and command-to-preview latency. Keep unit004 rejected style and all temporal exclusions; no new renderer proof cycle, TEST tuning, training or H2.'
 nxt=dict(action='continue',recommended_next_step=next_step,hypothesis='With bounded actual motion evidence available, a user still cannot request a new hatch direction from the saved asset. Target-only deterministic regeneration adds a missing core P1 operation while retaining complete-object identity and edit isolation.',
  fixed_controls=['Explicit unit003 inputs/selected.npz458 asset; unchanged mesh/renderer,width,ink and other-part198 paths','One prescribed DEV direction edit; freeze angle,generator,seed,lineage,trajectory and gates before actual evaluation','Independent analytic masks and fixed2px band; target L1>10, far other/background leakage<=.02, each part nonempty; no-edit must fail nonzero-edit gate','Keep unit004/005 DIAGNOSTIC_PREVIEW_ONLY and original density NO_GO; no threshold-closing retry on exposed frame19','All current paths/views are exposed diagnostics. Do not claim new blindTEST, reconstructed input or H1/H2','CPU<=2,noGPU,no historical or orchestration writes; ordinary invocation<=10min and unit<=45min'],
  go_no_go=dict(go='One actual CLI direction edit regenerates only target, gives visible nonzero target output with bounded independent-mask leakage, identical untouched part paths, reproducible cold configuration generation and saved full-lamp preview/video. Record total edit+render latency.',no_go='Wrong/non-isolated regeneration, no-op edit, leakage or emptying, unreadable output or failed cold replay: retain failure and do not promote fullP1; no parameter sweep.'),
  blockers=blockers,evidence_paths=['STATUS.json','TEMPORAL_SUMMARY.json','INDEPENDENT_VALIDATION.json','DELEGATED_VISUAL_REVIEW.json','figures/coverage_limits_enlarged.png','videos/orbit.mkv','videos/zoom.mkv','/mnt/hdd1/u00134/partwise_sketch_hatching_p1_v02/units/unit_005/STATUS.json'],
  p1_distance_reduced=progress+' 下一步把固定资产变为可执行的方向编辑，补上完整对象P1的可操作性缺口，不把当前有限时序GO误当全对象完成。',estimated_next_minutes=30,estimated_range_minutes=[25,35],updated_utc=datetime.now(timezone.utc).isoformat())
 write_json(U/'NEXT.json',nxt)
 timings=[read(f'frames/{seq}/{c["frame"]:04}.json')['render_seconds'] for seq,cameras in read('TRAJECTORIES.json').items() for c in cameras]
 r=dict(root_free_bytes=shutil.disk_usage(WORK).free,hdd_free_bytes=shutil.disk_usage(U).free,task_output_bytes=sum(p.stat().st_size for p in U.parent.rglob('*') if p.is_file()),cpu_affinity=sorted(os.sched_getaffinity(0)),numeric_threads=1,gpu=False,render_seconds_median=float(np.median(timings)),render_seconds_p95=float(np.percentile(timings,95)))
 assert r['root_free_bytes']>=2**30 and r['hdd_free_bytes']>=10*2**30 and r['task_output_bytes']<20*2**30
 write_json(U/'RESOURCES_FINAL.json',r)
 lines=['# unit007：完整台灯实际笔触时序审计','',f'结论：**{verdict}**。软件与冻结有效子集通过；完整视觉质量、全笔触时序与真实重建均未通过或未完成。',
 '',progress,'',
 '本轮完整阅读BRIEF、原大纲851行及旧round001/002/016报告、参数与NEXT，执行unit006建议的一项完整台灯时序审计。旧平面width审计仍为NOT_RUN/不属于当前路线前置，不伪报通过。全部结果只针对已曝光的人工GT旋转体，非RaDe-GS重建、非自动标签、非H1/H2研究结论。',
 '',
 '协议25f2993c在真实评测前冻结。必要指标测试8项通过；实现7aa4709a后，在尚未运行orbit/zoom/时序评测时，源码复核发现故障事件可能跨相邻对抵消，提交4aa26840把控制断言绑定到实际注入的相邻对。科学协议、阈值、路径、采样与相机均未改。SOURCE_LOCK_INITIAL/source_snapshot_initial和PRE_EVALUATION_REFINEMENT保留原版；最终SOURCE_LOCK在全部应用评测前冻结。',
 '',
 '输入明确为unit003/inputs/selected.npz：458条路径（灯罩260、支杆48、底座150），即已接受底座清理后的unit004比较基线；不是608条mixed原始集，也不是被拒的unit004支杆候选。网格868顶点/1728面、GT部件和周向/轴向/短交叉规则固定；世界锚点为face ID＋重心坐标。',
 '',
 '渲染固定512²、2×超采样、1px排线、0.006世界单位深度容差、visible_centerline轮廓及原墨量/光照，无LOD或重采样。独立复制的renderer_probe_unit007只导出18条实际逐ID墨迹图层，再按原maximum union合回全图；完整场景深度参与自遮挡和部件遮挡。与未修改原renderer的全图/各层和三个逐ID结果一致，仅作为实现回归，不是应用主门槛。',
 '',
 '转台24帧az=15i°、仰角20°、距离4.5；缩放12帧az30°、仰角20°、距离4.8−0.8cos(2πi/11)，实际范围4.0–5.567594。两者均重新渲染完整458路径。每部件几何选6ID：最短、最低、最高及均值周向最接近0/120/240°，顺序去重、ID破同分；选择未查看候选输出。所有旧视角/路径已曝光，不是新留出TEST。',
 '',
 '独立连续旋转体解析射线直接在样点UV求交，不插值候选网格深度；独立像素标签只用于固定2px部件边带。仍共享人工形状定义，且0.006容差容纳网格/解析曲面差异。每ID固定世界等弧长中点，n=clip(ceil(L/.008),8,128)，权重L/n；世界权重精确守恒，投影长度为采样区间弦长近似。固定2px图像/端点余量与4px非局部自投影歧义排除，不按实际墨迹决定资格。',
 '',
 '实际uint8逐笔触墨迹在±2px、0.25px步长法向剖面测定位，存在阈值0.05。共同可见对应按同ID同材料样点比较相邻帧；正常遮挡不计为异常消失。缺失不进入零误差捷径，而留在长度分母；法向残差仍含AA及法向旋转影响，不测完整切向漂移。没有orbit末帧到首帧接缝评价，也没有电影播放或主观无闪烁结论。',
 '',
 '|序列/部件|有效/原始可见长度|有效/全部抽样时空长度|位置P95 px|相邻残差P95 px|有效缺失率|冻结结论|',
 '|---|---:|---:|---:|---:|---:|---|']
 for seq,g in s['per_sequence'].items():
  for part,x in g['per_part'].items():
   lines.append(f'|{seq}/{part}|{100*x["eligible_over_raw_visible_world"]:.2f}%|{100*x["eligible_over_all_world"]:.2f}%|{x["centroid_abs_px"]["p95"]:.4f}|{x["temporal"]["normal_residual_change_abs_px"]["p95"]:.4f}|{x["missing_world_fraction"]:.1%}|{x["status"]}|')
 lines+=['',f'全部648个ID/帧记录、28,548观察中有效4,079；独特曾有效材料样点306。累计共同可见对应3,317。总体位置P95={a["centroid_abs_px"]["p95"]:.6f}px、相邻残差P95={a["temporal"]["normal_residual_change_abs_px"]["p95"]:.6f}px，缺失/异常消失/重现均0。最大相邻残差0.801498px，超过0.75但冻结门槛是P95，不能隐去最大值。',
 '',
 '**覆盖是关键限制：有效长度仅占全部抽样时空路径长度14.324%，占原始解析可见长度50.825%，不是全灯表面积覆盖。18/458路径被抽样，只有8ID整体可测，10ID为UNMEASURED；灯罩只有最高位置的一条ID产生有效样点。冻结部件汇总GO不能冒充六条灯罩路径都成功。** 全类别观察为可见4079、隐藏13625、歧义1346、边界9498、画外0。完整排除量、逐ID/逐帧原始数据已保存。',
 '',
 '未测量ID：'+', '.join(unmeasured)+'。图figures/coverage_limits_enlarged.png在评测后解释低位灯罩、高位被遮挡支杆和最短底座的限制，不构成新测试或改变排除。',
 '',
 '当前359个原始hidden剖面存在墨迹，经过固定边界/歧义排除后保留hidden支持0；这不证明隐藏泄漏解决。同ID其他段投影、边界覆盖、几何近似仍可贡献墨迹。继承17个隐藏剖面、上缘深度离群点均保留，不能拿0覆盖统计替换旧失败。',
 '',
 '独立验证8类检查通过：重新汇总全部覆盖与时序存在、逐部件实际PNG no-edit/横纵3px漂移/删墨、按确定性共同可见相邻对删除后一帧并检测dropout，以及完整媒体和来源检查。三部件横纵漂移均有响应，删墨缺失率均1；控制原图/故障图及每项指标保存于controls/independent。无编辑检查是重复实际PNG评价；仪表化回归另有实际重渲染。',
 '',
 'FFV1视频为12fps：orbit24帧/24个不同图像，zoom12帧/6个不同图像（往返对称距离，非伪运动）。producer与独立validator各完整解码36帧，RGB均与PNG一致。全帧及首/中/末接触图、每部件全帧局部图、18ID全帧剖面图均保存。没有新编辑视频，本轮camera-only；旧编辑证据只继承不升级。',
 '',
 '实际目视：全灯不裁切、三部件和三种风格可辨；放大/缩小有效。支杆仍为密集不均竖线，底座前缘有深交叉，灯罩有碎短线和不均间距。主代理与独立助手实际查看图片；助手23张图的路径/hash在DELEGATED_VISUAL_REVIEW。可读展示GO，完整视觉质量NO_GO保留；不是播放无闪烁证明。',
 '',
 f'36帧含probe导出的渲染时间median={r["render_seconds_median"]:.3f}s、P95={r["render_seconds_p95"]:.3f}s，CPU离线，不是24FPS或性能改进。独立校验unit003358项、unit006558项历史文件/提交源码，共916项一致；旧目录没有写入。全部科学执行收据rc0。两个辅助裸python命令因不存在返回127，未执行科学计算，显式授权解释器重试，记录于ENGINEERING_EVENTS；未掩盖。',
 '',
 '完整失败继承见INHERITED_FAILURES及inherited_failures：unit004的orbit19密度0.7521462443170939>0.75仍NO_GO，unit004/005仍为诊断预览；旧round001外层143/子退出UNKNOWN、round002 rc1、round004/012/013 NO_GO、unit006初始相机reader INVALID rc1及有条件适配恢复均未改。',
 '',
 '唯一下一步：为unit003458路径资产增加可执行的灯罩方向编辑CLI，保存生成配方与父子路径版本，只重生成灯罩，保留非目标198条路径/ID/墨量。DEV冻结一个方向修改后检查非零目标、独立掩码泄漏、非空全灯、编辑视频、冷配置重生成和完整命令到预览延迟；预计25–35分钟，推荐30分钟。它补上完整对象P1的用户操作缺口，不继续纯时序证明链，不依据已曝光0.752146结果重试支杆阈值，不训练或启动H2。',
 '',
 '源码/文档仅授权分支worktree；重输出仅unit007。CPU affinity[0,1]、数字/ffmpeg各1线程且串行，无GPU、凭据/环境输出、下载、push、merge；资源见RESOURCES_FINAL，满足根盘>=1GiB、HDD>=10GiB与任务20GiB上限。STATUS/NEXT/SEAL与manifest位于当前unit；runtime stdout/stderr在science manifest外、收据保留hash。']
 report='\n'.join(lines)+'\n';(U/'REPORT_ZH.md').write_text(report);(WORK/'docs/partwise_sketch_hatching_v02/REPORT_unit007_ZH.md').write_text(report)
 print(json.dumps(native(dict(verdict=verdict,claims=claims,resources=r))))
if __name__=='__main__':main()
