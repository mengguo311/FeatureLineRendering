Execution frozen UTC: 2026-09-18T10:55:24.430374+00:00
Starting branch: point-feature-foundation
Starting HEAD: fc27b3e01085cb35edc8418c5e9b1be33ed5d067
Decision memo SHA256: 70a23c90e63cd97f15ec676f7080fb7f3a7824512f80bd5572d1b3ae20262a7a

**裁决：只选择 B——由 TRAIN 多视图约束、冻结 GS 提供可检验支撑与可见性先验的三维边 UDF＋无符号切向场。首实验只检验其可辨识性，不训练完整场、不提取曲线。** 先回答：图像证据是否把有视觉价值的静态边约束成唯一的窄三维带，而且这种定位与方向能否抵抗 RGB 近等价的 GS 重参数化。若答案是否定的，不开发 tracer，不调阈值救结果。A 暂不具备已验证的 surface-sample 前提；C 的可解析性不等于几何可辨识性；直接优化曲线的 D 尚不能绕过同一证据瓶颈。

# FeatureLineRendering：底层特征结构研究决策备忘录

日期：2026-09-18。性质：研究裁决与下一轮预注册方案，**不是实验结果或实现完成报告**。本次仅阅读、文献核查与写作；没有运行新提取实验、训练、测试套件或修改仓库。以下数值门槛均是本备忘录提出的研究决策阈值，不是从新 DEV 结果估计出的数值，也不是文献保证。

## 1. 假设、证据与不得偷换的任务

### 1.1 已完整阅读的输入与仓库事实

四份指定报告已全文阅读，含来源列表及其核验限制：

| 输入 | 对本决策的作用 |
|---|---|
| [经典无网格方法报告](/home/u00134/research_inputs/pointcloud_feature_lines_for_frozen_3dgs_zh.md) | A 的几何定义与 surface-sample 前提；锐折痕和光滑脊谷应分开审查 |
| [学习式三维边表示报告](/home/u00134/research_inputs/learning_3d_edge_representation_review.md) | B 的证据来源；预训练 CAD 点云网络与 vanilla GS 的域差异 |
| [Gaussian 连续场报告](/home/u00134/research_inputs/gaussian_continuous_field_review.md) | C 的导数可计算性、opacity 语义与重参数化不变性反例 |
| [新颖性反方报告](/home/u00134/research_inputs/novelty_review_frozen_3dgs_strokes.md) | 最近邻工作和贡献上限；不能把已有表示重新命名为创新 |

已核对当前分支 `point-feature-foundation`，HEAD 为 `fc27b3e01085cb35edc8418c5e9b1be33ed5d067`，初始工作区干净。相关仓库证据：

* [raster-state RESULTS](/home/u00134/3dgs_line/tier1/out/raster_state_candidates/RESULTS.md)、[测试记录](/home/u00134/3dgs_line/tier1/out/raster_state_candidates/TEST_RESULTS.txt)、[Chair transfer](/home/u00134/3dgs_line/tier1/out/raster_state_candidates/chair_transfer/RESULTS.md)：D 增加 2,938 个 linelets，同墨量下仍未恢复清楚结构；33 项测试通过只证明程序行为。top-k 的 k4/k8 平均 Jaccard 为 0.08935，不能把 ID/贡献稳定当成既定事实。
* [gap recovery RESULTS](/home/u00134/3dgs_line/tier1/out/gap_recovery/RESULTS.md) 与 [PREREG](/home/u00134/3dgs_line/tier1/out/gap_recovery/PREREG.md)：三个预标缺口仅一个被选中修复；12/20 桥得到 held-out 支持，没有转化为整体视觉成功。该次 orbit 接近极点，不能据此证明全面遮挡稳定。
* [stroke organization RESULTS](/home/u00134/3dgs_line/tier1/out/stroke_organization/RESULTS.md)、[TESTS](/home/u00134/3dgs_line/tier1/out/stroke_organization/TESTS.md)、[PREREG](/home/u00134/3dgs_line/tier1/out/stroke_organization/PREREG.md) 和 [MANIFEST](/home/u00134/3dgs_line/tier1/out/stroke_organization/MANIFEST.json)：同墨面积下，A/C/null 的短片段率分别为 90.76%/81.24%/76.47%；C 的可见片段长度只有 A 的 1.189 倍。null 更长、更少碎片，明确否定“碎片指标改善便证明结构改善”。最终 45 项测试通过，视觉结论仍为 NO-GO。

本次另亲自查看路径组织的固定四帧同墨面积图与三个区域对照图：底板局部线更长，但机械结构周围仍有重复、短弯线和杂乱转折。这与报告相容；**本次没有重新审阅全部历史视频，不把报告作者的全帧检查冒充本次完成的检查。**

代码核查有四个直接影响决策的发现：

1. [linelet.py](/home/u00134/3dgs_line/tier1/src/linelet.py:38) 的旧切向来自筛选后的 **seed 中心分布**的最大 PCA 轴，既不是主曲率方向，也不是 Gaussian 最大轴。实际邻域半径使用所有 splat 尺度的全局中位数乘 3；不能把注释里的局部尺度解释成逐点适应的邻域。
2. [render.py](/home/u00134/3dgs_line/tier1/src/render.py:15) 的 defloat 依赖 opacity 与 kNN 距离；clone/split 能改变这个筛选本身。[raster_state.py](/home/u00134/3dgs_line/tier1/src/raster_state.py:33) 是圆盘 splat、full-K compositing 代理，**不是官方各向异性 raster fragments**。
3. [visibility.py](/home/u00134/3dgs_line/tier1/src/visibility.py:11) 使用 3×3 最小深度和 2% 容差。它能切断本来固定的三维线；先验错误不能用末端 smoothing 解释掉。SH0 颜色在代码中称为 albedo，也不等于真实去光照反射率。
4. 现有访问 [guard](/home/u00134/3dgs_line/tier1/scripts/run_stroke_organization.py:43) 是有价值的审计，不是覆盖 native IO 的安全隔离。历史报告均承认原始 GS 训练 split 未独立重建。新实验只能先主张“后处理未见 DEV 图像”，不能声称 GS 本身也未见过。

这些负结果约束的是已运行的实现与数据，不是所有曲线组织算法的不可能性定理。不过，继续花资源修理旧 linelets 已没有合理的第一实验优先级。

### 1.2 数学对象必须先限定语义

目标是一个允许缺失、固定在物空间的稀疏线资产。以下三类结构不能混称：

* **曲面内禀特征**：光滑 ridge/valley、锐 crease，需要曲面及其导数或面片交会信息。
* **静态视觉特征**：可由多视图重复定位的接缝、部件边界、材料边、某些稳定明暗边；不一定是曲率特征。
* **视点相关轮廓**：光滑物体的遮挡轮廓、suggestive contours、高光边一般随视点移动，不能全部编码为一组固定表面路径。

B 首先瞄准第二类中对形状表达有用的子集。锐几何边可能属于该子集；没有 RGB 边证据的光滑曲率 ridge 不在 B 的可恢复承诺内。静态材料边不是自动的错误，重复纹理也不是自动有用；这两者的 NPR 价值由独立视觉 gate 判定。固定光照下的投影阴影可能同样形成稳定三维视觉边，单靠跨视图一致性无法证明它是几何边。

这不是悄悄降低目标：若这个可观测子集在固定墨量下不足以表达形状，应 STOP 当前 NPR 主张，不能事后把大量纹理边改称“成功的抽象”。3Doodle 已明确区分固定三维 Bézier strokes 与视点相关 contour primitives；其后一类输出不能直接搬来满足本任务的固定路径约束。[3Doodle §3.1–3.2](https://arxiv.org/html/2402.03690)

### 1.3 可计算性与可辨识性

给定某个 posterior，能算出一个值、方向或曲线，只是**可计算**。本项目要检验的是：在相机、图像误差与分辨率容差内，输入是否把目标结构约束到足够小的等价类。

设两个 GS 资产在批准的视图域中渲染近似相同，记作 `G ~RGB G′`。有几何意义的推断至少应满足：在共同可观测范围内，`Γ(G,I_TRAIN)` 与 `Γ(G′,I_TRAIN)` 的横向位置、切向、重复结构和显隐足够接近。这里不要求 Gaussian 行号对应，不要求沿一条曲线的采样参数相同，也不把不可见区域纳入强保证。

这种近似不变性是**必要条件，不是正确性充分条件**：一个固定画错的圆、或完全忽略 GS 的算法，都可能通过。还必须通过 held-out 图像与视觉价值、非退化产量以及 GS 增益对照。

vanilla GS 的优化目标是辐射重建，位置、尺度、opacity、SH 与 densification 联动；它没有把中心定义成测量曲面样本。SuGaR 另加表面对齐正则的事实支持审查这个前提，而不是证明任何 vanilla GS 都没有可用局部几何。[原始 3DGS](https://arxiv.org/html/2308.04079)、[SuGaR](https://arxiv.org/html/2311.12775)

## 2. 候选比较及淘汰理由

| 假设 | 潜在对象与信息来源 | 最关键、尚未成立的前提 | 首轮裁决 |
|---|---|---|---|
| **A：稳健 meshless surface＋ridge/valley；1-vs-2 sheet crease** | 中心邻域定义单/多片曲面；光滑支路取曲率极值，锐支路取两片交线 | 中心确实接近可分离曲面；采样足以支撑导数；局部双片不是前后深度层或 floaters | **不选**。先做样本语义诊断；二片交线比高阶 ridge 更容易检验，但本轮不同时开发它 |
| **B：TRAIN edge-supervised UDF＋axial tangent** | 固定三维视觉边集的距离与切线；GS 仅给可检验的支撑/遮挡先验 | 边在多视图中是同一静态结构；基线与方向约束不退化；GS 没把正确边错删 | **唯一首选**。先检验信息是否足够，不把 neural field 当答案 |
| **C：解析 opacity/extinction mixture＋level surface 微分几何** | 从中心、协方差、权重形成解析标量场，再求 regular level 与导数 | photometric splat 参数对应稳定几何；权重/level/尺度在等价参数化下保持意义 | **不选**。存在简单双层与重参数化反例；导数精确不能修复语义 |
| **D：直接多视图优化固定 Bézier/line 集合** | 参数曲线直接解释 TRAIN 边图；可借 SketchSplat/CurveGaussian 范式 | 数据能辨别曲线位置、支数与拓扑；初始化与曲线数不主导结果 | **不选**。少一次离散拟合可能有工程优势，但不能先验解决欠约束，也不是空白方向 |

### 2.1 A 的强点与真正的门槛

A 具有最清楚的**内禀几何语义**。若有可靠单片曲面，ridge 可定义为 `D_e κ=0` 并检查极值类型；若两片真正相交，`t ∝ n₁×n₂` 比中心分布的最大 PCA 轴有更直接的解释。局部解析面片本身不违反 mesh 禁令。不能像输入学习综述的某些表述那样，把所有 surface fitting 都视为 mesh 泄漏；禁令针对 mesh 或其派生信息进入方法。

但稳健估计只抵抗所假定污染模型中的异常值。若大批中心来自分裂出的重复 primitive，或多个深度层共同承担图像解释，“多数样本”也可能是错误几何。密度补偿并不自动恢复表面采样测度。最小协方差轴未经验证不能充当 RIMLS 输入法向，协方差也不是已校准的测量误差矩阵。RIMLS 的作者项目页与 robust MLS 原文确实给出保特征曲面思路；它们没有验证这种 photometric posterior 分布。[RIMLS](https://www.labri.fr/perso/guenneba/publi/RIMLS_eg09/index.php)、[Robust MLS](https://www.cs.tau.ac.il/~dcor/articles/2005/Robust-Moving.pdf)

光滑 ridge 的零条件涉及曲面三阶信息，其极值类型与追踪稳定性还可能需要更高阶信息；“二阶面拟合看起来稳定”远远不够。双片交线也不能把两张不相交、平行的薄结构表面误认成 crease。经典点云工作已经覆盖多尺度显著性和曲线恢复，不能为这条管线宣称流程创新。[Pauly 等，2003](https://cgl.ethz.ch/Downloads/Publications/Papers/2003/Pau03b/Pau03b.pdf)

### 2.2 C 的反例比漂亮的 Hessian 公式更有决策价值

对正定协方差的有限 Gaussian 和，令 `A_i=Σ_i⁻¹`、`r_i=x−μ_i`、`g_i=exp(−r_iᵀA_i r_i/2)`：

`ρ=Σ_i w_i g_i`，`∇ρ=−Σ_i w_i g_i A_i r_i`，

`Hρ=Σ_i w_i g_i[(A_i r_i)(A_i r_i)ᵀ−A_i]`。

在 `ρ=τ` 且 `||∇ρ||>0` 的地方，投影 Hessian 可以定义 shape operator。这是数学事实；从它推出“识别了物体表面”则缺了一步。

本备忘录的三个直接推论是：

1. 薄 Gaussian 密集覆盖平面时，中心面可以处在法向密度极大处。理想均匀情形该处梯度为零；低于峰值的 regular level 得到两张 offset 面。选外层不等于恢复原面。
2. `w=α` 或 `w=−log(1−α)` 都是额外约定。后者是峰值光学厚度的转换，并不把原始 splat α 自动变成视向无关的每单位长度 extinction。解析射线积分包含方向相关宽度。物理一致 rasterization 文献区分了这些量。[Volumetrically Consistent 3D Gaussian Rasterization §4](https://arxiv.org/html/2412.03378)
3. 小 Gaussian 的逆尺度会放大高阶导数；固定 scale space 能降低噪声，却不能建立缺失的物理语义。若采用卷积尺度空间，除 `Σ+h²I` 外还须说明质量保持因子；若采用 `τ(x)`，导数须包括阈值场导数。有限解析场的 regular level 也没有真正法向不连续的锐折痕。

GOF 使用新的 ray-based opacity 定义并加入几何训练正则，不能被引用为“冻结 vanilla GS 已经有可靠曲率”的证据。[GOF](https://arxiv.org/html/2404.10772) 即便 C 的有限差分检查全过，也只说明求导器正确。

### 2.3 为什么没有更强的 D

直接曲线优化能减少“先采点、后拟合”的误差，但一条错误曲线也可拟合多张含重复纹理的边图；更多曲线甚至能逐视图制造相互遮挡的解释。CurveGaussian 与 SketchSplat 已直接优化参数边，后者默认监督还包含 2DGS depth 与单目 normals。本项目不能拿这些额外输入的效果当成 vanilla-only 可达证据。[CurveGaussian §3](https://arxiv.org/html/2506.21401)、[SketchSplat §4](https://arxiv.org/html/2503.14786v2)

多视图 edge triangulation/局部 bundle adjustment 是很合适的**信息探针**，不是一个更强、免假设的最终表示。因此把它用来检验 B 的必要前提，不另立 D 为主方法。预训练 CAD edge 网络、medial skeleton 或重新训练 SuGaR/2DGS 都没有同时改善本任务的证据前提与约束适配。

## 3. 唯一科学假设 B 与工程实现的分界

### 3.1 潜在数学对象

设 `Γ⊂R³` 是一组部分可见、分段光滑的固定三维曲线，允许端点、尖角和有限 junction；只在可观测域 `Ω_obs` 内承诺恢复。定义：

`d_Γ(x)=inf_{y∈Γ} ||x−y||`，以及 regular branch 上的 `T(x)=t(x)t(x)ᵀ`。

`T` 是秩一投影张量，`t` 与 `−t` 等价。置信度是可观测性/不确定度记录，不应成为一个可随意降低训练损失的自由 opacity 旋钮。`d` 在边本身和多个最近点的分界处一般不可微；不能要求处处光滑且处处满足 Eikonal。对没有 junction、位于正常管状邻域内的光滑边，平方距离 `q=d²` 可局部光滑，在边上有 `Hq=2(I−ttᵀ)`。这是局部几何关系，不是任意训练网络必然满足的性质。

在 Y/T/X junction，单一 `T` 无法表示全部分支；平均方向可能指向任何真实分支之外。首轮将其标成多模态/不可唯一切向并 abstain，不强选一支；未来需要分支集合与显式 junction 身份。远处近平行边导致的最近点切换，同样不能由切向平均解决。

**科学假设 H_B：**对预声明视觉区域中的一个非平凡子集，TRAIN 边图的多视图投影约束足以稳定限定 `Γ` 的横向位置和 axial tangent；冻结 GS 的支撑/遮挡先验有净收益，且该收益在 RGB 近等价参数化下保持。它不声称 Γ 唯一覆盖整物体，也不声称 Γ 等于全部内禀 ridge/crease。

### 3.2 为什么有机会比中心 PCA 更可辨识

对同一局部边的图像法向 `n_v` 与投影 Jacobian `J_v(x)`，定义 `a_v=J_vᵀn_v`。同一三维切向应满足 `a_vᵀt≈0`。若多视图反投影边约束的法向张成二维子空间，横向位置被约束，剩下一维近零方向才是切向；若只有一维约束、重复匹配或多个深度模式，则明确拒绝推断。

因此方向来自相机与图像观测，不来自 Gaussians 被 clone 后的计数偏置。新的信息来自 TRAIN 图像，而不是“连续”二字。连续网络仅提供函数表示与正则；它既不能凭空提供对应关系，也不能保证积分线形成正确拓扑。

EMAP 已从多视图边图学习 UDF 并由邻域梯度提取方向，随后仍需连接与参数拟合；其存在支持 B 的表示可行性，**不证明本数据的可辨识性，也不证明无需后续拓扑处理**。[EMAP §3](https://arxiv.org/html/2405.19295v1)

### 3.3 信息、优化变量与冻结边界

| 来源 | 允许提供 | 不允许冒充 |
|---|---|---|
| 冻结 GS | 宽空间边界、按实际 splat compositing 得到的深度贡献分布和遮挡不确定性、计算采样提议；官方 RGB 参照 | 表面真值、校准法向、物理 extinction、正确 3D edge labels |
| TRAIN RGB＋相机 | 固定检测器的 edge/方向及显式负证据；跨视图位置约束 | 真实曲率、材质/阴影的完美分类或唯一拓扑 |
| 连续场先验 | 距离结构、分支内局部一致性、适度正则 | 用平滑性填补无证据空洞的许可证 |
| DEV | 冻结后的一次性预测检查和视觉判断 | 调 detector、带宽、置信度、曲线数或输出子集 |
| Mesh | 后续独立 EVAL 的误差分析，首轮不打开 | 生成、拟合、选点、选参、追踪、normal/depth cache 或渲染输入 |

如果基础检验通过，后续可按场景优化新的 `d_θ`，从其局部截面导出 `T_θ`；只在确有证据需要时另拟合 axial head 并约束其与距离场一致。首轮不引入独立 learned tangent head、learned visibility、语义网络或自动 topology module。GS 的 `μ/Σ/α/SH`、相机和图像检测器全部不更新。

所以应写“**无需重新训练原 GS**”，不能写“无需按场景优化”。未来距离场仍需按场景学习。若主要效果来自新的 image-only edge learner，也不能把结果归功于原 GS 已蕴含可读几何。

最终若值得继续，曲线可从可信低距离位置出发，在物空间沿 `±t` 预测、在法平面校正回距离谷，遇到多模态、无证据区、junction 或低置信立即结束；只在局部正则区根据上一切向选择符号。得到路径后一次性固定几何、连接关系、ID 与 brush phase，运行时只投影、GS 可见性裁剪和绘制。**此段只是未来输出契约，本轮不实现、也不评估曲线提取。**

## 4. 最便宜的 foundation-only kill-test：先测证据，不拟合网络

### 4.1 实验能判什么

首实验名称：**B 的局部可观测性与 GS 不变性检验**。输出是深度代价剖面、三维位置不确定带、局部 axial glyph 和失效分桶；不是新 linelet 候选池，也不把输出送进旧 chainer。

最便宜的否证方式是：若允许全深度搜索、多个初始化的局部模型都找不到唯一且可迁移的边带，复杂 UDF 只能靠更强先验猜测。反过来，局部探针成功仅表示值得尝试全局场，不代表 B 的全局场或 NPR 资产已经成功。

局部探针有模型限制：有限分辨率、检测器及局部平直近似都可能导致失败。因此失败应标成“在本冻结证据/分辨率/预算下不支持投资 B”，不能冒充所有多视图重建的信息论不可能性证明。

### 4.2 固定数据、尺度和查询

* 顺序：Lego primary；仅其所有必要 gate 通过才运行预先锁定的 Chair transfer。两场景不改阈值。Chair 对柔和外形/纹理提出额外压力；两场景仍不足以主张普适性。
* 后处理 TRAIN 保持历史 16 个索引：`[1,7,14,21,27,33,41,47,53,59,67,73,79,86,93,99]`。拆为拟合 F=`[1,14,27,41,53,67,79,93]`、交叉验证 C=`[7,21,33,47,59,73,86,99]`。主输出只能用 F；交换 F/C 的独立探针只做稳定性诊断，不挑更好的输出。
* DEV 照片锁定为 `[2,22,42,62]`，不进任何优化。它们在历史工作中部分已被使用，必须叫“本轮 held-out”，不能叫全项目从未见过。TEST `[5,15,25,35,45,55,65,75,85,95]` 继续封存。
* 原图白底合成后统一 400px；主 detector 一次固定为灰度 Gaussian `σ=1.2px` 后 Canny `(50,120)`，5×5 edge 邻域估计无向 2D tangent。每像素最多一票；不把多通道或不同 detector 当多个独立 view。它不是“最优 detector”的主张。
* 空间坐标使用基准 GS 一次确定的宽边界：每轴中心分位数 `[0.1%,99.9%]`，各边外扩原盒对角线的 10%；记录盒外 Gaussian 在 TRAIN 的渲染贡献。盒外贡献超过 1% 则协议前提失败，不用裁剪隐藏问题。所有变体使用同一个盒、坐标与尺度，不重新对齐或重新归一化。
* 定义 `δ` 为基准资产在 16 个 TRAIN 视图的有效前景射线上，条件中位深度处 `z/f` 的中位数，即 400px 下约一像素的固定世界尺度。它是测量单位，不是真实表面精度。扰动资产不得重新计算 δ。
* 主查询来自 F 中 `[1,27,53,79]`：每图最多 64 个 edge 像素，按 8px 网格分层、固定 hash `seed=20260918` 选取；不使用旧 seeds、旧成功区域、mesh 或人工 3D 对应。交换组查询来自 `[7,33,59,86]`，同样规则。稀疏时保留不足，不补点。每组上限 256 条查询射线。
* 在整个宽盒内按射线均匀初扫，点数固定按 `max(256,ceil(2×盒内射线长度/δ)+1)` 计算，上限 2048；这是几何分辨率公式，不按拟合效果选择。对全部局部极小区间作固定两级细化，每级 8 点，保留并报告所有模式。若触及上限使相邻搜索样本距离仍大于 δ/2，标记分辨率不足，不能把未发现次峰写成唯一。不得只搜索 GS 中位深度附近。

### 4.3 先检查 Gaussian centers 是否像 surface samples

这是输入语义诊断，**不把 A 加进生成器**。在查询射线及独立背景查询的基准 GS 条件深度 5%/50%/95% 处建立空间单元，按固定 hash 取 128 个邻域；背景查询为每参考图 16 个离 edge 至少 6px 的前景像素，保留为负对照。邻域位置不由待测曲面拟合挑选；背景查询不进入最后的正输出。

在物理半径 `{2δ,4δ,8δ}` 下，比较一平面、局部二次片、两平面与体积散布解释。做以下控制：

1. 分组单位是边长 δ/2 的固定空间 cell，按 cell 划分拟合/验证，**不能把同一个 clone 的两个后代分进训练与验证**。报告 Gaussian 数与独立 occupied-cell 数；以 cell 等权和实际渲染贡献加权分别报告，不能只报密集点的点数平均。
2. 初次拟合只用中心与空间权重；不把 covariance 轴或 inverse covariance 当法向/测量精度。之后再比较最小轴与拟合 normal，按 learned anisotropy 分桶。
3. 单片可信标签要求至少 30 个有效 cells、held-out 正交距离 P90≤0.15h、两个相邻尺度及 cell bootstrap 法向差 P90≤15°，并且通过后述扰动下的位置/法向重复性。另要求拟合切平面内采样协方差的较小/较大特征值比≥0.1；否则一条细长点串也能完美拟合平面，不能称为 sheet。二次模型用来避免把真实光滑曲率当作“体积噪声”。
4. 双片标签还要求每片≥15 cells、held-out 残差相对最佳单片降低≥30%、无符号法向夹角≥25°、两侧空间支持充分且交线位于双侧支持范围的 δ 邻域内。两张平行深度层标成 layers；不外推两远面交线为 crease。
5. 分别统计 sheet / plausible crease / multilayer / blob / sparse / unstable；审查 floaters、重复/分裂中心与长轴 covariance 是否集中在失败桶。低 opacity 不等于 floater，低密度也不自动等于错误，禁止用旧 defloat 先删掉困难样本。

这些通过条件只能说明**局部近曲面采样模型相容**。中心拟合与中心 PCA 相互一致仍是内部自洽，必须再由独立图像约束检验位置。若不稳定，不允许在后文恢复“centers 默认是 surface points”的措辞；若稳定，也仅对通过的局部、尺度与分辨率成立。B 本身不要求多数中心通过，所以该审计失败不自动否决 B。

### 4.4 用多视图约束检验一维边带

对查询位置 x，评价 F 中 edge 距离与方向，搜索上述整个射线区间；允许局部横向 ±1px 的确定性扰动以检查检测误差。每个可评价 view 使用相同单位权重，像素残差截断在 6px。为每个深度模式冻结其可见性分类，在局部优化内不得通过“躲进遮挡”移除反对该模式的 view；若移动导致分类变化，记录模式不稳定并拒绝接受。

GS 可见性必须保留多层信息。首选按官方投影协方差与 alpha compositing 计算所有有贡献 splats 的 `w_i=T_i α_i(p)`，记录条件深度分布，而不是单一 mean depth、top-k ID 或圆盘 normal。这里仍是 **splat 深度代理，不是几何真值**。若该只读分析器不能在 TRAIN 重现 stock renderer 的 RGB/alpha 行为到预声明容差，基础实验标记工程未就绪；不能偷偷替换成旧 disc proxy 并宣称官方证据。

具体先验冻结为：support 使用每射线贡献分布 5%–95% 区间、保留其中所有分离层，再外扩 2δ；它只提供采样优先级和“GS 支撑/冲突”标签，**不截掉全盒诊断搜索**。遮挡以 x 前方超过 2δ 的 splats 的累计 transmittance 判断：`T_front≥0.8` 为可见，`≤0.1` 为隐藏，中间为不确定。隐藏/不确定不计负；但至少三个分离 F 视角可评价才允许接纳。所有模式和被 GS 拒绝的位置保留在 no-GS 对照中，以发现先验删错。

这里的相机投影协方差、alpha clamp、early termination 和深度排序规则都须与所锁定 stock renderer 一致；分析器在 TRAIN 的前景 RGB 最大绝对误差≤1/255、alpha 最大绝对误差≤1/255 才算数值校准通过。stock 接口没有直接 alpha 输出时，用固定参数的白底/黑底 RGB 差恢复累计透射率作为校准参照，不冒充已有官方 alpha/depth 通道。此校准验证 compositing 语义，不认证它的中心深度是真实表面深度。

对同一局部 edge 模式，建立仅来自图像约束的矩阵：

`H_img(x)=Σ_{v∈visible F} J_v(x)ᵀ n_v n_vᵀ J_v(x) / σ_pix²`，`σ_pix=1px`。

用有序特征值 `λ₁≤λ₂≤λ₃` 检验横向约束；最小特征向量给 axial tangent。**H_img 不包含 GS prior、平滑惩罚或 Eikonal 项**，防止把正则提供的曲率冒充图像信息。线性化横向不确定尺度记为 `u⊥=sqrt(5.99/λ₂)`；检测误差相关且模型非线性，它只能称为局部不确定度代理，不是校准的 95% 置信区间。

每个模式还须记录：投影到各 view 的 residual、无符号方向误差、角度分离、F leave-one-view-out 变化、跨 F/C 的空间带一致性、所有近优替代深度及 Foreshortening。`||J_v t||δ<0.25px` 的方向不可评价，不伪填零误差；数量和覆盖损失必须单报。

若两个模式横向相隔>2δ，而 F 的 RMS residual 相差≤0.5px，标记歧义，不选择更接近 Gaussian center 的那个。局部 Hessian 良好不能排除这种全局多模态；通过 Hessian 但存在次峰仍须拒绝。

输出一个局部似然/证据谷不等于输出 UDF：`Σ DT_v(π_vx)²` 受相机数量与夹角影响，不是三维欧氏距离；本轮绝不把它命名成已学到的 `d_Γ`。这项探针检验的是 B 所需的可观测性，成功后才考虑距离场表示。

### 4.5 重参数化是核心试验，不是附加 robustness 图

本次只检查到 `lego_static` 与 `chair_static` 目录各有一个 `point_cloud.ply` 和训练曲线 JSON，没有在这两个目录发现独立 seed checkpoint；不声称整个服务器不存在。首轮采用合成扰动副本，原 PLY 保持逐字节不变。若未来已有、来源可核验的独立 seed，必须在打开新结果前登记并纳入；不为本试验重新训练 GS。

冻结两种不同扰动，作用于按 parent hash 选出的 50% Gaussians：

* **P_clone**：每个被选 primitive 换成两个同中心、同 covariance、同 SH 的 clone，峰值 `α′=1−sqrt(1−α)`，保持 parent 深度排序与确定性 tie-break。Gaussians 行号打乱另作纯 IO 检查。
* **P_split**：沿最大轴取 `Δ=0.2 s_max e_max`，中心为 `μ±Δ`，子 covariance 为 `Σ−ΔΔᵀ`，两子采用同样的峰值 alpha 分配，SH 不变。这保持中心/协方差的某些 mixture 矩，但**不声称保持 splat 图像或物理密度**。

特别强调：clone 的公式仅在投影 Gaussian 值为 1 的峰值处匹配总 opacity；一般像素 `1−(1−α′g)²` 不等于 `αg`。二者都必须实际通过 RGB 近等价门槛，不能用公式直接认证。替换后的计数增加和贡献覆盖也必须非平凡：受影响 parents 合计覆盖至少 20% TRAIN 前景贡献权重；否则只算弱扰动，不能支持 GO。

近等价资格只看固定的 stock RGB 渲染：每个 TRAIN view 的固定前景 ROI 内 PSNR≥40dB、SSIM≥0.995，P99 像素绝对误差≤8/255；白底与黑底各检查一次，避免透明度差异被单一背景掩盖。ROI 在基准资产上一次冻结，不许使用全图白背景稀释误差。**不要求 depth/normal/ID 保持不变；那些正是被检验的量。**

参数、扰动 parents 与幅度不依据方法输出改变。只有 RGB 合格的非平凡扰动才进入不变性 gate；RGB 不合格记作“无有效等价干预”，既不算方法失败，也不算方法通过。至少一种非平凡干预合格才允许 foundation-GO；只有 clone 合格时，结论限于 clone，split 与跨 seed 不变性仍未建立。

对每个有效扰动，在相同 TRAIN 图像、相同坐标/盒/δ/查询上重新运行探针。分别测三维支持域、局部位置、T、歧义率和 glyph 显隐变化。DEV 相机渲染的近等价性在封存输出后再核验；若 DEV 上不再近等价，该干预的 DEV 不变性不可解释，不能据此惩罚或赞扬方法。

### 4.6 必需 controls 与反作弊

| 对照 | 它检验什么；公平性要求 |
|---|---|
| **旧 PCA-linelet null** | 按已冻结的旧 seed/PCA 初始化配方、相同 F 图像一次生成 p0/t/尺度，不运行 pull、prune 或新调参。历史 `baseline_initial.npz` 使用了全部 16 视角，含本轮 C，故只能展示作背景，不能冒充 F-only 公平 null。主比较使用旧算法原始位置；另报同查询位置借用最近旧切向的 paired-direction 诊断，明确后者不是原算法质量 |
| **去掉 GS prior 的同一图像探针** | 保持宽盒、查询、计算量、所有图像损失相同；不学习遮挡，不丢任何 in-frame 反对 view。用于检测 GS 的净贡献或错删，不把其误罚隐藏边归因于图像本身 |
| **错误跨视图关联 null** | 各 view 的 edge/方向图作预定不相同的整 32px 循环平移，计数、置信度和图像尺寸不变；新边界 32px 区域统一不可评价。它是证据关联 null，不是视觉真实边真值 |
| **固定位置随机 axial null** | 在与 B 完全相同的接受位置、相同 glyph 数与物空间长度下，使用固定随机无向方向；排除“只是选择较好位置”的解释 |
| **原资产 vs 有效 clone/split 或独立 seed** | 不匹配 Gaussian IDs，按共同空间 tube 与几何距离匹配；禁止 ICP 或每资产单独缩放来隐藏漂移 |
| **遮挡开启/关闭诊断** | 相同固定 glyph 仅改变显示裁剪，定位可见性切断；关闭遮挡图不是可提交的最终效果，也不改变主结论 |

配额与 ink：每 arm 原生全部输出都展示。方法接纳至少 64 个彼此相隔≥δ 的位置才具备非退化产量；显示再按固定空间 hash 选 64 个，每个 glyph 为固定物空间 `x±δt`、1px AA 黑线。它们只是 field 诊断，不是最终 stroke 资产。

no-GS 一项是冻结算法的先验消融，**不是完整 EMAP 的公平替身**。它对隐藏边可能过罚；其单独失败不能证明图像缺少信息。G4 的净增益必须同时在独立评估者标注的明确可见区域成立，并公开隐藏/不确定区域的分桶结果；若优势只来自给 no-GS 强加了错误可见性假设，只能得出“本先验消融处理遮挡较差”，不能满足 frozen 特征可辨识性的贡献 gate。

位置/方向数值对照使用相同空间审计域、相同可见性规则并单报 coverage；只在交集上报角度会隐藏方法 abstention，因此必须同时报告全体分母。ink 对照分两套：固定 64 glyph 数，以及实际 AA 墨面积匹配。后者以旧 PCA 64-glyph 在 F 的平均墨面积的 60% 为预定预算，各 arm 按固定 hash 前缀选择一个全程不变的 glyph 子集，F 上误差≤5%。不足预算记不可比，禁止增加低置信墨、调整笔宽或逐帧删除。DEV 不再重配子集，报告其实际差额；只有 DEV 平均差额≤5% 才可作“同墨量视觉优越”判断，否则视觉公平性 gate 未通过。

这对完整性没有高召回要求；它只防止靠一个漂亮小点或几乎零墨获得稳定性成功。首轮 glyph 不评价“长 stroke 数量”“fragment 减少”或真实 topology 正确率。

## 5. 冻结协议、预注册 gates 与判决表

### 5.1 数据隔离与评估材料

执行前，创建独立实验目录与只读输入清单，记录原 PLY/图像/相机/源码/renderer、detector 和所有输出的 SHA256。当前备忘录不创建这些实验资产。把这些机械清单填完整不构成修改上述阈值或另选场景的机会。

使用只读白名单输入目录：只含批准的 GS 副本、F/C 图像及相机元数据；方法进程看不到 mesh、其派生 depth/normal/crease 标签、2DGS/学习法向缓存、历史不明 NPZ、DEV/TEST 图像。renderer 只能读批准的 GS。用 OS 文件打开审计覆盖 native library，并保留 allowlist；现有 Python guard 可复用思想，不能当作完整隔离证明。评估进程另读 DEV，且禁止写回方法目录；首轮连 EVAL mesh 也不加载。

F 与 C 必须进一步分开挂载到各自探针进程；“都属于 TRAIN”不能成为主输出读取 C 的理由。δ、宽盒和查询策略可以使用冻结 GS 与批准的相机元数据，但主输出生成只能打开 F 的 RGB。C 对主输出的评分以及反向拟合只在主输出 hash 封存后进行。

在运行探针前，只依据 TRAIN RGB，由不参与算法选点的评估者为每场景锁定 12 条视觉目标 span（至少 4 条内部结构，不全是 silhouette；每条在至少 3 个 F view 中可辨），以及 12 个挑战区域：重复纹理、阴影/高光、光滑 silhouette、邻近多层各 3 个。人工图像标记只进入隔离的 evaluation 文件，不输入生成器、拟合、阈值、初始化或选择。**它们是图像视觉评价，不是 3D 几何 GT。** 若不能找到足够可信目标，记“当前证据不适合该主张”，不临时换场景或降低数量。

DEV 的对应 2D span 标记在模型/输出冻结后，由看不到 arm 身份与结果的评估者完成。边图 residual 同时对 detector 和人工 span 报告：前者是 detector 自洽，后者才用于避免 detector 证明自己的循环。不同 view 的标记不被用于反向三角化来重选输出。

DEV video 固定 120 帧、24fps、400px、全 360°；target、radius 使用基准 GS/相机一次冻结；仰角 `25°+8°sin(2φ)`、相位 22.5°，禁止近极点退化。查看 0/30/60/90 四帧与全部 120 帧 contact sheets；全视频无 GT overlay，另提供有误差标记的诊断版。此轨迹与历史类似，所以是压力测试，不是新场景盲测；其官方 RGB 仅供视觉参照，照片 DEV 才提供独立图像证据。

### 5.2 量化 gate：以下全部预定，不做 DEV rescue

这里“接受位置”只由 F 规则确定。C 和 DEV 验证失败的点仍保留在原生输出与统计中，不据此重选场。每个 gate 按场景报告，不能用 Lego/Chair 混合平均挽救失败场景。

| Gate | 固定必要门槛 | 否则说明什么 |
|---|---|---|
| **G0 输入与有效干预** | 所有禁止输入读取为 0；原 GS hash 不变；至少一种上述非平凡 RGB 近等价扰动有效；搜索分辨率合格；每个接受模式≥3 个可见 F view，至少一对视线分离≥20° | 实验有效性不满足；不得给方法 GO，也不能冒充证伪结论 |
| **G1 单一边带与非退化产量** | F 原生接受≥64 个 δ 分离位置；每个接受位置满足 `λ₁/λ₂≤0.1`、`λ₃/λ₂≤25`、`u⊥≤δ`、F RMS DT≤1.5px；F 内可评价投影切向误差中位≤10°；无上述近优替代深度 | 约束退化、低可信或多模态，拒绝建完整 UDF；不是“缺一个更好 tracer” |
| **G2 独立图像预测** | 至少 80% F 接受位置在 C 有≥2 个可评价 view；其中 DT≤2px 且方向≤20°的 joint support 比例≥80%。在 DEV 独立人工 span 邻域的支持 precision≥0.85，比原位置 PCA null 至少高 0.10；单位为投影采样、每个 view 等权，不能计 Gaussians 数 | 训练拟合/纹理巧合未转化成可迁移边 |
| **G3 重复性与不变性** | F leave-one-view-out、F/C 同查询条件重估及每个有效重参数化：基准可观测位置双向匹配率≥80%（距离≤2δ、轴角≤20°）；匹配位置距离中位≤0.5δ、P90≤δ；轴角中位≤10°、P90≤20°；共同观测域接受量变化≤15% | 位置/方向或接受规则依赖证据偶然性、GS 参数化或支撑层 |
| **G4 非 null 与 GS 增益** | shifted-view null 接受率≤真实的 1/3；B 的同位置投影切向误差中位至少比随机方向低 50%。相对 no-GS 图像探针，在 DEV precision 不降超过 0.02 下，多层/空中错误位置数减少≥25%；或在 precision 均≥0.85 时，可靠支持位置数增加≥20% | 不足以说明三维关联或 frozen GS 有不可替代价值；若双方该错误数均为 0，不能用“0减少25%”宣称增益 |
| **G5 视觉价值** | 以下视觉规则全部通过，含墨量公平性；12 个目标 span 至少 6 个上，glyph 方向与位置已清楚沿同一结构排列，且包含≥2 个内部目标；随机/关联 null 不能取得同等效果 | 正确的 detector edge 仍可能不是有用 NPR 结构；不能用 G1–G4 平均覆盖 |

G2 的 precision 定义为：冻结输出在 DEV 可评价投影中，落入独立标注的静态有用边 2px 带且切向差≤20°的样本数，除以所有可评价输出样本数；审计域外输出另外列出，不能默认正确。人工遗漏可能降低该 precision，故公开标注及未标输出，不能在看过结果后补标签救 gate。至少一半接受点必须在≥2 个 DEV 照片可评价，否则 G2 失败，不能靠把大多数点标成隐藏逃避验证。

G3 主比较在同一查询射线上进行：封存 F 输出后，C 图像独立计算全深度代价剖面，不用 F 的 loss、方向或深度初始化。查询射线的像素原来来自 F，因此准确名称是“条件于共同查询的重复定位”，不是完全独立的三维重建。逐查询匹配全部模式，并比较横向位置与轴角；没有可匹配模式计失败。F 中删掉该查询参考 view 的 leave-one-out 同样保留查询几何并标明这一条件。

交换 F/C 后从各自独立查询得到的两组原生点只用于覆盖诊断，不以稀疏点集 Chamfer 作为 G3 硬门槛：两个正确的边采样可能只是在曲线上相位不同。重参数化则必须使用相同查询，另将 glyph 按 δ/2 弧长采样、空间 cell 去重，报告共同域双向覆盖与位置/角度分位数。raw 点数与去重结果并列，不能用密集 Chamfer 把邻近平行线配错。

以上百分比是廉价 pilot 的实用效应门槛，不是统计显著性承诺。报告逐 view/逐目标区域数据，以区域为单位 bootstrap 描述不确定度；不把 120 个相关视频帧当作 120 个独立样本。

### 5.3 视觉 gate 的具体否决条件

视觉审查比较原生、同 glyph 数、同墨面积三套结果，先看无 overlay 主图，再看诊断。不以边图 Chamfer 代替形状表达。

* 三位不参与选参的评估者匿名比较 B 与旧 PCA，至少两位在“形状结构是否更清楚”和“无关杂线是否更少”两项均偏好 B；还须逐项核对目标 span。若只能由助手内部检查，不得称为盲评，G5 保持未认证，不能宣布 foundation-GO。
* 任一明显双轨、错误深度层、跨部件错位或结构性 texture/shadow 伪边占据主体并持续≥13帧，G5 失败；不要因它稳定存在而计为时间成功。
* 在原本连续可见的目标区域，固定 glyph 显示的出现/消失若不能由遮挡解释、且超过共同可观测 glyph 的 5%，失败。显示变化须与位置/ID 不变分开报告；固定 ID 本身不是“无闪烁”证明。
* 对光滑 silhouette 挑战区应表现为多模态/拒绝或局部有限可见的固定边，不允许形成一圈错误物空间“永久轮廓”。junction 的方向冲突必须标为不确定，不能被平均成斜向伪边。标记本身不画作最终墨。
* 允许未覆盖目标；不允许只剩一个局部好例、主体仍是稳定噪声。glyph 没有长笔画，因此本轮只能认证 raw 结构信息改善，**不能提前认证 clean final strokes 或长曲线质量**。

### 5.4 GO / PIVOT / STOP 的唯一解释

| 结果 | 决策 | 允许的下一步 |
|---|---|---|
| Lego 的 G0–G5 全过，Chair 原样复验也全过 | **FOUNDATION-GO**，仅是必要前提成立 | 下一轮单独预注册小型 UDF 的 raw-field 试验；仍不直接启动完整 curve extractor。只有 raw field 的位置、方向、重复性也过关才讨论路径 |
| 原图约束/C/DEV 定位与视觉 gate 均过；no-GS 对照稳定，但 GS 先验在有效扰动中导致>20% 原接受位置失配，或 G4 无净增益 | **PIVOT，唯一条件性 fallback** | 撤回“frozen GS 带来特征可辨识性”假设，转为 image-only EMAP 类分析；GS 只读显示价值另议。新任务需重新定位，不继续称为本轮 frozen-asset 方法成功 |
| 数学定位稳定，但视觉主要是纹理/阴影杂线，G5 失败 | **STOP NPR 主方向** | 可保留边可观测性诊断报告；不得改称 NPR GO，不加 selector/brush/cleanup 救场 |
| B 未通过必要定位/关联 gate，且图像约束在明确可见区域仍多模态、跨 F/C/DEV 不稳定；no-GS 也未满足 fallback 条件 | **STOP 当前 B 证据假设** | 保留反例和失败类型；不开发网络、不桥接、不自动转 A/C；不从 no-GS 单独失败推出信息论不可能 |
| GS prior 及 no-GS 都对噪声/关联 null 不区分，或只有正则让方向看似平滑 | **STOP** | 不能把先验幻觉当信息恢复 |
| Lego 过、Chair 不过 | **不授予两类场景 foundation-GO** | 若诊断清楚，只能报告 Lego 条件性局部可行；不得更换 transfer 场景或为 Chair 改参 |
| G0 无有效干预、渲染分析器未校准、标签/评估缺失、资源耗尽 | **实验未定，暂停投入；非科学 GO/PIVOT/STOP 证据** | 仅补齐原协议的执行条件。任何改变算法含义、阈值或输入证据的重试都是新预注册，不覆盖旧结果 |

不存在“差一点通过就放宽 20° 到 30°”“换 detector 看哪个 DEV 好”“选一个更顺的 orbit”“把 split 幅度减到看不出变化”这些救援。唯一 fallback 由上表的 **图像成功而 GS 无增益/有伤害** 诊断触发；A/C 不作为顺手拼入的备用模块。

判决优先级为：先判断执行有效性，再判断精确 fallback 条件，然后检查全部 GO 条件；其余任何未过必要 gate 的有效实验均停止本轮向 extractor 投资。若只是墨量匹配失败，结论限于“尚未建立公平的视觉优势”，不扩大为三维结构不存在。STOP 是研究投入决定，须保留具体失败诊断。

## 6. 新颖性边界与最强审稿人拒稿理由

| 最近邻 | 已覆盖的内容 | 本项目最多能保留的差异 |
|---|---|---|
| [EMAP](https://arxiv.org/html/2405.19295v1) | 多视图 UDF、从距离场得到方向、参数边提取 | 对冻结 radiance 资产的条件可观测性和重参数化审计；field 本身不新 |
| [EdgeGaussians](https://arxiv.org/html/2409.12886v1) | edge-specific Gaussians 的位置/主轴方向、聚类与参数边 | 它新训练 edge Gaussians；本项目保持原 RGB GS 不变，但可新优化独立 edge field |
| [CurveGaussian](https://arxiv.org/html/2506.21401) | Gaussian 与参数曲线耦合、直接曲线优化及拓扑适应 | 不能声称 Gaussian-to-curves 或直接优化三维边首创 |
| [LineGS](https://arxiv.org/html/2412.00477v3) | 利用已训练 GS 的分布后处理几何重建的直线段 | 不能声称首次利用 pretrained/frozen GS 抽线；本项目不限直线且检验其参数化依赖 |
| [SketchSplat](https://arxiv.org/html/2503.14786v2) | 参数 sketches、曲线上 Gaussian 采样、多视图优化、拓扑操作 | 默认额外几何监督不符合当前输入限制；可在同等 RGB edge 输入下比较其方法，不能拿默认配置假装公平 |
| [3Doodle](https://arxiv.org/html/2402.03690) | 多视图对象抽象、持久三维曲线及视点相关轮廓 | 持久 NPR strokes 不新；应分别比较符合固定路径约束的部分与完整方法，不能删掉其轮廓后仍叫原版 |
| [WIR3D](https://arxiv.org/html/2505.04813v2) | 稀疏 Bézier 的几何/视觉抽象、shape SDF 约束 | 说明视觉抽象已有直接竞争者；默认 surface/SDF 输入不应进入本实验，只能列额外输入参考 |
| [NEF](https://arxiv.org/html/2303.07653v2)、[Pauly 点云特征线](https://cgl.ethz.ch/Downloads/Publications/Papers/2003/Pau03b/Pau03b.pdf) | 连续 edge field、图像到参数曲线；点云 feature tracing 与 NPR | 连续场、点云 trace、无 mesh、最终 3D curves 都不是单独创新 |

EdgeGaussians 的大轴有 edge 语义，是因为其表示被专门训练和约束；不能把这个语义移植到 vanilla covariance。EMAP 明确列出 view-inconsistent edges 的限制。它们的成功与失败都要求直接比较输入条件，不能以“论文做过，所以本项目一定可辨识”替代试验。[EdgeGaussians §3/Appendix C](https://arxiv.org/html/2409.12886v1)、[EMAP Appendix D](https://arxiv.org/html/2405.19295v1)

最强拒稿意见是：

> 这只是 EMAP 加一个 GS depth/support mask，再接已有三维笔画 renderer。已训练 GS 用于线结构不新，固定曲线 NPR 也不新。你恢复的是图像边检测器的选择，既没证明内禀几何，也没证明 frozen GS 提供新信息；不变性通过可能只是算法忽略了 GS。

这是有效的批评。不能靠名称如“Gaussian-measure axial field”回避它。首轮即使通过，最多支持这个窄结论：

> 在明确的分辨率、观测域和静态视觉边子集上，冻结 vanilla GS 的某些支撑/遮挡信息经独立审计后，能改善多视图边的条件定位；其位置与方向对已测试的 RGB 近等价参数化扰动稳定，并比 Gaussian-center PCA 给出更有视觉价值的 raw 结构。

这个结论还不是新的 NPR 方法，更不是普遍几何可辨识性定理。可发表的方法贡献仍需一个实质机制或可验证诊断，证明何时应 abstain、如何区分 GS prior 的信息与偏差，并在最终 fixed-path、matched-ink 视频上超过强基线。后续至少需要 input-matched EMAP、EdgeGaussians、直接 SketchSplat/CurveGaussian 以及适用的 LineGS 和 3D stroke abstraction 参考；首轮只跑 PCA/null 不足以完成新颖性论证。

额外提醒：输入 novelty 报告提到的 2025–2026 邻近工作不能当作本次已全文验证。新检索还命中了 [SeCuRe 的期刊页面](https://www.sciencedirect.com/science/article/abs/pii/S0097849326000427)，本次只有检索摘要、未读正文，不以其算法细节或数字支持裁决。这进一步说明不能作“尚无同类工作”的穷尽性声明。

## 7. 文献核验范围

以下 URL 均为作者、原论文仓储或出版方来源。**全文能被工具打开不等于本次逐段读完。** 本次对外部论文按下表的实际阅读范围负责；除标明的短项目页，均不声称已全文审阅。关键数学判断中明确写作“本备忘录推论”的部分是分析，不冒充论文结论。

| 来源 | 本次实际核验；未完整检查的范围 |
|---|---|
| [原始 3DGS](https://arxiv.org/html/2308.04079) | 摘要、概述、参数优化说明；未逐段读完全部实验与附录 |
| [SuGaR](https://arxiv.org/html/2311.12775) | 摘要与 unorganized/surface-alignment 相关说明；未全文读完，不搬用其定量结果 |
| [RIMLS 作者页](https://www.labri.fr/perso/guenneba/publi/RIMLS_eg09/index.php) | 短项目页已完整检查；报告给定 HAL PDF 被验证页面拦截，其他 PDF 镜像亦未成功取得可读全文；不声称论文全文核验 |
| [Robust MLS PDF](https://www.cs.tau.ac.il/~dcor/articles/2005/Robust-Moving.pdf) | 摘要、引言与多片曲面构造动机；未逐页完整读完 |
| [Pauly 2003 PDF](https://cgl.ethz.ch/Downloads/Publications/Papers/2003/Pau03b/Pau03b.pdf) | 摘要、引言和管线/scale-space 部分；未逐页完整读完 |
| [Volumetrically Consistent Rasterization](https://arxiv.org/html/2412.03378) | splatting approximation 与 §4 射线积分公式；未全文读完 |
| [GOF](https://arxiv.org/html/2404.10772) | 摘要、引言与训练正则/opacity-field 定义；未全文读完 |
| [EMAP](https://arxiv.org/html/2405.19295v1) | §1–3、方向提取、部分补充实验与 Appendix D 限制；未逐段完整核对全部实验/附录与图 |
| [EdgeGaussians](https://arxiv.org/html/2409.12886v1) | §3 表示/监督、初始化训练细节与 Appendix C 限制；未全文读完。另确认存在 [WACV 2025 正式 PDF](https://openaccess.thecvf.com/content/WACV2025/papers/Chelani_EdgeGaussians_-_3D_Edge_Mapping_via_Gaussian_Splatting_WACV_2025_paper.pdf)，未进行版本逐项比对 |
| [CurveGaussian](https://arxiv.org/html/2506.21401) | §2–3 的问题定义与曲线表示；未全文读完，不引用性能排名 |
| [LineGS](https://arxiv.org/html/2412.00477v3) | 摘要、trained-GS 后处理说明及实验输入说明；未全文读完，不把其 Gaussian density 论断当成几何真值 |
| [SketchSplat](https://arxiv.org/html/2503.14786v2) | 引言、§4、默认 2DGS-SN 输入、补充限制/部分对照；未全文读完 |
| [3Doodle](https://arxiv.org/html/2402.03690) | §3.1–3.2 的固定/视变 primitives；未全文读完 |
| [WIR3D](https://arxiv.org/html/2505.04813v2) | SDF regularization、两阶段目标及相关消融说明；未全文读完 |
| [NEF](https://arxiv.org/html/2303.07653v2) | 原文页面可访问，核查标题/摘要层级；未全文读完，只用于已存在该范式的边界判断 |
| [AGPN](https://www.mdpi.com/2072-4292/8/9/710)、[Ohtake ridge/valley 原报告链接](https://pure.mpg.de/rest/items/item_1329814_3/component/file_3583968/content) | 本次直接访问失败；其具体方法描述仅由已完整阅读的输入报告提供。本裁决不以未经本次核验的细节作为关键证明 |
| [SeCuRe](https://www.sciencedirect.com/science/article/abs/pii/S0097849326000427) | 搜索命中/摘要层级，未读全文；仅记录新增文献风险 |

没有将输入报告对 EC-Net/DEF/NerVE/SGCR、Neural 3D Strokes、Dream3DVG、ViewCraft3D、Diff3DS、EdgeSplats、EdgeDoG 等的核验等级自动继承为本次的全文阅读。这些工作本次未独立完整核查；不据此主张性能优劣、发表状态或穷尽新颖性。

## 8. 下一动作与当前完成边界

下一轮只实施第 4–5 节的只读局部探针与隔离评估；预计以两场景、每组最多 256 条 edge 射线和 128 个表面诊断邻域控制成本。先给每场景 30 分钟计算上限，原 GS 训练预算为零，神经场训练预算为零；若基础 IO/渲染使预算耗尽，报告工程未完成，不把 timeout 写成科学 NO-GO。人工标注与匿名视觉审查单独记录成本。

在这之前不移植完整 EMAP、不搭建 RIMLS tracer、不增加 tensor voting、不拟合 Bézier、不改旧 pull/prune/path-cover。只有本基础门槛全部通过，才值得单独设计小型 raw UDF 实验；它仍需另有固定协议，不能把本探针的通过视为已完成连续场验证。

本备忘录是本次唯一持久写入，路径在仓库外。未修改、提交或运行仓库实验。最终只读 Git 核验见下方记录。

退出前核验（只读）：branch=`point-feature-foundation`；HEAD=`fc27b3e01085cb35edc8418c5e9b1be33ed5d067`；`git status --porcelain=v1` 为空；`git diff --exit-code` 与 `git diff --cached --exit-code` 均成功。与进入时一致。


# Execution clarifications frozen before any new scene render or method result

Author: Codex, primary implementing research engineer. This author is not an independent evaluator.

- Execution order is prerequisite first: input isolation, native renderer calibration, then both fixed perturbations on every TRAIN camera/background. If calibration fails, ENGINEERING_NOT_READY. If neither perturbation qualifies, UNDETERMINED and stop before local evidence/glyph/Chair work (memo §5.4). Unreached slices/artifacts will be explicitly recorded, not fabricated.
- Native path: pinned unmodified GRAPHDECO rasterizer 59f5f77e3ddbac3ed9db93ec2cfe99ed6c5d121d, already built under out/vrss/vendor/official_site. Decode its actual GeometryState/BinningState/ImageState and replay the native conic, sorted tile IDs, alpha clamp 0.99, alpha cutoff 1/255 and skip-triggering-splat early termination T<0.0001. Never call old disc renderer or defloat. Raw, unclipped stock RGB is calibrated; white-minus-black gives stock transmittance.
- Calibration checks every TRAIN pixel (stricter than foreground only), both backgrounds, maximum RGB and alpha errors <=1/255. Direct native final-T additionally checked. A synthetic off-center unequal-focal camera validates the adapter. Nonzero skew is rejected by the stock adapter (full fx/fy/cx/cy supported); geometric Jacobian includes full K.
- Baseline foreground ROI is alpha >=0.5, frozen once per view; no photo/edge-dependent ROI. Qualification uses raw float stock RGB, PSNR over foreground RGB, SSIM with Gaussian sigma=1.5/window=11/K1=.01/K2=.03/population moments/data_range=1, minimum of the three channel ROI means. P99 is the 99th percentile of the maximum absolute RGB channel difference per ROI pixel (stricter than pooled channels). Every TRAIN view and both backgrounds must pass. Coverage >=20% must hold separately in every view, stricter than pooled coverage. Empty ROI is invalid.
- Parents: canonical original PLY row order; SHA256 of UTF-8 `20260918:parent:<index>`, lowest floor(N/2) hashes selected exactly once, before renders. Selected parents are replaced in-place by minus/plus children; stable input order is the stock equal-depth tie-break. Clone center/covariance/SH identical; split maximum local scale axis (lowest axis index on ties), scale along that axis *=sqrt(.96), offsets +/-0.2*s_max*axis. No amplitude or parent reselection. Row shuffle is a separate synthetic/native IO check, not an invariance intervention.
- Wide box uses NumPy linear quantiles .001/.999 and expands all six faces by .1 times the original box diagonal. Outside-parent contribution is counted without deleting any primitive; >1% in any TRAIN view is invalid. Delta will use conditional per-ray median center-depth / sqrt(fx*fy), median over all 16 TRAIN foreground rays, baseline only. This choice equals z/f for these square calibrated cameras.
- Native access isolation uses Linux Landlock read-only exact input allowlists and writable run-output directory, with strace open/openat/openat2/creat audit covering native IO. F and C have separate directories and separately restricted processes when reached. User namespaces are disabled on this server; Landlock is the kernel-enforced alternative, not a claim of mount namespaces. Runtime library directories may be readable but repository caches/data and arbitrary home files are not. No method process will open DEV/TEST/photos/mesh or historical arrays. Prerequisite renderer reads no photographs at all.
- TRAIN-only annotation materials will be prepared before any local method output if that stage is reached; internal marks cannot certify independent G2/G5. No independent human annotators/reviewers are available in this session. G2 manual precision and G5 remain UNCERTIFIED. DEV stays unopened until a method-output freeze and independent annotation sequence is possible. No synthetic annotations will masquerade as observations.
- Scientific budget is 1800 seconds/scene; record perturbation qualification separately within scientific prerequisite time, native calibration/build/setup separately. No timeout will be called a scientific failure. No Chair unless Lego machine prerequisites pass. No downstream rescue.
- All remaining numeric rules and controls are exactly those in the copied memo above. Implementation details for unreached downstream work must be frozen before any C/DEV evidence is seen.
