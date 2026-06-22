# Novelty / 先行研究调研 —— 3DGS 混合特征线渲染

> 主题:**结合 object-space(直接从 3D Gaussian covariance 提取 silhouette/crease/corner 候选,无需重建 mesh)与 image-space(G-buffer 上 depth+normal 边缘检测)的混合特征线 NPR 渲染,实现时间稳定、实时、且无需重训 3DGS。**
>
> 检索时间 2026-06。知识截止 2026-01。下表每条引用都附了实际检索到的 URL;无法核实的条目已明确标注。

---

## 一、结论(中文速览)

**novelty 基本成立 —— 中高置信度。** 在 2023–2026 的公开文献里,**没有**发现与你这个具体组合相同的工作。相邻文献清晰地分成两大阵营,且都**不是**你要做的事:

1. **3D 边/线"重建"类**(EdgeGaussians、SketchSplat、LineGS):用 Gaussian 作为优化基底,从多视角 edge map **反求**参数化几何(直线/曲线)。它们用到了"covariance 朝向即边缘线索"这一点,但目标是**重建几何**,不是渲染稳定的风格化特征线。
2. **照片级风格迁移/风格化类**(StyleGaussian、G-Style、StylizedGS 等):对 splat 重新上色/上纹理,不产出矢量化特征线,也没有 G-buffer 线绘制管线。

最接近你"image-space 那一半"的,是一篇 2026-06 的 Houdini 博客实验(非正式、未完成、纯 image-space 后处理,无 object-space 的 Gaussian 几何成分,也不谈时间稳定),**不构成竞争**。

**置信度为何不是 100%:**(a) 3DGS 的 NPR 是个快速演进的小众方向,2025–2026 可能有用我没命中的术语发表的论文;(b) 我依赖搜索引擎/项目页,没有逐篇翻 SIGGRAPH Asia 2025 / PG 2025 / Eurographics 2026 / NPAR・Expressive 的完整 proceedings(见"风险与盲区")。

---

## 二、最接近的工作(Closest Works)

| # | 标题 | 出处/年份 | URL | 它做了什么 | 与你的差异 |
|---|------|----------|-----|-----------|-----------|
| 1 | **EdgeGaussians: 3D Edge Mapping via Gaussian Splatting** | arXiv 2024 (2409.12886) | https://arxiv.org/html/2409.12886v2 | 用 GS 学习有向 3D 边点(mean=位置,最大方差方向=边朝向),聚类后拟合线段/Bézier | **最接近"从 covariance 取边"的思路。** 但它是**反求 3D 几何**,非 NPR 渲染、无 image-space 融合、不谈时间稳定。应作为"covariance 朝向=边线索"的先例引用。 |
| 2 | **SketchSplat: 3D Edge Reconstruction via Differentiable Multi-view Sketch Splatting** | ICCV 2025 | https://arxiv.org/abs/2503.14786 · https://oceanying.github.io/SketchSplat/ | 把从参数化 sketch 采样的 Gaussian 可微光栅化,与 2D edge image 对齐来优化紧凑 3D 边 | 重建,非渲染。图像 loss 用于**拟合几何**而非输出特征线。作为"相关重建工作"列出。 |
| 3 | **LineGS: 3D Line Segment Representation on 3DGS** | arXiv 2024 (2412.00477) | https://arxiv.org/html/2412.00477v3 | 几何引导的 3D 线段重建 + 训练好的 3DGS,用集中在边上的 Gaussian 精修线段 | 仍是结构线重建。佐证"Gaussian 会聚集在边缘"这一可利用观察。 |
| 4 | **2D Gaussian Splatting (2DGS)** | SIGGRAPH 2024 | https://arxiv.org/abs/2403.17888 · https://surfsplatting.github.io/ | 把 3D Gaussian 压成有向 2D disk,给出视角一致的 normal+depth,实时 | **法线/几何基础。** 你的 object-space crease/silhouette 与 normal G-buffer 都受益于 2DGS 式 intrinsic normal。作为法线来源引用。 |
| 5 | **SuGaR: Surface-Aligned Gaussian Splatting** | CVPR 2024 | https://arxiv.org/abs/2311.12775 | 正则把 Gaussian 对齐到表面,Poisson 抽 mesh,再把 Gaussian 绑定到 mesh | 你**明确要避开**的 mesh 路线。作为"如果先重建 mesh"的对照,凸显你 no-mesh 的卖点。 |
| 6 | **DN-Splatter: Depth & Normal Priors for GS** | arXiv 2024 | https://maturk.github.io/dn-splatter/ | 给 3DGS 加 depth+normal 监督,得到更好的几何与渲染 normal/depth | 正好提供你 image-space 那半所需的 **depth+normal G-buffer**。若原版 3DGS 法线太噪,可作为获取可靠法线的途径。 |
| 7 | **RaDe-GS: Rasterizing Depth in GS** | arXiv 2024 (2406.01467) | https://arxiv.org/pdf/2406.01467 | 光栅化计算准确 depth + surface normal map | 又一个 G-buffer 来源(depth-discontinuity 边)。非 NPR。 |
| 8 | **3DGS with Normal-Involved Rendering** | NeurIPS 2024 | https://proceedings.neurips.cc/paper_files/paper/2024/file/8bd4f1dbc7a70c6b80ce81b8b4fdc0b2-Paper-Conference.pdf | 把法线纳入 3DGS 渲染过程,改善几何感知 | 支撑精确逐像素 normal buffer(你 image-space 检测器的输入)。 |
| 9 | **Comprehensible Rendering of 3-D Shapes (G-buffer line drawing)** | SIGGRAPH 1990, Saito & Takahashi | https://www.cs.princeton.edu/courses/archive/fall00/cs597b/papers/saito90.pdf | image-space NPR 奠基:把 depth/normal 存进 G-buffer,2D 图像处理画 discontinuity/contour | **你 image-space 那半的直接祖先。** 必引。 |
| 10 | **Apparent Ridges for Line Drawing** | SIGGRAPH 2007, Judd et al. | https://people.csail.mit.edu/tjudd/apparentLines.pdf | 基于曲率的视角相关 object-space 特征线 | 经典 **object-space** 特征线谱系,用于框定你的 crease/silhouette 候选与 object/image 二分法。 |
| 11 | **Suggestive Contours for Conveying Shape** | SIGGRAPH 2003, DeCarlo et al. | ⚠ 未取到一手 URL,引用前请核实 | 超出真 silhouette 的视角相关 object-space contour | 核心 object-space NPR 基础。**注意:agent 未取到主页/DOI,投稿前核实。** |
| 12 | [WIP] NPR Shading in Houdini using Gaussian Splatting | Medium 博客,2026-06 | https://medium.com/@surya.dakshina/wip-npr-shading-in-houdini-using-gaussian-splatting-6b8d95ece5c1 | 非正式、未完成:场景烤成 splat,在 Houdini COP 里做 image-space 描边/排线/半调 | **精神上最接近你 image-space 那半**,但纯 image-space 后处理、无 object-space covariance 提取、无 3D/2D 融合、不谈时间稳定与实时、非同行评审。诚实起见列出,不威胁 novelty。 |

*风格化阵营(作为"非特征线 NPR"背景,而非直接竞争):StyleGaussian (https://arxiv.org/pdf/2403.07807)、G-Style (https://arxiv.org/abs/2408.15695)、StylizedGS (https://arxiv.org/pdf/2404.05220)、Gaussian Splatting in Style (https://arxiv.org/pdf/2403.08498)。它们做颜色/纹理风格迁移,不产矢量特征线。*

---

## 三、建议的对比 baseline 与你可主张的差异点

**Baselines(实验里要打的对照):**
1. **纯 image-space(在 3DGS G-buffer 上做线绘制)** —— 即你自己 image-space 那一级单独跑(Saito–Takahashi 式,在 DN-Splatter/RaDe-GS 的 depth+normal 上)。这是最直接的 ablation 与最强的 naive 对手,会暴露 object-space gating 所修复的时间闪烁。
2. **mesh-then-NPR(SuGaR / 2DGS 抽 mesh → 经典 object-space 线)** —— 先抽 mesh 再跑 suggestive contours / apparent ridges。"老办法"对照,用来衡量你 no-mesh、no-retrain 的代价优势与重建伪影。
3. **EdgeGaussians / LineGS 渲成线** —— 说明面向重建的边方法会漏掉视角相关的 silhouette/contour,且非为逐帧稳定 NPR 设计。

**你可正当主张为 novel 的点:**
- **首个把 object-space(从 3D Gaussian covariance 导出)与 image-space(G-buffer)特征线融合用于 3DGS**;各成分单独存在,但这种 **gating/稳定化融合**尚无人主张。
- **不重建 mesh、直接从 covariance 结构取特征线候选** —— EdgeGaussians/LineGS 用 covariance 朝向去**重建几何**;把它当作**渲染期 NPR 稳定器**(silhouette/crease/corner gate)是不同的贡献。
- **用 3D gating 2D 边来获得时间稳定** —— 直击纯 image-space NPR 的闪烁失效模式;所调研的工作均未针对 splat 的时间一致特征线。
- **不重训基础 3DGS 模型** —— 相对需要微调/优化 Gaussian 的风格化方法,这是部署/实用上的差异点。

---

## 四、风险与盲区(投稿前的尽职核查)

- **没有同行评审的直接撞车。** 唯一直接的 NPR+GS+描边产物是那篇 Houdini Medium 帖(纯 image-space、非正式、未完成)。思路上最近的是 EdgeGaussians(covariance→边),但问题不同(重建)。需留意把 EdgeGaussians/SketchSplat/LineGS 转向**渲染**的后续工作。
- **检索盲区(proposal 里要诚实写明):**(1) 未逐篇翻 **SIGGRAPH Asia 2025 / Pacific Graphics 2025 / Eurographics 2026 / NPAR・Expressive** 的完整 proceedings —— 该方向小众论文可能藏在那里;(2) arXiv 搜到若干 **2026 年**预印(2601.* / 2602.* / 2603.* 等),仅凭标题报告其存在,**内容未逐篇核实**;(3) **Suggestive Contours (DeCarlo 2003)** 未取到一手 URL,引用前核实;(4) 非英文 + 最近 ~8 周的工作覆盖最弱。
- **投稿前建议手动复查:**
  - NPAR / Expressive symposium 的相关 session
  - awesome-3D-gaussian-splatting 的 Stylization/NPR 段:https://github.com/MrNeRF/awesome-3D-gaussian-splatting
  - advances_3d_neural_stylization:https://github.com/chenyingshu/advances_3d_neural_stylization
  - 临投稿前重跑一次 arXiv cs.GR(2026-05~06)列表查询

**一句话总结:** 在"严谨但非穷尽"的检索下,你这个具体混合是**开放的**。三块积木(covariance 即边线索、GS 的 normal/G-buffer、经典 G-buffer/object-space 线绘制)都已存在、应作为基础引用;而**面向时间一致特征线 NPR、无 mesh、无重训的"组合 + 稳定化融合"**正是你可辩护的 novelty。
