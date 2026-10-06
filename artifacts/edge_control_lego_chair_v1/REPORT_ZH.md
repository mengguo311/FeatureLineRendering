# Lego / Chair 实际原生局部边缘编辑报告

本轮直接加载两份 30000 步 PLY，保留完整 SH degree=3；使用 stock 3DGS 原生 CUDA forward/backward。监督来自实际原始 TRAIN Blender PNG，loss 保持原训练的显示 RGB 编码。仅剖面测量用明确 sRGB EOTF 转到线性 RGB。没有读取原始 TEST 图像，没有重训练底座。

两场景均是单前景物体；只找到原 PNG 的 AA alpha，未找到可信部件标签。因此执行的是 **label-free relative edge-support/local-control**，不是 object-pair contact / C1。内部 RGB 边缘与外轮廓分别评价。核贡献是可见支持责任，不是物理边缘身份；原 JointLeak 负例未改。

每场景固定 8 edit-train + 4 dev + 8 edit-holdout；全部属于原 GS TRAIN-seen。F/C/既有 arc 已被旧研究使用，8 个新 edit-holdout 也不能证明此前全研究未见；本轮只有封印后只读的探索性编辑留出评价，**不是独立正式 TEST**。所有优化只读 8 个 edit-train，配置/预算/UID/目标生成规则在评分前冻结，dev 没有触发参数调整。

原位置、opacity、高阶 SH 固定；仅选中行的 DC 可加有界共享 3D delta，协方差组再开放有界 scale/rotation。DC display delta≤0.15；scale ratio∈[1/1.2,1.2]；raw quaternion 相对 delta norm≤0.08。full SH 仍逐相机原生求值和 clamp_min，不把它假设成共享常数 RGB 的线性算子。零步 DC 投影只是一条独立诊断，未用作训练初始化；不宣称它约束了所有相机的有效 SH 颜色。

固定预算 min(ceil(0.10N),32768)，TRAIN-only 精确全模型 alpha·T / 颜色 Jacobian 流式统计，无 top-k 截断。relative score 将尺度/连通边段平衡证据除以自身可见质量密度，并考虑训练可见率；对照为原始 band contribution 排序和共同可见率/可见质量分层随机。旧 SH0/top64 排名同 PLY SHA，但目标/SH 语义不同，只作历史引用，不混入本轮公平排名。

局部目标为 band L1 + 10×outside 相对 B0 MSE；普通目标为全图 0.8 L1+0.2(1−SSIM)。两者共享相同参数权限及 coverage/协方差正则。coverage 实际走原生 alpha 到 scale/rotation 梯度，不开放 opacity。每满 8 步均另计算全部 8 训练相机的真实目标并保存；336 步为 42 个完整 epoch。同优化墙钟普通对照另外保存，初始化和候选选择成本分开。

宽度来自固定参考的边界法向，斜线/圆弧/等亮度/低对比/纹理 fixture 已实测。参考不合格剖面与结果不合格剖面均记录拒绝；低对比 W=null，不使用 17 条水平线。主指标始终覆盖完整固定 band。共同有效宽度按相机先平均再宏平均，不用缺测剖面制造改善。

## Lego

原模型 SHA256 `fa9bea3fa4f8d349fa873a66d892c53cd1263499caec6421c286350a5bb7cbbc`，N=310475，45 个高阶 SH 系数/核；源训练 commit `472689c0dc70417448fb451bf529ae532d32c095`。原数据有 100 个 TRAIN 相机，实际底座 GS 训练用了 86 个。

| 方法 | 步数 | 优化秒 | heldout band MSE | 全图 PSNR | outside变化 MSE | 全前景孔洞 | AA outline MSE |
|---|---:|---:|---:|---:|---:|---:|---:|
|B0|0|0.000|0.00155191|31.629|0|0.02478844|0.02313107|
|zero_step_dc_projection|0|0.000|0.001550161|31.633|2.089079e-07|0.02478844|0.02313107|
|relative_color|336|5.709|0.001500898|31.687|3.747045e-06|0.02478844|0.02313107|
|relative_color_ordinary|336|6.378|0.001502765|31.692|3.357553e-06|0.02478844|0.02313107|
|relative_cov|336|10.427|0.001455497|31.768|4.146137e-06|0.0222236|0.02301283|
|relative_cov_ordinary|336|11.161|0.001457558|31.778|3.852389e-06|0.02055291|0.02296271|
|relative_color_ordinary_time|303|5.711|0.001502765|31.693|3.135902e-06|0.02478844|0.02313107|
|relative_cov_ordinary_time|315|10.436|0.001457453|31.779|3.724219e-06|0.02064205|0.02296272|
|band2d_cov|336|10.392|0.001381375|31.900|7.622789e-06|0.0158237|0.02279201|
|random_cov|336|10.331|0.001442896|31.853|4.567551e-06|0.02287825|0.0224333|

固定主臂 relative_cov 相对 B0 的 heldout band MSE 改变：6.21% 改善；相对同权限 336 步普通微调：0.14% 改善（负数表示更差）。该单种子探索性结果不支持正式方法优势。开发与训练逐视角表、所有剖面、权限审计和完整 epoch 保存在 results。
候选选择实测 2.919 秒，编辑 31048 个原 UID；relative 的 TRAIN band 贡献覆盖 35.42%，这是可见贡献覆盖，不是错误核召回。

[四个开发视角同相机对比](figures/lego_dev_fourview_contactsheet.jpg)；[四个编辑留出视角](figures/lego_edit-holdout_fourview_contactsheet.jpg)。每行均是原参考/B0/普通颜色/relative颜色/普通协方差/relative协方差/全模型T候选叠加；原生像素边缘裁剪及放大均单独保存。

既有完整33帧开发 arc：[B0](videos/lego_B0_arc0_33.mp4)、[颜色](videos/lego_relative_color_arc0_33.mp4)、[协方差](videos/lego_relative_cov_arc0_33.mp4)。另保存新的完整360°原生可视化 orbit33；它没有参考照片、不参与优化或质量选优。所有视频为 H264/yuv420p/faststart，逐帧完整解码并核对33个不同frame与camera SHA；没有2D墨线替换原生RGB。

## Chair

原模型 SHA256 `13e4ecc9ffe9c5ae2a0656e2e5c56a737cfdc90a62ad04799db3c46b0b442f5d`，N=256690，45 个高阶 SH 系数/核；源训练 commit `472689c0dc70417448fb451bf529ae532d32c095`。原数据有 100 个 TRAIN 相机，实际底座 GS 训练用了 86 个。

| 方法 | 步数 | 优化秒 | heldout band MSE | 全图 PSNR | outside变化 MSE | 全前景孔洞 | AA outline MSE |
|---|---:|---:|---:|---:|---:|---:|---:|
|B0|0|0.000|0.003911611|32.030|0|0.001738916|0.04199619|
|zero_step_dc_projection|0|0.000|0.003902454|32.035|1.301137e-07|0.001738916|0.04199619|
|relative_color|336|5.269|0.003323707|32.414|1.2543e-05|0.001738916|0.04199619|
|relative_color_ordinary|336|6.115|0.003357194|32.407|8.720769e-06|0.001738916|0.04199619|
|relative_cov|336|9.724|0.003228914|32.488|1.380222e-05|0.001725526|0.04207279|
|relative_cov_ordinary|336|10.614|0.003270525|32.473|1.050391e-05|0.001725423|0.04204014|
|relative_color_ordinary_time|288|5.295|0.00337221|32.398|7.955454e-06|0.001738916|0.04199619|
|relative_cov_ordinary_time|311|9.735|0.003276247|32.469|1.017708e-05|0.001725423|0.04203883|
|band2d_cov|336|9.887|0.002299147|33.305|2.994896e-05|0.001771052|0.04083097|
|random_cov|336|9.743|0.00312882|32.585|1.184525e-05|0.001702499|0.04171118|

固定主臂 relative_cov 相对 B0 的 heldout band MSE 改变：17.45% 改善；相对同权限 336 步普通微调：1.27% 改善（负数表示更差）。该单种子探索性结果不支持正式方法优势。开发与训练逐视角表、所有剖面、权限审计和完整 epoch 保存在 results。
候选选择实测 2.956 秒，编辑 25669 个原 UID；relative 的 TRAIN band 贡献覆盖 17.90%，这是可见贡献覆盖，不是错误核召回。

[四个开发视角同相机对比](figures/chair_dev_fourview_contactsheet.jpg)；[四个编辑留出视角](figures/chair_edit-holdout_fourview_contactsheet.jpg)。每行均是原参考/B0/普通颜色/relative颜色/普通协方差/relative协方差/全模型T候选叠加；原生像素边缘裁剪及放大均单独保存。

既有完整33帧开发 arc：[B0](videos/chair_B0_arc0_33.mp4)、[颜色](videos/chair_relative_color_arc0_33.mp4)、[协方差](videos/chair_relative_cov_arc0_33.mp4)。另保存新的完整360°原生可视化 orbit33；它没有参考照片、不参与优化或质量选优。所有视频为 H264/yuv420p/faststart，逐帧完整解码并核对33个不同frame与camera SHA；没有2D墨线替换原生RGB。

## 结论边界

本轮完成两实际底座的原生可见贡献选择、自然 TRAIN RGB 的受限编辑、同权限普通对照、等数量选择对照、只读编辑留出评分及完整媒体。若指标接近原始基线误差底限，不能把微小变化包装成明显自然修复；失败图与视频原样交付。

R1 颜色能力认证、R4 已知UID尺度探针和 Task B 未执行；没有把自然编辑失败称为表示不可达定理，没有加入平面 oracle，没有完整作者 COB-GS 运行，也没有声称新颖性、独立 split、三种子或正式 GO。独立人工视觉 GO 仍待用户审阅。完整360°视频只证明实际渲染完成，不证明时间重投影优势。


## 实测数量、成本和负结果补充

Lego：relative-cov 相对 B0 的留出 band MSE 改善 6.21%，相对同权限 ordinary-cov 改善 0.14%；simple band2d 改善 10.99%，可见率/质量匹配 random 改善 7.02%。因此该预算下没有 relative selector 优势证据。relative TRAIN贡献覆盖 35.42%，band2d 69.99%；局部影响范围更窄也降低了边缘覆盖，不能只看覆盖率或只看 outside保持。

Chair：relative-cov 相对 B0 的留出 band MSE 改善 17.45%，相对同权限 ordinary-cov 改善 1.27%；simple band2d 改善 41.22%，可见率/质量匹配 random 改善 20.01%。因此该预算下没有 relative selector 优势证据。relative TRAIN贡献覆盖 17.90%，band2d 60.04%；局部影响范围更窄也降低了边缘覆盖，不能只看覆盖率或只看 outside保持。

两场景共400个实际同相机评估 RGB（20相机×10方法×2场景），16条完整33帧视频，共528个解码帧；另有4张四视角总览图、16张逐相机全图、16张原生边缘crop和16张放大crop。20张原始TRAIN照片/场景，没有300图campaign。

参考可测率与方法有效率分开：TARGET_FREEZE 的 metadata 保存原参考提案/拒绝/合格数量；results 的 valid_profile_rate 仅以固定合格参考剖面为分母，不能当作所有真实边缘的可测率。纹理Chair的部分相机参考剖面数为0，此时W=null，主要结论使用完整固定band RGB与真实图。

[完整epoch和实际留出对照曲线](figures/actual_complete_epoch_and_holdout_curves.png)。COUNTS/TIMINGS/SCIENTIFIC_DECISION 保存实际数量、墙钟范围与描述性判断；CPU后审计代码为 ANALYZE_FINAL.py，不改变生产源码、参数、目标或选择。


## 相同操作/数量的选核对比

额外四视角图直接使用已有原生渲染：参考/B0/relative-cov/band2d-cov/random-cov；开发相机与参数固定。failure context 沿已冻结 TRAIN-target ROI 中心扩大显示范围，不选择新的优化目标或改变评价区域。

- [Lego选核对比](figures/lego_fourview_selectors.jpg) / [固定ROI上下文放大](figures/lego_fourview_failure_context.jpg)。
- [Chair选核对比](figures/chair_fourview_selectors.jpg) / [固定ROI上下文放大](figures/chair_fourview_failure_context.jpg)。

## 参考剖面可测率与内部/轮廓共同宽度

Lego 留出共同内部剖面 18 条 / 6 视角；共同轮廓剖面 10 条 / 5 视角。内部和轮廓宽度不混为一种物理边缘。
internal 共同宽度 MAE(px)：B0 0.478011、relative-cov 0.462066、ordinary-cov 0.466814、band2d-cov 0.462430。
outline 共同宽度 MAE(px)：B0 0.334868、relative-cov 0.328781、ordinary-cov 0.325158、band2d-cov 0.322478。

Chair 留出共同内部剖面 4 条 / 4 视角；共同轮廓剖面 1 条 / 1 视角。内部和轮廓宽度不混为一种物理边缘。
internal 共同宽度 MAE(px)：B0 0.171404、relative-cov 0.169412、ordinary-cov 0.169371、band2d-cov 0.208439。
outline 共同宽度 MAE(px)：B0 0.702561、relative-cov 0.783819、ordinary-cov 0.757291、band2d-cov 0.710314。

所有20个参考相机的提案/拒绝/合格计数在 PROFILE_VALIDITY_AND_COMMON.json；此 CPU 只读复核在生产封印之后执行，核验固定剖面 ID 一致，没有产生新优化或方法选择。


## 独立实产物审计

独立 CPU agent 完成 21268 项核查、0 失败：15 份封印生产源码与所有依赖/原模型/封印一致，654 个完整 epoch、5232 个逐视角 float32 目标按实际运算顺序完全一致，280 个留出均值字段重算一致；400 个原生 RGB/PNG及16条视频528个独立解码帧全部匹配。起始 float64 算术探针最大差6.36e-9，仅为实际 float32 加法舍入，校准后未改实验参数/损失。审计详见 tests/INDEPENDENT_RESULT_AUDIT.json。两场景原生模型完整可见，实际视觉差异较细微；人工视觉 GO 仍待用户审阅。
