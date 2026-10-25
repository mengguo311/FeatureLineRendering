"""Chinese handoff from actual saved evidence; no scientific reruns."""
import runtime
from runtime import ACTIVE_UNIT as UNIT,HERE,sha,js,now
import json,datetime

AUTHORIZED='2026-10-25T13:16:00.547056+09:00'
def load(name):return json.loads((UNIT/name).read_text())

def main():
    a=load('asset/ASSET.json');d=load('DIRECTION_READBACK.json');audit=load('AUDIT.json');layer=load('LAYER_READBACK.json')
    match=load('BUILD_MATCH.json');rows=[r for r in load('SUMMARY.json') if r['kind']=='dev'];far=load('FAR_READBACK.json');attr=load('attribution/SUMMARY.json')
    replay=load('cached_coupling_replay/REPLAY_RECEIPT.json')
    assert audit['status']=='pass' and replay['all_equal']
    commands={p.stem:json.loads(p.read_text()) for p in sorted((UNIT/'logs').glob('*.json'))}
    assert commands['red_coupling']['child_returncode']==1
    assert all(r['child_returncode']==0 for name,r in commands.items() if name!='red_coupling')
    nextstep='下一次只读Astra审查与父级冻结后，转向既有Chair座面简单排线的一次真实间距编辑与新路径原ID支持验证。先在v07副本恢复原region4配置与路径，核对继承visibility_mask和owner-only新路径规则的差别；冻结一个间距修改（建议原0.045的1.25倍，不扫描），其他风格、目标、原256690行和纸底/墨权重及M1/UNKNOWN固定，非目标路径逐字节保持。为新路径分配新ID和face/bary，以预先固定的分层弧长样本记录实际CPU接受事件的original source_index、alpha、T、alpha*T及无支持样本，保留采样分母和未认证路径。输出前后完整old/new、自然独立墨、linked及同墨预算ungated控制，完成保存加载和一次实际复放。复用已有v07依赖/重放基础，不重复bootstrap；Chair是可操作性与来源证据验证，不是Lego载体噪声的跨场景因果对照。'
    why='本轮恢复交叉关系后，第二层图内相干性降低、后侧交叉网格回归，弱后侧支持只部分恢复且高仰角后侧进一步退化；没有继续扫描方向、锚点或平滑权重的依据。只读复看v06 Chair前61/24和后241/60整物体图，座面已有可辨平行排线；便携资产和实际CPU原ID接受事件接口存在。新路径尚未有逐路径来源证据，标准编辑与有界来源采样是BRIEF明确允许且与继续调Lego场不同的有效路线。'
    js(UNIT/'NEXT.json',dict(action='continue',recommended_next_step=nextstep,why=why,estimated_minutes=30,requires_next_read_only_review=True,no_new_units_after_jst='2026-10-25T14:25:00+09:00'))
    inspected=['ALL_DEV_MATCHED.png','ALL_DEV_NATURAL.png','REAR_CAMERA_SEQUENCE.png','dev/orbit_61_24_5.3/COMPARISON.png','dev/orbit_241_24_5.3/COMPARISON.png','dev/orbit_61_24_5.3/INK_LAYERS.png','dev/orbit_241_24_5.3/INK_LAYERS.png','dev/orbit_241_24_5.3/H_layer1_preS.png','dev/orbit_241_24_5.3/J_layer1_preS.png']
    visual=dict(verdict='negative for whole-object promotion; some inherited primary-line front benefit remains',inspected=inspected,
        front='J保留H部分较顺的主方向线束，但第二层带回交叉和局部折线；完整铲斗没有稳定更清楚。前侧覆盖/支持位于F0与H之间，不能忽略可见墨差异。',
        rear='J恢复斜向交叉网格，弱后侧覆盖/支持相对H回升但仍低于F0；高仰角后侧覆盖和墨量进一步下降。碎线、空白与照片残留仍存在。',
        interpretation='H/J第二层交叉关系和空间相干性同时变化；结果支持原H较少网格交叉依赖第二层配置，但不能唯一归因于交叉角，也不能判定载体噪声主因。',
        scope='有限目视检查；无独立用户偏好、物理真值或时序认证。')
    js(UNIT/'VISUAL_REVIEW.json',visual)
    verdict='negative for whole-object improvement: exact crossing restoration succeeds but secondary coherence worsens; weak rear support only partly recovers and high rear worsens; default unchanged'
    elapsed=(datetime.datetime.now(datetime.timezone.utc)-datetime.datetime.fromisoformat(AUTHORIZED)).total_seconds()/60
    status=dict(unit='unit_007',execution_state='completed',stage='actual_F0_H_J_comparison_visual_audit_replay_complete',scientific_verdict=verdict,
        gaussian_link_progress='Original310475 rows/geometry/fullSH/opacity/order, paper41058/ink21006 weights and M1/UNKNOWN195279 unchanged. J217 primary paths retain H IDs;163 new secondary paths retain explicit original-parent provenance and face/bary. Actual original-GS paper plus regional original-ID S; no new per-path Gaussian ownership certification.',
        scientific_seal=False,parent_verification='pending',actual_commands=commands,
        tests=dict(expected_red='red_coupling',green='green_coupling:4 groups',audit='audit',replay='replay',saved_result_diagnostics='diagnostics'),
        artifacts=['PROTOCOL.json','asset/FIELDS.npz','asset/ASSET.json','ALL_DEV_MATCHED.png','ALL_DEV_NATURAL.png','REAR_CAMERA_SEQUENCE.png','attribution/SUMMARY.json','DIRECTION_READBACK.json','LAYER_READBACK.json','COUPLING_READBACK.json','WALKER_GUARD_RECORD.json','FAR_READBACK.json','VISIBLE_INTERVENTION.json','AUDIT.json','VISUAL_REVIEW.json','cached_coupling_replay/REPLAY_RECEIPT.json','REPORT_ZH.md','NEXT.json','EXECUTION_RECORDS.json','HANDOFF_SOURCE_LOCK.json','ARTIFACT_MANIFEST.json'],
        blockers=[],candidate_limitations=['J layer1 coherence worsens; crossing/coherence not isolated individually.','No whole-object NPR improvement.','All cameras EXPOSED; no temporal or true-surface claim.','Original region S is not per-path original-ID ownership.'],
        execution_authorized_jst=AUTHORIZED,elapsed_minutes_from_authorization=elapsed,finished_utc=now())
    js(UNIT/'STATUS.json',status)
    lengths={arm:sum(a['paths'][arm+'_'+part]['length'] for part in ('old','added')) for arm in ('F0','H','J')}
    report=['# Unit007：恢复原交叉关系后，后侧网格回归，整物体优势仍未建立','',
        '**真实F0/H/J比较已完成。J精确恢复基线逐面交叉关系并保留H第0层，但整物体改进未建立，不升级默认。execution_state=completed，scientific_seal=false，父级验证待完成，NEXT=continue。**','',
        '已检查四DEV完整自然/配平图、前后独立墨、弱后侧第二层墨、linked/同预算ungated及231/241/251实际相机序列。J保留部分前侧主方向线束，第二层却重新引入交叉和折线；后侧网格回归，弱后侧支持只部分恢复，高仰角后侧覆盖进一步下降。局部主方向效果不抹去，但没有证据把H或J升级为整物体NPR优势。本观察不是用户偏好实验。','',
        '## 冻结干预与身份','',
        '逐面a=F0第0层、b=F0第1层、c=H第0层、n=单位法线，J0=c，J1=(a·b)c+[n·(a×b)](n×c)。这是由保存场唯一确定的切平面旋转，无新角度、锚点、全局求场或相机拟合。F0/H路径及记录从unit006逐字节复制；J第0层217条路径、几何/face/bary/ID及停止记录逐字节保留H。J第1层163条从unit001原始种子/请求长度生成，ID=原父ID+1100000000000，未从已截短H提取种子或长度。','',
        '同一16543顶点/29999面载体、380个种子、原请求长度、行走器及保护停止、旧2030/新增91分区、2121作者目标、1px/AA2、0.004遮挡容差和2px评价带保持。原310475 Gaussian行身份/顺序、PLY/中心/协方差/opacity/完整SH、41058纸底和21006墨行权重、M1/UNKNOWN195279保持。无补孔、载体修改、重排种子、扩目标或屏幕路径。','',
        f"独立旋转矩阵读回最大误差{audit['coupling_audit']['rotation_matrix_error']:.3g}；交叉点积及有向正弦误差均{audit['coupling_audit']['cross_dot_error']:.3g}。J与F0面积加权交叉角同为49.895273°，低于15°面积同为17.0964%；H分别为13.151954°和78.8601%。",'',
        '## 机制诊断与解释限制','',
        '| 方向场 | 第0层图内能量 | 第1层图内能量 | 第1层排除锐边能量 |','|---|---:|---:|---:|']
    for arm in ('F0','H','J'):
        e=a['normalized_field_energy'][arm];report.append(f"| {arm} | {e['graph_pairs'][0]:.9f} | {e['graph_pairs'][1]:.9f} | {e['excluded_pairs'][1]:.9f} |")
    report+=['','图内2483对边、排除锐边311对沿用保存数据。J第0层相干性保持H；第二层0.133850高于F0的0.091536和H的0.003303，排除锐边也未改善。恢复原交叉关系同时带回逐面关系变化，因此H/J不能作为纯交叉角单因素解释；F0/J只支持在原交叉关系下检验方向构造，不能排除全部载体噪声。','',
        f"三臂均380条；总世界长度F0/H/J={lengths['F0']:.9f}/{lengths['H']:.9f}/{lengths['J']:.9f}。J较F0短{100*(1-lengths['J']/lengths['F0']):.3f}%，较H略长；内部存储断点均0，不等于视觉连续。",'',
        '| 分层 | 笔触数 | 世界长度 | 相对原请求缩短笔触数 |','|---|---:|---:|---:|']
    for key,r in layer['paths'].items():report.append(f"| {key} | {r['strokes']} | {r['length']:.9f} | {r['shortened_strokes']} |")
    report+=['','J端点633达到请求长度、116遇作者边界、11遇网格边界，无新保护停止。H原第1层zero_step_cycle及其原始笔触完整保存在对照和WALKER_GUARD_RECORD；J是新路径，没有删除或延长旧失败。F0请求长度来自旧生成器已截断的笔触，不能据全部requested_length宣称原生成器无截断。','',
        '| 分区 | 跨面转角中位数F0/H/J | P95 F0/H/J |','|---|---:|---:|']
    for part in ('old','added'):
        qq=[d['paths'][part+'_'+arm]['shared_edge_turn_degrees_quantiles'] for arm in ('F0','H','J')]
        report.append('| '+part+' | '+'/'.join(f'{q[0]:.3f}°' for q in qq)+' | '+'/'.join(f'{q[2]:.3f}°' for q in qq)+' |')
    report+=['','## BUILD墨预算与实际DEV','',
        '自然四BUILD目标墨RGB L1：'+json.dumps(match['natural_totals'])+'。',
        f"共同预算{match['budget']:.6f}；全局系数"+json.dumps(match['scales'])+'。自然强度同时保存，未拟合DEV。公共预算仍由H决定，因此F0/H自然与配平全部图逐值保持unit006。H/J第0层自然pre-S完全相同；配平后该层强度只受各臂冻结全局系数影响，不能称配平层图也逐值相同。','',
        '| DEV | 目标像素 | 目标墨L1 F0/H/J | 覆盖F0/H/J | 内部覆盖F0/H/J |','|---|---:|---:|---:|---:|']
    for r in rows:
        q=[r[arm+'_linked'] for arm in ('F0','H','J')]
        report.append('| '+r['view']+f" | {r['target_pixels']} | "+'/'.join(f"{x['ink_L1']:.3f}" for x in q)+' | '+'/'.join(f"{100*x['coverage']:.2f}%" for x in q)+' | '+'/'.join(f"{100*x['interior_coverage']:.2f}%" for x in q)+' |')
    report+=['','两前侧J覆盖高于F0但低于H；弱后侧32.12%→34.41%仍低于F0的35.36%，高后侧H35.16%→J33.76%，低于F0的36.56%。弱后侧同预算ungated覆盖F0/H/J为40.57%/36.97%/39.46%，不能把更多覆盖直接解释为更清楚。J相对H四DEV目标图像差≥0.05占比21.01%、21.64%、16.14%、19.49%，干预确实可见；0.05仅为既有描述口径，无新增通过门槛。','',
        '## 自身支持、遮挡与S','',
        '| 相机/臂 | 代理可见长度px | pre-S自身缺失px | linked配平自身缺失px | linked支持长度px |','|---|---:|---:|---:|---:|']
    for r in attr:report.append(f"| {r['view']} {r['arm']} | {r['proxy_visible_length']:.3f} | {r['preS_own_visible_missing_length']:.3f} | {r['linked_matched_own_visible_missing_length']:.3f} | {r['proxy_visible_length']-r['linked_matched_own_visible_missing_length']:.3f} |")
    report+=['','前侧F0/H/J支持长度854.642/985.513/924.304px；弱后侧720.578/665.518/694.733px。J只部分恢复后侧支持，没有消除原问题。采样每条stroke自身墨而不借交叠笔触；可见分母、分区/深度拒绝和分层结果均保存。长度受投影及分段求积影响，参照仍是原代理，非独立物理真值。深度拒绝包含正确遮挡，不全部解释为渲染错误。S使墨另行衰减，但无证据证明其NPR质量贡献，继续作为可选原ID区域连接。','',
        '## 远区绝对损伤','',
        '| DEV | linked远其他源差L1 F0/H/J | linked背景源差L1 F0/H/J | J ungated远其他源差L1 |','|---|---:|---:|---:|']
    for r in rows:
        q=[r[arm+'_linked'] for arm in ('F0','H','J')]
        report.append('| '+r['view']+' | '+'/'.join(f"{x['far_other']:.9f}" for x in q)+' | '+'/'.join(f"{x['background']:.9f}" for x in q)+f" | {r['J_ungated']['far_other']:.9f} |")
    report+=['','这些源差包含原纸底已有损伤。六个不同评估相机J−H linked远区最大单像素L1=2.33203173e-06，J−F0=2.60770321e-06；仅弱后侧1个非零像素，超过1/255的远区变化像素0。不是严格零，没有扩大容差带或目标。','',
        '## 验证、复放与边界','',
        '预期RED为缺coupling模块rc1；随后4组GREEN覆盖已知平面旋转、曲面/共享边、法线及无向符号/反绕序、固定第0层、原始种子与face/bary、分离片/分区停止、同标签真实前景遮挡和零S。真实派生、四BUILD、四DEV/三arc、归因、审计、复放和分层读回全部rc0。',
        f"独立审计核对{audit['input_files_checked']}份冻结输入、源码及快照，原行权重不变；380×3个种子误差0，锚点误差{audit['max_anchor_error']:.3g}。{audit['pngs_decoded_and_checked']}张主输出PNG与数组核对，全部{audit['all_png_fully_decoded']}张当时PNG完整解码。新进程实际重栅格化弱后侧，{replay['arrays']}数组逐值一致。",'',
        '```bash','/mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_8build_part_prior_feasibility_v03/venv/bin/python -B /home/u00134/3dgs_line/partwise_sketch_hatching_gaussian_link_v07/experiments/partwise_sketch_hatching_v07/coupling_unit/replay_coupling.py --out /mnt/hdd1/u00134/partwise_sketch_hatching_gaussian_link_v07/units/unit_007/user_replay_001 --view orbit_241_24_5.3','```','',
        '输出须为unit007内不存在的新目录。复用锁定GS source/paper/S，墨实际重画；不是新一次cold GS或独立便携包。unit001一次冷重放记录保持。沿用既有NumPy/SciPy/Open3D依赖，CPU两核亲和、数值线程1、串行、CUDA为空，无安装、下载、GPU、训练、嵌套模型或push/merge。冻结源码和父级DECISION不改；事后报告/分层读回另列HANDOFF_SOURCE_LOCK。','',
        '四DEV与三arc仅六个不同评估相机，241°/24°明确重复，全部EXPOSED；三帧不是连续视频或稳定性认证。Lego为既有冻结GS资产，非本轮采集真实物体。当前为CPU原GS纸底与原ID区域S门控代理墨，非原生Gaussian排线、完整语义部件或逐路径原ID认证。','',
        'v05稀疏任务far8.044%、31像素腐蚀目标、4.49%作者区域变化失败，v06及v07 unit001–006负结果全部保留。原H局部PARTIAL不被改写为整体成功或纯角度效果；一次保守载体降噪及这些生成器负结果也不能证明载体必为主因。','',
        '## 下一步','',nextstep,'',why,'',f'本次只完成unit007；报告时从授权计约{elapsed:.2f}分钟。下一科学单元仍须只读审查和父级冻结；14:25禁启新单元、14:45科学收尾、15:00硬停止。']
    (UNIT/'REPORT_ZH.md').write_text('\n'.join(report)+'\n')
    js(UNIT/'EXECUTION_RECORDS.json',commands)
    js(UNIT/'HANDOFF_SOURCE_LOCK.json',dict(files={str(HERE/name):sha(HERE/name) for name in ('read_coupling_diagnostics.py','finish_coupling.py')}))
    print(json.dumps(dict(execution_state='completed',scientific_verdict=verdict,next='continue',elapsed_minutes=elapsed),ensure_ascii=False),flush=True)

if __name__=='__main__':main()
