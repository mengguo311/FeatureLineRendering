# 文献核验与唯一算法决定

本轮问题不是抽取更多线，也不是提高 mesh recall，而是在**不移动现有 D 候选中心**的条件下，判断整路径组织能否改善同墨量 NPR。以下来源由本轮实际联网打开。F=原文方法已读取；P=作者/机构项目页或摘要已读取；U=原文未能核验。没有把搜索摘要冒充原文。

## 与最近邻的真实距离

| 原始来源 | 已有技术与本轮关系 | 核验 |
|---|---|---|
| Xiangyu Zhu, Dong Du, Weikai Chen, Zhiyou Zhao, Yinyu Nie, Xiaoguang Han. **NerVE: Neural Volumetric Edges for Parametric Curve Extraction From Point Cloud**, CVPR 2023. [原论文](https://openaccess.thecvf.com/content/CVPR2023/papers/Zhu_NerVE_Neural_Volumetric_Edges_for_Parametric_Curve_Extraction_From_Point_CVPR_2023_paper.pdf) | 学习体素边表示，恢复连接的折线并拟合参数曲线。图连接、曲线拟合都不是新意。本轮不学习边场、不修正点位，而检验 noisy GS 候选上路径之间的竞争。 | F |
| Yunfan Ye, Renjiao Yi, Zhirui Gao, Chenyang Zhu, Zhiping Cai, Kai Xu. **NEF: Neural Edge Fields for 3D Parametric Curve Reconstruction from Multi-view Images**, CVPR 2023. [原论文](https://openaccess.thecvf.com/content/CVPR2023/papers/Ye_NEF_Neural_Edge_Fields_for_3D_Parametric_Curve_Reconstruction_From_CVPR_2023_paper.pdf) | 由多视图边图学习三维边场并恢复线/曲线。不能声称“图像边证据→3D 曲线”为新。这里输入几何冻结，任务是选择、组织而非重建。 | F |
| Haiyang Ying, Matthias Zwicker. **SketchSplat: 3D Edge Reconstruction via Differentiable Multi-view Sketch Splatting**, ICCV 2025. [原文 §4.3](https://arxiv.org/html/2503.14786v2) | 可微优化三维 sketch；明确有端点合并、重叠合并、共线合并和多视图过滤。普通端点连接或“多视图+持久曲线”不够。这里唯一值得检验的差别是：固定候选上，整条路径共享的可见支持是否能改变非局部路径取舍，并在同墨量下改善画面。未证明它构成论文级新颖性。 | F |
| Yang Chenggang, Shi Yuang. **LineGS: 3D Line Segment Representation on 3D Gaussian Splatting**, 2024. [原文 §III-C](https://arxiv.org/html/2412.00477v3) | 用 Gaussian 分布对已有线段进行后处理；涉及位置偏差、过长、重复和不连续。本轮不能把 GS 密度支撑或线段清理当首创；禁止它所采用的位置移动，且目标是 NPR 画面而非线重建精度。 | F |
| Liangliang Nan, Peter Wonka. **PolyFit: Polygonal Surface Reconstruction from Point Clouds**, ICCV 2017. [作者页](https://3d.bk.tudelft.nl/liangliang/publications/2017/polyfit/polyfit.html), [DOI](https://doi.org/10.1109/ICCV.2017.258) | 候选面全局选择是已有的 hypothesize-and-select 思路。它重建多面体表面，不是 curve extractor；本轮既不调用它，也不引入 mesh。 | P |
| Mikhail Bessmeltsev, Justin Solomon. **Vectorization of Line Drawings via PolyVector Fields**, 2018 arXiv / TOG 2019. [作者原始摘要](https://arxiv.org/abs/1801.01922), [DOI](https://doi.org/10.1145/3202661) | 多方向场解决 junction 错接，提醒我们不能用单一平滑方向抹掉机械转折。本文只从核验摘要引用这一点；86 MB PDF 被工具拒绝，未逐节核验其求解器。 | P；PDF U |
| Pierre Bénard, Jingwan Lu, Forrester Cole, Adam Finkelstein, Joëlle Thollot. **Active Strokes: Coherent Line Stylization for Animated 3D Models**, NPAR 2012. [作者原论文](https://gfx.cs.princeton.edu/pubs/Benard_2012_ASC/Benard_2012_ASC.pdf) | 用独立的 2D active strokes 组织线样本并保持笔触连续性。组织、风格载体与底层样本解耦并不新。本轮运行时必须保留固定世界坐标路径，不采用它的屏幕空间动态拓扑。 | F |
| Robert D. Kalnins, Philip L. Davidson, Lee Markosian, Adam Finkelstein. **Coherent Stylized Silhouettes**, 2003. [作者项目页](https://pixl.cs.princeton.edu/pubs/Kalnins_2003_CSS/index.php) | 一致笔触参数化已有深厚基础。本轮只检验固定 carrier 的离线组织；不能宣称持久 ID 自动解决可见性断裂和笔触参数化。 | P |
| Gérard Medioni. **Tensor Voting**，作者技术概述（网页未标出版年）. [作者概述镜像](https://homepages.inf.ed.ac.uk/rbf/CVonline/LOCAL_COPIES/MORDOHAI/tensorvoting.html) | 局部投票、方向与 junction 显著性，以及沿场提取结构，都属于已有技术。局部一致并不能证明跨部件连接正确，本轮因此检查整路径共同见证。 | P |
| David Mumford. **Elastica and Computer Vision**, 1993. [作者档案及出版信息](https://www.dam.brown.edu/people/mumford/vision/shape.html), [扫描原文](https://www.dam.brown.edu/people/mumford/vision/papers/1993b--Elastica-Harvard.pdf) | 弧长/曲率权衡是经典 good continuation；不应把平滑变长当新贡献。本轮不求连续 elastica，而用离散转角和有界候选支撑，保护有图像支持的尖角。扫描件可打开但无可抽取正文，具体公式未作为原文核验结论。 | P；扫描正文 U |
| Jérôme Berclaz, François Fleuret, Engin Türetken, Pascal Fua. **Multiple Object Tracking Using K-Shortest Paths Optimization**, TPAMI 2011. [EPFL 原项目及文献](https://www.epfl.ch/labs/cvlab/software/tracking-and-modelling-people/ksp/), [DOI](https://doi.org/10.1109/TPAMI.2011.21) | 全局轨迹关联/路径数选择已有标准方法。空间图没有时间 DAG，整路径跨视图见证也不是可加边代价，所以不借用它的最优性声称。本轮采用可审计的有限路径提案与集合打包近似。作者 PDF 请求超时。 | P；PDF U |

## 唯一决定：共享视图见证的奖赏路径覆盖（WV-PC）

**Thesis（待证伪）**：同一组视角能支持整条折线，比“每条短边分别被一些视角支持”更能阻止局部贪心拼成错误长线；让完整路径相互竞争，可以在固定墨量下减少碎段并保留转折。简称 Witnessed-View Prize-Collecting Path Cover。它是一个实验机制名称，不是已获证实的新方法。

兼容图顶点为冻结 NMS 后的 3D linelets。边由局部尺度、双端切向、现有候选支撑管、Gaussian ID 邻域、TRAIN 可见性和 Canny DT/方向决定。所有连接只在三维局部邻域提出。投影交点不生成节点。非共线转角可以保留，前提是两侧都受支持；近重合投影却跨深度层的边拒绝。

确定性 bounded beam 产生最多 36 节点的简单路径提案。完整路径奖赏包含候选覆盖、受支持长度、同一视角中可见且受支持的路径比例；惩罚路径启动、短路径、缺口、异常转角。然后对互相竞争的路径做确定性集合打包和最多两轮、每次至多替换两条路径的局部交换。普通路径 degree≤2，无 cycle；候选分叉显式记录未保留臂，不宣称已恢复真实 junction。

这里的“全局”仅指整路径间竞争，**不是全局最优保证**。不得把它写成新的 network-flow 求解器、首次端点连接、首次 GS 曲线抽取或首次 persistent strokes。最强可接受贡献取决于同墨量视觉结果以及 B/no-global 消融；若只有更长的路径统计而没有更好的画面，则机制失败。

选择这一近似而不用纯 min-cost flow，是因为空间图有回环、转角代价涉及三节点、共享见证涉及整路径；强行 DAG 化会引入任意方向偏置。曲线简化只允许删去 trust region 内的冗余顶点，主实验设 epsilon=0，避免靠平滑遮掩错误连接。
