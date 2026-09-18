# 主路径求解完成；DEV 仍未打开

固定参数一次运行，A/B/C/no-global/no-corner/N 分别生成 **2136 / 982 / 764 / 1952 / 760 / 636** 条固定三维路径。C 使用5619个节点，原A使用10470个节点。C/world median长度 .0603、A .0501，不能据此宣称画面更好。Null 的 median .0753 比 C 更长，已经说明“更长”不是有效性证明。

求解时间分别约1.82 / 22.43 / 23.53 / 2.29 / 3.06 / 24.17秒。每个 arm 的原始路径、完整目标分解、源ID/标签、见证视角和未保留图分叉都已经输出。A 的 npz SHA 与历史 paths_D **完全一致**。没有候选中心修改。

后续只做已经预注册的墨量显示校准和渲染，不修改图、分数、路径或阈值。所有 arm 使用同一个 visibility 采样步长：冻结节点 median half-length 的0.5倍；不沿用按各 arm 自身 median segment 改采样步长的隐含差异。原 chainer 输出仍完全不变，仅所有 arm 的公共可见性采样统一。

完整 potential-junction 拒绝日志较大，保留服务器并在 PATH_INDEX.json 中逐 arm 记录 SHA；它们不是确证的真实 junction。普通路径保持 node-disjoint，尚未解决共享端点的真实多分支组织。
