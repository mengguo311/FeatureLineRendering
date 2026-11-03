Astra 已完成调研。它建议优先改变“归组方式”，而不是继续堆拟合轮次。

核心是：**把“属于同一条边”与“必须拟合成一个载体”分开。** v05已经支持折线，下一步不是再换一个曲线拟合器，而是让多个有序局部片段共享edge_id，并全局处理竞争关系。

**三条优先路线（均未运行）：**

1. **分层载体＋全局路径关联，最优先。** 原核先归到局部片段，再联合决定片段怎样接成同一条边；重复观测不抢拓扑连接名额，无支持gap保留、不补画。网络流轨迹关联可提供思路，但一般三维没有天然时间顺序，不能直接继承普通费用流的最优性保证。[3]
2. **带正负约束的全局归组。** 用一致图划分处理多个竞争解释，允许重新分配，而不是永久锁住早期合并；可信排斥证据用于隔开近平行边。曲线和分支约束仍需另加。[1]
3. **多模型竞争＋鲁棒归属。** 多个有限直线／样条候选共同竞争观测，保留UNKNOWN，避免一颗错核否决整个大组；可借鉴PEARL，但它没有全局最优保证。[4]

**建议的最小验证：**冻结8个真实直线、曲线及平行／分支／深度交叉／gap上下文，在相同表示、候选与约束下，只比较“端口贪心”和“联合路径选择”。若只是颜色统一、assigned增加，或吞并明确独立的边，就不扩大实验。

Astra也不建议继续仅靠更宽DBSCAN、更多M轮或直接骨架化。**仅改分组不能清除原核已有的尖刺。**

本次只做调研与核验：指定Astra ultra正常退出，代码和旧资产保护检查未变，未实施新算法、未启动实验。完整中文报告及带来源／核验记录的轻量包附下。

## Sources

[1] https://arxiv.org/pdf/1505.06973 — Efficient Decomposition of Image and Mesh Graphs by Lifted Multicuts
[3] https://www.cvlibs.net/projects/autonomous_vision_survey/literature/Zhang2008CVPR.pdf — Global Data Association for Multi-Object Tracking Using Network Flows
[4] https://www.hossamisack.com/pdfs/pearl_ijcv12.pdf — Energy-based Geometric Multi-Model Fitting
