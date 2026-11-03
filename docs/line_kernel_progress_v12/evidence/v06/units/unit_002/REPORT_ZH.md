# unit002 保存结果分析

执行完成，科学结论仍为 **PARTIAL：联合选择没有带来主归属或画面优势**。本次把决策分量与证据邻域分开，完整处理固定候选图的699个分量；这解决了unit001的递归邻域膨胀，却没有证明更好的物理边身份。未运行任何新拟合、重渲染或后续实验。

父进程实际子进程returncode=0、reason=null，06:39:48.461845至06:41:16.175995 JST；RUN_RESULT记录87.061秒，solver累计6.919秒。退出依据为orchestration/unit_002/COMPUTE_EXIT.json，不以分析命令或wrapper状态替代。所有699个joint分量报告optimal；只是给定有限图和守卫下的优化结论。

## 范围与配对结果

2279条成功endpoint配对中，旧完整joint ambiguity mask排除1440条，剩839条形成699个决策分量：588个二叶、87个三叶、22个四叶、2个五叶。无超限/超时分量；入射拒绝及overlap证据保留但不递归扩张。完整仅相对于旧有截断候选列表，不是全部空间竞争关系。

|项目|greedy|joint|
|---|---:|---:|
|选择连接 / 复合路径|308 / 301|309 / 302|
|assigned / UNKNOWN|249667 / 208823|249667 / 208823|
|相对M4新增 / 丢失assigned|3318 / 0|3318 / 0|
|三叶路径|7|7|
|全行主edge_id差异|0|0|

两份458490行映射、有限叶载体、谱系及原生图均已保存并由runner冷载。版本元数据不应被误称为逐字段相同。新增3318个assigned不是准确率；既有3132行重新归组也不是新增观测。重复支持未被池化，连接只用于检查，未画桥或改变核。

唯一连接差异在分量150：greedy选105514；joint改选107787和108657，目标benefit由1.216658增至1.723981。对应路径支持仅3.731p、3.631p、2.511p，均未达4p激活要求，保持UNKNOWN。因此优化改进没有转换为主归属或可见归组改进。不能把它算成成功增长。

## 实际图片与有限支持

已通过image工具查看两张joint原生全景、53254/201906/10975双视图单组、201906双视图完整邻域，以及38670、parallel/branch负例邻域。全景仍有碎裂、重叠与尖刺；固定原核几何不能消除这些源资产缺陷。

[0012原生全景](scenes/scan24/stages/joint/0012_FULL.png) · [0036原生全景](scenes/scan24/stages/joint/0036_FULL.png)

|路径|核数/叶数|支持并集p|最长连续段p|有限长度p|总gap / 最大gap p|
|---|---:|---:|---:|---:|---:|
|53254|190 / 2|44.292|3.460|56.217|11.925 / 1.092|
|201906|282 / 2|39.387|4.004|50.170|10.777 / 1.117|
|115200|179 / 2|33.085|4.731|45.189|12.104 / 1.304|
|210790|159 / 2|24.904|2.585|32.798|7.895 / 1.425|
|10975|79 / 3|18.178|0.821|28.794|10.615 / 1.384|

53254的可见直段在两个相机中成立，但180/190核来自同一个旧parent；不能当作实质跨parent证明。

![53254 0012](scenes/scan24/stages/joint/diagnostics/PATH_53254_4dd9afa0_GROUP_0012_CROP4.png)
![53254 0036](scenes/scan24/stages/joint/diagnostics/PATH_53254_4dd9afa0_GROUP_0036_CROP4.png)

201906在两视图呈C形/浅U形，可见弯曲存在；248核的polyline叶原已存在，仅接入34核直叶，域外支持6.043p。两个实质原parent不构成物理真值。邻域仍有相邻颜色与端部重叠，无法凭单组干净曲线排除深度/平行误吞；且两臂相同。

![201906 0012](scenes/scan24/stages/joint/diagnostics/PATH_201906_f0179c6c_GROUP_0012_CROP4.png)
![201906 0036](scenes/scan24/stages/joint/diagnostics/PATH_201906_f0179c6c_GROUP_0036_CROP4.png)
[对应完整邻域0012](scenes/scan24/stages/joint/diagnostics/PATH_201906_f0179c6c_CONTEXT_0012_CROP4.png) · [邻域0036](scenes/scan24/stages/joint/diagnostics/PATH_201906_f0179c6c_CONTEXT_0036_CROP4.png)

10975三叶跨两个实质原parent，激活13个原UNKNOWN核；短直段可见，但18.178p支持并集的最长连续观测仅0.821p。115200、210790统计列供诊断，不以长度或parent数替代视觉验证。所有七条三叶路径在两臂一致，没有四叶以上已选路径。

## 负例与缺失

路径守卫确实产生拒绝/cut：joint记录self_contact312、vertex_turn210、window_turn43、unsupported_gap1；这是算法记录，不能当作已确认的真实几何错误数。parallel 84842/362883与branch 153248/377058的固定视图很小、部分重叠，无法判定物理安全。crossing/tangent与全部深度关系未完成逐例视觉判定。gap 301451/301459的单组及邻域在两个固定相机均为空白，未产生裁剪；这是缺失证据，不能报告gap安全通过。未更换相机。

共有188张已保存PNG、12个诊断case；有图文件不等于可辨证据。ficus/scan65本机制NOT_RUN。没有物理真值或held-out泛化检验；所有身份暂定。支持并集、域外支持、有限extent、最长连续段必须分别解释。

## 下一步与来源

建议只推进一个独立机制：**完整endpoint竞争分量上的全局歧义/反事实关联**，以当前保守mask结果为对照。保留现有候选、成本与几何守卫，比较完整替代路径及界限；不稳定关系继续UNKNOWN。涉及未建模overlap竞争者时必须弃权，不能遗漏对手后宣布身份确定。全局不确定性规则需下一决策单独冻结；不直接放开mask，不提高fit预算/距离。理由是1440条成功endpoint被旧局部歧义排除且决策图极小，不是solver耗时瓶颈。具体待审方案见NEXT.json，尚未运行。

来源：PARENT_RUN_FROZEN.json绑定的13个source_snapshot文件与两个renderer/libjoint helper均逐一SHA256复核通过；CONFIG/DECISION亦匹配。核对记录见ANALYSIS_PROVENANCE_CHECKS.json。CONFIG SHA256：`d32eb66790e729d8e8a3203dad8e08fc3979a7682ff6791cffcfa2d970afa6f1`；DECISION：`02848938d7f9fdcfa349cfeac18af01f8093bd616218ebac5a18c5b3b1cd3603`。不依赖可变HEAD。原始RUN_RESULT、实际EXIT、失败/拒绝记录不修改，静态seal由parent完成。

独立只读核对：两臂对应PNG字节相同 94 / 94；画面相同与主归属相同一致。
