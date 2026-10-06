"""CPU-only preregistration from existing frozen image fields; no D measurements."""
import json,subprocess
import numpy as np
from scipy.ndimage import distance_transform_edt,uniform_filter,gaussian_filter
from runtime import *

def roi_policy(a):
 L=a['ink'];alpha=a['alpha'];rgb=a['RGB'];sdf=distance_transform_edt(alpha>.5)-distance_transform_edt(alpha<=.5)
 smooth=gaussian_filter(rgb,sigma=(2,2,0));gy,gx=np.gradient(smooth,axis=(0,1));grad=np.sqrt((gx*gx+gy*gy).sum(2));density=uniform_filter((L>.2).astype(float),size=25)
 inside=np.zeros(L.shape,bool);inside[24:-24,24:-24]=True;internal=(sdf>8)&(L>.2)&inside
 vals=grad[internal];cut=float(np.quantile(vals,.65)) if len(vals) else 0
 classes={'outline':((L>.2)&(np.abs(sdf)<=4)&inside,L),
 'internal_color_transition':(internal&(grad>=cut),grad*(1-density)),
 'texture_proxy':(internal&(grad<cut),density*L),
 'flat_negative':((alpha>.95)&(L<=.02)&(uniform_filter(L,size=25)<.02)&inside,-grad)}
 result=[];used=[]
 for category,(valid,score) in classes.items():
  coords=np.column_stack(np.nonzero(valid));order=np.lexsort((coords[:,1],coords[:,0],-score[valid]))
  picked=[]
  for idx in order:
   y,x=map(int,coords[idx])
   if all((y-yy)**2+(x-xx)**2>=40**2 for yy,xx in used):
    picked.append((y,x));used.append((y,x))
    if len(picked)==2:break
  for j,(y,x) in enumerate(picked):
   points=[[y+dy,x+dx] for dy in (-8,-4,0,4,8) for dx in (-8,-4,0,4,8)]
   result.append(dict(category=category,fragment=j,center_yx=[y,x],box_xyxy=[x-12,y-12,x+12,y+12],sample_points_yx=points,selection_score=float(score[y,x]),intent='automatic image proxy, no physical annotation'))
 return result

def main():
 if (ART/'PROTOCOL.json').exists():raise RuntimeError('freeze already exists')
 old=json.loads((OLD/'artifacts/gaer_rgb_union_voting_v01/PRODUCTION_FREEZE.json').read_text())
 protected={};roots=[ROOT,OLD,ATTR,Path('/home/u00134/3dgs_line/gaer_view_selection_v01'),Path('/home/u00134/3dgs_line/image_space_edge_foundation_v1')]
 for r in roots:
  for q in subprocess.check_output(['git','ls-files','-z'],cwd=r).decode().split('\0'):
   p=r/q
   if q and p.is_file() and not (r==ROOT and q.startswith(('experiments/gaer_attribution_capacity_v02/','artifacts/gaer_attribution_capacity_v02/'))):protected[str(p)]=sha(p)
 for p in old['protected_before']:
  if Path(p).is_file():protected[p]=sha(p)
 scenes={}
 for scene,d in old['scenes'].items():
  views=[]
  for v in d['vote_views']+d['evaluation_views']:
   key=v['key'];p=OLD/f'artifacts/gaer_rgb_union_voting_v01/downloads/{scene}/{key}/source_fields.npz';protected[str(p)]=sha(p)
   # Validate prior seal containing this cache, without repeating its tests.
   unit=f"{scene}_{'eval' if key in ('r_001','r_014') else 'vote'}_{key}";seal=OLD/f'artifacts/gaer_rgb_union_voting_v01/seals/{unit}.json';s=json.loads(seal.read_text())
   expected=s['files'][str(p.relative_to(OLD))]
   if expected!=sha(p):raise RuntimeError('old cache seal mismatch')
   views.append(dict(key=key,camera=v['camera'],camera_sha256=v['camera_sha256'],source=str(p),source_sha256=sha(p),role=v['role'],old_seal=str(seal),old_seal_sha256=sha(seal)))
  rois={v['key']:roi_policy(np.load(v['source'])) for v in views if v['key'] in ('r_000','r_018')}
  scenes[scene]=dict(model=d['model'],model_sha256=d['model_sha256'],count=d['count'],views=views,rois=rois)
  protected[d['model']]=sha(d['model'])
  agg=OLD/f'artifacts/gaer_rgb_union_voting_v01/downloads/{scene}_votes_all_original.npz';protected[str(agg)]=sha(agg)
 protocol=dict(schema='attribution-capacity-v02-preregistered',base='bea1bfc10ec1d2e58f7ffd8ac857a55ade95d8b3',bootstrap_HEAD=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),scenes=scenes,
 source_views=['r_007','r_033','r_059','r_086','r_000','r_008','r_018','r_030'],evaluation_views=['r_001','r_014'],diagnostic_views=['r_000','r_018','r_001','r_014'],roi_views=['r_000','r_018'],
 domain='ALL original Gaussian IDs, full fixed original geometry/opacity/T; four known-target 800x800 capacity frames; ROI conclusions restricted to frozen samples',
 mask='original cached darkness L>.2',weak='0<L<=.2',nonline='L==0',budgets=[500,2000],coverage_thresholds=[.1,.5],
 roi_policy='24x24 fragments, two per category per ROI view, 5x5 fixed grid includes unmarked/undefined samples. Outline |alpha SDF|<=4; internal alpha SDF>8; smooth RGB gradient 65% cut splits color-transition and texture proxies; flat L<=.02 and 25px average<.02. Desc score then y,x; centers >=40px apart. Frozen before any contribution metric.',
 D=dict(delta=2.,K=[8,16,32,'full'],numerical_floor=2e-6,confidence_floor=.22,full_replay_RGB_tolerance=2e-5,full_replay_alpha_tolerance=3e-6,decomposition_tolerance=3e-5,winner_certification='full accepted sparse traversal; candidate center w>0; best-second margin >4e-6; undefined normals separately tracked, direction (1,0) only for diagnostic profiles'),
 probes=dict(views=['r_000'],fragments_per_category=2,methods=['center','oneD','multiD','color_signed','matched_random'],edited_count=8,DC_amplitudes=[.02,.01],DC_conversion='same +DC coefficient each channel; effective unclamped RGB change C0*DC where C0=.28209479177387814; native SH clamp retained',logscale_amplitudes=[.03,.015],opacity='NOT_RUN optional; DC and logscale suffice',profile_offsets=list(range(-12,13)),random_seed=20261006,matching='nearest joint standardized log full-view visible mass and log projected covariance area, without replacement; report residual'),
 solver=dict(objective='mean_frames [ sum_E(A-L)^2 + sum_outside L^2 + lambda*sum_outside A^2 ] / (2*800*800); outside includes both weak and zero regions, target outside zero; reported global target MSE uses original continuous L everywhere',lambda_outside=1.,sensitivity_lambdas=[],bounds=[0,1],max_iterations=500,min_iterations=40,power_iterations=12,backtracking_factor=2.,backtracking_max=20,relative_objective_tolerance=1e-7,projected_gradient_relative_tolerance=1e-4,dual_relative_gap_tolerance=.005,check_every=20,restart='monotone FISTA restart if objective rises; retain best feasible',starts=['zero','old_raw_top2000'],second_start_max_iterations=120,atomic_repeat_tolerance=3e-5,dual='f(s)=.5||WA s-y||^2+c; dual(u)= -.5||u||^2-y.u +sum_i min(0,(A^T W u)_i)+c; u=WA s-y; FP64 reductions; conservative .00003*sum_abs_adjoint allowance, label numerical certificate'),
 shape=dict(condition='valid original style operator and numerical dual relative gap<=.005 and line-domain residual MSE>.01 for any perview fit, or explicit visually broad profile; otherwise NOT_RUN reason',ratios=[2,4],views=['r_000'],ROI='first outline and first internal_color_transition frozen fragment',edited_count=16,selection='multiD sum on fragment frozen points; centers unchanged',semantics='ephemeral screen covariance override before inversion/radius/tiles; tangent doubled-angle normal average, cross covariance zero, normal variance=max(.3,original normal variance/ratio^2), tangent variance retained; stock .3 pixel covariance floor, original peak opacity retained, no determinant compensation or AA correction; full pipeline recomputes T'),
 visual=dict(gain=1.,GO='clean complete target narrow lines and plateaus retained; human visual acceptance pending, no numerical GO substitution'),resource=dict(GPU=0,CPU=2,MAX_JOBS=2,root_reserve_GiB=4,common_git_reserve_GiB=1.5,stage_cap_GiB=8,coding_budget_seconds=10800),old_contract='unchanged one pixel one vote; previous failures preserved; no new detector/training/views')
 for k in ('D','probes','solver','shape','visual','resource'):protocol[k+'_sha256']=digest(protocol[k])
 protocol['ROI_sha256']=digest({s:d['rois'] for s,d in scenes.items()});protocol['source_sha256']=digest({s:[(v['key'],v['source_sha256'],v['camera_sha256']) for v in d['views']] for s,d in scenes.items()})
 atomic_json(ART/'PROTECTED_BEFORE.json',dict(files=protected,AGENTS='none found in ancestors/project',old_dirty_independent_audit_preserved=True));atomic_json(ART/'PROTOCOL.json',protocol)
 (ART/'PROTOCOL_ZH.md').write_text('''# 冻结协议：归因截断、选择上界与原足迹线容量\n\n仅写入新阶段。复用原 Lego/Chair 全 SH3、八源相机及两个旧保留相机。线目标是旧显示连续 darkness L，E=L>.2；不修改检测器。\n\n先比较全 N、完整原 T 下 B=500/2000 的八源线质量 oracle 与旧 raw/center；两个保留相机的 pooled/perview oracle 只是在已知答案域的上界。线质量、覆盖阈值 .1/.5、非线泄漏分别报告，上界不限制泄漏，也不适用于改形状或删核。\n\nD/扰动使用 r_000/r_018 上自动选定的轮廓、内部颜色过渡、纹理代理及平坦负例。24×24 ROI 中固定 25 个格点全部保留。坐标与算法、输入 SHA 已写 PROTOCOL.json。D 是法向贡献变化，不能称因果边责任。原生双遍稀疏查询完整接收序列，按原 ID 双线性合并，比较 K8/16/32/full。分解使用原生 SH3 有效颜色和白背景；容差固定，不据结果改阈值。\n\n小扰动仅克隆原参数：每组 8 核；DC ±.02/±.01，logscale ±.03/±.015；五方法同样数量。比较 ± 导数、半幅收敛、25px profile、外域 MSE/alpha。原边没有目标错误，因此不宣称改善。\n\n线容量使用四个相同已知目标相机 r_000/r_018/r_001/r_014，原全部核/几何/opacity/T 固定；白背景颜色 1-s，s∈[0,1]。全 800×800 perview 与 shared 同域凸 box 二次拟合，outside λ=1，弱线及无墨域都处罚。两初始点，500/120 步上限；FISTA/backtracking、PG 与数值 dual gap 阈值已冻结。未收敛不能判足迹 NO-GO。连续全 N 不是等核数算法对照。\n\n条件 shape 仅在原生 style 有效且数值 gap≤.005、线域残差>.01 或可见宽 profile 时运行；原 ID 与中心固定，临时屏幕协方差法向缩窄 2/4，重算半径、分桶及完整 T，峰值 opacity 不补偿。否则写 NOT_RUN/ENGINEERING_NOT_READY。自动指标仅报告；完整干净窄线的视觉 GO 仍需人工。\n\n精确指标、停止条件、坐标、幅值和各配置 SHA 见 PROTOCOL.json。本提交发生在 GPU 诊断之前。\n''')
 print('FROZEN',sha(ART/'PROTOCOL.json'),len(protected))
if __name__=='__main__':main()
