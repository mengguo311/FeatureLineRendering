# 从成像底层重建：阶段 F0（先校准状态，不碰画笔）

作者归属：特征线管线属于 Weiren Hao / Tomohiko Mukai（SA 2026）；RaDe-GS 几何栅格化属于 Baowen Zhang 等（ACM TOG，公开源码 `HKUST-SAIL/RaDe-GS@d72f207`）。本阶段为我们的**独立兼容性重建**，不是任一作者的官方实现成果。

输入：已冻结 vanilla GS Lego PLY，不重训，不读取 mesh/TEST，不筛掉 Gaussian；训练相机 `r_0`。先用官方 RaDe-GS CUDA 实现（隔离安装，GPU 0）从同一个 PLY 计算 RGB/alpha/depth/normal，再与当前圆盘代理的状态画面并排。RaDe-GS 自己的公开加载器要求其训练时生成的 `filter_3D` 属性，而这个 vanilla PLY 不具有；仅在实验包装器里直传原始均值、缩放、旋转、opacity、颜色，不假造 `filter_3D`，也不将“从 vanilla 直接推深度”的结果称为作者训练模型。

核心机制：每条射线的 Gaussian 最大响应点 `t*=(vᵀΣ⁻¹(μ−o))/(vᵀΣ⁻¹v)` 与像素内可见权重 `w_i=α_i∏_{j<i}(1−α_j)`。F0 只验收真实成像状态（投影、alpha、深度、法线）并可视化；尚不声称复现 top-4 贡献 ID、门控或最终笔画。要求合成单 Gaussian 单元测试先行，实际 RGB/alpha/depth/normal 成功输出且检验 shape、有限值、图像解码。随后才能继续 F1 像素贡献列表和作者的特征线。
