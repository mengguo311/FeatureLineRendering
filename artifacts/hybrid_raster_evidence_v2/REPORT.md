# 同源 raster-state / RGB / 自动互补：阶段 1 实测报告

**阶段 1 已完成真实实验：196/196 帧、12段完整视频、52/52 测试及全量工程核验通过。新增 raster 响应明显，但本冻结 recipe 尚未建立整体“更多有用线条”的收益。** 阶段状态为 `ENGINEERING_VALID_RESULTS_COMPLETE_VISUAL_REVIEW_PENDING`。本报告由实现模型编写，不是独立人类视觉 GO。方向 2（自动 3D/2D 路由）与方向 3（时序身份传播）均未实施。

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
- 45 个高阶 SH 系数属性明确未使用，只有 SH0；输入颜色为 `clip(.5+C0*f_dc,0,1)`，所有核心臂使用完全相同的原生颜色缓冲。
- top4 只覆盖部分可见 alpha，不能把它当全射线贡献；完整矩来自所有接受的贡献。逐帧 coverage 单独报告。
- 法线是 RaDe 原生相机坐标 splat/ray-plane normal，未验证为真实表面法线。专用 loader 不计算协方差轴代理法线；上游病态 inverse-covariance fallback 保持原样并统计候选输入，不把它美化为真值。
- 颜色状态采用去白背景后的 visible SH0 mean，不是材质 albedo。论文将 C 称为 composite color，因此 `delta_C/E_C/E_T` 仅是本独立 state 约定上的公式结果；`S_L` 不依赖该颜色分支。没有声称官方 compositor 的精确复现。
- Drums/Ficus 使用同一 recipe 扩展，继承既有 posterior/input qualification 不通过；没有针对它们重新拟合尺度。原始资格证据是只读 `tier1/out/multiscene_foundation_corrected/RESULTS.md` 第15–16、24–25行：`INSUFFICIENT_POSTERIOR_QUALITY`、后续 `NOT_ELIGIBLE`。它已包含历史 native800→area400 事后采样校正，本次不重新认证其几何后验，也不将输入限制当作方法科学失败；路径/hash 见 [归属与输入限定](ATTRIBUTION.json)。

## 像素诊断与视觉审阅

墨量、支持像素、分层覆盖、A/B 重叠与 source argmax 都是像素诊断，没有真实线条标注，不能解释成 precision/recall 或有用细节百分比。source argmax 使用固定通道顺序处理并列，不代表唯一因果来源。support 指浮点墨浓度大于零，分母为完整 800×800 像素；不等于量化后的可见黑像素。诊断中的 background 是 `alpha>=.5` 核心及其4像素边带之外，可能包含低透明度对象碎片；它不同于共同 `.08` mask 外的严格无墨区域。

全部 196 帧的逐帧均值如下（[完整汇总与精确文件清单](SUMMARY.json)）。主场景独立 JSON 聚合与汇总脚本一致，见 [主场景数值复核](PRIMARY_NUMERICAL_REVIEW.json)。

| 场景/分组 | 平均连续墨量 A / B / C | 全帧 support % A / B / C |
|---|---:|---:|
| Lego F | 49239.6 / 96139.4 / 116555.5 | 7.69 / 28.95 / 28.95 |
| Lego C | 63981.0 / 111591.8 / 138276.9 | 10.00 / 33.36 / 33.37 |
| Lego arc0 | 69907.0 / 111134.3 / 141043.3 | 10.92 / 34.17 / 34.18 |
| Chair F | 42951.8 / 63812.8 / 82647.9 | 6.71 / 20.24 / 20.25 |
| Chair C | 31731.5 / 50895.7 / 64702.1 | 4.96 / 18.16 / 18.17 |
| Chair arc0 | 18289.2 / 33026.6 / 40892.8 | 2.86 / 13.84 / 13.85 |
| Drums F | 37247.9 / 61972.4 / 78532.2 | 5.82 / 23.16 / 23.22 |
| Drums C | 35683.6 / 63152.8 / 79062.9 | 5.58 / 24.60 / 24.65 |
| Drums arc0 | 36906.2 / 65037.8 / 81722.9 | 5.77 / 25.59 / 25.64 |
| Ficus F | 29197.0 / 37475.7 / 52074.3 | 4.56 / 12.58 / 12.62 |
| Ficus C | 29887.4 / 39308.0 / 54084.2 | 4.67 / 13.03 / 13.07 |
| Ficus arc0 | 28398.1 / 38274.5 / 52245.0 | 4.44 / 12.77 / 12.80 |

在 `alpha>.05` 像素上加权，top4 alpha 覆盖均值为 Lego F/C/arc `.6969/.6979/.6954`，Chair `.6458/.6780/.7003`。也就是说 top4 通常仍遗漏约三成可见贡献质量。对应 normal coherence 较高也不能证明法线准确；完整诊断保留逐帧分布而不以可靠度指标代替视觉判断。

扩展场景 C 组 top4 覆盖均值为 Drums `.6161`、Ficus `.5767`，遗漏更明显。四场景 C 组每帧平均 B-only support 分别约 149555、84573、122092、53793 像素；A-only 分别约 39、79、323、265 像素。B 的支持已覆盖几乎全部 A，因此 C 相对 B 的主要变化是重叠位置浓度加深；这些量不能区分有用线与面内杂纹。

在各 C 组 B-only 像素的固定顺序 argmax 标签中，`delta_G`（原 ID 支持变化）占 Lego/Chair/Drums/Ficus 的 **86.04% / 82.26% / 82.38% / 70.85%**。前三场景的第二大标签是 visibility，Ficus 则是 alpha 变化。这支持“本 dense max 读出广泛响应了面内支持变化”的解释，但并列标签不是唯一因果归属，也不能把这些比例叫作噪声率。逐通道原值、浓度、bits 和 argmax 均在产物中可核查。

已完成 F1/F41 工程审阅：共同 RGB 与对象轮廓对齐，无黑屏或错位；OUR B 出现广泛灰密纹理，C 保留 A 轮廓同时叠加该密纹。等连续墨量后也尚未建立比 A 更好线条结构的证据。该现象会保留，不借 C 改阈值。详见 [工程切片审阅](PILOT_REVIEW.json)。

主评估的实施模型审阅已查看 Lego/Chair 的 C 代表图、全部八 C 的完整画幅 contact sheet、arc 首/中/末，以及 800×800 单独 B 墨图。Lego 的部分凸点圆环与底板细节在 C 中显得更连续，但履带/支架也拥挤发黑；Chair 平滑椅背出现浅裂纹式响应，边框粗密，正面装饰区高度拥挤。等墨量后 B/C 仍主要表现为灰密纹，并未建立整体有用线条优于 A 的证据。具体已查看文件/hash 见 [VISUAL_REVIEW.json](VISUAL_REVIEW.json)，不得称为独立人类 GO。

Drums 的 F/C 代表帧中，镲片与鼓面出现大量面内杂纹，支架与踏板变黑；等墨量后仍偏向灰色纹理图。Ficus 的叶面、枝干与盆体也呈密纹，C 加深叶缘但让重叠叶片更拥挤；既定 C47 盆底视角包含明显斑驳响应，照常保留。扩展场景也已查看完整八 C contact sheets 和 arc 首/中/末。两场景均没有单独调参，它们的后验资格限制进一步收窄解释范围。

## 测试与审计

最终新测试和相关回归 **52/52 通过**：48项当前模块/旧dense与video/公式测试，2项旧 native 包装器测试（isolated patched），2项旧 foundation 包装器测试（isolated unpatched）。原生 export、typed evidence、seal 与阶段门禁均有实施前实际 RED→GREEN 日志；背景、ID/alpha*T、空射线、同源校准、融合/重叠、弱支持保留、维度、损坏重启及视频截断均有控制。精确命令、退出码与日志见 [FINAL_TESTS.json](FINAL_TESTS.json) 和 `logs/`。

[最终独立检查器核验](VERIFICATION.json)为 PASS：四场景各49帧，全部 native 字段重新解压检查有限性；校验 original IDs/权重、精确相机、源和参数锁、每文件 SHA、融合/provenance、分层统计/四类 raw 分布及墨量控制，重解码所有视频。缺失0、错误0。patched/unpatched 数值等价的直接校准范围仍限于 Lego/Chair 的四个 F1/F41 工程帧与合成 fixture，没有把此事写成196帧逐帧双渲染校准。

辅助检查复核曾发现空 trace 假 PASS、部分 scalar 诊断未重算两处漏洞；先新增篡改测试得到真实 RED，再修复 checker，独立重放后全部拒绝。未改冻结 producer，也未改已有输出。另有早期测试启动时的 import/PYTHONPATH/构建未就绪错误，原失败日志保留，不归类为科学 NO_GO。

[访问审计](ACCESS.json)覆盖主场景 C/arc 和扩展完整生产进程的两份 strace，合计解析 413828 次 open 调用，0 未解析、0 未决、0 违规；未见原始 C/DEV/TEST 图像读取或工作区外普通文件写入。该证据范围不覆盖更早 pilot/F 的全部系统调用，也不是整会话审计。每次 native render 前均检查 nvidia-smi/PID ownership，无外来计算 PID 的观察记录；该检查不是跨任务原子占用锁。

生产 runner 的 GPU context 阶段墙钟合计约 42.9 分钟（含 CPU 读出和落盘），低于冻结4小时上限；不把它当纯 CUDA 计算时长或实时 FPS。计时与 ownership 日志保留在 `out/hybrid_raster_evidence_v2/{RUNTIME.json,native_logs/}`。

## 产物与复现

完整目录：`out/hybrid_raster_evidence_v2/frames/{scene}/{F_001,C_007,arc0_000,...}/`。每帧包含 `native.npz`、`typed.npz`、`responses.npz`、`provenance.npz`、camera/diagnostics、全分辨率响应/线条/overlay/等墨量 panels、各臂白底与 overlay、`SEAL.json`。

`media/{scene}/` 提供整段原密度、overlay、等墨量比较 MP4，以及 F/C/完整 arc0 的 full-frame contact sheets 和首/中/末代表帧。视频必须先写临时文件，完整解码 33/33、33 distinct、尺寸正确后才发布；本报告不据此推断优越时序稳定性。

全部12个 MP4 均为未剪切33帧、12fps（2.75秒），比较版4000×832、overlay/等墨量版2400×832；每个原始相机画幅仍为800×800，附32像素标签行。完整轨道是 INPUTS 定义的短邻近视角段，不是360度重建展示。

| 场景 | 原密度白底与原生 RGB/作者式 | 模型叠加 | 等墨量控制 |
|---|---|---|---|
| Lego | [完整视频](videos/lego_arc0_comparison.mp4) | [overlay](videos/lego_arc0_overlay.mp4) | [matched](videos/lego_arc0_matched.mp4) |
| Chair | [完整视频](videos/chair_arc0_comparison.mp4) | [overlay](videos/chair_arc0_overlay.mp4) | [matched](videos/chair_arc0_matched.mp4) |
| Drums | [完整视频](videos/drums_arc0_comparison.mp4) | [overlay](videos/drums_arc0_overlay.mp4) | [matched](videos/drums_arc0_matched.mp4) |
| Ficus | [完整视频](videos/ficus_arc0_comparison.mp4) | [overlay](videos/ficus_arc0_overlay.mp4) | [matched](videos/ficus_arc0_matched.mp4) |

原始字段、所有 PNG、完整 contact sheets 与隔离 native build 保留在本地 `out/hybrid_raster_evidence_v2`（约7.9GB）；没有把大体积 raw 上传 Git。代码、报告、锁、精确路径/哈希清单、测试日志、20张完整画幅代表 JPEG 和全部视频入库。JPEG 只用于方便审阅；原始 PNG 和浮点字段是封存数据。

每场景15张完整 contact sheets 的精确目录：[Lego](../../out/hybrid_raster_evidence_v2/media/lego)、[Chair](../../out/hybrid_raster_evidence_v2/media/chair)、[Drums](../../out/hybrid_raster_evidence_v2/media/drums)、[Ficus](../../out/hybrid_raster_evidence_v2/media/ficus)。分别包含 F/C/arc0 的 RGB、A、B、C、author_gain；所有 frame 的 matched panel 与首/中/末单独图也保留。

精确命令见 [REPRODUCE.md](REPRODUCE.md)，冻结规则见 [PROTOCOL.md](PROTOCOL.md)。[参数锁](PARAMETER_LOCK.json)、[原生校准](CALIBRATION.json)、[工程复核](ENGINEERING_REVIEW.json) 分别记录设置、数值同源性与代码审阅；均不能代替视觉效用判断。[STATUS.json](STATUS.json) 记录终态；[FINAL.json](FINAL.json) 记录提交关系、精确路径和剩余门槛。

## 尚未验证与停止范围

有用线条数量/正确性没有人工标注或独立视觉评审；因此本次可交付的是工程有效、可复核的受限负观察，不是所有 raster 内部证据的科学 NO_GO。没有测试官方 RaDe 训练/filter_3D、full-SH 或作者官方 compositor，没有证明 splat normal 是表面法线，也没有验证优越时序稳定性。全程不打开 TEST、不依据 C 救援参数。

下一道门槛是用户查看原密度与等墨量视频、全幅 contact sheets 和原始通道，判断新增内容是否足够有用。此处停止，不自主推进方向2/3，不扩大旧曲线容量。旧 fixed-3D NO_GO 与原始固定三维目标未实现的事实保持不变。

## 第三方归属

[Hao–Mukai 作者海报](https://mukai-lab.org/content/SA2026PosterHao.pdf)的 Eq.1–5、常数和状态特征线思路属于 Weiren Hao / Tomohiko Mukai；[RaDe-GS](https://github.com/HKUST-SAIL/RaDe-GS) 原生 rasterizer 属于 Zhang 等。此处是独立重建与原生导出，OUR dense 和 A+B fusion 是附加实验。旧 proxy rank-max 不是作者方法；hybrid 本身不主张新颖性，3Doodle 已组合视角独立与相关成分。任何本次负观察均只限定于这个冻结输入与读出，不是否定作者方法或原生状态路线。
