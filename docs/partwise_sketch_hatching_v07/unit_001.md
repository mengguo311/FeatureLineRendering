# Unit001：固定载体上的切片与表面行走

完成一次Lego完整冷重放，并比较同一载体上的平面切片路径A与共享边展开续接B。380条笔触继承旧弧长中点、初始切向和长度预算；B有新身份与face/bary锚点。固定原GS、纸底、区域S、作者目标、渲染器及相机。B的跨面转折有所减少，但完整物体可读性优势未建立，不升级默认。

- [中文实验报告](/mnt/hdd1/u00134/partwise_sketch_hatching_gaussian_link_v07/units/unit_001/REPORT_ZH.md)
- [完整物体配平四视角](/mnt/hdd1/u00134/partwise_sketch_hatching_gaussian_link_v07/units/unit_001/ALL_DEV_MATCHED.png)
- [自然强度四视角](/mnt/hdd1/u00134/partwise_sketch_hatching_gaussian_link_v07/units/unit_001/ALL_DEV_NATURAL.png)
- [真实后侧相机序列](/mnt/hdd1/u00134/partwise_sketch_hatching_gaussian_link_v07/units/unit_001/REAR_CAMERA_SEQUENCE.png)
- [协议与原始结果](/mnt/hdd1/u00134/partwise_sketch_hatching_gaussian_link_v07/units/unit_001/PROTOCOL.json)
- [独立读回](/mnt/hdd1/u00134/partwise_sketch_hatching_gaussian_link_v07/units/unit_001/AUDIT.json)

代码在 `experiments/partwise_sketch_hatching_v07/`。`run_unit.py`分阶段冻结、生成、BUILD配平、评估和归因；`test_surface_walk.py`含5项针对性测试。预期缺模块RED与后续GREEN均保存。科学源码在评估前复制到单元source_snapshot；后加审计/交付脚本单独登记。

`replay_walk.py --out <新的v07输出目录>`重新栅格化保存的A/B路径，但复用经哈希校验的GS层。完整冷GS入口另在HDD的 `replay_package/code/linked_source_cli.py`，其hybrid为原A。需要已有Python/NumPy/SciPy/plyfile/Pillow/Open3D及冷重放用C++编译器；没有安装或修改旧环境。

本单元只验证本机Linux CPU。source_index保持原PLY行号；最新B仍是区域S关联代理墨，没有逐路径原Gaussian支持认证。所有视角已曝光，三相机序列不证明无闪烁。NEXT保留独立A/C载体诊断路线，不重做bootstrap或角度/纸底扫描。
