"""Continuous comparisons of frozen diagnostic axes; no post-holdout tuning."""
import json
from io_utils import *

def stage():
 rows=[]
 for scene in CFG['scenes']:
  s=json.loads((ART/('SUMMARY_'+scene+'.json')).read_text());standard=[r for r in s['standard'] if r['phase']=='C'];pairs=[]
  for b in CFG['budgets'][scene]:
   a=next(r for r in standard if r['budget']==b and r['arm']=='A');c=next(r for r in standard if r['budget']==b and r['arm']=='C')
   for arm in ('B','C','D','E'):
    x=next(r for r in standard if r['budget']==b and r['arm']==arm)
    if x['actual_views']!=8 or a['actual_views']!=8:continue
    ma=a['metrics'];mx=x['metrics'];mc=c['metrics'];pairs.append(dict(budget=b,arm=arm,vs_A=dict(major_coverage_difference=mx['major_coverage']-ma['major_coverage'],offedge_alpha_difference=mx['offedge_alpha_fraction']-ma['offedge_alpha_fraction'],major_coverage_ratio=mx['major_coverage']/ma['major_coverage'],offedge_alpha_ratio=mx['offedge_alpha_fraction']/ma['offedge_alpha_fraction']),vs_lambda0=dict(major_coverage_ratio=mx['major_coverage']/mc['major_coverage'],offedge_alpha_ratio=mx['offedge_alpha_fraction']/mc['offedge_alpha_fraction'])))
  matched=[r for r in s['coverage_matched'] if r['phase']=='C'];a=next(r for r in matched if r['arm']=='A');match=[]
  for x in matched:
   if not x['metrics'] or not a['metrics']:continue
   match.append(dict(arm=x['arm'],count=x['count'],major_coverage_ratio_vs_A=x['metrics']['major_coverage']/a['metrics']['major_coverage'],offedge_alpha_ratio_vs_A=x['metrics']['offedge_alpha_fraction']/a['metrics']['offedge_alpha_fraction']))
  rows.append(dict(scene=scene,same_budget_pairs=pairs,F_selected_coverage_matches=match))
 atomic(ART/'RESULT_INTERPRETATION.json',dict(quantitative_target='preserve major demand coverage and reduce nonedge leakage together; fixed axes, no posthoc tolerance',results=rows,human_visual_verdict='PENDING',scope='operatingpoints all chosen from F; C read-only comparisons'))
 report=(ART/'REPORT_ZH.md').read_text();marker='## 负结果、工程结论与科学范围';lines=['## 实测权衡：本轮不支持目标成功','']
 for row in rows:
  scene=row['scene'];b=CFG['budgets'][scene][1];s=json.loads((ART/('SUMMARY_'+scene+'.json')).read_text());standard=[x for x in s['standard'] if x['phase']=='C' and x['budget']==b];table={x['arm']:x['metrics'] for x in standard};a=table['A'];c=table['C'];e=table['E']
  if not all([a,c,e]):continue
  lines.append(f"**{scene}中档同数量**：A的C MAJOR覆盖为{a['major_coverage']:.4f}、offedge alpha比例{a['offedge_alpha_fraction']:.6f}；联合λ0为{c['major_coverage']:.4f}/{c['offedge_alpha_fraction']:.6f}，λ.3为{e['major_coverage']:.4f}/{e['offedge_alpha_fraction']:.6f}。λ.3相比λ0漏出改变{(e['offedge_alpha_fraction']/c['offedge_alpha_fraction']-1)*100:.1f}%，MAJOR覆盖改变{(e['major_coverage']/c['major_coverage']-1)*100:.1f}%；相对旧A依然明显增加非边缘贡献。这是覆盖/漏出权衡，不能称全面优势。")
  match=next(x for x in row['F_selected_coverage_matches'] if x['arm']=='E');lines.append(f"仅F选定λ.3 coverage匹配前缀{match['count']} IDs，在C的MAJOR覆盖是A的{match['major_coverage_ratio_vs_A']:.3f}倍，offedge alpha贡献是A的{match['offedge_alpha_ratio_vs_A']:.3f}倍。F匹配没有自动保持C的同覆盖，少ID不能当作成功。")
  lines.append('')
 lines+=['冻结λ惩罚确实改变联合组的漏出/覆盖前沿，但本轮没有证据支持“同时保留主要边界并比独立组减少非边缘泄漏”的总体目标。独立人工视觉判定仍PENDING；工程完成不转译成科学GO。参数、预算、证据、相机与λ均未为这些C结果更改。','']
 if marker in report:report=report.replace(marker,'\n'.join(lines)+marker)
 (ART/'REPORT_ZH.md').write_text(report)
 final=json.loads((ART/'FINAL.json').read_text());final['science_quantitative_verdict']='TARGET_NOT_SUPPORTED_AT_FROZEN_OPERATINGPOINTS';final['human_science_verdict']='PENDING';final['result_interpretation_sha256']=sha(ART/'RESULT_INTERPRETATION.json');atomic(ART/'FINAL.json',final)
if __name__=='__main__':stage()
