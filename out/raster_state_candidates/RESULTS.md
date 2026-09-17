# Raster-state candidates：四步实跑结果与 NO-GO

**四步均已实现并运行；Lego 六个 arm、三段完整视频和两种实际墨量匹配全部完成。
本轮整体 NO-GO。** 驾驶舱顶框有局部改善，但三个预标结构中最多一个明显受益，
履带与铲斗下缘仍未成为清楚的线画。相同墨量下没有足够的整体可读性收益。
这不是“代码没跑通”，也不是因 mesh recall 不高而否决；本轮没有计算 P/R。

结论范围必须限定：证据来自从 poster 逻辑抽出的 **Gaussian circular-disc
raster-state 代理**，不是官方各向异性 CUDA 光栅器的内部 fragments。官方原版
renderer 已用于所有 RGB 参照；其源码/内核/二进制 hashes 见
[render.json](lego/render.json)。不能把本结果扩大成“所有官方 raster-state 都无效”。

## 可直接检查的结果

- [实际墨面积匹配固定四帧](lego/render/fixed_area_matched.png)
- [实际线长匹配固定四帧](lego/render/fixed_length_matched.png)
- [A/B/C/D/最佳 null 固定四帧](lego/render/arms_area_matched.png)
- [官方 RGB｜A｜D 完整视频，墨面积匹配](lego/render/rgb_A_D_area_matched.mp4)
- [完整视频，线长匹配](lego/render/rgb_A_D_length_matched.mp4)
- [完整视频，原生输出](lego/render/rgb_A_D_native.mp4)
- [三个预标结构逐阶段放大](lego/diagnostics/preregistered_regions.png)
- [完整内部视觉审阅与边界](lego/VISUAL_REVIEW.md)

视频均为 120 帧、24fps、完整 360° 非极点轨迹，解码逐帧核验；无挑帧、无 GT overlay。
固定四帧为 0/30/60/90。`lego/render/contact_{native,length_matched,area_matched}_00..05.png`
覆盖所有帧。已亲自查看 native 与 area-matched 的全部 contact sheet、三种固定四帧、
线长匹配五-arm panel，以及 held-out 相机 [2,22,42,62]。这只是助手内部检查，
不是盲评或虚构的用户研究。视频/NPZ 按 ignore 留在服务器，报告与小图进入 Git。

## 冻结协议与代码

基点 `e0293bd5c847698b9dbe67175ef1cc96a8243df1`；只工作于 `raster-state-candidates`。
TRAIN 为 [1,7,14,21,27,33,41,47,53,59,67,73,79,86,93,99]；所有参数由
[MANIFEST.json](MANIFEST.json) 和 [PREREG.md](PREREG.md) 预先冻结。
manifest SHA256 为 `43bdee970291e302efc453d97b6df0e01b5d737f3d4f38d0be2d7c2e9a092aef`。

新入口 `scripts/run_raster_candidates.py` 依次执行各阶段。
`src/raster_state.py` 共享 fragments、top-k 与统计；`src/id_anchor.py` 做分层 ID 锚定；
`src/candidate_fusion.py` 做共享 ID + 距离 + 切向聚合与 linelet 生成。
`scripts/raster_candidate_outputs.py` 只读冻结 paths、GS depth 和官方 RGB，
`scripts/audit_raster_candidates.py` 做事后 TRAIN 诊断；完整复现步骤在
[REPRODUCE.md](REPRODUCE.md)。`scripts/poster_repro.py` 改为共享 renderer wrapper，
其旧 TEST CLI 未运行。float64 compositing/条件中值定义不是历史结果的位级复现；
历史输出没有改写。

运行时 guard 与各 `access_*.json` 记录实际读取。seed/pull 只读取这 16 个 TRAIN RGB；
DEV 生成发生在路径/参数提交 `5a57a17` 之后，运行时 RGB evidence 读取为零。
TEST 图像和 TEST 相机未用于方法或最终视频。没有 mesh、GT labels、污染旧 cache、
dd3/2DGS normals、GS 重训、逐帧 2D 墨。**原始预训练 GS 的数据划分仍未独立重建审计**，
因此只声明本轮后处理的 TRAIN-only，不把这一限制藏起来。

## Step1：图像空间通道

Lego 16 TRAIN 视角，400px，23.00 s。各通道各视角均达到预设 600 个 NMS 像素上限。
top-k weighted-overlap、SH0 Lab 梯度、Sobel statistics、normal 角差分开处理，
没有 rank-max 融合。保存 original IDs、贡献 weights、mean/conditional median depth、
vanilla covariance normal、alpha、SH0 RGB、entropy/margin/variance/dispersion、coverage。
SH0 RGB 不等于经光照分离的真实 albedo；covariance normal 不等于可靠表面法线。

k4/k8 掩码平均 Jaccard **0.08935**，说明截断敏感，不能声称 top-k 检测稳定。
top-k / RGB / entropy / margin / variance 的平均 silhouette 像素占比分别约
15.88% / 9.16% / 29.97% / 27.22% / 10.96%；alpha 为 100%。这是候选像素统计，
不是 feature-line 正确率。raw NMS 邻接图长度也不是最终可见墨长。

证据：[TRAIN53 channels](lego/step1/channels_053.png)、[逐视角数量/重叠矩阵](lego/step1.json)。
实际观察：RGB 更贴近若干部件边界；top-k、法线和统计通道也在表面内部产生大量细碎响应。

## Step2：ID-weighted 3D anchors

57,600 个 union 观测中 41,801 个通过锚定，6.51 s。中心来自 median-depth 层内
top-k Gaussian centers 的加权平均，带跨层、dominant-ID 邻域和 3px 回投限制；
没有把 depth backprojection 冒充主 anchor。纯回投仅作为 roundtrip 对照。

| 来源 | 输入 | 接受 | 接受回投误差 px* |
|---|---:|---:|---:|
| top-k | 9,600 | 8,218 | 0.454 |
| SH0 RGB | 9,600 | 4,107 | 0.636 |
| entropy | 9,600 | 7,599 | 0.803 |
| margin | 9,600 | 8,283 | 0.837 |
| depth variance | 9,600 | 6,082 | 0.922 |
| normal dispersion | 9,600 | 7,512 | 0.692 |

*各视角接受样本的中位误差，再对视角取中位数，分辨率 400。小误差不是几何正确性证明。
RGB 有 5,084 个观测被深度层质量门槛拒绝。没有事后放宽阈值救回这些点。
见 [anchor 图](lego/step2/anchor_053.png)、[完整原因/逐视角统计](lego/step2.json)。

## Step3：跨视图聚合与 null

同一 view 多通道不能冒充多个 view。cluster 需要共享贡献 IDs、3D proximity、
切向一致、至少 3 个 TRAIN views 和至少 15° 视角分离。总耗时 17.60 s。
N1 只打乱每个 view 的 ID 标签、保留正确 anchor，因此只能诊断 identity grouping；
它的失败不证明语义。N2 平移 field/tangent，并按 view/source 匹配有效观测数量。

| 来源 | 每 arm 匹配观测 | real clusters | N1 | N2 | real/N2 |
|---|---:|---:|---:|---:|---:|
| top-k | 7,119 | 586 | 0 | 184 | 3.18 |
| RGB | 4,107 | 293 | 0 | 34 | 8.62 |
| union | 37,706 | 2,717 | 0 | 1,573 | 1.73 |

预注册的 1.5x 描述性重复率阈值通过；没有统计显著性检验或独立多 seed 复验。
全量真实 B/C/D 分别为 712/293/2,938 clusters，支持视角中位数 3/4/4。
主 N2 使用 matched D 的 1,573 clusters，主 real D 使用全部有效观测；这两个入口
数量差别明确保留，最终还做实际墨量匹配。

[四视角 aggregation](lego/step3/aggregation_train.png) 仍主要是短段。
[额外等 linelet 数量可视化](lego/diagnostics/count_matched_clusters_train053.png)
用冻结 clusters 的确定性随机子集，不改变方法。真实 D 在顶框/悬臂上比移位 null
更集中，但尚不足以支持“非 null 的清楚结构线画”强主张。

## Step4：加入 A 并使用相同下游

全新 TRAIN-only M1a 初始化为 29,916 linelets。所有 arms 都用同一 sharp TRAIN DT、
100-step pull、5px trust region、prune、3D chaining 和笔刷/可见性。新增点会改变
kNN 平滑、NMS 和链化，不能假定 augmented arms 中旧 A 路径原封不动。
5-step/640-linelet smoke 通过，正式 Step4 67.81 s（包含 raw panels/cache），
各 arm 的 pull+prune+chain 为 2.9–4.1 s。

| Arm | raw pool | 新 linelets | 新点通过 prune | 新点进入 chains | 最终 chains | 原生墨长 px/帧 | 原生墨面积 px/帧 |
|---|---:|---:|---:|---:|---:|---:|---:|
| A | 29,916 | 0 | 0 | 0 | 2,024 | 7,382.06 | 7,010.66 |
| B | 30,628 | 712 | 652 | 121 | 2,019 | 7,416.04 | 7,037.39 |
| C | 30,209 | 293 | 280 | 89 | 2,026 | 7,451.22 | 7,045.88 |
| D | 32,854 | 2,938 | 2,512 | 722 | 2,136 | 7,828.17 | 7,421.38 |
| N1 | 29,916 | 0 | 0 | 0 | 2,024 | 7,382.06 | 7,010.66 |
| N2 | 31,489 | 1,573 | 1,144 | 277 | 2,049 | 7,611.14 | 7,231.59 |

A 与 N1 的实际 path 文件 SHA256 相同。D 的新点通过 prune 比例 85.50%，
进入 chains 比例 24.57%；C 相应为 95.56%/30.38%。不能将全部损失归于 prune。
RGB 新中心 51.54% 位于已有 A seed 的一个 Gaussian 间距以内，也提示信息冗余。
见 [raw 六-arm 投影](lego/step4/raw_053.png)、[new-only](lego/step4/new_only_053.png)、
[最终 TRAIN 六-arm](lego/diagnostics/final_arms_train053.png)、[source audit](lego/diagnostics/audit.json)。

## 墨量控制、失败定位与判定

原生 D 墨长增加 6.04%，墨面积增加 5.86%；这不能算视觉改进。所有匹配均为整段
DEV 轨迹上一个固定全局路径子集，绝不逐帧删墨。匹配线长和匹配墨面积是两个独立控制。

| 版本 | A 墨长 | D 墨长 | A 墨面积 | D 墨面积 |
|---|---:|---:|---:|---:|
| 原生 | 7,382.06 | 7,828.17 | 7,010.66 | 7,421.38 |
| 线长匹配 | 7,382.06 | 7,381.81 | 7,010.66 | 7,094.44 |
| 面积匹配 | 7,382.06 | 7,280.78 | 7,010.66 | 7,010.54 |

六 arms 的目标量匹配误差均 <0.05%。D 原生短碎片(<12px)比例 90.17%，
A 为 89.85%；这里统计可见 run，不能替代观看。墨量匹配后主结构缺失仍在，
新增碎段散落在底板、臂架和铲斗周边。三种视频及指标生成/核验用时 414.37 s。

[预标区域逐阶段 trace](lego/diagnostics/region_trace.json) 提供更具体的瓶颈：

- R1 顶框：TRAIN53 RGB 71 个观测→46 个 anchors；ROI 内 D 新 raw 中心 172，
  新最终 chain 顶点 57，出现局部可见收益。
- R2 履带：RGB 14→2，12 个因跨深度层被拒；variance 有 411 个观测但多不构成
  有价值边界。ROI 内新 raw 中心 74→prune 后 68→chain 顶点 11，画面仍缺关键组织。
- R3 铲斗下缘：RGB 29→14；新 raw 中心 39→prune 后 34→chain 顶点 11，仍断成短段。

这些 ROI 中心计数跨阶段并非严格同一观测 cohort，不能当 semantic recall。
它们支持的诊断是：部分价值证据先在层锚定中丢失；留下的重复点也不足以组成连续结构；
固定下游又损失很多新点。仅加候选数量没有解决“结构组织”问题。

| Gate | 判定 |
|---|---|
| G1 raw 候选恢复 >=2/3 结构 | 失败；最多顶框一处明显改善 |
| G2 非 null | 重复率效应通过；强视觉非-null 主张未建立 |
| G3 最终存活 >=2/3 结构 | 失败；履带与铲斗下缘仍失败 |
| G4 实际墨量匹配后画面改善 | 失败；局部顶框收益不足以改变整体可读性/碎线问题 |
| G5 持久载体/时间 | 固定 3D 载体成立；可见性显隐仍在，无“无闪烁”或普适稳定优势 claim |

因此整体 NO-GO，不改阈值、不扩完整第二场景。Chair 只完成四 TRAIN 视角 cheap transfer：
B/C/D 初始 linelets 为 66/91/338，matched real/N2 为 31/1、82/0、276/26。
已查看 chair 通道与完整 aggregation 图，仍是短碎段。详见
[chair transfer 报告](chair_transfer/RESULTS.md)，不能把它称作完整泛化验证。

## 各来源到底证明了什么

**top-k：**能产生跨视图重复且可下游存活的候选；但 k 敏感性很强，最终新结构收益
没有通过视觉门槛。不能作为本轮主方向成功结果。

**ID：**可作为持久归属/聚合约束；N1 显示打乱标签会破坏这个机制。
ID 本身不提供“这是形状线”的语义，更不能由 N1=0 证明视觉创新。

**SH0 RGB：**本轮相对最有效的单一证据信号：matched null 区分最大、chain 生存率较高，
但候选仅 293 条且与 A 重叠很多；其最终 C 与 A 非常接近，不足以解决当前稀疏性。

**贡献统计：**联合来源明显增加候选与存活点，带来顶框局部改善，也增加碎线。
本轮没有将 entropy/margin/variance/dispersion 各自独立消融，重叠 source tags
只能用于追溯，不能声称某一种统计量的独立因果贡献。它们未使整套方法过关。

**研究决定：不将当前配置推进为主方向。** 保留 renderer/ID provenance/分层锚定工具与
这组负结果。已得到的是“怎样产生更多持久短段”，尚未得到“怎样增加清楚、连贯的
NPR 结构”。官方 anisotropic fragments、别的锚定约束或下游成链机制属于未验证问题，
本轮不靠这些尚未运行的可能性改写 NO-GO。

## 实现与验证记录

33 个单元测试通过，见 [TEST_RESULTS.txt](TEST_RESULTS.txt)：原始 ID 三层映射、
按贡献选 top-k/并列分数、empty-empty、exact-n、k 敏感性、完整 K、ID/深度层锚定、
多视图分组/null、保留 A 初始化、固定全局墨量子集、非极点相机轨迹及既有协议测试。
Lego/chair 的小分辨率 GPU repeat IDs 完全相同、最大 weight 差为 0；A/N1 正式
下游也完全一致。没有将这种单机重复扩大成跨硬件 CUDA 位级确定性保证。

已提交并逐次推送/核验的前序里程碑：
`a37aa0c` 预注册；`77b4d60` 共享 raster-state 与 Step1；`c46faee` Step2；
`993d94f` Step3；`5a57a17` Step4 与 DEV 前冻结；`e67c474` 完整视频和 primary NO-GO。
本报告、chair transfer、区域 trace、汇总脚本与最终测试由后续收尾 commit 一并保存。
最终远端 SHA 以该 commit 的 `git ls-remote` 核验结果为准。

所有数值由 [RESULTS.json](RESULTS.json) 汇总原始阶段 JSON，脚本为
`scripts/summarize_raster_candidates.py`；图像判断单独标明为内部视觉观察。
本次各主阶段计时相加约 588.59 s（不含编程、检查、提交与额外诊断），没有长训练。
