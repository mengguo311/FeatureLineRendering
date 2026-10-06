import json
from runtime import ROOT,EXP,ART,OUT,OLD,NATIVE,sha,atomic_json,source_hashes
from evaluation import decide_gates

def update(freeze,results,complete=False):
    synth=results.get('synthetic',{})
    scene_results={}
    engineering=[]
    for name,r in results.items():
        if r.get('status')=='ENGINEERING_NOT_READY':engineering.append(name)
    for scene in ['lego','chair']:
        scores=results.get(scene+'_scores',{});val=results.get(scene+'_independent',{});media=results.get(scene+'_media',{})
        cal=results.get(scene+'_calibration',{})
        views=freeze['scenes'][scene]['views']
        classes={k:sum(v['reference']['metadata']['classes'].get(k,0) for v in views if v['entry']['role']=='edit-train') for k in ['outline','clear_color_transition','texture_detail_certified']}
        gates=decide_gates([synth.get('gate1_pass',False) and cal.get('pass',False) and scores.get('identity_pass',False),
                            val.get('gate2_numeric_advantage_pass',False),val.get('gate3_pass',False)])
        scene_results[scene]=dict(model_sha256=freeze['scenes'][scene]['model_sha256'],gaussian_count=freeze['scenes'][scene]['gaussian_count'],
              frozen_train_samples=classes,internal_semantics='UNCERTIFIED_NO_HUMAN_LABELS',
              evidence_only_ablation=scores.get('evidence_only_ablation'),weighting_only_ablation=scores.get('segment_equal_vs_arclength_ablation'),
              fixed_evidence_rank_reference=scores.get('fixed_evidence_ranking_reference'),independent_group_comparison=val.get('methods'),
              independent_response_advantage=val.get('paired_response_vs_best_simple_null'),
              score_response_spearman=val.get('construction_score_independent_response_spearman'),
              gates=gates,gate3_reason=val.get('gate3_reason','not reached'),accepted_diagnostic_count=len(val.get('accepted_rows',[])),
              media=media,calibration=cal,optimization='NOT_RUN',optimization_reason='all three independent gates required; human visual GO pending',
              selection_search_seconds=scores.get('selection_search_seconds'),validation_seconds=val.get('validation_seconds'),
              original_TEST_RGB_read=False,holdout='exploratory original TRAIN, GS-seen and previously used; not formal blind TEST')
    protected=None
    if complete:
        changed=[p for p,h in freeze['protected_sha256'].items() if sha(p)!=h]
        protected=dict(files_checked=len(freeze['protected_sha256']),changed_paths=changed,all_byte_identical=not changed,
                       old_models_sha256_after={s:sha(v['model']) for s,v in freeze['scenes'].items()},
                       source_hashes_unchanged=source_hashes()==freeze['source_hashes'])
        if changed or not protected['source_hashes_unchanged']:engineering.append('protected/source hashes')
    if synth and not synth.get('gate1_pass',False):engineering.append('synthetic_validation')
    status='RUNNING' if not complete else 'ENGINEERING_NOT_READY' if engineering else 'VALIDATION_GATES_NOT_PASSED'
    final=dict(status=status,execution_complete=complete,request_commit=freeze['request_commit'],
               input_freeze_sha256=sha(ART/'INPUT_FREEZE.json'),source_provenance=freeze['source_hashes'],
               synthetic=dict(native_frames=synth.get('frames',0),gate1_pass=synth.get('gate1_pass',False),
                              presence_passes=sum(r['presence_absence_pass'] for r in synth.get('records',[])),
                              signed_identity_passes=sum(r['native_identity_pass'] for r in synth.get('records',[])),
                              extras=synth.get('extras',[])),scenes=scene_results,engineering_not_ready_units=engineering,
               protected_inputs=protected,completed_units=list(results),human_visual_GO='PENDING',
               semantic_internal_certification='UNAVAILABLE',no_physical_contact_or_new_algorithm_advantage_claim=True,
               optimization_status='NOT_RUN',resume='experiments/edge_responsibility_lego_chair_v2/scripts/launch.py',
               plan_scope='bounded scoring validation, full-native diagnostics both scenes; downstream gated',
               result_paths={k:str((ART/'results'/f'{k}.json').relative_to(ROOT)) for k in results},
               remaining=['independent human inspection of evidence classes and selected native kernels',
                          'certify cross-view locality and boundary interpretation',
                          'satisfy response superiority gate before any 336-step paired local optimization'])
    atomic_json(ART/'FINAL.json',final)
    lines=['# Lego / Chair 边缘责任评分实际验证', '',
           f'状态：`{status}`。执行完成：`{complete}`。后续局部优化：`NOT_RUN`。', '',
           '本轮首先验证评分，未用下游修复代替评分验证。旧评分是相对位置支持代理；有符号变化记账与具体操作作用分开记录。真实内部目标仅为自动质量确认的颜色过渡，未认证几何、材质、纹理或物理接触语义。', '',
           f'原生合成验证：{synth.get("frames",0)} 帧；存在/缺失检查通过 {sum(r["presence_absence_pass"] for r in synth.get("records",[]))}；带背景项的有符号恒等式通过 {sum(r["native_identity_pass"] for r in synth.get("records",[]))}。构造真值在评分前冻结，未从梯度或评分推导标签。', '',
           'CPU 回归先在未修改的 v1 接口上 RED（拒绝条纹剖面仍进入主证据），在新接口上 GREEN。初次语法失败和原生失败也保留；日志位于 logs 和 failures。', '',
           '## 实际场景', '']
    for scene,r in scene_results.items():
        lines.extend([f'### {scene}', '',f'完整 SH3，{r["gaussian_count"]} 核，源 SHA256 `{r["model_sha256"]}`。',
                      f'八个 edit-train 视角冻结目标：{r["frozen_train_samples"]}。三个门槛：{r["gates"]["gates"]}。诊断接受核数：{r["accepted_diagnostic_count"]}。', ''])
        if r['evidence_only_ablation']:
            lines.extend(['固定旧评分、等片段权重的证据替换消融（核数相同；2px/4px 评价带独立固定）：', '',
                          '| 证据 | 核数 | 2px 贡献召回 | 4px 贡献召回 | 2px 选中质量集中度 |',
                          '| --- | ---: | ---: | ---: | ---: |'])
            for method,metric in r['evidence_only_ablation'].items():
                lines.append(f'| {method} | {metric["count"]} | {metric["narrow2_recall"]:.6f} | {metric["narrow4_recall"]:.6f} | {metric["narrow2_selected_mass_concentration"]:.6f} |')
            lines.append('')
        if r['independent_group_comparison']:
            lines.extend(['固定可信证据、每群相同核数，独立新方向/幅度验证：', '',
                          '| 方法 | 目标群 | 独立局部作用均值 | 局部代价通过率 | 诊断接受群 |',
                          '| --- | ---: | ---: | ---: | ---: |'])
            for method,metric in r['independent_group_comparison'].items():
                lines.append(f'| {method} | {metric["groups"]} | {metric["mean_independent_quality"]:.8f} | {metric["independent_locality_pass_rate"]:.4f} | {metric["accepted_groups"]} |')
            lines.extend(['',f'受约束响应与简单贡献/匹配随机中较好对照的配对差异：`{r["independent_response_advantage"]}`。',
                          f'构造分数与独立响应的 Spearman：`{r["score_response_spearman"]}`。候选群搜索和三个尺度轴探针的计算成本单列，响应法每目标搜索4个候选，不能称其免费。', ''])
        for sheet in r['media'].get('sheets',[]):lines.append(f'- [新原生渲染对比 {sheet.split("/")[-2]}](../../{sheet})')
        lines.extend(['',f'门槛3：{r["gate3_reason"]}。', ''])
    lines.extend(['## 约束与可复核文件','',
                  '每个核群记录有符号/绝对归因、抵消、完整法向剖面有限差分、平台与平坦区域成本、非目标区域成本、alpha孔洞与轮廓变化、独立扰动预测和跨视角同UID操作。主评分从原生颜色反向获取权重，完整SH3按原生方向和 clamp_min 求值；背景ΔT和总权重恒等式均检查。EOTF只对完整渲染应用。', '',
                  '选中贡献图保留完整模型的遮挡遍历，未选核特征置零。子集图实际移除未选核，使用原始完整SH3色，只能视为无原遮挡的诊断。正负差分采用统一20倍显示增益，原图与float32差分同相机保存。top10%仅是等预算排名参考，诊断接受集合可为空。', '',
                  '八个edit-train用于构造，四个dev用于数值校准和噪声/绝对门槛报告，四个此前GS训练见过的edit-holdout用于探索性跨视角检查；未打开原始TEST RGB。没有人工标签、部件标注、物理接触或正式盲测优势声明。', '',
                  '三项门槛全部通过前，不执行336步color/cov优化和普通同权限对照；此次优化保持NOT_RUN。', '',
                  f'保护输入核验：`{protected}`。', '',
                  '- [最终机器记录](FINAL.json)', '- [冻结输入与源](INPUT_FREEZE.json)', '- [源映射](SOURCE_MAP.json)',
                  '- [复现](REPRODUCE.md)', '- [24帧原生合成图](media/synthetic_24.png)', ''])
    (ART/'REPORT_ZH.md').write_text('\n'.join(lines))
    return final
