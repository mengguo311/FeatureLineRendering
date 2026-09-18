# WV-PC 实现规范（主实验前固定）

输入中心、切向、半长从冻结 pulled_D 逐位读取；复用原 prune/NMS，A 的节点序列必须和历史 D 完全相等。每个 proposal 是这些中心的有序子序列。主实验 simplify epsilon=0，不改变形状。

图的尺度单位 `s=median(half_length)`。k=12；中心距离≤4s；双端切向与连线绝对余弦≥.4；近似端部未覆盖缺口/局部尺度≤2；连接上9个采样点到现有候选中心的归一化最近距离≤1.25。尺度夹在 [.5s,2s]，避免超大 splat 无限制接线。没有用 mesh 或额外 normals。

每条边在16个 TRAIN 视角投影，使用同一 GS disc z-min、2% 容差和 alpha≥.5 判可见；至少4/9样点可见才可评价。支持为 `exp(-.5*(DT/2px)^2)*abs(tangent_dot)` 的可见样点均值。隐藏样点不作负证据。至少3个可评价视角且≥2视角支持≥.45 才进入 C。B 仅使用物空间图和相同跨深度物理保护。原 seed ID 通过原 p0 精确匹配 PLY 中心恢复（实际最大误差记入 nodes.json），新增节点沿用原 ID set。ID 邻域是几何亲和，不等于真实拓扑证明。

每节点 prize = clip(2l/s,.5,3)，C 再乘 source 均值权重和可见 TRAIN 支持均值。边基础分为 `.8*continuation - .35*clip(gap,0,2) - .25*(1-tangent_agreement)`；C 加 `.6*image_support + .2*ID_affinity - .5*(1-image_support)`。

路径目标：

```
F(P) = .3 Σ node_prize + .35 Σ link_value
       + 3*tanh(length/s/8)*whole_path_witness
       - 2 - max(0,1-length/s/4) - .4 Σ abnormal_turn
```

whole_path_witness：视角须可评价至少30%路径边；同视角中按可见投影长度加权的支持≥.6才是 witness。奖赏为可评价视角的支持均值，乘 `min(witness_count/3,1)`。因此每一短边分别在不同视角获得支持，不等于整条路径有共同见证。B 将 witness=1，完全没有 image/source 项。

三节点实际转角>110°拒绝；其余超过35°的归一化转角平方受罚。C 对相邻两边有≥3共同支持视角的角点将这一罚项乘.15。C-no-corner 则仅保留切向夹角<35°的边。不是从投影相交推断三维 junction。

确定性等间隔 node-ID seeds 最多4096；beam宽2、最大36节点，在3/6/12/24/36节点及死端评估完整路径。beam 扩展优先级是可加项，**非加性见证在完整 proposal 排序、集合选择和交换阶段生效**。这是有提案偏差的有限近似，不保证发现所有好路径。所有正收益提案排序后做 node-disjoint packing；最多两轮一换至多二的收益改善交换。不共享节点等价于重复覆盖的硬惩罚；允许图约束外的 bridge/depth violation 为不可行。JSON 中这些硬约束在可行解中的罚值为0，不能把0写成已证明没有任何视觉错接。

每条普通路径不重复节点、degree≤2。所有潜在 junction 的未选边写入独立审计，**本轮没有宣称恢复真实 junction 或保证全部分支存在**。C-no-global 用相同 C 边分数逐边贪心，显式防 cycle/degree/异常转角，不用完整路径启动成本和见证奖赏。B 就是 C-no-image。N 保留 C 的节点、允许边数量及真实可见性，置换 image 支持列和 node quality；它是保守的评分机制 null，没有把已经筛过的图本身 null 掉。

笔画颜色、线宽、depth visibility 相同。matched 图只对固定路径集合做固定哈希前缀选择；实际 AA 面积非像素计数、非候选数。length/area 是两套独立控制，不声称同一集合同时达到二者。
