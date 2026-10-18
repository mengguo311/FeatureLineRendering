from env import *
rd=ROOT/'round2';assert json.loads((rd/'COUNTS.json').read_text())['model_comparisons']==88
(rd/'ROUND2_REPORT_ZH.md').write_text('''# 第二轮：有限责任软sheet partition

科学NO_GO：原线没有通过双视角面片资格，也没有优于same-budget null。不扩大ROI、不进入正式NPR编辑。工程运行通过，不是ENGINEERING_INVALID。

实际3scene、11有效case、DEV+AUX两相机、4臂=88组局部模型。原线22组中19 REFUSED、2 single、1 two；几何轴18拒绝/3单片/1双片；移位21拒绝/1单片；打乱19拒绝/3单片。跨视角原线0、几何轴0、移位0、打乱1（scan65 cap_marks 单片，source责任重叠0.3909、normal差13.40°、对称面距0.488p）。这是反证：局部平面可由源几何与采样布局解释，不是线身份特有证据。

具体：建筑屋檐R1中位深度看似两侧，但全部条件source/pixel假设的左片RMS1.574p、右片1.273p，均未过冻结1p；单片2.824p。不能由此断言屋檐无物理面，仅说明当前贡献混合proxy不能认证。头骨cap_marks在0000为single、0024为two，身份/模型数不稳定；颅盖接缝两视角仍拒绝。Ficus薄叶DEV有single、AUX拒绝，DEV仅原查询责任质量约33.8%进入有限点图，剩余UNKNOWN；不得拿这一小片覆盖整叶。顶刺两视角没有合格点，真实负例保留。

图已通过view_image检查scan24屋檐、scan65颅盖接缝、Ficus薄叶及top_spike放大（round2/figures）。原fullframe/C8未裁，显示只临时改source颜色，source原SH/geometry/opacity不写回。3D散点显示<=1800点仅为图幅限制，完整图保存；散点大小未代表责任，稀薄远点不能按数量解释质量。

实现：sourceID↔query像素二部图，保留全部有限EWA贡献及条件不合格原因；有效满秩条件点按唯一像素归一。single和按两侧约束two分别5次IRLS，1p残差、展开条件、2p内质量80%、复杂度/重叠门不变；并非全scene图分割或真表面重建。source软patch质量/UNKNOWN不强制单标签；未查询原核默认UNKNOWN。source诊断PLY只有原核中心和ID，是可追溯显示副本，绝非surface mesh/新Gaussian模型。

13个本轮解析测试真实3轮RED→GREEN。拟合平面/折面/两层、同宽核不能复制成两面、像素重复不增样本、正常向翻转、没有sourceID重叠拒配等均通过；这不等于场景分类准确。

下一轮：GO有限反证。保留视角不重拟合R2面片，仅评价冻结候选；全部4臂独立算条件mode重排后alpha*T变化，ROI全N复核。若重排改善同样出现在null，不能称线专有效果。遮挡无观测≠反票；无法配对不自动归因rolling silhouette。
''')
js(rd/'VISUAL_REVIEW.json',dict(inspected=[str(rd/'figures'/s/ca/f) for s,ca,f in [('scan24','roof_wall_eave','CASE.jpg'),('scan65','cap_seam','CASE.jpg'),('ficus','thin_leaf_edge','CASE.jpg'),('ficus','top_spike','ZOOM.jpg')]],verdict='NO_GO_PRIMITIVE_UPGRADE'))
review('03_round3_GO_falsification','''R2工程88模型、原线跨视角0；null打乱反有1对。三scene实际图已查，NO_GO升级，但按预冻允许第三轮便宜证伪。GO R3：只运行固定0012/0036或test_r_14/test_r_79，在原case ROI；不改原模型，不新选线，不拟合保留视角patch作成功结果。
原center排序先严格复算alpha*T。条件mode排序重新用原opacity与完整EWA q还原每核alpha（包括旧排序被早停隐藏的贡献），以条件有效mode排序，否则保留mean作为UNKNOWN。这是局部排序反事实，不是官方RaDe/新全帧renderer。all-N核集合及权重校验。记录责任L1、条件native误差、可见/遮挡/前方不一致与实际视角角度；rolling/纹理/浮核仍是待区分解释。R2冻结DEV/AUX候选只投到保留视角，保持面参不动；不通过则REFUSED。每场景两保留视角全frame与局部原因图，保留毛刺负例，第三轮硬停。''',[rd/'COUNTS.json',rd/'CROSS_VIEW.json',rd/'ROUND2_REPORT_ZH.md',ROOT/'PROTOCOL_FREEZE.json'])
state('ROUND3_TESTS',completed_rounds=2,round=3,status='GO',children=[])
