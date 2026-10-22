"""Summarize validated fresh-view evidence without turning failures into GO."""
import runtime
from runtime import js,sha,now,OUTPUT_ROOT
from pathlib import Path
import argparse,json,shutil,datetime,subprocess
import numpy as np
from PIL import Image
from run_transfer_unit import load,ARMS
from run_path_unit import read_npz


def finish(unit):
    p=load(unit);summary={};allrows=[];diagnosis={}
    for scene,s in p['scenes'].items():
        root=unit/'results'/scene;validation=json.loads((root/'VALIDATION.json').read_text())
        assert validation['all_scheduled_views_validated']
        audit=json.loads((root/'PRIOR_AUDIT.json').read_text());rows=[]
        old=read_npz(root/'FOOTPRINT_BINDING.npz')
        for c in s['cameras']:
            folder=root/c['view'];r=json.loads((folder/'EVALUATION.json').read_text());rows.append(r);allrows.append((scene,r))
            z=read_npz(folder/'SELECTED_KERNEL_DIAGNOSTICS.npz');ids=z['source_index'];total=z['full_pixel_mass'][:,0]
            fraction=np.divide(z['full_pixel_mass'][:,3],total,out=np.zeros_like(total),where=total>0)
            exposed=total>=.02;rank=np.argsort(-z['far_RGB_L1_upper_bound'],kind='stable')
            detail=dict(new_exposed_selected_IDs=int(exposed.sum()),new_far_gt_5pct_IDs=int((exposed&(fraction>.05)).sum()),
                build_weighted_far_fraction=float((old['far'][ids]*z['strength']).sum()/max((old['total'][ids]*z['strength']).sum(),1e-30)),
                new_weighted_far_fraction=r['failure_diagnosis']['selected_responsibility_far_fraction'],
                top_far_bound_IDs=[dict(source_index=int(ids[j]),BUILD_far_fraction=float(old['far_fraction'][ids[j]]),
                    new_far_fraction=float(fraction[j]),new_total_mass=float(total[j]),
                    projected_sigma_major_px=float(z['projected_sigma_major'][j]),far_RGB_L1_bound=float(z['far_RGB_L1_upper_bound'][j])) for j in rank[:10]])
            js(folder/'TRANSFER_DIAGNOSIS.json',detail);diagnosis[scene+'/'+c['view']]=detail
        counts={arm:dict(locality=sum(r['arms'][arm]['intent_locality_gate'] for r in rows),
            coverage=sum(r['coverage'][arm]['coverage_gate'] for r in rows),joint=sum(r['joint_transfer'][arm] for r in rows)) for arm in ARMS}
        unknown=[r['M1_projection']['source_unknown_mass_fraction'] for r in rows]
        worst=max(rows,key=lambda r:r['arms']['specific']['far_non_target_fraction'])
        summary[scene]=dict(source_count=s['source_count'],M1_unknown=audit['M1_unknown'],selected_original_IDs=audit['selected_original_IDs'],
            scheduled_views=len(s['cameras']),evaluated_views=len(rows),pass_counts=counts,
            locality_scorable_views=sum(r['arms']['specific']['target_interior']['pixels']>0 for r in rows),
            coverage_scorable_views=sum(r['coverage']['specific']['coverage_scorable'] for r in rows),
            joint_scorable_views=sum(r['arms']['specific']['target_interior']['pixels']>0 and r['coverage']['specific']['coverage_scorable'] for r in rows),
            unscorable_views=[dict(view=r['camera']['view'],empty_target_interior=r['arms']['specific']['target_interior']['pixels']==0,
                insufficient_supported_anchors=not r['coverage']['specific']['coverage_scorable']) for r in rows
                if r['arms']['specific']['target_interior']['pixels']==0 or not r['coverage']['specific']['coverage_scorable']],
            unknown_source_responsibility_fraction_range=[min(unknown),max(unknown)],
            worst_far_view=worst['camera']['view'],worst_far_fraction=worst['arms']['specific']['far_non_target_fraction'],
            actual_evaluation_seconds=sum(r['seconds'] for r in rows),source_bindings_unchanged=True)
        for filename,dest in [('comparison.png','ALL_EVALUATION_VIEWS.png'),('controls.png','ALL_CONTROLS.png'),('difference_diagnostics.png','ALL_DIFFERENCES.png')]:
            images=[Image.open(root/c['view']/filename).convert('RGB') for c in s['cameras']]
            canvas=Image.new('RGB',(images[0].width,sum(im.height for im in images)),'white');y=0
            for im in images:canvas.paste(im,(0,y));y+=im.height
            canvas.save(root/dest)
    total={arm:{key:sum(s['pass_counts'][arm][key] for s in summary.values()) for key in ('locality','coverage','joint')} for arm in ARMS}
    js(unit/'SUMMARY.json',dict(utc=now(),scenes=summary,pass_counts=total,views=len(allrows),scientific_seal=False))
    next_step='Use unit004 as explicitly exposed DEV. Add fixed low/high-elevation BUILD evidence to improve original-row M1 exposure and kernel footprint constraints, then freeze separate new evaluation cameras. Compare old/new bindings with the same path capsules and matched actual source-RGB BUILD effect plus coverage gates; preserve UNKNOWN when there is no edit headroom. Inspect the saved leaking IDs and projected covariance; do not widen masks or relabel this transfer failure as success.'
    progress=dict(previous_gap='unit003 passed locality on six already-exposed cameras; broad view-transfer and retained path coverage were untested.',
        actual_advance='New per-original-ID accepted responsibilities, all-anchor path CSR, two explicit UNKNOWN-aware region projections, four frozen-control source tint renders, and actual source-opacity rerenders at sixteen fresh v05 cameras across two scenes.',
        milestones=dict(M1_region_original_binding=dict(state='partial',scope='Two frozen original-row membership universes reconstructed exactly; fresh soft versus abstention-aware projections quantify UNKNOWN. No new semantic labeling or confidence calibration.'),
            M2_path_original_support=dict(state='partial',scope='Sixteen new views retain every frozen stroke/segment/face/bary anchor, accepted original IDs and weights, rejected mass and UNKNOWN; full-kernel off-path evidence retained.'),
            M3_actual_linked_control=dict(state='finite_CPU_transfer_tested_with_failures',scope='Actual complete-source tint controls and source-opacity diagnostics; frozen strengths, no new-view fitting. Joint locality/coverage is not universally valid.'),
            M4_reusable_asset_demo=dict(state='partial',scope='Replay/query CLI, immutable arrays/source snapshot, cold exact replays and scene panels; original PLY/CPU environment remains external.')),
        reasoning='Original-Gaussian control is real and replayable, but BUILD footprint exclusion does not certify its projection at new elevations. Coverage and UNKNOWN are explicit instead of hidden behind a locality-only pass.',
        scene_counts=summary,pass_counts=total)
    replay={x.name:json.loads((x/'RECEIPT.json').read_text()) for x in unit.glob('replay_*') if (x/'RECEIPT.json').exists()}
    queries={x.name:json.loads((x/'RECEIPT.json').read_text()) for x in unit.glob('query_*') if (x/'RECEIPT.json').exists()}
    assert len(replay)>=4 and all(all(r['all_arrays_exact'].values()) for r in replay.values())
    assert len(queries)==2
    media=json.loads((unit/'media/VIDEO_VALIDATION.json').read_text()) if (unit/'media/VIDEO_VALIDATION.json').exists() else None
    end=datetime.datetime.now(datetime.timezone.utc);elapsed=(end-datetime.datetime.fromisoformat(p['started_jst'])).total_seconds()/60
    status=dict(unit='unit_004',stage='fresh_view_original_kernel_transfer_and_UNKNOWN_coverage_audit',execution_state='partial',
        scientific_verdict='UNCERTIFIED_CPU_MAPPING; finite original-ID controls validated; fresh-view joint locality/coverage not universal',
        scientific_seal=False,updated_utc=now(),gaussian_link_progress=progress,scenes=summary,pass_counts=total,
        tests=dict(new_TDD_tests=3,renderer_original_ID_occlusion_fixtures=2,prior_actual_trace_and_four_arm_metrics_views=6,
            fresh_actual_trace_views=16,source_tint_arm_renders=64,source_opacity_rerenders=16,
            original_CPU_baseline_exact_views=2,all_scheduled_persisted_evidence_validated=True,
            cold_source_replays=len(replay),all_cold_replay_arrays_exact=True,unpruned_path_queries=len(queries)),
        artifacts=dict(protocol='PROTOCOL.json',summary='SUMMARY.json',bindings='results/<scene>/SOURCE_BINDING.npz',
            fresh_path_support='results/<scene>/<view>/path_support.npz',M1_projections='results/<scene>/<view>/M1_PROJECTION.npz',
            per_ID_diagnosis='results/<scene>/<view>/SELECTED_KERNEL_DIAGNOSTICS.npz',CLI='delivery_source/run_transfer.sh',
            panels='results/<scene>/ALL_EVALUATION_VIEWS.png'),
        blockers=['Native CUDA per-ID calibration unavailable','M1 remains sparse/UNKNOWN','Fixed BUILD footprints do not guarantee new-view locality or coverage','Same-proxy intent is not independent semantic/surface truth'],
        original_failure_evidence=dict(previous_unit_seal_unchanged=True,TDD_red_returncode=1,
            interrupted_batch_outer_exit=143,interrupted_child_returncode=None,interrupted_outputs='interrupted_lego_view_0',
            recovery='Identical frozen-protocol retry; original log/start/interruption and output files preserved',
            historical_depth_differences_and_Ficus_NO_GO='unchanged; no recalibration or reinterpretation'),
        resource_discipline=p['resource_limits'],finished_utc=end.isoformat(),elapsed_minutes=elapsed,finished_before_55min=elapsed<=55,
        source_PLY_geometry_order_and_original_SH_unchanged=True,next_action='continue',
        code_commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
        media=media and dict(actual_arc_cameras=media['actual_arc_cameras'],actual_tint_levels=media['actual_tint_levels'],all_frames_decoded=True))
    js(unit/'STATUS.json',status)
    js(unit/'NEXT.json',dict(action='continue',recommended_next_step=next_step,
        recommended_next_step_zh='把本轮视角明确转为已曝光DEV；增加固定低／高仰角BUILD责任证据，改善M1曝光和原核footprint约束，再冻结新评估相机。保持同一路径掩码，以实际源RGB效果和覆盖预算比较新旧绑定；无可用编辑余量仍保留UNKNOWN。',
        gaussian_link_progress=progress,reasoning='Saved original-ID failure rows identify a useful next source-kernel experiment; time remains before the global science deadline.',
        stop_only_if=['safety','quota','no useful independent action','deadline'],deadlines_jst=dict(no_new_science='21:20',wrap='21:45',hardstop='22:00')))
    lines=['# Unit004：新仰角下的原始 Gaussian 联动与 UNKNOWN 审计','',
        '**execution_state=partial；UNCERTIFIED_CPU_MAPPING。** 真实原核联动已执行并验证；本轮不宣称跨视角全通过。',
        '',f'冻结16个新v05相机，Chair/Lego各8个：方位31/121/211/301°，仰角12/72°，距离5.1/5.3，384²。在前3单元286份JSON的101条相机记录中，精确外参不重合；旧v04曝光与源GS训练视角重合未核实，不能称为独立原生或语义盲测。协议SHA256：`{sha(unit/"PROTOCOL.json")}`。',
        '', '完整阅读BRIEF、大纲及v04适配器/真实接受位置/代理与编辑路径。上一单元6个实际评估视角的alpha×T、原行映射和四臂RGB指标均复算一致；两场景M1、路径、全footprint和强度数组逐行重建。旧6/6局部性结果保留，但它没有证明新仰角迁移或足够路径覆盖。',
        '', '本轮不重新选择核、不配平新视角、不调整阈值。四臂为full-footprint、旧path、同核数nearest-path和曝光分箱shuffled-ID，全部沿用unit003四个BUILD完整源RGB L1配平强度。旧path核数不同；其余三臂核数匹配。全SH3求值并下界clamp后作颜色混合，高阶视角变化保留于(1-strength)部分，原SH不写回。均值、协方差、旋转、原始行数／顺序及PLY均不变。',
        '', '原局部性条件为目标内部mean L1≥.02且远区变化占比≤2%；固定3px路径capsule和2px边界带。新增覆盖条件在评估前冻结：至少8个原支持锚点，编辑mass>.01的支持锚点比例≥50%，加权保留mass比例≥5%。局部性与覆盖必须同时成立才记joint通过。空目标或不足支持不会记成成功。',
        '', '| Scene | 原始行数 | M1 UNKNOWN | 选中原核 | specific局部性 | specific覆盖 | specific joint |',
        '|---|---:|---:|---:|---:|---:|---:|']
    for scene,s in summary.items():
        counts=s['pass_counts']['specific'];lines.append(f'| {scene} | {s["source_count"]} | {s["M1_unknown"]} | {s["selected_original_IDs"]} | {counts["locality"]}/8 | {counts["coverage"]}/8 | {counts["joint"]}/8 |')
    lines+=['','上表分母8（总表16）是全部预排相机数，包含不可评分视角；不将不可评分当成有目标条件下的失败。', '',
        '| Scene | 有目标内部可评分 | 覆盖可评分 | joint可评分 | 不可评分视角 |','|---|---:|---:|---:|---|']
    for scene,s in summary.items():lines.append(f'| {scene} | {s["locality_scorable_views"]}/8 | {s["coverage_scorable_views"]}/8 | {s["joint_scorable_views"]}/8 | '+', '.join(r['view'] for r in s['unscorable_views'])+' |')
    lines+=['','| Arm | 局部性/16 | 覆盖/16 | joint/16 |','|---|---:|---:|---:|']
    for arm,cnt in total.items():lines.append(f'| {arm} | {cnt["locality"]} | {cnt["coverage"]} | {cnt["joint"]} |')
    lines+=['','| Scene/view | 目标内部像素 | mean L1 | 远区占比 | 原支持锚点 | 编辑锚点比例 | 保留mass比例 | locality / coverage / joint |','|---|---:|---:|---:|---:|---:|---:|---|']
    fmt=lambda v:'UNKNOWN' if v is None else f'{v:.4f}'
    for scene,r in allrows:
        m=r['arms']['specific'];cv=r['coverage']['specific'];lines.append(f'| {scene}/{r["camera"]["view"]} | {m["target_interior"]["pixels"]} | {fmt(m["target_interior"]["L1_mean"])} | {m["far_non_target_fraction"]:.3%} | {cv["supported_anchors"]} | {fmt(cv["edited_anchor_fraction"])} | {fmt(cv["retained_mass_fraction"])} | {m["intent_locality_gate"]} / {cv["coverage_gate"]} / {r["joint_transfer"]["specific"]} |')
    lines+=['','M1现在明确保存两种投影：`soft_q`是原始区域证据直方图；`abstaining_q`把整核UNKNOWN的全部责任移入通道0。两者都按实际接受源alpha归一化，零质量射线是UNKNOWN。不能把前者的最大值当成确定标签；下面只报告同一作者代理的自洽性，非独立分割准确率。','',
        '| Scene | 有效样点中来自整核UNKNOWN的责任质量范围 |','|---|---:|']
    for scene,s in summary.items():
        lo,hi=s['unknown_source_responsibility_fraction_range'];lines.append(f'| {scene} | {lo:.2%}–{hi:.2%} |')
    lines+=['','每个新视角保留全部128个Chair或93个Lego锚点，包括遮挡、低支持和零事件记录。CSR关联原stroke_id、segment、代理face/bary/world与实际原核ID、权重及深度拒绝；这是一对多/多对多渲染支持，不是物理表面身份或一线一点一核。',
        '', '逐核诊断保存全部选中ID的新视角inside/band/far质量、投影协方差长轴标准差和颜色L1远区上界。上界是每核far质量×强度×颜色差，像素处颜色抵消使其不能当作精确损伤分摊。`TRANSFER_DIAGNOSIS.json`明确对比BUILD与新视角far比例，供下一轮定位原核失败；本轮没有根据这些结果改选择。',
        '', 'Opacity是单独源副本上opacity×(1-.5×未缩放strength)的完整重渲染，重新计算透射率和背层接受事件；16个视角均验证新trace重建。该诊断没有跨臂配平，不据此宣称优越性。Full-T支持覆盖图、selected-only重算T图和真实改色不同；本轮面板明确区分源RGB、作者意图、支持诊断、实际源编辑及固定3D排线。',
        '', '3项新逻辑测试先RED(模块缺失rc1)后GREEN；2项已有渲染器针对性fixture覆盖非连续ID、近裁剪、排序、背层和混合深度。实际验证16份全模型trace、64个改色渲染、16份opacity trace、两场景首视角与原CPU完全相等、逐锚点CSR/UNKNOWN及保存后独立指标重建。4次冷源重放所有数组精确，2次完整路径查询保留UNKNOWN。',
        '', 'Lego首视角所在批次会话返回143，runner未写子进程退出receipt；原因未确定，子进程退出码记null，不能伪造为-15或0。该视角已写文件及start/log/interruption记录保存在interrupted_lego_view_0，按同一协议独立重跑，随后逐视角执行。所有历史Ficus负结果、深度差异及unit003证据锁保持不变。',
        '', '局限：这仍是CPU replica映射；native per-ID校准不可用，历史同相机深度最大差异保留。covariance-plane深度是探索性代理，legacy T>.5更新不是条件半质量median。代理粗糙/孔洞/薄结构缺失未修复。16视角不是16个独立对象；只两个场景，指标是同代理意图自洽，不能证明语义、真实附着、原生Gaussian排线或H1/H2/H3。原始RGB为主预算／指标；PNG会裁剪至0–1，clipped指标另存，BUILD配平不保证新视角的显示效果配平。',
        '', 'NEXT=continue：'+next_step,
        '', f'本单元耗时（报告生成时）{elapsed:.2f}分钟；源码与绑定可由REPRODUCE_ZH.md入口复核。封存只覆盖已验证有限工程证据及标明的失败历史，scientific_seal=false。']
    if media:lines.insert(-4,'\n另保存4个真实相机位置的30°短弧与4级实际源改色；视频全帧解码，FFV1逐像素精确。这是展示复放，不是360°转台或时序稳定性评测。')
    (unit/'REPORT_ZH.md').write_text('\n'.join(lines)+'\n')
    (unit/'REPRODUCE_ZH.md').write_text(f'''# 冷重放原始Gaussian控制

源PLY与现有CPU venv为外部只读依赖。以下输出目录需尚不存在；重复运行时换名称。

```bash
bash {unit}/delivery_source/run_transfer.sh {unit} replay --scene chair --index 7 --operation tint --arm specific --output {unit}/new_replay_chair
bash {unit}/delivery_source/run_transfer.sh {unit} query --scene lego --index 7 --arm specific --output {unit}/new_query_lego
bash {unit}/delivery_source/run_transfer.sh {unit} validate --scene chair --output {unit}/new_validation_chair.json
```

封存后validate要求--output指定尚不存在的验证记录文件，避免覆盖原VALIDATION.json。replay/query只写所指定的新目录。原核ID为源PLY行号，M1/路径/footprint UNKNOWN含义不同，均保留。核心源文件由PROTOCOL.json逐字节约束；追加验证与报告工具由证据锁约束。
''')
    print(json.dumps(dict(pass_counts=total,scenes=summary,execution_state='partial'),default=runtime.json_default),flush=True)


if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--unit',type=Path,required=True);finish(ap.parse_args().unit)
