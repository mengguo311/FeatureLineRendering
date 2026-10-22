# Unit004：固定原核控制的新仰角迁移

本单元以 `partial / UNCERTIFIED_CPU_MAPPING` 交付。冻结原始ID、权重、同一作者路径与BUILD实际RGB预算，在Chair/Lego的新低／高仰角执行完整源GS改色与opacity诊断；同时保存软区域证据与整核弃权感知的UNKNOWN投影。结论需同时查看局部性、可评分范围和路径覆盖，不能从上轮6/6直接推断新视角全通过。

- [中文实证报告](/mnt/hdd1/u00134/partwise_sketch_hatching_gaussian_link_v05/units/unit_004/REPORT_ZH.md)
- [机器状态](/mnt/hdd1/u00134/partwise_sketch_hatching_gaussian_link_v05/units/unit_004/STATUS.json)
- [冻结协议](/mnt/hdd1/u00134/partwise_sketch_hatching_gaussian_link_v05/units/unit_004/PROTOCOL.json)
- [源模型重放与路径查询](/mnt/hdd1/u00134/partwise_sketch_hatching_gaussian_link_v05/units/unit_004/REPRODUCE_ZH.md)
- [下一步](/mnt/hdd1/u00134/partwise_sketch_hatching_gaussian_link_v05/units/unit_004/NEXT.json)

核心实现：`run_transfer_unit.py`、`transfer_audit.py`。`validate_transfer_unit.py`从落盘的原ID责任、全部锚点CSR、RGB数组独立复核；`run_transfer.sh`提供可复放入口。完整路径集合仍是代理固定3D排线，本单元增加其原始GS支持与控制证据，不是原生Gaussian排线或物理附着认证。过去所有失败和已封存单元保持只读。
