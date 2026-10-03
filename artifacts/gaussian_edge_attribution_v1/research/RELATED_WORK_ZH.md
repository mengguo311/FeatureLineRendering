# 文献定位与实现边界

本阶段研究冻结模型中参与边缘形成的 Gaussian，而非恢复三维曲线。相关工作提供的是属性随可见性混合投影的依据，不构成本实验已经获得表面几何边线或对象实例身份的证据。

Gaussian Grouping 的 ECCV 2024 原文第 5–8 页、图 2 和公式 1–3 已读取。它先用 SAM 生成掩码，再以 DEVA 跨视图关联身份；每个 Gaussian 增加 16 维可学习身份编码，以可微 alpha 混合投影到图像。二维分类交叉熵与三维近邻 KL 正则参与联合重建训练；论文明确同时学习 Gaussian 属性。这里的“保留原属性形式”不能误读为冻结既有检查点。[论文](https://www.ecva.net/papers/eccv_2024/papers_ECCV/papers/04195.pdf)

官方实现也直接支持这一理解：`scene/gaussian_model.py` 设置 `num_objects=16`，优化器同时包含位置、外观、不透明度、尺度、旋转和身份参数；`train.py` 将图像重建、二维身份分类和三维正则损失组合，并保留增密/裁剪。`utils/loss_utils.py` 通过欧氏近邻约束类别分布的 KL。训练说明给出的自有数据流程要求准备 DEVA 关联掩码。[固定版本官方代码](https://github.com/lkeab/gaussian-grouping/tree/0ab60afed3385b717c985af1d30a20f7b0884c89)、[训练实现](https://github.com/lkeab/gaussian-grouping/blob/0ab60afed3385b717c985af1d30a20f7b0884c89/train.py)、[正则实现](https://github.com/lkeab/gaussian-grouping/blob/0ab60afed3385b717c985af1d30a20f7b0884c89/utils/loss_utils.py)。

本阶段固定原始 Gaussian 行 ID 与全部模型属性，仅把独立的二维颜色、深度/遮挡及 alpha 轮廓证据，按原生遍历贡献 `w=alpha*T` 解析地汇集成每 Gaussian 分数。无需 SAM、DEVA、二维线点匹配、可学习标签或新增拟合。这是受属性提升思想启发的冻结模型归因实验，不是 Gaussian Grouping 论文复现，也不提出新的方法优先权或新颖性主张。未观测或贡献截断不等于负标签；KL 向遮挡内部传播标签的功能不在本阶段内。

原始 3DGS 论文第 3 节及第 6 节已读取。其颜色混合以排序后的 splat opacity 与前序透射率加权，且 tile 层级排序、阈值剔除与提前终止是实际渲染定义的一部分。因此“完整投影”在本报告中表示保留完整模型、使用同一原生遍历的所有有效贡献，并不表示对无限支撑 Gaussian 的精确连续体积分。[原始论文](https://repo-sam.inria.fr/fungraph/3d-gaussian-splatting/3d_gaussian_splatting_low.pdf)、[官方前向渲染代码](https://github.com/graphdeco-inria/diff-gaussian-rasterization/blob/59f5f77e3ddbac3ed9db93ec2cfe99ed6c5d121d/cuda_rasterizer/forward.cu)。

实际缓存采用既有 RaDe 原生分支提供深度，冻结模型来自 vanilla 3DGS。沿用 SH0、白背景、kernel_size=0 的已校准配方；不把 RaDe splat normal 或 covariance axis 当作物理表面法向。导出 top4 的插桩源码在原生颜色累加使用的同一个 `aT=alpha*T` 处记录原始 ID/权重/层深度，没有按 top4 总和重新归一化。

所有论文/代码获取 URL、字节数与 SHA256 见 `SOURCE_FETCH.json`；官方仓库的所读 HEAD 记录另存 `*_HEAD.json`。原文 PDF、文本摘取和源码副本保留于本目录但不纳入小型 Git 交付。阅读使用的是公开主来源；没有以他人的比较图或论文指标替代本实验测量。
