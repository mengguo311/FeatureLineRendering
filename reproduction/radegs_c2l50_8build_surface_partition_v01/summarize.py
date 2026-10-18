from env import *
from collections import Counter
import csv
if __name__=='__main__':
 r1=json.loads((ROOT/'round1/COUNTS.json').read_text());r2=json.loads((ROOT/'round2/COUNTS.json').read_text());r3=json.loads((ROOT/'round3/COUNTS.json').read_text());records=[json.loads(p.read_text()) for p in (ROOT/'round3/validation').glob('*/*/*/*/RESULT.json')];stats={}
 for s in SCENES:
  stats[s]={}
  for arm in ['line','shifted_12px','source_geometry_axis','shuffled_sides']:
   x=[r for r in records if r['scene']==s and r['arm']==arm];use=[r for r in x if r['old_conditional_native_error_p'] is not None];a=np.array([r['old_conditional_native_error_p'] for r in use]);b=np.array([r['reordered_conditional_native_error_p'] for r in use]);stats[s][arm]=dict(case_views=len(x),depth_usable_case_views=len(use),mean_responsibility_L1=float(np.mean([r['mean_responsibility_L1'] for r in x])),median_of_case_median_error_p_before=float(np.median(a)) if len(a) else None,median_of_case_median_error_p_after=float(np.median(b)) if len(b) else None,improved=int(np.sum(b<a-1e-12)),worse=int(np.sum(b>a+1e-12)),unchanged=int(np.sum(abs(b-a)<=1e-12)))
 js(ROOT/'round3/ORDERING_SUMMARY.json',stats)
 budget=[]
 for rd,sub in [('round1','scenes'),('round2','evidence'),('round3','evidence')]:
  for path in (ROOT/rd/sub).glob('*/*/*/*/CENTER_BASELINE.json'):
   r=json.loads(path.read_text());e=npz(path.parent/'EVIDENCE.npz');budget.append(dict(round=rd,scene=r['scene'],view=r['view'],case=r['case'],arm=r['arm'],query_pixels=len(e['query_uv']),unique_pixels=len(np.unique(e['query_uv'],axis=0)),source_ids=len(np.unique(e['source_index'])),positive_source_ids=len(np.unique(e['source_index'][e['weight']>0])),alphaT_sum=float(e['weight'].sum()),finite_conditional_fraction=float(np.nanmean(e['conditional_stats'][:,4])),qualified_pixels=int(e['conditional_pixel_qualified'].sum())))
 with open(ROOT/'BUDGET_AND_UNKNOWN.csv','w') as f:
  writer=csv.DictWriter(f,fieldnames=list(budget[0]));writer.writeheader();writer.writerows(budget)
 cal=[]
 for p in ROOT.glob('round*/**/CALIBRATION.json'):cal.append(dict(path=str(p),**json.loads(p.read_text())))
 js(ROOT/'CALIBRATION_AUDIT.json',dict(cameras=len(cal),all_engineering_go=all(x['engineering_go'] for x in cal),max_rgb_mae=max(x['rgb_mae'] for x in cal),max_alpha_mae=max(x['alpha_mae'] for x in cal),max_center_surface_p95=max(x['center_surface_p95'] for x in cal),max_query_renderer_error=max(x['renderer_query_max_abs'] for x in cal),all_N_reference_checks=sum(x['all_N_pixels'] for x in cal),all_N_ROI_checks=r3['all_N_ROI_pixels'],details=cal))
 (ROOT/'round3/ROUND3_REPORT_ZH.md').write_text('''# 第三轮：冻结保留视角的独立证伪

实际完成三scene×各2保留相机、11case×2view×4arm=88测量，264次ROI all-N对照。未拟合保留视角面参，未改第2轮任何参数。科学NO_GO正式primitive/NPR；诊断工程通过。

冻结原线的4个局部patch实例在保留视角产生8次检查：7次VISIBLE_DISAGREEMENT、1次UNOBSERVED，没有通过；其它null也均无通过。全臂合计26次冻结patch检查，21可比较不符/5未观测。UNOBSERVED没有负票。原线中心共198个沿线点检查，scan24为42可比较/9遮挡/3前方不一致；scan65为63可比较/9画外；ficus为16可比较/37遮挡/17未知/2画外。Ficus明显受遮挡/观测不足影响，不能把失败全归为曲面不存在。

独立排序反事实：保留同一有限EWA source集合，用原opacity与q重新计算alpha（包括旧早停隐藏的核），有效核按条件mode排序，无效者保持mean作为UNKNOWN。重新计算alpha*T，未将已被早停的旧alpha=0当原opacity。原mean权重回放误差通过2e-12界；complete查询与all-N一致。

原线每case/view平均责任L1（范围0..2）再跨case/view平均：建筑0.7721、头骨0.4297、Ficus0.3418。对应depth误差“各case中位的中位”(p)：建筑0.3131→0.3189、头骨0.5065→0.4708、Ficus0.4845→0.4661；并非所有案例改善。几何轴和移位同样有变化，没有线专属稳定收益。sourceID责任会大变而聚合深度近似不变，说明分配不唯一/排序敏感是重要限制。此结果不是证明条件排序物理正确，更不是官方CUDA替代。

实际view_image检查：scan24 0036 window_frame与0012 roof_wall_eave；scan65 0036 cap_marks与0012 socket_rim；ficus test_r_14和test_r_79 thin_leaf_edge。全画面保持原线，毛刺没有隐藏；原图主体清楚，责任着色只在局部。叶边在test_r_14未观测资格不足，test_r_79可比但冻结面不一致。头骨颅顶候选在侧后视角接近轮廓，不能自动认定same physical curve。视角角度DEV到reserved约18.36–98.40度，不是所有失败都能归结为几乎相同视角。

该实验没有识别出rolling silhouette、纹理、source floaters的唯一因果来源：原线可能落在外观边、片层混合或可见性改变处；代理自身与native读出也有不同。第三轮按预冻失败路线结束，未扩大ROI/正式NPR或启动第四轮。
''')
 inspected=[ROOT/'round3/figures'/s/v/ca/'CASE.jpg' for s,v,ca in [('scan24','0036','window_frame'),('scan24','0012','roof_wall_eave'),('scan65','0036','cap_marks'),('scan65','0012','socket_rim'),('ficus','test_r_14','thin_leaf_edge'),('ficus','test_r_79','thin_leaf_edge')]]
 js(ROOT/'round3/VISUAL_REVIEW.json',dict(inspected=[str(p) for p in inspected],sha256={str(p):sha(p) for p in inspected},verdict='NO_GO_FORMAL_PRIMITIVE_OR_NPR',round4_allowed=False))
 review('04_round3_delivery_NO_GO_STOP','''三轮已实际运行。R3三scene保留图逐个检查，冻结原线patch0通过，null亦无通过；排序改变责任较大而depth变化小。工程校准/测试通过，科学NO_GO正式surface primitive，不能等价“物体无面片”。只允许只读验证、统计、包装与本地commit；禁止第四轮。诊断图保留全部原C8/源模型，未生成新物理平面或正式NPR模型。''',[ROOT/'round3/COUNTS.json',ROOT/'round3/ROUND3_REPORT_ZH.md',ROOT/'round3/VISUAL_REVIEW.json'])
 counts=dict(expected_rounds=3,completed_rounds=3,scenes=SCENES,valid_cases=11,unavailable_cases=1,round1=r1,round2=r2,round3=r3,distinct_condition_measurement_units=len(budget),original_sources_unchanged=True,physical_primitives=0,new_GS_models=0,source_role_NPZ=len(list((ROOT/'round2/models').glob('*/*/*/*/SOURCE_ROLES.npz'))),diagnostic_point_PLY=len(list((ROOT/'round2/models').glob('*/*/*/*/SOURCE_ID_DIAGNOSTIC_POINTS.ply'))),case_boards=len(list(ROOT.glob('round*/**/CASE.jpg'))),all_round_images=len(list(ROOT.glob('round*/**/*.jpg'))),new_test_counts=dict(round1=8,round2=12,round3=8,total=28),scope='local pilot only; no full-scene classification',verdict='HONEST_NEGATIVE_FOR_PRIMITIVE_RECOVERY',no_automatic_continuation=True)
 js(ROOT/'COUNTS.json',counts);state('THREE_ROUNDS_COMPLETE_VERIFYING',completed_rounds=3,status='SCIENTIFIC_NO_GO_DELIVERY_PENDING',children=[],no_automatic_continuation=True)
