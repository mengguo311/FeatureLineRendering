"""Assemble audited artifacts and an explicitly limited Chinese handoff."""
import runtime
from runtime import ACTIVE_UNIT,OUTPUT_ROOT,js,sha,now,output_guard
from pathlib import Path
import datetime,json
import numpy as np
from PIL import Image
from run_hybrid import protocol,read_npz,panel,OLD

def main():
    u=ACTIVE_UNIT;p=protocol(u);v=json.loads((u/'VALIDATION.json').read_text())
    media=json.loads((u/'MEDIA_VALIDATION.json').read_text())
    for path,h in p['input_hashes'].items():assert sha(path)==h,path
    for name,h in json.loads((u/'DELIVERY_SOURCE_LOCK.json').read_text()).items():assert sha(u/'delivery_source'/name)==h
    for scene in p['scenes']:
        replay=json.loads((u/f'cold_replay_{scene}_001/REPLAY.json').read_text())
        assert all(replay['exact'].values())
        assert all(media['scenes'][scene]['all_frames_decoded_exact'])
    rows=v['per_view_summary'];overview=[];labels=[];old_images=[];old_labels=[]
    for index in range(4):
        for scene,s in p['scenes'].items():
            c=s['evaluation_cameras'][index];folder=u/'results'/scene/c['view']
            for name,label in [('source','Original GS'),('hybrid_gated','Region hybrid')]:
                overview.append(np.asarray(Image.open(folder/(name+'.png'))).astype(float)/255)
                labels.append(f'{scene} {c["azimuth"]:g}/{c["elevation"]:g} | {label}')
    panel(u/'ALL_VIEWS.png',overview,labels,'All eight exposed DEV cameras | Original GS paper + proxy ink | No native / semantic / temporal certification',columns=4)
    for scene,s in p['scenes'].items():
        c=s['evaluation_cameras'][1];folder=u/'results'/scene/c['view']
        paths=[folder/'source.png',OLD/'results'/scene/c['view']/'tint_specific.png',folder/'hybrid_gated.png']
        old_images.extend([np.asarray(Image.open(x)).astype(float)/255 for x in paths])
        old_labels.extend([scene+' | Same-camera original GS','v05 sparse-path tint / old task','v06 complete-region hybrid / new task'])
    panel(u/'BASELINE_COMPARISON.png',old_images,old_labels,'Different target scopes and operations: this is NOT a repair or re-score of the old sparse-path test.')
    weak=next(x for x in rows if x['scene']=='lego' and x['view']=='orbit_241_24_5.3')
    weak_row=json.loads((u/'results/lego/orbit_241_24_5.3/EVALUATION.json').read_text())
    old_readback=json.loads((OLD/'results/lego/orbit_241_24_5.3/VISIBILITY_READBACK.json').read_text())['arms']['specific']
    comparison=dict(old_unit=str(OLD),old_task='fixed sparse 3px capsules',new_task='complete authored region4 hybrid',
        identical_original_source_RGB_alpha_at_all_eight_cameras=True,
        old_lego_region_changed_fraction=old_readback['changed_authored_region4_fraction'],
        old_lego_region_mean_clipped_L1=old_readback['authored_region4_mean_clipped_RGB_L1'],
        old_lego_sparse_far_fraction=.08044,old_lego_eroded_capsule_pixels=31,
        new_lego_region_changed_fraction=weak_row['metrics']['hybrid_gated']['target_full']['visible_fraction_1_255'],
        new_lego_region_mean_clipped_L1=weak['hybrid_target_mean'],new_lego_full_region_far_fraction=weak['hybrid_far'],
        warning='Different targets, masks and operations; no causal selector improvement or retroactive sparse gate pass.')
    js(u/'BASELINE_REFERENCE.json',comparison)
    scene_data={}
    for scene,s in p['scenes'].items():
        rr=[x for x in rows if x['scene']==scene]
        match=json.loads((u/'results'/scene/'BUILD_MATCH.json').read_text())
        scene_data[scene]=dict(source_count=s['source_count'],selected_original_rows=match['source_counts']['primary'],
            unknown_original_rows=match['unknown_original_rows'],BUILD_ink_scale=match['ungated_ink_scale'],
            BUILD_nearest_source_scale=match['nearest_scale'],BUILD_matches_valid=bool(match['nearest_effect_match_valid'] and match['ink_effect_match_valid']),
            target_pixels_range=[min(x['target_pixels'] for x in rr),max(x['target_pixels'] for x in rr)],
            ink_retained_range=[min(x['ink_retained'] for x in rr),max(x['ink_retained'] for x in rr)],
            source_paper_far_range=[min(x['paper_far'] for x in rr),max(x['paper_far'] for x in rr)],
            hybrid_far_range=[min(x['hybrid_far'] for x in rr),max(x['hybrid_far'] for x in rr)],
            practical_screen_passes=sum(x['practical_screen'] for x in rr),views=len(rr))
    commands=[]
    for f in sorted((u/'logs').glob('*.start.json')):
        # The reporting command's own receipt is written only after this process
        # returns; do not mislabel that pending receipt as an interruption.
        if f.name.startswith('finish_'):continue
        start=json.loads(f.read_text());receipt=f.with_name(f.name.replace('.start.json','.receipt.json'))
        result=json.loads(receipt.read_text()) if receipt.exists() else {}
        commands.append(dict(stage=f.name.replace('.start.json',''),argv=start['argv'],start_utc=start['utc'],
            child_returncode=result.get('returncode'),outer_exit_code=143 if not receipt.exists() else None,
            receipt=str(receipt) if receipt.exists() else None,log=str(f.with_name(f.name.replace('.start.json','.log')))))
    interrupts=[json.loads(f.read_text()) for f in sorted(u.glob('INTERRUPTION_*.json'))]
    next_step='固定当前原核区域选择、纸底和保存路径，分离Lego的既存主排线层与交叉层，在相同BUILD实际可见墨量下比较单方向与交叉排线，并在低角度短弧中检查碎线/闪烁。唯一新变量为墨层组合；不调M1或删失败视角。若单层没有视觉改善，再定位代理几何/路径造成的碎线，停止重复责任门控调参。'
    next_why='本轮已经得到可见的原核关联区域混合风格，但门控未显示明确优势；Lego交叉排线与残余照片纹理叠加仍显杂乱。已存layer_id和固定3D路径提供便宜且独立的风格质量路线。下一单元仍需先做实际只读Astra审阅。'
    js(u/'NEXT.json',dict(action='continue',recommended_next_step=next_step,why=next_why,
        scientific_verdict='Visible hybrid achieved; added responsibility-gating benefit not established.',
        preserve='All v05 failures, this unit fixed parameters/results, two UNKNOWN child exit codes and initial media failure stay immutable.'))
    elapsed=(datetime.datetime.now(datetime.timezone.utc)-datetime.datetime.fromisoformat('2026-10-23T16:51:34.353171+09:00')).total_seconds()/60
    progress=dict(M1=dict(state='reused_unchanged',scope='Complete original-row unit005 membership/UNKNOWN reused; no extra evidence or relabeling.'),
        M2=dict(state='unchanged',scope='Old sparse path/CSR failures remain; no physical attachment certification.'),
        M3=dict(state='visible_region_hybrid_executed',scope='True original-GS paper color override plus proxy-carried ink, coupled by original-row full-T responsibility; separate layers and controls delivered.'),
        M4=dict(state='finite_replayable_asset',scope='Two exact cold replays, all eight whole-object views, two four-frame decoded edit videos. Original PLY, M1/mesh assets and local Python remain external dependencies.'),
        gating_increment='NOT_ESTABLISHED: visually close to simpler BUILD ink-matched un-gated proxy ink; geometry/visibility of paths unchanged.')
    status=dict(unit='unit_001',execution_state='completed',stage='validated_hybrid_handoff',work_in_progress=False,
        scientific_verdict='VISIBLE_AUTHORED_REGION_HYBRID_ON_EXPOSED_DEV; GATING_BENEFIT_NOT_ESTABLISHED; UNCERTIFIED_CPU_MAPPING',
        scientific_seal=False,gaussian_link_progress=progress,scenes=scene_data,
        tests=dict(targeted_TDD_tests=3,TDD_red_rc=1,TDD_green_rc=0,actual_original_kernel_fixture=True,
            evaluated_saved_views=8,independent_saved_pixel_and_input_validation_rc=0,source_paper_and_support_trace_reconstruction_views=8,
            original_source_RGB_alpha_exact_vs_unit005_views=8,cold_replays_exact=2,decoded_edit_frames=8,
            BUILD_source_renders=32,evaluation_source_renders=40,original_inputs_unchanged=43),
        process_receipts_complete=False,interruptions=interrupts,
        media_recovery=dict(first_rc=1,cause='ffmpeg absent from PATH',recovery_rc=0,method='Existing pinned v05 ffmpeg binary; no download or experiment rerun.'),
        actual_commands=commands,artifacts=dict(protocol='PROTOCOL.json',report='REPORT_ZH.md',validation='VALIDATION.json',
            all_views='ALL_VIEWS.png',baseline_comparison='BASELINE_COMPARISON.png',baseline_scope='BASELINE_REFERENCE.json',
            source='source_snapshot',delivery='delivery_source',selections='results/<scene>/SELECTION.npz',
            per_view_layers='results/<scene>/<view>/FRAME.npz',media='MEDIA_VALIDATION.json',next='NEXT.json'),
        limitations=['All eight views exposed DEV; no blind/generalization result.','Same authored proxy intent is not independent semantic or geometric truth.',
            'CPU replica is not native CUDA per-ID certification; fixed model is existing vanilla GS.',
            'Residual source texture, proxy/path jaggedness and ink fragmentation remain visible.',
            'Two completed Lego payloads validated independently but original child exit codes remain UNKNOWN.'],
        resource_discipline=dict(serial=True,CPU_affinity=2,numeric_threads=1,GPU=False,nested_models=False),
        started_jst='2026-10-23T16:51:34.353171+09:00',finished_utc=now(),elapsed_minutes=elapsed,
        finished_within_45_minutes=elapsed<=45,next_action='continue')
    js(u/'STATUS.json',status)
    lines=['# Unit001：可见的区域级原核关联混合排线','',
        '**执行完成；有可见应用进展；责任门控的额外收益未建立；scientific_seal=false。**','',
        'Chair座面patch与Lego铲斗作者区域现在能看到大面积纸底和固定三维排线。八个已曝光DEV视角全部保留，包含Lego241°/24°旧弱角度。实际查看了整物体结果及门控/不门控/最近代理面/打乱ID对照。',
        '这不是原生Gaussian排线：纸底来自真正的完整原GS颜色副本，墨线来自冻结代理上的三维路径，二者由原始行责任权重连接。全SH3求值保留，原PLY、中心、协方差、opacity、SH数组及行序不改。','',
        '## 冻结问题与实现','',
        f'协议SHA256：`{sha(u/"PROTOCOL.json")}`。parent DECISION、43个输入和实验源码先冻结，之后没有根据DEV结果调参。',
        '目标明确改为完整作者region4；旧3px路径capsule任务和7/8结论没有回算。新区域掩码取固定2×排线渲染的中心样本，像素数与旧1×诊断可能相差少量像素；所有本轮对照共用同一掩码。',
        '`s=q[:,4]`仅对非UNKNOWN且region_id=4的原核非零。Chair27873核、Lego20122核；M1 UNKNOWN仍为170281/195600，不强行填标签。源颜色混合到固定(0.95,0.95,0.95)，`S=sum(alpha*T*s)`使用完整原GS真实接受贡献，墨层为`H4*S`。',
        '主对照只切换墨层是否乘S；另保存未门控的原强度和BUILD可见墨量配平结果。Chair/Lego的未门控墨强度尺度为0.766800/0.697805。最近代理面源纸底尺度为0.823238/0.645309，四个原BUILD相机实际重渲染验证配平。shuffle是未配平负控制，不据此声称公平风格优势。','',
        '## 实际覆盖与损伤','',
        '下表“明显变化”指目标腐蚀内部clipped RGB L1≥0.05的像素比例；远区占比使用raw RGB L1，固定2px边界带另报。墨量保留相对同路径未门控墨层。这些描述实际效果，不是视觉质量认证。','',
        '| 场景/视角 | 全区域/内部像素 | 明显变化% | 墨量保留% | 源纸底远区% | 混合远区% | 区域混合mean L1 |',
        '|---|---:|---:|---:|---:|---:|---:|']
    for r in rows:
        lines.append(f'| {r["scene"]}/{r["view"]} | {r["target_pixels"]}/{r["interior_pixels"]} | {100*r["useful_fraction"]:.2f} | {100*r["ink_retained"]:.2f} | {100*r["paper_far"]:.3f} | {100*r["hybrid_far"]:.3f} | {r["hybrid_target_mean"]:.4f} |')
    lines+=['',
        '冻结的50%变化/50%墨量实用性筛查为8/8；源纸底远区为0.060%–0.826%，混合远区为0.068%–0.745%。所有逐视图的完整目标、腐蚀内部、边界、远其他部件、背景的mean/sum以及源层/墨层/混合层分别保存在EVALUATION.json；不能只看混合后可能抵消的差分。',
        '相同BUILD源效果预算下，最近代理面源纸底在Lego61°/24°、61°/60°的远区占比分别4.719%/2.342%，M1为0.826%/0.493%。这支持当前作者意图上的局部控制价值，但不是独立语义准确率，也不是对墨层门控收益的证明。',
        f'Lego241°/24°旧稀疏源改色仅改变作者区域{100*comparison["old_lego_region_changed_fraction"]:.2f}%，区域mean L1=0.00329。新完整区域混合mean L1={weak["hybrid_target_mean"]:.4f}、内部明显变化{100*weak["useful_fraction"]:.2f}%、墨量保留{100*weak["ink_retained"]:.2f}%。两者目标与操作不同，不能把旧8.044%远区失败改写成通过。BASELINE_COMPARISON.png仅作同相机应用效果参照。','',
        '## 视觉判断与负结果','',
        'Chair座面出现可辨认的平行排线；Lego铲斗出现明显交叉排线，原弱角度不再只有几处几乎不可见的蓝点。但纸底仍有绿/黄照片纹理残留，Lego排线有碎线和杂乱交叉。目标区域UNKNOWN责任质量约Chair19.8%–25.0%、Lego28.9%–36.7%，本轮未修复这些支持缺口。',
        '门控和按BUILD墨量配平的未门控结果视觉接近。门控不改变路径几何或代理遮挡，仅降低局部墨强度；它保留58.1%–75.0%墨量，没有可靠证据证明更好的附着或清晰度。故不把门控升级为必须模块，较简单的未门控代理墨层仍是强基线。本轮系统集成有效，不等同于新关联机制优越。','',
        '## 验证、回放与运行缺口','',
        '3项TDD先RED(rc1缺模块)后GREEN(rc0)，包含真实24个原核小夹具、零操作、ID置换响应和原数组不变。八视图旧原GS RGB/alpha逐值相同；按保存的真实原ID trace独立重建纸底RGB与S，误差均<1e-6。43个输入哈希和保存输出/指标核验通过。',
        '交付副本在Chair与Lego241°/24°各独立冷重放一次，source/paper/support/reference_ink/hybrid/ink_alpha六数组逐值一致。两条固定相机4级墨量编辑视频共8帧，FFV1完整解码逐像素一致；纸底固定，只改墨量，不是转台或时序稳定性验证。',
        'Lego视角0、1的外层工具会话各返回143，子退出码回执缺失，原因UNKNOWN。其完整payload已保存并通过后续独立验证，未重跑或覆盖；原日志、start和INTERRUPTION记录保留，不补造rc0。初次视频编码rc1（PATH无ffmpeg）；使用v05已安装二进制恢复rc0，原失败代码/日志及恢复工具独立保留。',
        '所有数值串行、两核亲和、单数值线程，无GPU、下载、嵌套模型或旧目录写入。CPU replica及协方差平面深度局限保持，不宣称native、物理/语义归属、H1/H2/H3或通用时序稳定性。','',
        '## 交付与下一步','',
        '入口与依赖见README_ZH.md。ALL_VIEWS.png包含全部八视角；各视图COMPARISON.png/CONTROLS.png、FRAME.npz、TRACE.npz保留实际源层、墨层和结果。原PLY、M1/代理资产与本机Python仍是外部依赖，不声称完全便携。','',
        'NEXT=continue：'+next_step,'',next_why,'',f'本次执行耗时截至报告生成约{elapsed:.2f}分钟；本单元没有启动下一个科学单元。']
    (u/'REPORT_ZH.md').write_text('\n'.join(lines)+'\n')
    python='/mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_8build_part_prior_feasibility_v03/venv/bin/python'
    readme=f'''# Unit001 可回放混合排线

先看 [全部视角](ALL_VIEWS.png)、[与旧实际输出并列](BASELINE_COMPARISON.png) 和 [报告](REPORT_ZH.md)。这是原GS纸底 + 代理三维墨线，不是原生Gaussian排线。主结果和简单未门控基线均保留；门控额外收益未建立。

真实冷回放（输出目录必须是新的v06目录）：

```bash
V06_UNIT_DIR={u} {python} -B {u}/delivery_source/replay_hybrid.py --scene lego --index 1 --output {u}/replay_user_001
```

scene可选chair/lego；index=0/1/2/3分别是61°/24°、241°/24°、61°/60°、241°/60°。当前工具会逐值比较冻结结果后导出hybrid/paper/ink及REPLAY.npz。输出受v06路径保护。

`results/<scene>/SELECTION.npz`保留完整原始source_index与primary/nearest/shuffled强度。原M1绑定位置和原PLY/代理/笔触哈希在PROTOCOL.json；这些大资产没有拷进包，仍依赖本机原只读路径及现有解释器。

`source_snapshot`是冻结科学代码；`delivery_source`另附已执行的独立验证、冷回放与媒体工具。最初make_media.py因PATH缺ffmpeg失败，原文件不改；实际恢复入口为make_media_recovery.py，已安装二进制及哈希见MEDIA_VALIDATION.json。恢复代码锁单独保存。

完整层：FRAME.npz含source/paper/ink/hybrid、S、UNKNOWN责任、代理区域/深度、各对照。TRACE.npz为验证采样点处所有接受的原ID贡献，不是完整图像逐像素CSR。未强制UNKNOWN归类。

固定相机墨量视频：
- [Chair](results/chair/orbit_241_24_5.1/ink_ramp/ink_edit_ffv1.mkv)
- [Lego](results/lego/orbit_241_24_5.3/ink_ramp/ink_edit_ffv1.mkv)

每条4帧、2fps，全部解码逐像素一致；不是相机环绕。两次原Lego子退出码UNKNOWN、媒体初次rc1与恢复rc0均保留在STATUS.json/logs，不以重放成功替代原记录。
'''
    (u/'README_ZH.md').write_text(readme)
    (OUTPUT_ROOT/'DEMO_README_ZH.md').write_text('# v06 当前可用结果\n\n[unit001说明](units/unit_001/README_ZH.md) · [全部视角](units/unit_001/ALL_VIEWS.png) · [实际报告](units/unit_001/REPORT_ZH.md)\n\n已实现Chair/Lego作者区域的原GS纸底与代理排线混合操作；责任门控额外收益未建立，原始失败保留。NEXT=continue，后续每单元仍需先审阅；本文件不表示整晚任务已结束。\n')
    js(OUTPUT_ROOT/'DELIVERY_STATUS.json',dict(latest_completed_unit='unit_001',execution_state='completed',scientific_seal=False,
        gaussian_link_progress=progress,next_action='continue',report=str(u/'REPORT_ZH.md'),updated_utc=now()))
    # Audit immutable science payloads only; runtime STATUS/logs/report remain outside this lock.
    files=[u/'PROTOCOL.json',u/'PROTOCOL_LOCK.json',u/'DECISION.json',u/'VALIDATION.json',u/'MEDIA_VALIDATION.json',u/'BASELINE_REFERENCE.json']
    for directory in ('results','source_snapshot','delivery_source','cold_replay_chair_001','cold_replay_lego_001'):
        files.extend(f for f in (u/directory).rglob('*') if f.is_file() and f.suffix not in ('.so',) and 'build' not in f.parts)
    js(u/'ARTIFACT_LOCK.json',dict(utc=now(),scientific_seal=False,scope='Audited finite engineering payloads; mutable runtime excluded.',
        files={str(f.relative_to(u)):sha(f) for f in files}))
    size=sum(f.stat().st_size for f in OUTPUT_ROOT.rglob('*') if f.is_file())
    assert size<20*2**30
    print(json.dumps(dict(status=status['execution_state'],elapsed_minutes=elapsed,views=8,artifact_files=len(files),output_bytes=size,next='continue')),flush=True)

if __name__=='__main__':main()
