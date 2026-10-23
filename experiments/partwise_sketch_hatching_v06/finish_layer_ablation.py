"""Administrative handoff from frozen, independently checked results."""
import runtime
from runtime import ACTIVE_UNIT as UNIT,js,sha,now,output_guard
from pathlib import Path
import json
import datetime

def main():
    p=json.loads((UNIT/'PROTOCOL.json').read_text());m=json.loads((UNIT/'BUILD_MATCH.json').read_text())
    v=json.loads((UNIT/'VALIDATION.json').read_text());media=json.loads((UNIT/'MEDIA_VALIDATION.json').read_text())
    replay=json.loads((UNIT/'cold_replay_001/REPLAY.json').read_text())
    assert v['saved_views']==13 and all(media['all_frames_decoded_exact']) and all(replay['exact'].values())
    for f,h in json.loads((UNIT/'AUDIT_SOURCE_LOCK.json').read_text()).items():assert sha(UNIT/'audit_source'/f)==h
    rows=[]
    for kind,cameras in [('dev',p['scene']['evaluation_cameras']),('arc',p['arc_cameras'])]:
        for c in cameras:
            e=json.loads((UNIT/kind/c['view']/'EVALUATION.json').read_text())
            row=dict(kind=kind,view=c['view'],target_pixels=e['metrics']['paper']['target_full']['pixels'],
                interior_pixels=e['metrics']['paper']['target_interior']['pixels'],arms={})
            for key in p['arms']:
                x=e['metrics'][key];ink=e['ink'][key];shape=e['shape'][key]['visible']
                row['arms'][key]=dict(target_visible_ink_L1=ink['target_visible_ink_L1'],visible_ink_pixels=shape['pixels'],
                    visible_ink_target_fraction=shape['target_fraction'],components=shape['components'],small_components=shape['small_components_le4'],
                    target_L1_mean=x['target_full']['clipped_L1_mean'],target_L1_sum=x['target_full']['clipped_L1_sum'],
                    interior_useful_fraction=x['target_interior']['useful_fraction_0_05'],
                    far_absolute_L1=x['far_other']['raw_L1_sum']+x['far_background']['raw_L1_sum'],
                    far_other_L1=x['far_other']['raw_L1_sum'],far_background_L1=x['far_background']['raw_L1_sum'],
                    far_fraction=x['far_raw_fraction'],far_ink_L1=ink['far_visible_ink_L1'],
                    ink_supported_length_pixels=e['length_proxy'][key]['ink_supported_length_pixels'])
            a=row['arms']['cross_matched'];b=row['arms']['base_matched']
            row['single_to_cross_effect_ratio']=b['target_visible_ink_L1']/a['target_visible_ink_L1']
            row['single_coverage_loss_fraction']=1-b['visible_ink_pixels']/a['visible_ink_pixels']
            assert a['far_absolute_L1']==b['far_absolute_L1'] and a['far_ink_L1']==b['far_ink_L1']==0
            rows.append(row)
    dev=[r for r in rows if r['kind']=='dev'];arc=[r for r in rows if r['kind']=='arc']
    js(UNIT/'SUMMARY.json',dict(build=m,views=rows,dev_coverage_loss_range=[min(r['single_coverage_loss_fraction'] for r in dev),max(r['single_coverage_loss_fraction'] for r in dev)],
        dev_effect_ratio_range=[min(r['single_to_cross_effect_ratio'] for r in dev),max(r['single_to_cross_effect_ratio'] for r in dev)],
        verdict='SINGLE_DIRECTION_QUALITY_GAIN_NOT_ESTABLISHED',default_style_changed=False))
    next_step='固定现有原核选择、纸底和layer0路径，做逐stroke的可见性归因：区分保存路径的计划间隙/几何断段、代理区域裁切、逐片元面平面深度拒绝与S减淡。优先用真实共享边路径和有前景遮挡的小夹具检验当前0.004深度规则是否误拒绝连续可见笔触，再决定是否采用中心线可见区间驱动的恒屏幕宽胶囊；不先放宽深度容差、不凭图像连通块数宣布修复。'
    reason='单层在全部四个DEV视角降低可见墨覆盖，弱角度和九帧短弧仍有断续笔触，未建立整物体可读性改善。交叉数量减少不是连续性改善；路径/遮挡归因是不同于继续调墨层或M1的可证伪路线。'
    js(UNIT/'NEXT.json',dict(action='continue',recommended_next_step=next_step,why=reason,
        scientific_verdict='Single-layer simplification has no established quality benefit; retain current cross style.',
        preserve='Original v05 sparse-path failures, unit001 gating negative result, unit002 frozen raw/matched results and arc0 UNKNOWN child exit remain immutable.'))
    interruptions=[json.loads(f.read_text()) for f in UNIT.glob('INTERRUPTION_*.json')]
    commands=[]
    for f in sorted((UNIT/'logs').glob('*.start.json')):
        start=json.loads(f.read_text());receipt=f.with_name(f.name.replace('.start.json','.receipt.json'))
        record=dict(stage=f.name.replace('.start.json',''),argv=start['argv'],start_utc=start['utc'],start_file=str(f))
        if not receipt.exists() and record['stage'].startswith('finish_'):
            continue  # This administrative process cannot report its own future exit.
        if receipt.exists():record.update(receipt=str(receipt),child_returncode=json.loads(receipt.read_text())['returncode'])
        else:
            assert record['stage']=='arc_0_001' and interruptions
            record.update(child_returncode=None,outer_returncode=143,cause='UNKNOWN')
        commands.append(record)
    elapsed=(datetime.datetime.now(datetime.timezone.utc)-datetime.datetime.fromisoformat('2026-10-23T17:29:18.868914+09:00')).total_seconds()/60
    status=dict(unit='unit_002',execution_state='completed',stage='validated_direction_layer_ablation_handoff',work_in_progress=False,
        scientific_verdict='SINGLE_DIRECTION_QUALITY_GAIN_NOT_ESTABLISHED; COVERAGE_LOSS; NO_DEFAULT_PROMOTION',scientific_seal=False,
        gaussian_link_progress=dict(M1='Unchanged: complete original-row universe, membership/UNKNOWN and 20122 selected Lego rows reused.',
            M2='Unchanged frozen mesh/face/bary/stroke/layer identities; no attachment or depth-correction claim.',
            M3='Actual original-GS paper and full-T original-ID S retained; equal-BUILD-ink direction edit evaluated. Single layer fails to establish readability benefit.',
            M4='Four complete DEV views, nine-frame actual camera arc, decoded movie and exact new-camera cold original-GS replay delivered.'),
        changed_variable=p['changed_variable'],build_match=m,summary='SUMMARY.json',default_style_changed=False,
        tests=dict(targeted_TDD_tests=3,TDD_red_rc=1,TDD_green_rc=0,legacy_BUILD_cross_exact=4,legacy_DEV_cross_exact=4,
            evaluation_records=13,unique_evaluation_cameras=12,new_arc_source_camera_pairs=8,source_render_calls_in_arc=16,
            cold_original_GS_replay_exact=True,cold_replay_source_render_calls=2,independent_saved_array_validation_rc=0,
            immutable_input_hashes_verified=29,decoded_video_frames=9,all_decoded_frames_exact=True),
        process_receipts_complete=False,interruptions=interruptions,actual_commands=commands,
        limitations=['Authored proxy intent is not independent semantics or physical geometry.',
            'CPU replica has no native CUDA per-ID certification.',
            'Image components merge at crossings; this is not an absolute stroke-fragment metric.',
            'Projected centerline length can credit overlapping strokes and includes occluded denominator samples.',
            'Only BUILD total ink was matched; evaluation view effects differ and were not retuned.',
            'Nine-frame arc inspected without independent motion correspondence; no general flicker/stability proof.',
            'Paper texture/UNKNOWN gaps and geometric/raster fragmentation remain unresolved.'],
        artifacts=dict(protocol='PROTOCOL.json',sources='source_snapshot',audit_replay_media_sources='audit_source',source_locks=['PROTOCOL_LOCK.json','AUDIT_SOURCE_LOCK.json'],
            comparison='ALL_DEV_VIEWS.png',arc_contact='ALL_ARC_FRAMES.png',video=media['movie'],frames='dev/<view>/FRAME.npz and arc/<view>/FRAME.npz',
            validation='VALIDATION.json',replay='cold_replay_001/REPLAY.json',readme='README_ZH.md'),
        next_action='continue',started_jst='2026-10-23T17:29:18.868914+09:00',finished_utc=now(),elapsed_minutes=elapsed)
    js(UNIT/'STATUS.json',status)
    table=[]
    for r in dev:
        a=r['arms']['cross_matched'];b=r['arms']['base_matched']
        table.append(f"| {r['view']} | {r['target_pixels']}/{r['interior_pixels']} | {a['target_visible_ink_L1']:.2f}/{b['target_visible_ink_L1']:.2f} | {a['visible_ink_pixels']}/{b['visible_ink_pixels']} | {a['components']}/{b['components']} | {a['far_absolute_L1']:.4f}/{b['far_absolute_L1']:.4f} |")
    report=f'''# Unit002：相同BUILD可见墨量下的排线方向层比较

**冻结实验执行完成；单方向质量收益未建立，不替换现有交叉风格；scientific_seal=false。**

本轮唯一主变量为Lego作者region4的方向层集合：两层对照、仅既存layer0。沿用原核20122个选择权重、完整310475行身份、M1/UNKNOWN、纸底、S、代理网格、保存路径、线宽、遮挡和2×采样。原PLY/SH/几何/opacity/行序未变。Chair未重跑，引用unit001的四个未修改结果。

协议 `{sha(UNIT/'PROTOCOL.json')}`、29个输入、实验源码及九帧相机在评估前冻结。额外审计/媒体/回放源码也在评估前独立锁定。新实现严格先在2×覆盖层取max再降采样；四个BUILD和四个DEV双层原强度墨层/结果与unit001逐值一致，没有因拆层引入抗锯齿变化。

BUILD目标内实际hybrid-paper RGB L1：交叉5566.2171，单层3591.1647；公共预算3411.6065，为较小可达效果的95%。冻结全局衰减系数交叉0.6129129367、单层0.95，实际合成预算相对误差均低于2.1e-8。原强度两臂同时保留。公共预算只有旧交叉效果的61.29%，不能把配平图更淡当作质量提升；DEV的单/双效果比为{min(r['single_to_cross_effect_ratio'] for r in dev):.3f}–{max(r['single_to_cross_effect_ratio'] for r in dev):.3f}，未按DEV重配。

## 实际结果

表中成对数字均为“配平交叉/配平单层”。可见墨像素采用alpha>0.05；连通块为8邻接图像诊断，交叉会连接块，因此不能直接解释为真实路径断裂数。

| 视角 | 全目标/腐蚀内部像素 | 目标可见墨L1 | 可见墨像素 | 图像连通块 | 远区绝对L1 |
|---|---:|---:|---:|---:|---:|
{chr(10).join(table)}

单层可见墨覆盖在四视角分别下降{', '.join(f"{r['single_coverage_loss_fraction']*100:.2f}%" for r in dev)}。弱角度241°/24°实际目标墨量491.14对473.90，差异仅约3.51%，但可见墨像素1042降至718，单层仍为断续碎线。其投影中心线有墨支持长度代理为1180.86对604.27px；这包含两臂不同路径数及重叠信用，不能当作等几何连续性优劣。

所有13份记录两臂墨层远区L1均为0；源纸底固定，两臂远区绝对损伤完全相同。远区比例差异只是混合编辑总量/抵消导致的分母变化，**不是局部性改善**。四DEV内部明显变化约97.26%–98.68%，但主要由纸底造成，不能借此宣称墨线可用性。所有完整/内部/边界/其他部件/背景的mean、sum与可见覆盖均在逐视图EVALUATION.json；SUMMARY.json保留原强度及配平四臂读数。

实际检查ALL_DEV_VIEWS、ALL_ARC_FRAMES全部九相机结果及弱角度墨层图。单层在局部减少横向交叉，但整物体上并未稳定获得更清楚的铲斗形体；在后侧低角度仍有碎线、黄/灰纹理和照片残留。墨线减少使部分连接消失，不能说已经修复连续性。故结论为收益未建立，保留旧交叉默认。本轮未进一步调整角度、密度、源选择或深度阈值。

九帧是真实231°–251°、仰角24°、距离5.3的相机短弧。八个新相机重新渲染完整原GS source/paper与原ID S；241°帧使用同相机旧缓存且严格核对相机。九帧展示中碎线问题持续存在；没有独立共同可见对应或时序指标，不宣称闪烁被消除。4个DEV加9个短弧记录只有12个独立相机设置，不能当作13个独立样本。

## 验证与运行缺口

3项针对性TDD：先RED缺模块rc1，后GREEN rc0，包含48段真实路径、2×合成次序、固定锚点/身份、可见效果配平及零责任空墨。独立复算13份保存记录的合成、墨量、目标/远区指标和新相机原ID trace；29个输入哈希保持不变。236°新相机独立冷重放，source/paper/S/双臂ink/hybrid/alpha逐数组一致。视频9帧全部解码并与保存PNG逐像素一致。

arc_0_001外层工具返回143，子进程退出码缺失，原因UNKNOWN。其完成清单、全部数组与日志保留，通过后续独立验证，未重跑或补造rc0。其余科学阶段和独立验证/回放/媒体均有实际rc0回执。执行状态completed表示冻结的有限实验payload完成；不表示退出记录完整或科学认证。

原v05稀疏capsule弱角度8.044%远区失败与4.49%区域可见变化保持；本轮不重评该不同目标任务。unit001责任门控优势未建立、旧中断/媒体失败和其他历史负结果均未覆盖。CPU replica、作者代理自洽和协方差平面深度局限保持；不是原生Gaussian排线、语义/物理归属或H1/H2/H3证据。

## 下一步

NEXT=continue：{next_step}

{reason}

生成报告时约耗时{elapsed:.2f}分钟；本轮没有启动下一科学单元。可复放入口与依赖见README_ZH.md。
'''
    output_guard(UNIT/'REPORT_ZH.md').write_text(report)
    readme='''# Unit002 结果与复放

本包是原Gaussian纸底加代理排线的有限对照。单层未建立视觉质量优势，保留交叉默认。

- `ALL_DEV_VIEWS.png`：四个完整物体视角，原GS、旧交叉强度、配平交叉、配平单层。
- `ALL_ARC_FRAMES.png`：九个实际相机的两臂结果。
- `media/layer_comparison_arc_ffv1.mkv`：4fps、九帧、三列完整物体视频，全部无损解码验证。
- `dev/`、`arc/`：每视图source、intent、paper、四臂结果/墨层、FRAME.npz和指标。八个新相机另含TRACE.npz。
- `PROTOCOL.json`、`BUILD_MATCH.json`、`SUMMARY.json`、`VALIDATION.json`、`STATUS.json`和`REPORT_ZH.md`记录协议、比较、检查与局限。

本机冷复放一个已冻结新相机，必须指定新的输出名称，禁止覆盖现有结果：

```bash
V06_UNIT_DIR=/mnt/hdd1/u00134/partwise_sketch_hatching_gaussian_link_v06/units/unit_002 CUDA_VISIBLE_DEVICES='' /mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_8build_part_prior_feasibility_v03/venv/bin/python -B /mnt/hdd1/u00134/partwise_sketch_hatching_gaussian_link_v06/units/unit_002/audit_source/replay_layer_ablation.py --index 2 --name cold_replay_review_002
```

它实际重渲染完整原GS及冻结笔触，并核对已保存结果，写入本unit的新子目录。`--index`为0–8。无GPU，数值单线程、两核亲和。原始PLY、v05资产/M1、unit001缓存及已安装Python/依赖仍是外部输入；路径和SHA见PROTOCOL.json，不声称完全便携。`source_snapshot/`是评估前冻结实验代码；`audit_source/`是独立锁定的验证、回放和媒体代码。原文件只读。

该短弧不是固定相机墨量渐变，也不是360°转台或时序稳定性认证。arc首帧的外层143/子退出码UNKNOWN记录见INTERRUPTION_arc_0_001.json，后续验证不抹去它。
'''
    output_guard(UNIT/'README_ZH.md').write_text(readme)
    js(UNIT/'HANDOFF_SOURCE_LOCK.json',dict(path=str(Path(__file__).resolve()),sha256=sha(__file__)))
    print('HANDOFF',status['scientific_verdict'],'elapsed',elapsed,flush=True)

if __name__=='__main__':main()
