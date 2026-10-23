# Unit010：局部方向框架

一次BUILD确定的部件切平面框架已完成实际对照，原Gaussian行、纸底许可和墨责任保持固定。方向编辑在完整物体上可见，配平后53.21%–56.47%的目标像素明显改变；三个DEV视角的墨覆盖下降，弱视角整体NPR质量优势未建立，不升级默认。

实际旧配置是XZ、35°/95°。四BUILD首交可见目标面去重后共2096面，按面积法向外积确定宏观法向，按三角形面积位置矩确定面内长轴。固定符号规则、世界原点和切片相位；旧2030面与新增91面分别生成。新380条/1946段，旧375条/2004段。旧分支逐值恢复。宏观平面与XZ相差约13.32°，基底符号还改变方向方位；不能把所有可见差异归因于退化减少，也没有证明优于同等手工旋转。

`hatching.py`新增可选正交`cutting_basis`，缺省行为不变。`local_frame.py`负责框架与分区生成，`run_frame_unit.py`负责冻结/BUILD/DEV，`audit_frame_unit.py`提供原ID trace读回及真实完整GS冷重放。两项针对性测试通过；13条DEV/arc记录核验，冷重放实际完整GS三次与两套代理路径一致，零墨及全零许可控制正确。九帧FFV1全部解码一致。极小非零远区变化保留；旧纸底损伤没有消失。

科学输出根目录：`/mnt/hdd1/u00134/partwise_sketch_hatching_gaussian_link_v06/units/unit_010`。

- [完整报告](/mnt/hdd1/u00134/partwise_sketch_hatching_gaussian_link_v06/units/unit_010/REPORT_ZH.md)
- [同墨预算整物体对照](/mnt/hdd1/u00134/partwise_sketch_hatching_gaussian_link_v06/units/unit_010/ALL_DEV_MATCHED.png)
- [独立墨层](/mnt/hdd1/u00134/partwise_sketch_hatching_gaussian_link_v06/units/unit_010/ALL_DEV_INK.png)
- [冷重放说明](/mnt/hdd1/u00134/partwise_sketch_hatching_gaussian_link_v06/units/unit_010/README_ZH.md)

冻结协议SHA256：`045f90746d897949028f9ee3f07c5f55d211d4a476a643a8908385ac9840d16b`。旧unit001–009和v05全部负结果保留。本轮交付脚本一次缺少导入导致rc1，原源码/部分交付归档，单独修复后handoff_002 rc0；冻结科学源码和结果没有修改。

这是原GS纸底与原ID关联代理墨层，不是原生Gaussian排线、独立物理/语义归属或H1/H2/H3证明。原PLY、本地Python及历史锁定缓存仍是外部依赖。NEXT停止原因仅为完成时已过21:20禁启新单元，不是宣称所有路线耗尽。
