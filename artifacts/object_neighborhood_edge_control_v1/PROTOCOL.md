# object-neighborhood-edge-control-v1 的执行协议

本次实验继承原始执行入口全部 30 行、研究大纲全部 544 行与启动用户合同。原始文档不可修改；具体 SHA256 与分节绑定见 `source_bindings/task_inheritance.json`。不可变基线是 `8deeb1d6f12ef813c4ff20cbd4992410311d92ba`。实际阶段状态由 `STATUS.json`、结果封印与最终 `FINAL.json` 决定，本文件不代表阶段已经通过。

这是 seed=1729 的工程 pilot，不是正式三种子结果。先做高对比共面面板的单场景闭环，再处理低对比与远背景负例。每条件 512×512、24 train / 6 val / 12 TEST；后 6 个 TEST 位于连续 [22°,32°] 保留区段。另生成 36 个不同相机的保留路径。正式 60/20/20、120 帧、10 条件、三种子均不由本 pilot 代替。

原生训练采用固定的官方 3DGS 历史版本 `472689c0dc70417448fb451bf529ae532d32c095` 与原生 rasterizer `59f5f77e3ddbac3ed9db93ec2cfe99ed6c5d121d`，直接调用未修改的 training()。7000 迭代、SH degree=0、4096 随机体积点初始化，4000 后停止增密；这是平面漫反射场景的有界 pilot，不声称官方 30k 质量。全部参数保存在 train 场景 manifest。C++ 标准头兼容通过编译参数强制包含 cstdint/cfloat，不修改 upstream 源码、不覆盖已安装扩展。独立 COB renderer 只服务 B4 官方基线，不引入到控制方法。

确定性射线/平面相交生成器采用线性 sRGB/D65、固定不随视角变化的表面颜色、黑背景，2×2 超采样箱形 PSF。训练输入是量化线性 RGB PNG，展示图单独应用 sRGB OETF。训练和颜色修复使用相同 8-bit 训练图；评价用保存的浮点目标，量化差异纳入误差上限。二值 ID、连续 coverage、深度、法线、表面点、mesh 与任务 B 的三维颜色场目标另存；后三类几何只能由评价器读取。任务 A/B 文件分开，任务 B 目标生成不表示 P4 已运行。

主模型是随机体积初始化后联合 RGB 训练的 GS，不是按物体构造的 oracle 模型。标签来自 24 个训练 instance mask 对同一原生 alpha·T 合成的贡献支持，归一化概率最大值 ≥0.85 才分配标签，否则保留 unknown。mask 是非学习的合成训练标注，未跑 SAM 或 Gaussian Grouping 特征学习。不可把它称为 learned segmentation 或真实 Gaussian 实例真值。UID 从后训练 checkpoint 起冻结，标签、概率、初始 anchor 一起保存；数组重排不能改 UID。拆分由 parent_uid 继承，官方 B4 的最终歧义裁剪也显式记入日志。

C0 使用明确中心半径；C1 用全椭球 AABB 粗筛、共同可行点与凸距离上下界证书。不能用固定 k 最近邻把远物体强行接上。C0/C1 只报告 Gaussian neighborhood proxy，真实表面 contact/near/separated 只出现在 oracle 评价。可见贡献通过官方 feature pass 及颜色 Jacobian 取出，保留同一 footprint、排序、alpha 截断、透射提前终止；不二次乘 opacity，不用 top-k 或 N×H×W 稠密张量。depth 输出是 Gaussian 中心的 alpha 加权代理，不等于真实表面深度。

宽度从线性 RGB 剖面端点颜色方向上测 W10–90；mask 只定位，不用 argmax 的硬边作宽度证据。低对比返回 width=null；复杂剖面与 hidden 返回拒绝原因。对比采用声明条件的 ΔE76（D65、2°观察者）及 ΔL。profile 的阈值交点不参与反向传播，局部损失使用固定参考像素。观测、错误假设和显式目标分别存储，不从 RGB 推断唯一物理原因。

比较顺序为 B0、B1、B3、B6、B4 mask-only、B4 official，然后 C0/C1 控制。B1 是普通 L1+SSIM 局部颜色微调；B3 在同一 C1 集合统一缩小尺度 0.85 后颜色恢复；B6 只用二维训练 band 的贡献排序，数量匹配 C1。颜色编辑冻结位置/尺度/旋转/opacity、标签与非指定行。低对比/没有可信空间集合的自动方法 no-op。B3 允许作为失败基线产生覆盖问题，但必须计入评价，不能隐去。

B4 是固定提交 `559a9fc11888b06d59969eea9534b1a6f845a585` 的官方 foreground/rest mask 梯度符号计数、歧义选择、N=2 随机拆分和外观恢复。mask-only 与 finetune_mask 必须分别记录。UID/标签 sidecar 是身份 instrumentation，不更改其选择算法。官方全局恢复更新与最后 ambiguity prune 原样保留，作用域、数量与孔洞变化单独报告；执行成功不自动意味着等数量/时间比较合格，也不意味着整个 10 条件 P3 完成。

验证阶段结束后才冻结评价器、所有模型/选择/目标、验证校准的工程阈值和结论判定规则，再打开 TEST。TEST 不返回控制器，冻结后不得根据 TEST 更改模型或目标。正式成功仍需要三个种子、多条件、相应完整强基线与独立人工视觉 GO。两次候选控制消融若未优于等预算普通局部微调，停止增加复杂模块并交付失败证据。

运行只用 GPU0，CPU 线程上限 2。每训练/构建/原生程序前检查 GPU jobs、根盘 ≥4GiB、公用 Git 盘 ≥1.5GiB、新 stage ≤16GiB。外来 job 导致等待，不终止。旧模型/旧 TEST/旧代码/旧 seals/out 完全只读。大数据、扩展、缓存与 raw log 都在新 stage 的 gitignored out；仅新代码、source bindings、结果表、小图、视频与报告提交。
