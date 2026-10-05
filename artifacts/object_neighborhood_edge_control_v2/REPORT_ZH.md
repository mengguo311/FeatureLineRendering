# v2 原生实验执行报告

本报告记录新实测；245e056 的公开指标重分析属于历史报告复核。单场景单种子诊断不构成正式 GO。旧高对比 TEST/path 已成为探索性开发资料，原一次封印评价仍保留；旧低对比/远背景 TEST 未读取。独立新 TEST 保持 **TEST_CLOSED**。

## R0：原 checkpoint 只读扫描

实际 checkpoint SHA256：`cc440283b70bf62cd98dfedf24bf47383a147b70483deec4f849763f3f7847c6`。N=10659，固定 C1=1379。有效颜色范围 [0, 1.2257]，候选超盒通道 2。零步投影与对称扰动独立记录。贡献覆盖不是错误核召回；表面中心/厚度仅使用 z=0 oracle 作评价代理。

| 角色 | band MSE（float） | W px | 可测率 | 全前景孔洞 | 外轮廓 MSE |
|---|---:|---:|---:|---:|---:|
|train|1.68138e-05|0.00402897|1.0000|0.0018443|0.000475169|
|dev-out|0.00955047|5.94081|0.8382|0.00545519|0.0188411|
|dev-in|1.52544e-05|0.00383378|1.0000|0.00180677|0.000629253|

## R1：固定权重颜色能力（首轮600步；最终收敛补充见后表）

原生 override_color 和颜色反向的 A/Aᵀ 使用固定排序、alpha 与提前终止；无 N×H×W 张量。每个 Gaussian 跨视角共享 RGB，非候选有效颜色保留 SH0 下限截断及 >1 值。逐像素区间下界仅为必要条件。视角等权，权重后的 MSE=2P/M，float32 原生算子采用 float64 求和及预先固定的 3e-7 MSE 数值余量。

| 单元 | 拟合角色/集合 | P 上界 | D 下界 | gap | MSE 上/下界 | 状态 |
|---|---|---:|---:|---:|---|---|
|F00|train / 1379|3.57133|3.06499|0.506344|1.48044e-05 / 1.27054e-05|UNDETERMINED_OPTIMIZATION|
|F01|train / 10659|3.55412|2.9037|0.650413|1.4733e-05 / 1.20369e-05|UNDETERMINED_OPTIMIZATION|
|F10|train + diagnostic-supervision / 1379|176.494|173.045|3.44941|0.000627365 / 0.000615103|UNDETERMINED_OPTIMIZATION|
|F11|train + diagnostic-supervision / 10659|150.854|146.784|4.06996|0.000536226 / 0.000521759|UNDETERMINED_OPTIMIZATION|

F10/F11 使用额外诊断监督，只是能力参照，不参加仅原 train 方法排名。全体 Gaussian 是容量支线。gap 大时只报告优化未充分；即使数值下界超过阈值，也只涉及该固定权重和盒约束，不推断 3DGS 基本极限。所有角色分别评分，增加诊断监督后重新计算实际内插/外推状态。band-only 的 outside 损伤完整保存，不作为合格修复。

条件 outside 对照 F00_outside：最终 {'iteration': 300, 'band_mse': 1.480604692005727e-05, 'outside_mse': 5.2425990400746985e-09, 'seconds': 28.713440198916942}，fit 角色 ['train']；保持 band MSE 目标，非 L1 替代。
条件 outside 对照 F01_outside：最终 {'iteration': 300, 'band_mse': 1.4732752409448343e-05, 'outside_mse': 1.0422554837704231e-08, 'seconds': 18.226382213877514}，fit 角色 ['train']；保持 band MSE 目标，非 L1 替代。
相同 v1 凸目标（量化 train band L1 + outside MSE）：原 Adam 全视角目标=0.00084563237；Chambolle–Pock 可行目标=0.00064935769，对偶=4.2253873e-05，gap=0.00060710382。有限预算尚有 gap 时不称已证明最优；band MSE 最优值不能代替 L1 证明。

## R2：7000 步 2×2 底座诊断

四组全部实际重训练，4096 初始点、SH0、同一 24 张量化线性 PNG、同一增密与学习率日程。surface 仅给 z=0 表面中心，颜色恒为 127/255，无真 UID 标签；原生最近邻尺度随初始化制度改变。oracle 正则中心离面与法向厚度，tau=0.015 场景单位，未用中心深度代替表面监督。每 epoch 保存全部训练相机 RGB 目标与几何项。

| 分支 | 初始化 | oracle | 最终 N / 参数 | 秒 | dev-out band MSE | dev-out W |
|---|---|---|---:|---:|---:|---:|
|G00|byte-exact original seeded random-volume point cloud; native nearest-neighbour scale|False|10628 / 148792|80.6|0.00721988|3.63427|
|G10|uniform known z=0 panel surface; native nearest-neighbour scale|False|14054 / 196756|83.8|0.00053732|1.00287|
|G01|byte-exact original seeded random-volume point cloud; native nearest-neighbour scale|True|10187 / 142618|173.8|0.000692257|0.729752|
|G11|uniform known z=0 panel surface; native nearest-neighbour scale|True|13880 / 194320|182.9|0.000322115|0.661993|

band MSE 因素效应/交互：`{"G01-G00": -0.006527623405418126, "G11-G10": -0.00021520532391150482, "G10-G00": -0.006682559872388083, "G11-G01": -0.00037014179088146193, "interaction": 0.006312418081506621}`。最终 N 不同，需要数量匹配确认后才能作正式因果优势或效率排名。未追加 14000 步；不把新的学习率策略混为唯一迭代数改变。

## R3：原 B0 同权限对照

各组相同 B0、固定 1379 UID、固定 ROI/标签/opacity/中心；O-color 与 O-cov 共用 band L1 + outside MSE + coverage。普通微调使用全图 0.8 L1+0.2 SSIM，加相同 coverage，并具有完全相同参数权限。协方差组实际检验 coverage→scale/rotation 梯度。可靠前景（coverage>0.99）不透明约束与外缘连续 AA coverage 分开处理；报告 band、非 band 和全前景孔洞。

| 分支 | 步数 | 优化秒 / 预处理秒 | dev-out band MSE | outside 损伤 | 全前景孔洞 | 配对 W（前→后/条数） |
|---|---:|---:|---:|---:|---:|---|
|O_color|336|5.430 / 2.328|0.00952566|4.40453e-06|0.00545519|5.940813467990116 → 5.9340347406156795 / 57|
|O_color_ordinary|336|6.095 / 2.373|0.00956282|1.56208e-06|0.00545519|5.940813467990116 → 5.948477194946327 / 57|
|O_cov|336|6.708 / 2.456|0.010199|1.12648e-05|0.00528934|5.940813467990116 → 5.878197816438721 / 57|
|O_cov_ordinary|336|7.908 / 2.392|0.0100327|1.06563e-05|0.00516192|5.940813467990116 → 5.9434492185384595 / 57|
|O_color_ordinary_time|292|5.439 / 2.371|0.00956631|1.42835e-06|0.00545519|5.940813467990116 → 5.946675506650045 / 57|
|O_cov_ordinary_time|309|6.717 / 2.367|0.0100027|9.53588e-06|0.00503279|5.940813467990116 → 5.918210379272745 / 57|

## R4 / R5 / 正式阶段

R4：自然局部操作未显示 10% 开发潜力，条件触发了六组可恢复尺度探针，结果见末表；短优化失败仍不等于无可行解。

R5：可恢复尺度探针显示控制潜力后，条件执行了三态支持距离与支持包围盒的工程诊断。原 epsilon=0.02 保留，原 1379 UID 不重选。仅评测预先规则选出的诊断子集及明确几何定义的解析例，不声称完成全模型成本优化或物理接触检测。

未开启 opacity/position、拆分、软边、m(x)、新 kernel、多场景三种子或独立新 TEST。现有工程 pilot 不能支持 H1–H5 方法优势。旧低对比 no-op 和远背景 C1 跨阈值拒绝仅引用历史证据，本轮没有打开这些 TEST。

## 封印、成本与限制

量化 train 与浮点参考同时评分；全前景和外轮廓独立保存。W 同时给可测率/拒绝原因和共同有效剖面配对，缺失不当作零。新底座标签均 unknown，mask/foreign 分数不用于底座排名。原 C1 约 404.5 秒选择预处理来自历史测量，本轮复用固定集合；新控制预处理与优化墙钟分别记录，等步骤与等优化时间普通对照均保存。视频为实际 36 帧开发路径 H264/yuv420p/faststart，每帧完整解码验 SHA；未实测重投影时间稳定优势。

dev 门槛：`{"O_color": {"band_improvement": 0.0025974397080721356, "dev_in_mse_increase": -2.2241404925201286e-07, "psnr_drop": -0.16662905759326208, "hole_increase": 0.0, "pass": false}, "O_cov": {"band_improvement": -0.06790221671549079, "dev_in_mse_increase": 4.851831666504344e-06, "psnr_drop": 0.14243835968914098, "hole_increase": -0.00016585677296523504, "pass": false}}`。即便绝对门槛通过，仍需超过同权限普通微调并完成多个场景/种子，才可开启正式结论。独立 TEST_CLOSED 的工程原因是开发门槛/方法优势/正式数量匹配与多种子证据尚未完成，不能用新 TEST 帮助拟合。


### R4 实际条件触发结果

R4_C1_color: before=0.0368033, after=0.0265668, improvement=27.814%; known-UID solver does not read original scales/amplitude.
R4_C1_scale: before=0.0368033, after=0.00479274, improvement=86.977%; known-UID solver does not read original scales/amplitude.
R4_all_color: before=0.0368033, after=0.0264802, improvement=28.049%; known-UID solver does not read original scales/amplitude.
R4_all_scale: before=0.0368033, after=0.00466026, improvement=87.337%; known-UID solver does not read original scales/amplitude.
R4_known_color: before=0.0368033, after=0.0302582, improvement=17.784%; known-UID solver does not read original scales/amplitude.
R4_known_scale: before=0.0368033, after=0.00698092, improvement=81.032%; known-UID solver does not read original scales/amplitude.
## R1 同目标收敛补充（实际续算）

对角预条件只改变求解流程，固定权重、盒范围、相机、目标与归一化保持一致；原 600 步结果保留作为优化日志。AᵀA1 的非负权重主化关系经 CPU 数学测试和真实原生算子二次型验证。

| 单元 | P 上界 | D 下界 | P-D | 归一化 gap | MSE 上/下界 | 追加迭代 | 判读 |
|---|---:|---:|---:|---:|---|---:|---|
|F00|3.5121603|3.2710602|0.24110015|9.9944306e-07|1.4559113e-05 / 1.355967e-05|91|FEASIBLE_WITHIN_TOLERANCE|
|F01|3.4365275|3.1990071|0.23752043|9.8460391e-07|1.4245589e-05 / 1.3260985e-05|128|FEASIBLE_WITHIN_TOLERANCE|
|F10|175.54681|175.26934|0.27747117|9.862959e-07|0.00062399671 / 0.00062301041|236|NUMERICALLY_BOUNDED_UNREACHABLE|
|F11|149.68763|149.40792|0.27970745|9.9424494e-07|0.00053207795 / 0.0005310837|257|NUMERICALLY_BOUNDED_UNREACHABLE|

数值下界对应原生固定权重和有效 SH0 颜色 [0,1] 的操作权限，带预先冻结 3e-7 MSE 有限精度余量；不把它推广为 3DGS 固有极限，不唯一归因于位置、尺度或选核。需要更严格的误差预算时保留数值认证边界；本轮不发布一般表示不可达定理。F10/F11 的 dev-out 数据角色中，22/26/30° 已成为其实际训练范围内插值，仅38°仍为外推；各行相机状态详见 SUPPLEMENTAL_AUDIT.json。额外诊断监督不参加仅原监督方法排名。

相同 v1 band L1+outside MSE 续算：可行 P=0.000578613346，D=0.0005464707，gap=3.21426453e-05；原 Adam 同目标=0.000845632368。可行目标降低 31.58%，gap 高于1e-6，状态仍为 UNDETERMINED_OPTIMIZATION，尚未认证最优；只能比较已得到的可行解。这项改善不等于开发外推修复，不借用 MSE 目标最优值证明 L1 最优。

## 全域、配对剖面与端到端费用补充

| R2 分支 | dev-out 可测率 | 全可靠前景孔洞 | 外轮廓 MSE | 全部7000步秒 / 单元总秒（含准备、评价） |
|---|---:|---:|---:|---|
|G00|0.7206|0.01244927|0.0212672|80.575 / 90.899|
|G10|1.0000|0.0008433355|0.002691624|83.832 / 93.521|
|G01|1.0000|0.003046786|0.009905236|173.763 / 183.807|
|G11|1.0000|0.0008677062|0.002241552|182.936 / 192.843|

G00 最后1000步 RGB目标接近平稳且轻微波动，未启动长度扩展。R2 的最大分配显存包含随后评价，不能当成纯训练峰值做效率优势主张。共同有效剖面需按每视角配对；R3 表已使用共同剖面，R2 宽度需结合上述可测率与逐剖面 JSON，不因拒绝更多剖面宣称更好。

完整 C1 选择历史实测 404.497 秒，本轮固定集合复用。冷启动费用需再加该成本；v2 单元总墙钟含准备和评价，R3 单独记录优化墙钟及预处理。等墙钟普通对照包括实际目标日志开销，不是纯 CUDA kernel 时间。所有组基于训练 mask 的贡献代理标签和固定 coverage；不宣称完全无 mask 的 RGB-only 端到端系统。

R5 实际诊断子集 N=64，包围盒候选对=361，三态计数={'support_near': 160, 'support_far': 201, 'uncertain': 0}，查询 0.00814779 秒、上下界求解 2.59444 秒。已知跨阈值区间返回 uncertain。解析例将 contact、near-noncontact、远平面/大 Gaussian 支持代理分别保存；远表面可以有 support_near，因此仍不能把支持相交当物理接触。该子集成本不能替代原全量404.5秒成本。

R0 的相机横向协方差投影宽度、贡献权重、量化误差底限，以及 O-cov 最终完整训练 epoch 的分项梯度均有新增实测审计；梯度只验证连接，不跨单位排名。新 TEST 的尺寸/姿态条件与相机已冻结，但姿态后边界法向评价器和目标生成扩展尚未验证，这也是保持 TEST_CLOSED 的工程原因。三条视频各36帧全部解码，包含失败的完整视角；未评测或宣称时间重投影优势。

## 可检查的图表与媒体

- [原始600步颜色求解轨迹](figures/R1_actual_convergence.png) 与 [同目标续算轨迹](figures/R1_refined_actual_convergence.png)。
- [四组实际训练目标和数量曲线](figures/R2_actual_curves.png)。
- [同一 v1 凸目标首轮轨迹](figures/C1_exact_objective_actual.png)，4000步续算详见 results/C1_exact_convex_refined.json。
- [38°同相机完整图](figures/O_cov_dev-out_003_full.png) 与 [固定边缘放大图](figures/O_cov_dev-out_003_edge.png)，三列分别为参考/B0/O-cov。
- 完整36帧开发路径：[B0](videos/R0_B0_devpath.mp4)、[O-color](videos/O_color_devpath.mp4)、[O-cov](videos/O_cov_devpath.mp4)。

归因边界：原 train 的固定颜色可以达到本轮容差；额外诊断监督下，即使全体颜色仍有高数值下界，支持继续检查权重或底座重建。R2 的表面/平面先验诊断有改善，R3 的当前局部自然修复没有独立收益。R4 证明受控尺度故障有恢复潜力，不能把它当作自然错误的唯一物理解释。B1/C1原来使用同1379 UID，差异主要为损失；这些结果不单独证明三维选核失效。

## R2 共同有效剖面配对补充

以下是原生结果的配对重聚合，没有新增渲染或打开TEST。参考、原B0与四组底座同时可测的剖面取共同集合，每视角先平均再按视角平均，不将拒绝样本记为零。

| 角色 | 共同剖面 / 有效视角数 | 原B0 W误差 | G00 | G10 | G01 | G11 |
|---|---|---:|---:|---:|---:|---:|
|train|408 / 24|0.00402897|0.00603142|0.00443358|0.0035684|0.00604032|
|dev-in|102 / 6|0.00383378|0.00573416|0.00381362|0.00380542|0.005654|
|dev-out|44 / 4|6.38482|3.65977|1.07926|1.09918|0.636812|

逐相机共同索引与各自拒绝情况见 [R2_COMMON_PROFILES.json](results/R2_COMMON_PROFILES.json) 和各方法逐剖面结果；band MSE仍评价所有固定band像素。
