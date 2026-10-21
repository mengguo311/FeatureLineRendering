"""Report measured unit008 evidence; keep full-object and research limits explicit."""
from common import *
from datetime import datetime,timezone
import shutil
U=OUT.parent/'unit_008'
read=lambda p:json.loads((U/p).read_text())
v=read('INDEPENDENT_VALIDATION.json');m=read('METRICS.json');media=read('VIDEO_VALIDATION.json');edit=read('outputs/edited/EDIT.json');history=read('HISTORICAL_SEAL_AUDIT.json')
assert v['verdict']=='VALID' and all(x['passed'] for x in v['checks'].values())
assert all(r['quantitative_go'] for r in m['stills'])
assert read('EXECUTION_tests.json')['returncode']==0 and media['decoded_frames']==24 and media['all_rgb_exact']
viewed=['figures/full_lamp_comparison.png','figures/all_parts_comparison.png','figures/edit_all_frames.png','figures/edit_first_middle_last.png']
review=dict(reviewer='root; actual view_image inspection',artifacts=viewed+['dev/before/renders/000.png','dev/after/renders/000.png'],direction_edit_visual='GO_BOUNDED_FOUR_VIEWS',full_visual='NO_GO_RETAINED',observations=['All four whole lamps are fully framed with shade, stem and base readable','Shade hatches visibly rotate from circumferential to diagonal arcs; no gross new cross-part spill seen','Stem dense dark axial fragments, shade uneven gaps/paired stacking, base foreground dark crossings remain','Top opening contains diagonal marks; this is not an occlusion correctness verdict','All24 source frames and first/middle/last viewed; before12 then after12, no tween'],limitations=['Static contact-sheet viewing, not movie playback; exact decoded/source equality independently verified','No new orbit,zoom,stroke temporal,full-occlusion or perceived-flicker claim'])
write_json(U/'VISUAL_REVIEW.json',review)
write_json(U/'DELEGATED_VISUAL_REVIEW.json',dict(reviewer='read-only audit_direction agent; separate actual view_image inspection',artifacts=viewed,direction_edit_visual='GO_BOUNDED_FOUR_VIEWS',full_visual='NO_GO_RETAINED',observations=['All three parts and complete shape readable at30/120/210/300deg','Shade arcs change visibly from near-horizontal to oblique rising arcs','No visible gross new spill; stem and base appear unchanged','Crowded dark stem fragments, uneven shade stacking/gaps, tangled darker base foreground crossings remain','Top-opening diagonal marks are a limitation, not proof of hiding','Contact sheets show00..11 before and12..23 after; first/middle/last agree'],video_file_record=dict(decoded_frames=24,all_rgb_exact=True,distinct_frames=2,decode_returncode=0,header_returncode=1,header_reason='input-only FFmpeg; expected'),limitations=['No movie playback or dynamic flicker judgment'],viewing_errors=[]))
blockers=[
'Full visual NO_GO persists: unit003 dense uneven stem, shade spacing/stacking and base foreground crossing clutter. Direction edit is usable, not a whole-object cleanup.',
'No verified trained RaDe-GS lamp or reconstructed main proxy; CPU-only disallows training. Unit006 synthetic RGB/camera readiness is not reconstruction.',
'Unit007 temporal audit sampled18/458 paths;10 IDs unmeasured, eligible world-length14.324% of all sampled and50.825% of raw-visible. Only one of six sampled shade IDs contributed eligible observations. No all-stroke stability claim.',
'Inherited17 hidden-profile observations,359 raw-hidden supported observations before unit007 exclusions, and shade rim-depth outliers remain. Zero new edit leakage does not establish baseline hiding correctness.',
'Edited+15deg shade has only four exposed still views and a fixed-camera discrete edit video in this unit; its orbit/zoom temporal behavior is NOT newly audited.',
'Unit004 orbit19 ink ratio0.7521462443170939>.75 remains NO_GO. Unit004/005 stay DIAGNOSTIC_PREVIEW_ONLY; no threshold-closing retry.',
'CLI now supports shade absolute direction with deterministic target regeneration plus saved198 non-target paths. Spacing/density,length,crossing target operations and whole-object recipe regeneration remain incomplete.',
'GT geometry,GT labels,manual directions remain diagnostic upper bounds. No real/click-assisted labels, reconstructed lamp,H1/H2 comparison,LOD or24FPS claim.',
'Unit006 original signed-RGB reader failure and disclosed uint8 adapter recovery retained. Historical round001 rc143/PythonUNKNOWN,round002 stdout rc1,round004/012/013 NO_GO and original validation UNKNOWN preserved.',
'Old round016 planar width1->2 audit remains NOT_RUN and dispensable for this bounded whole-object surface-capsule route; it is not claimed passed.'
]
progress='完整458路径GT台灯新增可执行灯罩方向编辑：固定0→15°仅重生成260条灯罩路径，保存父资产/路径版本和确定性配方，198条非目标路径逐字段字节保持。四视角实际图像有非零局部变化且远部件/背景新增泄漏为0，三部件非空；无目标缓存的冷生成和独立保存路径重放均复现四幅输出，24帧编辑视频完整解码。P1从固定路径宽度编辑推进到可复现的局部方向生成操作；完整视觉、重建和动态覆盖缺口仍未关闭。'
claims=dict(coding='COMPLETE_FOR_FROZEN_SHADE_DIRECTION',software='GO',direction_edit_visual='GO_BOUNDED_FOUR_EXPOSED_VIEWS',full_visual='NO_GO_RETAINED',reconstructed_input='BLOCKED_NOT_TESTED',full_P1='PARTIAL_NOT_COMPLETE',H1_H2='NOT_TESTED',edited_path_temporal='NOT_NEWLY_TESTED')
status=dict(stage='completed_target_only_shade_direction_cli',execution_state='complete',scientific_verdict='SHADE_DIRECTION_EDIT_GO_FULL_P1_PARTIAL',tests=dict(algorithm_tests_passed=6,independent_checks_passed=len(v['checks']),views=4,changed_target_paths=v['evidence']['target_only_direction_config_paths_and_cold_arrays']['changed_target_paths'],unchanged_non_target_paths=198,non_target_per_field_bytes_exact=True,cold_target_regeneration_png_exact=True,cold_saved_path_replay_png_exact=True,decoded_frames=24,distinct_video_states=2,historical_manifest_files=sum(r['files'] for r in history['checks']),actual_visual_review=True),artifacts=['PROTOCOL.json','SOURCE_LOCK.json','SOURCE_LOCK_INITIAL.json','PRE_EVALUATION_REFINEMENT.json','METRICS.json','INDEPENDENT_VALIDATION.json','outputs/edited/asset.json','outputs/edited/recipe.json','cold_request/','references/','figures/full_lamp_comparison.png','figures/all_parts_comparison.png','videos/edit.mkv','VIDEO_VALIDATION.json','VISUAL_REVIEW.json','DELEGATED_VISUAL_REVIEW.json','HISTORICAL_SEAL_AUDIT.json','REPORT_ZH.md'],blockers=blockers,outline_milestone='P1/W3/W4/W9; outline5.6,7.2,9.2,9.7,11.1,14.3',p1_progress=progress,claim_status=claims,protocol_commit='8fbeb96a',implementation_commit='f90367eb',validation_refinement_commit='dbd9a27a',session_start_jst='2026-10-21T18:45:06.347737+09:00',completed_utc=datetime.now(timezone.utc).isoformat())
write_json(U/'STATUS.json',status)
next_step='Implement ONE stem-only nested density CLI control on the explicit unit008 baseline selected458 asset: freeze density0.5 selecting24 of48 existing short axial stem paths by a deterministic farthest-seed prefix, retaining shade260/base150 and retained stem IDs/coordinates/inks exactly. Freeze one DEV candidate and coverage bins before evaluation; show four-view whole lamp, enlarged stem and edit video, independent-mask target/leakage, four predeclared visible axial-bin supports, cold config re-selection and preview latency. Treat it as density/seed-budget control, not guaranteed geometric spacing. Do not use rejected unit0048-long-path style or tune toward its .75 cutoff.'
write_json(U/'NEXT.json',dict(action='continue',recommended_next_step=next_step,hypothesis='A nested subset of existing short stem hatches can add a missing user density operation and visibly reduce the dense-stem P1 blocker while preserving surface attachment and non-target assets; fixed axial-bin coverage prevents success by emptying the part.',fixed_controls=['Explicit unit008 outputs/baseline asset458 with original0deg shade, so the stem experiment changes only stem density. Preserve unit008 edited15deg as separate usable recipe output.','One density0.5 value48->24; fixed deterministic seed-prefix selection, oneDEV0 check, no sweep or changed threshold after exposed views','Same mesh,renderer,width,ink,length,shade/base paths, independent analytic masks and fixed2px band','Freeze min nonzero change, leakage<=.02 and per-bin coverage gates before evaluating; failure retained, no retries to close unit004 threshold','Actual whole-lamp4views/edit media and cold re-selection primary; path identity secondary; no new temporal/reconstruction/H1/H2 claim','CPU<=2,noGPU,invocation<=10min,unit<=45min; only new authorized unit outputs'],go_no_go=dict(go='Visible cleaner stem with nonempty required axial coverage, nonzero isolated density edit, deterministic nested selection and cold replay; preserve fullvisual NO_GO if base clutter remains.',no_go='Empty/gapped/unreadable stem, no-op, leakage, lost IDs/inks or cold mismatch; preserve failure without changing density/coverage gate.'),blockers=blockers,evidence_paths=['STATUS.json','METRICS.json','INDEPENDENT_VALIDATION.json','figures/all_parts_comparison.png','outputs/edited/recipe.json','VISUAL_REVIEW.json','videos/edit.mkv'],p1_distance_reduced=progress+' 下一步既新增可操作的疏密控制，也直接处理整灯仍未通过的密集支杆外观；不是重复渲染器数值证明。',estimated_next_minutes=30,estimated_range_minutes=[25,35]))
rows='\n'.join(f"| {r['azimuth']}° | {r['edit']['inside_delta']:.6f} | {r['edit']['boundary_band_fraction']:.6%} | {r['edit']['far_other_parts_fraction']:.6%} | {r['edit']['far_background_fraction']:.6%} | "+'/'.join(str(r['candidate_footprint'][str(p)]['support_pixels']) for p in (1,2,3))+' |' for r in m['stills'])
report=f'''本轮完成一个实质步骤：**完整台灯的灯罩方向编辑 CLI 与目标部件配方冷生成**。判定 `SHADE_DIRECTION_EDIT_GO_FULL_P1_PARTIAL`。P1 可操作性推进；完整视觉仍 NO_GO，重建输入仍阻塞，H1/H2未测试。

已完整读取BRIEF与851行原大纲、unit007交接及继承round001/002/016报告/参数/NEXT。协议提交8fbeb96a先于测试与渲染；实现f90367eb。验证器最后的逐字段字节检查遇到冻结时序冲突，dbd9a27a在指标评价前登记修订；初始锁/验证器保留，生成器、15°角度、相机与阈值未变。准备阶段的路径误读、稀疏git add和缺失python命令返回码另保存在PREPARATION_FAILURES.json。

固定输入是unit003 selected458：260灯罩＋48支杆＋150底座。网格为人工GT，标签和方向均人工给定。唯一变化为相对周向场的绝对偏移0→15°，保留种子1729、长度0.32、步长0.015、线宽1px、512×512、2×采样、深度容差0.006、固定光照与相机。没有参数扫选，DEV0看图后没有调整。四个评价视角均曾曝光，不是新盲测。

实际PNG与独立连续解析曲面掩码给出下列结果。掩码不来自候选三角深度，但与GT网格共享人工几何定义。边界带固定2px。目标L1门槛>10；远其他部件和远背景新增泄漏各≤2%。支持像素用hatch>0.1，仅表示非空图像覆盖。

| 方位 | 目标L1 | 外边界带变化占比 | 远其他部件 | 远背景 | shade/stem/base支持像素 |
|---|---:|---:|---:|---:|---:|
{rows}

四视角门槛全过，完整形体均在画面内。无编辑控制L1=0且失败于非零门槛；16个远部件黑像素注入泄漏占比1，正确失败；3px栅格位移产生非零变化。原始outside_fraction存在约1e-16求和舍入符号，区域逐项质量为精确0，未更改原指标。当前图中解析背景仍有68–100个hatch支持像素，来自既有渲染/边界差异；新增编辑泄漏为0不能证明绝对遮挡正确。

6项必要生成/输入测试和16项独立文件/图像检查通过。零角生成复现原260灯罩，15°改变{status['tests']['changed_target_paths']}条目标路径；logical seed ID保留，目标几何revision变化。198条非目标ID/part/ink/faces/bary逐字段类型、形状和字节一致。数组一致性是隔离回归，主验收是上述真实图像变化、非空覆盖与看图。

编辑目标生成{edit['regeneration_seconds']:.3f}s；模块入口至首次预览{edit['command_to_first_preview_seconds']:.3f}s，至四幅预览{edit['command_to_all_previews_seconds']:.3f}s；外层进程墙钟{read('EXECUTION_edited.json')['wall_seconds']:.3f}s，包含解释器启动。没有实时FPS承诺。具体接口见DIRECTION_CLI_ZH.md。

冷生成在独立进程、冻结源码副本上运行，输入cold_request仅有recipe、mesh、retained198和config；不包含编辑后灯罩路径缓存。它重新生成灯罩并复用非目标路径，四幅PNG及保存图层/路径与编辑输出完全复现。独立保存路径replay也复现四幅输出。这是**目标配方重生成＋非目标保存路径复用**，不是全对象仅凭配置重生成。

新视频24帧、12FPS、FFV1，前12帧为实际原状态，后12帧为实际编辑状态，没有淡化/补间。全24帧解码与源RGB精确相等、恰有两个状态。视频header输入检查的预期rc1保留，编码和解码rc0。根代理和只读审查代理均实际查看四视角全灯、全部部件、全部24帧接触表、首/中/末；灯罩倾斜弧线变化明确，三部件可读。未播放视频，也未借静态接触表宣称无闪烁。

完整视觉NO_GO继续保留：支杆密集竖线、灯罩间距不均/叠线、底座前缘交叉杂乱；顶口斜线没有获得新的遮挡证明。unit004的0.7521462443170939>0.75失败未覆盖；旧17hidden观察、rim-depth离群、unit007低覆盖时序结论与所有退出码保留。新15°路径只做四静帧和固定相机编辑，没有新增orbit/zoom时序验证。RaDe-GS lamp、点击标签、LOD、H1/H2仍缺失。

unit003–007的{status['tests']['historical_manifest_files']}项历史封存文件SHA复核通过。全程两核affinity、数值线程1、FFmpeg线程1、无GPU、无历史/orchestration写入、无push/merge；当前输出和磁盘资源见RESOURCES_FINAL.json。

下一轮建议一个支杆嵌套密度编辑：在本轮baseline458上固定48→24短路径的确定性种子前缀，冻结四个轴向覆盖区间，评价实际整灯清理、编辑隔离、冷重选与耗时。它直接针对密集支杆并补齐疏密操作，不复用unit0048长线失败方案或追逐其阈值；预计25–35分钟，中心30分钟。完整STATUS/NEXT/SEAL及图像、路径、掩码、视频位于{U}。
'''
(U/'REPORT_ZH.md').write_text(report);(WORK/'docs/partwise_sketch_hatching_v02/REPORT_unit008_ZH.md').write_text(report)
shutil.copyfile(WORK/'docs/partwise_sketch_hatching_v02/DIRECTION_CLI_ZH.md',U/'DIRECTION_CLI_ZH.md')
commands=[]
for p in sorted(U.glob('EXECUTION_*.json')):
    if p.stem.endswith('_START'):continue
    r=json.loads(p.read_text());commands.append(dict(receipt=p.name,command=r['command'],returncode=r['returncode'],wall_seconds=r['wall_seconds']))
write_json(U/'EXECUTION_INDEX.json',dict(commands=commands))
print(json.dumps(dict(status=status['scientific_verdict'],checks=status['tests'],report=str(U/'REPORT_ZH.md')),ensure_ascii=False))
