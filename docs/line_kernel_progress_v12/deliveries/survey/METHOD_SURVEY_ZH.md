# 零散线高斯统一归组：方法筛选

**建议优先尝试：①分层载体上的全局端口路径选择；②带远程排斥和几何约束的全局归组；③有限直线／样条模型库的联合归属与模型选择。** 关键改变是把“共享 edge_id”与“所有核必须压进同一个拟合载体”解耦，同时允许竞争解释保留、重分配。不是继续增加M轮、预算或放宽距离。

本次仅研究；以下迁移方案全部为 **PROPOSED／NOT_RUN**，没有收益证明。已核实发布HEAD `77aaee103a74d6f9fa912915ea2d90b16d40906e`、数值冻结版本及父级验收；只读报告、必要源码和四张已有图，没有加载完整数组。父级工程验收PASS，科学结论PARTIAL。相较L1的assigned增加不是准确率，53254的44.289p支持只有3.458p最长连续段，不能称为完整长边。

## 当前限制：六件事不能混为一谈

1. **候选信息不足**：邻近采样和端点补充只回答“附近有谁”，没有新视图或表面证据，无法判断两段是否同一物理边。补充候选曾有建筑收益，故不能认定候选已充分。
2. **全局关联受限**：源码先按局部端口近似并列标歧义，再按成本作不相交提交；保护prefix保住旧结果，也锁住重新解释机会。它没有优化完整路径或整体划分的质量。
3. **表示与曲率受限**：每次合并后只保留一个line/polyline；全部历史成员须同时过最大残差／切向及转角守卫。一个错核可否决整组，模板次序也会影响曲线。这是源码支持的瓶颈推断，尚非消融结论。
4. **重复观测多重性**：核多不等于独立证据多。v05已经按占用区间均衡拟合、按区间并集计支持；再做一次密度加权不是新方法。尚需把“多个观测支持同一小段”和“小段之间的拓扑连接”分层。
5. **源几何噪声**：ficus和颅骨全景有显著长尖刺。固定位置、协方差、opacity且渲染全部核时，换edge_id只能改善身份显示，不能删掉尖刺。Gaussian形状协方差也不能直接当成测量置信度。
6. **身份不可辨识**：几何重合、相同切向但不同物理来源，可能无法仅凭现有资产区分。旧parent不是标签；UNKNOWN必须保留。当前线核渲染没有源表面遮挡，投影交叠也不是同边证据。

## 六类核心方法与两类条件路线

下表“文献做了什么”与“项目迁移判断”分列；论文和代码链接见Sources，实际阅读范围见[引文阅读账本](notes/SOURCE_READING_REGISTER.json)。

|方法族|文献的真实输入→输出、能力|本项目迁移与限制；实现情况|
|---|---|---|
|全局图划分：multicut／correlation clustering|带边成本的图→一致划分；[Lifted Multicut](https://arxiv.org/pdf/1505.06973)加入非邻接关联，后续工作研究must-join/must-cut约束。[1][2]|用载体片段为节点，远距离平行排斥、跨局部的共同证据为边。划分本身不保证单曲线、无分叉，须另加端口或高阶约束；NP难，启发式不保证全局最优。作者C++库可见。[12]|
|路径覆盖／最小费用流|[Zhang等](https://www.cvlibs.net/projects/autonomous_vision_survey/literature/Zhang2008CVPR.pdf)以有时间顺序的检测→不重叠轨迹，显式容纳起止、误检和遮挡。[3]|将轨迹思想迁到有限载体端口；重复核不是路径节点。3D无天然时间DAG，闭环、无向端口和曲率约束加入后，不能照搬普通最小费用流的最优性。原作者代码本次未核实。|
|多模型鲁棒拟合／MDL|[PEARL](https://www.hossamisack.com/pdfs/pearl_ijcv12.pdf)以点和模型假设→模型标签、参数与离群点，交替标签优化和重估；只保证局部极小。[4] [T-Linkage](https://fusiello.github.io/papers/jvci17.pdf)以假设偏好向量聚类，最后拟合，仍是凝聚式方法。[5]|有限直线／局部样条竞争，允许噪声进UNKNOWN；需防无限直线把远处共线段合并、模型成本吞并近平行边。T-Linkage有作者MATLAB入口[13]；PEARL完整实现未核实。|
|主曲线／弹性载体／骨架|[主曲线](https://hastie.su.domains/Papers/Principal_Curves.pdf)从点云得到穿过分布中部的一维非线性摘要，原文讨论曲率与平滑偏差。[6] [L1-medial](https://www.cs.tau.ac.il/~dcor/articles/2013/L1-Medial-Skeleton-of-Point.pdf)从原始点云得到形状的局部中心骨架。[7]|主曲线可用于已判定单边的局部carrier，不能替代归组。整物体骨架会把表面边／双轮廓收缩为中心结构；不是本任务身份恢复。两者当前配套代码可获取性未核实，不列首选。|
|线稿／笔画聚合|[StrokeAggregator](https://www.cs.ubc.ca/labs/imager/tr/2018/StrokeAggregator/)聚类过描二维笔画并拟合共同曲线[8]；[StrokeStrip](https://www.cs.ubc.ca/labs/imager/tr/2021/StrokeStrip/)输入已分簇vector strokes，联合一维参数化后输出聚合曲线，并不自行发现全部簇。[9][14]|借鉴共同弧长与重叠对应；3D无统一纸面、绘制次序和“作者意图”。近平行实边不能当过描。前者页面提供非商业Windows binary；后者开源但依赖另行许可的Gurobi。本次只读项目说明／代码README。|
|多视图轨迹与重投影|[LIMAP](https://arxiv.org/pdf/2303.17504)以标定图像、2D线匹配及可选SfM点→3D直线tracks和结构关联；其track阶段也使用评分剪枝后的connected components。[10]|值得借的是新观测和跨视图一致性，不是把它包装成全局最优曲线算法。需真实图像边缘、相机和可见性信息，现有线核自渲染不提供独立证据；作者工具库可用。[15]|
|结构先验（条件路线）|LIMAP利用线点、平行和正交关联。[10]|建筑可用平面交线／消失方向提出候选，但同方向不等于同edge_id；植物、颅骨不能默认Manhattan。需额外可靠平面或观测，不能用规则补造边。|
|学习方法（条件路线）|[NEF](https://yunfan1202.github.io/NEF/)从标定多视图边缘图训练隐式边密度，再提取参数曲线；作者提供代码入口。[11]|这是训练与重建，不是冻结核的直接归组器。learned affinity／GNN另需适用标签或经验证权重；当前没有已核实的即插即用模型。暂不优先，不能以自生成组作真值证明成功。|

**为何不是直接connected components或DBSCAN？** 一条弱桥就可传递“同组”；空间密度不能区分平行边、交叉边与重复观测。谱聚类能缓解局部贪心，但若相似度本身错误，谱也不会产生缺失的物理证据。LIMAP使用连通分量并非反例：它先引入真实多视图匹配和几何筛选，输入证据与这里不同。

## Top 3：具体如何迁移（均为推断）

**① 分层载体＋全局端口路径选择。** 输入现有seedlet、有限载体、成员行、切向和端点。一个edge_id持有多个有序有限片段；重复观测挂在片段支持层，不消耗拓扑度数。目标联合考虑连接可信度、路径起止和转角，端口最多一个续接；曲率通过相邻片段方向约束，近平行排斥另存，真分支保留junction及不同边身份。无证据的中断仍是未支持区间，不补画；未决关联留UNKNOWN或候选列表。与v05不同的是整条路径联合选，不要求每轮只配一对，也不先将全组压成一个模型。

现有资产可支持原型，但可靠重叠归属未必齐全。局部有明确弧长顺序时可建DAG费用流；一般3D需端口整数规划／路径集合选择，不能声称多项式全局最优。最简单强基线是在**同一片段表示、候选和约束**上做现有成本排序的端口贪心。最便宜反证：在真实弯曲／平行冲突区域，联合方法若仍选错延续，或只让颜色更统一而没有更多可见连续正确片段，就否定这次迁移。错误的重叠压缩、端点方向及环路处理是主要风险。

**② 带cannot-link与高阶几何约束的全局归组。** 输入同一批片段和带正负证据的候选图，以一致划分代替逐轮合并；共同身份下保留多载体，不强行平均。用远程排斥阻止邻近桥链吞并平行边，以三元转角／分支约束限制曲线拓扑；UNKNOWN是未决状态，不是把全部未知并成一个类。只把高可信冲突设为硬约束，距离远、遮挡或v05一次拒绝都不能直接当cannot-link。[1][2]

已有几何可启动，但关联代价需要校准，不能凭空称为概率。基线为同一signed graph上的局部凝聚，再对比允许移动、分裂和重分配的求解；几何约束必须一致。最便宜反证是固定真实平行／T/X反例：若全局目标下降却出现巨组、支路被吞，目标设计失败。另测不改变几何的候选顺序置换；持久ID应在最终归属上单独管理，不能拿最小行号稳定冒充成员稳定。

**③ 有限模型库＋鲁棒联合归属。** 输入现有有限直段、局部曲段假设及原观测，模型表示采用有限支持直线／分段样条。以几何与切向残差、有限域外代价、模型复杂度和UNKNOWN代价联合分配；允许在多个候选载体之间重新归属，再重估辅助模型，不动Gaussian。可借PEARL的竞争与离群标签、T-Linkage的多假设偏好；共同参数化只在已兼容的重叠簇内使用。[4][5][9]

曲线靠局部样条表达，平行边靠独立有限模型，分支拆为多个模型而非一个平均中心；端点邻接需另验，不能从低残差推断拓扑。现有资产可做，但不是直接运行论文代码。强基线：固定同一模型库的最近残差分配＋UNKNOWN；比较联合分配是否真减少错误碎裂。最便宜反证：重复某段观测的权重压力测试、相交曲线和两条近邻平行线；若模型数惩罚促使合并，或样条追逐尖刺／跨gap，就失败。噪声尺度、复杂度惩罚及初始模型覆盖是主要风险。

## 唯一建议下一步：一个小型真实区域对照，由用户另行决定

选①，先比较“同一复合片段表示上的贪心端口连接”与“联合路径选择”，**不同时测试②③、不训练、不扫阈值**。建议冻结8个真实局部上下文：两条直段、两条曲段，以及parallel、T分支、深度交叉、gap各一；由已有案例建立候选清单，连同所有竞争邻居封存，不能只截取成功成员。选择规则和疑难标注应在看新方法输出前固定；无法从现有证据判定的关联标为不可判，不强造GT。

先复用已有候选和数值守卫，只改变路径联合选择；共同片段表示、代价、UNKNOWN、重复支持权重与输出核完全相同。原片段的残差／切向仍各自受约束，完整组合还要检查转角、交叉、分支及gap，不能假定两两通过就能传递。这个复合表示不是与v05等价的加速，因此另保留封存v05为参考，并用共享新表示的贪心对照隔离求解策略。若候选不含人工可辨的正确续接，记录候选瓶颈并停止，不能暗中扩半径。未来预算建议CPU/BLAS≤2、单次计算硬上限1800秒，非耗时预测；实现、许可及输出范围需新授权，当前没有启动。

评价顺序为：固定原核全景、完整上下文单组、固定相机短序列中的干净／完整／稳定；再看误吞、丢失和支持区间诊断。视频只是视角一致性展示，旧训练／已阅视角不是held-out，也不证明物理身份。若两种方法均只有重着色、没有可辨直线与曲线收益，或任何已明确的平行／分支被吞，不扩大到全资产。所有方案保留原核和不支持gap；若最终需求还包括消除尖刺，需另议源资产质量或显示规则，不偷换成本次归组收益。

不值得继续的是：更宽DBSCAN／连通分量、无新增证据的M轮或fit预算、直接骨架收缩、拿高assigned替代视觉验收。最重要的不确定性是现有几何究竟足以辨别多少真实同边关系；任何求解器都无法凭空补足这一信息。

读取原文与失败记录在[evidence](evidence/)及[阅读登记](notes/SOURCE_READING_REGISTER.json)。核心PDF取得全文后阅读相关章节；StrokeAggregator/StrokeStrip与NEF仅以作者项目说明为证据，未宣称读完其全文。代码仅核查入口／README，均未安装运行。引文CLI核验只验证编号与原句链，不验证迁移方法正确性；其中文句子统计为0，不构成逐句引用覆盖认证。

## Sources

[1] https://arxiv.org/pdf/1505.06973 — Efficient Decomposition of Image and Mesh Graphs by Lifted Multicuts
[2] https://proceedings.mlr.press/v70/hornakova17a/hornakova17a.pdf — Analysis and Optimization of Graph Decompositions by Lifted Multicuts
[3] https://www.cvlibs.net/projects/autonomous_vision_survey/literature/Zhang2008CVPR.pdf — Global Data Association for Multi-Object Tracking Using Network Flows
[4] https://www.hossamisack.com/pdfs/pearl_ijcv12.pdf — Energy-based Geometric Multi-Model Fitting
[5] https://fusiello.github.io/papers/jvci17.pdf — Multiple Structure Recovery with T-Linkage
[6] https://hastie.su.domains/Papers/Principal_Curves.pdf — Principal Curves
[7] https://www.cs.tau.ac.il/~dcor/articles/2013/L1-Medial-Skeleton-of-Point.pdf — L1-Medial Skeleton of Point Cloud
[8] https://www.cs.ubc.ca/labs/imager/tr/2018/StrokeAggregator — StrokeAggregator: Consolidating Raw Sketches into Artist-Intended Curve Drawings
[9] https://www.cs.ubc.ca/labs/imager/tr/2021/StrokeStrip — StrokeStrip: Joint Parameterization and Fitting of Stroke Clusters
[10] https://arxiv.org/pdf/2303.17504 — 3D Line Mapping Revisited
[11] https://yunfan1202.github.io/NEF — NEF: Neural Edge Fields for 3D Parametric Curve Reconstruction from Multi-view Images
[12] https://github.com/bjoern-andres/graph — Graphs and Graph Algorithms in C++, including Minimum Cost (Lifted) Multicuts
[13] https://fusiello.github.io/demo/jlk/index.html — Robust fitting of multiple models with J-linkage and T-linkage
[14] https://github.com/davepagurek/StrokeStrip — StrokeStrip: Joint parameterization and fitting of stroke clusters
[15] https://github.com/cvg/limap — LIMAP: 3D mapping toolbox
