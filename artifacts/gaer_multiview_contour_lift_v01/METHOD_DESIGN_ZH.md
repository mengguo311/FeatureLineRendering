# 多视角二维轮廓升维：事前方法设计

本轮主输入允许二维轮廓沿校准射线升维。旧禁止 lift 的约束不适用。只输出一次固定的1D中心图及细世界管线；不作椭球/体素并集，不 closing，不用物体剪影代替线。

已读真实历史 REPORT_ZH、RESEARCH_ZH、INPUT_FREEZE、PROTOCOL、cpu_native.py、fixed_contour_asset 的 README/run/core。上轮 NO_GO_CONTOUR_OVERFILL 不改写。上轮完整椭球的多方向并集会铺开为表面；前景 veto 无法阻止形体内部填黑。r_33 旧 lift 用 top32 αT×C_style 中心 z 均值并滤波，只保留外边界；单源回投影吻合是射线构造保证，并非表面深度正确。本轮重新生成同一 r_33 基线，三个臂共用条件 accepted αT 中位中心深度、线宽及实体 tube renderer；与旧 C_style 方法不混称同法。

CPU replica 的历史四缓存校准是近似而非 CUDA bit-exact。本轮复制源码到专用 stage，不导入旧 runtime，不修改共享 binary；保留完整 forward，再新增稀疏 all-accepted 查询。严格沿中心深度排序和原 α/T 截断规则，对每个有序边界采样像素保存所有 accepted kernel IDs/αT，条件权重累计达总质量一半的中心 z 为 depth_proxy。q10/q90 是贡献分布的离散宽度，不是可信的表面误差置信区间。绝不使用旧名为 median_depth 的绝对 T=.5 crossing 代替条件中位数。

alpha=.5 二值域采用 RETR_TREE 的有序边界；按 hierarchy 深度奇偶标记 outer/hole，外连负空间由原曲线形状保留。2px弧长采样，周长<16px的小环明确排除并统计；不提取 RGB 内部细节。每点保留相机、像素、中心 z proxy、源支撑、q10/q90、源闭环 ID。沿原链仅连接有限近邻，深度跳跃切开；不补桥、不MST。

跨视角候选先以世界近距和互为最近节点生成，要求反向等价的切线一致、共享 accepted ID 质量、双向 epipolar、射线夹角和正深度，以及三角点对两个源像素重投影/相对proxy位移均受限。还要求同一对源曲线至少3个局部顺序连续匹配；禁止仅因一对点靠近或共享核而强配。通过者仍称“多源同一性候选”，并非证实的物理棱边。rolling rim 通常无法通过这些条件，拒绝原因与未匹配源全部保存。

每个合并簇最多一个点/相机；逐次尝试加入来源后，以全簇射线最小二乘求中心，重新检查所有source重投影、位移和切线，避免A-B/B-C传递合并绕过A-C。不作全局位置优化或额外平滑。最终融合图仅保留两端皆有至少两个相机来源的原链短边；平行重复edge按节点簇去重并保存所有原edge来源，不新增跨链连接。未通过多源条件的曲线仍完整保存在 rawunion / 单source资产中，不冒称主线恢复完整。

三个固定臂：single=r_33；rawunion=全部24份经过同样局部跳变切分的源图原样并列；fused=上面的多源条件筛选、控制点融合及重复边消除。所有臂同一世界radius；单源/union区别衡量更多source，union/fused同时包含同一性筛选、位移与去重，不能作纯去重单因子归因。

世界尺度自动取所有construction相机焦长和有效proxy中位深度的中位 z/f，记wpp。只允许radius=[.75,1,1.25]×wpp，对应参考深度1.5/2/2.5px直径。DEV只按投影几何直径最接近2px且p95<=6px选择；不得按覆盖/效果加粗。选定后所有XYZ/topology/radius/path ID封印，reserved和arc才开封。实体三角管线只做资产自身zbuffer；相对原GS是完整xray，不使用未验证proxy深度消除后方杂线。

评价不使用GTmesh：800px全图、孤立stroke profile、投影几何直径尾部、墨迹距离变换尾部和大片交叉黑块、前景空白/孔洞与开放负空间、轮廓覆盖、短段和重复边。8reserved及33arc均来自历史曝光域，reserved仅本轮construction holdout；下半球及其他域未验证。视觉失败就给PARTIAL/NO_GO，固定资产工程通过不等于视觉GO。不宣称方法新颖性。
