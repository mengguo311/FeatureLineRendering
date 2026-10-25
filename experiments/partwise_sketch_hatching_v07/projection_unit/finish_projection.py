"""Data-driven handoff for the completed frozen projection comparison."""
import runtime
from runtime import ACTIVE_UNIT as UNIT,HERE,OUTPUT_ROOT as ROOT,sha,js,now
import json,datetime

def load(path):return json.loads(path.read_text())

def main():
    a=load(UNIT/'asset/ASSET.json');d=load(UNIT/'DIRECTION_READBACK.json');audit=load(UNIT/'AUDIT.json')
    summary=load(UNIT/'SUMMARY.json');match=load(UNIT/'BUILD_MATCH.json');far=load(UNIT/'FAR_READBACK.json')
    visible=load(UNIT/'VISIBLE_INTERVENTION.json');attr=load(UNIT/'attribution/SUMMARY.json')
    replay=load(UNIT/'cached_projection_replay/REPLAY_RECEIPT.json')
    assert audit['status']=='pass' and replay['all_equal']
    commands={p.stem:load(p) for p in sorted((UNIT/'logs').glob('*.json'))}
    assert commands['projection_RED']['child_returncode']==1
    assert all(x['child_returncode']==0 for key,x in commands.items() if key!='projection_RED')
    images=['ALL_DEV_MATCHED.png','ALL_DEV_NATURAL.png','REAR_CAMERA_SEQUENCE.png',
        'dev/orbit_241_24_5.3/COMPARISON.png','dev/orbit_61_24_5.3/INK_LAYERS.png','dev/orbit_241_24_5.3/INK_LAYERS.png']
    images += [f'dev/{view}/P1_layer{layer}_preS.png' for view in ('orbit_61_24_5.3','orbit_241_24_5.3') for layer in (0,1)]
    visual='完整四DEV自然/配平图、弱后视角linked/ungated对照、前后独立及分层墨图、231/241/251实际相机序列均已检查。P1在前侧把原平行线束变为更零散的弯折短线；后侧部分位置墨较多，但短交叉和杂乱仍在。没有形成清楚的完整铲斗形体优势，不能用局部覆盖增长升级默认。'
    js(UNIT/'VISUAL_REVIEW.json',dict(utc=now(),images=[dict(path=p,sha256=sha(UNIT/p)) for p in images],
        observation_chinese=visual,verdict='negative_for_whole_object_advantage',method='Direct limited visual inspection by executing assistant; not an independent user study.'))
    guarded=[]
    for part in ('old','added'):
        for r in load(UNIT/'asset'/('P1_'+part+'_SEEDS.json')):
            if r['minus_stop']=='zero_step_cycle' or r['plus_stop']=='zero_step_cycle':guarded.append(dict(partition=part,record=r))
    assert len(guarded)==1
    js(UNIT/'WALKER_GUARD_RECORD.json',dict(records=guarded,source='Saved frozen P1 seed/stop records; no rerun or source changes.',
        interpretation='The inherited walker terminated one direction via its zero-step-cycle safeguard. Keep its shortened path and failure visible; do not certify complete integration or change tolerance.'))
    next_step='下一次只读Astra审查与父级冻结后，优先用已能辨认平行排线的既有Chair座面简单基线，做一次单区域间距编辑及新路径原ID支持验证。先确认原region4路径能按原配置重建、继承visibility_mask与新路径owner-only支持的差异，再冻结一个编辑值；不扫描风格。原256690行、纸底/墨权重、M1/UNKNOWN、作者目标和其他区域路径保持，后者逐字节核验。新路径使用新ID和face/bary，在前后固定相机上按预先固定的分层弧长样本记录实际接受的original-ID、alpha、T和alpha*T，保留无支持样本、分母及未认证路径，不用最近核或区域S代替逐路径证据。输出完整old/new、独立墨、linked/同预算ungated及保存加载复放。Chair只作为已有可用基线的编辑和连接能力验证，不作为Lego载体噪声的跨场景因果对照。'
    why='Lego的续接、保守载体降噪、共享场正则化、种子重排和本次直接切向投影均没有建立整物体优势；本次大幅可见方向变化还增加急转和长度损失，缺少继续叠加或扫参数的依据。只读核对v06 Chair前61/24及后241/60完整图，座面已有可辨平行排线；旧资产和真实source_ewa_link事件接口存在。以简单基线验证新的路径来源及一次实际编辑是独立、已授权的应用进展，旧路径证据不能自动迁移。H2当前硬停止边界不能凭空制造越界余量。'
    js(UNIT/'NEXT.json',dict(action='continue',recommended_next_step=next_step,why=why,estimated_minutes=30,
        requires_next_read_only_review=True,no_new_units_after_jst='2026-10-25T14:25:00+09:00'))
    total0=sum(d['paths'][part+'_P0']['length'] for part in ('old','added'))
    total1=sum(d['paths'][part+'_P1']['length'] for part in ('old','added'))
    lines=['# Unit005：固定宏观切向投影真实改变路径，整物体优势未建立','',
        '**P0/P1真实比较完成；P0精确恢复旧基线，P1不升级默认。execution_state=completed，科学结论为负；scientific_seal=false，父级验证待完成，NEXT=continue。**','',visual,'',
        '## 单变量与原始提纲M4','',
        'P0=normalize(n_face×q)。P1先用冻结unit010宏观法向n0确定a=normalize(n0×q)，再按normalize(a−(a·n_face)n_face)投影到每个局部切平面。q仍由冻结基底及35°/95°产生；宏观参考平面上两者同向，没有重新估计PCA、改变基底手性、调角度或相机拟合。这是方向构造规则对照，不是自动方向估计创新。局部初始切向随规则改变，实际两层交叉角、间距、路径形状和边界截断均可能变化。',
        '两臂使用逐字节沿用unit003的line_field.py行走器：真实共享边、几何内向符号、原边界与保护停止。没有叠加unit002降噪、unit003场扩散或unit004重排。P1没有证明全局相干；投影退化<=1e-12时只回退同面P0，此数值保护未调参。','',
        '原16543顶点/29999面、原380个弧长中点种子、逐笔触请求长度及方向层保持；旧2030面与新增91面仍分别停止。原310475行身份/行序、源PLY、中心/协方差/opacity/完整SH、41058纸底和21006墨权重、195279 UNKNOWN及M1、2121面作者目标、1px线宽/AA2、0.004遮挡容差及2px评价带均固定。源纸底/S缓存复用，墨层每个不同相机真实重新栅格化。',
        'P0/P1身份分别为父路径ID＋700000000000/800000000000；保存face/bary、种子、初始切向和停止原因。这些仍是代理路径身份，不是逐路径原Gaussian所有权。','',
        '## 干预效果、长度和保护停止','',
        f"2121个目标面，两层退化回退总数{a['field']['fallback_selected_face_layers']}；目标面方向变化中位数/P95/最大为{a['field']['selected_change_degrees_quantiles'][0]:.3f}°/{a['field']['selected_change_degrees_quantiles'][2]:.3f}°/{a['field']['selected_change_degrees_quantiles'][3]:.3f}°。这是明显不同的场，不是小幅平滑强度变化。",'',
        '| 分区 | 实际长度P0/P1 | 跨面转角中位数P0/P1 | 跨面转角P95 P0/P1 | P1缩短笔触数 |',
        '|---|---:|---:|---:|---:|']
    for part in ('old','added'):
        x=d['paths'][part+'_P0'];y=d['paths'][part+'_P1']
        lines.append(f"| {part} | {x['length']:.9f}/{y['length']:.9f} | {x['shared_edge_turn_degrees_quantiles'][0]:.3f}°/{y['shared_edge_turn_degrees_quantiles'][0]:.3f}° | {x['shared_edge_turn_degrees_quantiles'][2]:.3f}°/{y['shared_edge_turn_degrees_quantiles'][2]:.3f}° | {y['strokes_shorter_by_over_1e_6']} |")
    lines += ['',f'两臂均保留380条笔触；总长度{total0:.9f}→{total1:.9f}，减少{100*(1-total1/total0):.3f}%。存储内部断点0不等于连续可读。P1端点607个达到请求长度、128个遇作者边界、24个遇网格边界、1个触发zero_step_cycle；134条笔触有大于1e-6的长度损失。P0的请求长度来自已被原生成器截短的路径，760个requested_length终止不能证明原生成器没有边界截断。',
        '保护停止具体为新增分区父stroke14500000159、新ID814500000159，seed_face5779；请求0.100995702、实际0.079752178，plus端zero_step_cycle，44段、15次钝角边转换。原记录另存WALKER_GUARD_RECORD.json，未删除该路径、延长它或改保护阈值。所有锚点有效，故比较可以完成，但不宣称全部路径完整积分。',
        '继承行走器在新面选内向符号，相对于传输后旧切向的钝角转换由P0的21次增至P1的101次；新增分区每单位长度总转角明显增加。该统计含真实折面，不是噪声真值，也不能单凭它确定实现错误。',
        f"两层面积加权交叉角均值{d['cross_layer']['P0']['area_weighted_mean_degrees']:.3f}°→{d['cross_layer']['P1']['area_weighted_mean_degrees']:.3f}°；小于15°面积{100*d['cross_layer']['P0']['area_fraction_below15']:.3f}%→{100*d['cross_layer']['P1']['area_fraction_below15']:.3f}%。低交叉角比例改善没有转化为整物体优势。",'',
        '| DEV相机 | 目标像素 | 至少一层场变化>1°像素 | 目标实际图像差比例 |','|---|---:|---:|---:|']
    for r,f in zip(visible[:4],far[:4]):lines.append(f"| {r['view']} | {r['target_pixels']} | {r['changed_field_target_pixels_over_1deg']} | {100*f['target_changed_fraction_005']:.2f}% |")
    lines += ['','可见场变化覆盖约87%–99%的目标像素，实际配平图变化约30%–40%，不是no-op。1°及RGB L1≥0.05仅为描述口径，不是新的科学通过门槛。','',
        '## BUILD墨预算和完整DEV','',
        f"四BUILD自然目标墨RGB L1：{json.dumps(match['natural_totals'])}。公共预算{match['budget']:.6f}；每臂固定全局系数{json.dumps(match['scales'])}。实际合成读回在浮点误差内一致；自然强度保留，无DEV/逐帧拟合。P0本轮配平缩放不同于旧unit004，因此跨单元比较应使用自然强度或明确配平条件。",'',
        '| DEV相机 | 目标墨L1 P0/P1 | 全目标覆盖P0/P1 | 内部覆盖P0/P1 |','|---|---:|---:|---:|']
    for r in summary[:4]:
        x=r['P0_linked'];y=r['P1_linked'];lines.append(f"| {r['view']} | {x['ink_L1']:.3f}/{y['ink_L1']:.3f} | {100*x['coverage']:.2f}%/{100*y['coverage']:.2f}% | {100*x['interior_coverage']:.2f}%/{100*y['interior_coverage']:.2f}% |")
    lines += ['','三个DEV全目标及内部覆盖下降；弱241°/24°略升，但其DEV目标墨量也增加，BUILD配平不保证每个DEV相等。两前侧由规则线束变为更碎乱短线，不能把覆盖减少称为干净。弱后侧同预算ungated覆盖40.57%→41.03%，仍未形成整物体可读性收益。S继续作为可选原行区域连接，原GS纸底/选择控制保留，不声称门控的NPR贡献。','',
        '## 可见长度、缺墨和S','',
        '| 相机/臂 | 代理可见长度px | pre-S自身缺失px | linked配平自身缺失px | linked支持长度px |','|---|---:|---:|---:|---:|']
    for r in attr:lines.append(f"| {r['view']} {r['arm']} | {r['proxy_visible_length']:.3f} | {r['preS_own_visible_missing_length']:.3f} | {r['linked_matched_own_visible_missing_length']:.3f} | {r['proxy_visible_length']-r['linked_matched_own_visible_missing_length']:.3f} |")
    lines += ['','前侧缺失分子下降同时可见长度大幅下降，linked支持长度856.024→694.434px；不能解释成连续性修复。弱后侧pre-S缺失略增，linked支持长度723.555→748.109px，但只支持该投影采样量增加，完整图仍杂乱。曲线改变、投影缩短和分段求积都会影响这些量；不把重复/急转路径长度当更好形体表达。每笔触仅使用自身光栅支持，不借其他笔触重叠；参照仍是原代理可见性，非独立物理真值。',
        '原深度规则和源S未放宽。前后深度拒绝含正确背面与遮挡，不能全部标为错误；分区/深度拒绝及可见分母均保存于attribution与VISIBLE_INTERVENTION。','',
        '## 绝对远区影响','',
        '| DEV相机 | linked远其他源差L1 P0/P1 | linked背景源差L1 P0/P1 | P1 ungated远其他源差L1 |','|---|---:|---:|---:|']
    for r in summary[:4]:
        x=r['P0_linked'];y=r['P1_linked'];lines.append(f"| {r['view']} | {x['far_other']:.9f}/{y['far_other']:.9f} | {x['background']:.9f}/{y['background']:.9f} | {r['P1_ungated']['far_other']:.9f} |")
    lines += ['',f"表内包含原纸底已有损伤。六个不同评估相机P1-P0 linked远区最大单像素L1={max(r['far_max_pixel_L1'] for r in far):.12g}，超过1/255的像素合计{sum(r['far_pixels_above_1_255'] for r in far)}；弱后视角一个非零像素，不能称严格零。没有扩评价带、删困难像素或修改作者区域。",'',
        '## 测试、重放与解释边界','',
        f"预期RED因缺projection_field模块rc1，随后5组GREEN rc0：参考平面同向、解析倾斜投影、噪声曲面/反绕序/分离片、退化同面回退、旧切片路径恢复/锚点/分区停止、同标签真实前景遮挡与零S。真实Lego派生、BUILD、DEV/arc、归因、独立审计和重放均rc0。审计核对{audit['input_files_checked']}份冻结输入、源码快照、原行权重和场公式，种子误差{audit['max_seed_error']:.3g}，锚点误差{audit['max_anchor_error']:.3g}，P0端点误差{audit['max_P0_endpoint_error']:.3g}；完整解码并核验{audit['pngs_decoded_and_checked']}张PNG。P0全部实际自然墨图与旧A逐值一致。",'',
        '```bash',
        '/mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_8build_part_prior_feasibility_v03/venv/bin/python -B /home/u00134/3dgs_line/partwise_sketch_hatching_gaussian_link_v07/experiments/partwise_sketch_hatching_v07/projection_unit/replay_projection.py --out /mnt/hdd1/u00134/partwise_sketch_hatching_gaussian_link_v07/units/unit_005/user_replay_001 --view orbit_241_24_5.3',
        '```','',
        f"输出必须为unit005内不存在的新目录。新进程实际重栅格化弱后视角，{replay['arrays']}个数组逐值一致；复用已验证GS source/paper/S，明确不是第二次冷GS或独立便携包。unit001一次完整冷重放成功范围保持。沿用现有NumPy/SciPy/Open3D环境，数值线程1、CPU两核亲和、串行、CUDA为空，无安装/下载/GPU/训练/嵌套模型；所有重数据在新HDD单元。",'',
        '四DEV与三后侧arc共六个不同评估相机，241°/24°明确重复复用，均为EXPOSED。三帧相机序列不是连续视频或时序稳定认证。当前Lego是既有冻结GS资产，不是本轮采集真实物体。',
        'v05稀疏任务far8.044%、31像素腐蚀目标及4.49%作者区域变化失败，v06全部负结果及v07 unit001至004负结果完整保留。一次保守降噪失败加多个生成器变体失败，仍不能证明所有载体噪声已排除、载体必为主因或所有生成器无效。当前输出仍是CPU原GS纸底加原ID区域门控代理墨，不是原生Gaussian排线、完整语义部件或H1/H2/H3证明。','',
        '## 下一步','',next_step,'',why,'',
        '本单元仅完成unit005；下一单元仍须新的只读审查及父级冻结。14:25禁启新科学单元、14:45科学收尾、15:00硬停止。']
    (UNIT/'REPORT_ZH.md').write_text('\n'.join(lines)+'\n')
    elapsed=(datetime.datetime.now(datetime.timezone.utc)-datetime.datetime.fromisoformat('2026-10-25T12:48:47.731846+09:00')).total_seconds()/60
    js(UNIT/'STATUS.json',dict(unit='unit_005',execution_state='completed',stage='actual_P0_P1_comparison_visual_review_audit_replay_complete',
        scientific_verdict='negative_for_projected_macro_guide: visible intervention without whole-object advantage; increased sharp turns and one inherited walker zero-step safeguard; default not promoted',
        gaussian_link_progress='Original310475 rows, geometry/fullSH/opacity, paper41058 and ink21006 weights, M1/UNKNOWN195279 fixed. Actual new paths linked through unchanged regional original-ID S; no new per-path Gaussian certification.',
        scientific_seal=False,parent_verification='pending',actual_commands=commands,tests=dict(expected_red='projection_RED',green='projection_GREEN_001',audit='audit',replay='cached_projection_replay'),
        artifacts=['PROTOCOL.json','asset/ASSET.json','ALL_DEV_MATCHED.png','ALL_DEV_NATURAL.png','REAR_CAMERA_SEQUENCE.png','attribution/SUMMARY.json','DIRECTION_READBACK.json','AUDIT.json','FAR_READBACK.json','VISIBLE_INTERVENTION.json','VISUAL_REVIEW.json','WALKER_GUARD_RECORD.json','cached_projection_replay/REPLAY_RECEIPT.json','REPORT_ZH.md','NEXT.json'],
        blockers=[],candidate_limitations=['One P1 direction stopped via zero_step_cycle; original record retained.'],
        elapsed_minutes_from_authorization=elapsed,execution_authorized_jst='2026-10-25T12:48:47.731846+09:00',finished_utc=now()))
    js(UNIT/'EXECUTION_RECORDS.json',commands)
    js(UNIT/'HANDOFF_SOURCE_LOCK.json',dict(files={str(p):sha(p) for p in HERE.iterdir() if p.is_file()}))
    print(json.dumps(dict(execution_state='completed',scientific_verdict='negative',next='continue',elapsed_minutes=elapsed)),flush=True)

if __name__=='__main__':main()
