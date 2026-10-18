from env import *
def main():
 prior=json.loads((ROOT/'r10_prior_verify.json').read_text());assert prior['manifest_verified'] and prior['packages_verified']
 st=json.loads((R9/'ITERATION_STATUS.json').read_text());assert st['sealed'] and st['round']==9 and st['next_allowed']
 assert git(Path.cwd(),'rev-parse','HEAD')=='e4f868cff7b97512339fe85e5020d10fbb4db925'
 assert not (R/'METHOD_FREEZE.json').exists();R.mkdir(exist_ok=True);(R/'logs').mkdir();(R/'reviews').mkdir()
 js(R/'ROLLBACK_BEFORE.json',rollback());js(R/'RESOURCE_PREFLIGHT.json',guard())
 src=json.loads((R9/'SOURCE_MANIFEST.json').read_text())['files']
 for p in R9.rglob('*'):
  if p.is_file() and p.name not in ['AGENT_LAUNCH.json','ASTRA_RUNTIME_FINAL.md','ASTRA_RECOVERY_RUNTIME_FINAL.md'] and 'mplconfig' not in p.parts and not p.name.endswith('.tar.gz'):src[str(p)]=sha(p)
 for p in (CODE.parent/'round09').glob('*'):
  if p.is_file():src[str(p.resolve())]=sha(p)
 js(R/'SOURCE_MANIFEST.json',dict(files=src,read_only=True))
 cfg=dict(round=10,mechanism='finite alpha-supported normalized convolution, not texture scale/classifier tuning',new_arms=['alpha_texture','shifted_alpha_texture'],readonly_baselines=['r09/raw_rgb','r09/rgb_texture','r05/withdraw_conflict','v02/RGB-only'],support=dict(weights='original finite alpha clipped [0,1], invalid alpha ->0, no object-segmentation claim',derivative='d(N/D)=(dN*D-N*dD)/D^2; N=G_s(wI), D=G_s(w)',tensor='G_3s(w * grad(I_norm) outer grad(I_norm))/G_3s(w)',scale='min(H,W)/581',sigma=1.,integration_sigma=3.,truncate=3.,numerical_denom_min=1e-6,unknown='original inference mask unchanged; unavailable normalized feature -> UNKNOWN; any unavailable BUILD seed refuses arm, never silently drops seed',null='cyclic horizontal roll of alpha by round(3*s) pixels, exact weight multiset; same RGB; wrap seam disclosed'),density=dict(same_r09=True,bins=16,sigma=.75,quantile=.05,posterior=.65,margin=.2,equal_class_view_mass=True),views={s:dict(fit=[DEV[s],AUX[s]],reserved=RES[s]) for s in SCENES},expected=dict(new_feature_views=12,new_models=6,new_predictions=24,new_ficus_matches=6,readonly_match_controls=9),limits=dict(cpu=2,cap_gib=12,unit_seconds=300,round_minutes=35,wrap_JST='07:40',stop_JST='08:00'),downstream='C/D/source membership/NPR NOT_RUN',tuning=False,historical_exposure=True)
 js(R/'CONFIG.json',cfg)
 (R/'METHOD_FREEZE_ZH.md').write_text('''# r10：观测支撑归一化能否避免把背景当作部件纹理（真实结果前冻结）

## 实际GO评估与不同机制
已核读r09状态/报告及总览、test14盆/干负例，重读v02冻结/报告/A/B门并实看主体总览和Ficus K3/K5/RGB-only全图。r09封存独立验证完成；当前HEAD e4f868cf，旧源码和来源受保护。r09真实texture让代理种子更可分，却使完整盆缘UNKNOWN、冠内木类丢失。不能从该现象断言背景混入是唯一原因。本轮只检验一个新的观测域机制：梯度和张量积分是否受到无有效source覆盖像素的干扰。它不同于换sigma/K/颜色、图传播或明暗归一化。

主臂w=原source alpha有限值裁到[0,1]，非有限置0并记录。alpha是全scene覆盖，不是物体语义mask；DTU台面/建筑地台同样有alpha，预计不能因此解决主体身份。Ficus孤立覆盖较有诊断价值，但RGB边缘已含背景混合，归一化也不等于去混色。没有新语义模型、手工mask、原核编辑或C8墨迹自证。

## 数学与冻结对照
s=min(H,W)/581。N=G_s(w I)，D=G_s(w)，归一梯度为s*(dN*D-N*dD)/D²，分别求x/y和RGB通道。将梯度外积以w加权、G_(3s)积分并除以G_(3s)(w)。其余三维编码与r09完全相同，0.05能量常数、truncate3不变。原mask完全不缩、不侵蚀、不填洞、不删薄枝。D及积分支撑分母都>1e-6才有数值资格，否则该像素UNKNOWN；这个epsilon是数值门，不是已校准几何置信。全1支撑须恢复r09特征至1e-10浮点容差，零支撑不得捏造texture。

两新臂alpha_texture、shifted_alpha_texture。null只把w向右循环平移round(3s)像素，精确保留全图支撑权重多重集和总质量；RGB与原构建seed UV/labels不变。这一有限错位仍与原mask部分相关，且画边有循环接缝，不称随机语义null；其目的检验局部对齐，不是证明主臂比任意错误mask都好。若任一BUILD原seed无数值资格，该arm记录工程/证据REFUSED，不删seed或悄悄补值。原像素推断mask与原RGB因子完全相同，归一特征无资格则UNKNOWN，所有拒绝计入完整分母。

比较只读r09 raw_rgb、无条件rgb_texture和r05图传播、v02 RGB-only。只计6个新密度模型、24新预测、12特征view缓存，Ficus6组新双向资格；r09/r05九组匹配只读引用不冒充新运行。分类器16³hist/.75bin平滑/每类视角均等质量/自身5%密度门/.65后验/.2margin全不变，RGB×texture独立近似仍可能过度自信。不是新阈值搜索。

## 相机、原输入及执行门
scan24/65 native RaDe RGB/alpha/depth777x581，Ficus vanillaGS+CPU plane proxy800²，世界非米。DEV/AUX=0000/0024或train_r_80/train_r_7；reserved0012/0036、test_r_14/test_r_79。所有历史曝光、DTU为源GS训练视角，不是blind。新拟合只两BUILD；reserved在BUILD图审后一次运行，不修改规则。旧C8 arms/C、source和joint只读，全部完整SH/filter/Inf/几何保持；本轮无新source渲染、source责任或NPR。

先真实RED→GREEN：同一薄前景换背景归一特征不变、无条件特征会变；全1支撑等价、恒色边界零纹理、空支撑UNKNOWN、soft权重倍乘一致、错位权重多重集、非方形、无输入改动及finite检查。然后Ficus双BUILD端到端；若解析反事实失败先工程INVALID，修复相同定义而不改门。若工程通过而科学差，可继续已冻结DTU负对照和一次reserved诊断，绝不推进失败上游的正式大块/NPR。

A须完整楼顶/窗/牙/颅且分离地台桌面；B须盆/干/冠完整且跨相机可比身份稳定，至少两块资格不能替代视觉门。特别检查边界削弱是否丢薄叶/盆轮廓，UNKNOWN降低/像素数变化不作成功。DTU A若失败B/C/D NOT_RUN；Ficus B不过C/D NOT_RUN。对缺失支持、低alpha、循环null接缝保存全图及证据，不能把较少墨或灰色区当更精确。

两CPU、全任务12GiB/root1GiB/HDD10GiB，300秒每unit/35分钟本轮，07:40进入收尾、08:00硬截止。逐unit原子seal，可恢复，不覆盖旧结果。源码/配置预冻结、所有新数组readonly精确复算，原893Python及12树/来源hash再核；本地commit不push/merge。runtime排除静态manifest。此调用只r10，封存并退出，不开r11。
''')
 js(R/'METHOD_FREEZE.json',dict(utc=now(),method_sha256=sha(R/'METHOD_FREEZE_ZH.md'),config_sha256=sha(R/'CONFIG.json'),prior_commit=git(Path.cwd(),'rev-parse','HEAD'),before_new_science=True))
 review('00_support_domain_GO','允许归一观测域的廉价可证伪诊断。解析薄物体换背景和全1等价须先过；不预认alpha为主体/纹理归一为分块。所有数值和失败门在真实数据前锁定。',[R9/'REPORT_ZH.md',R9/'delivery/ficus_FAILURE_ROI.jpg',V2/'REPORT_ZH.md',R/'METHOD_FREEZE.json'])
 status('FROZEN',children=[])
if __name__=='__main__':main()
