# Unit002：固定生成器的载体对照

一次有界载体降噪真实改变了441个顶点和1349个目标面；同切片生成器、固定原遮挡参考与原GS纸底/S下，完整物体可读性优势未建立。保留原默认、全部负结果和工程失败。下一候选是原载体上的全局相干方向场，须另经只读审查与父级冻结。

- [完整实验报告](/mnt/hdd1/u00134/partwise_sketch_hatching_gaussian_link_v07/units/unit_002/REPORT_ZH.md)
- [完整DEV对照](/mnt/hdd1/u00134/partwise_sketch_hatching_gaussian_link_v07/units/unit_002/ALL_DEV_MATCHED.png)
- [状态与实际命令](/mnt/hdd1/u00134/partwise_sketch_hatching_gaussian_link_v07/units/unit_002/STATUS.json)

代码入口：`experiments/partwise_sketch_hatching_v07/carrier_unit/run_carrier.py`。协议冻结后不重跑已有输出阶段；原日志和结果不可覆盖。`replay_carrier.py --out <unit002下不存在的新目录>`可重栅格化保存路径，并校验与原结果逐值一致。它依赖冻结的旧GS缓存，不是再次冷渲染GS。

载体与遮挡参考是不同参数。原始Gaussian几何/行身份、目标、M1/UNKNOWN、纸底及S不变；新路径仅有代理face/bary身份，不构成逐路径Gaussian归属证明。输出是CPU EWA原GS纸底与区域关联代理墨，不是原生Gaussian排线。
