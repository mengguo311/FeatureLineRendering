"""Chinese handoff from completed, frozen evidence; no experiment reruns."""
import runtime
from runtime import ACTIVE_UNIT as UNIT,HERE,sha,js,now
import json,datetime

AUTHORIZED='2026-10-25T13:32:56.142088+09:00'
def load(name):return json.loads((UNIT/name).read_text())

def main():
    asset=load('asset/ASSET.json');audit=load('AUDIT.json');diag=load('BOUNDARY_READBACK.json')
    match=load('BUILD_MATCH.json');rows=[r for r in load('SUMMARY.json') if r['kind']=='dev'];attr=load('attribution/SUMMARY.json')
    replay=load('cached_boundary_replay/REPLAY_RECEIPT.json');assert audit['status']=='pass' and replay['all_equal']
    commands={p.stem:json.loads(p.read_text()) for p in sorted((UNIT/'logs').glob('*.json'))}
    assert commands['red_boundary']['child_returncode']==1
    assert all(r['child_returncode']==0 for name,r in commands.items() if name!='red_boundary')
    for path,h in load('ENGINEERING_ADAPTER_LOCK.json')['files'].items():assert sha(path)==h
    visual=dict(verdict='negative: no established whole-object benefit of boundary-aligned gaps over equal-length sham gaps',
        inspected=['ALL_DEV_MATCHED.png','ALL_DEV_NATURAL.png','REAR_CAMERA_SEQUENCE.png','dev/orbit_241_24_5.3/COMPARISON.png','dev/orbit_241_24_5.3/INK_LAYERS.png','dev/orbit_61_24_5.3/INK_LAYERS.png'],
        front='B/C均保留原H部分顺向线束，同时引入额外断笔；局部形状略有差异，完整铲斗未呈现B稳定优于C的清晰度或完整性。',
        rear='后侧自然和配平结果仍有短线、空白及照片残留。边界处留白未形成明确整物体优势；231/241/251实际相机变化中未见稳定优于非边界留白。',
        interpretation='B确实删除更多排除边转折，但转折计数降低不等于可读性改善。B/C均减少可见支持；不能把删墨后较稀疏称为成功。',
        scope='有限目视比较，无独立用户偏好、真实表面或时序稳定认证。')
    js(UNIT/'VISUAL_REVIEW.json',visual)
    nextstep='下一次只读Astra审查与父级冻结后，在已有可辨认平行排线的Chair作者座面region4，验证一次固定间距编辑及新路径原ID支持。建议spacing由0.045一次改为0.05625，不扫描；角度95、length0.22、width1及ink_strength0.35和载体、纸底/墨行权重、M1/UNKNOWN保持。先恢复原资产并核对继承visibility_mask与新路径owner-only规则，必要时用同规则重生成对照，避免把掩码变化算作间距效果。非目标路径逐字节保持，新路径分配新身份及face/bary。预先固定分层弧长样本，记录实际CPU接受的original source_index、alpha、T、alpha*T、无支持样本和未认证剩余路径；完整前后图、自然墨、linked/同预算ungated、保存加载及实际重放一并交付。现有依赖和冷重放基础复用。该路线验证编辑和来源证据，不是Lego载体噪声的跨场景因果结论。'
    why='Lego边界配对已有实际余量：59条父路径、73次排除边转折被删除，但B未优于等长C建立整物体收益，继续扫描宽度或边界角阈值无依据。只读复看v06 Chair的61/24及241/60完整图，座面平行排线可辨；实际asset.json有region4风格，link_renderer.py具备真实接受事件与original source_index/alpha/T接口。标准编辑和有界新路径来源记录仍是BRIEF允许的独立路线，旧区域S不能替代这项证据。'
    js(UNIT/'NEXT.json',dict(action='continue',recommended_next_step=nextstep,why=why,estimated_minutes=30,requires_next_read_only_review=True,no_new_units_after_jst='2026-10-25T14:25:00+09:00'))
    verdict='negative for boundary-gap promotion: B removes sharp-interface transitions but does not establish whole-object advantage over equal-length sham C; both lose coverage/support; default unchanged'
    elapsed=(datetime.datetime.now(datetime.timezone.utc)-datetime.datetime.fromisoformat(AUTHORIZED)).total_seconds()/60
    status=dict(unit='unit_008',execution_state='completed',stage='actual_A_B_C_visual_audit_and_replay_complete',scientific_verdict=verdict,
        gaussian_link_progress='Original310475 rows/geometry/fullSH/opacity/order and paper41058/ink21006 weights, M1/UNKNOWN195279 remain fixed. A is saved H; each B/C has118 new children from59 H parents and321 unchanged paths, explicit original-parent plus immediate-H provenance and face/bary. Cached original-GS paper/S with actual rerendered proxy ink; no per-path original-ID ownership certification.',
        scientific_seal=False,parent_verification='pending',actual_commands=commands,
        tests=dict(expected_red='red_boundary:missing module rc1',green='green_boundary:3 groups',audit='audit',replay='replay:41 arrays exact',post_eval_readback='diagnostics'),
        artifacts=['PROTOCOL.json','asset/ASSET.json','asset/old_PAIRS.json','asset/added_PAIRS.json','ALL_DEV_MATCHED.png','ALL_DEV_NATURAL.png','REAR_CAMERA_SEQUENCE.png','attribution/SUMMARY.json','PAIR_READBACK.json','BOUNDARY_READBACK.json','VISIBLE_INTERVENTION.json','FAR_READBACK.json','AUDIT.json','VISUAL_REVIEW.json','cached_boundary_replay/REPLAY_RECEIPT.json','ENGINEERING_ADAPTER_LOCK.json','REPORT_ZH.md','NEXT.json'],
        blockers=[],execution_authorized_jst=AUTHORIZED,elapsed_minutes_from_authorization=elapsed,finished_utc=now(),
        limitations=['Geometric excluded edges are not confirmed semantic boundaries.','59/380 eligible parents; unchanged additions have no excluded crossings.','B/C match total length and child count, not child-length distribution or projected visible removal.','All cameras EXPOSED; no temporal, true-surface, native-Gaussian or per-path ownership claim.'])
    js(UNIT/'STATUS.json',status);js(UNIT/'EXECUTION_RECORDS.json',commands)
    lengths={arm:sum(asset['paths'][arm+'_'+part]['length'] for part in ('old','added')) for arm in ('A','B','C')}
    report=['# Unit008：边界留白未优于等长非边界留白建立整物体收益','',
        '**实际A/B/C对照、四BUILD、四DEV/三arc、逐笔触支持归因、独立审计及保存加载重放完成。结果为负，不升级默认。execution_state=completed，scientific_seal=false，父级验证待完成，NEXT=continue。**','',
        visual['front']+visual['rear']+'这是有限目视检查，不是用户偏好研究。','',
        '## 冻结干预与实际余量','',
        'A逐字节保留unit007的H路径及种子/停止记录。B在既有excluded_pairs的真实跨面处留白；C在同一父路径上、与B不重叠且不跨排除边的最长可用区间中心留白。均使用原0.035世界弧长，每父路径最多一处；按保存弧长顺序采用首个可配对位置。每臂保留两个非空子路径；精确并列取较早弧长区间。无法配对的路径保持原样。无相机参与选择，无新角度、场求解、载体改动或间隙宽度扫描。','',
        '原H旧分区360条中130条跨越排除边，共178次跨面；59条可配对，71条没有可行等长对照，230条不跨排除边。新增分区20条全部不跨排除边。共59条父路径被处理、321条保持；每个B/C臂有118条新子路径，总439条，对照A为380条。两臂各删除2.065世界长度；没有删除整条父路径。','',
        f"总世界长度A/B/C={lengths['A']:.9f}/{lengths['B']:.9f}/{lengths['C']:.9f}；相对A减少{100*(1-lengths['B']/lengths['A']):.3f}%。B/C匹配每父路径总保留长度与子路径数，但断点位置使两个子路径的长度分配不同，不能声称逐子路径长度分布相同。",'',
        '新ID：B为2e12、C为3e12起的分区/父路径序号/左右子路径编码。原parent_stroke_id保持，PAIRS.json另存即时H父ID、切除区间、触发面边、C可用区间及子ID。未处理路径的所有字段/ID不变。face/bary只是代理锚点，不是Gaussian所有权。','',
        '原16543顶点/29999面、两层H方向与交叉关系、原310475行身份/顺序/PLY/中心/协方差/opacity/完整SH、41058纸底和21006墨行权重、M1/UNKNOWN195279、2121作者目标与旧2030/新增91分区、1px/AA2、0.004深度容差、2px评价带不变。排除边来自冻结几何启发式，不能称为确认的语义/结构真值。','',
        '## 转折机制与反证','',
        '| 旧分区 | 图内跨面 | 图内钝角 | 排除边跨面 | 排除边钝角 |','|---|---:|---:|---:|---:|']
    for arm in ('A','B','C'):
        q=diag['transitions'][arm+'_old'];report.append(f"| {arm} | {q['graph']['transitions']} | {q['graph']['obtuse_intrinsic']} | {q['excluded']['transitions']} | {q['excluded']['obtuse_intrinsic']} |")
    report+=['','B真实删除73次排除边跨面，其中8次为展开后的钝角转向；C保留全部178次及20次钝角。剩余B排除边世界转角P95反而较高，说明删去某些转折不等于剩余表面更平滑。真实干预成立，但这不是图像质量分数。原H的zero_step_cycle父路径和失败记录完整保留于A及BOUNDARY_READBACK；B/C对子路径的裁切不是修复该行走器问题。','',
        '## BUILD墨量与完整DEV','',
        '自然四BUILD目标墨RGB L1：'+json.dumps(match['natural_totals'])+'。',
        f"共同预算{match['budget']:.6f}；每臂固定全局系数"+json.dumps(match['scales'])+'。自然结果同时保存，无DEV拟合。A自然墨/混合逐值恢复unit007 H；本轮A配平系数改变，不能把新A配平图当成旧单元同强度H。','',
        '| DEV | 目标像素 | 目标墨L1 A/B/C | 覆盖A/B/C | 内部覆盖A/B/C |','|---|---:|---:|---:|---:|']
    for r in rows:
        q=[r[a+'_linked'] for a in ('A','B','C')];report.append('| '+r['view']+f" | {r['target_pixels']} | "+'/'.join(f"{x['ink_L1']:.3f}" for x in q)+' | '+'/'.join(f"{100*x['coverage']:.2f}%" for x in q)+' | '+'/'.join(f"{100*x['interior_coverage']:.2f}%" for x in q)+' |')
    report+=['','B/C在四DEV覆盖均低于A。B相对C在三视角略多覆盖、前低视角更少，但没有稳定整物体观感优势；弱后侧31.93%/31.04%/30.91%的接近数值不能替代可读性判断。独立墨层仍有碎线，S还会使其变淡；同预算ungated也未显示明确的边界留白优势，区域S继续只作为可选原ID连接。','',
        'B与C配平linked的目标RGB L1差≥0.05占比（仅沿用描述口径，不是通过门槛）：'+', '.join(f"{r['view']}={100*r['above_005_fraction']:.2f}%" for r in diag['BC_dev_effects'])+'。实际差异存在，幅度有限；全目标未参与切除的位置也可能因单一全局配平系数产生强度差。','',
        '## 逐笔触自身支持','',
        '| 相机/臂 | 代理可见长度px | pre-S缺失px | linked配平缺失px | linked支持px |','|---|---:|---:|---:|---:|']
    for r in attr:report.append(f"| {r['view']} {r['arm']} | {r['proxy_visible_length']:.3f} | {r['preS_own_visible_missing_length']:.3f} | {r['linked_matched_own_visible_missing_length']:.3f} | {r['proxy_visible_length']-r['linked_matched_own_visible_missing_length']:.3f} |")
    report+=['','两种留白均缩小可见长度分母。弱后侧linked支持A/B/C约661.536/603.828/606.755px；B甚至略低于C。缺失分子变小不能称为连续性改善。样本使用每个子stroke自身光栅支持，不借其他笔触重叠；裁切改变采样区间与求积分段，差值是代理描述，不是独立物理真值。深度拒绝包含正确遮挡。','',
        '## 远区绝对损伤','',
        '| DEV | linked远其他源差L1 A/B/C | 背景源差L1 A/B/C |','|---|---:|---:|']
    for r in rows:
        q=[r[a+'_linked'] for a in ('A','B','C')];report.append('| '+r['view']+' | '+'/'.join(f"{x['far_other']:.9f}" for x in q)+' | '+'/'.join(f"{x['background']:.9f}" for x in q)+' |')
    report+=['','上述源差包含固定纸底的原有损伤。六个不同评估相机、三组臂间比较的linked配平远区最大单像素L1='+f"{diag['maximum_linked_matched_far_pixel_L1']:.12g}"+'；超过1/255的远区变化像素合计0。存在微小非零差，不能写成严格零。自然/配平、linked/ungated的全部绝对读回在FAR_READBACK.json。','',
        '## 测试、工程记录和复放','',
        'TDD先缺boundary模块的预期RED rc1，随后3组GREEN：平面无可用边/短路径不变；平面/折面/曲面等长切除、非空子路径、确定性、端点与锚点；同标签分离前景真实遮挡及零S。实际派生、BUILD、DEV/arc、归因、独立审计、复放和诊断均rc0。',
        f"独立审计检查{audit['input_files_checked']}份输入，使用另一种区间分割读回选择规则；最大切除长度误差{audit['max_removed_length_error']:.3g}，锚点误差{audit['max_anchor_error']:.3g}。核对{audit['pngs_checked']}张主PNG与数组，完整解码当时全部{audit['all_png_fully_decoded']}张PNG。新进程实际重栅格化弱后侧，{replay['arrays']}数组逐值恢复。",'',
        '复制继承循环时PATH_ARMS误替换为PATB_ARMS；在首次DEV评估前静态检查发现。冻结run_boundary.py、协议、DECISION及完成的BUILD均保留，单独哈希锁定execute_boundary.py仅提供相同三臂tuple的别名，评估和归因通过该入口执行。此问题没有触发运行失败，没有修改科学机制/参数或重跑BUILD。ENGINEERING_ADAPTER_LOCK.json记录适配范围；原预期RED日志不覆盖。','',
        '```bash','/mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_8build_part_prior_feasibility_v03/venv/bin/python -B /home/u00134/3dgs_line/partwise_sketch_hatching_gaussian_link_v07/experiments/partwise_sketch_hatching_v07/boundary_unit/replay_boundary.py --out /mnt/hdd1/u00134/partwise_sketch_hatching_gaussian_link_v07/units/unit_008/user_replay_001 --view orbit_241_24_5.3','```','',
        '输出必须为unit008内不存在的新目录。source/paper/S复用已验证缓存，墨实际重画；不是第二次冷GS或独立便携包。unit001一次cold hybrid记录保持。现有依赖不变，CPU两核亲和、数值线程1、串行、CUDA为空；无安装、下载、GPU、训练、嵌套模型或push/merge。','',
        '四DEV与三arc仅六个不同评估相机，241°/24°明确重复，全部EXPOSED；三帧不是连续视频或时序认证。场景是既有NeRF Synthetic Lego冻结vanilla-GS的CPU协方差平面深度/TSDF代理，非本轮采集真实物体或RaDe训练/GT。当前是原GS纸底和原ID区域S门控代理墨，非原生Gaussian排线、完整语义部件、物理真值或逐路径原ID认证。','',
        'v05稀疏任务far8.044%、31像素腐蚀目标、4.49%作者区域变化失败，以及v06与v07 unit001–007全部负结果保持。H局部PARTIAL不改写为整物体成功；B/C负结果也不能反推载体必为主因或否定所有确认结构边界关联。','',
        '## 下一步','',nextstep,'',why,'',f'本次只完成unit008，报告时从授权计约{elapsed:.2f}分钟。下一科学单元须新的只读审查与父级冻结；14:25禁启、14:45科学收尾、15:00硬停止。']
    (UNIT/'REPORT_ZH.md').write_text('\n'.join(report)+'\n')
    js(UNIT/'HANDOFF_SOURCE_LOCK.json',dict(files={str(HERE/name):sha(HERE/name) for name in ('execute_boundary.py','read_boundary_diagnostics.py','finish_boundary.py')}))
    print(json.dumps(dict(execution_state='completed',scientific_verdict=verdict,next='continue',elapsed_minutes=elapsed),ensure_ascii=False),flush=True)

if __name__=='__main__':main()
