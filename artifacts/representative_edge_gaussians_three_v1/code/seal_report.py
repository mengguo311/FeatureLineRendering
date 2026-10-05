"""Add truthful final audit scope and continuous interpretation; science is read-only."""
from io_utils import *

def stage():
 verify_s0();verify(OUT/'F_SELECTION_SEAL');f=json.loads((ART/'FINAL.json').read_text());pairs=json.loads((ART/'RESULT_INTERPRETATION.json').read_text())['samecount_continuous_C_differences'];joint=[p for p in pairs if p['arm'] in ['C','D','E']];above=all(p['offedge_difference']>0 for p in joint)
 a=json.loads((ART/'INDEPENDENT_CPU_AUDIT.json').read_text());failed=[r for r in a['results'] if not r['original_float64_absolute_check_pass']];assert a['all_pass'] and len(failed)==1 and failed[0]['scene']=='chair'
 f.update(science_quantitative_verdict='TARGET_NOT_SUPPORTED_AT_FROZEN_OPERATINGPOINTS' if above else 'CONTINUOUS_COMPARISONS_HUMAN_PENDING',science_diagnostic=dict(all_joint_samecount_offedge_above_A=above,points=len(joint),no_posthoc_tolerance=True),CPU_arithmetic_contract=dict(original_float64_all_pass=False,original_failed_scene='chair',original_B_score_abs_error=failed[0]['original_float64_errors']['B_score'],unchanged_original_abs_limit=5e-6,stored_dtype_independent_all_pass=True,stored_dtype_max_B_score_error=max(r['errors']['B_score'] for r in a['results']),native_calibration_tolerances_unchanged=True,scientific_inputs_and_selections_unchanged=True,note='AUDIT_ARITHMETIC_NOTE.md'),independent_ffmpeg_video_audit=dict(all_pass=True,path=str(ART/'INDEPENDENT_VIDEO_DECODE.json'),sha256=sha(ART/'INDEPENDENT_VIDEO_DECODE.json')),engineering_scope='All147 native poses/calibrations, exact stored-dtype arithmetic, residual bound, full media verification; inherited float64 absolute-score failure explicitly retained')
 atomic(ART/'FINAL.json',f)
 p=ART/'REPORT_ZH.md';s=p.read_text().replace('工程结论 **GO；','工程结论 **GO**；').replace('家长/第三方','父级审阅者/第三方')
 if '原双精度CPU审计在Chair' not in s:
  note='原双精度CPU审计在Chair的B分数误差6.795×10⁻⁶超过固定5×10⁻⁶界限，**原审计未全过**，原代码/断言及失败记录保留。C前增加的独立stored-float32算术验证重现继承矩阵的实际运算，仍用原界限，最大分数误差3.15×10⁻¹⁴；科学输入、F选择和native容差未改。工程GO以实际存储算术、全147校准和媒体验证为范围；详见[AUDIT_ARITHMETIC_NOTE.md](AUDIT_ARITHMETIC_NOTE.md)，不能表述为原float64检查全通过。\n\n';s=s.replace('## 科学配方与输入边界',note+'## 科学配方与输入边界')
 if '在全部27个joint同数量C比较点' not in s and above:
  text='在全部27个joint同数量C比较点，offedge alpha贡献均高于A。λ惩罚降低了joint自身漏出，但本轮没有证据支持“同时保留主要支持并比独立A减少非边缘泄漏”的总体目标；这是冻结操作点上的覆盖/漏出权衡，**不支持科学目标成功**。\n\n仅F选定λ.3匹配点在C的覆盖/漏出相对A为：';parts=[]
  for ss in f['scenes']:
   rs={r['arm']:r for r in ss['coverage_matched'] if r['phase']=='C'};base=rs['A']['metrics'];e=rs['E']['metrics'];parts.append(f"{ss['scene']} {e['major_coverage']/base['major_coverage']:.3f}倍/{e['offedge_alpha_fraction']/base['offedge_alpha_fraction']:.3f}倍（{rs['E']['count']} IDs）")
  text+='；'.join(parts)+'。Lego在C覆盖更高，Chair/Ficus在C覆盖下降，三者漏出均更高；F匹配没有自动形成C同覆盖比较。人类视觉结论仍PENDING，不因这些结果重调预算、normalization、阈值或λ。\n\n';s=s.replace('## 每场景六图与完整视频',text+'实际坏点及模型辅助查看记录见[VISUAL_REVIEW_ZH.md](VISUAL_REVIEW_ZH.md)。该记录不是独立人类验收。\n\n## 每场景六图与完整视频')
 s=s.replace('两尺寸各自独立逐帧decode及排除标题RGB crop distinct=33，','两尺寸均已由现有OpenCV检查和独立ffmpeg rawvideo管线逐帧decode；六段每段去标题RGB crop distinct=33（[独立解码记录](INDEPENDENT_VIDEO_DECODE.json)），');p.write_text(s)
if __name__=='__main__':stage()
