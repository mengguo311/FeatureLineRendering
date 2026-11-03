本单元工程执行完成，科学结论仍为 **PARTIAL**。共同有限辅助曲线明显改变了固定端点图上的可行归属，但尚未证明双视图可辨的、实质跨来源直线与曲线同时改善；MILP在两种表示下都没有超越同库greedy。保存结果可以交付，不能将130个选中假设、更多assigned或平滑辅助q解释为130条真实边。

父进程记录实际子进程PID3152172、returncode=0、reason=null，09:16:15.659260启动，09:17:36.874034结束；runner记录80.498秒。unit010此前rc1及其加载接口失败完整保留，并非本轮数值对照。这里只读取已保存结果、PNG和冻结源码，未拟合、重渲染、重跑或修改源代码。

148/148完整eligible分量完成，176次完整路径拟合，无新增空间候选；296份joint分量回执均为optimal，总求解0.568秒。固定图只含163条eligible endpoint，593条成功endpoint仍被原mask排除；原756条成功关系中的这一限制没有被解决。拼接库40个可行路径，共同曲线库152个。拼接拒绝为self_contact77、vertex_turn53、window_turn6；共同曲线拒绝为finite_domain23、fit_tangent1。这是表示及共同参数化见证的效果，不是放宽原核残差阈值，也不是证明原self-contact判定在物理上错误。

四臂都先checkpoint、冷载完整285956行MEMBERSHIP，再保存两张800×800原生全景。本次复核了四臂映射和全景checkpoint所列文件SHA，检查line_kernel_id/edge_id形状，核对79个冻结source_snapshot文件。GEOMETRY_AUDIT保存原核字段前后哈希、原行序及数量一致，辅助曲线不参与渲染。所有旧M4分配零丢失、旧组零拆分。

|表示（两种选择器结果相同）|选中路径假设|assigned|UNKNOWN|相对M4新增assigned|相对M4丢失|
|---|---:|---:|---:|---:|---:|
|concat|39|118911|167045|441|0|
|common|130|119860|166096|1390|0|

选中假设不等于已激活身份：concat选中组内仍有236核UNKNOWN，common为1024核。concat全为两叶；common为123个两叶、6个三叶、1个四叶，部分多叶组仍未达到激活支持门槛。满足保存统计中“至少两个实质parent贡献”的组数分别12和16，也不是物理准确率。

两种表示各自的greedy/joint主归属一致，双全景PNG也逐字节一致；因此缺失项top3_selection_member_differences是没有实际差异可展示，不是遗漏渲染。concat主归属还精确复现unit009。common相对concat/unit009新增分配1079核、撤回130核，改变ID1381行，并拆开5个unit009新增组：47878、47914、54189、71920、158396。零M4损失不能掩盖这些较新归属的撤回。

先看实际全景：细碎叶缘、重叠线和长尖刺依然明显；肉眼没有看到整体干净程度或完整性发生明确改变。固定核归属方法不能消除原有几何尖刺。

![common全景test_r_1](scenes/ficus/stages/common_joint/test_r_1_FULL.png)
![common全景test_r_79](scenes/ficus/stages/common_joint/test_r_79_FULL.png)

同相机拼接对照：[test_r_1](scenes/ficus/stages/concat_joint/test_r_1_FULL.png)、[test_r_79](scenes/ficus/stages/concat_joint/test_r_79_FULL.png)。均为实际原核，原宽度/opacity、白底floor0.0144及UNKNOWN灰；没有辅助carrier或无支持桥。

137016是较有价值的局部直线证据：152核来自5393的56核和8864的96核，两者均为实质贡献；common新激活16核。隔离图在两个视角均为近直的细小连续痕迹，但非常浅淡，视觉增益幅度不能靠数字夸大。[视图1](scenes/ficus/stages/common_joint/diagnostics/PATH_137016_GROUP_test_r_1_CROP4.png)、[视图79](scenes/ficus/stages/common_joint/diagnostics/PATH_137016_GROUP_test_r_79_CROP4.png)、[完整邻域79](scenes/ficus/stages/common_joint/diagnostics/PATH_137016_CONTEXT_test_r_79_CROP4.png)。支持并集26.585p、最长段9.209p、有限长度32.197p、总gap5.612p、最大gap0.305p；它不是一条26.585p的连续观测。

92122在两个视角仅可见浅弯，104核中93核来自同一parent3577，另外4/7核的支持未达实质贡献；不能据此证明实质跨parent曲线归组。[视图1](scenes/ficus/stages/common_joint/diagnostics/PATH_92122_GROUP_test_r_1_CROP4.png)、[视图79](scenes/ficus/stages/common_joint/diagnostics/PATH_92122_GROUP_test_r_79_CROP4.png)。其支持22.717p、最长段1.803p、总gap10.099p、最大gap0.382p、有限长度32.836p。230214虽是三叶42核并全部激活，却全来自parent9210；双视图是很小的斜线，[图1](scenes/ficus/stages/common_joint/diagnostics/PATH_230214_GROUP_test_r_1_CROP4.png)、[图79](scenes/ficus/stages/common_joint/diagnostics/PATH_230214_GROUP_test_r_79_CROP4.png)，不能当作跨来源大组成功。

112780/116525在common可行、concat因self_contact拒绝，双视图可见弯曲，但这是既有v05 M5见过的曲线，不是首次发现的新曲线证据。[图1](scenes/ficus/stages/common_joint/diagnostics/REFERENCE_112780_116525_GROUP_test_r_1_CROP4.png)、[图79](scenes/ficus/stages/common_joint/diagnostics/REFERENCE_112780_116525_GROUP_test_r_79_CROP4.png)。支持9.843p、最长段2.474p、最大gap1.206p；不能忽略间断。21870/22319两表示成员相同，其约69.081p支持并集只有1.759p最长段，约34.691p总gap，主要是继承大组而非新增收益。

64355/65064仍无通过模型：concat因window_turn，common因一个原核中心有限域右越界0.001682p，失败保持保存，未扩大EPS。71920是common撤回的曲线相关案例，隔离图仍见灰色未归属部分：[图1](scenes/ficus/stages/common_joint/diagnostics/PATH_71920_GROUP_test_r_1_CROP4.png)、[图79](scenes/ficus/stages/common_joint/diagnostics/PATH_71920_GROUP_test_r_79_CROP4.png)。四个固定负例上下文均有保存；已查看112/205435双视图，只能看到很小的重叠短痕迹，不能判断真实深度关系或证明分支安全。[上下文1](scenes/ficus/stages/common_joint/diagnostics/NEGATIVE_112_205435_CONTEXT_test_r_1_CROP4.png)、[上下文79](scenes/ficus/stages/common_joint/diagnostics/NEGATIVE_112_205435_CONTEXT_test_r_79_CROP4.png)。其余固定负例本次未逐张目检，不能宣称全部视觉守卫通过。

本轮没有inter-carrier overlap pooling；共同模型的支持区间经过重映射，是投影代理。GROUPS中的anchor_outward_support_p=0不能作为“物理外延为零”的独立测量；也不能用pooling_not_extension=false推出真实延伸。成员bbox、有限extent、各parent交集与gap已保存在GROUP_STATISTICS，但没有新传感器观测。遮挡、平行结构、分支和深度安全仍未全面验证；旧parent仅是来源，全部身份provisional，无held-out或物理真值主张。

当前已过09:15新单元截止，NEXT.action=stop表示停止开新科学单元并交接，不表示方法方向耗尽。唯一延期建议是：在未来授权窗口，以真实多视图观测为593条masked endpoint关系提供独立的关联/弃权证据，并与旧mask基线比较。先核实独立观测与可见性输入；没有则NOT_READY，不能以原核自渲染替代。保留完整竞争邻域和原几何守卫，遮挡继续UNKNOWN。此建议尚未运行，不在本窗口自动实施。

溯源：CONFIG SHA256 `f13916c506a78b767e01cde78ecd8e0c754428dc55ca1ba69e8610cdc6c61168`；decision SHA256 `d5fa8f7711577cec59f2e7303ffd6954c77b46c33316ef9c52cb5d8258025794`。精确源码使用[PARENT_RUN_FROZEN.json](PARENT_RUN_FROZEN.json)指向的79文件快照，不依赖将来的工作区HEAD。renderer.py SHA256 `ce24cd30d663e6f421064d83006f097b02a5cf6a74b20c177a905ca514caed93`；libjoint.so SHA256 `033a973a71dc5364677a5bf0625f23dc4fe445b70257f04de7cb70cdccca84b0`，本次读取核对一致。真实父命令见RUN_REQUEST：批准venv的python -B path_library_runner.py --config 本单元CONFIG.json；只作复现说明，当前未重跑。父负责后续封存，本报告不建立含可变运行流的SEAL。
