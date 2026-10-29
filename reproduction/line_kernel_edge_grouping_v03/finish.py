"""Verify immutable pilot artifacts and write the final handoff, without regrouping."""
from pilot import *

def main():
    guard();config=json.loads((OUT/'CONFIG.json').read_text());assert sha(OUT/'DECISION.json')==config['decision_sha256']
    for f,h in {**config['source_files'],**config['helper_files']}.items():assert sha(f)==h,f
    checked=0
    for seal in sorted(OUT.rglob('SEAL.json')):
        d=json.loads(seal.read_text())
        for name,h in d['files'].items():assert sha(seal.parent/name)==h,str(seal.parent/name);checked+=1
    for scene in ['scan24','ficus','scan65']:
        before=json.loads((OUT/scene/'SOURCE_HASHES_BEFORE.json').read_text());after=json.loads((OUT/scene/'SOURCE_HASHES_AFTER.json').read_text());assert before==after
        for f,h in before.items():assert sha(f)==h,f
    run=json.loads((OUT/'RUN_EXIT.json').read_text());assert run['all_complete'];assert json.loads((OUT/'TEST_GREEN_RECEIPT.json').read_text())['returncode']==0;assert json.loads((OUT/'TEST_RED_RECEIPT.json').read_text())['returncode']!=0
    audit=json.loads((OUT/'INDEPENDENT_AUDIT_SUMMARY.json').read_text());assert json.loads((OUT/'DIAGNOSTICS_PROCESS_EXIT.json').read_text())['returncode']==0
    reviews=dict(reviewed_utc=now(),scope='Manual inspection of both fixed-camera full comparisons, Hough largest-three isolated groups and largest-three cross-parent groups in all scenes; scan24 baseline largest groups and selected scan24 negative proposals also inspected.',large_object_blob_observed=False,physical_identity_certified=False,broad_grouping_goal_met=False,hough_improvement_demonstrated=False,findings_zh=[
        'scan24最大Hough组639核、仅1个旧parent；最大跨parent组159核，由120+39核组成，支持局部几何连续，但不是大规模碎片统一。',
        'scan24跨parent组95112为127+4核，存在明显转折；不能把跨parent数量当作多个完整碎片成功拼接。',
        'ficus最大组1186核、仅1个旧parent；全景中最大几条线伸出植株外。几何比特不变证明这些线属于原始专用线核资产，本次未裁剪或修饰，不能称为真实叶缘成功。',
        'ficus最大跨parent组74核（66+8），另一个72核组为71+1；可见的是短局部轨迹，没有展示跨大量碎片的完整叶缘。',
        'scan65最大跨parent组167核为163+4；最大几组没有物体级巨团，但碎片聚合仍很弱。',
        '原生固定相机存在离屏或端视压缩，部分负例在一个视图为空；放大图是原生高斯渲染裁剪放大，不是新几何。',
        'parallel_or_crossing_reject仅为角度拒绝类别名称，不是真实平行或交叉的人工标签。'])
    js(OUT/'VISUAL_REVIEW.json',reviews)
    summary=dict(engineering_status='COMPLETE_ALL_THREE_FULL_ASSETS',scientific_status='LIMITED_LOCAL_CROSS_PARENT_GROUPING; BROAD_LONG_EDGE_GOAL_NOT_MET; HOUGH_BENEFIT_NOT_DEMONSTRATED',total_original_kernels=sum(COUNTS.values()),methods=['baseline','hough'],no_tuning_after_freeze=True,all_geometry_audits_passed=True,all_child_returncodes=[r['returncode'] for r in run['receipts']],all_scenes_completed_before_deadline=True,comparisons=audit['comparisons'],frozen_decision_sha256=config['decision_sha256'],config_sha256=sha(OUT/'CONFIG.json'),output_bytes_before_final_index=sum(f.stat().st_size for f in OUT.rglob('*') if f.is_file()),elapsed_from_administrative_start_seconds=time.time()-(DEADLINE-35*60),completed_utc=now(),remaining_work='None for this authorized one-shot pilot; no automatic continuation.')
    js(OUT/'SUMMARY.json',summary)
    lines=['# 完整线高斯核跨 parent 边分组：单次冻结试验','',
    '已完成 scan24 → ficus → scan65 三份原始完整 C8 资产，共 1,024,062 个核；两个方法均保存全量 kernel→edge_id/UNKNOWN、原始几何扩展 PLY、彩色显示副本、固定两视图全景与最大组隔离渲染。**工程交付完成；科学目标只得到局部跨 parent 拼接支持，未达到大规模长曲边归并，Hough 未证明优于空间/切向基线。**','',
    '没有重新平滑、移动核或拟合替代曲线，没有调参重跑。旧 parent 不参与候选资格或评分；它只用于来源统计。所有身份均为暂定几何假设，无独立真实边标签，也无源场景 GS 关联或物理正确率。','',
    '| 场景 | 方法 | 全核数 | 已分配 | UNKNOWN | 覆盖率 | 组数 | 跨 parent 组 | 跨 parent 组内核数 | 最大跨 parent 组 |',
    '|---|---|---:|---:|---:|---:|---:|---:|---:|---:|']
    by={(d['scene'],d['method']):d for d in audit['scenes_methods']}
    for scene in ['scan24','ficus','scan65']:
        for method in ['baseline','hough']:
            d=by[(scene,method)];lines.append(f"| {scene} | {method} | {d['complete_rows']} | {d['assigned']} | {d['unknown']} | {d['assigned']/d['complete_rows']:.2%} | {d['emitted_groups']} | {d['cross_parent_groups']} | {d['cross_parent_kernels']} | {d['largest_cross_parent'][0]['kernels']} |")
    lines += ['', '跨 parent 不等于正确：有些组只从第二个 parent 吸收1–5个核。要求每个来源 parent 至少贡献6核后，Hough 的跨 parent 组数为 scan24 213、ficus 123、scan65 145。最大跨 parent 组来源组成分别为120+39、66+8、163+4核。','',
    'Hough 确实进行了全资产分块投票和跨块协调，三个场景协调合并了3098、895、1165对线族假设，保留2065、1225、1517个候选线族。它们不是主边身份。相对空间邻居新增的候选对为609、3、319，但**新增候选中最终接受的连接均为0**；实际结果差异来自已有候选的固定0.85评分修正及共同歧义规则。不能把候选线族数描述成已发现的物理边数。','',
    '| 场景 | Hough − 基线已分配核 | 主分组内跨 parent 连接：基线 / Hough |', '|---|---:|---:|']
    for c in audit['comparisons']:
        scene=c['scene'];lines.append(f"| {scene} | {c['hough_minus_baseline_assigned']} | {by[(scene,'baseline')]['primary_cross_parent_links']} / {by[(scene,'hough')]['primary_cross_parent_links']} |")
    lines += ['', 'METRICS.json 的 accepted_cross_parent_links 还包括不足最小组长度、最后仍为 UNKNOWN 的短链；上表使用独立审计中实际导出主分组内的连接，避免夸大交付。','',
    '视觉检查没有在所查最大组中发现整个物体被并为巨团，但这不等于整体正确。scan24 最大组仍是单 parent；最大跨 parent 组仅为短局部边。ficus 最大几条彩色线在全景中伸出植株外，原始几何完全保留，不能作为真实叶缘成功证据。scan65 有弯曲局部轨迹，但最大跨 parent 组主要由单 parent 贡献。全体核中的多数仍为 UNKNOWN。','',
    '以下全景每张都渲染完整资产；六个最大组着色，其余核（包括 UNKNOWN 和未突出显示的已分配组）为灰色。灰色不是 UNKNOWN 专用掩码。颜色只在同一方法、同一场景的固定相机间共享；不同方法颜色相同不证明身份相同。','']
    for scene in ['scan24','ficus','scan65']:
        lines += [f'**{scene}**', '', f'[全量基线/Hough两视图比较]({scene}/FULL_COMPARISON.png) · [最大组隔离图]({scene}/hough/ISOLATED_PANEL.png) · [最大跨parent组隔离图](diagnostics/{scene}/hough/CROSS_PARENT_ISOLATED_PANEL.png) · [parent来源着色](diagnostics/{scene}/hough/PARENT_PROVENANCE_PANEL.png) · [拒绝/歧义案例](diagnostics/{scene}/hough/NEGATIVE_PANEL.png)', '',f'![{scene} full Gaussian comparison]({scene}/FULL_COMPARISON.png)','']
    lines += ['冻结规则由 [DECISION.json](DECISION.json)、[CONFIG.json](CONFIG.json) 和 [CAMERAS.json](CAMERAS.json) 给出。实际导数来自 control/control_index/derivative_basis；seedlet最多6核、跨度2p。全局32邻居/4p候选，共同1.5p间隙、30°切向、35°连接角、15%歧义、度数2、8p内90°转角与20000代表上限。跨 parent 和跨块候选经过同一门槛，长间隙仅保留为暂定拒绝候选，不进入主分组，也没有绘制填缝几何。','',
    '四个实际回归用例先RED后GREEN：碎片直线与parent标签置换、渐弯链、近平行边、X/T交叉。不是800例合成活动。六份真实输出另做独立冷读审计：完整行数/原始行序、每核唯一主身份或UNKNOWN、每个已分配组连通且ID等于最小核行号、来源映射、间隙/角度/度数/转角/规模界限全部通过。原始NPZ的非颜色字段及扩展PLY所有原始字段逐字节相同；显示PLY只改DC颜色；冷载显示NPZ重渲染与保存PNG逐字节一致。本次读取的输入锁定文件和渲染helper哈希保持不变（未打开源场景GS）。','',
    '实际三个场景子进程耗时约54、24、25秒，真实退出码均为0；完整运行早于原管理截止时间。初始实现与冻结阶段约10分44秒，超过预估7分钟，但未改变整体35分钟上限、场景次序或科学设置。CPU/BLAS最多2、严格串行；输出约0.62GiB。没有读取源场景高斯、GPU、训练、安装、额外代理或推送。','',
    '主要文件：每场景各方法的 MEMBERSHIP.npz、GROUPS.json、LINKS.npz、CHAINS.npz、EXTENDED.ply、DISPLAY.ply、DISPLAY_GAUSSIANS.npz、GEOMETRY_AUDIT.json；每场景 REPRESENTATIVES.npz、HOUGH_FAMILIES.npz、SOURCE_HASHES_BEFORE/AFTER.json。diagnostics 中含独立几何与身份审计、显式 JUNCTION_ALTERNATIVES.npz、跨parent完整图和原生高斯裁剪放大图。[MEMBERSHIP_SCHEMA.json](MEMBERSHIP_SCHEMA.json) 定义原因码，score只是几何评分，不是概率。','',
    '所有旧文件、原始资产和失败RED回执保留。各场景 CHILD_START/CHILD_EXIT、RUN_START/RUN_EXIT 记录真实状态；没有把启动器退出当作计算成功。每个方法及诊断目录有文件哈希封存。无第二次调参；本次试验到此停止。失败仅说明这组冻结规则对这三份噪声融合资产的广泛归并效果不足，不构成普遍不可能性结论。','']
    with (OUT/'REPORT_ZH.md').open('x') as f:f.write('\n'.join(lines))
    js(OUT/'VALIDATION.json',dict(utc=now(),all_sealed_file_hashes_passed=True,sealed_files_checked=checked,all_frozen_code_and_helpers_unchanged=True,all_source_hashes_passed=True,all_scenes_complete=True,RED_nonzero_GREEN_zero=True,independent_six_method_audits_passed=True,physical_accuracy_not_claimed=True))
    js(OUT/'CODE_MANIFEST.json',{str(f):sha(f) for f in sorted(CODE.iterdir()) if f.is_file()})
    js(OUT/'DELIVERABLES.json',dict(report=str(OUT/'REPORT_ZH.md'),summary=str(OUT/'SUMMARY.json'),scenes={s:{m:dict(membership=str(OUT/s/m/'MEMBERSHIP.npz'),canonical_extended_PLY=str(OUT/s/m/'EXTENDED.ply'),colored_Gaussians=str(OUT/s/m/'DISPLAY_GAUSSIANS.npz'),colored_PLY=str(OUT/s/m/'DISPLAY.ply'),full_comparison=str(OUT/s/'FULL_COMPARISON.png'),largest_isolated=str(OUT/s/m/'ISOLATED_PANEL.png'),cross_parent_isolated=str(OUT/'diagnostics'/s/m/'CROSS_PARENT_ISOLATED_PANEL.png')) for m in ['baseline','hough']} for s in ['scan24','ficus','scan65']}))
    print(json.dumps(summary,ensure_ascii=False,indent=2),flush=True)
if __name__=='__main__':main()
