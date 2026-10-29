# v04 单次渐进载体试验：PARTIAL

**已交付 scan24 的完整 L0 强基线与 L1 重叠池化；没有交付完成的几何增长层。** ficus、scan65 因 building 未完成五层而未运行。

| 层级 | 核数 | 已分配 | UNKNOWN | 主组 | 跨 parent 组 |
|---|---:|---:|---:|---:|---:|
| L0 | 458490 | 210278 | 248212 | 6187 | 396 |
| L1 | 458490 | 220726 | 237764 | 6106 | 2803 |

L1 新分配 10,448 个原 UNKNOWN 核，共接受 4,527 次包含式池化。独立冷读与完整合并 DAG 核验确认，每个 L1 载体逐点等于某个前驱宿主载体：这不是几何延伸。跨 parent 组数增加不能证明获得更长真实边；每组 parent 核数和去重支持长度见 GROUPS.json。

L0 有 5,995 个旧组通过新载体验证；192 个旧组因转角或切向不合格保留原身份、冻结增长。所有原 UNKNOWN seedlet 重新进入候选资格，旧歧义不作为永久排除条件；无效源切向仍保留明确 UNKNOWN。

L1 达到每层 30,000 次整组验证上限。记录 3,918 次平行拒绝、2 次分支拒绝、856 次歧义和 37,099 次 fit_cap；第二遍池化没有接受新合并。候选截断及近邻饱和均有统计，不能声称穷尽所有可合并支持。

原监督进程以 143 退出；L1 完整检查点存在，但子进程实际退出码丢失，严格记为 UNKNOWN。唯一一次工程恢复保留原源码、配置与检查点，批量化相同候选去重和投影评分，使用脱离交互连接的监督进程；未改科学参数。恢复后 L2 日志记录 14,602 次内存合并，但在池化结束、导出与封存前耗尽 scan24 的 600 秒计算预算，被监督进程终止，实际退出码 -15。它没有有效 MEMBERSHIP 或图像，不能把这些内存合并计作交付或成功。

原核总数、行序、位置、协方差、宽度、旋转、尺度、不透明度与所有非颜色字段通过冷载逐字节核验；图像只渲染真实原核。原 v03 封存文件、继承文件和旧工作树状态经独立只读检查。源 RGB 高斯未打开。

本次未证明五级渐进长边目标，也未证明真实直线与曲线的跨碎片延伸。所有身份仍是暂定几何假设；没有独立物理真值、间隙内部证据或留出泛化结论。三层增长及两份后续完整资产明确未完成，不自动开第二个科学单元。

[全量两层两视图](/mnt/hdd1/u00134/radegs_paper_reproduction_v01/line_kernel_edge_growth_v04/units/unit_001/delivery/SCAN24_COMPLETE_LEVELS.png) · [L0 隔离放大](/mnt/hdd1/u00134/radegs_paper_reproduction_v01/line_kernel_edge_growth_v04/units/unit_001/delivery/L0_CROSS_PARENT_CROPS.png) · [L1 隔离放大](/mnt/hdd1/u00134/radegs_paper_reproduction_v01/line_kernel_edge_growth_v04/units/unit_001/delivery/L1_CROSS_PARENT_CROPS.png) · [相同核集合的池化前后](/mnt/hdd1/u00134/radegs_paper_reproduction_v01/line_kernel_edge_growth_v04/units/unit_001/delivery/POOLING_LINEAGE.png) · [真实负例上下文](/mnt/hdd1/u00134/radegs_paper_reproduction_v01/line_kernel_edge_growth_v04/units/unit_001/delivery/NEGATIVE_CASES_CROPS.png)

放大图仅裁剪并最近邻放大已保存的原生 Gaussian 图像；完整原生固定相机图像仍保留。颜色变化表示身份变化，不表示几何改变。支持长度使用原 seedlet 有限端点投影区间的并集；间隙不计作支持，不能使用旧 seedlet 长度总和冒充去重边长。


人工图像复核：最大三组分别为 639+3、555+4、402+4 个旧 parent 核，仍由单个旧 parent 主导，不能称为跨实质碎片的大边。真实负例图的投影很小，且展示的是前级来源上下文，不一定覆盖当遍累计候选的全部支持；因此没有据此宣布分支或深度正确性。五项小型回归测试通过，真实 RED 检查实际退出 1、GREEN 实际退出 0。最终报告处理子进程实际退出 0；首个报告处理会话的 143 和部分图像也保留。

完整资产目录：/mnt/hdd1/u00134/radegs_paper_reproduction_v01/line_kernel_edge_growth_v04/units/unit_001
