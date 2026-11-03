# 零散线高斯统一归组：父级结论与交付说明

**研究完成，不是新算法验证完成。** 本报告由真实 `gpt-6-astra`、`ultra` 原会话调研，父级复核原文、执行回执与文件保护记录。所有迁移方案仍是 **PROPOSED / NOT_RUN**。未修改项目代码、原核或旧实验产物，未创建分支、commit或push。

## 核心判断

Astra建议将“同一条边的身份”与“拟合载体”分开：先保留可靠的局部有限片段，再联合判断哪些片段共享一个 `edge_id`。这是待检验的设计推断，不是论文或现有数据已经证明的收益。

v05 **已经支持polyline**；新建议不是简单地把直线改成折线，而是让同一身份对应多个有序局部载体，并允许竞争解释、回拆和重新分配。原核的几何、协方差、opacity、宽度、行序和核数仍不改变；辅助载体不能替代实际核渲染。

## 优先级

1. **分层载体＋全局端口路径选择。** 先分开“重复观测支持某片段”和“片段之间的拓扑衔接”，再联合选择完整路径。借鉴网络流轨迹关联和线稿共同参数化，但二维、带时间顺序的问题不能直接提供一般三维端口路径问题的最优性保证。[3][9]
2. **带正负约束的全局归组。** 用一致图划分比较多个竞争解释，并允许重分配；可信的排斥证据可阻止近平行边被桥链吞并。Lifted multicut提供非邻接关联与must-cut/must-join表达；曲线转角、分支和无支持间隙的规则仍须另行设计，不能拿优化目标值代替物理正确性。[1][2]
3. **有限直线／样条库＋鲁棒联合归属。** 多个候选模型竞争同一批观测，并允许离群、UNKNOWN和重分配。借鉴PEARL的全局能量与T-Linkage的多假设偏好；PEARL只取得局部极小，T-Linkage仍是凝聚式方法，均不是现成的此NPZ归组器。[4][5]

特别注意：StrokeStrip输入已经带cluster_id，不能把它宣传成自动解决全部分簇；其实现依赖单独安装、许可的Gurobi。[14]

## 一个最小后续实验——尚未启动

只比较第1条：共享新片段表示、候选、代价、UNKNOWN与几何守卫的 **端口贪心 vs 联合路径选择**。保留已封存v05作额外参考，不能把表示改变和求解器改变混成一项因果收益。

- 预先冻结8个真实上下文：直段2、曲段2、平行、T分支、深度交叉、无支持gap各1；包含全部竞争邻居，不只挑成功成员。
- 首先确认正确续接是否在已有候选中；不在则报告候选瓶颈，不暗中扩半径。
- 不补画gap、不移动原核；以真实原核全景、完整上下文及固定相机短序列的干净、完整、稳定为首要判据。
- 若只有assigned／颜色统一的变化而没有可辨的同边连续性收益，或误吞明确独立的平行／分支，则不扩大到全资产。
- 已看过的开发案例不是held-out；建议预算与solver尚未冻结，本报告**不是可直接执行的RUN_REQUEST**。

不建议继续仅靠更宽的DBSCAN／连通分量、更多M轮或fit预算。固定全部核参数时，换edge_id也不会清除已有几何尖刺。若需删除／修复尖刺，须另立资产质量或显示规则任务，不能偷算成本次归组成功。

## 实际核验范围

- 真实模型子进程退出码0，使用指定模型、effort和原session；没有另外启动综合恢复。
- 前后项目快照的854个已落地文件哈希、HEAD和clean状态相同。监督器前后实核12,020条封存引用未变；父级复核其执行代码与回执，**没有再次远端重算这12,020条hash**。
- 六个原始交付文件与Astra登记SHA-256逐项一致；15个来源的登记引文在保存的证据中逐条匹配。父级另行获取8个核心来源，核对方法与适用范围，未将作者代码入口当作已安装运行。
- 15是来源条目数，包含论文／作者项目页／代码，并非15篇全文。Astra对8篇取得全文并阅读相关章节，对StrokeAggregator、StrokeStrip、NEF只使用作者项目说明；不声称逐页读完全部论文。
- 引文CLI返回0，但中文句子计数为0：只验证编号、URL与原句证据链，不代表逐句引用覆盖、物理身份正确或新方法有效。

## 文件导航

- `METHOD_SURVEY_ZH.md`：Astra原始中文报告，保持原字节。
- `RECOMMENDATIONS.json`：原始三条方法建议和未运行的反证实验设计。
- `citations.json`：Astra原始15来源账本；`parent_review/citations.json`保留相同编号并补充父级原文证据。
- `notes/SOURCE_READING_REGISTER.json`：原始实际阅读范围，含未获取全文、失败重试说明。
- `parent_review/PARENT_VERIFICATION.json`：父级核验范围与明确限制。
- `FINAL_STATUS.json`、`research_0/LAUNCH.json`、`research_0/EXIT.json`及保护回执：真实运行与只读保护记录。
- `evidence/SELECTED_QUOTES.md`：来源链接及短引文，不含第三方整篇论文。

轻量交付包**不包含原论文PDF／完整抽取文本**。阅读登记中的原始evidence文件路径对应服务器完整研究档案，不应当作轻量包已包含的文件。原始档案位置：`/mnt/hdd1/u00134/radegs_paper_reproduction_v01/line_kernel_grouping_method_survey_20261031`。

AI披露：文献筛选、方法迁移与报告由Astra辅助完成，父级另做来源与工程核验；优先级是研究建议，不是已验证结论。

## Sources

[1] https://arxiv.org/pdf/1505.06973 — Efficient Decomposition of Image and Mesh Graphs by Lifted Multicuts
[2] https://proceedings.mlr.press/v70/hornakova17a/hornakova17a.pdf — Analysis and Optimization of Graph Decompositions by Lifted Multicuts
[3] https://www.cvlibs.net/projects/autonomous_vision_survey/literature/Zhang2008CVPR.pdf — Global Data Association for Multi-Object Tracking Using Network Flows
[4] https://www.hossamisack.com/pdfs/pearl_ijcv12.pdf — Energy-based Geometric Multi-Model Fitting
[5] https://fusiello.github.io/papers/jvci17.pdf — Multiple Structure Recovery with T-Linkage
[9] https://www.cs.ubc.ca/labs/imager/tr/2021/StrokeStrip — StrokeStrip: Joint Parameterization and Fitting of Stroke Clusters
[14] https://github.com/davepagurek/StrokeStrip — StrokeStrip: Joint parameterization and fitting of stroke clusters
