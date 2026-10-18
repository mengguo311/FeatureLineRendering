from env import *
def main():
 assert git(Path.cwd(),'rev-parse','HEAD')=='b22ade8691dc6a3de65ac0c97db1512280e0f655'
 prior=json.loads((R3/'ITERATION_STATUS.json').read_text());assert prior['round']==3 and prior['sealed'] and prior['next_allowed']
 for f,d in json.loads((R3/'RESULTS_MANIFEST.json').read_text())['members'].items():assert sha(R3/f)==d['sha256'],f
 assert not (R/'METHOD_FREEZE.json').exists();R.mkdir(exist_ok=True)
 for d in ['reviews','logs','literature']:(R/d).mkdir(exist_ok=True)
 js(R/'ROLLBACK_BEFORE.json',rollback());js(R/'RESOURCE_PREFLIGHT.json',guard())
 files=json.loads((R3/'SOURCE_MANIFEST.json').read_text())['files']
 for f in R3.rglob('*'):
  if f.is_file() and 'mplconfig' not in f.parts and f.name not in ['ASTRA_RUNTIME_FINAL.md','AGENT_LAUNCH.json'] and not f.name.endswith('.tar.gz'):files[str(f)]=sha(f)
 js(R/'SOURCE_MANIFEST.json',dict(files=files,read_only=True))
 cfg=dict(round=4,mechanism='screened harmonic coupling of frozen conditional-appearance unary with depth-qualified pixel adjacency and multiview links',views={s:dict(fit=[DEV[s],AUX[s]],reserved=RES[s]) for s in SCENES},
 arms=['coupled','no_cross','geometry_pair','unary_seeded'],
 unary=dict(source='r03 pooled_rgb exact frozen posterior and accepted labels',gamma='max(weighted_degree,1) * accepted * (qmax-qsecond) / (4*5^2)',diffusion_scale_px=5,no_new_density_fit=True),
 seeds=dict(source='r03 pooled_rgb stored seed_image, including DTU proxy seeds',hard_constraints=True,reserved_has_no_new_seeds=True),
 graph=dict(native_resolution=True,local_neighbors=4,max_world_distance_p=4,color_sigma=.12,color_floor=1e-5,cross_weight=.5,cross_z_p=2,cross_cycle_px=1.5,cross_world_p=3),
 target=dict(unary='own raw RGB through frozen r03 density output',transfer='frozen build probability via qualified projection, .5*edge affinity / target cross-degree',no_feedback=True,no_height_seed=True),
 output=dict(probability=.65,margin=.2,no_density_rejection_after_propagation=True,component_without_seed_or_unary_or_projection='UNKNOWN'),
 solver=dict(rtol=1e-8,maxiter=3000,same_system_LU_fallback=True,probability_tolerance=1e-5),
 comparisons=['r03 pure appearance','r02 pure propagation for ficus','r01 subject for DTU','v02 RGB-only for ficus','new unary_seeded exact hard-seed control'],
 gates=dict(ficus='complete pot/trunk/crown, pot highlight not wood, leaf holes unchanged; visible coherent regions and reserved agreement required; numbers alone insufficient',dtu='complete roof/cap/dark teeth, platform/table excluded; otherwise A fails and no B',downstream='C/D/NPR NOT_RUN; only joint evidence inference this round'),
 limits=dict(unit_seconds=900,total_minutes=65,cpu=2,cap_gib=12,wrap_jst='07:40',stop_jst='08:00'),threshold_tuning=False,historically_exposed=True)
 js(R/'CONFIG.json',cfg)
 (R/'METHOD_FREEZE_ZH.md').write_text('''# r04 冻结：让两种互补证据在同一个可拒绝图中约束

在核验r03封存、真实REPORT和全图/盆高光失败图后，GO执行本轮可证伪耦合；不授予精确分组成功。r02图传播较能维持盆的单一归属但无锚叶片大量UNKNOWN；r03条件外观能给断连叶和冠内木干证据，却把盆高光当木。新变量是**非局部外观一元项与真实depth合格邻接同时存在**，不是放宽边/旧门，也不是再调K/高度切点。保留原两个机制作为配对对照。

## 固定目标函数和尺度
每像素soft标签q，能量 E=Σ_(i,j) w_ij||q_i-q_j||² + Σ_i γ_i||q_i-u_i||²；构建种子固定onehot。u_i直接读取r03 pooled_rgb冻结posterior；仅r03已通过密度/概率拒绝门的像素接受一元项。c_i=maxq-secondq，γ_i=max(weighted_degree_i,1)*c_i/(4*5²)。5px是在均匀4邻接平面上选择的约5px扩散相互作用尺度，不从新scene图调参；颜色边和不规则度下不声称精确5px物理扩散半径。孤立节点有合格一元证据仍可赋类；没有种子/一元/投影证据的连通片UNKNOWN。
局部四邻接完整fx/fy/cx/cy反投影，距离<=4p；w=max(exp(-||RGB_i-RGB_j||²/(2*.12²)),1e-5)/max(d/p,1)，p=z/sqrt(fx*fy)。构建跨视角边严格复用r02门：depth差<=2p、反投影<=1.5px、world差<=3p，遮挡/画外非负票；双向候选去重并按跨边度归一，再乘.5。源核ID不构图，ink不参与候选。solver CG rtol1e-8/3000，不合格只可同矩阵LU修复，不改概率1e-5数值容差；最终max>=.65且margin>=.2才赋类。传播后的标签不再受原像素density硬门，否则无法检验邻接补足外观缺口；此改变明确属于联合推理，不是静默降低旧门。

## 配对臂与种子偏差
coupled=颜色成对项+合格跨view+外观一元；no_cross仅去构建跨边；geometry_pair仅去成对颜色权，但仍有r03颜色一元，不能叫完全无颜色。unary_seeded移除所有图边、仅相同一元与构建硬seed，是匹配seed夹持的便宜对照；r03本身不夹seed，二者必须分开。hard seed来自r03已保存seed_image，不补新人工或高度seed；Ficus来自r01粗内部，DTU来自局部方向/图像池的代理。它们可能错，尤其冠种子含木、DTU中心种子偏立面；不能当GT。相同seed/geometry/模型跨臂保留，任何看起来更纯的块若只是强迫seed必须揭示。
目标reserved没有新seed/高度信息，不更新构建图。固定r03自身外观一元加构建概率的合格回投软先验，后一项沿用r02 .5*edge affinity、按target投影数量归一；两项γ加和、prior按γ加权。no_cross仅构建阶段无跨边，目标仍可从两独立图转移；unary_seeded目标不转移，以隔离图系统整体作用。目标RGB/depth只固定推理。禁止改变subjectmask/填洞。

## 真实范围、图与门
优先Ficus DEV/AUX端到端并查看图，再同冻规则运行DTU和reserved。DTU A尚NO_GO，本轮是新联合主体候选诊断；不输出其部件。Ficus A只继承孤立alpha主体proxy，B比较盆沿/亮纹/土、裸干、冠内木干、薄叶/负空间。若盆线更纯却吞叶、木干断掉或UNKNOWN掩盖大错，精确B仍NO_GO。DTU必须保灰屋顶/亮颅顶/暗牙颌同时去地台/桌面，不能把红墙色当整栋楼。
DEV/AUX scan24/65 0000/0024，Ficus train_r_80/train_r_7；reserved0012/0036及test_r_14/test_r_79。全历史曝光，DTU源GS训练图，不叫blind/GS-heldout。原C8+joint图只读展示，source/line所有属性不动；新区域颜色是图像诊断，不是GS编辑。DTU nativeRaDe camera-z与Ficus vanilla+CPU条件plane代理分别标记。参照r02统一可见门再测相互配对，但视觉全图是主门，不以UNKNOWN下降或配对数充当正确率。
本轮C线边界、D source责任、NPR预冻NOT_RUN。原高斯/线核不生成、不删、不训练；若上层真局部GO，下一次resume才可独立冻结责任/线门。3scene每4图英文全frame原RGB/C8/真joint/原单机制/耦合和反例。无额外新视角、无模型下载。

## TDD与停止
先RED再GREEN：无seed的断连节点可由独立一元驱动，无任何锚仍UNKNOWN；短假颜色带在同surface邻接下可修正，深度断边不桥接；硬seed与unary冲突必须记录；geometry_pair仍有颜色unary；权重统一缩放不改变解；二/三类/全空/孤立、概率SPD系统/行和/固定ID、遮挡不负票、目标无heightseed、mask孔洞保留；既有投影函数复用并记录相同SHA，不冒算新测试。每unit900秒、轮65分钟，CPU2/总12GiB/root1/HDD10，阶段资源核验。一次配置，不科学调参；工程修复同轮留负记录。07:40后只收尾，08:00停止。本次r04封存并退出，无自动r05。

## 文献边界
沿用实读Grady2006作者全文的seeded Laplacian/Dirichlet图推理，以及GrabCut2004§2–3条件外观。新增一元screening、跨视角资格和自动代理seed是本任务组合，不声称论文已提供自动多部件NPR。两篇已封存正文可复查，未下载模型。
''')
 js(R/'METHOD_FREEZE.json',dict(utc=now(),config_sha256=sha(R/'CONFIG.json'),method_sha256=sha(R/'METHOD_FREEZE_ZH.md'),prior_commit=git(Path.cwd(),'rev-parse','HEAD'),before_new_results=True))
 review('00_mechanism_GO','r03真实全图和盆面负例表明一元与邻接有互补缺陷，允许新联合推理证伪。先Ficus构建图；DTU只主体候选，不越门。参数由解析5px扩散尺度冻结，不看新图调权。',[R3/'REPORT_ZH.md',R3/'delivery/OVERVIEW.jpg',R3/'delivery/ficus_train_r_80_FAILURE.jpg',R/'METHOD_FREEZE.json'])
 status('FROZEN',children=[])
if __name__=='__main__':main()
