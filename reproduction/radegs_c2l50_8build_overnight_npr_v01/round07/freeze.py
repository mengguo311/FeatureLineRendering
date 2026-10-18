from env import *
def main():
 prev=json.loads((ROOT/'r07_prior_verify.json').read_text());assert prev['manifest_verified'] and prev['packages_verified'];st=json.loads((R6/'ITERATION_STATUS.json').read_text());assert st['sealed'] and st['next_allowed'] and st['round']==6
 assert git(Path.cwd(),'rev-parse','HEAD')=='6f1ff83d61af5d96f1f277fa7460d246d9b1fdb5';assert not (R/'METHOD_FREEZE.json').exists();assert not list(R.glob('*'));R.mkdir(exist_ok=True);(R/'reviews').mkdir();(R/'logs').mkdir()
 js(R/'ROLLBACK_BEFORE.json',rollback());js(R/'RESOURCE_PREFLIGHT.json',guard());sources=json.loads((R6/'SOURCE_MANIFEST.json').read_text())['files']
 for p in R6.rglob('*'):
  if p.is_file() and p.name not in ['ASTRA_RUNTIME_FINAL.md','AGENT_LAUNCH.json'] and 'mplconfig' not in p.parts and not p.name.endswith('.tar.gz'):sources[str(p)]=sha(p)
 for folder in ['round06','round03']:
  for p in (CODE.parent/folder).glob('*.py'):sources[str(p.resolve())]=sha(p)
 for p in [JC/'renderer.py',JC/'format.py',JC/'ewa.cpp',ROOT.parent/'c2l50_8build_joint_gs_v01/build/libjoint.so']:sources[str(p)]=sha(p)
 js(R/'SOURCE_MANIFEST.json',dict(files=sources,read_only=True))
 cfg=dict(round=7,mechanism='frozen source SH angular-appearance counterfactual, independent of r06 morphology',arms=['full_sh','dc_only','anchor_sh'],anchor_view=DEV,scene_roster={s:views(s) for s in SCENES},fit_views={s:[DEV[s],AUX[s]] for s in SCENES},reserved=RES,render=dict(source='original REGISTRY model only, no ink',full_SH_preserved_on_disk=True,dc='max(0,.5+C0*SH0)',anchor='evaluate full SH for each original source kernel at DEV camera center, then freeze RGB for all views',bg=dict(scan24=[0,0,0],scan65=[0,0,0],ficus=[1,1,1]),floor_variance=dict(scan24=.0144,scan65=.0144,ficus=.3),near=.2,jacobian='original +/-1.3tanFOV, fx/fy/cx/cy unchanged',renderer='readonly joint CPU EWA; center-depth outputs diagnostic only'),engineering_gates=dict(full_cpu_replay='bitexact V1 reference RGB/alpha/center_z at every camera',arms_geometry='bitexact alpha/median_center_z/expected_center_z',native_comparison='report existing CPU/native difference; same-view MAE RGB/alpha <=.02 and relative center-vs-native-depth p95 <=.15, inherited v01 no relaxation',pilot='first Ficus DEV under 120 seconds per render, no nonfinite RGB'),classifier=dict(implementation='exact r03 density.py',bins=16,sigma=.75,threshold_quantile=.05,posterior=.65,margin=.2,seeds='same original r03 pooled RGB UV and proxy labels; all three arms same budget',mask='exact original r03 inference_mask; never re-derived from counterfactual color',DTU='2-label A foreground/background proxy test only; no B parts',ficus='3-label B candidate; labels not GT',no_graph=True),limits=dict(cpu=2,root_reserve_gib=1,hdd_reserve_gib=10,task_cap_gib=12,unit_seconds=600,round_minutes=55,latest_new_science_JST='07:40'),downstream='C/D/NPR NOT_RUN this round',historically_seen=True,tuning=False)
 js(R/'CONFIG.json',cfg)
 (R/'METHOD_FREEZE_ZH.md').write_text('''# r07 冻结：源GS角度外观分解对分区的作用

## 真实评估 GO（证伪执行许可，非科学成功）
已读取r06 sealed状态/完整REPORT，实看OVERVIEW及test14失败图；r06新形态主要扩大UNKNOWN，DTU没有可用主体负空间。旧seal/packages只读通过，HEAD6f1ff83d，diff/status干净。另实读joint renderer.py、format.py、ewa.cpp、produce.py及RENDERER_AUDIT：source确有完整SH，颜色与geometry投影分开；可在不动文件的前提下做严格同遮挡配对。因此本轮不是调形态/平滑/seed门，而检验**视角相关颜色项是否误导部件外观**。

## 新变量和强对照
原source每核c_i(d)=max(0,.5+Σ_lm f_i,lm Y_lm(d))。full_sh正常使用目标相机方向；dc_only只求max(0,.5+C0*f_i,0)，不改原SH数组；anchor_sh在DEV相机方向求原完整SH颜色，然后每核颜色固定，全部相机沿用同值。anchor在DEV必须与full_sh位级相同，在其它视图保留一个实际观察方向的高阶外观；区分“冻结角度变化”与“删除高阶信息”。DC不是albedo/光照移除真值，SH可能补偿错几何、遮挡、曝光，DC颜色可能更差。
三臂means/covariance/filter激活/opacity、full source核集合、camera、pixelcenter、背景、排序及alpha*T全相同，只有颜色求值函数变。线C8完全不读入source render，不参与本轮segmentation，也不输出新风格模型。所有source原始SH/Inf/filter及原C8磁盘文件保持只读。使用官方filter补偿已审计activate函数，+Inf经sigmoid1有效，最短cov轴不当normal。

## 输入与可重复性工程门
三scene原REGISTRY.model和SHA，独立读取原PLY，数量与joint原prefix RANGES一致；不把ink混进去。DTU777x581、fx/fy不等、COLMAP W2C；Ficus800²。source source-only CPU floor DTU.0144/Ficus.3，DTU黑背景/Ficus白背景；图像gain1，不每view归一。近.2，世界单位非米。
每个full_sh原生帧必须逐数组重放V1 REFERENCE的source_rgb/source_alpha/source_center_z；每个counterfactual alpha/median_center_z/expected_center_z必须与full bitexact。输出center depth仅渲染诊断，分区mask/跨view可见性继续读取原native RaDe camera-z（DTU）与原CPU plane proxy（Ficus），绝不换成核中心深度。
与原缓存RGB/alpha MAE<=.02、中心vs原surface depth relative p95<=.15沿用v01工程门，同时报告绝对差和source条件，非CUDA等价。若任何scene不通过，保存INVALID不进行其classifier，不放宽容差；其它scene继续。先Ficus DEV真实全帧三臂预算实测，每render120秒门，单unit600秒。参考旧CPU速度约1–4s只作估计，非本轮实测。

## 条件外观配对，门不变
同r03原seed UV/原proxy labels、原infer mask，逐类逐view均等质量16³ RGB histogram、sigma.75bin、本类5%训练密度门、posterior .65/margin .2完全不变，分别在每臂对应的BUILD图像拟合，不调整label/height/mask/graph。旧r03用原native/CPU cache，与本轮fullCPU略有renderer差异，故本轮full_sh才是配对baseline；旧r03/r05/v02作为强历史参考。高于1的渲染RGB保存在证据里，density.indices既有clip到bin边界保持三臂相同；显示仅固定clip0..1，不伪称原rawRGB数值不变。
DTU只是2个旧foreground/background代理类的A阶段测试；即使两色更整齐也必须完整屋顶/牙齿且无地台/桌面，不能称屋顶/墙或颅/颌B通过。Ficus在既有isolated主体范围内做3类盆/木/冠proxy的B精确性。原seed偏差仍存在，无GT，改变后验只是诊断，不是准确率。

## 视角、科学门与禁止越级
DEV/AUX DTU0000/0024、Ficus train_r_80/train_r_7；reserved DTU0012/0036、Ficus test_r_14/test_r_79。全历史曝光，DTU源GS训练视角；reserved只在fit模型封存及BUILD图审后一次推理，不决定任何参数/方向。anchor只能DEV，不能目标view挑好方向。总36真实source渲染（三scene×4view×3臂）、9密度文件、36native标签；资源或工程阻断准确记录实际数。
视觉主门：DC/anchor是否保留完整主体、叶间孔洞，减少盆高光误作木、冠内木误作叶；DTU亮屋顶/暗牙齿与地台/桌面分离。与paired fullSH和既有r05比，不能靠更多UNKNOWN/删mask变干净。保留同ROI失败及所有四视角，跨视图资格沿旧2p depth/1.5px cycle/3p world不改，遮挡不负票。无GT不能报告classification accuracy。若只是色图更平但实体边界/共同可见身份不改善则NO_GO；局部进展可PARTIAL明确限制。
本轮冻结C线支持/D源成员/正式NPR全部NOT_RUN，即使DC图看似style也只能叫source外观counterfactual。后续必须另轮过可见稳定分区门，不能跳源责任。no-line/shifted-line目前无资格不运行。07:40开始收尾/08:00停止，本invocation只r07，不运行r08。

## TDD与交付
逐API RED→实现GREEN：DC解析值及角度不变、full角度改变、anchor DEV等价、原SH/cov/opacity不变、source-only排除ink、filter/Inf激活、samegeometry真实透明遮挡alpha/depth一致、source顺序与front/background、完整fx/fy/cx/cy、fit不读reserved、全部原mask/UNKNOWN保留。真实源fullRGB精确重放不冒充新算法视觉成功。
每scene同相机原RGB/C8/真joint只读参考，full/DC/anchor新source图及差分，paired标签/历史强baseline；所有阴影/高光失败保留。新色只在内存/图片，不导出修改GS。保存render数组、源index颜色求值摘要、class密度、UV、概率/UNKNOWN及计数、校准和实际秒数。独立readonly replay全部render/预测/配对；来源SHA/旧893源码和12worktree不变，安全包、本地commit，r07 ITERATION_STATUS封存退出。
''')
 js(R/'METHOD_FREEZE.json',dict(utc=now(),method_sha256=sha(R/'METHOD_FREEZE_ZH.md'),config_sha256=sha(R/'CONFIG.json'),prior_commit=git(Path.cwd(),'rev-parse','HEAD'),before_new_science=True))
 review('00_angular_appearance_GO','实际代码允许只改颜色求值而不改任何源文件，三臂同geometry可严格比较。DC不等albedo。允许真实小帧预算/TDD后扩展，一切A/B精确门仍待实图，不授NPR资格。',[R6/'REPORT_ZH.md',R6/'delivery/OVERVIEW.jpg',JC/'renderer.py',JC/'format.py',JC/'ewa.cpp',R/'METHOD_FREEZE.json'])
 status('FROZEN',children=[])
if __name__=='__main__':main()
