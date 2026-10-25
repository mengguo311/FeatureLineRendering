"""Unit009 evidence-based Chinese handoff; no new scientific run."""
import runtime
from runtime import ACTIVE_UNIT as UNIT,HERE,sha,js,now
import json,datetime

AUTHORIZED='2026-10-25T13:50:13.351914+09:00'
def load(name):return json.loads((UNIT/name).read_text())
def main():
    from run_embedding import protocol,check_assets
    protocol();check_assets()
    asset=load('asset/ASSET.json');audit=load('AUDIT.json');geom=load('GEOMETRY_READBACK.json');material=load('MATERIAL_VISIBILITY.json')
    match=load('BUILD_MATCH.json');rows=[r for r in load('SUMMARY.json') if r['kind']=='dev'];attr=load('attribution/SUMMARY.json')
    replay=load('cached_embedding_replay/REPLAY_RECEIPT.json');assert audit['status']=='pass' and replay['all_equal']
    commands={p.stem:json.loads(p.read_text()) for p in sorted((UNIT/'logs').glob('*.json'))}
    assert commands['red_embedding']['child_returncode']==1
    assert all(r['child_returncode']==0 for name,r in commands.items() if name!='red_embedding')
    visual=dict(verdict='negative: bounded material carrier migration does not establish whole-object NPR improvement',
        inspected=['ALL_DEV_MATCHED.png','ALL_DEV_NATURAL.png','REAR_CAMERA_SEQUENCE.png','dev/orbit_241_24_5.3/COMPARISON.png','dev/orbit_241_24_5.3/INK_LAYERS.png','dev/orbit_61_24_5.3/INK_LAYERS.png'],
        front='A/T均保留H局部顺向线束。少量线段位置和弯折改变，但自然和配平完整前侧没有明确更清楚的铲斗形体。',
        rear='弱后侧和高后侧仍有碎线、空白及照片残留；231/241/251三实际相机中未见稳定整物体优势。',
        ungated='同BUILD墨预算ungated亦未显示明确载体迁移收益；pre-S已存在碎线，S另使墨减淡。',
        scope='有限目视检查，不是独立用户偏好、真实表面或时序稳定认证。')
    js(UNIT/'VISUAL_REVIEW.json',visual)
    nextstep='下一次只读Astra审查与父级冻结后，转向Chair作者座面region4的一次标准间距编辑及新路径原ID支持。使用实际v06便携包的只读Chair资产，在新v07目录复制最小输入并记录原哈希；不重复Lego冷bootstrap。建议spacing0.045一次改为0.05625，保持angle95、length0.22、width1、ink_strength0.35、载体、原行纸底/墨权重及M1/UNKNOWN。保留原保存资产作历史对照；因原region4是转移来的140条路径且visibility_mask继承为20，新生成owner-only为16，应先用同一生成器和同一owner-only规则生成spacing0.045控制臂，再与0.05625比较，单独报告历史资产与重生成控制的差异。非目标路径逐字节保持，新路径用新身份及显式来源。冻结有界分层弧长样本和相机，记录CPU真实接受的original source_index、alpha、T、alpha*T、无支持样本及未认证剩余路径；交付完整前后自然/配平linked及同预算ungated、保存加载与实际重放。此路线验证编辑和来源证据，不作为Lego载体噪声的跨场景因果证明。'
    why='本轮保留380条路径和连接，仅替换已有有界载体，仍没有整物体收益；同材料采样进一步显示原遮挡参照下支持损失，不能靠放宽容差或加大降噪掩盖。重新只读查看Chair前61/24和后241/60完整图，座面平行排线可辨；实际asset.json明确记录140条转移路径及继承掩码，CPU link_renderer具备原行接受事件接口。标准编辑和有界新路径支持是BRIEF明确允许且尚未完成的独立路线。'
    js(UNIT/'NEXT.json',dict(action='continue',recommended_next_step=nextstep,why=why,estimated_minutes=25,requires_next_read_only_review=True,no_new_units_after_jst='2026-10-25T14:25:00+09:00'))
    verdict='negative: exact H material paths on saved bounded denoised carrier have modest geometric changes but no established whole-object benefit; visible support decreases; default unchanged'
    elapsed=(datetime.datetime.now(datetime.timezone.utc)-datetime.datetime.fromisoformat(AUTHORIZED)).total_seconds()/60
    status=dict(unit='unit_009',execution_state='completed',stage='actual_A_T_visual_audit_material_diagnosis_and_replay_complete',scientific_verdict=verdict,
        gaussian_link_progress='Original310475 rows/geometry/fullSH/opacity/order and paper41058/ink21006 weights, M1/UNKNOWN195279 unchanged. A preserves380 H paths; T has380 new identities, same face/bary/segment connectivity and immediate H plus original-parent provenance. Cached original-GS layers with actual proxy-ink rerendering; no per-path Gaussian ownership certification.',
        scientific_seal=False,parent_verification='pending',actual_commands=commands,
        tests=dict(expected_red='red_embedding missing module rc1',green='green_embedding 3 groups',audit='audit independent anchors/images/inputs',replay='replay all arrays exact',post_eval='material_visibility identical material points and fixed A weights'),
        artifacts=['PROTOCOL.json','asset/ASSET.json','ALL_DEV_MATCHED.png','ALL_DEV_NATURAL.png','REAR_CAMERA_SEQUENCE.png','attribution/SUMMARY.json','GEOMETRY_READBACK.json','MATERIAL_VISIBILITY.json','VISIBLE_INTERVENTION.json','FAR_READBACK.json','FRAGMENT_READBACK.json','AUDIT.json','VISUAL_REVIEW.json','cached_embedding_replay/REPLAY_RECEIPT.json','REPORT_ZH.md','NEXT.json'],
        blockers=[],execution_authorized_jst=AUTHORIZED,elapsed_minutes_from_authorization=elapsed,finished_utc=now(),
        limitations=['One bounded saved carrier perturbation; not all possible carrier noise.','Original first-hit occluder remains fixed; mismatch-induced depth rejections are explicit.','Lengths/directions/crossing angles change as embedding consequences.','All cameras EXPOSED; six distinct evaluation cameras, no temporal or physical truth.','Inherited H zero_step_cycle remains an inherited failure.'])
    js(UNIT/'STATUS.json',status);js(UNIT/'EXECUTION_RECORDS.json',commands)
    lengths={a:sum(asset['paths'][a+'_'+p]['length'] for p in ('old','added')) for a in ('A','T')}
    far=[r for r in load('FAR_READBACK.json') if r['mode']=='linked_matched'];maxfar=max(r[k]['max'] for r in far for k in ('other','background'))
    farpixels=sum(r[k]['above_1_255'] for r in far for k in ('other','background'))
    effects=[r for r in load('VISIBLE_INTERVENTION.json') if r['mode']=='linked_matched' and r['view'] in {x['view'] for x in rows}]
    report=['# Unit009：固定H路径的载体迁移未建立整物体收益','',
        '**实际A/T、四BUILD、四DEV/三arc、逐笔触支持归因、同材料采样诊断、独立审计和新进程重放已完成。结果为负，不升级默认。execution_state=completed，scientific_seal=false，父级验证待完成，NEXT=continue。**','',
        visual['front']+visual['rear']+visual['ungated']+visual['scope'],'',
        '## 冻结干预与真实变化','',
        'A逐字节保留unit008的A_old/A_added，即unit006/007原H，未使用unit008留白变体。T仅将同一face/bary作用于unit002已保存CARRIER的三角形顶点。没有重新降噪、求方向场、行走、重排、删除短线或补洞。380条路径、2330段的顺序/连接、两层、face/bary、visibility_mask及原parent_stroke_id保持。T分配4e12加分区偏移和父路径排序的新ID，即时H父ID另存MIGRATION记录。新ID和代理锚点都不是Gaussian所有权。','',
        '旧主分区221/360条、1413/2224段发生大于1e-12的端点移动；新增分区13/20条、82/106段移动，共234/380条。最大路径端点位移0.001999775世界单位。该判据只描述浮点级变化，不是质量门槛。所有路径保留且内部存储断点为0；这不等于视觉连续。','',
        f"世界总长度A/T={lengths['A']:.9f}/{lengths['T']:.9f}，下降{100*(1-lengths['T']/lengths['A']):.4f}%。几何长度、转角与交叉角是载体变形的结果，不能声称保持这些量。",'',
        '| 分区 | 跨面转换数A/T | 跨面世界转角中位数A/T | P95 A/T |','|---|---:|---:|---:|']
    for part in ('old','added'):
        a=geom['face_transition_turns']['A_'+part];t=geom['face_transition_turns']['T_'+part]
        report.append(f"| {part} | {a['face_transitions']}/{t['face_transitions']} | {a['world_turn_quantiles'][0]:.3f}°/{t['world_turn_quantiles'][0]:.3f}° | {a['world_turn_quantiles'][2]:.3f}°/{t['world_turn_quantiles'][2]:.3f}° |")
    report+=['','转角读回排除了同面种子分段。主分区中位数下降，新增分区P95反而上升，不能仅挑中位数称为整体改善。实际两层同面线段交点对旧/新增为30/1；旧区交叉角中位数41.715541°→41.658274°、最大变化1.086351°，新增交点几乎不变。此统计只覆盖实际相交线段，可能重复计算共享边端点，不等于H全目标面积加权方向场夹角；H既有近平行风格混杂没有被修复。','',
        'unit002的441个移动顶点、保拓扑/锐边/分区保护及0.002上限原样复用。原16543顶点/29999面索引、原310475行及PLY/中心/协方差/opacity/完整SH/顺序、41058纸底与21006墨权重、M1/UNKNOWN195279、2121作者目标面与旧2030/新增91分区、1px/AA2、0.004容差和2px评价带保持。遮挡首交与区域图始终使用原代理，只有笔触所属面平面来自各臂载体；不把变形代理当物理真值。','',
        'H原父路径14500000040的minus_stop=zero_step_cycle完整保存在A_INHERITED_STOPS及GEOMETRY_READBACK。T只是其原材料轨迹的变形，没有重新积分，不能将该失败改写为成功。','',
        '## BUILD与完整DEV','',
        '自然四BUILD目标墨RGB L1：'+json.dumps(match['natural_totals'])+'。',
        '共同预算'+f"{match['budget']:.6f}"+'；每臂固定全局系数'+json.dumps(match['scales'])+'。自然结果同时保存，无DEV拟合。A自然墨/混合逐值恢复unit008；本轮配平系数不同，不能把新配平A与旧单元当成相同强度。','',
        '| DEV | 目标像素 | 墨L1 A/T | 覆盖A/T | 内部覆盖A/T |','|---|---:|---:|---:|---:|']
    for r in rows:
        q=[r[a+'_linked'] for a in ('A','T')];report.append('| '+r['view']+f" | {r['target_pixels']} | "+'/'.join(f"{x['ink_L1']:.3f}" for x in q)+' | '+'/'.join(f"{100*x['coverage']:.3f}%" for x in q)+' | '+'/'.join(f"{100*x['interior_coverage']:.3f}%" for x in q)+' |')
    report+=['','前侧两视角覆盖略降、后侧两视角略升；弱后侧32.122%→32.187%的微小变化不代表可读性进步。同预算ungated弱后侧36.968%→37.099%，完整图仍有碎线。区域S继续仅为可选原ID连接，未建立NPR质量贡献。','',
        '四DEV配平linked的目标RGB L1差≥0.05像素占比（沿用描述口径，非门槛）：'+', '.join(r['view']+'='+f"{100*r['above_005_fraction']:.2f}%" for r in effects)+'。存在真实图像变化，幅度有限，不能称不可见的完全no-op，也不能据此宣称有效改善。','',
        '## 可见支持及深度归因','',
        '| 相机/臂 | 代理可见px | 受影响可见px | pre-S自身缺失px | linked配平缺失px | linked支持px |','|---|---:|---:|---:|---:|---:|']
    for r in attr:report.append(f"| {r['view']} {r['arm']} | {r['proxy_visible_length']:.3f} | {r['affected_proxy_visible_length']:.3f} | {r['preS_own_visible_missing_length']:.3f} | {r['linked_matched_own_visible_missing_length']:.3f} | {r['proxy_visible_length']-r['linked_matched_own_visible_missing_length']:.3f} |")
    report+=['','前侧linked支持985.513→938.131px、弱后侧665.518→656.893px。缺失分子虽变小，可见分母也减小，因此不称连续性修复。样本使用各笔触自身光栅支持，不借其他笔触重叠；原参照仍是代理，深度拒绝包含正确遮挡以及变形相对固定遮挡面的偏离。','',
        '为排除独立自适应采样/缩小分母造成的解释混淆，另对A保存的同一批中心线样本恢复材料坐标，将其迁移到T，并用完全相同A投影长度权重统计两臂可见状态；这只是事后读回，没有改图像、阈值或科学协议。','',
        '| 相机 | A可见固定权重px | T可见固定权重px | 可见→深度拒绝px | 深度拒绝→可见px |','|---|---:|---:|---:|---:|']
    for r in material:report.append(f"| {r['view']} | {r['A_visible_length']:.3f} | {r['T_visible_with_fixed_A_weights']:.3f} | {r['visible_to_depth_rejected']:.3f} | {r['depth_rejected_to_visible']:.3f} |")
    report+=['','同材料诊断仍显示可见支持下降，新增深度拒绝占主要变化。不能把本结果解释成单纯去除了物理表面噪声；也不能放宽0.004容差掩盖原遮挡参照的限制。更大尺度载体噪声、不同重建和重新生成器的交互均未被排除。','',
        '## 远区绝对损伤','',
        '| DEV | linked远其他源差L1 A/T | 背景源差L1 A/T |','|---|---:|---:|']
    for r in rows:
        q=[r[a+'_linked'] for a in ('A','T')];report.append('| '+r['view']+' | '+'/'.join(f"{x['far_other']:.9f}" for x in q)+' | '+'/'.join(f"{x['background']:.9f}" for x in q)+' |')
    report+=['','这些源差包括固定纸底的原有损伤。六个不同评估相机A/T配平linked远区最大单像素L1='+f'{maxfar:.12g}'+f'；超过1/255的变化像素合计{farpixels}。弱后侧1个微小非零差，不能称严格零。所有自然/配平、linked/ungated的远其他与背景绝对读回在FAR_READBACK。','',
        '## 测试、重放和范围','',
        'TDD预期RED为缺embedding模块rc1，随后3组GREEN覆盖恒等载体、已知仿射变形的平面/折面/曲面、共享边连续和边界锚点、拓扑/标签拒绝、同标签分离前景遮挡、独立owner面深度及零S。实际derive、BUILD、DEV/arc、归因、审计、重放、同材料诊断均rc0。预期RED不覆盖；本轮无额外科学执行失败。',
        f"独立审计核对{audit['input_files_checked']}份输入，380条新路径，独立按坐标求和锚点最大误差{audit['max_independent_anchor_error']:.3g}；核对{audit['pngs_checked']}张主PNG与数组、完整解码当时全部{audit['all_png_fully_decoded']}张PNG，独立合成误差{audit['composition_error']:.3g}。新进程实际重栅格化弱后侧，{replay['arrays']}数组逐值恢复。",'',
        '```bash','/mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_8build_part_prior_feasibility_v03/venv/bin/python -B /home/u00134/3dgs_line/partwise_sketch_hatching_gaussian_link_v07/experiments/partwise_sketch_hatching_v07/embedding_unit/replay_embedding.py --out /mnt/hdd1/u00134/partwise_sketch_hatching_gaussian_link_v07/units/unit_009/user_replay_001 --view orbit_241_24_5.3','```','',
        '输出须为unit009内不存在的新目录。原GS source/paper/S复用哈希固定缓存，墨实际重画；不是再次冷GS或独立便携包。unit001成功cold hybrid范围和旧独立验收缺依赖失败均保持。现有NumPy2.2.6/SciPy1.15.3/Open3D0.20.0环境不改，CPU两核亲和、数值线程1、串行、CUDA为空，无安装/下载/GPU/训练/嵌套模型/push或merge。','',
        '四DEV与三arc只有六个不同评估相机，241°/24°明确重复且复用完成输出，全部EXPOSED；三帧不是连续视频或时序稳定认证。Lego是既有NeRF Synthetic冻结vanilla-GS及CPU协方差平面深度/TSDF代理，非本轮采集真实世界物体、RaDe训练或GT。当前输出是原GS纸底和原ID区域S门控代理墨，非原生Gaussian排线、完整语义部件或逐路径原ID认证。','',
        'v05稀疏任务far8.044%、31像素腐蚀目标、4.49%作者区域变化失败，以及v06和v07 unit001–008各负结果全部保持。H原局部PARTIAL不改写为整物体成功，本轮也不证明全部载体噪声或生成器路线无效。','',
        '## 下一步','',nextstep,'',why,'',f'本次只完成unit009，报告时从授权计约{elapsed:.2f}分钟。下一科学单元须新的只读Astra审查及父级冻结；14:25禁启、14:45科学收尾、15:00硬停止。']
    (UNIT/'REPORT_ZH.md').write_text('\n'.join(report)+'\n')
    js(UNIT/'HANDOFF_SOURCE_LOCK.json',dict(files={str(HERE/name):sha(HERE/name) for name in ('audit_embedding.py','read_material_visibility.py','finish_embedding.py')}))
    print(json.dumps(dict(execution_state='completed',scientific_verdict=verdict,next='continue',elapsed_minutes=elapsed),ensure_ascii=False),flush=True)

if __name__=='__main__':main()
