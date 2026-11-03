# v10 unit002 保存结果分析

R4硬拒绝已真实解除：匹配R2控制0次且完整状态复现，R2_R4新增6次（200509/201906/202023各2次），每次均带parallel冲突见证。末端因KNOT_CAPACITY停止，数值rc=0不等于科学完整，无连接/闭合不能覆盖此容量中断。新增10个UNKNOWN核、406个原assigned核被整组吸收；已有平行结构被试验性归入同身份，但图像小、竞争背景拥挤，物理误并尚不能认证。

实际子进程rc=0、reason=null，01:22:03.261711–01:29:22.400071 JST，运行438.19秒；RUN_RESULT=partial。两臂458490行映射和原核全景已保存，原核哈希审计unchanged=true。

R2控制保留全部成员/q/版本，零新增。R2_R4六次：200509吸收114346/113541；201906吸收165472/-201934；202023吸收274276/204525。每次有parallel见证；规则4没有偷偷重新硬拒绝。

已看双视图之一全景、事件1隔离/完整竞争背景及事件3另一视图隔离。小图不支持物理准确率结论；继承长段不算新恢复，固定原核保留旧尖刺。无辅助桥墨或源表面遮挡；无物理、held-out、时间稳定认证。

下一单元另行冻结同一起点[2,4]对[2,4,6]：解除自接触、gap和no_unique_support硬返回，保留有限软J及规则1/3/5。先核查本次257结点容量中断的具体候选；若从当前终态会使共同库不可完成，则使用本轮封存START作matched-start，不增大容量、不把截断库当穷尽。保留本轮全部6次及最坏事件，不恢复R2/R4；不得在分析启动计算。

实际查看：
- [scenes/scan24/stages/R2_R4_OFF_TRANSPORT_FINAL/0036_FULL.png](scenes/scan24/stages/R2_R4_OFF_TRANSPORT_FINAL/0036_FULL.png)
- [scenes/scan24/worst_events/R2_R4_OFF_TRANSPORT/0001/0012_ISOLATED_CROP.png](scenes/scan24/worst_events/R2_R4_OFF_TRANSPORT/0001/0012_ISOLATED_CROP.png)
- [scenes/scan24/worst_events/R2_R4_OFF_TRANSPORT/0001/0012_FULL_OBJECT_CONTEXT.png](scenes/scan24/worst_events/R2_R4_OFF_TRANSPORT/0001/0012_FULL_OBJECT_CONTEXT.png)
- [scenes/scan24/worst_events/R2_R4_OFF_TRANSPORT/0003/0036_ISOLATED_CROP.png](scenes/scan24/worst_events/R2_R4_OFF_TRANSPORT/0003/0036_ISOLATED_CROP.png)


本次补充核验（保存数据分析，无科学重算）

实际子进程rc=0、reason=null，01:22:03至01:29:22；RUN_RESULT为partial。R2控制0次，全部membership字段与START逐项相同；六次接受的四文件CHECKPOINT哈希均吻合、每次458490行，原行ID和parent不变，原assigned无损失且无组被拆分，FINAL与第六次checkpoint相同。原核几何不变另由保存GEOMETRY_AUDIT支持；本分析没有重新渲染或移动任何核。

|次序|组←donor|并入核|J|新增独特支持p|
|---|---|---:|---:|---:|
|1|200509←114346|53|-.066232|7.872930|
|2|201906←165472|24|-.171915|7.187907|
|3|202023←274276|113|.082377|12.786390|
|4|200509←113541|178|-.093451|29.634691|
|5|201906←-201934|10|.021831|.174028|
|6|202023←204525|38|.030164|13.302096|

上述每步完整库合格解释数分别3/3/1/20/1/3，提交保存的最低J，随后重新进入搜索；三组各连续接受两次。每步均有parallel见证；最后一例的冲突[274276,334885]已由前次继承，不能把它误报成新donor直接造成的平行关系。WHOLE旧域拟合位移最大值分别.4282/.2684/.9815/.1410/.6538/.4290p，证明辅助旧段实际共同调整，而非仅换标签；这些位移不涉及原核。首次平行吸收已在步骤1；步骤3和5/6出现距离或角度超旧R2线的旧成员损伤，解除后仍保留有限J与接受资格。没有巨组物理正确性的结论，最大目标组由990增至1221核。

|组|核数START→FINAL|union支持p|最长run p|最大gap p|相对START域外支持p|
|---|---|---|---|---|---:|
|200509|990→1221|184.367→221.466|89.02499→89.02091|.841138→.841003|38.3410|
|201906|339→373|63.709→71.402|53.14211→53.07621|.080652→.003888|7.6936|
|202023|113→264|41.142→70.369|36.595→57.067|.190027→.308670|26.9520|

200509和201906的union增加并未增加最长连续run；201906最后十核仅.174p独特支持，主要是重叠/内部填充。202023有较大域外及run增益但最大gap变大，双视图证据不足。实质M4贡献数分别13→15、3→4、3→5；三贡献及4p代理并非物理完整曲线证明。53254、132977、210790未变。

相同START比较：新增UNKNOWN→assigned为10、lost0、旧组split0；406原assigned行由5个旧身份完整归并，合计416标签变化。最终260039 assigned/198451 UNKNOWN。对M5累计gain281、lost0（起点已gain271）；对M4累计gain13690/lost0（起点13680）；对v09 WHOLE累计gain54（起点44）。v06 greedy/joint各累计gain11182、lost1231、旧组split81；起点已经lost1231/split81，这些不能归咎本轮或被忽略。与起点比较使用保存contingency，不能凭数字ID差当获益。

真正停止是KNOT_CAPACITY：0014_200509中的113545未完成，87邻居/342记录中已有8个合格解释，30个donor未尝试，程序正确未截断选胜者。无任何支持闭合；201906/202023的最后接受后还没有完整终态重查。控制六组无连接仅适用于该完整控制库。剩余132977有17个branch/137个vertex拒绝，53254有194个vertex拒绝；200509未完成库有40个no_unique_support和2个branch。不能把当前容量停机当整个场景或研究窗口穷尽。

实际视觉：全对象0036保留建筑线结构和拥挤细节；200509隔离是很窄的近竖直线，全对象裁剪中有多条邻近平行线，难判新增身份边界。201906起点和最终0012都是相近的小弧，完整背景含多条弯曲竞争，0036呈浅弧；不能用继承弧和颜色证明新增完整曲线。202023在0036是微小短线/多线竞争，最坏事件0012全白，明确缺该视图证据。未发现足以独立确认第三臂/深度误吞的可辨图像，并不等于排除了这些错误。现有尖刺原几何不变；错吸入某身份仍需计为风险。全部PNG为保存原核图，不使用source-surface遮挡或辅助曲线/桥墨。

下一步：下一单元另行审核冻结同一封存unit002 START的[2,4] versus [2,4,6]，复用本轮已执行[2,4]轨迹作控制并核对初始库，不重跑已完成的历史增长。新策略仅解除no_unique_support、self_contact、gap硬返回，允许纯pooling但保留有限原J和规则1/3/5；完整六种子、全donor范围、拟合与容量不变。选START而非当前FINAL，是因为FINAL的200509→113545已知KNOT_CAPACITY且尚有30个donor未完成；禁止升容量或截断选赢家。若新策略再次容量阻断，保存并另审真实可完成的种子范围；不得冒充自然耗尽。新实验尚未运行，须新DECISION。

已实际查看的图：
- [scenes/scan24/stages/R2_R4_OFF_TRANSPORT_FINAL/0036_FULL.png](scenes/scan24/stages/R2_R4_OFF_TRANSPORT_FINAL/0036_FULL.png)
- [scenes/scan24/worst_events/R2_R4_OFF_TRANSPORT/0001/0012_ISOLATED_CROP.png](scenes/scan24/worst_events/R2_R4_OFF_TRANSPORT/0001/0012_ISOLATED_CROP.png)
- [scenes/scan24/worst_events/R2_R4_OFF_TRANSPORT/0001/0012_FULL_OBJECT_CONTEXT.png](scenes/scan24/worst_events/R2_R4_OFF_TRANSPORT/0001/0012_FULL_OBJECT_CONTEXT.png)
- [scenes/scan24/worst_events/R2_R4_OFF_TRANSPORT/0003/0036_ISOLATED_CROP.png](scenes/scan24/worst_events/R2_R4_OFF_TRANSPORT/0003/0036_ISOLATED_CROP.png)
- [scenes/scan24/diagnostics/201906/R2_R4_OFF_TRANSPORT_0012_ISOLATED_CROP.png](scenes/scan24/diagnostics/201906/R2_R4_OFF_TRANSPORT_0012_ISOLATED_CROP.png)
- [scenes/scan24/diagnostics/201906/R2_R4_OFF_TRANSPORT_0012_FULL_OBJECT_CONTEXT_CROP.png](scenes/scan24/diagnostics/201906/R2_R4_OFF_TRANSPORT_0012_FULL_OBJECT_CONTEXT_CROP.png)
- [scenes/scan24/diagnostics/202023/R2_R4_OFF_TRANSPORT_0036_FULL_OBJECT_CONTEXT_CROP.png](scenes/scan24/diagnostics/202023/R2_R4_OFF_TRANSPORT_0036_FULL_OBJECT_CONTEXT_CROP.png)
- [scenes/scan24/diagnostics/200509/R2_R4_OFF_TRANSPORT_0036_ISOLATED_CROP.png](scenes/scan24/diagnostics/200509/R2_R4_OFF_TRANSPORT_0036_ISOLATED_CROP.png)
- [scenes/scan24/diagnostics/200509/R2_R4_OFF_TRANSPORT_0036_FULL_OBJECT_CONTEXT_CROP.png](scenes/scan24/diagnostics/200509/R2_R4_OFF_TRANSPORT_0036_FULL_OBJECT_CONTEXT_CROP.png)
- [scenes/scan24/diagnostics/201906/START_0012_ISOLATED_CROP.png](scenes/scan24/diagnostics/201906/START_0012_ISOLATED_CROP.png)
- [scenes/scan24/diagnostics/201906/R2_R4_OFF_TRANSPORT_0036_ISOLATED_CROP.png](scenes/scan24/diagnostics/201906/R2_R4_OFF_TRANSPORT_0036_ISOLATED_CROP.png)
- [scenes/scan24/worst_events/R2_R4_OFF_TRANSPORT/0003/0012_ISOLATED.png](scenes/scan24/worst_events/R2_R4_OFF_TRANSPORT/0003/0012_ISOLATED.png)
