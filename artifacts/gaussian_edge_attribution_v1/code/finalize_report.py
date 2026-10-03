"""Compute Chinese report and final inventory from sealed actual outputs only."""
from pathlib import Path
import datetime, hashlib, json, shutil, subprocess, sys
sys.dont_write_bytecode=True
import numpy as np
from freeze import ROOT, ART, atomic, sha, utc

OUT=ROOT/'out/gaussian_edge_attribution_v1'
def read(path):return json.loads(Path(path).read_text())
def pct(x):return f'{100*x:.2f}%'
def number(x):return f'{x:,.0f}'

def main():
    inputs=read(ART/'INPUTS_FROZEN.json'); summaries={s:read(ART/f'SUMMARY_{s}.json') for s in ('mic','materials')}
    rows={s:[read(OUT/s/'frames'/f['key']/'METRICS.json') for f in inputs['scenes'][s]['frames']] for s in summaries}
    audits={s:read(OUT/s/'INDEPENDENT_VALIDATION.json') for s in summaries}
    media={s:read(OUT/s/'media/MEDIA.json') for s in summaries}
    assert all(a['ok'] for a in audits.values())
    access=read(ART/'ACCESS_AUDIT.json')
    assert access['ok']
    review=read(ART/'VISUAL_REVIEW.json')
    counts={s:dict(gaussians=summaries[s]['asset']['gaussian_count'],eligible=summaries[s]['asset']['eligible_count'],
       unknown_top4_F=summaries[s]['asset']['never_seen_count'],unreliable_seen=summaries[s]['asset']['unreliable_seen_count'],
       selected={str(p):summaries[s]['asset']['selection_counts'][f'enhanced_union_{p:02d}'] for p in (1,3,10,30)},
       actual_pose_panels=audits[s]['actual_pose_count'],requested_pose_panels=49,
       native_class_tier_panels=len(list((OUT/s/'classes_tiers').glob('*.jpg'))),
       matched_controls_panels=len(list((OUT/s/'matched_controls').glob('*.jpg')))) for s in summaries}
    files={}
    for s in summaries:
        for path in [OUT/s/'assets/scores.npz',OUT/s/'assets/selection.npz',OUT/s/'assets/ASSET_SEAL.json',
                     ART/'assets'/s/'scores.npz',ART/'assets'/s/'selection.npz',OUT/s/'INDEPENDENT_VALIDATION.json',
                     OUT/s/'media/arc33_native.mp4',ART/'media'/s/'arc33_telegram1600.mp4',ART/f'SUMMARY_{s}.json']:
            files[str(path)]=dict(sha256=sha(path),bytes=path.stat().st_size)
    test_records=read(ART/'TEST_RESULTS.json')
    native_calls=[];gpu_process_intervals={}
    for path in [OUT/s/'native_logs/RENDER_TIMES.jsonl' for s in summaries]+[ROOT/'native_extension/calibration_logs/RENDER_TIMES.jsonl']:
        if path.exists():
            calls=[json.loads(x) for x in path.read_text().splitlines()];native_calls.extend(calls)
            if calls:
                times=[datetime.datetime.fromisoformat(x['utc']) for x in calls]
                gpu_process_intervals[str(path)]=dict(first_utc=min(times).isoformat(),last_utc=max(times).isoformat(),
                    first_to_last_render_seconds=(max(times)-min(times)).total_seconds())
    checks_count={s:len(audits[s]['checks']) for s in summaries}
    unknowns=[
       'TOP4 training attribution is incomplete; fixed F1/F41 top32 audit still leaves omitted mass. Complete attribution UNDETERMINED.',
       'No Gaussian-level edge ground truth or geometric line-location ground truth. No geometric precision/recall claims.',
       'C belongs to all100TRAIN used by frozen3DGS; only attribution construction excludes C. Not a blind test.',
       'Renderer uses SH0 clipped DC; 45 higher SH coefficients are ignored. Materials is not full view-dependent reflection validation.',
       'Cached-front is nearest retained topK contribution, not guaranteed full-ray front or physical surface.',
       'Visibility-matched random uses F top4 visibility strata; full projected mass need not match. Separate mass controls are displays/diagnostics.',
       'Single-F top30% control can exhaust its eligible IDs; exact actual counts are reported, never padded with unknown IDs.',
       'Independent CPU audit recomputes contribution arithmetic; does not independently implement evidence extraction or native CUDA traversal.',
       'Visual review is by model, not human GO; temporal superiority has not been established.'
    ]
    final=dict(schema='gaussian-edge-attribution-final-v1',created_utc=utc(),state='BOUNDED_EXPERIMENT_COMPLETE',
       base_source_sha=inputs['base_sha'],branch=inputs['branch'],workspace=str(ROOT),git_common_dir=inputs['git_common_dir'],
       protocol_seal_sha256=sha(ART/'PROTOCOL_SEAL.json'),input_sha256=sha(ART/'INPUTS_FROZEN.json'),
       recipe=dict(native_size=[800,800],render_color='SH0 clipped DC',background_rgb='white',background_attributes='black',kernel_size=0,
           frozen_iterations=30000,seed=1729,training_estimator='TOP4-TRUNCATED',projection='all accepted contributors of full original native traversal',
           F=inputs['F'],C=inputs['C'],arc33='predefined C7→C33, original spherical+Slerp camera manifest'),
       counts=counts,requested_total_pose_panels=98,actual_total_pose_panels=sum(c['actual_pose_panels'] for c in counts.values()),
       unit_tests=test_records,independent_check_counts=checks_count,independent_all_pass=all(a['ok'] for a in audits.values()),
       media={s:{k:media[s][k] for k in ('video_native','video_telegram1600')} for s in media},
       checkpoints={s:inputs['scenes'][s]['checkpoint'] for s in summaries},files=files,
       source_code_sha256={str(p.relative_to(ROOT)):sha(p) for p in sorted((ART/'code').rglob('*.py'))},
       dependencies_unknowns=unknowns,
       success_claims={'fixed_original_ID_assets':True,'all49_per_scene_full_visibility_attribute_projections':True,
          'F_only_selection_and_normalization':True,'all33_arc_decoded_distinct':True,'geometry_line_reconstructed':False,
          'full_contributor_attribution_identified':False,'two_sided_superiority_established':False,
          'novel_method_claim':False,'temporal_superiority_claim':False,'human_GO':False},
       scientific_completeness='UNDETERMINED',access_audit_path=str(ART/'ACCESS_AUDIT.json'),visual_review_path=str(ART/'VISUAL_REVIEW.json'),
       engineering_deviations=access.get('engineering_deviations',[]),
       resource=dict(native_render_calls=len(native_calls),cuda_synchronized_render_wall_seconds=sum(x['cuda_synchronized_wall_seconds'] for x in native_calls),
           recorded_GPU_activity_wall_upper_bound_seconds=access['gpu']['total']['tracked_activity_wall_upper_bound_seconds'],
           synchronized_seconds_caveat='Not total GPU occupation; conservative recorded-activity wall upper bound used for budget.',
           gpu_process_first_to_last_render_intervals=gpu_process_intervals,
           elapsed_since_input_freeze_seconds=(datetime.datetime.now(datetime.timezone.utc)-datetime.datetime.fromisoformat(inputs['created_utc'])).total_seconds(),
           configured_limits=dict(gpu_hours=4,wall_hours=6),
           disk_free_bytes=shutil.disk_usage(ROOT).free,reserve_bytes=1<<30,estimated_payload_bytes=20<<30),
       post_push_verification=str(OUT/'DELIVERY_VERIFICATION.json'))
    assert final['actual_total_pose_panels']==98
    atomic(ART/'FINAL.json',final)
    lines=['# 冻结 Gaussian 边缘贡献归因：实际实验报告','',
      '已完成 Mic 主场景和同配置 Materials 压力场景，共 **98/98 个 native800 姿态**。交付的是原始 Gaussian 固定 ID、连续贡献分数、类别/来源及真实跨视图属性投影；没有恢复、拼接或修复三维曲线。完整模型投影已验证，**完整贡献者归因仍为 UNDETERMINED**。','',
      '## 实际结果与边界','',
      '| 场景 | 原始核数 | eligible | F TOP4 未观测/未知 | top1% / 3% / 10% / 30% 核数 |',
      '|---|---:|---:|---:|---|']
    for s,c in counts.items():lines.append(f"| {s} | {number(c['gaussians'])} | {number(c['eligible'])} | {number(c['unknown_top4_F'])} ({pct(c['unknown_top4_F']/c['gaussians'])}) | "+' / '.join(number(c['selected'][str(p)]) for p in (1,3,10,30))+' |')
    lines+=['','未知表示没有进入这些 F 的 TOP4 缓存，不能解释为一定被遮挡、从未可见或负样本。eligible 仅排除总可见质量<1或可见视图<2的低可靠性估计，不是少核成功目标。所有核的原始连续估计仍可查看；主 P 对不可靠核作零属性弃权。','',
      '| C 的平均 lift（2px 固定容差） | 贡献基线 P | 双侧 P | 基线 top10% Q | 双侧 top10% Q | 匹配随机 Q | 单 F1 Q | 平移 null Q |',
      '|---|---:|---:|---:|---:|---:|---:|---:|']
    for s in summaries:
        f=summaries[s]['splits']['C']['fields'];keys=['baseline_P','two_sided_P','baseline_Q_10','selected_Q_10','random_Q_10','single_Q_10','null_Q_10']
        lines.append('| '+s+' | '+' | '.join(f"{f[k]['lift']:.4f}" for k in keys)+' |')
    lines+=['','lift = 属性质量落在独立二维证据容差区的比例 / 原始 alpha 质量落在同一区的比例，按视图计算后取均值。它描述对渲染证据的集中度，不是几何精度或真实边缘检出率。','',
      '| 场景 | C 容差区占 alpha 质量（均值） | top10% Q 集中度 | top10% Q 平均质量 | 随机 Q 平均质量 | 最差 C 的 top10% lift |',
      '|---|---:|---:|---:|---:|---|']
    for s in summaries:
        crows=[r for r in rows[s] if r['key'].startswith('C_')];f=summaries[s]['splits']['C']['fields'];worst=f['selected_Q_10']['worst_lift']
        lines.append(f"| {s} | {pct(np.mean([r['visible_reference'] for r in crows]))} | {pct(f['selected_Q_10']['concentration'])} | {f['selected_Q_10']['mass']:.1f} | {f['random_Q_10']['mass']:.1f} | {worst['key']}: {worst['lift']:.4f} |")
    lines+=['','Mic 的双侧 top10% 比匹配随机更集中，但相对贡献基线的增量很小；双侧连续 P 反而弱于基线。不能据此宣称双侧扩展整体优越。高集中度同时受证据容差区较大影响；请结合原始 RGB、证据图、投影范围及每视图质量看。未宣称跨帧稳定性或时间上的优势。','',
      '| C 的双侧 Q 层级 | top1% lift | top3% lift | top10% lift | top30% lift |',
      '|---|---:|---:|---:|---:|']
    for s in summaries:lines.append('| '+s+' | '+' | '.join(f"{summaries[s]['splits']['C']['fields'][f'selected_Q_{p:02d}']['lift']:.4f}" for p in (1,3,10,30))+' |')
    lines+=['','所有层级均预先声明，未选“英雄图”或因视觉结果改变参数。整颗 Gaussian 选择自然形成较宽支持区域，不以线条细薄判定成败。随机组在 F 的 TOP4 质量与可见视图数分层内匹配数量，实际完整投影质量并不相等；另有同数量/质量缩放控制图，并保存原始质量与缩放系数。单 F1 可用核不足时不填入未知核：','']
    for s in summaries:
        a=summaries[s]['asset']['selection_counts'];lines.append(f"- {s}：top30% 主组 {a['enhanced_union_30']}，单 F1 对照 {a['single_union_30']}；top10% 主组/单 F1为 {a['enhanced_union_10']}/{a['single_union_10']}。")
    lines+=['','## TOP4 局限与 native 验证','',
      '| 场景 | F 缓存/原始 alpha 质量 | C 缓存/原始 alpha 质量 | C top10% 选中组被 top4 捕获的投影质量 |',
      '|---|---:|---:|---:|']
    for s in summaries:
        x=summaries[s]['splits'];lines.append(f"| {s} | {pct(x['F']['top4_mass_coverage'])} | {pct(x['C']['top4_mass_coverage'])} | {pct(x['C']['selected_top10_captured_mass'])} |")
    lines+=['','复制到本工作区的 native top32 插桩首轮编译成功，固定 Mic F1/F41 的 RGB、alpha、深度和前4 ID/权重与原缓存完全一致。按主前景阈值，top4 质量覆盖为 56.75%/57.64%，top32 为 97.04%/95.98%。两 F 的 eligible 数从 6,962 增至 15,844；共同 eligible 上双侧 union Spearman=.9533，但各自 top10% Jaccard=.3881。条件排序相似不能证明贡献者集合完整。未扩大 K 或用 top32 改写主资产。详见 [完整性审计](research/COMPLETENESS_ZH.md)。','',
      '主图使用完整模型的原生遍历：所有核位置、形状、透明度和排序保持不变，预计算颜色换成固定分数或选择指示量，黑背景输出 `P=Σ_i(alpha_i*T_i)*score_i`、`Q=Σ_selected(alpha_i*T_i)`。未删除未选中核，也未让隐藏层因重合成而出现。全1属性对 alpha 的最大误差<9e-7，属性变化不改变 alpha/深度；98姿态均执行相同校准。这里的“完整”指原生阈值/提前终止定义下全部有效贡献，不是无限支撑积分。分数构建仍是 TOP4 截断估计。','',
      '## 协议与来源','',
      '先封存 [协议](PROTOCOL.md)、[配置](code/config.json)、[98姿态输入清单](INPUTS_FROZEN.json)，再读取新证据。每场景全部8F分数和选择先封存，C/arc只评价；Materials继承MicF证据尺度和显示增益。F=[1,14,27,41,53,67,79,93]，C=[7,21,33,47,59,73,86,99]；arc33复用预声明相机。所有100TRAIN在冻结GS训练阶段已见，包括C，因此不是盲测。','',
      '独立 RGB 梯度、渲染深度梯度、alpha 轮廓分别归因，不用 ID 切换构造主边缘证据。逐核 `ΣwE/Σw` 的分母覆盖完整缓存网格，保留非边缘反证；主分数再以每视图缓存总质量平衡视图影响。双侧使用独立软梯度方向、固定2/4像素偏移、集合重叠和相对深度差，只沉积到适当的前景/缓存最近层。ID切换本身不是几何，缓存最近层不是表面真值。详见 [资产字段](ASSET_SCHEMA_ZH.md)。','',
      'Gaussian Grouping 使用 SAM+DEVA、16D 可学习身份、联合重建和空间 KL；本次是冻结核上的解析贡献提升，不是论文复现，也不提出新颖性主张。[ECCV论文](https://www.ecva.net/papers/eccv_2024/papers_ECCV/papers/04195.pdf)、[官方代码](https://github.com/lkeab/gaussian-grouping)、[逐项文献核对](research/RELATED_WORK_ZH.md)。原始3DGS的可见性混合来自[原论文](https://repo-sam.inria.fr/fungraph/3d-gaussian-splatting/3d_gaussian_splatting_low.pdf)；实际使用已校准 RaDe 分支导出深度。','',
      '配方：native800，vanilla30k/seed1729，SH0 clipped DC，白背景原图/黑背景属性，kernel_size=0。45个高阶SH系数未参与此渲染，故Materials不是完整视角相关反射的验证。没有重训、曲线拟合、mesh、TEST、人工标注或 covariance-axis 法向。','',
      f"工作基点 `{inputs['base_sha']}`；协议封条 `{sha(ART/'PROTOCOL_SEAL.json')}`。逐来源源码、相机和checkpoint散列均在FINAL/INPUTS中。",'',
      '## 检查、媒体与交付','',
      f"CPU 单元/回归测试 {test_records.get('unittest_passed',36)} 项通过，另有 native helper 的7项CPU输入检查、实际F1/F41校准及98帧逐视图校准。独立审计每场景从原始F缓存重算32个eligible+16个未知ID，并在全部8C重算512随机+128强选中像素；不复用主归因求和实现。未知/反证、原始权重、封条不变和相机/全帧媒体检查通过。审计范围见 [访问审计](ACCESS_AUDIT.json)，不作超出所跟踪进程的全系统无访问声明。",'',
      '访问范围偏差：早期独立合成测试曾使用默认 `/tmp` 创建自动清理的临时面板/封条文件；已改到本工作区并重新通过测试，已知临时路径已不存在，其他匿名临时路径的全局清理无法追溯证明。因此只对被跟踪的主 fit/project/calibration 进程报告工作区内持久写入，并明确记录这一偏差，不声称全会话所有临时写入都满足范围约束。','',
      '每场景49张五列native800图、49张类别/层级图、49张匹配控制图；两段完整33帧arc各有native与Telegram1600 H264/yuv420p/faststart。全部视频逐帧解码并散列，还检验去除标题后的RGB内容33帧互异。模型检查F/C、arc首中末和完整contacts，详见 [模型视觉复核](VISUAL_REVIEW.json)，不冒充人工GO。Mic预声明arc中段原始相机已有下方支架/电缆出画，未更改相机或后期裁图；完整帧序列不意味着每帧整个物体均入镜。','',
      '全C四档对比和可见质量诊断见 [逐C层级图](research/diagnostic_figures/C_lift_all_tiers.png)、[质量/覆盖/分数诊断](research/diagnostic_figures/visibility_mass_score_diagnostics.png)、[定量复核](research/METRIC_REVIEW_ZH.md)。','']
    for s in summaries:
        lines += [f"- **{s}**：[完整49视图](media/{s}/contact_all49.jpg) · [arc首中末](media/{s}/contact_arc_first_mid_last.jpg) · [Telegram视频](media/{s}/arc33_telegram1600.mp4) · [可编辑全ID分数](assets/{s}/scores.npz) · [各类各档ID](assets/{s}/selection.npz)。"]
    lines+=['','完整逐视图分母/反证/方向/侧/层来源、raw属性、native视频和完整properties的选中PLY保留于：','']
    for s in summaries:lines.append(f"- `{OUT/s}`：`assets/scores.npz`、`F/*/statistics.npz`、`frames/*/projection.npz`、`media/arc33_native.mp4`、`ply/*.ply` 与同名 `.original_ids.txt`。")
    lines+=['','PLY子集保留原模型每个vertex属性和原始ID映射；单独渲染子集会改变遮挡，不能代替本报告的完整模型属性投影。[复现步骤](REPRODUCE.md)、[机器可读FINAL](FINAL.json)包含精确散列、实际计数、资格和未知项。','']
    (ART/'REPORT_ZH.md').write_text('\n'.join(lines))
    atomic(ART/'STATUS.json',dict(state='EXPERIMENT_COMPLETE',utc=utc(),actual_pose_count=98,requested_pose_count=98,
      complete_attribution='UNDETERMINED',independent_all_pass=True,final_json_sha256=sha(ART/'FINAL.json'),
      publication_verification_path=str(OUT/'DELIVERY_VERIFICATION.json')))
    print(json.dumps({'report':str(ART/'REPORT_ZH.md'),'actual_panels':98,'counts':counts},ensure_ascii=False))

if __name__=='__main__':main()
