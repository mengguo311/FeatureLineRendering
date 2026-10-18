from env import *
def main():
 pre=json.loads((ROOT/'r09_prior_verify.json').read_text());assert pre['manifest_verified'] and pre['packages_verified'];st=json.loads((R8/'ITERATION_STATUS.json').read_text());assert st['round']==8 and st['sealed'] and st['next_allowed'];assert git(Path.cwd(),'rev-parse','HEAD')=='6b99f5204a09dbce8edd5f5e57e42c540244f422';assert not (R/'METHOD_FREEZE.json').exists();R.mkdir(exist_ok=True);(R/'logs').mkdir(exist_ok=True);(R/'reviews').mkdir(exist_ok=True)
 js(R/'ROLLBACK_BEFORE.json',rollback());js(R/'RESOURCE_PREFLIGHT.json',guard());src=json.loads((R8/'SOURCE_MANIFEST.json').read_text())['files']
 for p in R8.rglob('*'):
  if p.is_file() and p.name not in ['ASTRA_RUNTIME_FINAL.md','ASTRA_RECOVERY_RUNTIME_FINAL.md','AGENT_LAUNCH.json'] and 'mplconfig' not in p.parts and not p.name.endswith('.tar.gz'):src[str(p)]=sha(p)
 for folder in ['round08','round03']:
  for p in (CODE.parent/folder).glob('*.py'):src[str(p.resolve())]=sha(p)
 js(R/'SOURCE_MANIFEST.json',dict(files=src,read_only=True))
 cfg=dict(round=9,mechanism='local RGB gradient structure tensor conditional evidence, not intensity quotient or graph tuning',arms=['raw_rgb','rgb_texture','rgb_scrambled_texture','texture_only'],texture=dict(scale='min(H,W)/581',derivative_sigma=1.,integration_sigma=3.,truncate=3.,gradient_scale_normalized=True,channels='mean RGB derivative outer products',features=['.5+.5*(Jxx-Jyy)/(trace+1e-12)','.5+Jxy/(trace+1e-12)','sqrt(trace)/(sqrt(trace)+.05)'],null='deterministic seed1729 within nonoverlapping round(33*scale) square blocks; preserve RGB triplet multiset in each block; raw RGB color factor unchanged',view_dependence='orientation in image coordinates, covariance under in-plane rotation; not physical material invariant'),density=dict(bins=16,sigma=.75,quantile=.05,posterior=.65,margin=.2,class_view_equal_mass=True,product='p_RGB * p_texture; conditional independence approximation, no posterior calibration claim',masks='original r03 masks exact',seeds='original r03 proxy UV and labels same all arms'),views={s:dict(fit=[DEV[s],AUX[s]],reserved=RES[s]) for s in SCENES},expected=dict(feature_views=12,texture_fields=24,models=12,predictions=48,ficus_matches=15),limits=dict(cpu=2,task_cap_gib=12,root_reserve_gib=1,hdd_reserve_gib=10,unit_seconds=300,round_minutes=40,wrap_JST='07:40',stop_JST='08:00'),downstream='C/D/NPR NOT_RUN',tuning=False,historically_exposed=True)
 js(R/'CONFIG.json',cfg)
 (R/'METHOD_FREEZE_ZH.md').write_text('''# r09：局部纹理布局提供的独立证据（结果前冻结）

## 实际评估 GO：独立证伪机制
已读r08 sealed状态/报告/更正，实看OVERVIEW、Ficus盆和头骨0036负例。r08已复核2712来源及seal/packages；当前HEAD6b99f520，diff/status干净。r08头骨阴影局部改善，但颜色比例丢失亮度后Ficus盆类0，未过上层精确门。v02主体身份/地台与Ficus盆吞干根因继续保留，不能换标签名称冒充解决。

本轮不再改变SH或单像素颜色，而检验**同样颜色的局部空间排列**。盆横向重复肋纹、细干的方向性、交织叶群可能提供附加证据；这只是待证伪的外观proxy，不是语义部件/物理表面。与r04/05的图传播不同：本轮不传播label，不设新硬seed，只在每个原像素周围从原source RGB计算局部描述子。RGB原三通道保留，绝不采用r08归一颜色替代原输入。无C8墨迹自证，无coreline/mvcore标签。

## 固定特征、四臂和公平null
s=min(H,W)/581。各RGB通道用sigma=s的高斯导数（truncate3）求梯度，并乘sigma作尺度归一；J=G_(3s)*(mean_channels grad I grad I^T)。t=Jxx+Jyy，f=(.5+.5*(Jxx-Jyy)/(t+1e-12), .5+Jxy/(t+1e-12),sqrt(t)/(sqrt(t)+.05))，三维范围0..1。前两量编码方向与相干性，第三量固定对比映射；.05与全部尺度此时冻结，不根据scene改。该方向在图像坐标，随camera roll协变，不宣称跨任意视角不变；透视缩短/薄干邻近背景/材质条纹都是预注册反例。边界反射padding，RGB有限；不从alpha或depth构造texture。

raw_rgb：精确r03 baseline。rgb_texture：原RGB类条件密度乘texture密度。rgb_scrambled_texture：原RGB因子保持，texture在固定seed1729、边长round(33s)非重叠方块内随机排列RGB三元组后的图像上计算；每个方块颜色多重集exact，但空间排列破坏。它会产生人为块间/块内高频，这是预先承认的null限制；不声称每个滑动中心patch统计完全相同。texture_only：同描述子独立密度诊断，检验是否只是纹理强分而非颜色辅助。

均用原r03每类每view相同UV/代理labels与原mask、不删seed或像素，无graph/height/K/new classifier family。两个3D密度均用16³hist、sigma.75bin平滑、class/view均等质量；组合采用乘积、按该组合的自身BUILD density5%分位设范围门，再用既有maxq>=.65/margin>=.2拒绝。RGB与梯度并非条件独立，乘积可能过度自信，故作为明确近似并设scrambled对照；不称校准概率。texture_only同门，raw必须与r03的模型及labels/q/d位级相等。

## 场景、执行顺序和停止门
三scene原source RGBC8输入关系不变：DTU官方native RaDe RGB/alpha/camera-z777x581，Ficus vanillaGS+CPU plane proxy800²；世界非米。C8核数458490/279616/285956仅历史输入数量引用，本轮不重新导出/改线/改source。DEV/AUX=0000/0024和train_r_80/train_r_7；reserved=0012/0036和test_r_14/test_r_79。全部历史曝光，DTU源GS训练视角，不称fresh blind。fit只两个BUILD，模型和BUILD图审后reserved统一一次推断，不反向选参数。

先TDD解析纹理和Ficus双BUILD，工程过则两个DTU同冻结方案，即使Ficus科学NO_GO仍完成预冻同机制低成本负对照；不在失败上游运行B/C/D新结构。目标12原生view texture缓存（原/扰乱共24）、12密度模型、48推断及Ficus四臂+r05共15组双向资格诊断。DTU还是两类peripheral-horizontal/central-nonhorizontal priors的A测试，不冒充前景语义；Ficus3proxy类。原v01C8/true joint、r05graph和r07DC为readonly强对照，不冒充新渲染。必要灰UNKNOWN保留，更多颜色/更少UNKNOWN不是成功。

A门是完整楼顶/窗/牙/颅与地台桌面分离；B门是Ficus盆干冠形体完整、枝叶空隙保留、至少2块共同可见身份稳定且不互吞。完整四图和0036/test14弱视角是必看；单薄干被局部窗口吞掉须负面呈现。匹配仍2p depth/1.5px cycle/3p world及旧分母/75%门，遮挡不负票。必须比同原RGB与scrambled控制呈现真实外形增益，不能只报seed分离/互配数。无GT，所有统计不是accuracy。

## TDD与资源
逐垂直slice RED→GREEN：恒色无结构、水平/垂直条纹同颜色多重集但tensor方向异、90度旋转协变与相干性不变、对称交叉纹理、finite/bounds、原RGB不变、blockshuffle exact multiset/确定性/非方画面、组合密度与RGB原样基线、reserved禁fit、UNKNOWN不当背景、不改变mask/sourceuv、伪标签不等GS ID。旧geometry/renderer只读不计新tests；本轮不新计算source核责任，旧CPU校准非官方CUDA。
CPU2，无GPU/训练/模型下载/mesh；单位300秒、本轮40分钟，ROOT12GiB/root1/HDD10门，07:40必须终验而非开新科学轮；08:00停止。源与旧12树/893Python哈希保护。只读replay精确复算texture/model/prediction/match，原静态seal/runtime分离，safe包、本地commit、r09状态后退出。本轮C/D/source软成员/NPR均冻结NOT_RUN，不新启动r10。
''')
 js(R/'METHOD_FREEZE.json',dict(utc=now(),method_sha256=sha(R/'METHOD_FREEZE_ZH.md'),config_sha256=sha(R/'CONFIG.json'),prior_commit=git(Path.cwd(),'rev-parse','HEAD'),before_new_science=True));review('00_texture_layout_GO','已有数据允许廉价局部纹理对照，与单像素颜色/SH和label图传播不同。阴影与颜色关联不是唯一信息，空间布局可被固定null破坏。许可仅TDD及三scene证伪，未授精确分块或NPR资格。',[R8/'REPORT_ZH.md',R8/'delivery/OVERVIEW.jpg',R/'METHOD_FREEZE.json']);status('FROZEN',children=[])
if __name__=='__main__':main()
