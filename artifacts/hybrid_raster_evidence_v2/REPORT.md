# 同源 raster-state / RGB / 自动互补：阶段 1 实测报告

**当前状态：生产评估进行中，最终核验与视觉结论尚待完成。** 本报告由实现模型编写，不是独立人类视觉 GO。方向 2（自动 3D/2D 路由）与方向 3（时序身份传播）均未实施。

## 已固定的实验范围

目标是 frozen vanilla 3DGS 的自动高密度 NPR，优先更多有用细节。这里比较同一次原生渲染的三种**视角相关 2D**读出；没有旧橙线、没有人工线标、mesh、重训练或曲线容量扩充。旧 I-arm 的 fixed-3D NO_GO 不变，原始固定三维目标仍未实现。

先推送协议 `9ba89eb404f2e95e2f2c778e518978f5aec2c781`，再实现；实现提交 `61d324a`。Lego、Chair 的全部 16 个 F 完成后，F-only 归一化锁于提交 `de7f3e0` 推送，之后才打开 C 渲染评估。参数 hash：`6c4ef4afa648f54794d7094a7b21368a89e14cdbc792766441aa3d3639d487c9`。

F=`[1,14,27,41,53,67,79,93]`；C=`[7,21,33,47,59,73,86,99]`。C 对本次参数拟合留出，但属于 GS TRAIN 且历史已查看，**不是新盲测**。所有相机来自既有 INPUTS，800×800；arc0 完整保留 33 个精确 pose，不重新生成相机轨道。方法不解码原始 C/DEV/TEST 图像，C/arc 输出由真实相机的 frozen GS 重新栅格化。TEST 保持关闭。

## 三臂及控制

| 输出 | 定义 | 如何解释 |
|---|---|---|
| A | 同源 SH0 RGB 双尺度 Canny + 同源中位深度导数/NMS/hysteresis + alpha silhouette | 当前 dense Canny 风格移植；不是历史 full-SH RGB 的逐像素相同基线 |
| B | 保留全部作者公式字段；OUR dense 对 D/alpha/normal/color/ID-support/visibility 六个 raw 通道作固定 F 归一化、连续读出并逐点 max | 我们附加的高密度读出，不是作者最终合成器 |
| C | `A+B*(1-A)`，保留每臂及每通道 provenance | 自动互补；没有 pooled top-k 墨量上限或连通结构剪除 |
| 作者原式 | 原值 `S_L`，另有固定 F-positive-P99 增益图 | 独立公式重建的原输出，没有借 OUR dense 改写 |
| 等墨量 | A/B/C 各自整图乘浓度，使总连续墨量等于该帧三者最小值 | 保留非零支持；不是等黑像素数，也不是按预算删线 |

三臂统一 native RGB、alpha、depth、相机、mask、像素尺寸和 1 像素采样笔刷。主输出全是纯 2D；不把历史固定曲线投影当成新证据增益。B 的可靠度只调整浓度，保留 `.35` 下限；这一选择让弱结构可见，也可能把大量非线状支持变化画出来。所有 raw、normalized、typed、作者原值、OUR 读出均保留，便于审查。

## 工程有效性与来源限定

真实 GPU top4 原 ID、`alpha*T`、贡献 depth/normal、RGB/alpha/期望深度/中位深度/normal、完整二阶矩和 normal length 来自**同一个 `renderCUDA` 遍历**。原始权重不归一化；公式输入的 top4 归一化权重和 mass coverage 另存。禁止拼接另一渲染器的几何和代理 ID。

两版最小源码隔离编译，未改 sibling renderer 或 Python 全局安装。Lego/Chair F1/F41 重新做真正 patched/unpatched 同输入校准，RGB、alpha、期望深度、中位深度、normal 的逐元素最大误差均为 **0**。合成 fixture 覆盖原 ID、`.704/.12` 的真实贡献混合、空射线、>4 贡献仍保留完整矩，以及 399.5 主点映射。生产入口先拒绝非有限/非法字段，不靠源公式中的 `nan_to_num` 修复 export。

限定不能省略：

- frozen vanilla checkpoint 没有 RaDe 训练时的 `filter_3D`，也没有重训练、去漂浮或人为补字段。
- 45 个高阶 SH 系数属性明确未使用，只有 SH0；所有核心臂使用完全相同的原生颜色缓冲。
- top4 只覆盖部分可见 alpha，不能把它当全射线贡献；完整矩来自所有接受的贡献。逐帧 coverage 单独报告。
- 法线是 RaDe 原生相机坐标 splat/ray-plane normal，未验证为真实表面法线。专用 loader 不计算协方差轴代理法线；上游病态 inverse-covariance fallback 保持原样并统计候选输入，不把它美化为真值。
- 颜色状态采用去白背景后的 visible SH0 mean，不是材质 albedo。论文将 C 称为 composite color，因此 `delta_C/E_C/E_T` 仅是本独立 state 约定上的公式结果；`S_L` 不依赖该颜色分支。没有声称官方 compositor 的精确复现。
- Drums/Ficus 若按同一 recipe 扩展，继承既有 posterior/input qualification 限制；不会针对它们重新拟合尺度。

## 像素诊断与视觉审阅

此处待完整结果写入。墨量、支持像素、分层覆盖、A/B 重叠与 source argmax 都是像素诊断，没有真实线条标注，不能解释成 precision/recall 或有用细节百分比。source argmax 使用固定通道顺序处理并列，不代表唯一因果来源。

已完成 F1/F41 工程审阅：共同 RGB 与对象轮廓对齐，无黑屏或错位；OUR B 出现广泛灰密纹理，C 保留 A 轮廓同时叠加该密纹。等连续墨量后也尚未建立比 A 更好线条结构的证据。该现象会保留，不借 C 改阈值。详见 [工程切片审阅](PILOT_REVIEW.json)。

## 产物与复现

完整目录：`out/hybrid_raster_evidence_v2/frames/{scene}/{F_001,C_007,arc0_000,...}/`。每帧包含 `native.npz`、`typed.npz`、`responses.npz`、`provenance.npz`、camera/diagnostics、全分辨率响应/线条/overlay/等墨量 panels、各臂白底与 overlay、`SEAL.json`。

`media/{scene}/` 提供整段原密度、overlay、等墨量比较 MP4，以及 F/C/完整 arc0 的 full-frame contact sheets 和首/中/末代表帧。视频必须先写临时文件，完整解码 33/33、33 distinct、尺寸正确后才发布；本报告不据此推断优越时序稳定性。

精确命令见 [REPRODUCE.md](REPRODUCE.md)，冻结规则见 [PROTOCOL.md](PROTOCOL.md)。[参数锁](PARAMETER_LOCK.json)、[原生校准](CALIBRATION.json)、[工程复核](ENGINEERING_REVIEW.json) 分别记录设置、数值同源性与代码审阅；均不能代替视觉效用判断。`STATUS.json` 记录实际进度与错误；最终完整核验写入 `VERIFICATION.json` 和 `FINAL.json`。

## 第三方归属

[Hao–Mukai 作者海报](https://mukai-lab.org/content/SA2026PosterHao.pdf)的 Eq.1–5、常数和状态特征线思路属于 Weiren Hao / Tomohiko Mukai；[RaDe-GS](https://github.com/HKUST-SAIL/RaDe-GS) 原生 rasterizer 属于 Zhang 等。此处是独立重建与原生导出，OUR dense 和 A+B fusion 是附加实验。旧 proxy rank-max 不是作者方法；hybrid 本身不主张新颖性，3Doodle 已组合视角独立与相关成分。任何本次负观察均只限定于这个冻结输入与读出，不是否定作者方法或原生状态路线。
