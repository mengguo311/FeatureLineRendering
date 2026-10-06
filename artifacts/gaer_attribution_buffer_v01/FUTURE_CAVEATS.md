本阶段只验证工程缓冲区，不检验 H1，不支持几何边语义、因果责任或多视图/时间一致性结论。

Hao 与 Mukai 的 [SIGGRAPH Asia 2026 作者预印本](https://mukai-lab.org/content/SA2026PosterHao.pdf) §2 已保留 top-K 原语 ID 与 alpha*T 权重，并比较邻像素 raster states。本阶段的机制与其重合，不作新颖性声明；旧 RaDe-GS 的深度/法线通道未被移植。

仅作为未来研究备忘：对总质量严格为 1 的非负分布，L1 距离的一半等于 `1 - sum(min(p_i,q_i))`，因此归一化 L1 与支持重叠距离存在直接关系。归一化会抹掉总 alpha 与 top-K 覆盖率的差异；带 epsilon 的归一化不一定严格满足单位总质量。本阶段没有计算邻域分布差或任何边分数。

上传文件的未来公式 `n=normalize(grad(E))` 在边响应脊线处可能因梯度为零而不定义。top-K 未保留某 ID 表示未知的截断质量，不能当作真实零贡献。删除某个 Gaussian 会改变后续 T，并可能露出后景或产生空洞。任何后续采样、补偿、移除实验或算法改动都需要下一阶段的明确授权。

完整可见颜色应写为 `C(p)=sum(w_i(p)*c_i(view))+T_final(p)*background`。本实现的 full SH3 颜色依赖视角，权重仅是合成系数；相同贡献权重并不保证相同 RGB。图中的 alpha、coverage、dominant ID 是缓冲区诊断，不是边检测结果。
