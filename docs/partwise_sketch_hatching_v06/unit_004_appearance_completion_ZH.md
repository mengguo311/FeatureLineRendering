# Unit004：原核纸底外观许可补全

2026-10-23，同会话Astra只读决策后执行。冻结协议SHA256为`d5508044588ba7780acf553093b8aac0f5773b11b20e68637195571a056fb2f6`。

在12个既有BUILD上累计完整原GS逐核alpha×T footprint，只为通过区域投影局部性门槛的UNKNOWN原核添加独立外观许可。新增19352核，总计39474个可编辑原核；195600个UNKNOWN标签保持不变。旧20122核权重、原PLY/SH/几何/opacity/行序、代理路径与旧墨alpha/S均不变。

四个DEV视角的自然强度内部纸底残留下降45.14%–61.50%，完整物体图可见部分斑驳减少；源编辑量也更大。四个原BUILD实际源RGB配平后，四个DEV内部残留均未改善，退化0.59%–20.94%。自然强度远区绝对损伤全部略增，不能把多数远区比例下降写成局部性提高。仍有黄灰残留与断续交叉墨线，故不升级默认，不宣称原生Gaussian排线或语义归属。

三项针对性TDD通过；独立核验12份完整footprint、完整原ID和未变M1，并在所有目标像素与固定7px背景网格上的原ID trace重建原RGB、四种纸底及支持。弱角度5次完整GS冷重放逐数组一致；九帧真实相机短弧全帧解码一致。一次外层143/子退出UNKNOWN的空中断保留，缺失帧以新回执完成；全部最终阶段有实际rc0。

- [完整报告](/mnt/hdd1/u00134/partwise_sketch_hatching_gaussian_link_v06/units/unit_004/REPORT_ZH.md)
- [全部自然强度视图](/mnt/hdd1/u00134/partwise_sketch_hatching_gaussian_link_v06/units/unit_004/ALL_DEV_VIEWS.png)
- [全部配平视图](/mnt/hdd1/u00134/partwise_sketch_hatching_gaussian_link_v06/units/unit_004/ALL_DEV_MATCHED.png)
- [冷重放CLI与依赖](/mnt/hdd1/u00134/partwise_sketch_hatching_gaussian_link_v06/units/unit_004/README_ZH.md)
- [NEXT](/mnt/hdd1/u00134/partwise_sketch_hatching_gaussian_link_v06/units/unit_004/NEXT.json)

执行入口为`run_completion_unit.py`，全像素累积器和选核在`appearance_completion.py`，独立读回及冷重放入口为`audit_completion_unit.py`。C++累积器逐字来自v05 unit005只读快照；原来源路径和哈希保存在冻结协议中。实验、审计及媒体源码在评估前冻结于unit004/source_snapshot；结果报告生成器另有handoff_source与哈希记录。

NEXT建议固定本轮自然强度纸底，单独测试计划弧长间隙0.035→0，并按BUILD实际可见墨量配平。不得连接不同代理链或跨越真实边界；新路径是显式风格变体，不能称旧路径bug修复。旧v05稀疏失败和unit001—003负结果保持。
