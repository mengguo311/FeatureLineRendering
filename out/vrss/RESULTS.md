# VRSS chair DEV cheap kill-test：NO-GO

## 实际执行到哪里

完成 PHASE 0 输入/相机/官方 renderer 核验，完成 PHASE 1 最小实现和 10 项测试，**实际运行完 PHASE 2 的 A/B/C/D 及两部完整连续视频**。不进入 PHASE 3；没有跑 lego/cadpartA、20% 档、TEST、Truck 或盲评，也没有虚构参与者。

**实现闭环成立，方法视觉收益未成立。** 本轮只能判当前冻结实现和候选/可见性组合未通过 cheap gate，不能宣称从理论上否定所有 VRSS 目标或所有持久三维笔画。

## 冻结输入与代码

- 分支 vrss-experiment；基线 visual-stroke-render 保持 acd4ab9530fb4e5f654f2198c239bf6ddb62095e。
- 协议与全部参数见 [PREREG.md](PREREG.md)、[manifest.json](manifest.json)。16 个 TRAIN 索引：[1, 7, 14, 21, 27, 33, 41, 47, 53, 59, 67, 73, 79, 86, 93, 99]。
- 清洁重生成 17,065 个 seed，prune 后 15,561 linelets，冻结 1,258 条路径 / 6,490 顶点。候选 SHA256 `b7e77d5786cdd9789a7e310834e599569c0119b3c8c2c1289a90d6377096836e`。旧 cache 未使用，候选生成后未移动顶点、补线、重连或换曲线表示。
- 核心实现：[stroke_relations.py](../../src/stroke_relations.py)、[stroke_select.py](../../src/stroke_select.py)、[run_vrss.py](../../scripts/run_vrss.py)。复现命令及限制见 [IMPLEMENTATION.md](IMPLEMENTATION.md)。
- 完整 K 回归涵盖 fx≠fy、偏心主点、skew、各相机不同 K 与梯度；G-buffer fx=100, fy=50 的单点峰值位于正确的 v=20（旧 fx 公式会给 25）。G-buffer 圆盘半径仍沿用旧 fx 近似，不声称已变成官方深度。
- M1a 明确要求 train_indices，缺省、重复、非法及 VAL/TEST indices 拒绝；旧 score 不会自动获得 TRAIN-only 标签。原 GS 的训练图像范围未独立确认，隔离仅声明 line module。
- 原先 SC-GS kernel 的初步 smoke 不足以确认官方内核；最终独立编译 pinned 官方 rasterizer，实际视频使用未修改的官方 Python renderer + 官方 CUDA RGB。见 [OFFICIAL_RENDERER_AUDIT.md](OFFICIAL_RENDERER_AUDIT.md)。TRAIN 单帧 PSNR 诊断 28.30756 dB；不是新视角质量结论。
- 早期 feature commit 含一个尚未处理的异步 fixture 失败，已在 IMPLEMENTATION.md 记录，后续修复并在真实候选运行前确认 10 项全通过。未重写 Git 历史。

## 真实数值

A=independent/average，B=no-relations，C=no-tail，D=full。共同 q 始终用完整 U/R/D 公式重算，故可横向读取；不是每个版本自己的最优化分数。

| 版本 | 路径数 | TRAIN 长度/全池 | q 均值 | q 最差25% | DEV 平均可见长度 px | DEV 平均实际墨面积 px | 短碎片比例 | 重叠率 | 选择耗时 s |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| A | 269 | 39.99651% | 0.148399 | 0.083603 | 1136.87 | 1133.74 | 62.76% | 17.30% | 0.01 |
| B | 485 | 39.99908% | 0.089115 | 0.080110 | 1445.66 | 1382.11 | 79.65% | 21.91% | 51.88 |
| C | 270 | 39.99947% | 0.154720 | 0.085360 | 1113.47 | 1150.67 | 60.83% | 14.31% | 29.20 |
| D | 478 | 39.99940% | 0.096782 | 0.084986 | 1402.09 | 1400.82 | 75.76% | 18.85% | 52.62 |

短碎片：每帧可见连续片段中长度 <12px 的数量占比，再跨帧平均；不是缺失 feature-line recall。墨面积为 antialias 后累计 1-gray/255；重叠为二值路径覆盖中被至少两条路径占用的像素比例。详见 [selection_summary.json](chair_dev/selection_summary.json)、[render_metrics.json](chair_dev/render_metrics.json)。

**预算公平性限制：** 四版本均满足预注册的 TRAIN 平均可见长度 40% 预算，误差不足 0.004 个百分点。但该预算没有保证 DEV 轨迹的实际画面墨量相同：D 的 DEV 长度比 A 多 23.33%，实际墨面积多 23.56%。因此不能声称本轮完成了严格等实际墨量的 DEV 优势比较。这个分布差异本身计入 NO-GO/协议局限，不通过改笔宽、换轨迹或事后重选预算来粉饰。

D 的 q 最差25% 比 A 增加 1.65%，但均值显著降低；C 的最差25% 还高于 D。C 也是相同预算下的可行子集，所以后者证明当前 bounded greedy 未找到已知更好的 tail 可行解，**不能仅用此结果认定 tail 数学目标本身被证伪**。B 按预注册在移除 R 后把 U 权重归一为 1、beta 不变，并非保持所有系数不变的纯 R 删除；C 是同权重下的 mean-vs-tail 消融。

## 亲自检查的视觉证据

已打开查看四个固定帧 0/30/60/90、B/C/D 四帧 panel、全部 120 帧接触表和从编码视频解码的连续 0–11 帧 D。没有声称进行了人类盲评或主观打分实验，也不把接触表检查称为完整实时视频观看。

- 四个固定帧中，A/C 主要保留离散的扶手/装饰弧段；D/B 往往增加短线、碎片和局部重叠。线图独立呈现时，靠背、座面和扶手的关系不够清楚，D 没有形成可指出的、伴随消融退化的结构表达提升。这是画面可读性问题，不是要求完整 feature lines。
- D 的局部短段、锯齿和中断在连续帧中仍存在；固定 IDs 没有自动产生干净连贯的墨迹。未计算或宣称新的 P_pop/ink_churn 稳定优势。
- 主视频的 120 个连续帧均保留，24fps、5 秒、360°，无 GT overlay。两部视频均逐帧解码确认 120 帧。最终路径集合在整个片段中不变，仅进行 GS 可见性裁剪；render 阶段 RGB 文件读取日志为空。

主要产物：
- [官方 RGB | A | D 连续视频](chair_dev/rgb_A_D.mp4)
- [B | C | D 连续消融视频](chair_dev/ablation_B_C_D.mp4)
- [固定四帧主 panel](chair_dev/fixed_quartiles.png)
- [固定四帧消融 panel](chair_dev/ablation_quartiles.png)
- [120 帧接触表](chair_dev/complete_contact_sheet.png)
- [连续 0–11 帧 D](chair_dev/first12_consecutive_D.png)

视频、npz 和第三方构建目录按规则留在本地并忽略；代码、报告、manifest、JSON 和小 PNG 提交。

## 失败定位：已验证与尚未隔离

**已验证的 relation detector/matcher 瓶颈：** 58 条双尺度关系中仅 11 条有可解释候选，20 个匹配条目对应 16 个不同组合；9/16 个视角完全没有可解释关系。保留未匹配关系作为分母，不删除困难项抬分。见 [evidence_audit.json](chair_dev/evidence_audit.json) 和 [TRAIN evidence 图](chair_dev/train_evidence_quartiles.png)。

**已验证的组合收益结果：** A/B/C/D 激活关系数分别为 9/3/11/4。D 相比 A 仅新增 TRAIN 99 的一条关系（paths 759,1190），B/C 同样激活该关系；D 另丢失或降低 A 的 7 条关系。因此这个唯一新增代理关系也不能支持“完整机制必要”的 claim。见 [relation_activation.json](chair_dev/relation_activation.json)。

**已验证的代理失配迹象，因果解释尚未隔离：** D 最差四个 TRAIN 视角是 53/79/14/1；在这些视角，即使选满全池，当前 detector/matcher 的 R ceiling 仍为 0。tail 目标的瓶颈视角无法通过增加 R 改善，这支持“当前代理/尾部设计把结构收益排除在关键瓶颈之外”的解释；不等于证明真实形状没有结构关系。

**候选与可见性不能混为一谈：** 100% 候选在固定可见性下也呈现断裂、装饰局部聚集，见 [全池诊断](chair_dev/candidate_pool_quartiles.png)。额外只读诊断将同一候选投影时去掉遮挡裁剪，四帧可见保留长度原为约 33.8–46.9%，去裁剪后确实出现更多座面周边连接，见 [无遮挡诊断](chair_dev/candidate_no_occlusion_diagnostic.png)、[数值](chair_dev/candidate_projection_audit.json)。它包括本应隐藏的线，**不是合法最终 NPR 结果，也不是修复**。目前不能确认问题主要是候选表面附着错误、真实遮挡、还是旧近似 G-buffer 误裁；不能草率把它全归因于“缺线”。没有用此诊断重选任何路径。

## 预注册判定与边界

- 算法语义、TRAIN 隔离、官方 RGB 接入、冻结候选、预算审计、两部完整视频：完成。
- 清晰可见的 D>A 结构关系提升并伴随 B 或 C 对应退化：**未观察到，NO-GO**。
- 严格等 DEV 实际墨量优势：**未验证**；TRAIN 预算匹配不等于 DEV 墨量匹配。
- mesh/GT P/R：未计算、不 gate；没有 mesh、GT label/cache 或额外 2DGS normals 的方法输入。
- TEST 图像/评估：未打开。共享相机 JSON 整体解析含 100 帧元数据，但 seed/pull/selection 只索引登记的 16 个 TRAIN 相机，DEV 由其中第一个相机派生。泛化到 lego/cadpartA/真实场景、所有 frozen 候选池、所有相机范围：均未验证。

停止此轮 VRSS 扩展、调参和三场景计划，保留负结果。若后续决定重启，首先另行预注册“现有路径为什么被可见性裁掉”的输入/渲染审计，并明确 DEV 墨量预算在哪个相机分布计价；本轮不执行该后续研究，不通过调整 relation 权重或补候选抢救结果。

## 时间与 Git 里程碑

候选 38.03s；evidence 15.24s；四个 selector 共 133.72s；视频及指标 130.20s。不包括开发和官方内核编译，均未触及预设超时上限。

已逐个 commit/push 并用 ls-remote 验证：030b0f1（预注册）、84957c4（K/TRAIN 修正）、49152b0（最小实现）、35347df（fixture 修正）、2a4232e（官方内核核验/候选冻结）、a3acd6f（证据与四版本选择冻结）。最终结果提交 SHA 由 `git log -1 -- out/vrss/RESULTS.md` 查询；最终远端 SHA 在交付答复给出，避免自引用哈希。
