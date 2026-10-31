unit_002 已完成完整 ficus 的 L0→L1→M2_MERGE_ONLY 交付，科学结论为 **PARTIAL**。parent 实际子进程返回码 **0**、reason=null，2026-10-31 06:11:48 至06:17:48 JST；runner记录359.428秒。全部8个请求阶段完成，没有用测试或内存进度代替结果。原始285956个LINE核全部保留，三个级别均已保存全行membership、有限载体、支持区间、谱系和两张原生图。scan65、L3/L4与M2后池化没有运行。

本次只更换完整场景，沿用unit_001科学设置。L1为两次固定宿主有限范围的containment pooling，不能称为宿主延伸；M2为一次载体拓扑合并，多核支持与载体拓扑分开。实际有小型直线与曲线续接示例，但整体仍碎片化，不能宣称形成了大规模完整物理边缘。

|保存级别|分配核|UNKNOWN|覆盖率|主分组|
|---|---:|---:|---:|---:|
|强v03对应L0|95951|190005|33.5545%|3318|
|池化L1|106399|179557|37.2082%|3289|
|单轮拓扑M2|109052|176904|38.1359%|3243|

L1新增10448核，M2较L1新增2653核。L1第一pass消耗21550次fit、累计2778事件；第二pass累计30000次fit、3059事件，预算没有重置。M2重新使用30000次fit，记录11320次载体合并。大量事件涉及尚未激活的载体，所以11320不是新增主边缘数。L1/M2分别记录9768/14677次fit_cap拒绝；M2还记录531 parallel、31 branch、2488 tangent、16586 endpoint_tangent、56790 endpoint_gap、3968 ambiguous。完成的是冻结截断预算下的一轮，不是穷尽所有候选。

保存的增长门槛有10组通过（4 line、6 polyline），均有宿主域外支持；其中只有4组跨原始primitive parent，只有3组至少两个原始parent各贡献≥6核且≥2p支持。v03碎片、L1载体与原始parent是不同的溯源层次，不能互换计数。10组满足旧片段数值门槛，不代表10个跨原始parent物理边缘，也不支持“≥5个实质跨原始parent增长组”结论。以下长度均以保存场景p为单位，核数与去重支持分别列出。

|M2组/模型|L1贡献核|最大L1支持→M2并集|域外支持|最长连续支持|最大/总间隙|有限载体长度|
|---|---|---|---:|---:|---|---:|
|34448 / polyline|43+31|9.210→15.786|6.582|2.970|0.624/3.630|19.424|
|14456 / polyline|41+16|7.129→11.298|4.198|2.498|0.694/3.302|14.614|
|36790 / line|37+15|5.680→10.046|4.389|3.223|0.778/1.956|12.003|
|107514 / polyline|20+28|5.361→10.678|5.324|1.523|1.320/3.026|13.733|

34448的原始parent贡献为9核/2.432p与65核/15.219p；36790为15核/4.371p、22核/4.927p、15核/3.054p。14456有两个实质parent，第三个仅1.499p；107514的次要parent仅8核/1.800p，故不计入两个实质parent组。各parent的支持可能重叠，不能相加当总支持。完整bbox、各级贡献、有限域及间隙见[GROUPS.json](scenes/ficus/stages/M2_MERGE_ONLY/GROUPS.json)，原始有限区间见[CARRIERS.npz](scenes/ficus/stages/M2_MERGE_ONLY/CARRIERS.npz)。不把间隙桥接成可渲染支持，所有物理身份仍为暂定。

已用image工具实际查看56张保存PNG，文件和逐项观察见[VISUAL_REVIEW.json](VISUAL_REVIEW.json)。总共保存210张原生/既有确定性裁剪PNG，未在本分析中重渲染。全景中既有长直异常线在L0已存在，不能算本轮新发现或新增长。主要图片均是位置、协方差、宽度与opacity不变的原始核，仅修改颜色；裁剪为运行阶段已保存的4倍最近邻辅助图，未新增拟合线或2D叠线。

|级别|相机test_r_1|相机test_r_79|
|---|---|---|
|L0|[原生图](scenes/ficus/stages/L0/test_r_1_FULL.png)|[原生图](scenes/ficus/stages/L0/test_r_79_FULL.png)|
|L1|[原生图](scenes/ficus/stages/L1/test_r_1_FULL.png)|[原生图](scenes/ficus/stages/L1/test_r_79_FULL.png)|
|M2|[原生图](scenes/ficus/stages/M2_MERGE_ONLY/test_r_1_FULL.png)|[原生图](scenes/ficus/stages/M2_MERGE_ONLY/test_r_79_FULL.png)|

34448（短弧）双视图均可见，L1的分色片段在M2统一。test_r_1：[L1](scenes/ficus/stages/M2_MERGE_ONLY/diagnostics/CROP_34448_test_r_1_GROUP_34448_L1_test_r_1.png)、[M2](scenes/ficus/stages/M2_MERGE_ONLY/diagnostics/CROP_34448_test_r_1_GROUP_34448_M2_test_r_1.png)、[原始parent](scenes/ficus/stages/M2_MERGE_ONLY/diagnostics/CROP_34448_test_r_1_GROUP_34448_PARENTS_test_r_1.png)；test_r_79：[L1](scenes/ficus/stages/M2_MERGE_ONLY/diagnostics/CROP_34448_test_r_79_GROUP_34448_L1_test_r_79.png)、[M2](scenes/ficus/stages/M2_MERGE_ONLY/diagnostics/CROP_34448_test_r_79_GROUP_34448_M2_test_r_79.png)、[原始parent](scenes/ficus/stages/M2_MERGE_ONLY/diagnostics/CROP_34448_test_r_79_GROUP_34448_PARENTS_test_r_79.png)。

36790（短直线）双视图均可见，L1的分色片段在M2统一。test_r_1：[L1](scenes/ficus/stages/M2_MERGE_ONLY/diagnostics/CROP_36790_test_r_1_GROUP_36790_L1_test_r_1.png)、[M2](scenes/ficus/stages/M2_MERGE_ONLY/diagnostics/CROP_36790_test_r_1_GROUP_36790_M2_test_r_1.png)、[原始parent](scenes/ficus/stages/M2_MERGE_ONLY/diagnostics/CROP_36790_test_r_1_GROUP_36790_PARENTS_test_r_1.png)；test_r_79：[L1](scenes/ficus/stages/M2_MERGE_ONLY/diagnostics/CROP_36790_test_r_79_GROUP_36790_L1_test_r_79.png)、[M2](scenes/ficus/stages/M2_MERGE_ONLY/diagnostics/CROP_36790_test_r_79_GROUP_36790_M2_test_r_79.png)、[原始parent](scenes/ficus/stages/M2_MERGE_ONLY/diagnostics/CROP_36790_test_r_79_GROUP_36790_PARENTS_test_r_79.png)。

这些对照使用相同最终成员行集，因此轮廓应当一致；变成单色不独立证明增长。域外支持和显著旧片段贡献提供数值延伸证据，双视图用于发现明显不连贯/误并。34448和36790仅为小型暂定例子，14456接近水平且像素少；107514虽有小弯曲，跨原始parent实质贡献不足。固定最大组21870、21927、20007、93407也已查看双视图，它们不满足增长门槛，不能拿“大”替换“增长”。

scan24只重放unit_001已保存的两个实际成员集合，没有拟合或更改旧membership。103748双视图近直线；202626双视图呈曲弧。L1、M2及parent颜色的保存图片补齐了unit_001选择器漏选的视觉证据，但未改写旧单元的PARTIAL结论。

scan24 103748：0012 [L1](controls/scan24/CROP_103748_0012_GROUP_103748_L1_0012.png) / [M2](controls/scan24/CROP_103748_0012_GROUP_103748_M2_0012.png) / [parent](controls/scan24/CROP_103748_0012_GROUP_103748_PARENTS_0012.png)；0036 [L1](controls/scan24/CROP_103748_0036_GROUP_103748_L1_0036.png) / [M2](controls/scan24/CROP_103748_0036_GROUP_103748_M2_0036.png) / [parent](controls/scan24/CROP_103748_0036_GROUP_103748_PARENTS_0036.png)。

scan24 202626：0012 [L1](controls/scan24/CROP_202626_0012_GROUP_202626_L1_0012.png) / [M2](controls/scan24/CROP_202626_0012_GROUP_202626_M2_0012.png) / [parent](controls/scan24/CROP_202626_0012_GROUP_202626_PARENTS_0012.png)；0036 [L1](controls/scan24/CROP_202626_0036_GROUP_202626_L1_0036.png) / [M2](controls/scan24/CROP_202626_0036_GROUP_202626_M2_0036.png) / [parent](controls/scan24/CROP_202626_0036_GROUP_202626_PARENTS_0036.png)。

六类精确版本负例/最差接受例均查看双相机：parallel、branch、crossing_tangent、gap、ambiguity、accepted_worst_margin。记录、完整行集与版本见[CONTEXT_SELECTION.json](scenes/ficus/stages/M2_MERGE_ONLY/diagnostics/CONTEXT_SELECTION.json)。最差接受例113517+250960的q95残差0.499891p，接近0.5p上限；间隙拒绝115630+204683距阈值仅0.000003906p。这些例子大多仅数个原生像素，放大后仍无法可靠辨认三臂或深度分离；没有把“图片存在/守卫拒绝”冒充视觉正确性。未确认整场无平行吞并、无分支误并，故视觉否证审查仍PARTIAL。

14份parent冻结源码快照、13个配置helper引用（含9份旧单元快照）、18个输入引用与12个完整checkpoint的文件哈希已核对。三个级别的membership已重新读取，行号连续且原始primitive_id逐行相等，L0等于强v03，旧已分配核没有退回UNKNOWN；保存的冷载geometry审计逐字段bitexact，原始Gaussian NPZ哈希一致。分析只检查现存数组，不执行拟合。详见[ANALYSIS_AUDIT.json](ANALYSIS_AUDIT.json)及[ANALYSIS_PROVENANCE.json](ANALYSIS_PROVENANCE.json)。未来验证使用source_snapshot，不要求工作树latest HEAD继续对应本单元。

CONFIG SHA256为`2b9042ad166cf5e8ba203b9306ac7d1c717be537fa25ff0681728b33c86eac54`；DECISION SHA256为`ed5eab00f056f7c27bf76617a8422abe70815625a7c208a3f8609f9211f1128e`。parent命令、helper与输入散列见provenance；实际退出保留在[PARENT_COMPUTE_RECEIPT.json](PARENT_COMPUTE_RECEIPT.json)。原请求helper分类失败、真实RED/GREEN与接口修复记录均保留；修复只改请求分类，科学配置和源码未改。原freezer文件仍保留历史行为，后续新单元应遵循修复后的请求分类，不能不加检查地重用原freezer输出。

本分析未更改源码或科学参数，未运行拟合/测试/渲染，没有GPU、RGB源场景GS或新几何。v04仍是历史PARTIAL；本次交付不会覆盖其未知/失败退出。单位输出约158MB，完整工作量和静态文件见[SEAL.json](SEAL.json)，不封存仍在增长的orchestration/API日志。

下一步建议仅做完整scan65（279616核）的同设置L0→两次L1池化→一次M2拓扑合并，固定0012/0036相机、1800秒parent预算，M2状态先落盘，最后420秒交付；不重跑scan24/ficus，不调阈值。精确预算、控制与视觉否证见[NEXT.json](NEXT.json)。这将补足当前实际缺失的场景对照；之后才依据三场景证据选择机制改动。12:00 JST后不开新单元，12:35停止science。这里没有物理真值验证，也没有独立held-out泛化结论。
