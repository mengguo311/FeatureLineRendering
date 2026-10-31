**unit_007：scan24 第三轮拓扑增长已交付；科学结论 PARTIAL。**

Parent 的实际数值子进程退出码为 **0**、reason 为 null，运行时间为 2026-10-31 07:52:00.769141—07:55:39.489795 JST；runner 自报耗时 218.085 秒。权威记录是 [COMPUTE_EXIT](../../orchestration/unit_007/COMPUTE_EXIT.json)，没有用 launcher 状态代替。已保存 M3_RESTORE_VERIFIED、M4_STATE、M4_NATIVE 和 M4_DIAGNOSTICS；本单元请求的计算阶段无缺失。分析阶段没有拟合、渲染、重跑、参数或源码修改。

M4 已从磁盘读取并检查全部 **458490 行**：245985 行分配到 6020 个主组，212505 行保持 UNKNOWN，覆盖率 53.6511%。相对 M3 新增分配 13461 行，所有前驱已分配行仍保留分配。载体成员、主映射及各层贡献核数一致；所有组身份暂定。两张实际原始 Gaussian 全景为 [0012](scenes/scan24/stages/M4_MERGE_ONLY/0012_FULL.png) 与 [0036](scenes/scan24/stages/M4_MERGE_ONLY/0036_FULL.png)。没有添加拟合线、桥接间隙或 RGB source GS。

| 已保存层级 | 已分配核 | UNKNOWN | 主组数 |
|---|---:|---:|---:|
| 强 v03 L0 | 210278 | 248212 | 6187 |
| v04 L1，仅固定宿主范围池化 | 220726 | 237764 | 6106 |
| unit001 M2 | 224948 | 233542 | 5884 |
| unit004 M3 | 232524 | 225966 | 5823 |
| unit007 M4 | 245985 | 212505 | 6020 |

M4 只增加一轮拓扑合并，没有池化。4180 个接受事件不等于 4180 个有意义的大边；新激活的 UNKNOWN 组也会增加主组数。本轮使用满 30000 次 fit，记录 fit_cap 3767、candidate_cap 76968、sample_query_saturated 102287，不能声称穷尽搜索。候选顺序、守卫和模型设置未改；累计轮数与总拟合机会同时增加，不是两者的独立因果对照。

冻结增长门槛通过 **28 组**，其中 line 15、polyline 13。19 组有至少两个实质原 parent；6 组有至少三个实质 L1 片段；两者交集为 5 组。25 组域外支持至少 4p，16 组同时有两个实质原 parent；同时满足三 L1、两原 parent、域外至少 4p 的为 4 组。这里 p=0.0014320037356621643，是保存的场景尺度。贡献长度会重叠，不能相加代替区间并集。

| 组 | M3 成员组合 | M4 支持并集 | 相对最大 M3 增量 | 域外支持 | 最长连续支持 | 总/最大间隙 |
|---|---|---:|---:|---:|---:|---:|
| 157014，polyline | 136+84=220 核 | 30.8398p | 7.9291p | 7.0848p | 14.7295p | 5.4144/0.3320p |
| 25859，line | 80+44=124 核 | 26.2970p | 9.5787p | 9.5864p | 2.6747p | 11.6445/1.3373p |
| 36554，polyline | 71+36=107 核 | 25.7992p | 7.9346p | 7.8603p | 2.6117p | 8.6103/1.1217p |
| 34132，polyline | 58+37=95 核 | 24.4125p | 9.8665p | 9.8728p | 1.9282p | 8.0340/0.7251p |
| 69200，line | 73+27=100 核 | 24.1836p | 6.4253p | 6.4284p | 1.1833p | 10.7489/1.3835p |

157014 的有限载体长度为 36.2577p，三实质 L1 片段贡献 97/84/39 核，三实质原 parent 贡献 94/81/42 核，另有 3 核小贡献。它提供了跨旧片段逐步组合的实际例子；然而两张图片都近似直线，polyline 标签本身不能证明新增曲线续接。其 [0012 M3](scenes/scan24/stages/M4_MERGE_ONLY/diagnostics/CROP_157014_0012_GROUP_157014_M3_0012.png)、[0012 M4](scenes/scan24/stages/M4_MERGE_ONLY/diagnostics/CROP_157014_0012_GROUP_157014_M4_0012.png)、[0036 M3](scenes/scan24/stages/M4_MERGE_ONLY/diagnostics/CROP_157014_0036_GROUP_157014_M3_0036.png)、[0036 M4](scenes/scan24/stages/M4_MERGE_ONLY/diagnostics/CROP_157014_0036_GROUP_157014_M4_0036.png)和 [parent 贡献色](scenes/scan24/stages/M4_MERGE_ONLY/diagnostics/CROP_157014_0036_GROUP_157014_PARENTS_0036.png)均已直接查看。

25859 的两视图显示近直线的端部支持续接：[0012](scenes/scan24/stages/M4_MERGE_ONLY/diagnostics/CROP_25859_0012_GROUP_25859_M4_0012.png)、[0036](scenes/scan24/stages/M4_MERGE_ONLY/diagnostics/CROP_25859_0036_GROUP_25859_M4_0036.png)。其有限载体长 37.9416p，支持间隙仍多，不能把载体全长视作连续观测。34132 在 0012 有弯折、0036 近直线，且 91/95 核来自同一原 parent，不能用三个 L1 片段冒充三个实质原 parent。36554 的轻微形状变化也不足以通过严格的双视图新增曲线要求。

最大组 308174（741 核）、14128（646 核）、18608（406 核）本轮增量与域外支持都为零，是继承结果。14128 在 0012 可见的弯折也是继承的。跟踪组 110254、114600、69519 分别增加 4、62、24 核，但域外支持仅 0.000063p、0.411740p、0.003015p，全部未过本轮增长门槛。114600 由 polyline 变为 line 是辅助载体类型变化；核几何未变。内部补洞、重复覆盖和微小漂移没有被计为明显延伸。

共保存 309 张实际 PNG，本次直接查看其中 **54 张**，包括两个全景、全部 11 个选定组的 M4 双视图、增长组前后对照、部分 parent 色与全景 highlight，以及六类精确版本负例的双视图。完整清单及逐例判断见 [VISUAL_REVIEW.json](VISUAL_REVIEW.json)，未声称看过全部图片。原生图与既定 4 倍最近邻裁剪均保持原相机、核宽度、opacity 和白背景 floor=0.0144。

负例仍有明确可见性限制：gap 对 301451/301459 两图为空；最差接受对 102148/102152 在 0036 不可见，0012 只有很小的支持。其最大 tangent 为 29.9957679°；crossing/tangent 拒绝对 52414/400805 为 30.0005328°。parallel、branch、ambiguity 的固定案例虽有像素，但不足以核实深度或真实分支关系。本次未从所看图片确证吞并独立结构，也不能据此给出安全通过结论。新增曲线双视图证据与负例可辨性均未完成，因此科学结论保持 PARTIAL。

[ANALYSIS_AUDIT.json](ANALYSIS_AUDIT.json) 验证了 33 个 parent 源码快照、44 个冻结输入、33 个 helper 引用（其中四个外部 helper）和五个完整检查点。原始 means、covariance、opacity、primitive_id、internal_piece_id、arc_t 的 dtype、shape 与字节哈希全部相等，行顺序及前驱分配保留通过。第一次只读审计误把 colors 要求纳入“非颜色字段”而退出 1；确认只多出 colors 后修正检查并通过，过程已如实记录，与实际 science 子进程退出 0 分开。原文件没有因此改动。

配置 SHA256 为 `5ef2a3ea03b7b89e97a9349ab77b0ca67eac301f157212927e77fe52a004c012`；决策 SHA256 为 `fc46a472c90c482837926bba814df15a25b5e89d743c5d8dc81a3950dbcd9fc8`。可复现源码依据 [PARENT_RUN_FROZEN.json](PARENT_RUN_FROZEN.json) 的 source_snapshot 映射，不依赖未来工作树 HEAD。[RUN_REQUEST](RUN_REQUEST.json) 与 [INTERFACE_VALIDATION](INTERFACE_VALIDATION.json) 保存完整脚本、配置及命令参数；实际入口为批准 venv 的 `python -B continuation_level.py --config CONFIG.json`，所有路径均在该请求内绝对指定。BUILD 的 11 项小测试实际退出 0，真实 RED/GREEN 保留，但测试本身不作为本轮科学结果。

本单元未运行初始化、池化、M5、ficus M4 或 scan65 M4。此前三场景 M3 是各自封存的外部参考，旧 v04 仍是 PARTIAL；其历史缺失退出和未保存内存进度不会被这次成功覆盖。全部物理身份暂定，没有独立真值、held-out 泛化或间隙连续性结论。

下一独立单元建议为 **ficus 封存 M3 → 一轮 M4**，完全相同数值设置和 1800 秒上限，使用 unit005 状态，跟踪 79171、204470、57769；保留 57769 的主要单-parent 性质作为对照。原因是本轮建筑已有实质多片段增长，而曲线新增长与同设置场景迁移尚待验证。具体冻结输入、阶段、控制和视觉否证条件见 [NEXT.json](NEXT.json)。本次仅提出建议，未启动下一单元。

