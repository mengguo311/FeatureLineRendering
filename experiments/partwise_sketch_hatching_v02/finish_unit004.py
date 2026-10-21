"""Write evidence-derived report/handoff, preserving any failed gates."""
from common import *
import shutil
import shlex
from datetime import datetime, timezone

OUT=OUT.parent/'unit_004'
def read(name):return json.loads((OUT/name).read_text())

def main():
    assert not (OUT/'SEAL.json').exists()
    m=read('METRICS.json');v=read('INDEPENDENT_VALIDATION.json');cold=read('COLD_REPLAY.json')
    visual=read('VISUAL_REVIEW.json');lock=read('SOURCE_LOCK.json');history=read('HISTORICAL_SEAL_AUDIT.json')
    stages=['prepare','tests','dev','freeze','stills','orbit','zoom','media','cold_replay','validation','history_audit']
    executions={name:read(f'EXECUTION_{name}.json') for name in stages}
    cold_go=all(cold[key] for key in ('regenerated_digest_exact','candidate_png_exact','baseline_png_exact'))
    density_contract_go=m['scientific_gates']['all52_image_pairs_quantitative_go']
    software_go=(v['verdict']=='VALID' and all(m['scientific_gates'][name+'_local_edit_go'] for name in ('stills','orbit','zoom'))
        and all(m['scientific_gates'][name+'_whole_object_coverage_go'] for name in ('stills','orbit','zoom'))
        and m['scientific_gates']['metric_controls_go_four_stills'] and cold_go
        and history['valid'] and all(e['returncode']==0 for e in executions.values()))
    visual_go=visual['stem_visual_verdict'].startswith('GO') and visual['whole_lamp_readability_verdict'].startswith('GO')
    verdict=('GT_STEM_STYLE_AND_THREE_VIDEO_GO_BOUNDED' if software_go and visual_go and density_contract_go
             else 'STEM_VISUAL_GO_FROZEN_DENSITY_NO_GO' if software_go and visual_go and not density_contract_go
             else 'STEM_STYLE_NO_GO' if v['verdict']=='VALID' else 'ENGINEERING_INVALID')
    blockers=[
        'Frozen density contract NO_GO: orbit frame19/az285 stem ink ratio0.7521462443170939 exceeds predeclared0.75; no retuning or threshold waiver. Candidate remains a labeled diagnostic preview.',
        'No verified reconstructed lamp: authored GT mesh/parts and manual directions remain a diagnostic upper bound; CPU-only blocks new training.',
        'Inherited17 hidden-profile observations, rim-depth outliers and nine-ID temporal coverage limitations unresolved; raw frame differences/full decode do not establish jitter or flicker performance.',
        'Visible residual base front-edge dark crossings/uneven patches and shade raster/stacking irregularity remain; bounded engineering readability is not polished hand-drawn quality.',
        'Current generator is deliberately restricted to the authored straight96-sector cylinder and one fixed style; no general-mesh spacing or equal-darkness claim.',
        'Legacy edit_asset CLI/common.OUT still targets unit001 and old inputs; the418-path diagnostic preview needs an explicit input/output editing interface before practical reuse.']
    progress=('Replaced the conspicuous clustered short-stem bars with8 separated long axial paths while retaining260 shade and150 accepted base paths. '
        'The complete three-style lamp now has refreshed orbit/zoom/local-edit outputs, actual independent-mask isolation/coverage evidence and cold target-only regeneration. '
        'This closes the visible stem obstacle and supplies the missing three-style zoom evidence, while full reconstructed-input/visibility/usability P1 remains incomplete.')
    if not density_contract_go or not software_go or not visual_go:progress+=' Frozen density NO_GO is retained; the418-path output is a diagnostic preview, not an all-gates accepted style.'
    media={name:v.get('evidence',{}).get(f'complete_{name}_video_decode',{}) for name in ('orbit','zoom','edit')}
    timings={}
    for name in ('orbit','zoom'):
        times=[read(f'frames/{name}/{i:04}.json')['seconds'] for i in range(24)]
        timings[name]=dict(frame_seconds_median=float(np.median(times)),frame_seconds_p95=float(np.percentile(times,95)))
    timings.update(generation_seconds=cold['generation_seconds'],regenerate_and_render_seconds=cold['regenerate_and_render_seconds'],
        cpu_affinity=[0,1],numeric_threads=1,gpu=False,not_realtime=True)
    write_json(OUT/'TIMING_SUMMARY.json',timings)
    status=dict(stage='completed_stem_style_and_three_video_validation',execution_state='complete' if v['verdict']=='VALID' else 'invalid',
        scientific_verdict=verdict,tests=dict(stem_contracts=dict(tests=3,passed=3 if executions['tests']['returncode']==0 else None,returncode=executions['tests']['returncode']),
            artifact_validation=v['verdict'],artifact_checks=len(v['checks']),all52_numeric_pairs_go=m['scientific_gates']['all52_image_pairs_quantitative_go'],
            metric_controls=m['scientific_gates']['metric_controls_go_four_stills'],cold_snapshot_replay=cold_go,
            video_decoded_frames={name:media[name].get('decoded_frames',0) for name in media},
            historical_manifest_files=history['files_checked'],historical_manifest_valid=history['valid'],
            preserved_engineering_failure='Delegated syntax invocation python alias missing rc127; corrected absolute interpreter rc0; no scientific failure relabeled'),
        artifacts=['PROTOCOL.json','SOURCE_LOCK.json','CONFIG.json','STYLE.json','GENERATION.json','inputs/selected.npz',
            'METRICS.json','INDEPENDENT_VALIDATION.json','COLD_REPLAY.json','VISUAL_REVIEW.json','DELEGATED_VISUAL_REVIEW_STILLS.json',
            'DELEGATED_VISUAL_REVIEW_MEDIA.json','figures/full_lamp_comparison.png','figures/stem_comparison.png',
            'figures/orbit_all_frames.png','figures/zoom_all_frames.png','figures/edit_all_frames.png',
            'videos/orbit.mkv','videos/zoom.mkv','videos/edit.mkv','FROZEN_GATE_FAILURES.json','figures/failure_orbit_019.png','REPORT_ZH.md'],blockers=blockers,
        outline_milestone='P1 complete-object GT engineering slice: three-style readability and three-video refresh; full P1 not complete',
        p1_progress=progress,claim_status=dict(coding='COMPLETE_FOR_FROZEN_SCOPE',software='GO_ISOLATED_REGENERATION_AND_MEDIA' if software_go else 'NO_GO',
            frozen_density_contract='GO' if density_contract_go else 'NO_GO',candidate_promotion='DIAGNOSTIC_PREVIEW_ONLY' if not density_contract_go else 'BOUNDED_GO',
            stem_visual=visual['stem_visual_verdict'],whole_lamp_readability=visual['whole_lamp_readability_verdict'],
            full_P1='PARTIAL_NOT_COMPLETE',reconstructed_input='BLOCKED',independent_temporal='NOT_ESTABLISHED',H1_H2='NOT_TESTED'),
        historical_failures='Original stdout rc1/143/UNKNOWN,round004/012/013 NO_GO,rim outliers,unit001/002 full visual NO_GO retained unchanged.',
        session_started_jst='2026-10-21T17:33:56.378752+09:00',completed_utc=datetime.now(timezone.utc).isoformat(),protocol_source_commit=lock['git_commit'])
    write_json(OUT/'STATUS.json',status)
    next_step=dict(action='continue',
        recommended_next_step='One explicit-asset part-editing CLI unit: expose separately named unit003 baseline and unit004418-path diagnostic preview with required input/output paths and retained verdict metadata. Freeze one real edit on the preview: part1 shade screen width1.0 to1.5px. Save config,paths,actual full-lamp render and command-to-preview latency; validate four exposed views for nonzero target response,fixed2px independent-mask leakage,all-part nonempty coverage/full shape,and one cold saved-config replay. Preserve unit004 density NO_GO without automatic promotion or a threshold-closing style sweep; the stem thinning ratio gate is inapplicable to a shade width edit. Do not reload original608 paths or write historical units; no H2/planar proof.',
        hypothesis='Explicit asset/config handling can turn the readable three-style diagnostic preview into a usable local-edit asset while preserving its failed density contract and keeping untouched styles stable. This usability work is independent of forcing0.752146 below0.75.',
        fixed_controls=['Explicit unit003 baseline and unit004 diagnostic preview identities; preserve their different verdicts','same GT labels/manual directions provenance','unchanged parts IDs/anchors/ink/config',
            'visible_centerline512x512,2xAA,.006 depth tolerance,1px baseline hatches,.8px contours',
            'fixed2px independent masks and nonempty hatch coverage; exposed views remain exposed',
            'historical failures/17 hidden observations and temporal/reconstruction blockers remain visible'],
        go_no_go=dict(go='The concrete shade-width CLI edit produces intended nonzero visible target change without far-part/background leakage above2%; all parts remain nonempty/full shape visible; untouched styles and saved-input provenance retained; cold replay and full command-to-preview latency recorded.',
            no_go='Silent reset to original asset, wrong output destination, empty target, failed isolation, or suppressed unit004 density NO_GO: retain artifacts and stop promotion; do not tune on evaluation.'),
        blockers=blockers,evidence_paths=['STATUS.json','METRICS.json','VISUAL_REVIEW.json','COLD_REPLAY.json','inputs/selected.npz',
            'figures/full_lamp_comparison.png','videos/orbit.mkv','videos/zoom.mkv','videos/edit.mkv'],
        p1_distance_reduced=progress+' The next CLI step closes practical part-selection/edit/save/replay while retaining quality verdict metadata; it does not reinterpret the failed density bound.',
        estimated_next_minutes=25,estimated_range_minutes=[20,30],updated_at_utc=datetime.now(timezone.utc).isoformat())
    if not software_go or not visual_go:
        next_step['recommended_next_step']='One bounded diagnosis of the recorded unit004 failed gate, preserving this candidate and frozen thresholds. Use its actual whole-lamp failing views and masks; do not promote candidate or start H2. Scope the repair from the measured failure before running it.'
    write_json(OUT/'NEXT.json',next_step)
    resource=dict(root_free_bytes=shutil.disk_usage(WORK).free,hdd_free_bytes=shutil.disk_usage(OUT).free,
        task_unit_output_bytes=sum(p.stat().st_size for p in OUT.parent.rglob('*') if p.is_file()))
    assert resource['root_free_bytes']>=2**30 and resource['hdd_free_bytes']>=10*2**30 and resource['task_unit_output_bytes']<20*2**30
    write_json(OUT/'RESOURCES_FINAL.json',resource)
    table='\n'.join(f"| {r['azimuth']} | {r['edit']['inside_delta']:.3f} | {r['stem_ink_ratio']:.4f} | {r['stem_support_ratio']:.4f} | {100*r['candidate_footprint']['2']['support_fraction']:.2f}% | {100*r['edit']['boundary_band_fraction']:.4f}% | {100*r['edit']['far_other_parts_fraction']:.4f}% / {100*r['edit']['far_background_fraction']:.4f}% |" for r in m['stills'])
    summaries='\n'.join(f"- {name}: {m[name+'_summary']['quantitative_go_frames']}/{m[name+'_summary']['expected_frames']}图像对满足冻结门槛；支杆墨量比{m[name+'_summary']['stem_ink_ratio_min']:.4f}–{m[name+'_summary']['stem_ink_ratio_max']:.4f}，绝对支持最低{100*m[name+'_summary']['candidate_support_fraction_min']:.2f}%。" for name in ('stills','orbit','zoom'))
    decoded='；'.join(f"{name}={media[name].get('decoded_frames',0)}帧、{media[name].get('distinct_frames',0)}个不同图像" for name in media)
    failed=[dict(sequence=name,measurement=row) for name in ('stills','orbit','zoom') for row in m[name] if not row['quantitative_go']]
    write_json(OUT/'FROZEN_GATE_FAILURES.json',dict(verdict='NO_GO' if failed else 'GO',failed_pairs=failed,
        interpretation='Actual raster density guard failure, not numerical-equality or engine failure; fixed criterion preserved',
        changed_after_evaluation=False,diagnostic_preview_only=bool(failed)))
    from run_unit002 import contact
    contact([OUT/'frames/baseline/0019.png',OUT/'frames/orbit/0019.png'],
        ['Baseline | orbit19 az285','Candidate | ink ratio0.752146 >0.75'],OUT/'figures/failure_orbit_019.png',columns=2,thumb=512)
    report=f'''# unit004：完整台灯的长疏支杆与三视频刷新

结论：**{verdict}**。仅执行unit003 NEXT的一个实质步骤：把支杆48条短轴向线替换为8条均匀周向长线，固定已接受的灯罩260条和底座150条。整灯458→418条；新支杆使用新的版本ID，未把几何变化伪装成旧笔触身份不变。软件、实际视觉、重建输入和研究假设分别判定，完整P1仍未完成。

**冻结密度门槛未全部通过。** 52组实际图像对中51组通过；旋转第19帧az285的支杆墨量比0.7521462443高于上限0.75，即墨量减少24.7854%，未达到预定至少25%。这是实际hatch墨量合同失败，不是浮点严格相等或程序中断。全部编辑隔离、非空/完整形体和媒体检查通过；不能用这些通过或视觉改善改写该NO_GO。失败原图/原始数组仍在，另保存FROZEN_GATE_FAILURES.json及failure_orbit_019.png；无调参、无放宽门槛。418条候选仅标为诊断预览。

已完整读取BRIEF、851行原大纲和继承round001/002/016报告/原参数/NEXT。当前工作对应大纲§5.6/5.8、§7.1、§9.2/9.6和§11.1。旧有限平面width1→2审计仍NOT_RUN；不再是此整灯路线前置条件。

协议在DEV前写入；协议/实现提交`{lock['git_commit']}`。唯一候选在DEV az0上实际查看，未调参；源码/输入锁于`{lock['frozen_utc']}`，先于四视角与轨迹评价。全部资产/视角属于已曝光GT诊断，没有新的留出研究TEST。基线和历史输出只读。

支杆沿96分段圆柱的扇区j=1+12k，以边内插比例0.37选种子，世界高度0.875，沿旧v2轴向行走±0.675，固定高度范围0.20–1.55。8条路径全部保持三角面+重心坐标，每条实际长度达到1.35；世界光照墨量公式沿用旧规则。仅有此受限圆柱实现，不宣称任意网格参数化/Poisson间距。路径数、长度和位置共同改变，结果归于长疏风格操作，不单独归因于密度。暗度有意降低，不是等暗度比较。

保持512²、2×超采样、1px排线、0.8px轮廓、0.65px实体环、0.006世界深度容差和visible_centerline后端。其owner平面跨线宽延伸、有限采样和轮廓端帽近似均仍在。GT网格/GT部件/人工方向不能冒称RaDe-GS重建或自动分部。

主要数值验收使用实际保存PNG及独立连续旋转体射线部件掩码：支杆内L1>10，固定2px外带，远其他部件/背景各≤2%；hatch层墨量比0.15–0.75、支持保留比≥0.15、绝对支杆支持≥5%，三部件排线非空且全形体留在画内。掩码实现独立于三角形光栅，但共享人工GT形状配方。路径数组固定仅作次要回归。4个投影高度分段的支杆支持另存描述，不用新增门槛救结果。

| 方位° | 支杆内L1 | 支杆墨量比 | 支持保留比 | 支杆掩码支持 | 外部2px带变化占比 | 远部件 / 背景 |
|---|---:|---:|---:|---:|---:|---:|
{table}

{summaries}

三项必要算法测试返回{executions['tests']['returncode']}；独立制品审计为{v['verdict']}，{len(v['checks'])}项文件/帧/媒体检查（不是独立研究样本）。no-edit拒绝非零门槛、远灯罩16像素注墨和3px栅格漂移控制均实际运行；控制总判定为{m['scientific_gates']['metric_controls_go_four_stills']}。锚点、均匀角间距、独立圆柱距离和非目标410条记录见INDEPENDENT_VALIDATION.json。

旋转24帧az=15i，缩放24帧距离4.0+0.8(1−cos(2πi/24))、方位30°，仰角均20°；每帧从同一固定资产重新投影/深度测试。缩放基线也实际重渲染。编辑前12帧旧48条支杆、后12帧新8条，两个实际状态，无图像插值。三个视频12fps、FFV1无损，完整解码结果：{decoded}。首/中/末和全帧接触图已保存并实际查看。解码一致仅证明文件完整性，原始帧差含正常投影/遮挡/AA变化，不是独立抖动/闪烁成绩。

实际视觉判定：支杆{visual['stem_visual_verdict']}，整灯可读性{visual['whole_lamp_readability_verdict']}。密集短黑条已成为分开的连续长轴向线；三种部件风格和整灯形体保留。底座前缘较深X形、局部疏密不均及灯罩细线采样/叠线缺陷仍公开。独立静帧/媒体审阅另存两份DELEGATED_VISUAL_REVIEW文件。仅是有界GT工程示范，不是精致手绘质量或用户偏好研究。

冷快照新进程重新生成8条支杆并渲染az30：路径/候选PNG/基线PNG重放结果{cold_go}；生成{cold['generation_seconds']:.4f}s，生成加整灯重绘{cold['regenerate_and_render_seconds']:.3f}s。orbit单帧median/P95={timings['orbit']['frame_seconds_median']:.3f}/{timings['orbit']['frame_seconds_p95']:.3f}s，zoom={timings['zoom']['frame_seconds_median']:.3f}/{timings['zoom']['frame_seconds_p95']:.3f}s；CPU离线，不声称24FPS。

历史unit003完整manifest的{history['files_checked']}个文件校验结果{history['valid']}。保留旧stdout失败rc1/143/UNKNOWN、round004/012/013 NO_GO、灯罩上缘深度离群、unit001/002视觉NO_GO及17个隐藏剖面观察。此次助手语法检查首次使用不存在的python别名返回127，绝对路径重试返回0，已单独保存工程记录；不改写为首次成功。FFmpeg只读流头检查预期rc1（未指定输出），实际解码要求rc0，二者分开记录。

距P1的缩短：移除了剩余显眼的支杆堆墨障碍，并补齐该三风格诊断预览的缩放，使整灯旋转/缩放/局部编辑都有可复查输出。真实重建输入、可靠隐藏/独立时序证据和可复用编辑接口仍待完成；H1/H2未测试。下一步只推荐一个显式资产配置CLI单元，分别保留unit003基线和unit004诊断预览及其失败元数据，冻结一个灯罩线宽1.0→1.5px的实际编辑，验证非零目标变化、独立掩码泄漏、覆盖、保存/重放和命令到预览延迟，预计20–30分钟，推荐25分钟。该应用步骤不依赖把0.752146调到0.75以下；本次密度NO_GO永久保留，不作为全门槛接受的风格自动推广；支杆稀疏化墨量比例门槛不用于灯罩宽度编辑。

所有科学写入仅unit004，源码/文档仅授权分支worktree；CPU affinity[0,1]、数值/ffmpeg各1线程、无GPU/训练/下载、无push/merge。磁盘/任务总量见RESOURCES_FINAL.json；原始命令和返回码见EXECUTION收据及REPRODUCE.md。STATUS/NEXT/SEAL与显式SHA清单位于`{OUT}`；runtime stdout/stderr在科学manifest外，由收据hash绑定。
'''
    (OUT/'REPORT_ZH.md').write_text(report)
    commands='\n\n'.join(f"{name}: rc={e['returncode']}, wall={e['wall_seconds']:.3f}s\n\n```bash\n{shlex.join(e['command'])}\n```" for name,e in executions.items())
    reproduce=f'''# unit004 exact execution record

Authorized branch: partwise-sketch-hatching-p1-v02. Frozen commit: {lock['git_commit']}.
Output: {OUT}. Input/source SHA: SOURCE_LOCK.json. Protocol: PROTOCOL.json.
These are recorded commands, not permission to overwrite this sealed unit. A future replay requires a newly authorized output directory and an explicit adapted runner.

Every science child was wrapped by receipt_unit004.py, taskset0,1, CUDA disabled, numerical libraries1 thread, timeout590s. FFmpeg uses1 thread. stdout/stderr remain outside the science manifest and have receipt SHA. The delegated syntax-only rc127 failure and corrected rc0 are in DELEGATED_ENGINEERING_RECEIPTS.json.

{commands}

Cold replay used the frozen source_snapshot tree in a fresh process. Three videos each contain24 actual512x512 frames. Preserve all historical failures and the distinction between readable GT software, unmeasured temporal quality and blocked reconstruction.
'''
    (OUT/'REPRODUCE.md').write_text(reproduce)
    for source,target in [('REPORT_ZH.md','REPORT_unit004_ZH.md'),('REPRODUCE.md','REPRODUCE_unit004.md'),('SOURCE_LOCK.json','SOURCE_LOCK_unit004.json')]:
        shutil.copyfile(OUT/source,WORK/'docs/partwise_sketch_hatching_v02'/target)
    print(json.dumps(native(dict(scientific_verdict=verdict,software_go=software_go,visual_go=visual_go,timing=timings)),ensure_ascii=False))

if __name__=='__main__':main()
