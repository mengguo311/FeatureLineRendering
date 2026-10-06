"""Curate actual results without changing frozen scientific gates or old evidence."""
import json,sys,collections
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'experiments/edge_responsibility_lego_chair_v2/src'))
from runtime import ART,OUT,sha,atomic_json
from evidence import profile_vector

def main():
    frozen=json.loads((ART/'INPUT_FREEZE.json').read_text())
    final=json.loads((ART/'FINAL.json').read_text())
    if not (ART/'MAIN_EXECUTION_FINAL.json').exists():atomic_json(ART/'MAIN_EXECUTION_FINAL.json',final)
    audit=json.loads((ART/'INDEPENDENT_ENGINEERING_AUDIT.json').read_text())
    timing=json.loads((ART/'GROUP_TIME_COST.json').read_text())
    synth=json.loads((ART/'results/synthetic_kernel_score_appendix.json').read_text())
    final['supplemental_results']=dict(native_synthetic_kernel_score_frames=synth['frames'],
         paths=['results/synthetic_kernel_score_appendix.json','results/lego_localization_appendix.json','results/chair_localization_appendix.json'],
         additional_native_constructs=[dict(id=r['construct']['id'],construct_property_pass=r['pass_all'],cancellation=r['signed']['cancellation'],
                parameter_derivatives=r['parameter_derivatives']) for r in synth['additional_native_fixtures']],
         original_gate_failures_retained=True,
         synthetic_acceptance_labels='construct target policy/negative class, not proof of a learned classifier or causal method advantage',
         synthetic_right_side_control_ROI='fixed comparison ROI; in stripe condition it contains legitimate detail and is not certified flat')
    final['independent_engineering_checks']=dict(status=audit['status'],count=len(audit['checks']),
         path='INDEPENDENT_ENGINEERING_AUDIT.json',does_not_certify_scientific_gates=True)
    final['real_group_cost']=dict(atomic_group_units=timing['group_units'],native_forwards=timing['native_forwards_in_real_group_units'],
         path='GROUP_TIME_COST.json',time_precision='actual resource timestamps and completion seconds; intervals reported',search_candidates_per_target=4)
    final['failure_cases_path']='FAILURE_CASES.json'
    final['remaining']=['three frozen high-contrast localization failures and initial partially hidden fixture block gate1',
                        'additional cancellation fixture has unstable log-scale finite branches; do not treat local gradient as general predictor',
                        'independent response advantage CI lower bound equals zero in both scenes; gate2 not passed',
                        'human visual GO, semantic internal certification and cross-view boundary interpretation remain pending',
                        'missing matched flat ROI in several views means flat_rms=0 there is undefined, not zero observed cost',
                        '336-step paired color/cov local optimization remains NOT_RUN until all gates pass independently']
    ringing=[]
    for scene in ['lego','chair']:
        val=json.loads((ART/'results'/f'{scene}_independent.json').read_text())
        scores=json.loads((ART/'results'/f'{scene}_scores.json').read_text())
        loc=json.loads((ART/'results'/f'{scene}_localization_appendix.json').read_text())
        final['scenes'][scene]['missing_matched_flat_ROI_views']=audit['missing_flat_ROI_views'][scene]
        final['scenes'][scene]['flat_zero_cost_convention']='undefined when flat ROI mask is empty; do not use as evidence of zero cost'
        final['scenes'][scene]['flat_negative_rejection']=loc['flat_negative_rejection']
        final['scenes'][scene]['selected_kernel_interpretation']='local diagnostic candidates; subset surface blobs and gaps retained; no certified edge asset'
        final['scenes'][scene]['localization_appendix']=f'results/{scene}_localization_appendix.json'
        for g in val['groups']:
            s=g['sample']
            with np.load(ROOT/scores['cache'][g['view_key']]['baseline_path']) as z:b0=z['rgb'].astype(float)
            p0=profile_vector(b0,s,False)
            ref=np.array(s.get('reference_native_profile',p0))
            lo=ref[:10].mean(0);hi=ref[-10:].mean(0);delta=hi-lo;norm=float(np.linalg.norm(delta))
            if norm<.01:
                ringing.append(dict(group=g['id'],status='low_contrast_no_reliable_RGB_ringing_direction'));continue
            u=delta/norm
            def measure(p):
                q=(p-lo)@u/norm
                return dict(projected_range_overshoot=float(max(0,-q.min(),q.max()-1)),
                            reverse_variation=float(np.maximum(-np.diff(q),0).sum()),
                            encoding='native full-render RGB normal profile, fixed reference endpoint direction and contrast')
            before=measure(p0)
            for param,r in g['independent_probes'].items():
                ringing.append(dict(group=g['id'],param=param,status='measured',before=before,
                      after={sign:measure(p0+np.array(dp)) for sign,dp in r['native_profile_deltas'].items()}))
    atomic_json(ART/'RINGING_APPENDIX.json',dict(records=ringing,
             replaces_interpretation_not_bytes_of_original_metric=True,
             original_ringing_overshoot_field_is_RGB_range_change_proxy=True,
             full_profile_vectors_are_actual_render_outputs=True))
    final['ringing_metric_appendix']='RINGING_APPENDIX.json'
    atomic_json(ART/'FINAL.json',final)
    source=json.loads((ART/'SOURCE_MAP.json').read_text())
    source['appendix_runners']={str(p.relative_to(ROOT)):sha(p) for p in sorted(ART.glob('*.py'))}
    source['appendices_do_not_modify_frozen_production_sources']=True
    atomic_json(ART/'SOURCE_MAP.json',source)
    report=ART/'REPORT_ZH.md';base=report.read_text().split('<!-- CURATED_APPENDIX -->')[0]
    text=['<!-- CURATED_APPENDIX -->','## 补充实际检验与限制','',
          '原始24帧的三项4px定位失败与部分遮挡夹具失败均保留，门槛1没有通过。对同24个冻结构造追加了逐核old relative、绝对贡献、signed、可见mass/投影面积/数量匹配random的等预算完整模型扰动检查；强制top64仅作比较。构造类型来自独立构造记录，不代表自动语义分类器已经通过。', '',
          '另加两个先冻结的新原生夹具：全画面完全遮挡的后核，其DC、尺度、opacity正负有限差分全图响应严格为0；正负抵消夹具的抵消率为99.801%。后者log-scale原生局部梯度约0.001519，但δ有限差分为-0.058860、δ/2为-0.122630，明确标记unstable_response。不能以新增夹具替换原始失败，也不能将加性恒等式当作操作预测优势。', '',
          '新增按outline、清楚颜色过渡、unknown分列的2px/4px贡献召回/集中度、selected mass距固定目标段分布、连续覆盖与缺口长度。纹理类别在真实模型中没有独立语义标注，因此保持unknown；不能称其假边缘。距离统计仅覆盖固定少量目标段，不是全物体真值普查。', '',
          '部分视角找不到满足冻结质量规则的匹配平坦ROI：原始flat_rms字段在空mask时的0是未定义值，不是观测到零代价。附录明确标记UNVERIFIED，原始平台剖面与整个非目标区域成本仍单列；这不满足独立完整局部性认证。Lego平坦负例8群、Chair 4群均未接受。平坦负例有47核和29核的低可见数案例；同一目标四种方法数量严格相同，64为上限而非填满配额。', '',
          '原始ringing_overshoot字段只是RGB范围变化代理；[RINGING_APPENDIX.json](RINGING_APPENDIX.json)用固定参考方向/对比给出完整native剖面的规范化越界量与反向变化量。原始结果不改写。线性RGB宽度/位置和误差改善仍由对完整渲染EOTF后的原生剖面记录提供。', '',
          '工程完整性42项检查与5项CPU回归通过，不等于三个科学门槛通过。真实核群构造/独立测试共192个原子单位、3456次完整模型native forward；逐群实际时间区间与搜索成本记录在GROUP_TIME_COST.json。记录只有秒级结束时间，未伪造精确GPU计时。', '',
          '已查看Lego和Chair对比图：signed排名参考仍覆盖大量表面；诊断接受子集存在团块和跨视角缺口。这是实现者的观察，不能代替独立human visual GO。', '',
          '- [原始失败明细](FAILURE_CASES.json)', '- [独立工程检查](INDEPENDENT_ENGINEERING_AUDIT.json)',
          '- [逐群实际时间与成本](GROUP_TIME_COST.json)', '- [合成逐核评分补充](results/synthetic_kernel_score_appendix.json)',
          '- [Lego定位/覆盖附录](results/lego_localization_appendix.json)', '- [Chair定位/覆盖附录](results/chair_localization_appendix.json)',
          '- [Lego独立作用/成本图](media/lego/independent_effect_cost.png)', '- [Chair独立作用/成本图](media/chair/independent_effect_cost.png)',
          '', '当前状态仍为ENGINEERING_NOT_READY；两场景门槛2置信区间下界均为0，门槛3人工复核pending，color/cov普通同权限局部优化均为NOT_RUN。', '']
    report.write_text(base+'\n'+'\n'.join(text))
    atomic_json(OUT/'DELIVERY_COMPLETE.json',dict(status=final['status'],optimization='NOT_RUN',final_sha256=sha(ART/'FINAL.json'),
                 main_units=len(final['completed_units']),appendix_units=3,tests='5 CPU + 42 engineering checks',human_visual_GO='PENDING'))

if __name__=='__main__':main()
