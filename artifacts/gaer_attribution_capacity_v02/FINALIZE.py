"""Presentation and independent scalar followup only; never changes sealed science."""
import sys,json,csv,math
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'experiments/gaer_attribution_capacity_v02'))
import numpy as np
from runtime import *
from media import save,sheet,profile_plot
from diagnostics import sample_image,normal_points,row_sample
from probes import profile_metrics
from scipy.sparse import csr_matrix

def scalar_stats(profile):
 raw=np.asarray(profile,dtype=np.float64);p=np.maximum(raw,0);offset=np.arange(-12,13);total=p.sum();center=float((offset*p).sum()/max(total,1e-20));width=float(np.sqrt(((offset-center)**2*p).sum()/max(total,1e-20)));variation=float(np.abs(np.diff(p)).sum());return dict(native_ink_min=float(raw.min()),moment_domain='nonnegative ink, native roundoff below zero retained in raw data',peak=float(p.max()),center=center,ink_mass_width=width,contrast=float(p.max()-min(p[0],p[-1])),ringing_TV_excess=variation-abs(float(p[-1]-p[0])))

def finalize():
 guard('finalize',gpu=False);P=json.loads((ART/'PROTOCOL.json').read_text());audit=json.loads((ART/'tests/ROI_INDEPENDENT_AUDIT.json').read_text());summary={};profiles=[];envelopes={};shape_association={};allfits=[];media_files=[]
 for scene,record in P['scenes'].items():
  oracle=json.loads((ART/'results'/f'{scene}_oracle.json').read_text());capacity=json.loads((ART/'results'/f'{scene}_capacity.json').read_text());probe=json.loads((ART/'results'/f'{scene}_probes.json').read_text());shape=json.loads((ART/'results'/f'{scene}_shape_anyview_condition.json').read_text());vs={v['key']:v for v in record['views']};pool_metrics={}
  for label in oracle['per_view'][0]['metrics']:
   if 'diagnostic_perview_' in label:continue
   rows=[v['metrics'][label] for v in oracle['per_view']];fields=[np.load(vs[v['view']]['source']) for v in oracle['per_view']];full=sum(float(a['alpha'][a['line_binary']].sum(dtype=np.float64)) for a in fields);pixelcounts=[int(a['line_binary'].sum()) for a in fields];total=sum(r['total_contribution'] for r in rows);mass=sum(r['line_total_contribution'] for r in rows);pool_metrics[label]=dict(line_total_contribution=mass,mass_recall=mass/full,coverage_gt_01=sum(r['coverage_gt_01']*n for r,n in zip(rows,pixelcounts))/sum(pixelcounts),coverage_gt_05=sum(r['coverage_gt_05']*n for r,n in zip(rows,pixelcounts))/sum(pixelcounts),nonline_mass_leakage=1-mass/total)
  pv=[f for f in capacity['fits'] if f['scope']=='perview_known_target'];shared=capacity['fits'][-1];roi_counts={k:v['counts'] for k,v in audit['scenes'][scene].items()};tot=sum(v['total_samples'] for v in roi_counts.values());marked=sum(v['marked_samples'] for v in roi_counts.values());probe_methods={}
  for parameter,amp in (('DC',.01),('logscale',.015)):
   for method in P['probes']['methods']:
    rows=[r for r in probe['rows'] if r['method']==method and r['parameter']==parameter and r['amplitude']==amp];probe_methods[parameter+'_'+method]=dict(fragments=len(rows),mean_target_response_fraction=float(np.mean([r['target_response_fraction'] for r in rows])),median_half_amplitude_derivative_relative_change=float(np.median([r['half_amplitude_derivative_relative_change'] for r in rows])),max_half_amplitude_derivative_relative_change=max(r['half_amplitude_derivative_relative_change'] for r in rows),mean_visible_mass=float(np.mean([r['visible_mass'] for r in rows])),mean_projected_area=float(np.mean([r['projected_area'] for r in rows])),median_outside_MSE=float(np.median([r['outside_MSE'] for r in rows])),max_matched_mass_error=max([r['matched_random_residual']['relative_total_mass_error'] for r in rows if r['matched_random_residual']] or [0.]))
  costs={}
  for g in json.loads((ART/'results'/f'{scene}_roi_r_000.json').read_text())['groups']:
   matchedrows=[r for r in probe['rows'] if r['roi']==g['roi'] and r['method']=='matched_random'];costs[str(g['roi'])]=matchedrows[0]['matched_random_residual']
  line_rows=[];envelopes[scene]=[]
  for f in pv:
   key=f['view'];a=np.load(vs[key]['source']);alpha=a['alpha'].astype(float)+3e-6;L=a['ink'].astype(float);E=a['line_binary'];floor=np.maximum(L-alpha,0)**2;envelopes[scene].append(dict(view=key,continuous_whole_target_MSE_lower_bound=float(floor.mean()),line_target_MSE_lower_bound=float(floor[E].mean()),line_pixels_target_exceeds_full_accepted_alpha=int((E&(L>alpha)).sum()),interpretation='necessary pixel envelope bound A(s)<=sum original weights for s in [0,1]; independent-pixel relaxation, not a sufficiency test'))
  # Save every loss/KKT/dual log, not just terminal successes.
  lossfile=ART/'downloads'/scene/'known_target_solver_logs.csv';lossfile.parent.mkdir(parents=True,exist_ok=True)
  with lossfile.open('w',newline='') as out:
   keys=['scope','view','start','iteration','primal_feasible_objective','dual_lower_bound','relative_dual_gap','projected_gradient_norm','projected_gradient_relative','relative_objective_change','wall_seconds'];writer=csv.DictWriter(out,fieldnames=keys);writer.writeheader()
   for fit in capacity['fits']:
    allfits.append(dict(scene=scene,scope=fit['scope'],view=fit.get('view','shared'),certificate=fit['independent_FP64_certificate']))
    for start in fit['starts']:
     for row in start['log']:writer.writerow({k:(fit.get(k,'shared') if k in ('scope','view') else row.get(k)) for k in keys})
  # Plot all frozen profiles and paired probe profiles without selecting winners.
  import matplotlib;matplotlib.use('Agg')
  import matplotlib.pyplot as plt
  fig,ax=plt.subplots(figsize=(8,5))
  for f in capacity['fits']:
   logs=f['starts'][0]['log'];ax.plot([r['iteration'] for r in logs],[r['primal_feasible_objective'] for r in logs],label=f.get('view','shared'))
  ax.set(xlabel='iteration, zero start',ylabel='feasible objective',title=scene+' frozen native solver');ax.legend();fig.tight_layout();p=ART/'media'/scene/'solver_objectives.png';fig.savefig(p,dpi=140);plt.close(fig);media_files.append(rel(p))
  for key in P['roi_views']:
   a=np.load(vs[key]['source']);per=np.load(ART/'downloads'/scene/f'{key}_perview_native_RGB.npz')['ink'];shared_ink=np.load(ART/'downloads'/scene/f'{key}_shared_native_RGB.npz')['ink'];rois=record['rois'][key];groups=json.loads((ART/'results'/f'{scene}_roi_{key}.json').read_text())['groups'];overview=a['RGB'].copy()
   from PIL import Image,ImageDraw,ImageFont
   im=Image.fromarray(np.round(np.clip(overview,0,1)*255).astype(np.uint8));draw=ImageDraw.Draw(im);font=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',13)
   for j,r in enumerate(rois):draw.rectangle(r['box_xyxy'],outline=(255,0,0),width=1);draw.text((r['box_xyxy'][0],r['box_xyxy'][1]-14),str(j)+':'+r['category'],font=font,fill=(200,0,0))
   p=ART/'media'/scene/f'{key}_frozen_ROI_coordinates.png';im.save(p);media_files.append(rel(p))
   for j,r in enumerate(rois):
    points=np.asarray(groups[j]['profiles_yx']);target_profile=sample_image(a['ink'],points);per_profile=sample_image(per,points);shared_profile=sample_image(shared_ink,points);profiles.append(dict(scene=scene,view=key,roi=j,category=r['category'],fragment=r['fragment'],target=scalar_stats(target_profile),perview=scalar_stats(per_profile),shared=scalar_stats(shared_profile)))
  if scene in P['scenes']:
   pdata=np.load(ART/'downloads'/scene/'original_parameter_probes.npz');groups=json.loads((ART/'results'/f'{scene}_roi_r_000.json').read_text())['groups'];fig,axs=plt.subplots(len(groups),2,figsize=(12,2.8*len(groups)),squeeze=False)
   for g in groups:
    for col,(parameter,amp) in enumerate((('DC',.01),('logscale',.015))):
     ax=axs[g['roi'],col]
     for method in P['probes']['methods']:
      k=f'roi{g["roi"]}_{method}_{parameter}_{amp}_derivative_profile';ax.plot(np.arange(-12,13),pdata[k].mean(1),label=method)
     ax.set(title=f'{g["category"]} #{g["fragment"]} {parameter}',xlabel='normal offset native pixels',ylabel='paired RGB derivative');ax.legend(fontsize=7)
   fig.tight_layout();p=ART/'media'/scene/'all_frozen_probe_profiles.png';fig.savefig(p,dpi=120);plt.close(fig);media_files.append(rel(p))
  # Correct label for initial shape offset: it was relative to fragment center.
  # Additional nearest marked-pixel association audit, without changing shapes.
  d=np.load(ART/'downloads'/scene/'r_000_ROI_full_CSR.npz');a=np.load(vs['r_000']['source']);xy=d['projected_means_xy'];associated=[]
  for g in json.loads((ART/'results'/f'{scene}_roi_r_000.json').read_text())['groups']:
   if g['fragment']!=0 or g['category'] not in ('outline','internal_color_transition'):continue
   y,x=g['center_yx'];yy,xx=np.nonzero(a['line_binary'][y-12:y+12,x-12:x+12]);linepoints=np.column_stack([xx+x-12,yy+y-12])
   for i in g['multiD_top16']:
    if not len(linepoints):continue
    point=linepoints[np.argmin(np.sum((linepoints-xy[i])**2,1))];n=a['normal_xy'][point[1],point[0]].astype(float);norm=np.linalg.norm(n)
    if norm<1e-8:continue
    n/=norm;delta=xy[i]-point;associated.append(dict(roi=g['roi'],original_ID=i,center_xy=xy[i].tolist(),nearest_frozen_marked_xy=point.tolist(),normal_offset_signed=float(delta@n),normal_offset_abs=float(abs(delta@n)),euclidean_distance=float(np.linalg.norm(delta))))
  shape_association[scene]=dict(initial_field_correction='signed_centerline_offset_quantiles in initial shape result means offset to frozen fragment center along assigned doubled-angle normal, not closest line; use this independent nearest marked-pixel audit for line offset',associations=associated,nearest_line_normal_abs_quantiles=np.quantile([r['normal_offset_abs'] for r in associated],[0,.25,.5,.75,1]).tolist() if associated else [])
  summary[scene]=dict(original_N=record['count'],roi_total_samples=tot,roi_marked_samples=marked,all_K8_winner_changes=sum(v['all_K8_winner_changes'] for v in roi_counts.values()),all_K32_winner_changes=sum(v['all_K32_winner_changes'] for v in roi_counts.values()),marked_K8_winner_changes=sum(v['marked_K8_winner_changes'] for v in roi_counts.values()),marked_fallback_to_valid_full=sum(v['old_fallback_to_valid_full'] for v in roi_counts.values()),oracle_budgets=oracle['budgets'],oracle_evaluation_metrics=pool_metrics,probe_methods=probe_methods,matched_random_residuals=costs,perview_whole_target_MSE=float(np.mean([f['metrics']['whole_target_MSE'] for f in pv])),shared_whole_target_MSE=float(np.mean([r['whole_target_MSE'] for r in shared['per_view_metrics']])),perview_mean_objective=float(np.mean([f['independent_FP64_certificate']['primal_feasible_objective'] for f in pv])),shared_objective=shared['independent_FP64_certificate']['primal_feasible_objective'],capacity_certificates={f.get('view','shared'):f['independent_FP64_certificate'] for f in capacity['fits']},shape=shape)
 atomic_json(ART/'results/PROFILE_METRICS.json',profiles);atomic_json(ART/'results/PIXEL_ENVELOPE_BOUNDS.json',envelopes);atomic_json(ART/'tests/SHAPE_ASSOCIATION_AUDIT.json',shape_association)
 answers=[dict(question='截断是主要限制吗？',status='SEVERE_FOR_D_NOT_PROVEN_PRIMARY_VISUAL_LIMIT',answer='K8严重改变冻结样本的D赢家与回退；K32仍不等于完整。完整记录并未单独证明D更好，不能把截断称为最终线绘唯一或主要限制。'),dict(question='完整记录后D胜过center吗？',status='NO_CLEAR_UNIVERSAL_ADVANTAGE',answer='实际DC/logscale成对扰动已运行；单赢家D在两场景/ROI上优劣不一致，multiD常较局部但可见质量/面积不同；没有普遍优势或因果边责任结论。'),dict(question='旧选择距B上界多远？',status='MEASURED_FULL_N',answer='B500/2000八源 raw 达源域上界约80–83%，center更接近；两个已知诊断视图 raw 仅达 pooled 上界约11–31%。必须区分源域、已知答案域和perview适配。'),dict(question='理想强度下原足迹能形成线吗？',status='RECOGNIZABLE_LINES_PARTIAL_FIDELITY_HUMAN_PENDING',answer='全N连续强度确实生成可辨线结构，远超固定少量二值核；窄峰/深色平台/轮廓仍有误差。四个perview未达到冻结近最优证书，其他perview及两个shared已有证书；只对冻结E/外域λ=1目标有效，不是全表示不可能证明。'),dict(question='固定集合和视角激活限制？',status='BOTH_VIEW_ADAPTATION_AND_JOINT_STRENGTH',answer='诊断perview固定B上界高于pooled；同四图 perview连续目标误差低于shared，仍含已知答案。固定八视角集合、单赢家、view activation 是不同约束；不是泛化算法。'),dict(question='需要shape吗，有何剩余限制？',status='TINY_NATIVE_CAPABILITY_NO_SUFFICIENCY_EVIDENCE',answer='每场景32原核法向2/4缩窄已原生重算T，改善极小；中心未移动，所选核总强度小，不能判定shape必需或足够。单独报告nearest旧mask法向偏移；初次更严格gate的NOT_RUN保留。')]
 atomic_json(ART/'FINAL.json',dict(status='BOUNDED_DIAGNOSTICS_COMPLETE_WITH_UNCONVERGED_AND_VISUAL_PENDING_LIMITS',protocol_sha256=sha(ART/'PROTOCOL.json'),scenes=summary,six_questions=answers,next_one_action='allocationaggregation',next_one_reason='联合贡献/连续强度已能形成线结构，单赢家固定少量集合损失大量共同支持；下一步最有证据支持联合分配与强度聚合，不把oracle当预测算法，不新增训练或新视角。',not_run=dict(opacity_probes='optional, DC and logscale actual probes performed',lambda_sensitivity='protocol predeclared empty; only lambda=1',new_training='outside authorized scope',generalization='known-target capacity only',long_shape_optimization='only fixed-ratio capability permitted'),scientific_primary_objective='continuous L on E=L>.2; weak and zero regions targeted white, outside L^2 constant and lambda A^2 penalty; whole original continuous target MSE separately reported'))
 # Report assembled directly from actual JSON, including all failures/statuses.
 text=['# 实际归因与线容量诊断（v02）\n','两场景的八源全 N oracle、两源完整稀疏 ROI、原参数 ± 扰动、四图 800×800 全 N perview/shared 黑墨拟合，以及限定原生 shape 能力测试均已实际完成。结论是 **原足迹能形成可辨线结构，但完整窄线与深色平台仍为 PARTIAL / 人工视觉验收待定**。不能把未收敛视图、有限 ROI 或固定 λ 的结果称为全表示 NO-GO。\n',f'GPU诊断前冻结提交 `0b77071`；PROTOCOL SHA256 `{sha(ART/"PROTOCOL.json")}`。原模型/旧阶段 5,535 文件哈希保持不变。旧“工程映射完成、无D优势”结论与其失败记录全部保留。\n','## 六个问题的直接回答\n']
 for i,r in enumerate(answers,1):text.append(f'{i}. **{r["question"]}** {r["answer"]} 状态：`{r["status"]}`。\n')
 text+=['## 实际图与数据\n','| 场景 | 四图全图原生容量 | 两保留图同预算oracle | 原生shape固定ROI | 原参数扰动profile |\n|---|---|---|---|---|']
 for s in summary:text.append(f'| {s} | [四图](media/{s}/fourview_known_target_capacity.jpg) / [原生PNG](media/{s}/capacity/r_001_perview_native.png) | [同图同gain](media/{s}/two_holdout_native_oracles.jpg) | [24px最近邻](media/{s}/conditional_shape_ROI_nearest.png) | [全部冻结ROI](media/{s}/all_frozen_probe_profiles.png) |')
 text+=['\n源/保留相机均是历史研究见过的相机。oracle 的八源排名只用八源E；两个保留图 pooled/perview oracle 直接知道评价答案，只是域内上界。容量拟合 r_000/r_018/r_001/r_014 四图全部知道答案；perview和shared同一四图池，不构成泛化测试。\n','## 截断与H1校正\n','| 场景 | 全部冻结样本 | K8→full赢家变化 | K32→full赢家变化 | 标注样本K8→full变化 | 原回退变full有效 |\n|---|---:|---:|---:|---:|---:|']
 for s,d in summary.items():text.append(f'| {s} | {d["roi_total_samples"]} | {d["all_K8_winner_changes"]} | {d["all_K32_winner_changes"]} | {d["marked_K8_winner_changes"]}/{d["roi_marked_samples"]} | {d["marked_fallback_to_valid_full"]} |')
 text+=['\nD为 `|w_i(p−2n)−w_i(p+2n)|`，候选必须中心可见。[ROI排名收敛审计](tests/ROI_RANKING_CONVERGENCE.json)保存四种score在同ROI上K8/16/32到full的TOP8变化，以及含未知center候选的充分赢家区间。初始K8/16/32 JSON的winner_certified_margin_pixels名称只计保留集间隔，不能证明full赢家；需best下界超过其余及未见ID上界。旧残量小于最大D的回退门控也不等于赢家认证。multiD TOP8平均Jaccard依次Lego .597/.725/.897、Chair .533/.629/.832。完整双遍查询原生分桶及接收序列，只查询冻结点/端点/25px profile 的整数邻居，按原ID双线性合并；不插值槽位，不建 H×W×N。全部格点保留，包括未标注/未定义normal/无中心贡献。Lego自动政策只找到 r_000 的1个flat_negative，r_018无合格flat；没有补选。\n','原生有效 SH3 颜色使用 mean−camera 方向、每通道max(SH+.5,0)，无上限clamp、无额外EOTF。官方CPU SH3函数独立校准，ROI RGB/alpha回放误差约10⁻⁶，signed分解 `ΔRGB=Σ c_i Δw_i + bg ΔT` 通过固定容差。相同原ID/权重、同色可有大D而RGB差为0；Σ|D|不能抵消。Lego平坦负例平均ΣD≈.821，而RGB双侧差范数≈.008，颜色项抵消约99.1%。H1应叫**法向贡献变化**，没有RGB因果责任标签。\n','首轮近零颜色分母导致的cancellation展示负大数已保留原封印；[独立FP64归一化审计](tests/ROI_INDEPENDENT_AUDIT.json)给出修正及低信号标志，未改变赢家/选择/扰动。原生CSR、原始ID、有效颜色、全部K理由/赢家/残量/间隔与逐ROI全N分数在 downloads/*/*ROI_full_CSR.npz。\n','## 同预算线质量上界\n','TopB取全N `b_i=Σ_vΣ_E w_i` 最大系数，在原始完整T固定时最大化线域总质量；不限制泄漏。FP32颜色梯度使用全部接收贡献，没有topK截断。FP64原接收权重审计给出舍入差与最大可能次优质量；冻结排名未据结果改动。上界不适用于删核、opacity或covariance变化。\n','| 场景 | B | 八源raw/源上界 | 八源center/源上界 | 保留域raw/pooled上界 | pooled/perview上界质量 |\n|---|---:|---:|---:|---:|---:|']
 for s,d in summary.items():
  for r in d['oracle_budgets']:text.append(f'| {s} | {r["budget"]} | {r["raw_source8_fraction_of_bound"]:.2%} | {r["center_source8_fraction_of_bound"]:.2%} | {r["raw_diagnostic_fraction_of_pooled_bound"]:.2%} | {r["diagnostic_pooled_bound"]:.2f} / {r["diagnostic_perview_adapted_bound"]:.2f} |')
 text+=['\n以下在同两个保留图累计；质量召回、阈值覆盖和非线泄漏是三个指标。不是把“支持质量”当成干净墨线。\n','| 场景 | 集合 | 线总质量 | 质量召回 | 覆盖>.1 / >.5 | 非线质量泄漏 |\n|---|---|---:|---:|---:|---:|']
 for s,d in summary.items():
  for label in ('raw_500','center_500','source8_oracle_500','diagnostic2_pooled_oracle_500','raw_2000','center_2000','source8_oracle_2000','diagnostic2_pooled_oracle_2000'):
   m=d['oracle_evaluation_metrics'][label];text.append(f'| {s} | {label} | {m["line_total_contribution"]:.2f} | {m["mass_recall"]:.2%} | {m["coverage_gt_01"]:.2%} / {m["coverage_gt_05"]:.2%} | {m["nonline_mass_leakage"]:.2%} |')
 text+=['\n旧raw多数像素回退至center（八源Lego65.53%、Chair80.95%），不是纯D。新oneD组也保留固定normal/数值条件的center回退。单赢家会丢共同强度；八源固定集合不是逐图边集合。旧full-T baseline仅验证原封印并读缓存；没有重新做旧buffer/vote工程检查。另导出原生白背景颜色1−s的实际RGB，确认与1−feature质量在3e−6内一致。删除核后的原SH子集并非此处黑墨。\n','## 实际小扰动\n','每场景r_000自动ROI全部参与；每方法每组8原ID，DC±.02/±.01（有效未clamp RGB改变量=.28209479×DC）、logscale±.03/±.015，原全SH3保持。克隆被编辑参数，不改输入。五方法同数量、同权限、同渲染次数；random按全视可见质量及投影面积匹配，不匹配局部位置，可能和主组重叠。\n','| 场景 | 方法 | DC局部响应占比均值 | logscale局部响应占比均值 |\n|---|---|---:|---:|']
 for s,d in summary.items():
  for method in P['probes']['methods']:text.append(f'| {s} | {method} | {d["probe_methods"]["DC_"+method]["mean_target_response_fraction"]:.3f} | {d["probe_methods"]["logscale_"+method]["mean_target_response_fraction"]:.3f} |')
 text+=['\n这些是整图导数能量落入24×24目标ROI的比例，不是修复率或语义正确率。center/oneD/multiD/color_signed可见质量及面积不相同，完整JSON保留其代价、random匹配残差、外域/其他ROI MSE、alpha阈值覆盖损伤及半幅导数差。小幅SH clamp与raster接受阈值会使半幅不完全线性。profile保存25个normal像素的实际RGB±值、导数、中心/gradient-width/端点contrast/TV excess；原边没有错误目标，不能称“改善”。\n','## 原足迹全图已知目标容量\n','实际原生外观为 `color_i=1−s_i`，白背景，全部原位置/scale/rotation/opacity/T保留，0≤s≤1。原生 `I=1−Σw_i s_i`，feature A与AT adjoint和白背景公式的新fixture及四图检查通过。\n','**冻结主目标**为 `f=(Σ_E(A−L)^2+Σ_out L^2+λΣ_out A^2)/(2HW)`，λ=1；E=L>.2内仍使用连续L，弱墨迹及零墨域都被当外域压向白，弱域原L²是常数。此目标不是全像素连续L拟合；全图与原连续L的MSE另外报告，不能混称。shared取同四图目标平均。全N连续解不是等B算法优越性比较，也不是紧凑边资产。\n','FISTA/power/backtracking与两初值预算冻结为500/120步，保留最好可行值。原生FP32优化；独立FP64接受权重的Fenchel dual下界验证于显式小矩阵，保守FP64舍入界及预声明余量全部减去。完整loss/PG/dual日志在 downloads/*/known_target_solver_logs.csv。0.5% gap阈值未达者写预算内未认证，不扩大预算、不能据其失败下NO-GO。\n','| 场景 | 相机/共享 | primal / dual lower | 相对gap | 近最优状态 |\n|---|---|---:|---:|---|']
 for r in allfits:
  c=r['certificate'];text.append(f'| {r["scene"]} | {r["view"]} | {c["primal_feasible_objective"]:.7f} / {c["dual_lower_bound"]:.7f} | {c["relative_dual_gap"]:.3%} | {c["status"]} |')
 text+=['\n| 场景 | perview平均全连续L MSE | shared同池MSE | perview平均主目标 | shared主目标 |\n|---|---:|---:|---:|---:|']
 for s,d in summary.items():text.append(f'| {s} | {d["perview_whole_target_MSE"]:.7f} | {d["shared_whole_target_MSE"]:.7f} | {d["perview_mean_objective"]:.7f} | {d["shared_objective"]:.7f} |')
 text+=['\n原始ID strength NPZ包括全N而非假compact集合，view/source SHA、0/1约束、活动数量/强度总量/饱和数均有记录。原全SH3输入未变；共享和逐图actual native RGB独立导出。有限原足迹必有A≤full accepted alpha；[pixel envelope](results/PIXEL_ENVELOPE_BOUNDS.json)给出独立像素松弛的必要误差下界，不证明所有其他样式都不可能。\n','## 条件原生shape与剩余限制\n','冻结协议允许“任一perview已认证且线残差>.01”触发固定r_000。初次runner过严要求r_000自身认证，所以保存的shape NOT_RUN是工程gate记录；补充anyview条件单元按冻结规则实际完成。每场景两个固定fragment各16原ID，双角平均normal，法向方差÷2²/4²并保留.3像素协方差下限；tangent方差保留、cross置零，中心固定。isolated单行cov2D override发生在逆矩阵/半径/tiles之前；重跑整个native流水线与T。stock无determinant AA opacity补偿，峰值opacity保持；没有2D画线代理。\n']
 for s,d in summary.items():
  sh=d['shape'];text.append(f'{s}：实际编辑{sh["metrics"][0]["edited_count"]}核、其原拟合强度总和{sh["edited_strength_sum"]:.3f}；原线MSE {sh["condition_line_MSE"]:.6f}，ratio2/4为'+ ' / '.join(f'{m["line_MSE"]:.6f}' for m in sh['metrics'])+'。全T/alpha变化有实际地图与计数。')
 text+=['\n改动少、所选强度小，效果微弱不能作为shape必要性/充分性证明。初始shape JSON中的offset字段实际是相对fragment中心的法向偏移，不能当最近线距离；[关联审计](tests/SHAPE_ASSOCIATION_AUDIT.json)另存每ID到冻结marked像素的nearest法向偏移。窄化不移动中心，background/外侧目标、重叠宽足迹、固定强度跨视角与强度预算仍可能分别限制质量。\n','## 下一项与状态\n','只选择 **allocationaggregation：联合贡献分配与强度聚合** 作为下一研究方向。实际连续共同支持能形成线结构，单赢家/固定少量二值集合损失很大；本轮没有证明新选择算法或perview预测能泛化。形状缩窄没有显示明显充分性，所以不据此优先进入更长shape优化。\n','工程算子READY；部分拟合预算内未认证；原足迹视觉PARTIAL；完整干净窄线视觉GO人工待定。optional opacity/λ敏感性/长shape轨迹均NOT_RUN（协议中未启用）；新训练/新detector/新视角未做。已保存[工程问题](tests/ENGINEERING_FAILURES.json)、初次NOT_RUN和此前全部失败，不因新图更好覆盖旧结论。\n','[复现说明](REPRODUCE.md)、[最终JSON](FINAL.json)、[新数学fixture](tests/NEW_MATH.json)、[FP64证书fixture](tests/FP64_CERTIFICATE.json)、[独立保存结果审计](tests/INDEPENDENT_ARTIFACT_AUDIT.json)、[保护哈希](tests/PROTECTED_AFTER.json)。']
 (ART/'REPORT_ZH.md').write_text('\n'.join(text)+'\n')
 print('FINALIZED',list(summary),flush=True)
if __name__=='__main__':finalize()
