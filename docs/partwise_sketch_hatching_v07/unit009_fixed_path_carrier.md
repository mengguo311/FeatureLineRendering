# Unit009：固定路径的载体迁移

已完成 Lego A/T 实际比较：A 保留 unit008 的原 H；T 用 unit002 已保存的降噪载体重建相同 face/bary 路径。380 条路径及 2330 段全部保留，234 条位置改变；没有重新降噪、求场、行走、删线或修复继承失败。

结果为负，不升级默认。主分区跨面转角中位数由 14.654° 降至 12.668°，完整前后视图未建立可读性优势。弱后侧配平 linked 支持长度由 665.518 降至 656.893 px；同材料样本、同 A 权重诊断仍显示原代理参照下可见性下降。该有限扰动不能排除所有载体噪声或生成器机制。

完整报告与证据位于：

- [中文报告](/mnt/hdd1/u00134/partwise_sketch_hatching_gaussian_link_v07/units/unit_009/REPORT_ZH.md)
- [完整 DEV 对照](/mnt/hdd1/u00134/partwise_sketch_hatching_gaussian_link_v07/units/unit_009/ALL_DEV_MATCHED.png)
- [同材料可见性诊断](/mnt/hdd1/u00134/partwise_sketch_hatching_gaussian_link_v07/units/unit_009/MATERIAL_VISIBILITY.json)
- [状态及执行回执](/mnt/hdd1/u00134/partwise_sketch_hatching_gaussian_link_v07/units/unit_009/STATUS.json)

针对性 TDD 为预期 RED 后三组 GREEN；独立审计通过，新进程实际重画墨层并逐值恢复。source/paper/S 使用已验证缓存；unit001 冷 hybrid 重放未重复。这里仍是原 GS 纸底与原 ID 区域 S 门控的代理墨，不是原生 Gaussian 排线或逐路径原核归属认证。全部旧负结果及 H 的 zero_step_cycle 保留。

复放入口为 `experiments/partwise_sketch_hatching_v07/embedding_unit/replay_embedding.py`，要求 `--out` 为 unit009 内不存在的新目录。确切解释器、命令和依赖见中文报告。运行固定 CPU 两核亲和、数值线程 1、CUDA 为空。

NEXT=continue：下一次父级只读审查与冻结后，可验证 Chair 座面标准间距编辑及有界新路径原 ID 支持。必须单独控制继承 visibility_mask=20 与新生成 owner-only=16 的差异，不把掩码变化算作间距效果。
