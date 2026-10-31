# unit_006：scan65 第二轮拓扑合并

执行完成，科学结论 **PARTIAL**。Parent实际数值子进程returncode=0、reason=null，07:30:57–07:33:33 JST；runner耗时155.06秒。完整279616行M3已保存、冷载并渲染，状态、有限载体/支持、谱系和诊断均已交付。本分析只读取保存结果及图片，没有拟合、重跑、参数调整、源码修改或新渲染。

本单元恢复unit003封存M2，恰好追加一轮M3，累计两轮拓扑合并。没有初始化、池化或其他场景重跑。原始核位置、协方差、宽度、不透明度、数量和顺序冻结；载体只是辅助模型，图片始终显示实际原始LINE kernels。旧parent只作溯源，UNKNOWN有效候选资格保持，失败旧组及拒绝前驱保留。

| scan65阶段 | 已分配核 | UNKNOWN | 主组数 |
|---|---:|---:|---:|
| 强v03/L0 | 97950 | 181666 | 3490 |
| L1固定宿主池化 | 112061 | 167555 | 3450 |
| M2 | 114798 | 164818 | 3402 |
| M3 | 118343 | 161273 | 3443 |

M3增加3545个已分配核，覆盖率42.32%。新增分配和主组数不能代替更大边的证据。本轮24215次fit，未达到30000上限；4469个accepted events包含dormant载体，不能等同于4469个新主边。候选仍受截断（candidate_cap45953、sample_query_saturated48841），所以未耗尽fit预算不证明搜索完备。记录有endpoint_gap32843、residual11449、parallel1156、branch30、ambiguous2962等；这些是原口径事件统计，不应简单相加为独立样本。

12组通过冻结增长公式：6条line、6条polyline。其中8组具有两个以上实质原parent，11组域外支持至少4p；同时满足实质跨原parent及域外至少4p者7组。64877域外为3.931p，但并集增量5.841p，仍按原公式达标；没有事后修改门槛。3组有至少三个实质L1片段，但这3组全部只有一个实质原parent，尚未形成更深层的跨parent组合证据。

| 组/模型 | 核数 | 最大M2支持p → M3并集p | 域外支持p | 最长连续段p | 总/最大间隙p | 贡献 |
|---|---:|---:|---:|---:|---:|---|
| 64877/polyline | 118 | 17.094 → 22.935 | 3.931 | 12.295 | 2.784 / 0.393 | 60+58个M2核；两实质L1、三实质原parent |
| 56133/line | 101 | 10.802 → 17.525 | 6.710 | 2.755 | 3.917 / 1.023 | 68+33个M2核；两实质原parent |
| 167509/polyline | 100 | 13.693 → 26.730 | 13.105 | 1.582 | 13.921 / 1.484 | 四实质L1；仅一个原parent |
| 113334/polyline | 96 | 10.769 → 18.314 | 7.585 | 3.390 | 3.216 / 0.339 | 50+46个M2核；两实质原parent |
| 54560/polyline | 86 | 9.308 → 17.128 | 7.839 | 2.716 | 5.725 / 1.295 | 50+36个M2核；两实质原parent |
| 95478/line | 77 | 9.071 → 14.023 | 4.952 | 3.729 | 2.675 / 0.309 | 52+25个M2核；两实质原parent |

56133的同成员M2两色片段在M3形成一条投影对齐的线段；0036清楚，0012窄而近乎竖直。64877在0036显示浅弧及两段M2/原parent贡献，在0012严重缩短。113334在两视图显示小幅弯折。54560和167509尽管存为polyline，两视图投影却接近直线；模型名称不是曲率真值。

167509的四个L1贡献分别25、25、30、20核，M2为50+50核，说明确有逐级组合；但100核来自同一原parent。有限载体长40.703p，支持并集26.730p，最长连续支持仅1.582p，最大间隙1.484p。不能把载体长度或统一颜色解释为连续观测，更不能把同parent重组说成实质跨parent增长。每个parent的映射支持可能重叠，不能直接相加。

固定最大组238627、61267、67265在双视图呈较长曲线/弯折形状，却均为M3支持增量0、域外0，属于继承资产。跟踪直线62791保持159核和27.362p支持，未增长。跟踪曲线167261变为167257，只添4核，支持增加0.5895p、域外0；这是内部支持补充，不是新的向外延伸。

实际保存268张PNG，本次通过image工具直接检查50张，覆盖两张全景、全部11个选中组双视图、重点同成员M2/M3/L1与parent色、全部六类负例双视图。清单及观察见VISUAL_REVIEW.json。原相机0012/0036、白背景、floor0.0144、原宽度/opacity保持；UNKNOWN灰。裁剪沿用已冻结RGB8联合bbox、pad16、4倍最近邻，不是新视图或新增几何。

困难负例仍不足以做物理确认：parallel在0012呈重叠的较长线段，在0036明显缩短；branch、crossing/tangent、gap、ambiguity多为少量原生像素。最差接受例157058/198686仅几个像素，切向29.999514°接近30°；最近切向拒绝169208/169213为30.000381°。看到这些图不等于视觉验证了守卫。现有图片未提供足以确认所有深度关系、分支和邻近平行结构的证据，因此不宣称全部接受正确。

实际图链接：

- [完整0012](scenes/scan65/stages/M3_MERGE_ONLY/0012_FULL.png)、[完整0036](scenes/scan65/stages/M3_MERGE_ONLY/0036_FULL.png)
- [56133 M2](scenes/scan65/stages/M3_MERGE_ONLY/diagnostics/CROP_56133_0036_GROUP_56133_M2_0036.png)、[M3](scenes/scan65/stages/M3_MERGE_ONLY/diagnostics/CROP_56133_0036_GROUP_56133_M3_0036.png)、[0012 M3](scenes/scan65/stages/M3_MERGE_ONLY/diagnostics/CROP_56133_0012_GROUP_56133_M3_0012.png)
- [64877 M2](scenes/scan65/stages/M3_MERGE_ONLY/diagnostics/CROP_64877_0036_GROUP_64877_M2_0036.png)、[M3](scenes/scan65/stages/M3_MERGE_ONLY/diagnostics/CROP_64877_0036_GROUP_64877_M3_0036.png)、[parent色](scenes/scan65/stages/M3_MERGE_ONLY/diagnostics/CROP_64877_0036_GROUP_64877_PARENTS_0036.png)
- [167509 L1](scenes/scan65/stages/M3_MERGE_ONLY/diagnostics/CROP_167509_0012_GROUP_167509_L1_0012.png)、[M2](scenes/scan65/stages/M3_MERGE_ONLY/diagnostics/CROP_167509_0012_GROUP_167509_M2_0012.png)、[M3](scenes/scan65/stages/M3_MERGE_ONLY/diagnostics/CROP_167509_0012_GROUP_167509_M3_0012.png)、[同一原parent](scenes/scan65/stages/M3_MERGE_ONLY/diagnostics/CROP_167509_0012_GROUP_167509_PARENTS_0012.png)
- [最差接受例](scenes/scan65/stages/M3_MERGE_ONLY/diagnostics/CROP_CONTEXT_accepted_worst_margin_0012_CONTEXT_accepted_worst_margin_0012.png)

完整性核验全部通过：29个Parent源码快照、40个输入引用、30个helper引用（4个获准外部helper）、5个检查点哈希；完整行顺序、baseline/previous映射、所有已分配前驱保留、载体成员归属、无效源UNKNOWN、有限载体/支持、选图完整行集合及负例精确输入版本。重新读取原NPZ核对means、covariance、opacity、primitive_id、internal_piece_id、arc_t的dtype/shape/字节哈希。见ANALYSIS_AUDIT.json。主资产行顺序精确；诊断行集合精确，不要求诊断文件按行号排序。

CONFIG SHA256：`f8e62e62b769002ddd34efff8650711790e6013919c9201fd60d2ceb25d8064b`；DECISION SHA256：`5c6ce63c92c53987cfc4aa6981c5f510af42dc85de9c6beaf7c786f7c9f9fb0a`。PROVENANCE.json保存原始输入、helper、不可变快照哈希、实际runner命令和Parent EXIT引用。实际命令为批准venv Python的`-B continuation_scene.py --config unit_006/CONFIG.json`。未来HEAD不影响快照验证。BUILD为诚实的REGRESSION_ONLY：11项小测试实际rc0，最终真实切片123seedlets/577核、7fit/6接受；初始零fit切片与补充原因也保留，均不是全场景研究结果。

所有请求阶段完成；本单元初始化、池化、M4、scan24、ficus为NOT_RUN。三场景现在都有保存的M3，但科学评价分别保留各自PARTIAL。v04历史PARTIAL、未知/失败退出及未保存阶段不因本单元rc0而改写。所有物理身份仍暂定，无RGB source GS、补画间隙、拟合线替代图、独立真值或held-out泛化主张。静态SEAL仅涵盖已关闭本单元文件，不纳入外部实时监督/API流。

NEXT=continue，建议下一独立单元从unit004的完整scan24 M3追加恰好一轮M4，累计第三轮；同参数、同30000fit上限，不池化、不重跑其他场景。当前三场景两轮结果证明有局部增长，但更深的实质跨parent合并仍稀少；building的110254直线、114600 polyline以及三实质L1/三实质原parent的69519提供具体跟踪对象。对比M3时必须承认轮数与总拟合机会同时增加。相对于最大M3贡献者衡量增量，另列至少三实质L1且至少两实质原parent的交集；继承大组、内部补洞不计为向外增长。

下一步需新决策冻结、BUILD小测试与RUN_REQUEST、Parent实际compute、ANALYSIS四阶段；本次没有启动。NEXT.json给出状态/检查点哈希、1800秒及120/1380/1800阶段预算、固定视图与否证条件。没有依据仅因ficus/scan65结果有限而提高fit cap，两场景最近一轮均未耗尽。后续有用实验仍受12:00不开新单元、12:35结束science的绝对窗口约束。
