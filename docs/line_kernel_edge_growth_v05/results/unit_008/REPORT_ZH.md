**unit_008：完整 ficus M4 已交付，科学结论 PARTIAL。**

Parent 实际数值子进程 returncode=0、reason=null，时间为 2026-10-31 08:10:03.924141—08:12:52.562560 JST；runner 自报耗时 168.052 秒。权威记录为 [COMPUTE_EXIT](../../orchestration/unit_008/COMPUTE_EXIT.json)。没有用 launcher 返回或内存进度替代结果。M3_RESTORE_VERIFIED、M4_STATE、M4_NATIVE、M4_DIAGNOSTICS 全部保存，请求的计算阶段无缺失。分析阶段没有拟合、渲染、重跑、参数或源码修改。

285956 行 M4 已从磁盘读取并检查：118428 行已分配，167528 行 UNKNOWN，3458 个主组，覆盖率 41.4148%。相对 M3 新增分配 5895 行，前驱所有已分配行仍保留分配。实际原始 Gaussian 全景为 [test_r_1](scenes/ficus/stages/M4_MERGE_ONLY/test_r_1_FULL.png) 与 [test_r_79](scenes/ficus/stages/M4_MERGE_ONLY/test_r_79_FULL.png)。原始核几何、宽度和 opacity 固定；辅助载体不是渲染几何，没有补画间隙。

| 已保存层级 | 已分配核 | UNKNOWN | 主组数 |
|---|---:|---:|---:|
| unit002 L0，强 v03 等价映射 | 95951 | 190005 | 3318 |
| unit002 L1，固定范围池化 | 106399 | 179557 | 3289 |
| unit002 M2 | 109052 | 176904 | 3243 |
| unit005 M3 | 112533 | 173423 | 3281 |
| unit008 M4 | 118428 | 167528 | 3458 |

本轮只有一次拓扑合并，无初始化或池化。1343 个接受事件不等于 1343 个有意义的大边；新激活 UNKNOWN 会增加主组数。19949 次 fit 未触及 30000 上限，候选截断 35383、查询饱和 33345 仍存在。记录包含 endpoint_gap 40640、connector 22362、residual 13730、endpoint_tangent 10345、parallel 1534、branch 22、ambiguous 1550；这些是原算法的逐项计数，不能据此推断放宽某条守卫必然有效。累计轮数与总拟合机会同时增加，不能把两者效果分离。

**6 组通过冻结增长公式：1 个 line、5 个 polyline。** 全部域外支持至少 4p，其中 5 组有两个实质原 parent。没有本轮增长组达到三个实质 L1 片段；三 L1 与两原 parent 的交集也为零。数值五组门槛通过，逐级更深组合未在本轮出现。p=0.003530473547030632 为冻结场景尺度；不同贡献的支持可重叠，不能直接求和。

| 组 | M3 核数组合 | M4 支持并集 | 增量 | 域外支持 | 最长连续段 | 总/最大间隙 |
|---|---|---:|---:|---:|---:|---:|
| 29734，polyline | 85+24=109 | 21.9766p | 5.1892p | 5.1960p | 3.0047p | 4.9935/0.8476p |
| 229534，polyline | 35+38=73 | 16.1376p | 7.8879p | 7.8889p | 2.0730p | 5.4530/1.0413p |
| 26432，polyline | 59+24=83 | 13.6925p | 4.8761p | 4.8884p | 4.1659p | 3.0154/1.4515p |
| 80817，line | 36+24=60 | 13.2486p | 4.6090p | 4.6350p | 1.9580p | 3.3015/1.2571p |
| 171204，polyline | 24+20=44 | 10.2422p | 5.0032p | 5.0068p | 2.7691p | 4.6385/1.3096p |
| 50883，polyline | 22+23=45 | 8.8731p | 4.2504p | 4.2548p | 1.9467p | 4.9290/1.3238p |

29734 在两视图中可见曲线的端部续接，M3 两种成员色对应的片段在 M4 统一；其有限载体长 27.0387p，原 parent 的实质贡献为 63、21、22 核，另有 3 核小贡献。已查看 [M3/test_r_1](scenes/ficus/stages/M4_MERGE_ONLY/diagnostics/CROP_29734_test_r_1_GROUP_29734_M3_test_r_1.png)、[M4/test_r_1](scenes/ficus/stages/M4_MERGE_ONLY/diagnostics/CROP_29734_test_r_1_GROUP_29734_M4_test_r_1.png)、[M3/test_r_79](scenes/ficus/stages/M4_MERGE_ONLY/diagnostics/CROP_29734_test_r_79_GROUP_29734_M3_test_r_79.png)、[M4/test_r_79](scenes/ficus/stages/M4_MERGE_ONLY/diagnostics/CROP_29734_test_r_79_GROUP_29734_M4_test_r_79.png)以及 [parent 色](scenes/ficus/stages/M4_MERGE_ONLY/diagnostics/CROP_29734_test_r_79_GROUP_29734_PARENTS_test_r_79.png)。这是可见的暂定曲线组合，不是连续物理边的真值。

80817 的两视图显示近直线支持组合：[test_r_1](scenes/ficus/stages/M4_MERGE_ONLY/diagnostics/CROP_80817_test_r_1_GROUP_80817_M4_test_r_1.png)、[test_r_79](scenes/ficus/stages/M4_MERGE_ONLY/diagnostics/CROP_80817_test_r_79_GROUP_80817_M4_test_r_79.png)。其有限载体长 16.5501p，实质原 parent 为 46 核/12.6624p 和 10 核/2.2553p，另有 4 核。原生像素尺度不足以判断细微曲率和深度关系。229534 的浅曲线组合也可见；26432 虽标为 polyline，投影接近直线，且最大间隙 1.4515p 必须保留。171204 的 40/44 核来自同一原 parent，不作为强跨-parent 证据。50883 未进入冻结选图集合，本次仅报告其已保存数值，不补渲染、不作视觉结论。

跟踪曲线 79171（104 核）与 204470（77 核）完全没有本轮支持增量或域外增长。79171 仍有三实质 L1 片段，但这是继承结果。其保存候选拒绝为 connector/parallel/residual/endpoint_gap 各 2；204470 为 connector 3、residual 3、parallel 1、endpoint_gap 1。因此当前停滞不能归因于耗尽 fit 上限。57769 仅加 3 核，支持增加 0.2327p、域外为零，且 150/163 核来自单个原 parent。大组 21870 加 4 核、支持增加 0.3717p、域外零；21927 与 20007 不变。内部补洞和继承大组没有被计作本轮实质延伸。

共保存 312 张 PNG，本次通过 image tool 直接查看 60 张：两张全景、全部 11 个固定选中组的 M4 双视图、五个选中增长组的 M3/M4/parent 双视图、六类精确版本负例双视图及两组全景 highlight。清单和判断见 [VISUAL_REVIEW](VISUAL_REVIEW.json)。未声称看过全部图片，也没有使用拟合线替代核图。相机 test_r_1/test_r_79、白背景 floor=0.0144、原 covariance/width/opacity、既定 4 倍最近邻裁剪均固定。

六类负例均有可见像素，但 gap、ambiguity 和最差接受例仅有很少原生像素，parallel/branch/depth 分离仍不可确证。最差接受对 193505/193519 的最大支持间隙为 1.4997037p，接近 1.5p 边界；拒绝 gap 对为 230419/253129，parallel 对为 3377/3382，branch 对为 14386/14392。所看图片没有确证误吞独立结构，但也不足以给出物理安全通过。因此保留 PARTIAL：有真实新增曲线与近直线组合，仍缺本轮更深的三片段增长和可辨的负例物理验证。

[ANALYSIS_AUDIT](ANALYSIS_AUDIT.json) 验证了 36 个 parent 源码快照、42 个冻结输入、37 个 helper 引用（四个获准外部 helper）及五个完整检查点。磁盘读回的映射行顺序、载体归属、前驱分配保留和各层贡献核数一致。原 means、covariance、opacity、primitive_id、internal_piece_id、arc_t 的 dtype、shape、字节哈希全部相等。所有物理身份仍为暂定，原 parent 只作溯源；无独立真值、held-out 泛化或间隙连续性结论。

配置 SHA256：`6d4cd08c821e15d3eb2bb42d7017375611662a2a942c48e8c5a61e27e2426052`。决策 SHA256：`3bf26559f71e241b04c316fedadf35358371ba6fbdc58273dd226d4fd70f292c`。可复现源码依据 [PARENT_RUN_FROZEN](PARENT_RUN_FROZEN.json) 的不可变 source_snapshot 映射，不依赖未来工作树 HEAD。[RUN_REQUEST](RUN_REQUEST.json) 和 [INTERFACE_VALIDATION](INTERFACE_VALIDATION.json) 保存准确脚本、配置路径、全部哈希与批准 Python 的完整参数；入口为 `python -B continuation_level.py --config CONFIG.json`。BUILD 的 9 项预检查和 11 项最终回归实际退出均为 0；生产代码未改，无新 RED 宣称，测试不代替科学结果。

本单元初始化、池化、M5、scan24 重跑及 scan65 M4 均 NOT_RUN。其他场景已有层级仍引用原封存单元；旧 v04 的 PARTIAL 与历史缺失退出不被覆盖。

建议下一独立单元完成 **scan65 封存 M3 → 同设置一轮 M4**，仅改变场景，跟踪 56133（直线）、64877（曲线）和 167509（多 L1、单实质原 parent 对照）。先补齐三场景第三轮比较，再由拒绝和可见性证据决定机制改动；不直接给 ficus 追加时间、轮次或放宽守卫。输入哈希、1800 秒预算、固定阶段与否证条件见 [NEXT.json](NEXT.json)。本交接没有启动下一单元。

