"""Post-inspection handoff only; never changes frozen experiment results."""
import runtime
from runtime import ACTIVE_UNIT as UNIT,js,sha,now
from pathlib import Path
from collections import Counter
import json
import shutil

def main():
    p=json.loads((UNIT/'PROTOCOL.json').read_text());m=json.loads((UNIT/'BUILD_MATCH.json').read_text())
    assert (UNIT/'VALIDATION.json').exists() and (UNIT/'MEDIA_VALIDATION.json').exists()
    rows=[]
    for v in [v for v in p['views'] if v['kind']!='build']:
        e=json.loads((UNIT/v['kind']/v['camera']['view']/'EVALUATION.json').read_text());a=e['attribution']['all']
        row=dict(kind=v['kind'],view=v['camera']['view'],target_pixels=e['metrics']['legacy_matched']['target_full']['pixels'],interior_pixels=e['metrics']['legacy_matched']['target_interior']['pixels'],proxy_visible_length=a['proxy_visible_length'],arms={})
        for arm in ('legacy','interval'):
            key=arm+'_matched';m0=e['metrics'][key];ink=e['ink'][key]
            row['arms'][arm]=dict(target_ink_L1=ink['target_visible_ink_L1'],visible_ink_pixels=e['shape'][key]['visible']['pixels'],
                target_L1_mean=m0['target_full']['raw_L1_mean'],target_L1_sum=m0['target_full']['raw_L1_sum'],interior_useful_fraction=m0['target_interior']['useful_fraction_0_05'],
                far_other_L1=m0['far_other']['raw_L1_sum'],far_background_L1=m0['far_background']['raw_L1_sum'],far_ink_L1=ink['far_visible_ink_L1'],
                own_missing_before_S=a[arm+'_before_S']['visible_missing_length'],own_missing_matched=a[key]['visible_missing_length'],
                own_occluded_supported_matched=a[key]['occluded_supported_length'])
        row['restored_fraction_of_proxy_visible_length']=(row['arms']['legacy']['own_missing_matched']-row['arms']['interval']['own_missing_matched'])/a['proxy_visible_length']
        row['matched_effect_ratio']=row['arms']['interval']['target_ink_L1']/row['arms']['legacy']['target_ink_L1'];rows.append(row)
    endpoints=json.loads((UNIT/'STORED_PATH_ENDPOINTS.json').read_text())['records'];counts=Counter(x[k] for x in endpoints for k in ('start_class','end_class'))
    summary=dict(records=rows,endpoint_counts=dict(counts),stored_internal_discontinuities=sum(x['stored_internal_discontinuities'] for x in endpoints),
        verdict='SMALL_RENDER_SUPPORT_GAIN; WHOLE_OBJECT_QUALITY_GAIN_NOT_ESTABLISHED; NO_DEFAULT_PROMOTION',default_renderer_changed=False)
    js(UNIT/'SUMMARY.json',summary)
    nextstep='固定现有原核集合、M1/UNKNOWN和交叉墨层，测试同支撑的饱和纸底传递：当前s=q与仅已选20122个原核s=1的真实完整GS颜色副本比较，直接检查能否消除整区域照片残留；同时分解未选/UNKNOWN贡献与已选核未饱和贡献。明确这是源效果不等的容量上限对照，不宣称选择优势，不扩张标签或修改原PLY。若饱和上限仍斑驳，就将下一瓶颈定位为原核支持覆盖，而不是继续调墨层可见性。'
    why='本轮可见性修改只恢复少量笔触支持，完整物体和九帧短弧没有明确可读性收益；独立纸底图已显示明显黄灰纹理。去纹理的源层容量是不同于继续改遮挡或门控的有用路线。'
    js(UNIT/'NEXT.json',dict(action='continue',recommended_next_step=nextstep,why=why,
        preserve='v05 sparse failure, unit001 gate negative, unit002 style negative and historical UNKNOWN exit records remain immutable; unit003 no quality promotion.'))
    science_stages=['tdd_red_001','tdd_green_001','freeze_001','build_001']+[f'dev_{i}_001' for i in range(4)]+[f'arc_{i}_001' for i in range(9)]+['validation_001','replay_001','media_001','cache_replay_001']
    commands=[]
    for stage in science_stages:
        file=UNIT/'logs'/f'{stage}.receipt.json';receipt=json.loads(file.read_text());expected=1 if stage=='tdd_red_001' else 0
        assert receipt['returncode']==expected,(stage,receipt)
        commands.append(dict(stage=stage,receipt=str(file),**receipt))
    dev=[x for x in rows if x['kind']=='dev'];weak=dev[1];a=weak['arms'];visible=weak['proxy_visible_length']
    start=json.loads((UNIT/'logs/tdd_red_001.start.json').read_text())['utc']
    status=dict(unit='unit_003',execution_state='completed',stage='validated_visibility_mechanism_handoff',work_in_progress=False,scientific_seal=False,
        scientific_verdict=summary['verdict'],default_renderer_changed=False,changed_variable=p['changed_variable'],
        gaussian_link_progress=dict(M1='Unchanged complete 310475 original-row universe, UNKNOWN, and 20122 selected weights.',
            M2='Frozen proxy face/bary/path/stroke/layer identities unchanged; per-stroke visibility and endpoints now diagnosed.',
            M3='Real original-GS source/paper/S reused and two full GS cold renders exactly reproduced; only proxy ink visibility changed. Minor support recovery, no established whole-object quality benefit.',
            M4='All four DEV and nine actual arc frames, independent readback, decoded movie, repeatable cached CLI and exact cold replay available.'),
        tests=dict(targeted_TDD=3,red_rc=1,green_rc=0,BUILD_legacy_exact=4,evaluation_records=13,unique_evaluation_cameras=12,immutable_inputs=54,
            original_ID_S_trace_verified_records=13,cold_GS_render_calls=2,cold_replay_exact=True,decoded_frames=9,cache_CLI_replay_exact=True),
        commands=commands,blockers=[],artifacts=['PROTOCOL.json','BUILD_MATCH.json','SUMMARY.json','STORED_PATH_ENDPOINTS.json','ALL_DEV_VIEWS.png','ALL_ARC_FRAMES.png','media/visibility_arc_ffv1.mkv','VALIDATION.json','cold_replay_001/REPLAY.json','README_ZH.md'],
        limitations=[p['scope'],p['sampling_reference'],p['interval_uncertainty'],'The signed owner-plane foreground guard remains a proxy approximation; fixtures do not certify general occlusion.','Paper texture residue is unchanged.'],
        inherited_negatives=p['inherited_negatives'],scientific_process_receipts_complete=True,started_test_utc=start,generated_utc=now(),
        administrative_receipt='Current finish process is omitted from scientific command list; see logs/finish_001.receipt.json after it exits.')
    js(UNIT/'STATUS.json',status)
    table=[]
    for r in dev:
        x=r['arms']['legacy'];y=r['arms']['interval']
        table.append(f"| {r['view']} | {r['target_pixels']}/{r['interior_pixels']} | {x['target_ink_L1']:.2f}/{y['target_ink_L1']:.2f} | {x['visible_ink_pixels']}/{y['visible_ink_pixels']} | {x['own_missing_matched']:.2f}/{y['own_missing_matched']:.2f} | {x['far_other_L1']+x['far_background_L1']:.4f}/{y['far_other_L1']+y['far_background_L1']:.4f} |")
    report=f'''# Unit003：中心线可见区间与原逐片元规则的对照

**冻结实验完成；少量渲染支持改善，整物体质量收益未建立；保留旧默认后端。scientific_seal=false。**

唯一主变量为固定排线路径的可见性求值。新规则以≤0.25原尺寸像素间隔投射真实中心线代理射线，按可见采样单元生成区间胶囊；区域支持和0.004容差不变，锚定面深度保留为单侧前景遮挡保护。两臂固定交叉层{{0,1}}、1px线宽、2×采样、全部三维路径/face/bary/stroke ID、M1/UNKNOWN、20122个原核权重、纸底及原ID责任S。未修改旧render.py或默认风格。该后端的深度保护仍是代理近似，不能声称普遍遮挡正确。

协议SHA256 `{sha(UNIT/'PROTOCOL.json')}`。54个输入、全部实验/审计/媒体源码和相机在评估前冻结。四BUILD的旧墨层逐值等于unit001；13份DEV/arc旧原强度结果逐值等于unit002。所有原PLY、完整310475行身份、几何、协方差、opacity、SH不变。

BUILD目标可见墨L1：旧{m['raw_target_visible_ink_L1']['legacy']:.4f}，新{m['raw_target_visible_ink_L1']['interval']:.4f}；公共预算{m['budget']:.4f}，全局衰减旧{m['scales']['legacy']:.10f}、新{m['scales']['interval']:.10f}。保留原强度和配平两组，DEV/arc没有重配。

## 实际视觉和覆盖

已检查ALL_DEV_VIEWS、ALL_ARC_FRAMES全部九帧及弱角度独立墨层。新图仅局部补宽或接续极短墨段，四个完整物体及短弧中没有明确更清楚的铲斗形体；黄/灰照片残留、计划短笔触和杂乱交叉仍在。不能把像素/连通块改善当作可用性成功。

下表数字均为旧/新，墨像素阈值alpha>0.05；长度以投影像素计，是逐stroke自身墨层的采样支持，其他笔触不能提供重叠信用。

| 视角 | 全目标/内部像素 | 配平目标墨L1 | 可见墨像素 | 可见区自身缺失长度 | 远区绝对L1 |
|---|---:|---:|---:|---:|---:|
'''+ '\n'.join(table)+f'''

弱角度241°/24°的代理可见长度{visible:.2f}px；乘S前旧/新缺失{a['legacy']['own_missing_before_S']:.2f}/{a['interval']['own_missing_before_S']:.2f}px。旧规则本来已支持约{100*(1-a['legacy']['own_missing_before_S']/visible):.2f}%的代理可见中心线，说明遮挡裁切并非全部碎线的主要来源。配平并乘S后缺失{a['legacy']['own_missing_matched']:.2f}/{a['interval']['own_missing_matched']:.2f}px，仅恢复代理可见总长度的{100*weak['restored_fraction_of_proxy_visible_length']:.2f}%。该归因不能证明M1门控应当删除；unit001的配平门控对照已未建立优势。

路径记录有351个stroke、1904段，内部存储断点总数{summary['stored_internal_discontinuities']}；端点分类：{json.dumps(dict(counts),ensure_ascii=False)}。面内端点按原生成器解释为计划长度截断；共享边歧义明确保留，没有把所有断裂归为bug，也没有补连不同stroke。

逐视图ATTRIBUTION.json与SAMPLES.npz保存区域拒绝、代理深度拒绝、乘S前后及配平后的自身支持；layer0另列。精确中心线射线与原尺寸四舍五入墨像素位置不同，故“遮挡中心线附近有墨”包含量化/轮廓过渡，不是实测穿透真值。样本和分母全部保留，没有剔除困难角度。

所有13份记录墨层远区L1均为0，原纸底固定使两臂远其他部件和背景绝对损伤完全相同。混合远区比例的变化只是总变化分母差异，不能称局部性提升。完整/腐蚀内部/边界/远其他部件/背景mean、sum、可见覆盖均保存在EVALUATION.json；内部大面积变化主要来自纸底，不代表墨线可用。

## 验证与可复现性

3项针对性TDD先RED缺模块rc1，后GREEN rc0：真实共享边路径和旧光栅逐值一致；同region不相连前景正确挡住笔触；计划间隙保持，S=0为空墨，锚点身份不变。独立复算13份保存结果/自身长度统计，并在原始ID trace上重建S；54个输入哈希保持。236°独立冷重放实际完整原GS两次，source/paper/S、旧新墨层/alpha/hybrid逐数组一致，原数组哈希不变。九帧实际231°–251°短弧全部解码逐像素一致；没有独立时序真值，不宣称稳定性改善。4DEV+9arc只有12个独立相机。

另交付可选新目录的缓存CLI并实际精确复放弱角度。缓存CLI明确不重新渲染GS；真实GS冷重放另有记录。所有本轮科学阶段有实际退出回执，初始RED以外均rc0。旧v05稀疏8.044%远区失败/4.49%可见变化、unit001门控负结果、unit002单层负结果及历史143/UNKNOWN不变。本轮是原GS纸底+原ID责任连接的代理墨层实验，不是原生Gaussian排线、独立语义/物理或H1/H2/H3证明。

## 下一步

NEXT=continue：{nextstep}

{why}
'''
    (UNIT/'REPORT_ZH.md').write_text(report)
    handoff=UNIT/'handoff_source';handoff.mkdir(exist_ok=False)
    for name in ('finish_visibility_unit.py','replay_visibility_cache.py'):
        shutil.copy2(Path(__file__).with_name(name),handoff/name)
    js(UNIT/'HANDOFF_SOURCE_LOCK.json',dict(files={f.name:sha(f) for f in handoff.iterdir()}))
    readme=f'''# Unit003 复放

结论：可见性后端有小幅自身墨支持改善，整物体质量收益未建立，旧默认保持。

查看REPORT_ZH.md、ALL_DEV_VIEWS.png、ALL_ARC_FRAMES.png，以及media/visibility_arc_ffv1.mkv。每视图有FRAME.npz、SAMPLES.npz、ATTRIBUTION.json和EVALUATION.json。

缓存精确复放到一个尚不存在的新目录（不要覆盖已有replay_*）：

```bash
/mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_8build_part_prior_feasibility_v03/venv/bin/python -B {UNIT}/handoff_source/replay_visibility_cache.py --unit {UNIT} --kind dev --index 1 --name replay_user_001
```

此CLI依赖本机冻结unit001/002缓存、原代理资产和Python/Open3D，不是完全便携包。通过source_snapshot的v06 runtime限定串行两CPU、禁GPU。完整原GS冷重放证据见cold_replay_001/REPLAY.json及TRACE.npz；其两次实际GS渲染与缓存逐数组一致。CLI本身GS_render_calls=0，重新计算的是冻结路径的两种代理墨层，再用实际原GS缓存和原ID S合成。

source_snapshot保存评估前冻结源码，PROTOCOL/INPUT/source哈希不得改动。原始PLY、M1完整行映射和UNKNOWN为外部只读依赖；任何新实验应另建授权单元。运行记录见STATUS.json和logs/*.receipt.json。
'''
    (UNIT/'README_ZH.md').write_text(readme)
    js(UNIT/'ARTIFACT_MANIFEST.json',dict(utc=now(),scientific_seal=False,files={str(f.relative_to(UNIT)):sha(f) for f in UNIT.rglob('*') if f.is_file() and f.name not in ('ARTIFACT_MANIFEST.json','STATUS.json') and 'logs' not in f.parts and 'orchestration' not in f.parts}))
    print('HANDOFF',summary['verdict'],'NEXT continue',flush=True)
    print('\n'.join(table),flush=True)

if __name__=='__main__':main()
