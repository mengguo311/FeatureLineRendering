"""Publish the completed unit004 evidence; no scientific result is rerun."""
import runtime
from runtime import ACTIVE_UNIT as UNIT,OUTPUT_ROOT as ROOT,HERE,sha,js,now
from pathlib import Path
import json,datetime

def load(p):return json.loads(p.read_text())

def main():
    asset=load(UNIT/'asset/ASSET.json');audit=load(UNIT/'AUDIT.json');readback=load(UNIT/'PATH_READBACK.json')
    match=load(UNIT/'BUILD_MATCH.json');summary=load(UNIT/'SUMMARY.json');attr=load(UNIT/'attribution/SUMMARY.json');far=load(UNIT/'FAR_READBACK.json')
    replay=load(UNIT/'cached_placement_replay/REPLAY_RECEIPT.json');assert audit['status']=='pass' and replay['all_equal']
    commands={p.stem:load(p) for p in sorted((UNIT/'logs').glob('*.json'))}
    assert commands['placement_RED']['child_returncode']==1
    assert all(x['child_returncode']==0 for k,x in commands.items() if k!='placement_RED')
    images=['ALL_DEV_MATCHED.png','ALL_DEV_NATURAL.png','REAR_CAMERA_SEQUENCE.png',
        'dev/orbit_241_24_5.3/COMPARISON.png','dev/orbit_61_24_5.3/SEPARATE_LAYERS.png',
        'dev/orbit_241_24_5.3/SEPARATE_LAYERS.png','dev/orbit_241_24_5.3/INK_LAYERS.png']
    js(UNIT/'VISUAL_REVIEW.json',dict(images={name:sha(UNIT/name) for name in images},
        verdict='Visible local rearrangement; no established whole-object readability/cleanliness advantage. Front still short bundles; rear still cross grid and patchy paper; keep original default.',
        scope='Assistant inspection of complete object, natural/matched, linked/ungated, separate layers and actual changing cameras; not a blind preference study or temporal certification.'))
    next_step='下一次只读Astra审查及父级冻结后，优先转向已具可辨认平行排线的既有Chair座面，保留简单基线，做一次固定的单部件间距编辑及新路径原ID支持验证。先核查v06实际Chair源码、region_4路径、SOURCE_LINK和前后完整图，再冻结一次编辑值与相机；不搜索风格参数。新路径分配新身份，非目标路径逐字节保持，原256690行、M1/UNKNOWN及原纸底/墨权重不改。对预先分层抽取的新stroke弧长样本记录真实接受的original-ID、alpha、T与alpha*T，保存无支持样本、采样分母和未认证剩余路径；不能把最近核或区域S当逐路径所有权。输出实际前后linked/同墨预算ungated完整物体、独立墨层及保存加载复放。依赖现有环境，不重复bootstrap；所有旧Chair资产只读，适配与输出进入新v07单元。此为已有可用基线上的编辑与链接能力验证，不宣称本轮Lego布置成功或新的NPR优势。'
    why='Lego四轮不同机制均未建立整物体优势，本轮甚至未提高全局平均同层间距，继续调候选预算、距离阈值或叠加平滑没有证据。只读查看v06保存的Chair hybrid及报告，座面已有可辨认平行排线；对应资产、原行绑定和旧路径查询数据实际存在。选择这个已有可用的简单生成器开展BRIEF的新路径支持/标准编辑，是独立的应用与原Gaussian连接进展；旧路径证明不能自动迁移到新路径。Chair不是噪声真值或跨场景因果对照。'
    js(UNIT/'NEXT.json',dict(action='continue',recommended_next_step=next_step,why=why,estimated_minutes=25,
        requires_next_read_only_review=True,no_new_units_after_jst='2026-10-25T14:25:00+09:00'))
    js(UNIT/'ENGINEERING_NOTES.json',dict(expected_RED='Missing placement module; original rc1 and traceback preserved. All later scientific commands rc0.',
        read_only_lookup='The v07 replay package has no Chair directory; a read-only lookup confirmed the original v06 portable Chair assets and displayed its saved hybrid. No Chair import, write, run or second-scene experiment occurred in unit004.',
        sample_scope='Whole-path clearance uses segment-based quadrature and graph upper bounds. It is not exact geodesic distance or an independent collision certificate; per-stroke visibility also has inherited segment quadrature dependence.',
        selection_limit='A minimum-clearance-first coordinate pass does not optimize global mean spacing. It also treats longitudinal endpoint gaps and transverse gaps with an isotropic distance, so it is not a certified equal-spacing hatch layout.'))
    lines=['# Unit004：固定长度的表面种子重排，整物体优势未建立','',
        '**G0/G1实际比较完成；73条种子移动，380条笔触数量及逐笔触长度保持。完整物体可读性优势未建立，不升级默认。NEXT=continue，scientific_seal=false，父级验证待完成。**','',
        '已实际检查四个完整DEV自然/配平图、弱后视角linked/同预算ungated对照、前后分层pre-S墨以及231°/241°/251°相机序列。前侧局部线条重排、有些位置更密；后侧短交叉网格和斑驳纸底仍在。完整物体未稳定呈现更清楚、干净的铲斗形体。这是有限目视检查，不是独立用户偏好研究。','',
        '## 单一机制与公平约束','',
        'G0用原载体和unit003保存F0场、相同行走器恢复旧路径；全部保存几何及实际墨图逐值恢复unit003 F0/原A。G1只移动三维种子。每个旧/新增分区、方向层、真实流形共享边连通分量的笔触配额及每个父路径请求长度固定，不能把短线转移为长线或删掉困难分量。G0/G1新身份分别为父ID+500000000000/600000000000，face/bary和父路径来源保存；不表示Gaussian所有权。','',
        '一次确定性坐标替换：按父ID升序，每条stroke从原连通分量按三角形面积抽12个均匀表面候选，PCG64种子为20261025+父ID。每个候选沿固定F0双向各走原长度一半；任一端提前停止即拒绝，原种子始终为可行候选。对同分量同方向层的其他当前完整路径，先最大化最小距离，再最大化弧长加权平均距离；相等保留原种子，仅做一遍。双层预期交叉不互相排斥。','',
        '距离通过真实流形共享边中点作为通道、三角形内直线连接；另直接计算同面采样点到其他线段距离。整条路径按不超过0.01世界单位分段采样、梯形弧长加权，距离按继承层间距0.06/0.075封顶。该路线距离是表面距离上界近似，不是精确测地线，也不是碰撞真值。目标优先改善局部最小间距，不保证全局平均间距改善；各向同性距离也没有区分预期纵向断笔间隙与横向线间距。不能将本次实现称为成熟等距表面排线。','',
        '原16543顶点/29999面、法线、F0场、unit010基底及35°/95°切平面法向、原遮挡/0.004容差、1px/AA2和2px评价带保持。原310475 Gaussian行/顺序、原PLY/几何/协方差/opacity/完整SH、41058纸底与21006墨权重、195279 UNKNOWN/M1、2121面作者目标与旧2030/新增91分区保持。新位置采样同一F0会改变初始切向；实际间距/空间相位是干预，不宣称保留原0.035间隙。没有叠加unit002载体降噪或unit003场正则化。','',
        '## 实际生成与布置反证','',
        '| 分区 | 原连通分量 | 移动/总笔触 | 可完整生成候选/尝试 | 总长度G0/G1 |','|---|---:|---:|---:|---:|']
    for part in ('old','added'):
        d=asset['placement'][part];a=asset['paths']['G0_'+part];b=asset['paths']['G1_'+part]
        lines.append(f"| {part} | {d['components']} | {d['moved_strokes']}/{d['strokes']} | {d['feasible_candidates']}/{d['attempted_candidates']} | {a['length']:.9f}/{b['length']:.9f} |")
    lines += ['',f"760个输出端点均达到继承请求长度，存储内部断点0。逐笔触长度最大误差{audit['max_request_length_error']:.3g}，face/bary锚点误差{audit['max_anchor_error']:.3g}；沿固定F0的每笔触切片层位残差最大{audit['max_cutting_plane_residual']:.3g}。拒绝的替代候选原因全部保存，主要为真实网格/作者分区边界；没有为了提高可行数放宽停止规则。旧请求长度本身已含历史边界截断，不能说原路径没有边界停止。",'',
        '| 分区 | 同层最小采样距离G0/G1 | 弧长加权平均封顶距离G0/G1 | 主分区/新增分区转角中位数G0/G1 |','|---|---:|---:|---:|']
    for part in ('old','added'):
        d=load(UNIT/'asset'/('PLACEMENT_'+part+'.json'));a=d['before'];b=d['after'];x=readback['paths'][part+'_G0'];y=readback['paths'][part+'_G1']
        lines.append(f"| {part} | {a['sample_quantiles'][0]:.6f}/{b['sample_quantiles'][0]:.6f} | {a['weighted_mean_capped_distance']:.6f}/{b['weighted_mean_capped_distance']:.6f} | {x['shared_edge_turn_degrees_quantiles'][0]:.3f}°/{y['shared_edge_turn_degrees_quantiles'][0]:.3f}° |")
    lines += ['','主分区最小距离有所增大，但两个分区的全局加权平均距离均下降，P10也下降；不能说整体分布更均匀或已经修复同层拥挤。主分区跨面转角中位数18.817°→19.252°、P95 90.048°→94.358°，单位长度总转角也增加；新增小分区略改善。重排改变了采样到的载体位置，没有修正F0的局部转折。','',
        '全物体图像的干预有效：四DEV目标中RGB L1差≥0.05的像素约18.86%–23.16%，不是只移动不可见路径或no-op。0.05仅为描述，不是新的通过门槛。单独分层图没有证明所有网格交点都是同层碰撞；跨层交叉属于原定风格。','',
        '## BUILD墨量与完整DEV','',
        f"四BUILD自然目标墨RGB L1：{json.dumps(match['natural_totals'])}。公共预算{match['budget']:.6f}，每臂固定全局系数{json.dumps(match['scales'])}。实际合成读回在浮点误差内一致，自然强度保留，无DEV/逐相机拟合。",'',
        '| DEV相机 | 目标像素 | 目标墨L1 G0/G1 | 全目标覆盖G0/G1 | 内部覆盖G0/G1 |','|---|---:|---:|---:|---:|']
    for r in summary[:4]:
        a=r['G0_linked'];b=r['G1_linked'];lines.append(f"| {r['view']} | {r['target_pixels']} | {a['ink_L1']:.3f}/{b['ink_L1']:.3f} | {100*a['coverage']:.2f}%/{100*b['coverage']:.2f}% | {100*a['interior_coverage']:.2f}%/{100*b['interior_coverage']:.2f}% |")
    lines += ['','四DEV墨覆盖均增加，但完整可读性未随之建立。弱241°/24°目标覆盖仅35.66%→35.69%，配平目标墨量下降；前侧覆盖更广且部分笔触更密，也不能单独归为清晰度改善。同预算ungated弱角度覆盖40.57%→40.50%，仍没有明显整物体优势。S继续作为可选原行区域连接，不宣称NPR质量贡献。','',
        '## 可见支持与S衰减','',
        '| 相机/臂 | 代理可见长度px | pre-S自身缺失px | linked配平自身缺失px | linked有支持长度px |','|---|---:|---:|---:|---:|']
    for r in attr:lines.append(f"| {r['view']} {r['arm']} | {r['proxy_visible_length']:.3f} | {r['preS_own_visible_missing_length']:.3f} | {r['linked_matched_own_visible_missing_length']:.3f} | {r['proxy_visible_length']-r['linked_matched_own_visible_missing_length']:.3f} |")
    lines += ['','前侧支持长度增长来自重新分布后的可见长度增长，不是修复同一笔触的断裂。弱后视角pre-S缺失基本不变，linked缺失减少，但可见长度853.910→834.621px，最终有支持长度726.001→711.731px反而下降。必须保留可见长度分母，不能只看缺失分子。采样使用每笔触自身光栅支持，不借别的笔触重叠获益；它仍依赖分段求积和当前代理可见性，并非物理真值。深度拒绝中含真实背面与遮挡，不全部算渲染错误。','',
        '## 绝对远区损伤','',
        '| DEV相机 | linked远其他源差L1 G0/G1 | linked背景源差L1 G0/G1 | G1 ungated远其他源差L1 |','|---|---:|---:|---:|']
    for r in summary[:4]:
        a=r['G0_linked'];b=r['G1_linked'];lines.append(f"| {r['view']} | {a['far_other']:.9f}/{b['far_other']:.9f} | {a['background']:.9f}/{b['background']:.9f} | {r['G1_ungated']['far_other']:.9f} |")
    lines += ['',f"表内包含原纸底既有损伤。六个不同评估相机的新增G1-G0 linked远区最大像素L1={max(r['far_max_pixel_L1'] for r in far):.12g}，超过1/255的像素合计{sum(r['far_pixels_above_1_255'] for r in far)}；弱后视角有一个非零远区像素，不称严格零。未扩大评价边界带或删除困难区域。",'',
        '## 验证、复放与范围','',
        f"TDD缺placement模块的RED rc1原日志保留；4组GREEN通过，涵盖已知平面近距/交叉、曲面长度与确定性、真实共享边/孔洞/分离片/仅顶点接触/非流形边，以及同标签前景和零S。实际派生、BUILD、DEV/arc、逐笔触归因和独立审计均rc0。审计核对{audit['input_files_checked']}份冻结输入、源码快照、原行身份权重、每父路径长度与分量/层配额，并完整解码校验{audit['pngs_decoded_and_checked']}张PNG。新进程实际重栅格化弱后视角，{replay['arrays']}数组逐值恢复。",'',
        '```bash',
        '/mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_8build_part_prior_feasibility_v03/venv/bin/python -B /home/u00134/3dgs_line/partwise_sketch_hatching_gaussian_link_v07/experiments/partwise_sketch_hatching_v07/placement_unit/replay_placement.py --out /mnt/hdd1/u00134/partwise_sketch_hatching_gaussian_link_v07/units/unit_004/user_replay_001 --view orbit_241_24_5.3',
        '```','',
        '输出须是unit004内不存在的新目录。该入口验证锁定源码/资产并实际重画墨，复用已验证GS source/paper/S；不是第二次冷GS或独立便携包。unit001一次完整冷重放成功保持。本轮沿用现有NumPy/SciPy/Open3D环境，CPU两核亲和、数值线程1、串行、CUDA为空；无GPU、训练、安装、网络下载或嵌套模型。所有重数据在新HDD单元，旧包/原PLY/旧环境未写入。','',
        '四DEV与三后侧arc只有六个不同评估相机，241°/24°明确复用，全部EXPOSED。三帧实际变相机序列不是连续视频或时序稳定认证。Lego是既有冻结GS资产，非本轮采集的真实世界数据；载体是重建代理，不是独立表面真值。','',
        'v05稀疏任务far8.044%、31像素腐蚀目标及4.49%作者区域可见变化失败，v06各负结果以及v07 unit001续接、unit002降噪、unit003场正则化负结果全部保留。当前仍是原GS纸底加原ID区域门控代理墨，不是原生Gaussian排线、逐路径原ID所有权、完整语义部件或H1/H2/H3证明。','',
        '## 下一步','',next_step,'',why,'',
        '本单元仅完成unit004，不自动开启另一个科学单元。后续须重新只读审查及父级冻结；14:25禁启新单元，14:45科学收尾，15:00硬停止。']
    report='\n'.join(lines)+'\n';(UNIT/'REPORT_ZH.md').write_text(report)
    docs=HERE.parent.parent.parent/'docs/partwise_sketch_hatching_v07';docs.mkdir(exist_ok=True)
    (docs/'unit004_surface_placement.md').write_text(report)
    elapsed=(datetime.datetime.now(datetime.timezone.utc)-datetime.datetime.fromisoformat('2026-10-25T12:31:26.099609+09:00')).total_seconds()/60
    js(UNIT/'STATUS.json',dict(unit='unit_004',execution_state='completed',stage='actual_G0_G1_comparison_and_readback_complete',
        scientific_verdict='negative_for_this_placement: visible rearrangement without established whole-object advantage; global mean clearance decreased; default not promoted',
        gaussian_link_progress='Original310475 rows, paper41058/ink21006 weights and M1/UNKNOWN unchanged. Actual new path rasterization linked to fixed original-ID regional S; no new per-path certification.',
        scientific_seal=False,parent_verification='pending',actual_commands=commands,
        tests=dict(expected_red='placement_RED',green='placement_GREEN_001',audit='audit',replay='cached_placement_replay'),
        artifacts=['PROTOCOL.json','asset/ASSET.json','asset/PLACEMENT_old.json','asset/PLACEMENT_added.json','ALL_DEV_MATCHED.png','ALL_DEV_NATURAL.png','REAR_CAMERA_SEQUENCE.png','attribution/SUMMARY.json','AUDIT.json','PATH_READBACK.json','FAR_READBACK.json','VISUAL_REVIEW.json','cached_placement_replay/REPLAY_RECEIPT.json','REPORT_ZH.md','NEXT.json'],
        blockers=[],elapsed_minutes_from_authorization=elapsed,execution_authorized_jst='2026-10-25T12:31:26.099609+09:00',finished_utc=now()))
    js(UNIT/'EXECUTION_RECORDS.json',commands)
    js(UNIT/'HANDOFF_SOURCE_LOCK.json',dict(files={str(p):sha(p) for p in HERE.iterdir() if p.is_file()}))
    print(json.dumps(dict(execution_state='completed',elapsed_minutes=elapsed,next='continue')),flush=True)

if __name__=='__main__':main()
