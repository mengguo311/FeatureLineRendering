"""Report the frozen field experiment without altering its scientific artifacts."""
import runtime
from runtime import ACTIVE_UNIT as UNIT,HERE,OUTPUT_ROOT as ROOT,sha,js,now
import json,shutil,datetime

def load(p):return json.loads(p.read_text())

def main():
    a=load(UNIT/'asset/ASSET.json');d=load(UNIT/'DIRECTION_READBACK.json');audit=load(UNIT/'AUDIT.json')
    summary=load(UNIT/'SUMMARY.json');match=load(UNIT/'BUILD_MATCH.json');far=load(UNIT/'FAR_READBACK.json');visible=load(UNIT/'VISIBLE_INTERVENTION.json');attr=load(UNIT/'attribution/SUMMARY.json')
    replay=load(UNIT/'cached_field_replay/REPLAY_RECEIPT.json');assert audit['status']=='pass' and replay['all_equal']
    commands={p.stem:load(p) for p in sorted((UNIT/'logs').glob('*.json'))}
    assert commands['field_RED']['child_returncode']==1
    assert commands['handoff']['child_returncode']==1
    assert all(x['child_returncode']==0 for key,x in commands.items() if key not in ('field_RED','handoff'))
    # Preserve the original filename and record the display lookup failure.
    wrong=UNIT/'REAR_CAMERF0_SEQUENCE.png';right=UNIT/'REAR_CAMERA_SEQUENCE.png'
    assert wrong.exists() and not right.exists();shutil.copyfile(wrong,right);assert sha(wrong)==sha(right)
    js(UNIT/'ENGINEERING_NOTES.json',dict(display_lookup_failure=dict(tool='view_image',requested=str(right),error='No such file or directory',
        cause='The initial A_ -> F0_ helper adaptation also changed CAMERA_SEQUENCE to CAMERF0_SEQUENCE.',
        remedy='Byte-identical correctly named alias added at handoff; original PNG and frozen producer retained; no rerender or scientific source change.'),
        attribution_quadrature='F0 adds one seed split per original stroke. The unchanged sampler samples each segment separately, so F0 centerline quadrature differs slightly from older A although every rendered pixel is identical. Compare F0/F1 within this unit, not F0 versus historical A sampling totals.'))
    next_step='下一次只读审查并冻结后，优先检验尚未改变的跨笔触空间布置机制：在原始载体、固定F0场及同一行走器上，对照原切片中点种子与确定性的表面间距约束种子放置。先检查保存路径的同层拥挤/空白及边界短笔触是否确有可改善空间，不能凭交叉层的预期交点虚构同层碰撞。若有，按旧/新增分区及方向层保持种子数量与请求长度分布，用真实拓扑上的距离约束放置固定3D种子并生成新身份；禁止屏幕距离筛选、跨分离片KNN、删困难区域或增加笔触长度来冒充相同风格。只比较这一生成器机制，保留自然及同BUILD可见墨预算的pre-S/linked/ungated完整前后图。若无实际间距问题则不实施该臂，转向有证据的独立诊断；不扫描本轮正则化强度、不叠加C、不放宽遮挡。'
    why='unit001续接、unit002有界载体变化和本轮共享场正则化均未建立整物体优势；本轮F0精确恢复原A，F1确有可见方向变化却仍保留原切片种子/长度组织。固定种子的场平滑没有检验M5跨笔触空间布置；这与再次调角、调平滑强度或补间隙不同，是否有实际余量须由下一次审查确认。'
    js(UNIT/'NEXT.json',dict(action='continue',recommended_next_step=next_step,why=why,estimated_minutes=30,requires_next_read_only_review=True,no_new_units_after_jst='2026-10-25T14:25:00+09:00'))
    lines=['# Unit003：共享方向场更相干，但整物体收益未建立','',
        '**F0/F1真实实验完成；F0逐值恢复旧A，F1没有建立完整物体可读性优势，不升级默认。NEXT=continue，scientific_seal=false，父级验证待完成。**','',
        '已检查四个完整DEV的自然/配平图、前后pre-S/linked独立墨层、弱后视角同预算ungated对照及实际231°/241°/251°相机序列。局部线段略移位，前侧大面仍是短笔触束，后侧仍是短交叉网格、局部杂线与斑驳纸底；没有观察到足以称为整物体改进的清晰差别。这是有限目视检查，不是用户偏好研究。','',
        '## 因果比较与保持项','',
        '载体保持原16543顶点/29999面，不叠加unit002降噪。F0=t=normalize(n_face×q_layer)，q由保存unit010基底及35°/95°构造；35°/95°是切平面法向角。基底、手性和PCA结果不重估。F1用无向切向dyad做8次同步更新：每次0.5原始dyad＋0.5按邻面面积归一化的传输邻域均值；最后取主特征线，保留原方向约束，不扫描强度或次数。共享边传输按边轴/两面内向基构造，不依赖法线正负或面绕序。','',
        '平滑图仅包含同旧/新增分区的真实流形共享边；无向二面角≥60°不参与平滑。这个启发式不等于语义锐边真值，也不新增行走停止边界。两臂使用同一个分片常切向场行走器，在共享边选择进入邻面的线场符号；允许真实尖转折，不跨空间邻近面、补洞或改遮挡。','',
        '380个原笔触弧长中点种子、每条原请求长度及方向层保持；种子初始切向随场改变，未宣称它保持。原310475行Gaussian身份/顺序、源PLY/中心/协方差/opacity/完整SH、41058纸底许可及权重、21006墨责任及权重、195279 UNKNOWN及M1、2121面作者目标、旧2030/新增91分区停止、1px/AA2、0.004绝对深度容差与2px评价带保持。实际笔触间距、长度损失和交叉角是机制结果，不假装逐点风格相同。','',
        '新路径F0/F1身份分别为父ID＋300000000000/400000000000，保存face/bary、种子、层、初始切向和停止原因；这些是代理路径身份，不是原Gaussian所有权。原A、unit001 straightest B和unit002载体C保持原样。','',
        '## 有效干预与原A恢复','',
        f"平滑图{a['field']['edge_pairs']}对共享边，排除{a['field']['sharp_pairs_excluded']}对锐边；两层各{a['field']['layers'][0]['active_faces']}面参与，退化/歧义回退均0。图上面积加权方向连接能量{a['field']['raw_connection_energy']:.9f}→{a['field']['regularized_connection_energy']:.9f}。目标面场变化中位数/P95/最大={a['field']['selected_change_degrees_quantiles'][0]:.3f}°/{a['field']['selected_change_degrees_quantiles'][2]:.3f}°/{a['field']['selected_change_degrees_quantiles'][3]:.3f}°。能量只在平滑图上定义，不是全表面误差或NPR成功标准。",'',
        f"独立读回380×2个种子与unit001保存记录完全一致；最大种子误差{audit['max_seed_error']:.3g}，锚点误差{audit['max_anchor_error']:.3g}，F0端点误差{audit['max_F0_endpoint_error']:.3g}。F0全部BUILD/DEV/arc实际pre-S与自然linked均逐值恢复旧A。F0多380个种子处分段，几何长度和光栅图不变；转角统计排除同面种子分段。",'',
        '| 分区 | 实际长度 F0/F1 | 跨面转角中位数 F0/F1 | F1缩短>1e-6的笔触 |','|---|---:|---:|---:|']
    for part in ('old','added'):
        x=d['paths'][part+'_F0'];y=d['paths'][part+'_F1']
        lines.append(f"| {part} | {x['length']:.9f}/{y['length']:.9f} | {x['shared_edge_turn_degrees_quantiles'][0]:.3f}°/{y['shared_edge_turn_degrees_quantiles'][0]:.3f}° | {y['strokes_shorter_by_over_1e_6']} |")
    len0=sum(d['paths'][part+'_F0']['length'] for part in ('old','added'));len1=sum(d['paths'][part+'_F1']['length'] for part in ('old','added'))
    lines += ['',f'两臂均380条笔触、存储内部断点0；总长度{len0:.9f}→{len1:.9f}，减少{100*(1-len1/len0):.3f}%。F1共550个方向端点达到请求长度，176个遇作者分区边界、34个遇网格边界；没有场退化、边切向退化、顶点歧义、零步循环或步数保护终止。F0的760端点均记requested_length，因为继承的长度已经包含原A边界截断，不能据此宣称原A没有边界停止。',
        '新增91面分区的跨面转角P95从49.216°升至61.572°，单位长度总转角也增加；不能只报主分区中位数改善。两层表面交叉角面积均值49.895°→50.214°，小于15°面积17.096%→17.276%；没有整体方向层塌缩，但低交叉角问题也未改善。','',
        '| DEV相机 | 目标像素 | 至少一层场变化>1°的目标首交像素 | 该变化中位数 |','|---|---:|---:|---:|']
    for r in visible[:4]:lines.append(f"| {r['view']} | {r['target_pixels']} | {r['changed_field_target_pixels_over_1deg']} | {r['field_change_degrees_quantiles'][0]:.3f}° |")
    lines += ['','可见面场变化覆盖约69%–89%的目标像素，不是只改不可见面；实际图像明显差异仅覆盖约5.6%–7.8%的DEV目标像素，视觉效应有限。1°和0.05只是描述口径，不新增通过门槛。','',
        '## 可见墨预算与完整视图','',f"四BUILD自然目标墨RGB L1：{json.dumps(match['natural_totals'])}。公共预算{match['budget']:.6f}；全局系数{json.dumps(match['scales'])}。实际合成读回与预算一致到浮点误差；DEV不重新拟合，自然强度保存。",'',
        '| DEV相机 | 目标墨L1 F0/F1 | 全目标覆盖 F0/F1 | 内部覆盖 F0/F1 |','|---|---:|---:|---:|']
    for r in summary[:4]:
        x=r['F0_linked'];y=r['F1_linked'];lines.append(f"| {r['view']} | {x['ink_L1']:.3f}/{y['ink_L1']:.3f} | {100*x['coverage']:.2f}%/{100*y['coverage']:.2f}% | {100*x['interior_coverage']:.2f}%/{100*y['interior_coverage']:.2f}% |")
    lines += ['','三个DEV全目标及内部覆盖下降，61°/60°微增；弱241°/24°从35.66%降至35.33%。同预算ungated弱后视角从40.57%降至40.11%，仍没有清楚整物体优势。S保留为可选原ID区域连接机制，不宣称带来新NPR质量贡献；原GS纸底与原行选择能力独立保留。','',
        '## 自身缺墨、可见长度与采样限制','',
        '| 相机/臂 | 代理可见长度px | pre-S自身缺失px | linked自身缺失px | linked支持长度px |','|---|---:|---:|---:|---:|']
    for r in attr:lines.append(f"| {r['view']} {r['arm']} | {r['proxy_visible_length']:.3f} | {r['preS_own_visible_missing_length']:.3f} | {r['linked_matched_own_visible_missing_length']:.3f} | {r['proxy_visible_length']-r['linked_matched_own_visible_missing_length']:.3f} |")
    lines += ['','弱后视角pre-S自身缺失24.119→19.841px、linked缺失127.909→121.581px，但可见长度853.910→846.760px，同时linked支持长度726.001→725.179px。因此较小缺失分子没有变成总体连续支持增长。前侧linked支持长度858.147→852.693px，同样下降。真实遮挡、背面及分区拒绝单独保存，不把全部深度拒绝当错误裁剪。','',
        '重要采样限制：F0的光栅图逐值等于旧A，但新增种子处分段改变了继承的逐段中心线采样位置，故F0代理可见长度和缺失统计与unit001/002的旧A略有差别。这是数值求积对分段的依赖，不是新收益；本轮只比较共同采样器下F0/F1，并以实际完整图和像素指标为主。逐段片段计数也含更多圆帽重叠，不能与旧A片段数直接解释为额外覆盖。','',
        '## 远区绝对损伤','',
        '| DEV相机 | linked远其他源差L1 F0/F1 | linked背景源差L1 F0/F1 | F1 ungated远其他源差L1 |','|---|---:|---:|---:|']
    for r in summary[:4]:
        x=r['F0_linked'];y=r['F1_linked'];lines.append(f"| {r['view']} | {x['far_other']:.9f}/{y['far_other']:.9f} | {x['background']:.9f}/{y['background']:.9f} | {r['F1_ungated']['far_other']:.9f} |")
    lines += ['',f"表内包含原纸底既有损伤。六个不同评估相机中，两臂新增linked远区差最大单像素L1={max(r['far_max_pixel_L1'] for r in far):.12g}，超过1/255的远区像素合计{sum(r['far_pixels_above_1_255'] for r in far)}；不是严格零，不靠比例分母或扩边界带宣称进步。",'',
        '## 验证与复放','',
        'TDD先因缺line_field模块RED rc1，随后四组GREEN rc0：平面恒等、已知曲面/噪声与反绕序、分离片/分区、原切片路径恢复、同标签真实前景遮挡及零S。真实Lego派生、BUILD、DEV/arc、每笔触归因与独立审计均rc0。独立审计核对677个冻结输入、源码快照、原行身份和权重、种子/锚点/字段、实际BUILD预算及112张输出PNG完整解码。新进程实际重栅格化弱后视角，全部26数组逐值一致。','',
        '一次可视化查找因继承脚本字符串替换把序列文件名写为REAR_CAMERF0_SEQUENCE.png而失败。该原文件保留，交付时增加逐字节相同的REAR_CAMERA_SEQUENCE.png别名；科学源码、协议和结果未修改，无重跑。详见ENGINEERING_NOTES.json。首次handoff因导入运行时不存在的ROOT名称而rc1，尚未写报告；原脚本和原因保存在interrupted_handoff_001，修为OUTPUT_ROOT别名后以handoff_002新回执完成。冻结科学源码未改。','',
        '```bash',
        '/mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_8build_part_prior_feasibility_v03/venv/bin/python -B /home/u00134/3dgs_line/partwise_sketch_hatching_gaussian_link_v07/experiments/partwise_sketch_hatching_v07/field_unit/replay_field.py --out /mnt/hdd1/u00134/partwise_sketch_hatching_gaussian_link_v07/units/unit_003/user_replay_001 --view orbit_241_24_5.3',
        '```','',
        '输出目录必须是unit003内的新目录。运行入口固定两核亲和、数值线程1、CUDA为空；沿用现有依赖，不安装、不GPU、不训练、不网络、不嵌套模型。本入口复用锁定GS层并实际重画代理墨，不称第二次冷GS或独立便携包；unit001已成功的一次冷重放保持。','',
        '四DEV与三后侧arc共六个不同评估相机；241°/24°重复项明确复用。全部已曝光，不当独立测试集；三帧相机序列不是连续视频或无闪烁认证。Lego是既有实际冻结GS资产，不是本轮新采集真实世界数据。','',
        'v05稀疏任务far8.044%、31像素腐蚀目标及4.49%作者区域变化失败，v06全部负结果、unit001续接与unit002载体负结果均保留。当前结论不证明真实表面、完整语义部件、自动方向估计优势、原生Gaussian排线、逐路径原ID归属或H1/H2/H3。','',
        '## 下一步','',next_step,'',why,'',
        '本单元仅完成unit003；下一科学单元仍需父级只读审查和冻结。14:25禁止新单元，14:45科学收尾，15:00硬停止。']
    (UNIT/'REPORT_ZH.md').write_text('\n'.join(lines)+'\n')
    elapsed=(datetime.datetime.now(datetime.timezone.utc)-datetime.datetime.fromisoformat('2026-10-25T12:16:12.131420+09:00')).total_seconds()/60
    js(UNIT/'STATUS.json',dict(unit='unit_003',execution_state='completed',stage='actual_F0_F1_comparison_and_readback_complete',
        scientific_verdict='negative_for_this_regularization: no established whole-object readability improvement; do not upgrade default',
        gaussian_link_progress='Original310475 rows, paper41058 and ink21006 weights/M1/UNKNOWN fixed; cached source-GS layers plus actual new proxy ink. Regional S only; no new per-path ID certification.',
        scientific_seal=False,parent_verification='pending',actual_commands=commands,tests=dict(expected_red='field_RED',green='field_GREEN_001',audit='audit',replay='cached_field_replay'),
        engineering_notes=['ENGINEERING_NOTES.json','interrupted_handoff_001/EXPLANATION.json'],artifacts=['PROTOCOL.json','asset/ASSET.json','ALL_DEV_MATCHED.png','ALL_DEV_NATURAL.png','REAR_CAMERA_SEQUENCE.png','attribution/SUMMARY.json','AUDIT.json','FAR_READBACK.json','VISIBLE_INTERVENTION.json','cached_field_replay/REPLAY_RECEIPT.json','REPORT_ZH.md','NEXT.json'],
        blockers=[],elapsed_minutes_from_authorization=elapsed,finished_utc=now(),scope='One fixed-field regularization diagnostic; all old negative results preserved.'))
    js(UNIT/'EXECUTION_RECORDS.json',commands)
    js(UNIT/'HANDOFF_SOURCE_LOCK.json',dict(files={str(p):sha(p) for p in HERE.iterdir() if p.is_file()}))
    print(json.dumps(dict(execution_state='completed',scientific_verdict='no_whole_object_advantage',elapsed_minutes=elapsed,next='continue')),flush=True)

if __name__=='__main__':main()
