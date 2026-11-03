unit010 的实际执行被加载器回调接口错误阻断，科学实验尚未开始。执行状态为 **blocked**，科学结论为 **NOT_RUN_INTERFACE_FAILURE**，不是共同参数化的负结果，也不是求解器失败。没有本轮可分析的成员映射、载体模型、谱系或原核图像。

权威[COMPUTE_EXIT.json](../../orchestration/unit_010/COMPUTE_EXIT.json)记录实际子进程rc=1、reason=null、actual_child_exit=true：09:09:50.204703启动，09:09:51.289060结束。保留原失败退出，不用wrapper返回值或测试rc0覆盖。[RUN_RESULT.json](RUN_RESULT.json)记录completed=[]、fit_calls=0、new_candidates=0、actual_saved_pngs=[]，内部记录耗时0.311241秒。父进程记录的整个子进程时段约1.084秒，两者口径不同。

失败位置明确：[冻结runner第29行](source_snapshot/path_library_runner.py)以`load(c, lambda: guard('readiness'))`传入无参数回调；[冻结加载器第54行](source_snapshot/scene_adapter.py)调用`guard('readiness')`，抛出`TypeError: ... takes 0 positional arguments but 1 was given`。异常发生在输入/helper/source文件哈希验证之后、前驱checkpoint绑定检查和STATE/NPZ数值加载之前。因此不能声称本次已经核验285956行所有权、恢复全部载体或生成148分量。此前19项小型测试通过，但垂直测试替换了整个load函数，未覆盖这个真实调用契约；这是本次新增runner的工程缺陷。

|计划交付|实际保存状态|
|---|---|
|ficus M4的285956原核恢复与行序检查|NOT_RUN；只有计划输入绑定|
|163 eligible端点、148完整分量及路径枚举|NOT_RUN；这些是冻结预期，不是本次测量|
|concat_greedy / concat_joint映射|MISSING|
|common_greedy / common_joint映射|MISSING|
|辅助模型、四臂checkpoint及冷载|MISSING|
|四臂test_r_1/test_r_79原生全景|MISSING，0张|
|单组、完整邻域、困难负例、几何审计|MISSING|
|assigned得失、UNKNOWN、旧组拆分|不可评估，不能填写为0|
|支持并集、最长段、域外支持、gap、parent贡献|不可评估|

检查范围限定为`scenes/`：该目录下没有科学产物。`tests/`中的18行合成夹具和mock像素只是构建测试证据，绝不是原核科学结果或预览。BUILD的测试隔离事件和已保存修复证据仍保留于tests/TEST_ISOLATION_INCIDENT.json，不删除或改写失败日志。

为了交代科学动机，本次通过image tool复看以下**unit009历史参考**，没有生成新图。这些图不得算作unit010交付：

![仅unit009参考：ficus原核全景test_r_79](../unit_009/scenes/ficus/stages/joint/test_r_79_FULL.png)

![仅unit009参考：112780/116525完整邻域裁剪test_r_79](../unit_009/scenes/ficus/stages/joint/diagnostics/REFERENCE_112780_116525_CONTEXT_test_r_79_CROP4.png)

参考全景仍有大量碎片和长尖刺；固定原核归属不能移除这些几何缺陷。参考局部短弧可见但像素少，不能独立确认物理身份。unit009实际两臂相同39个二叶身份；64355/65064被window_turn拒绝，112780/116525被self_contact拒绝。这仍支持检验共同有限参数化的动机，但unit010尚未提供任何支持或反驳该假设的新证据。实质跨片段直线/曲线、parallel/branch/depth安全、有限gap和held-out泛化均未验证；更多同色、支持池化或目标改善本来就不足以证明物理正确。

下一步只推荐一次：在新的、parent冻结的单元修复phase-aware guard接口，并执行本次完全相同的四臂共同有限路径实验。不要在本分析阶段修改源码、重跑unit010或改变阈值。新BUILD先用真实加载器调用契约配合小型合成输入记录RED→GREEN，不能继续mock掉整个load；保留完整输入验证、资源/阶段期限及已有19项回归。仅修复接口，不因没有科学结果而另选无依据的新机制。本轮所有原始失败产物保持只读。09:15前冻结新单元、最迟09:18启动、计算≤1200秒且末600秒保留交付；不满足时只交付已有成果，不声称方向耗尽。详见NEXT.json，尚未实施。

本次只读核对父冻结的78个源码快照文件和2个helper哈希，均匹配[PARENT_RUN_FROZEN.json](PARENT_RUN_FROZEN.json)及配置；不依赖将来工作树HEAD。CONFIG SHA256：034ebbb44b46e9a989f7019dcf6ed287922028cbd3a7ae32ec6edd609a9d19e6；decision SHA256：82b0d3bad636e82f8458fc42511a8aa2e7a0c70743d341238fca245d74dbc77b。原M4 STATE绑定SHA：7d1457b144b0c58b8a3fe1fd1f1620e967158c1ace8326c64e6d996671378900。renderer.py SHA：ce24cd30d663e6f421064d83006f097b02a5cf6a74b20c177a905ca514caed93；libjoint.so SHA：033a973a71dc5364677a5bf0625f23dc4fe445b70257f04de7cb70cdccca84b0。

原批准命令保留在[RUN_REQUEST.json](RUN_REQUEST.json)：`/mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_8build_part_prior_feasibility_v03/venv/bin/python -B /home/u00134/3dgs_line/line_kernel_global_association_v06/reproduction/line_kernel_global_association_v06/path_library_runner.py --config /mnt/hdd1/u00134/radegs_paper_reproduction_v01/line_kernel_global_association_v06_20261101/units/unit_010/CONFIG.json`。本阶段未执行该命令、未拟合/渲染/测试、未修改源码或参数，只写本报告、STATUS及NEXT。封存由parent完成，不生成worker SEAL。
