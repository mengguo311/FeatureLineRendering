from env import *
def main():
 assert git(Path.cwd(),'rev-parse','HEAD')=='dca2ebd9fb0997b9a384fa9734dc4d11832d4b67'
 prior=json.loads((R1/'ITERATION_STATUS.json').read_text());assert prior['round']==1 and prior['sealed'] and prior['next_allowed']
 for f,d in json.loads((R1/'RESULTS_MANIFEST.json').read_text())['members'].items():assert sha(R1/f)==d['sha256'],f
 R.mkdir(exist_ok=True);(R/'reviews').mkdir(exist_ok=True);(R/'logs').mkdir(exist_ok=True)
 js(R/'ROLLBACK_BEFORE.json',rollback());js(R/'RESOURCE_PREFLIGHT.json',guard())
 files=json.loads((R1/'SOURCE_MANIFEST.json').read_text())['files']
 for f in R1.rglob('*'):
  if f.is_file() and 'mplconfig' not in f.parts and f.name not in ['ASTRA_RUNTIME_FINAL.md','AGENT_LAUNCH.json'] and not f.name.endswith('.tar.gz'):files[str(f)]=sha(f)
 js(R/'SOURCE_MANIFEST.json',dict(files=files,read_only=True))
 cfg=dict(round=2,mechanism='seeded multiview harmonic propagation on source-only visible pixel graph',
  views={s:dict(fit=[DEV[s],AUX[s]],reserved=RES[s]) for s in SCENES},
  graph=dict(native_pixels=True,local_neighbors=4,world_edge_limit_p=4,color_sigma=.12,minimum_weight=1e-5,cross_weight=.5,cross_z_tolerance_p=2,cross_cycle_pixels=1.5,cross_world_p=3),
  seeds=dict(r01_fixed_height_intervals=True,central_fraction=.5,min_distance_to_alpha_edge_px=2,max_per_region_per_view=2048,selection='deterministic equal linear indices'),
  solver=dict(type='Dirichlet harmonic / random walker',rtol=1e-8,maxiter=3000,probability=.65,margin=.2,unseeded_components='UNKNOWN',no_seed_repair=True),
  arms=['joint_rgb','independent_rgb','joint_no_rgb'],target_rule='frozen DEV/AUX probabilities as soft Dirichlet neighbors; no target height seeds, no feedback to build',
  dtu_diagnostic=dict(offset_px=2,normal_qualification_max_neighbor_p=8,planarity_max_p=2,upright_angle_deg=20,formal_subject_output=False),
  gates=dict(keep_subject_mask_exact=True,minimum_visually_coherent_parts=2,pot_rim_trunk_separate=True,leaf_open_spaces_preserved=True,unknown_never_deleted=True,improvement_over_no_crossview_required_for_multiview_claim=True),
  max_unit_seconds=900,round_minutes=70,reserved_historically_exposed=True,downstream='C/D/NPR NOT_RUN this round; precise B boundary test only',threshold_tuning=False)
 js(R/'CONFIG.json',cfg)
 text='''# r02 方法冻结：可信粗块内部→多视角受边界约束传播

这是读取 r01 封存与实图后的实际自评，冻结在 r02 新结果之前。r01 的部件内部已有收益，但高度切面把盆沿/土面划给干层；相同世界高度自然产生高配对数，不能认证语义。建筑方向资格挡住立面却无地台，头骨方向正确但桌面残片仍混入。本轮不改高度切点、不调 K 或旧平面阈值。

## 允许的下一步与科学区别
Ficus B GO 执行**传播试验**，不是授予精确分块 GO。以 r01 两个固定切点各区间中间50%高度、距alpha边缘>=2px的原可见像素为保守种子，每view/label最多2048，确定性等距索引。种子只是粗层先验，不是人工GT；叶冠含高枝本就不是木/叶语义。只用DEV train_r_80 与AUX train_r_7。两个真实图的原RGB、camera-z、alpha形成联合像素图，无C8 ink输入，无source核ID当对应。与v01泛颜色graph-cut/网格watershed不同：固定粗形体内种子、显式可见回投约束进入生成阶段、求soft调和场而非最小割或再聚类。

每view原尺寸alpha>=.5且finite z>.2像素为节点，四邻接；邻接world距>4个worldpixel代理则断开。有效边权 exp(-||RGBi-RGBj||²/(2*.12²))/max(world距/p,1)，下限1e-5只用于已通过几何的边。跨view必须target z差<=2p、反投影cycle<=1.5px、世界差<=3p，遮挡/画外/不一致不构图也不负票。跨边权同颜色规则乘.5并按端点跨边度归一，消除重复采样加权；这仍是同GS两视角证据，不是两份独立物理真值。最小化sum wij||qi-qj||²，种子Dirichlet固定onehot，连通分量无种子则UNKNOWN，不补种。CG rtol1e-8、最多3000，未收敛为工程INVALID；标签max>=.65且margin>=.2，其余UNKNOWN。

主臂 joint_rgb；同预算seed/原像素/几何门的 independent_rgb（去跨边）与joint_no_rgb（只去颜色权），旁列r01原层/等三分及v02 RGB-only原图。比较是否真正改善盆沿/枝冠交界，而非只让图更稀疏。三个臂的保留图都只能把DEV/AUX冻结的soft概率，经合格投影作为软Dirichlet邻接传播到目标；目标无高度seed、不回传更新构建图。independent臂的目标使用其独立训练图概率，同样可见传递，因而仅隔离构建阶段跨视角耦合，不谎称目标完全无多视图信息。目标RGB/depth仅用于固定推理，无调参/拟合新身份。未见表面可UNKNOWN，不能高度填色冒充新观测。

## DTU上层失败机制诊断（不造多块）
scan24/65 A 继续NO_GO，不执行B/C/D。实际四相机计算原浮点depth的2px中心差分法线候选，完整K/W2C；九点邻域均有效、邻距<=8p、拟合切平面残差<=2p才记录，最短cov轴不参与。比较方向<=20°共同up的可见局部支撑与旧外围采样、r01平面资格/残差：是否存在方向合格的局部台面而外围单平面池未代表它。只是normal/层观测诊断，不当真表面、不输出新subject或物理plane。不改变台面门槛，也不以此偷偷进入B。

## 相机、真对照和验收
DTU DEV/AUX=0000/0024，reserved0012/0036；Ficus DEV/AUX=train_r_80/train_r_7，reserved test_r_14/test_r_79。全部历史曝光，DTU原GS训练图，非blind。DTU native RaDe，Ficus vanilla+CPU条件平面depth代理，世界单位非米。原source/C8真正统一排序joint只读参考；本轮区域色是诊断覆盖图而非新GS/NPR渲染。
主视觉门：完整alpha主体/负空间逐像素保持；盆沿不吞干、裸干不吞叶簇、至少2真正可读粗块且4视图身份一致；UNKNOWN不能隐藏被错分结构；保留图未经新seed仍可辨识。相对去跨视角对照无收益则不能宣称多视角增益。若传播失真或种子不可靠，B NO_GO，保留全部结果。C线边界/D源责任/NPR本轮预定NOT_RUN，不跳门。DTU只有机制诊断，不能算完成分块。

## TDD / 时间 / 源保护
先RED再GREEN：孤立无seedUNKNOWN、硬seed/概率和/边界阻抗、同色不保证一物体、前后遮挡不连接、完整K循环、薄叶无填洞、相机ID置换不改身份、去跨边消融真实、未观测目标无height强赋、概率软传递、局部plane斜率/step资格。原source/ink排除由数据入口和来源hash验证，不宣称已测试GS责任。单unit900s、轮70min、CPU2、12GiB/root1/HDD10GiB门。最多本冻结一次配置，无科学调参；数值工程失败可同门修复并保留日志。07:40后只收尾。全图+局部失败图、source/旧893py/12树核验、只读replay、seal、local commit后退出，runner决定下一轮。

## 已读依据与复现边界
Grady 2006《Random Walks for Image Segmentation》作者公开全文 https://leogrady.net/wp-content/uploads/2017/01/grady2006random.pdf ，实际核读§III A/B、Eq1、8–12。该方法以种子和加权图求到达标签概率，非自动语义识别。本轮跨视角边、几何门和自动粗层种子为自定义适配，不是论文现成多视角NPR算法。下载首次TLS失败，公开PDF仅本次curl -k获取，文件hash记录；web工具亦超时。不涉及认证或全局TLS修改。
'''
 (R/'METHOD_FREEZE_ZH.md').write_text(text)
 js(R/'METHOD_FREEZE.json',dict(utc=now(),config_sha256=sha(R/'CONFIG.json'),method_sha256=sha(R/'METHOD_FREEZE_ZH.md'),prior_commit=git(Path.cwd(),'rev-parse','HEAD'),no_new_scientific_result_yet=True))
 js(R/'SOURCES.json',dict(primary=[dict(title='Random Walks for Image Segmentation',author='Leo Grady',year=2006,url='https://leogrady.net/wp-content/uploads/2017/01/grady2006random.pdf',read_sections=['III.A','III.B Eq 8-12'],sha256=sha(R/'literature/grady2006random.pdf'),access='curl default TLS failed; public curl -k succeeded; no global setting change')]))
 review('00_preflight_GO','GO：r01 seal核验通过，旧树/source保护正常。Ficus粗结构内部可作有风险种子，允许界面传播证伪；DTU仅局部深度方向诊断，不授予主体门。无新结果已生成。',[R1/'REPORT_ZH.md',R1/'delivery/FICUS_RIM_test_r_79.jpg',R/'METHOD_FREEZE.json'])
 status('FROZEN',children=[])
if __name__=='__main__':main()
