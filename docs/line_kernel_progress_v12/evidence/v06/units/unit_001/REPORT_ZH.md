本单元结论为 **PARTIAL：交付已落盘，尚无联合选择优于贪心的证据**。父持有的实际数值子进程于2026-11-01 06:22:59.427188–06:23:19.695458 JST执行，returncode=0、reason=null；依据[实际退出回执](../../orchestration/unit_001/COMPUTE_EXIT.json)，没有用外层启动器退出替换它。RUN_RESULT的complete描述程序交付完成；科学范围仍有5/8上下文NOT_RUN，不能升级为全场景成功。

本次只分析既存输出，没有拟合、重新渲染、测试、改参数或改源码。新表示让共同edge_id持有有序有限载体，多重观测不占拓扑度；未把整个组合重新拟合成一条曲线，也未做重叠池化。两臂共享候选、成功拟合成本、歧义排除、激活规则及完整路径守卫。封存v05是外部参考，配对对照是相同新表示的greedy。

两臂均已保存458490行MEMBERSHIP、CARRIERS、GROUPS、LINEAGE、solver记录和双相机原核全景，共48张PNG。分析冷读映射，核对行序、两臂所有字段相等及两份映射检查点内全部hash；24对PNG逐一hash相同。实际选中record_index均为107129、108632、112094。assigned从M4的246349增至246400，UNKNOWN从212141降至212090：新增51、丢失0、旧组拆分0，77行edge_id改变，其中26行是旧assigned的重新归组。这不是准确率，也不能与另一个历史阶段的assigned直接混作损失。仅scan24局部tracer被求解；全行导出不等于全场景联合优化，ficus/scan65均NOT_RUN。

|上下文|完整载体数|可选endpoint连接|状态与限制|
|---|---:|---:|---|
|0：大组53254贡献者|3706|104|超128，NOT_RUN|
|1：ranked_component_1715|106|6|唯一非空求解上下文|
|2：ranked_component_51636|205|15|NOT_RUN|
|3：parallel记录84842/362883|503|21|NOT_RUN，不能称负例通过|
|4：branch记录153248/377058|350|14|NOT_RUN，不能称负例通过|
|5：crossing/tangent记录153427/153430|65|0|5个成功endpoint记录在排除后无可选边|
|6：大组210790贡献者|398|20|NOT_RUN|
|7：gap记录301451/301459|19|0|没有成功endpoint边|

[选择清单](scenes/scan24/readiness/SELECTION.json)的全局成功endpoint为2279，歧义过滤后839。这里的闭包仅相对历史已截断候选完整，不能保证空间中所有正确续接都曾提出。递归吸纳拒绝/overlap记录把大组及parallel/branch上下文扩为巨块，是最早明确的范围瓶颈。无候选或被固定歧义排除属于候选/信息与保守弃权问题，不能归咎MILP。

唯一非空图的MILP完成4次求解，加入vertex_turn一次和self_contact两次no-good cut，最终通过既定守卫的目标benefit=2.234404499330625，与greedy完全相同；求解记录status0、gap0、累计0.013159s。该有限候选问题的最优状态不是物理正确性证明。记录保留SciPy对threads/parallel选项的转交HiGHS警告。本结果未展示三片以上路径或全局竞争优势；所有输出路径均仅含两个叶载体。

|路径|核数/seedlets|支持并集p|最长观测段p|有限长度p|总gap/最大gap p|相对最大叶域外支持p|主分配|
|---|---|---:|---:|---:|---|---:|---|
|1354|33/9|4.121|1.166|6.778|2.657/1.365|1.874|33个UNKNOWN激活|
|1727|44/11|8.054|1.771|11.241|3.187/0.682|2.896|18激活、26原assigned保留归组|
|2352|23/5|2.950|1.653|4.351|1.400/0.773|1.298|全部23仍UNKNOWN，仅保存建议关联|

详见[支持与贡献](scenes/scan24/stages/joint/GROUP_STATISTICS.json)。1354和1727各有两个原parent贡献达到≥6核/2p，但parent只是来源；各贡献支持可重叠，不能相加代替并集。三路径均无≥4p域外支持。支持并集、有限载体extent、最长连续观测、gap以及身份统一是不同量；未把connector当观测支持，未画桥，未作池化。2352不足4p激活支持门槛而留UNKNOWN，不能把三条建议路径都算新增主组。

以下是实际已查看的原核全景；greedy对应文件hash完全一致。楼体边缘仍碎裂、多色、含原始离群细线，未观察到联合选择带来的全景改善。固定核参数不能清掉原资产尖刺。渲染没有源表面遮挡，深度结构身份不能仅由这些投影认证。

![原核全景0012](scenes/scan24/stages/joint/0012_FULL.png)
![原核全景0036](scenes/scan24/stages/joint/0036_FULL.png)

已实际查看三个单组的双视图及context1双视图。1354在0012贴近画面左缘，仅几像素，0036同样极小；1727是几像素短斜段/短竖段；2352为微小灰色UNKNOWN。它们没有足够可见证据确认新增曲线，亦不能证明跨片段同一物理边。

![1354，0012，左缘微小片段](scenes/scan24/stages/joint/diagnostics/GROUP_1354_0012.png)
![1354，0036](scenes/scan24/stages/joint/diagnostics/GROUP_1354_0036.png)
![1727，0012](scenes/scan24/stages/joint/diagnostics/GROUP_1727_0012.png)
![1727，0036](scenes/scan24/stages/joint/diagnostics/GROUP_1727_0036.png)

另实际查看context3/4/5/7的0036图：parallel与branch候选上下文呈多条重叠彩线，尺度小，无法辨识物理分离；crossing/tangent同样微小；gap图视觉上近乎全白。前两者本来未求解，后两者没有可选连接，都不能宣称parallel/branch/depth/gap安全通过。未逐张审视的保存图片明确不作视觉认证。14张实际查看清单见[ANALYSIS_CHECKS](ANALYSIS_CHECKS.json)；全48张的存在不等于48张都可判。没有补画预览、改相机或新裁剪。

![完整context1，0036](scenes/scan24/stages/joint/diagnostics/CONTEXT_1_0036.png)
![未求解parallel上下文，0036](scenes/scan24/stages/joint/diagnostics/CONTEXT_3_0036.png)
![gap上下文，0036，近乎空白](scenes/scan24/stages/joint/diagnostics/CONTEXT_7_0036.png)

来源绑定：decision SHA256为02bfda02ed358041390851cc32e6e292dd83ad5e088016466e33eacac92bb24b；config为a15b4f24fd57bbc138cdd456ac40642ea4f58afb8459763cdaf0af509d5c7be1。已逐一核对[PARENT_RUN_FROZEN](PARENT_RUN_FROZEN.json)引用的9个不可变source_snapshot文件及两个helper：renderer.py的ce24cd30d663e6f421064d83006f097b02a5cf6a74b20c177a905ca514caed93、libjoint.so的033a973a71dc5364677a5bf0625f23dc4fe445b70257f04de7cb70cdccca84b0。不依赖未来工作树HEAD。原核来源/颜色/相机见[DISPLAY_SOURCE](scenes/scan24/stages/joint/DISPLAY_SOURCE.json)；[GEOMETRY_AUDIT](GEOMETRY_AUDIT.json)记录458490核及六字段前后hash/行序不变，分析未重新执行该审计或加载完整原核计算。正式命令是获准Python以-B运行RUN_REQUEST指定runner.py --config CONFIG.json，实际退出归父记录。

下一单元只建议一个改变：**把端口决策连通分量与只读证据邻域分开**。在相同scan24 M4及839条现有可选endpoint边上，全部可占端口的竞争边必须完整进入决策分量；历史成功但masked的替代及所有入射拒绝/overlap记录保留完整对方行作证据邻域，不让纯证据边递归扩张求解变量。检查真实共享硬约束后才可宣称可分解。保留128决策载体上限、相同greedy/MILP、原成本/歧义/守卫/UNKNOWN，不提高预算或生成新候选；优先大组53254/210790所在分量，再按固定顺序覆盖其余全场景决策分量。下一轮必须另冻结，详见[NEXT](NEXT.json)，本次没有启动。

这针对5/8超限的真实瓶颈，不能保证获得新增长。如839条边仍没有可见有效续接，则记录候选/弃权瓶颈，另议独立证据机制；不能偷偷放宽本轮阈值。所有物理身份仍暂定，未验证完整平行/分支/深度安全，无物理真值、独立held-out或泛化主张。单元文件及source不改动，静态封存由父完成。
