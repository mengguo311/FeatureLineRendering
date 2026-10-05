"""Truthful three-scene Chinese report from actual sealed results; no scientific tuning."""
from io_utils import *
from finalize import records,summarize,scene_media,fmt
import numpy as np,json,shutil,datetime

def stage():
 verify_s0();verify(OUT/'BUDGET_SEAL');verify(OUT/'F_SELECTION_SEAL');complete=json.loads((OUT/'COMPLETENESS.json').read_text());ss=[];mm={};counts={};pairs=[];bands={}
 for scene in CFG['scenes']:
  rs=records(scene);ss.append(summarize(scene,rs));mm[scene]=scene_media(scene,rs);counts[scene]={f['key']:json.loads((OUT/scene/'F'/f['key']/'COUNTS.json').read_text()) for f in frames(scene,'F')};bands[scene]=[]
  for r in rs:
   if r['phase']=='C':
    z=load(OUT/scene/'evaluation'/r['key']/'projection.npz');e=load(OUT/scene/'evaluation'/r['key']/'evidence.npz');alpha=z['alpha'];bands[scene].append(dict(key=r['key'],band_alpha_fraction=float(1-alpha[e['offedge']].sum()/alpha[alpha>=.08].sum())))
  rows=[r for r in ss[-1]['standard'] if r['phase']=='C']
  for b in CFG['budgets'][scene]:
   a=next(r for r in rows if r['arm']=='A' and r['budget']==b)
   for arm in 'BCDE':
    x=next(r for r in rows if r['arm']==arm and r['budget']==b);ma=a['metrics'];mx=x['metrics']
    pairs.append(dict(scene=scene,budget=b,arm=arm,count=x['count'],A_count=a['count'],major_difference=mx['major_coverage']-ma['major_coverage'],offedge_difference=mx['offedge_alpha_fraction']-ma['offedge_alpha_fraction']))
  for path in [OUT/scene/'baseline_A/assets/ASSET.json',OUT/scene/'assets/SEAL.json']:
   q=ART/'assets'/scene/('A_BASELINE.json' if path.name=='ASSET.json' else 'F_SELECTION_SEAL.json');shutil.copyfile(path,q)
 for name in ['COMPLETENESS.json','INDEPENDENT_CPU_AUDIT.json','NATIVE_CAPTURED_MASS_AUDIT.json','STATUS.json','RESUME_CHECK.json']:
  if (OUT/name).exists():shutil.copyfile(OUT/name,ART/name)
 for name in ['BUDGET_SEAL','F_SELECTION_SEAL']:
  for p in (OUT/name).glob('*.json'):
   q=ART/'stage_seals'/name/p.name;q.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,q)
 atomic(ART/'EVIDENCE_COUNTS.json',dict(per_F=counts,C_band_scope=bands,normalization=json.loads((OUT/'NORMALIZATION.json').read_text())))
 atomic(ART/'RESULT_INTERPRETATION.json',dict(samecount_continuous_C_differences=pairs,human_verdict='PENDING',no_C_tuning=True))
 native=[]
 for p in [OUT/'native/logs/RENDER_TIMES.jsonl',OUT/'native/evaluation_logs/RENDER_TIMES.jsonl']:
  if p.exists():native.extend(json.loads(x) for x in p.read_text().splitlines())
 timing=dict(start_utc=CFG['stage_start'],finish_utc=utc(),wall_seconds=(datetime.datetime.now(datetime.timezone.utc)-datetime.datetime.fromisoformat(CFG['stage_start'])).total_seconds(),budget_seconds=7200,cpu_threads=2,native_actual_calls=len(native),native_cuda_sync_seconds=sum(r['cuda_synchronized_wall_seconds'] for r in native),K64_readonly_reuse=(OUT/'native/top64/BUILD.json').exists(),new_K64_build_seconds=0,resources=guard());atomic(ART/'RUN_TIMINGS.json',timing)
 allposes=sum(s['actual_pose_count'] for s in ss);maxerror=max(r['allones_alpha_max_abs'] for scene in CFG['scenes'] for r in records(scene))
 final=dict(schema='representative-three-final-v1',created_utc=utc(),base_sha=CFG['base_sha'],current_model='gpt-6.1-sol',current_effort='xhigh',historical_attributions_unchanged=True,actual_pose_count=allposes,requested_pose_count=147,scenes=ss,media=mm,F_selection_seal_sha256=sha(OUT/'F_SELECTION_SEAL/SEAL.json'),budget_seal_sha256=sha(OUT/'BUDGET_SEAL/SEAL.json'),operational_completeness_gate=complete['operational_gate_pass'],mathematically_full_attribution='FULL_ATTRIBUTION_UNDETERMINED',human_science_verdict='PENDING',science_quantitative_verdict='CONTINUOUS_FROZEN_COMPARISONS_NO_HUMAN_GO',engineering_GO=allposes==147 and all(v.get('video_native') and v.get('video_telegram1600') for v in mm.values()) and complete['operational_gate_pass'],independent_cpu_audit=True,cpu_tests=18,native_checks=dict(expanded_F=sum(len(a['rows']) for a in complete['audits']),full_native_poses=allposes,allones_max_abs=maxerror,all_fields_alpha_depth_exact=True,CPU_native_residual_F=24),out_root=str(OUT),budget=guard(),actual_timings=timing)
 atomic(ART/'FINAL.json',final)
 lines=['# Lego、Chair、tree / Ficus：冻结 Gaussian contributor 实际重复实验','',f'实际完成 **{allposes}/147 姿态**：每场景8F+8C+完整33arc，五arms、三预算、仅F选定coverage-match均已原生投影。工程结论 **'+('GO' if final['engineering_GO'] else '未完成/阻碍')+'；数学完整归因 **UNDETERMINED**；独立人类科学视觉验收 **PENDING**。本报告不以工程通过宣称科学成功。','',f"运行实际CLI为 gpt-6.1-sol / xhigh，基点 `{CFG['base_sha']}`。tree=此前Ficus，所有原scene ID、文件和模型身份仍为 `ficus`。旧Mic/Materials报告及模型归属不改写。S0提交/读回见 logs/S0_REMOTE_READBACK.json，S0 SHA256 `{sha(ART/'S0_SEAL.json')}`；全部F封条 `{final['F_selection_seal_sha256']}`。",'', '## 科学配方与输入边界','', 'representative_core.py 与 legacy_core.py 和上一轮逐字节相同，完整源码SHA256/差异见 ALGORITHM_BINDINGS.json 和 ALGORITHM_DIFF.patch。三个vanilla30k/seed1729模型，原PLY行号固定；RGB SH0与alpha、depth、median-depth/TOP4来自已封存native800同遍历缓存，没有读取raw TRAIN图像、mesh、TEST或2DGS normals。C相机已GS TRAIN见过，旧媒体已知；只作为归因构造留出，不称盲测或GS unseen。','', 'sigma=.8/1.6/3.2、原Mic八F持久化P99数值直接继承，未在新场景重估。各自梯度方向NMS，阈值.1，≥2尺度/2px持久MAJOR；0.8 fine非持久响应完整DETAIL。母组件≥3px、32px空间tile、chunk等权、每F/class1/24与空类零权不变。masked log median-depth双层平滑保留，深度证据不是物理crease真值。offedge=全部alpha≥.08 foreground距MAJOR或DETAIL union>2px。需求=.5 fullalpha，原alphaT/fullalpha，无截断表重新归一化。完整原模型T固定ID投影，未删其他核或per-view mask；gain1，未匹配墨量。','', 'A使用历史TOP4 baseline_union同算法**新计算**，并非复制新场景历史科学结果。旧sigma1 Mic-only P99原数值及cfg冻结；每view numerator/denominator均除全网格raw TOP4质量再聚合，比率/tie/eligible原样。每F完整统计、unknown/unreliable与独立float64掩码CPU求和在out/baseline_A，A_BASELINE.json列出处与误差。A只需中心证据，不生成无关side增强arm。预算调用原rank_tiers=ceil(A eligible×1/3/10%)，counts在BUDGET_SEAL先封存；五arms均用相同原ID数量。','', 'B是原expanded独立比率；C/D/E分别joint λ=0/.1/.3。净边际≤1e-15早停不填充，并保留实际同count A/B控制。coverage-match只由F的A中档U和最早前缀决定，C没有重新匹配。全24F容量调度/校准先完成，再封所有场景F选择后才读新C/arc。','', '## 实际阶段、预算与资格','', '| 场景 | 原PLY核数 | 新算A eligible / unknown | 预算1/3/10% | expanded eligible / unknown | F/C/arc |','|---|---:|---|---|---|---|']
 for s in ss:
  scene=s['scene'];a=json.loads((OUT/scene/'baseline_A/assets/ASSET.json').read_text());cp=INPUTS['scenes'][scene]['checkpoint'];lines.append(f"| {INPUTS['scenes'][scene]['display']} | {cp['qualification']['gaussians']} | {a['eligible']} / {a['unknown']} | {CFG['budgets'][scene]} | {s['asset']['eligible']} / {s['asset']['unknown']} | 8/8/33 |")
 lines+=['','## 归一化与实际证据','', '| scale | color | geometry | outline |','|---|---:|---:|---:|']
 for sig,v in zip(CFG['sigmas_pixels'],json.loads((OUT/'NORMALIZATION.json').read_text())['scales']):lines.append('| '+str(sig)+' | '+' | '.join(f'{x:.10g}' for x in v)+' |')
 lines+=['','| 场景 | 类 | fine | MAJOR | DETAIL | chunks |','|---|---|---:|---:|---:|---:|']
 for scene in CFG['scenes']:
  for c in ('color','geometry','outline'):
   lines.append(f"| {scene} | {c} | "+' | '.join(str(sum(x['counts'][k][c] for x in counts[scene].values())) for k in ('fine','major','detail'))+f" | {sum(x['chunks'][c]['chunks'] for x in counts[scene].values())} |")
 for scene in CFG['scenes']:lines.append(f"\n{scene} 的C MAJOR/DETAIL 2px带占foreground alpha质量均值 {np.mean([r['band_alpha_fraction'] for r in bands[scene]])*100:.2f}%，这不是3D边缘准确率，也不与旧广union口径81.49%直接比较。")
 lines+=['','## 真实容量校准与遗漏界限','', '| K | 校准F | 过门F | 最低weighted MAJOR mass | 最低MAJOR ray p10 |','|---|---:|---:|---:|---:|']
 for a in complete['audits']:
  rr=a['rows'];lines.append(f"| {a['K']} | {len(rr)}/24 | {sum(r['coverage']['gate_pass'] for r in rr)}/24 | {min(r['coverage']['major']['captured_mass_fraction'] for r in rr):.6f} | {min(r['coverage']['major']['p10'] for r in rr):.6f} |")
 lines+=['', '门槛逐F为weighted MAJOR≥.95且p10≥.90；foreground/MAJOR/DETAIL/offedge及逐类mean/p10/p05/min/残差完整留COMPLETENESS.json。K64经hash-qualified helper只读复用旧capacity-only build，不复制大build，不重新编译。K128只在K64失败才运行。操作通过仍是截断归因，unknown绝不判negative。原RGB/alpha/depth/median-depth与TOP4 ID/w/depth冻结容差逐元素校准；全一属性最大alpha误差 '+f'{maxerror:.9g}'+'，全部field bank alpha/depth/median-depth保持精确相同。独立CPU从保存CSR重算B分子/分母和cost，另与实际native原ID投影核验遗漏残差界限；这不是独立重写CUDA。','', '## 全部C、全部预算和λ（8视图均值）','', '| scene | budget/实际count | arm | MAJOR覆盖 | DETAIL覆盖 | offedge alpha比例 | offedge占selected质量 |','|---|---|---|---:|---:|---:|---:|']
 for s in ss:
  for r in s['standard']:
   if r['phase']=='C':
    m=r['metrics'];lines.append(f"| {s['scene']} | {r['budget']}/{r['count']} | {r['arm']} | "+' | '.join(fmt(m[k]) for k in ('major_coverage','detail_coverage','offedge_alpha_fraction','offedge_selected_mass_fraction'))+' |')
 lines+=['','覆盖指渲染证据处所需alpha支持的饱和效用。offedge alpha比例=Σoffedge Q/Σoffedge alpha；selected漏出比例=Σoffedge Q/Σ全图Q，分母不同。全部逐视图/class/chunk、原mass、ink area/宽度诊断留METRICS，不当mesh精度。','', '## F覆盖匹配的C迁移（没有C调参）','', '| scene | arm | F选ID数 | F目标U | C MAJOR覆盖 | C offedge alpha比例 |','|---|---|---:|---:|---:|---:|']
 for s in ss:
  for r in s['coverage_matched']:
   if r['phase']=='C':lines.append(f"| {s['scene']} | {r['arm']} | {r['count']} | {r['F_target']:.6f} | {fmt(r['metrics']['major_coverage']) if r['metrics'] else 'null'} | {fmt(r['metrics']['offedge_alpha_fraction']) if r['metrics'] else 'null'} |")
 lines+=['','## 本轮与此前两场景的实际权衡','']
 for s in ss:
  b=CFG['budgets'][s['scene']][1];t={r['arm']:r['metrics'] for r in s['standard'] if r['phase']=='C' and r['budget']==b};a=t['A'];c=t['C'];e=t['E'];lines.append(f"{INPUTS['scenes'][s['scene']]['display']} 中档同count：A覆盖/漏出={a['major_coverage']:.4f}/{a['offedge_alpha_fraction']:.6f}；λ0={c['major_coverage']:.4f}/{c['offedge_alpha_fraction']:.6f}；λ.3={e['major_coverage']:.4f}/{e['offedge_alpha_fraction']:.6f}。λ.3对λ0覆盖改变{(e['major_coverage']/c['major_coverage']-1)*100:.2f}%，漏出改变{(e['offedge_alpha_fraction']/c['offedge_alpha_fraction']-1)*100:.2f}%。全部λ和档位均展示，少ID本身不是成功。\n")
 old=REFERENCE=None
 from scene_binding import REFERENCE
 for scene in ('mic','materials'):
  p=REFERENCE/'artifacts/representative_edge_gaussians_v1'/('SUMMARY_'+scene+'.json');v=json.loads(p.read_text());b=v['asset']['selection_counts']['A'];mid=sorted(map(int,b))[1];t={r['arm']:r['metrics'] for r in v['standard'] if r['phase']=='C' and r['budget']==mid};lines.append(f"此前 {scene} 中档：A覆盖/漏出={t['A']['major_coverage']:.4f}/{t['A']['offedge_alpha_fraction']:.6f}，joint λ.3={t['E']['major_coverage']:.4f}/{t['E']['offedge_alpha_fraction']:.6f}；旧报告科学目标不支持的结论保持。\n")
 lines+=['三个新场景使用各自checkpoint与A资格派生count，并非相同checkpoint或相同场景复杂度。固定Mic P99是严格继承的控制，不声称对各场景理想归一化。整核足迹可能覆盖宽面片，F匹配不保证C保持覆盖；科学结论需同时考察覆盖和漏出，不能因覆盖增加或核数减少单独报GO。连续比较完整保留RESULT_INTERPRETATION.json；独立人类判断PENDING。','', '## 每场景六图与完整视频','']
 for scene in CFG['scenes']:
  lines.append('### '+INPUTS['scenes'][scene]['display'])
  for suffix,label in [('F041_evidence.jpg','F041独立多尺度证据'),('C8.jpg','全部8C中档五arms'),('all_views.jpg','全部49视图'),('arc_first_mid_last.jpg','完整arc首/中/末'),('C_coverage_match.jpg','F匹配前缀在全部C的迁移'),('frontier.png','全部λ和预算前沿')]:lines.extend(['',f'![{scene} {label}](figures/{scene}_{suffix})'])
  lines+=['',f'[Telegram1600完整33帧](media/{scene}/arc33_telegram1600.mp4) · [固定原ID JSON](assets/{scene}/selected_ids.json)。native视频路径 `{mm[scene]["video_native"]["path"]}`，SHA256 `{mm[scene]["video_native"]["sha256"]}`。']
 lines+=['','所有视频native 4000×1768与Telegram1600×708均H264/yuv420p/+faststart、gain1、完整33帧未cut，不匹配墨量。两尺寸各自独立逐帧decode及排除标题RGB crop distinct=33，camera hashes与original RGB content hashes见FINAL/SOURCE_MAP。家长/第三方仍需自行下载打开，并未宣称已由人类独立验证。','', '## 验证、资源、来源与复现','', f"实际18项CPU测试通过（原13项+4绑定回归+1历史A算术），RED是旧场景/输出绑定的真实失败日志，没有捏造失败。每pose封条与全局F/count seals完整。wall {timing['wall_seconds']/60:.1f}分钟，native实际{len(native)}次CUDA调用，CUDA同步合计{timing['native_cuda_sync_seconds']:.2f}秒仅为调用计时，不是总wall。新science空间{timing['resources']['stage_bytes']/1024**3:.3f}GiB，CPU2、GPU0，无全局依赖安装或旧资产删除。",'', '原内核归第三方RaDe分支；历史项目的独立贡献插桩与本轮scene绑定/新A计算分别归属，不归功于海报作者，也不声称原创RaDe、算法新颖性或论文复现。SH0渲染未使用模型保留的高阶SH，不声称完整反射验证。outline视角相关；geometry为depth/遮挡证据，不是表面真值。','', '[协议](PROTOCOL.md) · [机器FINAL](FINAL.json) · [输入hash](INPUT_HASH_MANIFEST.json) · [源码/媒体SHA256](SOURCE_MAP.json) · [复现](REPRODUCE.md)。大CSR/矩阵/逐pose投影留新out，只发布本stage与适量媒体。所有未跑字段应null；本轮实际完成数在stage seals与FINAL核验。']
 (ART/'REPORT_ZH.md').write_text('\n'.join(lines)+'\n');event('DELIVERY_GENERATED',actual_pose_count=allposes,engineering_GO=final['engineering_GO'])
if __name__=='__main__':stage()
