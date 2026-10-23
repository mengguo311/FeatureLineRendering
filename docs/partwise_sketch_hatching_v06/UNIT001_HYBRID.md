# 区域级原核关联纸底与代理排线

本单元把冻结的 unit005 原始 Gaussian 区域权重接入实际纸底和墨层。输入是完整原始 PLY 行号、保存的作者区域4、固定三维笔触及原来的相机。目标是 Chair 人工座面 patch 和 Lego 人工铲斗表面；不是完整语义部件，也不是旧稀疏路径 capsule 任务。

对已支持且非 UNKNOWN 的区域4原核，`s_i=q_i(4)`。完整 SH3 求值后，将颜色混合到固定 `(0.95,0.95,0.95)` 纸底。原始几何、协方差、opacity、SH 文件与行顺序不变。真实接受贡献处累计 `S(p)=sum(alpha*T*s)`；代理网格只承载固定三维排线，生成独立墨层 `H4`。主结果墨层为 `H4*S`。

主比较仅改变墨层是否乘 `S`。未门控的固定强度结果和在四个 BUILD 相机上按实际可见 RGB 墨量配平的结果均保存。最近代理面基线匹配源纸底变化；曝光分箱打乱原 ID 是单独的负控制。八个评估相机来自 unit005，全部明确标为已曝光 DEV。

输出根：`/mnt/hdd1/u00134/partwise_sketch_hatching_gaussian_link_v06/units/unit_001`。实验源码冻结在该目录的 `source_snapshot`，实际结果、图像、墨层和源层数组在 `results/<scene>/<view>`。每个阶段保留独立 stdout、退出码及时间回执。原始失败和 parent-owned DECISION 不改写。

这是 original-GS source editing + proxy-anchored ink 的混合资产，不是原生 Gaussian 排线。CPU 内部贡献重建不等同于原生 CUDA 校准；作者代理意图不提供独立语义或物理表面真值。最终结论以单元内 `REPORT_ZH.md`、`VALIDATION.json` 和整物体图为准。
