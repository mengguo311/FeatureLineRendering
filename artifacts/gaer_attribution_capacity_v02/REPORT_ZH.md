# 实际归因与线容量诊断（v02）

两场景的八源全 N oracle、两源完整稀疏 ROI、原参数 ± 扰动、四图 800×800 全 N perview/shared 黑墨拟合，以及限定原生 shape 能力测试均已实际完成。结论是 **原足迹能形成可辨线结构，但完整窄线与深色平台仍为 PARTIAL / 人工视觉验收待定**。不能把未收敛视图、有限 ROI 或固定 λ 的结果称为全表示 NO-GO。

GPU诊断前冻结提交 `0b77071`；PROTOCOL SHA256 `4218282d0823f0b530089af4b75555f03606071aea4e68e03838fd7f96111132`。原模型/旧阶段 5,535 文件哈希保持不变。旧“工程映射完成、无D优势”结论与其失败记录全部保留。

## 六个问题的直接回答

1. **截断是主要限制吗？** K8严重改变冻结样本的D赢家与回退；K32仍不等于完整。完整记录并未单独证明D更好，不能把截断称为最终线绘唯一或主要限制。 状态：`SEVERE_FOR_D_NOT_PROVEN_PRIMARY_VISUAL_LIMIT`。

2. **完整记录后D胜过center吗？** 实际DC/logscale成对扰动已运行；单赢家D在两场景/ROI上优劣不一致，multiD常较局部但可见质量/面积不同；没有普遍优势或因果边责任结论。 状态：`NO_CLEAR_UNIVERSAL_ADVANTAGE`。

3. **旧选择距B上界多远？** B500/2000八源 raw 达源域上界约80–83%，center更接近；两个已知诊断视图 raw 仅达 pooled 上界约11–31%。必须区分源域、已知答案域和perview适配。 状态：`MEASURED_FULL_N`。

4. **理想强度下原足迹能形成线吗？** 全N连续强度确实生成可辨线结构，远超固定少量二值核；窄峰/深色平台/轮廓仍有误差。四个perview未达到冻结近最优证书，其他perview及两个shared已有证书；只对冻结E/外域λ=1目标有效，不是全表示不可能证明。 状态：`RECOGNIZABLE_LINES_PARTIAL_FIDELITY_HUMAN_PENDING`。

5. **固定集合和视角激活限制？** 诊断perview固定B上界高于pooled；同四图 perview连续目标误差低于shared，仍含已知答案。固定八视角集合、单赢家、view activation 是不同约束；不是泛化算法。 状态：`BOTH_VIEW_ADAPTATION_AND_JOINT_STRENGTH`。

6. **需要shape吗，有何剩余限制？** 每场景32原核法向2/4缩窄已原生重算T，改善极小；中心未移动，所选核总强度小，不能判定shape必需或足够。单独报告nearest旧mask法向偏移；初次更严格gate的NOT_RUN保留。 状态：`TINY_NATIVE_CAPABILITY_NO_SUFFICIENCY_EVIDENCE`。

## 实际图与数据

| 场景 | 四图全图原生容量 | 两保留图同预算oracle | 原生shape固定ROI | 原参数扰动profile |
|---|---|---|---|---|
| lego | [四图](media/lego/fourview_known_target_capacity.jpg) / [原生PNG](media/lego/capacity/r_001_perview_native.png) | [同图同gain](media/lego/two_holdout_native_oracles.jpg) | [24px最近邻](media/lego/conditional_shape_ROI_nearest.png) | [全部冻结ROI](media/lego/all_frozen_probe_profiles.png) |
| chair | [四图](media/chair/fourview_known_target_capacity.jpg) / [原生PNG](media/chair/capacity/r_001_perview_native.png) | [同图同gain](media/chair/two_holdout_native_oracles.jpg) | [24px最近邻](media/chair/conditional_shape_ROI_nearest.png) | [全部冻结ROI](media/chair/all_frozen_probe_profiles.png) |

源/保留相机均是历史研究见过的相机。oracle 的八源排名只用八源E；两个保留图 pooled/perview oracle 直接知道评价答案，只是域内上界。容量拟合 r_000/r_018/r_001/r_014 四图全部知道答案；perview和shared同一四图池，不构成泛化测试。

## 截断与H1校正

| 场景 | 全部冻结样本 | K8→full赢家变化 | K32→full赢家变化 | 标注样本K8→full变化 | 原回退变full有效 |
|---|---:|---:|---:|---:|---:|
| lego | 325 | 155 | 20 | 45/72 | 46 |
| chair | 400 | 230 | 54 | 75/83 | 74 |

D为 `|w_i(p−2n)−w_i(p+2n)|`，候选必须中心可见。[ROI排名收敛审计](tests/ROI_RANKING_CONVERGENCE.json)保存四种score在同ROI上K8/16/32到full的TOP8变化，以及含未知center候选的充分赢家区间。初始K8/16/32 JSON的winner_certified_margin_pixels名称只计保留集间隔，不能证明full赢家；需best下界超过其余及未见ID上界。旧残量小于最大D的回退门控也不等于赢家认证。multiD TOP8平均Jaccard依次Lego .597/.725/.897、Chair .533/.629/.832。完整双遍查询原生分桶及接收序列，只查询冻结点/端点/25px profile 的整数邻居，按原ID双线性合并；不插值槽位，不建 H×W×N。全部格点保留，包括未标注/未定义normal/无中心贡献。Lego自动政策只找到 r_000 的1个flat_negative，r_018无合格flat；没有补选。

原生有效 SH3 颜色使用 mean−camera 方向、每通道max(SH+.5,0)，无上限clamp、无额外EOTF。官方CPU SH3函数独立校准，ROI RGB/alpha回放误差约10⁻⁶，signed分解 `ΔRGB=Σ c_i Δw_i + bg ΔT` 通过固定容差。相同原ID/权重、同色可有大D而RGB差为0；Σ|D|不能抵消。Lego平坦负例平均ΣD≈.821，而RGB双侧差范数≈.008，颜色项抵消约99.1%。H1应叫**法向贡献变化**，没有RGB因果责任标签。

首轮近零颜色分母导致的cancellation展示负大数已保留原封印；[独立FP64归一化审计](tests/ROI_INDEPENDENT_AUDIT.json)给出修正及低信号标志，未改变赢家/选择/扰动。原生CSR、原始ID、有效颜色、全部K理由/赢家/残量/间隔与逐ROI全N分数在 downloads/*/*ROI_full_CSR.npz。

## 同预算线质量上界

TopB取全N `b_i=Σ_vΣ_E w_i` 最大系数，在原始完整T固定时最大化线域总质量；不限制泄漏。FP32颜色梯度使用全部接收贡献，没有topK截断。FP64原接收权重审计给出舍入差与最大可能次优质量；冻结排名未据结果改动。上界不适用于删核、opacity或covariance变化。

| 场景 | B | 八源raw/源上界 | 八源center/源上界 | 保留域raw/pooled上界 | pooled/perview上界质量 |
|---|---:|---:|---:|---:|---:|
| lego | 500 | 80.25% | 82.15% | 21.89% | 4684.76 / 6355.71 |
| lego | 2000 | 83.00% | 85.71% | 31.48% | 11447.59 / 15128.85 |
| chair | 500 | 81.80% | 86.87% | 10.70% | 5873.34 / 7043.67 |
| chair | 2000 | 83.31% | 87.00% | 18.03% | 12905.46 / 15141.66 |

以下在同两个保留图累计；质量召回、阈值覆盖和非线泄漏是三个指标。不是把“支持质量”当成干净墨线。

| 场景 | 集合 | 线总质量 | 质量召回 | 覆盖>.1 / >.5 | 非线质量泄漏 |
|---|---|---:|---:|---:|---:|
| lego | raw_500 | 1025.58 | 1.46% | 5.06% / 0.37% | 86.55% |
| lego | center_500 | 1154.70 | 1.64% | 5.90% / 0.43% | 83.75% |
| lego | source8_oracle_500 | 1213.89 | 1.73% | 5.39% / 0.42% | 87.96% |
| lego | diagnostic2_pooled_oracle_500 | 4684.76 | 6.66% | 19.49% / 4.55% | 81.28% |
| lego | raw_2000 | 3603.94 | 5.12% | 17.62% / 2.24% | 84.35% |
| lego | center_2000 | 3704.16 | 5.26% | 18.16% / 2.64% | 81.47% |
| lego | source8_oracle_2000 | 3715.49 | 5.28% | 16.04% / 1.98% | 85.53% |
| lego | diagnostic2_pooled_oracle_2000 | 11447.59 | 16.27% | 40.00% / 12.56% | 80.24% |
| chair | raw_500 | 628.72 | 0.83% | 2.58% / 0.22% | 81.98% |
| chair | center_500 | 626.47 | 0.82% | 2.62% / 0.21% | 80.80% |
| chair | source8_oracle_500 | 976.07 | 1.28% | 3.70% / 0.22% | 80.26% |
| chair | diagnostic2_pooled_oracle_500 | 5873.34 | 7.72% | 26.71% / 1.09% | 73.42% |
| chair | raw_2000 | 2326.62 | 3.06% | 9.72% / 0.85% | 78.32% |
| chair | center_2000 | 2288.99 | 3.01% | 9.54% / 0.83% | 77.56% |
| chair | source8_oracle_2000 | 3268.71 | 4.30% | 13.32% / 0.81% | 78.76% |
| chair | diagnostic2_pooled_oracle_2000 | 12905.46 | 16.97% | 48.06% / 8.00% | 73.22% |

旧raw多数像素回退至center（八源Lego65.53%、Chair80.95%），不是纯D。新oneD组也保留固定normal/数值条件的center回退。单赢家会丢共同强度；八源固定集合不是逐图边集合。旧full-T baseline仅验证原封印并读缓存；没有重新做旧buffer/vote工程检查。另导出原生白背景颜色1−s的实际RGB，确认与1−feature质量在3e−6内一致。删除核后的原SH子集并非此处黑墨。

## 实际小扰动

每场景r_000自动ROI全部参与；每方法每组8原ID，DC±.02/±.01（有效未clamp RGB改变量=.28209479×DC）、logscale±.03/±.015，原全SH3保持。克隆被编辑参数，不改输入。五方法同数量、同权限、同渲染次数；random按全视可见质量及投影面积匹配，不匹配局部位置，可能和主组重叠。

| 场景 | 方法 | DC局部响应占比均值 | logscale局部响应占比均值 |
|---|---|---:|---:|
| lego | center | 0.872 | 0.798 |
| lego | oneD | 0.909 | 0.780 |
| lego | multiD | 0.917 | 0.818 |
| lego | color_signed | 0.894 | 0.736 |
| lego | matched_random | 0.000 | 0.000 |
| chair | center | 0.727 | 0.569 |
| chair | oneD | 0.677 | 0.593 |
| chair | multiD | 0.730 | 0.667 |
| chair | color_signed | 0.707 | 0.546 |
| chair | matched_random | 0.007 | 0.002 |

这些是整图导数能量落入24×24目标ROI的比例，不是修复率或语义正确率。center/oneD/multiD/color_signed可见质量及面积不相同，完整JSON保留其代价、random匹配残差、外域/其他ROI MSE、alpha阈值覆盖损伤及半幅导数差。小幅SH clamp与raster接受阈值会使半幅不完全线性。profile保存25个normal像素的实际RGB±值、导数、中心/gradient-width/端点contrast/TV excess；原边没有错误目标，不能称“改善”。

## 原足迹全图已知目标容量

实际原生外观为 `color_i=1−s_i`，白背景，全部原位置/scale/rotation/opacity/T保留，0≤s≤1。原生 `I=1−Σw_i s_i`，feature A与AT adjoint和白背景公式的新fixture及四图检查通过。

**冻结主目标**为 `f=(Σ_E(A−L)^2+Σ_out L^2+λΣ_out A^2)/(2HW)`，λ=1；E=L>.2内仍使用连续L，弱墨迹及零墨域都被当外域压向白，弱域原L²是常数。此目标不是全像素连续L拟合；全图与原连续L的MSE另外报告，不能混称。shared取同四图目标平均。全N连续解不是等B算法优越性比较，也不是紧凑边资产。

FISTA/power/backtracking与两初值预算冻结为500/120步，保留最好可行值。原生FP32优化；独立FP64接受权重的Fenchel dual下界验证于显式小矩阵，保守FP64舍入界及预声明余量全部减去。完整loss/PG/dual日志在 downloads/*/known_target_solver_logs.csv。0.5% gap阈值未达者写预算内未认证，不扩大预算、不能据其失败下NO-GO。

| 场景 | 相机/共享 | primal / dual lower | 相对gap | 近最优状态 |
|---|---|---:|---:|---|
| lego | r_000 | 0.0043748 / 0.0043445 | 0.692% | MAX_BUDGET_UNCERTIFIED |
| lego | r_018 | 0.0060631 / 0.0060355 | 0.455% | CERTIFIED_WITH_ROUNDOFF_ALLOWANCE |
| lego | r_001 | 0.0051884 / 0.0051643 | 0.464% | CERTIFIED_WITH_ROUNDOFF_ALLOWANCE |
| lego | r_014 | 0.0067699 / 0.0067367 | 0.491% | CERTIFIED_WITH_ROUNDOFF_ALLOWANCE |
| lego | shared | 0.0067853 / 0.0067526 | 0.481% | CERTIFIED_WITH_ROUNDOFF_ALLOWANCE |
| chair | r_000 | 0.0023227 / 0.0022805 | 1.818% | MAX_BUDGET_UNCERTIFIED |
| chair | r_018 | 0.0039692 / 0.0039233 | 1.155% | MAX_BUDGET_UNCERTIFIED |
| chair | r_001 | 0.0048461 / 0.0048242 | 0.454% | CERTIFIED_WITH_ROUNDOFF_ALLOWANCE |
| chair | r_014 | 0.0053025 / 0.0052718 | 0.579% | MAX_BUDGET_UNCERTIFIED |
| chair | shared | 0.0051855 / 0.0051613 | 0.468% | CERTIFIED_WITH_ROUNDOFF_ALLOWANCE |

| 场景 | perview平均全连续L MSE | shared同池MSE | perview平均主目标 | shared主目标 |
|---|---:|---:|---:|---:|
| lego | 0.0085735 | 0.0110052 | 0.0055991 | 0.0067853 |
| chair | 0.0058152 | 0.0079010 | 0.0041101 | 0.0051855 |

原始ID strength NPZ包括全N而非假compact集合，view/source SHA、0/1约束、活动数量/强度总量/饱和数均有记录。原全SH3输入未变；共享和逐图actual native RGB独立导出。有限原足迹必有A≤full accepted alpha；[pixel envelope](results/PIXEL_ENVELOPE_BOUNDS.json)给出独立像素松弛的必要误差下界，不证明所有其他样式都不可能。

## 条件原生shape与剩余限制

冻结协议允许“任一perview已认证且线残差>.01”触发固定r_000。初次runner过严要求r_000自身认证，所以保存的shape NOT_RUN是工程gate记录；补充anyview条件单元按冻结规则实际完成。每场景两个固定fragment各16原ID，双角平均normal，法向方差÷2²/4²并保留.3像素协方差下限；tangent方差保留、cross置零，中心固定。isolated单行cov2D override发生在逆矩阵/半径/tiles之前；重跑整个native流水线与T。stock无determinant AA opacity补偿，峰值opacity保持；没有2D画线代理。

lego：实际编辑32核、其原拟合强度总和1.581；原线MSE 0.128486，ratio2/4为0.128441 / 0.128455。全T/alpha变化有实际地图与计数。
chair：实际编辑32核、其原拟合强度总和2.873；原线MSE 0.099038，ratio2/4为0.099045 / 0.099028。全T/alpha变化有实际地图与计数。

改动少、所选强度小，效果微弱不能作为shape必要性/充分性证明。初始shape JSON中的offset字段实际是相对fragment中心的法向偏移，不能当最近线距离；[关联审计](tests/SHAPE_ASSOCIATION_AUDIT.json)另存每ID到冻结marked像素的nearest法向偏移。窄化不移动中心，background/外侧目标、重叠宽足迹、固定强度跨视角与强度预算仍可能分别限制质量。

## 下一项与状态

只选择 **allocationaggregation：联合贡献分配与强度聚合** 作为下一研究方向。实际连续共同支持能形成线结构，单赢家/固定少量二值集合损失很大；本轮没有证明新选择算法或perview预测能泛化。形状缩窄没有显示明显充分性，所以不据此优先进入更长shape优化。

工程算子READY；部分拟合预算内未认证；原足迹视觉PARTIAL；完整干净窄线视觉GO人工待定。optional opacity/λ敏感性/长shape轨迹均NOT_RUN（协议中未启用）；新训练/新detector/新视角未做。已保存[工程问题](tests/ENGINEERING_FAILURES.json)、初次NOT_RUN和此前全部失败，不因新图更好覆盖旧结论。

[复现说明](REPRODUCE.md)、[最终JSON](FINAL.json)、[新数学fixture](tests/NEW_MATH.json)、[FP64证书fixture](tests/FP64_CERTIFICATE.json)、[独立保存结果审计](tests/INDEPENDENT_ARTIFACT_AUDIT.json)、[保护哈希](tests/PROTECTED_AFTER.json)。
