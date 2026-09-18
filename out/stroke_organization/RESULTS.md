# Lego 冻结候选路径组织：完整运行，视觉 NO-GO

**结论：本轮 WV-PC 没有解决“候选多但线仍碎”的视觉问题，不进入 Chair，不作为已成立的 M1 主方法。** 已实际完成原论文调研、候选图审计、预注册、实现、单元测试、TRAIN smoke、六臂求解、120帧三套渲染及全帧审阅。代码完成与路径变少不等于方法成功。

最先查看：[同墨面积固定四帧](render/fixed_area_matched.png)、[官方RGB｜A｜C完整视频](render/official_A_C_area_matched.mp4)、[六臂固定四帧](render/all_fixed_area_matched.png)、[三个预标区域](render/regions_area_matched.png)。全部原生/长度匹配/面积匹配视频、54张连续序列 contact sheets 和诊断图见 [GALLERY.md](GALLERY.md)。主结果是黑线白底，无 GT overlay。

## 1. 研究与实现究竟检验了什么

[LITERATURE_AND_DECISION.md](LITERATURE_AND_DECISION.md) 记录本轮实际联网核验的原论文、作者项目页及访问限制。NerVE/NEF 已处理三维边与曲线恢复；SketchSplat 已有端点、重叠、共线合并及多视图过滤；LineGS 已使用 Gaussian 分布清理三维线段；Active Strokes 与 Coherent Stylized Silhouettes 已研究线样本组织和笔触一致性。good continuation、elastica、方向场与路径关联也是已有技术。**普通连接、曲线平滑、GS支撑、持久ID均不能作为本轮创新。**

唯一被检验的机制是 **Witnessed-View Prize-Collecting Path Cover（WV-PC，共享视图见证奖赏路径覆盖）**：同一批视角应能支持整条路径，而不只是各条短边分别得到某些视角的支持；让完整路径竞争固定候选节点，判断能否改善同墨量画面。这只是待证伪机制名称，本轮结果不支持将其包装成已成功的新算法。

实现保留原 frozen D、prune/NMS、官方 RGB、GS depth visibility 和画笔资产。新增 `src/stroke_graph.py` 构造候选支撑管内的兼容边，记录距离、缺口、切向、ID邻域、TRAIN可见性/DT/方向及跨层项；`src/path_cover.py` 生成有界路径提案，按节点、连接和共享见证收益减去启动/短路径/异常转角代价，做 node-disjoint 选择；`src/stroke_simplify.py` 提供保角且受 trust region 限制的简化，主实验 epsilon=0。入口为 `scripts/run_stroke_organization.py`，冻结后显示由 `scripts/stroke_organization_outputs.py` 执行。完整公式及约束见 [ALGORITHM.md](ALGORITHM.md)。

最终新增连线由固定三维候选中心序列构成；未移动任何中心、未新增候选、未拟合Bezier、未逐帧组织。运行时仅投影固定路径并裁剪可见性。所有最终顶点均与输入中心逐位一致，整路径显示子集跨帧固定，实测核验见 RESULTS.json 的 integrity。

## 2. 冻结、来源与协议边界

只在 `stroke-organization` 工作，基点 `3a10d3908173e35d359d41eec1469f5adaac4e56`。输入 `out/raster_state_candidates/lego/step4/pulled_D.npz` 的 SHA256 为 `47ca8925cb86a98886f97aa3c88ef58f5c821cfdcfd656a3fb0a0ec19ca1d489`。旧 step4.json 记录的实际生成代码 commit 为 `993d94f44580d438f34c8d5327ef4a4e7b18606f`；3a10d390 是保留其成果的分支基点，不偷换成生成commit。

输入包含32,854条linelets，其中历史M1a 29,916、新D 2,938；冻结prune后26,995，公共NMS后15,869。A精确复现旧D：2,136条chains、10,470个使用节点，其中新增D节点722，路径NPZ哈希与历史 `paths_D.npz` 完全相同。原chainer端点邻域有14,207对候选近邻，不等于全部可接。

16个TRAIN索引为1/7/14/21/27/33/41/47/53/59/67/73/79/86/93/99；构图读图审计确认仅这些照片。所有路径、manifest和渲染源码在 `76680c7` 提交后才生成DEV轨迹。TEST索引没有读取；manifest中的4个DEV验证照片索引也未读取。本次使用解析环绕120帧、24fps、400px，较旧轨迹相位偏22.5°。过去任务已观察相似环绕，因此这不是新场景的完全盲测。原GS预训练历史split没有独立证实，本轮的TRAIN-only保证限定于候选组织/证据读取。

真实官方vanilla RGB成功运行，renderer commit `472689c0dc70417448fb451bf529ae532d32c095`，CUDA kernel commit `59f5f77e3ddbac3ed9db93ec2cfe99ed6c5d121d`，源码/二进制哈希见 render.json。**可见性深度仍为既有vanilla Gaussian disc proxy，非官方anisotropic raster depth。** 没有冒充官方深度，没引入额外2DGS normals。方法访问日志与输入哈希核验通过，无mesh、GT crease或mesh-derived cache输入；未计算P/R。

固定1px AA黑笔刷。只有一组参数，没有DEV后调参。三套显示：native、长度匹配、面积匹配。后两者分别以A原生全120帧均值的60%为目标，按固定整路径哈希前缀标定，仅用于显示，不反馈构图/评分。两套匹配是独立控制，并非同一集合同时严格等长等面积；保证轨迹平均墨量，不承诺每一帧面积完全相等。

## 3. 实际候选图与运行数值

116,422对潜在连接中，34,043通过物空间约束，32,784再通过图像门槛；后者保留96.30%，拒绝1,259。额外跨深度门槛本数据拒绝0条，不能声称它已产生实证价值。完整图2,377个连通分量，最大3,171节点。R1驾驶室/R2举升臂/R3底板前缘分别有1,799/1,429/1,472个可见节点和3,814/2,667/3,778条内部允许边。候选存在这个任务前提成立，但图的真实拓扑并未因此获得验证。

| arm | 允许边 | 使用节点 | 原生paths | 新D节点进入paths | 求解秒 |
|---|---:|---:|---:|---:|---:|
| A 原chainer | 未导出原内部图 | 10,470 | 2,136 | 722 | 1.82 |
| B geometry-only = C-no-image | 34,043 | 6,490 | 982 | 372 | 22.43 |
| C full | 32,784 | 5,619 | 764 | 330 | 23.53 |
| C-no-global | 32,784 | 10,726 | 1,952 | 672 | 2.29 |
| C-no-corner | 10,018 | 3,801 | 760 | 192 | 3.06 |
| N support-permuted | 32,784 | 5,227 | 636 | 275 | 24.17 |

图构造10.32s，工程smoke 1.85s，三套完整渲染/匹配/视频生成252.08s。没有长实验或训练。原生world-path长度中位数A=.05007、C=.06029、N=.07526；这些数字本身不能说明画面变好。

主判据为实际墨面积匹配，以下均为完整120帧均值：

| arm | AA墨面积px² | 可见长度px | <12px短片段率 | 可见片段median px |
|---|---:|---:|---:|---:|
| A | 4456.68 | 4177.84 | 90.76% | 4.558 |
| B | 4459.34 | 4254.26 | 81.27% | 5.181 |
| C | 4459.86 | 4233.81 | 81.24% | 5.419 |
| C-no-global | 4455.38 | 4344.24 | 86.96% | 4.633 |
| N | 4460.41 | 4315.12 | 76.47% | 6.245 |

**C短片段率相对只降10.50%（要求40%），可见片段中位长度仅1.189×（要求1.8×）**。长度统计按连续可见片段，不把遮挡两侧相加冒充长笔画。B几乎得到同样短片段率，N甚至更好，因此“更长、更少”不是机制证据。

C-no-corner全量面积只有3607.55px²，低于目标19.10%；可见长度3340.89px，低于目标29.58%。该列在matched图中实际UNMATCHED，不能做公平消融推断。没有降低全部目标或给它补墨。其他各组两个预算匹配均在冻结3%容差内。逐帧值、完整三套表、每source存活、长度分布和运行时间见 [NUMBERS.md](NUMBERS.md)、[RESULTS.json](RESULTS.json)、render.json。

## 4. 视觉判定与停止

已经逐页打开54张完整序列contact sheets、三套固定四帧及预标区域图。视频核验为完整MP4解码帧序列审阅，不是实时播放，也不是人类盲评。详细观察见 [VISUAL_REVIEW.md](VISUAL_REVIEW.md)。

R1仍杂乱且可能丢掉原本存在的屋顶长边；R2只有局部斜边连续性变化，机械转折未明显清楚；R3有较长底边，但仍带小环、锯齿和重复线。严格0/3区域达到预注册改善标准；即使宽松计R3局部改善也只有1/3。C没有清楚超过B，同墨面积下相对A也没有形成稳定、可读的少量笔画组织。没有用缺失的履带或mesh recall作为失败理由。

| gate | 判定 | 理由 |
|---|---|---|
| G1 更长且少碎片 | FAIL | 10.50%和1.189×均未达门槛 |
| G2 >=2个预标区域清楚改善 | FAIL | 0个明确通过，局部变化不等于结构表达改善 |
| G3 无持续明显错误连接 | NOT CERTIFIED | 未见巨大的跨部件桥，但无法排除持续细小错误轮廓；不把“没注意到”认证成通过 |
| G4 image/global机制有视觉价值 | FAIL | C未清楚优于B；相对no-global的数字收益未转化为区域改善，null相近 |
| G5 同墨面积仍更清楚 | FAIL | A/C墨量匹配成立，视觉收益不成立 |
| G6 固定3D持久载体 | PASS（约束） | 固定顶点、ID和显示子集；不等于证明时间优势 |

整体 **NO-GO**，已按协议停止，不扩Chair，不添加候选、不移动中心、不新增网络、不重调权重。TEST继续封存。

## 5. 失败定位与对本算法的对抗性检查

**有证据的判断：**图像边门槛弱区分，保留96.3%几何边；C与B在同墨面积下的短片段率相近；null并未显示预期退化；固定候选上的长度/启动成本可以减少路径，但不能自动产生清楚的部件结构。输入候选存在与结构可组织性是两件事。当前最有效的可观察因素更像一般的长路径偏好和删减，而非已验证的共享视图见证机制；因为没有逐项独立消融，不能进一步断言是哪一个罚项起效。

**求解器局限必须正面记录：**这是最多4096 seeds、beam=2、最多36节点的有限提案，加按整路径分数降序贪心集合打包。所有主求解组的交换数都是0。进一步检查发现，当前“一条新proposal替换至多两条旧proposal”的规则，在初始按单条分数降序打包后通常根本没有首个可获益交换：未选proposal冲突的先入路径已不低于它的单条分数，替换多条只会增加损失。因此不能把代码里有交换循环写成实际有效的非局部改进。全局性仅限完整proposal之间竞争，不是联合最优路径覆盖。本轮不在看过DEV后修改求解器救结果。

共享见证是软奖赏而非硬约束：C的764条路径中34条不足3个见证视角，1条没有见证。原有Canny证据也已被前序pull/prune使用，可能缺少额外的拓扑辨别信息；这是符合结果的解释，但本轮没有隔离证明“换证据就能成功”。

graph中10,657个degree>=3节点是邻接歧义，**不是10,657个真实junction**。未选分支都已记录，但没有恢复真实共享端点拓扑。重复约束主要是公共NMS与node-disjoint，不能排除不同节点形成近重复线；零硬约束罚值不能解释为无视觉错接。C-no-corner同时删非平滑边和取消角点优惠，是复合smooth-only消融；B也同时移除image/source项。N保留已筛选的C图，仅置换评分，不是构图null。不能超出这些比较的分辨能力讲机制故事。

可见性继续切断长路径，但raw无裁剪图也有弯曲乱线，所以不能把失败全部归咎于visibility。固定几何中已有偏差、图的拓扑歧义、代理目标和有限proposal共同限制结果；这次实验无法唯一分离四者。它否定的是**本实现、该冻结Lego候选池上的视觉收益**，不是所有全局组织算法。现有结果不足以支撑WV-PC作为M1主贡献；应保留它为有完整控制与视觉证据的负结果。

## 6. 测试、复现与提交

最终45项单元测试全部通过，0.497s；新增12项覆盖跨深度、平行近邻、共同见证、低局部收益长路径、尖角、cycle/degree、确定性、trust region、实际墨量、公共采样和可见片段计量。真实输入和输出另核验所有hash、路径顶点逐位不变、node-disjoint、A历史精确一致、120帧视频完整。结果汇总脚本 `scripts/summarize_stroke_organization.py` 从运行JSON读取数字并执行这些数据断言；不是用测试替代实验。

已执行阶段命令（现有输出受拒绝覆盖保护，不能在历史目录原地重跑）：

```bash
CUDA_VISIBLE_DEVICES=1 OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 /home/u00134/bin/miniconda3/envs/vfsdgs/bin/python -m unittest discover -s tests -v
# 同一环境，顺序执行，实际运行均有 timeout 上限：
python scripts/run_stroke_organization.py audit
python scripts/run_stroke_organization.py graph
python scripts/run_stroke_organization.py smoke
python scripts/run_stroke_organization.py solve --arm A
python scripts/run_stroke_organization.py solve --arm B
python scripts/run_stroke_organization.py solve --arm C
python scripts/run_stroke_organization.py solve --arm C-no-global
python scripts/run_stroke_organization.py solve --arm C-no-corner
python scripts/run_stroke_organization.py solve --arm N
# 提交冻结路径/参数/源码后：
python scripts/run_stroke_organization.py render
python scripts/summarize_stroke_organization.py
```

完整复现依赖服务器上的frozen GS、原图、候选NPZ及既有官方CUDA renderer，不声称纯Git clone即可下载全部资产。视频/NPZ/较大junction日志按ignore留服务器；小图、代码、测试、协议、审计与报告提交。PATH_INDEX.json记录全部路径和junction文件哈希。

提交里程碑：`e38db0e` 冻结文献/协议/图审计；`86148c5` 实现与smoke；`76680c7` 六臂路径及渲染入口在DEV前冻结。每个里程碑均已push并通过ls-remote核验。最终报告提交位于上述commit之后；其实际SHA以Git和最终交付消息为准，避免在文件里预写未发生的commit。没有PR或合并。
