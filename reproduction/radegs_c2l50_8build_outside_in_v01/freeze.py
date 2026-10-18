from env import *
import urllib.request
p=ROOT/'literature'/'grabcut2004.pdf'
try:
 with urllib.request.urlopen('https://pub.ista.ac.at/~vnk/papers/grabcut_siggraph04.pdf',timeout=30) as r:p.write_bytes(r.read())
 subprocess.run(['pdftotext','-layout',str(p),str(p.with_suffix('.txt'))],check=True)
except Exception as e:js(ROOT/'literature'/'GRABCUT_ACCESS_ERROR.json',dict(error=str(e)))
config=dict(pilot_count=1,scenes=SCENES,DEV=DEV,AUX=AUX,reserved=RESERVED,scientific_input='original arms/C only',historically_seen=True,threads=2,task_cap_bytes=8*2**30,
 stageA=dict(algorithm='automatic border/central appearance seeds + iterative RGB Gaussian-mixture grid cut; depth only pairwise',border_fraction=.02,palette_bins=8,palette_min_border_fraction=.10,bg_seed_color_distance=.16,fg_seed_color_distance=.22,seed_rx=.18,seed_ry=.26,seed_x_shifts=[-.025,0,.025],seed_y=.5,min_seed_pixels=32,gmm_components=5,gmm_covariance_type='diag',gmm_reg_covar=.001,gmm_max_iter=40,gmm_sample_budget_per_class=12000,outer_iterations=3,random_seed=1729,unary_clip=20,pair_gamma=2,pair_color_sigma=.08,pair_depth_sigma_worldpixels=3,pair_unknown_depth_factor=1.,capacity_scale=1000,hard_seed_cost=1000,alpha_background=.02,alpha_reliable=.5,alpha_seed=.8,near_clip=.2,uncertain_unary_margin=.5,rgb_alpha_control_distance=.15,depth_connected_control_neighbor_worldpixels=4,depth_connected_seed_radius_fraction=.04,no_hole_fill=True,no_component_removal=True,no_absolute_depth_cut=True),
 calibration=dict(rgb_MAE=.02,alpha_MAE=.02,center_vs_native_depth_p95=.15,allN_atol=2e-12,query_render_atol=5e-7,allN_pixels_per_view=12),
 A_gate=dict(seed_engineering_required=True,nonempty_fraction_range=[.01,.98],seed_consensus_IoU_min=.90,unknown_in_possible_subject_max=.15,transfer_visible_min=.20,transfer_inside_min=.90,visual_required=['complete visible subject; no loss of roof/walls, cap/teeth, leaves/branches/pot','no large remote background/table included as subject','negative space preserved; no filling leaf gaps or treating socket cavity as proven background','stable overall extent in DEV/AUX; reserve failures veto downstream'],not_GT=True),
 transfer=dict(pixel_stride=4,depth_tolerance_relative=.01,depth_tolerance_worldpixels=6,target_mask_dilation_pixels=1),
 stageB=dict(conditional_on_A=True,grid_marker_spacing_fraction=.06,boundary_RGB_sigma=.08,boundary_depth_worldpixels=6,merge_levels=[.5,1.,2.],minimum_major_area_fraction=.015,max_major_regions=12,required_transfer_inside=.75,required_view_support=2,no_physical_plane_claim=True),
 stageC=dict(conditional_on_B=True,arms=['original_C8','shifted_C8_12px','no_lines'],boundary_samples_per_region=128,max_regions=12,support_distance_pixels=2,visible_only=True,minimum_original_minus_shifted_support=.10,no_subject_from_ink=True),
 stageD=dict(conditional_on_C=True,soft_source_only_alpha_T=True,unknown_unobserved=True,never_modify_source=True),
 visual_review=dict(per_scene_before_reserved=True,max_DEV_parameter_revisions=0,wholeframe_only_before_A_GO=True,ROI_after_failed_A='explanatory failure crop only, never selection or lower grouping'),
 stop=dict(per_unit_seconds=900,scientific_fail='stop formal dependent stages; frozen controls and failure diagnostics permitted',engineering_fail='keep logs; fix prerequisite without loosening tolerance',after_one_pilot=True))
assert not (ROOT/'CONFIG_FREEZE.json').exists();js(ROOT/'CONFIG_FREEZE.json',config)
text='''# 从外到内的区域优先实验大纲（真实结果前冻结）

本文件是执行方案，不是结果。一次三场景有界pilot；不自动迭代三轮。同一执行上下文亲自评估，不委派其他模型。launcher身份元数据不能代替真实运行证据。

## 问题与研究判断

用户希望先完整主体，再大形体，最后解释窗格、眼眶、叶缘。原C8短parent端点图不能可靠形成大框架：前轮建筑13个墨迹白区仅2个不合格图候选；源GS责任分区跨视角合格面片0。二者不证明没有物体或面片。新假设是**全画面源图的区域先验能否提供足够稳定的主体框架，再让原线作为边界证据**。本轮不改原线、填闭环、删毛刺或改源GS。

Arbeláez等2011 §3–4用局部亮度/颜色/纹理与谱全局化，OWT初分区及UCM层级合并；高层只留强边界。但gPb组合权重由BSDS训练，区域不自带物体语义。我们只借鉴区域层级和门槛顺序，不声称复现gPb/OWT-UCM。[作者全文](https://www2.eecs.berkeley.edu/Research/Projects/CS/vision/grouping/papers/amfm_pami2010.pdf)

Zhou/Friedman/von der Heydt2000实验说明同一局部边缘的归属受远处上下文影响，且并非对所有线索不变。它是生理证据，不是自动分割算法或本数据的GT。[原论文](https://pmc.ncbi.nlm.nih.gov/articles/PMC4784717/)；出版PDF访问失败，网页检索返回的正文已读取，访问状况另存，不声称已取得PDF全文。

GrabCut2004 §2–3把颜色区域模型和对比敏感相邻约束共同优化，依赖用户给出的初始背景/框。这里以自动外围颜色与中央弱种子替代交互，其错误必须由全图gate发现；无border matting，没有语义保证。[作者全文](https://pub.ista.ac.at/~vnk/papers/grabcut_siggraph04.pdf)

Gaussian Grouping2024 §3.2先SAM区域、零样本tracker跨视角关联，再训练16维Identity Encoding及空间约束，使用alpha*T渲染。不能省掉这些监督后把原核ID当物理面。本任务不下载SAM、不训练编码，只在上层合格后允许有限责任映射。[ECCV全文](https://www.ecva.net/papers/eccv_2024/papers_ECCV/papers/04195.pdf)

Elder/Zucker和Wang闭合只能给既有边界假设评分，不能认证主体/物理面，继承前轮已核验来源；本轮不以闭合驱动主体。

## 输入、相机及对象范围

唯一线输入原c2l50_multiview05_v01/arms/C：实读scan24/scan65/ficus 458490/279616/285956核。源原PLY/full SH/filter/opacity只读；DTU为native RaDe，Ficus为vanilla GS+CPU covariance-plane depth代理。完整fx/fy/cx/cy、W2C、整数像素中心，非米；DTU777×581，Ficus800×800。source_index与line primitive_id分离。多数原parent单来源，不把多次投影当独立线观测。

DEV=0000/0000/train_r_80；AUX=0024/0024/train_r_7；reserved=0012/0036和test_r_14/test_r_79。所有视角历史曝光，DTU是源GS训练视角，不叫blind/GS-heldout。reserved结果不改参数。本轮零DEV调参轮；工程修错保留失败日志，不放宽门。

scan24范围是主体建筑及近处屋顶墙体，远处场景背景或UNKNOWN；scan65整个颅骨、牙齿及内部孔洞；Ficus盆、枝叶和薄叶。全scene alpha不是主体mask。输入审计显示DTU大部分alpha接近1且背景也有深度，Ficus多数背景alpha0，故不能拿同一alpha阈值宣称全场景语义成功。禁止p20/1.15 z硬裁切或全局max depth裁主体。

## Stage A：完整主体代理先验（首先真正运行）

1. 原生float32 RGB不变，不读C8墨迹构造mask。外围2%像素的8³ RGB箱取最多箱中位颜色作为背景外观假设；占比不足10%拒绝初始化。只在外围与该颜色距离<.16、以及颜色相似的alpha<.02像素设背景种子，不把所有边框设背景。中央归一椭圆半轴.18/.26中与背景距离>.22且alpha>.8/有效深度的像素作弱前景种子。种子不是人工GT，中心外主体不被裁掉；无种子则ENGINEERING_NOT_READY。
2. 原图RGB的前后景各至多5个对角GMM，3次区域重新估计/图cut。每类最多12000等间隔样本，reg=.001、最多40 EM步、seed1729。此为本图无监督外观拟合，不是GS或外部模型训练。
3. 原尺寸4邻接图，E=ΣD_RGB(label)+2Σ[label_i≠label_j]exp(−||RGB_i−RGB_j||²/(2*.08²))exp(−j_z²/(2*3²))。j_z=|z_i−z_j|sqrt(fx fy)/mean(z_i,z_j)；只有双方可靠深度才用第二因子，否则为1并标未知。它只影响接续，不对整幅z排序截断主体。真实斜面也可能减弱接续，不能认作遮挡GT。cost×1000整数量化，hard seed1000，unary截20；保证不把负log似然直接变负容量。
4. 三个固定中央种子x=.475/.5/.525运行同配方；主候选为中心版本，三版本交/并和unary margin<.5、低alpha/无深度构成不确定账本。绝不填洞、去小连通域、只留最大组件或强连枝叶。颜色模型与中央先验可能遗漏灰屋顶/褐枝干或卷入桌面，必须显式判负。
5. 同图对照：alpha>.5全scene覆盖；RGB偏离背景>.15且alpha>.02；纯源深度的中央连续层flood（邻接≤4 world-pixel，中央.04尺度种子、无RGB或global-z cutoff）。后三者不是语义GT。

工程gate：同renderer source fullSH RGB/alpha vs冻结缓存MAE≤.02，center/native深度相对p95≤.15；两深度仍不等价。每视角12有限贡献像素全N精确校准atol2e-12，query对整图5e-7。完整C8 xray和source+ink统一排序联合渲染仅作上下文，不给自己投票。

A验收：非空非全幅（面积.01–.98仅sanity）、种子变动交并比≥.90、候选内unknown≤.15；DEV/AUX投影可比率≥.20、可比位置在另一候选内≥.90。visibility用冻结raw depth/alpha，tol=max(.01z,6z/f)，遮挡、画外和未知不反对。每4px采样、目标1px栅格容差，不用IoU证明身份。另必须全图视觉通过：完整主屋顶墙体/颅盖牙齿/盆枝叶，没有大块远背景或桌面误入，不填负空间。数值通过不能覆盖视觉失败。reserved按同冻结规则运行一次，其明显失败否决升级；若DEV失败reserved仅失败机制诊断。

## Stage B/C/D 条件性执行（未通过上层绝不启动正式下层）

B仅A合格场景：主体mask内用原RGB/depth梯度的marker watershed与邻接图构建区域层级；标记间距.06×短边。共同RGB .08、depth6p归一，固定合并尺度.5/1/2；统计大区域≥主体1.5%、最多12个。输出nested regions/holes/open/UNKNOWN，不等同物理平面；跨相机可见投影归入同大区≥.75且至少2相机，整体部件视觉不破坏才GO。若不能形成可辨认的大块而只有颜色碎片则NO_GO。

C仅B合格：原C8/平移12px C8/无线路径，最多12区域×128边界点、距离2px、相同可见ROI上限。线只加边界支撑，不产生主体mask；原线相对移位支持至少+.10且完整结构可读、无伪闭合才允许升级，实际预算分别报。

D仅C合格：只读source alpha*T到软区域/UNKNOWN，在保留视角预测区域外形/层，不要求源ID绝对稳定，不写源PLY、不称恢复真实primitive。否则D=NOT_RUN，不用全UNKNOWN文件冒称已分区。

## TDD、可复核和停止

每功能先真实RED再最小实现GREEN：空种子拒绝、破碎主体/薄叶不去组件、孔洞不填、覆盖不是主体、边框主体不强设背景、画外/遮挡UNKNOWN、rolling轮廓不强制固定线、完整相机回投/尺度、层级包含、source ID≠line ID、上层失败禁下层、mincut小图枚举能量、源/ink统一排序和全N责任。原源码/893Python/HEAD/index/status/hash前后核验。新代码、配置、每unit封存；readonly verify复算mask/指定camera/source hash不重写结果。

2 CPU，root≥1GiB/HDD≥10GiB/task≤8GiB。每unit900s有界、阶段实时查；单scene故障不吞其它。一次pilot后停；不训练GS、无GPU/mesh/新模型/正式NPR或新线资产。若A失败，交付足够全图及失败机制而非局部漂亮区域。

预计图：每scene4原尺寸相机，原source RGB/原C8 xray/true joint/深度alpha；主体候选+UNKNOWN、RGB/alpha/深度连续层对照、三种子分歧；DEV→AUX/reserved投影可比图。上层失败可做清楚标注的解释性放大，不做ROI选线。English标题、Chinese报告；所有NOT_RUN单独列出。封存ASTRA_FINAL与runner运行文件分离，AGENT_LAUNCH不进静态manifest。
'''
assert not (ROOT/'OUTLINE_ZH.md').exists();(ROOT/'OUTLINE_ZH.md').write_text(text)
js(ROOT/'PLAN_SEAL.json',dict(utc=now(),before_any_new_segmentation=True,members={n:dict(sha256=sha(ROOT/n)) for n in ['CONFIG_FREEZE.json','OUTLINE_ZH.md','INPUT_AUDIT.json','SOURCE_MANIFEST.json']}))
review('01_design_GO','GO：已读取层次分割正文及源数据，允许执行Stage A工程TDD及3scene DEV完整主体候选。先比较背景/区域先验；不采用线端点造主体。A失败的scene下层NOT_RUN，视角规则不更改。', [ROOT/'OUTLINE_ZH.md',ROOT/'CONFIG_FREEZE.json',ROOT/'INPUT_AUDIT.json'])
state('PLAN_FROZEN')
