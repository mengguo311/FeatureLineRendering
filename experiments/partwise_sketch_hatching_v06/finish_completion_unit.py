"""Post-result handoff only. Does not change selection, experiment or old units."""
import runtime
from runtime import ACTIVE_UNIT as UNIT,js,sha,now,output_guard
from pathlib import Path
import datetime
import json


def main():
    read=lambda f:json.loads((UNIT/f).read_text())
    p=read('PROTOCOL.json');summary=read('SUMMARY.json');validation=read('VALIDATION.json')
    media=read('MEDIA_VALIDATION.json');replay=read('cold_replay_001/REPLAY_CHECK.json');match=read('BUILD_MATCH.json')
    assert len(validation['views'])==13 and all(media['all_frames_decoded_exact']) and all(replay['exact'].values())
    assert sha(UNIT/'PROTOCOL.json')==read('PROTOCOL_LOCK.json')['sha256']
    assert sha(UNIT/'DECISION.json')==p['decision_sha256']
    dev=[r for r in summary['records'] if r['kind']=='dev'];arc=[r for r in summary['records'] if r['kind']=='arc']
    sel=summary['selection'];receipts=[]
    for f in sorted((UNIT/'logs').glob('*.receipt.json')):
        r=json.loads(f.read_text());receipts.append(dict(name=f.name,argv=r['argv'],returncode=r['returncode'],elapsed_seconds=r['elapsed_seconds']))
        assert r['returncode']==(1 if f.name=='tdd_red_001.receipt.json' else 0),f.name
    expected=['freeze_001','select_001','budget_001','audit_001','replay_001','media_001','tdd_green_001']
    expected += [f'footprint_{i}_001' for i in range(12)]+[f'dev_{i}_001' for i in range(4)]
    expected += [f'arc_{i}_'+('002' if i==5 else '001') for i in range(9)]
    for name in expected:assert (UNIT/'logs'/(name+'.receipt.json')).exists(),name
    started=datetime.datetime.fromisoformat('2026-10-23T09:27:25.897615+00:00')
    elapsed=(datetime.datetime.now(datetime.timezone.utc)-started).total_seconds()/60
    verdict='VISIBLE_NATURAL_SUBSTRATE_CAPACITY_GAIN; MATCHED_INTERIOR_RESIDUAL_NO_GAIN; FAR_DAMAGE_TRADEOFF; NPR_QUALITY_PARTIAL; NO_DEFAULT_PROMOTION'
    next_step='固定unit004自然强度补全纸底、原核许可和旧S，单独测试排线生成器的计划间隙gap=0.035对gap=0。沿用同一组世界切平面、角度、spacing、length=0.12、作者区域、代理连接链、线宽与旧遮挡；只填同一连续代理链内原计划留出的弧长区段，不跨网格孔洞、区域边界或遮挡。重新生成的路径/笔触身份作为新风格变体明确保存，不能伪称旧路径修复。四个BUILD按实际可见墨RGB L1配平，并同时保留原强度，检查四DEV与弱角度短弧的完整物体可读性。先验证共享边连续和真实边界不被跨越。仍无视觉收益则保留负结果，不继续扫描长度/间距。'
    why='补全已让纸底明显更白，但残留黄灰面和断续交叉线仍限制NPR；同源效果配平没有内部残留优势，故不继续靠加核或放松门槛追白。unit003已发现329个面内计划长度端点且没有存储内部断点；源码明确使用length=0.12和硬编码gap=0.035。去除计划间隙是独立、可证伪的局部风格操作，区别于已失败的单层替换和微调遮挡。'
    js(UNIT/'NEXT.json',dict(action='continue',recommended_next_step=next_step,why=why,
        preserve='v05 sparse failure and all unit001-004 negatives/interruptions remain immutable; next unit still requires parent-frozen read-only Astra review.'))
    rows=[];matched_rows=[]
    for r in dev:
        o=r['arms']['original'];n=r['arms']['completed'];om=r['arms']['original_matched'];nm=r['arms']['completed_matched']
        rows.append(f"| {r['view']} | {r['target_pixels']}/{r['interior_pixels']} | {o['interior_residual_mean']:.4f}/{n['interior_residual_mean']:.4f} | {100*r['residual_reduction']['natural']['target_interior']:.2f}% | {100*o['near_paper_fraction']:.2f}/{100*n['near_paper_fraction']:.2f}% | {o['far_other_L1']:.4f}/{n['far_other_L1']:.4f} | {o['far_background_L1']:.4f}/{n['far_background_L1']:.4f} |")
        matched_rows.append(f"| {r['view']} | {om['interior_residual_mean']:.4f}/{nm['interior_residual_mean']:.4f} | {100*r['residual_reduction']['matched']['target_interior']:.2f}% | {om['far_other_L1']+om['far_background_L1']:.4f}/{nm['far_other_L1']+nm['far_background_L1']:.4f} |")
    report=f'''# Unit004：可见纸底容量提升，配平收益未成立

**冻结实验完成。自然强度纸底斑驳减少；同源RGB编辑预算下内部残留未改善，远区有代价；NPR仍不完整，不升级默认。scientific_seal=false。**

本轮唯一主变量是原核纸底的外观支持补全。原20122核及q权重不变，12个既有BUILD的完整alpha×T footprint依冻结规则新增{sel['added_original_rows']}核，合计{sel['final_selected']}核。新增核仍为UNKNOWN；完整M1的{sel['M1_unknown_unchanged']}个UNKNOWN、标签、冲突、原深度证据均未改写。新增原因分类：{json.dumps(sel['added_by_M1_reason'],ensure_ascii=False)}。这不是给UNKNOWN强制补语义标签。

只在UNKNOWN且无跨视角冲突的行中选择：目标累计质量≥0.02、至少两个视角各有≥0.002目标质量、目标/总质量≥0.7、累计远区比例≤0.02、总质量≥0.02的各视角远区比例≤0.05。目标仍为完整作者region4，边界带仍为2px。新外观许可不要求M1深度资格；第五深度接受通道仅作诊断，因而不能把投影局部性解释成物理表面归属。

协议SHA256 `{sha(UNIT/'PROTOCOL.json')}`。55个输入、12个BUILD及4DEV/9arc相机、全部实验/审计/媒体源码在BUILD前冻结。全像素累积器从v05只读源码逐字复制，使用v06本地运行时和输出目录。原310475行、原PLY、几何、协方差、opacity、完整SH与行序不变；颜色在完整SH3求值后仅对副本混合到(0.95,0.95,0.95)，实际渲染完整GS。

## 实际视觉和自然强度结果

已检查四个完整物体自然/配平面板、弱角度单图与全部九帧短弧。补全纸底在多个铲斗面上明显更白，原黄灰斑驳有所减少；后侧弱角度也可见该变化。但前侧仍有明显黄色区域，后侧仍有残余斑块，固定交叉线仍呈断续和杂乱。不能把纸底变白写成排线连续性或整套NPR已经可用。原代理墨alpha与旧原ID责任S逐值固定，源纸底与墨层分别交付。

残留为纸底到固定纸色的clipped RGB L1。下表成对数字为旧/补全；“近纸色”阈值为内部L1≤0.15，是辅助描述而非新通过门槛。远区使用raw RGB L1绝对和，其他部件与背景分列。

| 视角 | 全目标/内部像素 | 内部残留mean | 残留下降 | 内部近纸色比例 | 远其他L1 | 背景L1 |
|---|---:|---:|---:|---:|---:|---:|
{chr(10).join(rows)}

自然强度四视角内部残留下降45.14%–61.50%，冻结的20%残留筛查4/4，包含弱角度；远区比例参考也为4/4。弱角度平均原核替换责任从0.5754升至0.7614，但195600个UNKNOWN仍在。目标内部明显编辑像素比例约98.57%–99.60%，这仅说明编辑发生，不能替代线条质量。

自然强度的远区绝对损伤在四视角均增加：总L1依次16.3964→18.8854、2.5075→3.2938、17.6534→20.3460、2.8690→4.4345。比例为0.0704%–0.7425%，多数比例下降有总编辑量增大的分母因素，不能称局部性提高。整物体图未见大块新增外溢，但细小损伤仍保留在统计和原始输出中。边界、完整/腐蚀目标、远其他和背景的mean/sum/覆盖均在逐视图EVALUATION.json。

## 相同源RGB预算的负结果

四个原BUILD自然源编辑L1：旧{match['natural_source_RGB_L1']['original']:.4f}，补全{match['natural_source_RGB_L1']['completed']:.4f}；补全用了更多源编辑量。公共预算{match['budget']:.4f}，全局衰减系数旧{match['scales']['original']:.10f}、补全{match['scales']['completed']:.10f}。两臂在四个BUILD上实际重渲染后配平，无DEV拟合。

| 视角 | 配平内部残留mean旧/补全 | 残留下降，负数为退化 | 配平远区总L1旧/补全 |
|---|---:|---:|---:|
{chr(10).join(matched_rows)}

配平后的内部残留四视角均未改善，退化0.59%–20.94%；弱角度补全图更均匀偏灰，但不能称更干净的纸底。配平远区绝对损伤两视角减少、两视角增加，无统一局部性优势。本轮支持同一冻结GS通过新增外观许可获得更高去纹理容量，不支持同预算选择优势。墨alpha没有随配平重新调整；纸底变化引起的实际墨RGB对比度已单独记录，不能当成新笔触或更好附着。

九帧231°–251°实际短弧的自然内部残留下降约{100*min(r['residual_reduction']['natural']['target_interior'] for r in arc):.2f}%–{100*max(r['residual_reduction']['natural']['target_interior'] for r in arc):.2f}%；配平后内部残留仍均未改善。4DEV+9arc共12个独立相机设置。全部为已曝光诊断视角，没有独立时序真值，不宣称泛化或闪烁改善。

## 验证、回放及中断

三项针对性TDD先RED缺模块rc1，后GREEN rc0，含真实原核的全像素贡献分区、非连续原ID映射、零编辑及ID置换响应。独立读回重新计算补全集，核验12份全像素质量分区、完整行身份和未变M1；55个输入哈希保持。13份结果均从真实原ID trace重建原源RGB、四种纸底及原/新增支持；固定墨alpha、旧纸底与旧混合输出逐值一致。

弱角度独立冷重放实际渲染5次完整GS；source/alpha/新增支持、四种纸底与混合图均逐数组一致。九帧FFV1视频全部解码并与保存PNG逐像素一致。README_ZH.md提供真正冷重放CLI和外部依赖说明。

短弧批次外层工具会话40402返回143。arc_4_001已有子rc0；arc_5_001只有启动记录和空日志，子退出码与原因UNKNOWN，空输出目录保存在interrupted_attempt_001，原日志不覆盖。确认无本轮数值进程后，以arc_5_002新回执完成缺失帧rc0，其余帧单独执行。所有最终科学阶段和验证均有实际rc0回执；未给旧失败补造成功码。

v05弱角度稀疏capsule远区8.044%与仅4.49%作者区域可见变化保持，不能用本轮不同区域操作倒算通过。unit001责任门控收益未建立、unit002单层负结果、unit003微小可见性收益但整物体质量未建立，以及历史中断/配额失败均保留。CPU replica、代理自洽、协方差平面深度的局限不变；这是原GS纸底加代理排线的关联混合资产，不是原生Gaussian排线、语义/物理归属或H1/H2/H3证明。

## 下一步

NEXT=continue：{next_step}

{why}

报告生成时本轮执行约{elapsed:.2f}分钟；本轮没有启动下一科学单元。
'''
    output_guard(UNIT/'REPORT_ZH.md').write_text(report)
    js(UNIT/'STATUS.json',dict(unit='unit_004',execution_state='completed',stage='validated_appearance_completion_handoff',
        scientific_verdict=verdict,scientific_seal=False,finished_utc=now(),elapsed_minutes=elapsed,
        frozen_experiment_execution_complete=True,finished_within_45_minutes=elapsed<=45,
        gaussian_link_progress=dict(
            M1='Complete 310475 original rows and 195600 UNKNOWN labels unchanged; no semantic promotion.',
            M2='Same proxy anchors, paths, layers and legacy raw ink alpha/S; no new stroke geometry in this unit.',
            M3='19352 additional original-row appearance permissions, 39474 edited rows total. Actual full-GS paper improves natural-strength residual 45.14%-61.50%; matched interior residual worsens in all four DEV, far damage tradeoff retained.',
            M4='Twelve full-footprint BUILD records, four DEV and nine arc outputs, independent trace readback, five-render exact cold replay, decoded movie and runnable CLI.'),
        numerical_screen=summary['numerical_screen'],default_renderer_or_style_changed=False,
        artifacts={k:str(UNIT/k) for k in ('README_ZH.md','REPORT_ZH.md','PROTOCOL.json','SELECTION.npz','SUMMARY.json','VALIDATION.json','ALL_DEV_VIEWS.png','ALL_DEV_MATCHED.png','ALL_ARC_FRAMES.png','MEDIA_VALIDATION.json','cold_replay_001/REPLAY_CHECK.json','media/paper_completion_arc_ffv1.mkv')},
        tests_and_actual_commands=receipts,blockers=[],
        limitations=['Equal-effect interior residual advantage not established','M1 UNKNOWN retained and projected appearance permission is not physical ownership','Residual photo texture and broken-looking cross ink remain','Exposed proxy-authored views and CPU replica only'],
        interruption=read('logs/ARC_BATCH_INTERRUPTION_001.json'),next_action='continue'))
    files={str(f.relative_to(UNIT)):dict(sha256=sha(f),bytes=f.stat().st_size) for f in UNIT.rglob('*') if f.is_file() and f.name!='ARTIFACT_MANIFEST.json' and not str(f.relative_to(UNIT)).startswith('scratch/') and not f.name.startswith('finish_001.')}
    js(UNIT/'ARTIFACT_MANIFEST.json',dict(utc=now(),scientific_seal=False,scope='Finite unit artifacts; not a mutable global/runtime science seal.',files=files))
    print('HANDOFF',verdict,'elapsed_minutes',elapsed,'artifacts',len(files),flush=True)


if __name__=='__main__':main()
