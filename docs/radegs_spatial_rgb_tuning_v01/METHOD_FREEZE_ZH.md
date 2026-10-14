# Spatial RGB 检线预设冻结

这轮只处理 RGB 检线，不创建或修改 3D。参数冻结于查看新 EVAL 结果之前；3 个先行参考是 scan24/0000、scan65/0000、Ficus/train_r_80，随后不改参数应用其余 8 张 DTU 图。EVAL 均已在历史研究看过，不是盲测。

16 预设 × 11 张原生图。A10/A15/A20/A30/A40/A50 只改变严格 darkness>T 的候选门槛，A20 为现有 05 候选基线。B75/B50/B25/B00 使用 max(structural,lambda*detail)，T=.2；A20 是 lambda=1 对照。M75T30/M50T30 同时改混合与门槛，不能归因为单一因素。C1 的尺度为 [1,2,4]，C2 为 [1.4,2.8,5.6]，U20 使用完整 union，L50 使用 lambda=.5，两者 T=.2。这是算法尺度变化，不称为 DEFAULT。

所有图 gain=1、ink_sigma=.5，不做自适应对比度。soft=max(S,lambda D)，darkness=1-ink(soft)[...,0]，marked=darkness>T，skeleton=skeletonize(marked)。候选展示为 1-darkness*marked，不再做第二次模糊；另存二值 marked 和 skeleton，避免把淡化误称拓扑改变。保存未截断 soft 和 darkness，后续用户可重选，但本轮不改 05。

DEFAULT 原始分析器字节不变。weak/strong 只影响 structural 的连通滞后门槛；detail 可绕过 profile 拒绝。本轮不换 Canny、不用语义/深度/alpha、没有 ROI 保留掩码，没有形态闭合。RGB 保持输入 float32，包括渲染值大于1的部分；仅 RGB 显示裁剪到屏幕范围。

判断优先看屋脊/窗框、头骨外轮廓/鼻腔/牙齿/下颌、叶片/叶柄/枝条/花盆。强纹理不等于无用，弱线也不等于噪声。强门槛、纯结构、粗尺度均可能丢主体细节，负例完整交付。没有 GT，候选像素、骨架像素、8邻域分量/端点/结点只是诊断，不是真实信噪比，也不据此选最优。

测试先 RED 后 GREEN：原 union 和 lambda=1 位级相同，lambda=0 等于结构分支；门槛严格且嵌套；RGB-only 接口；有限范围；常量背景与弱真边/纹理合成控制；同图复算与原文件哈希不变。合成图只能证明机制，不能证明真实图中的纹理类别。
