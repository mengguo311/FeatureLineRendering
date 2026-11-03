# unit007 保存结果分析

结论：**执行PARTIAL，已交付大范围真实重叠归属；尚未证明joint比同库greedy获得更好的直线与曲线双视图身份。** 清楚的直线例308174可见多个旧叶统一，但两臂相同，且属于重叠观测归组，不是端点续接。主要改变的polyline例48211在0012中为空，无法通过双视图曲线判据。全景仍有碎裂、重叠和尖刺；冻结原核几何不能清除这些尖刺。所有身份暂定，没有物理真值或held-out主张。

父持有的[实际退出](../../orchestration/unit_007/COMPUTE_EXIT.json)：2026-11-01 08:07:26.473829至08:20:58.921545 JST，child returncode=0、reason=null、actual_child_exit=true。[RUN_RESULT](RUN_RESULT.json)记录811.351s，delivery_gate=true，状态partial；返回0不表示科学完成。本分析仅读取保存数据和PNG，未拟合、测试、重渲染或修改源码。

**实际处理范围。** 固定scan24 M4的458490原核、112414候选记录、5452成功overlap，1917完整分量、6775叶，最大43叶，无128叶超限。1774分量建库完整，覆盖6463叶/5279对；其余143分量因600s建库期限记NOT_RUN_BANK_DEADLINE，312叶/173对未完成并保留M4。实际新恢复5241模型，加复用38模型，共5279；无恢复metrics失败。unit006控制精确重放，7245假设供两臂共享；累计求解28.297s。已完成分量的joint回执为optimal，不把未处理分量算作求解成功。这里的最优只针对有限假设库与目标函数，不是物理最优。先保存映射checkpoint并冷载，再保存原生全景和诊断；本次有300张实际PNG。

|保存指标|greedy|joint|
|---|---:|---:|
|全行映射|458490|458490|
|assigned / UNKNOWN|263539 / 194951|263491 / 194999|
|相对M4新增 / 丢失assigned|17190 / 0|17142 / 0|
|相对unit006新增 / 丢失assigned|17102 / 0|17054 / 0|
|相对unit003新增 / 丢失assigned|16305 / 2854|16271 / 2868|
|选中overlap组|1752|1873|

原M4组保持不可分，unit006原8分量被保留；unit003的新端口身份没有受保护，以上撤回必须保留。joint相对greedy新增assigned593行、退回UNKNOWN641行，净少48；共5059行edge_id不同，greedy独有134假设、joint独有255假设。更多组或更高目标都不能代替可见身份正确性，joint不支配greedy。无端点外延运行；UNKNOWN仍受3seedlets/6kernels/4p去重支持门槛限制。

**实际图像。** 已查看joint[0012全景](scenes/scan24/stages/joint/0012_FULL.png)、[0036全景](scenes/scan24/stages/joint/0036_FULL.png)、[greedy 0036全景](scenes/scan24/stages/greedy/0036_FULL.png)及下列保存的原核裁剪。全景仍见密集建筑边、重复片段和离群核，未见足以宣布整体视觉清理完成的变化。相机、宽度、opacity固定，无carrier或connector补画。

308174两臂均包含6叶、848核、250seedlets，22个UNKNOWN核获得归属；含5个达到保存实质贡献标准的原parent，但7814贡献639核占主导。其原核隔离在[0012](scenes/scan24/stages/joint/diagnostics/COVERAGE_308174_29140ef4_GROUP_0012_CROP4.png)和[0036](scenes/scan24/stages/joint/diagnostics/COVERAGE_308174_29140ef4_GROUP_0036_CROP4.png)均呈清楚直线。[M4同一行集](scenes/scan24/stages/M4_reference/diagnostics/COVERAGE_308174_29140ef4_GROUP_0036_CROP4.png)显示原先分色，[完整证据邻域](scenes/scan24/stages/joint/diagnostics/COVERAGE_308174_29140ef4_CONTEXT_0036_CROP4.png)仍含近邻重叠线及侧向短刺，因此这只是有可见依据的候选统一，不是平行/深度安全认证。支持并集138.454p，最长连续段仅2.751p，有限范围183.029p，总gap44.575p、最大gap0.312p、重复支持17.099p、域外代理0。不能把138.454p写成连续边长或新增外延。

48211是实际两臂差异：greedy选择叶48211/48293/190688/190715（261核）；joint选择48211/48261/48293（263核）。joint支持58.976p、最长5.217p；greedy58.489p、最长3.491p，两者域外代理均0。joint两实质parent为1138和8268，后者229核占主导。其[0036隔离图](scenes/scan24/stages/joint/diagnostics/COVERAGE_48211_ffb1ea1c_GROUP_0036_CROP4.png)是带台阶的浅弯细线，尚不是清楚完整曲边；[greedy上下文](scenes/scan24/stages/greedy/diagnostics/COVERAGE_48211_ffb1ea1c_CONTEXT_0036_CROP4.png)和[joint上下文](scenes/scan24/stages/joint/diagnostics/COVERAGE_48211_ffb1ea1c_CONTEXT_0036_CROP4.png)仍有旁支/重叠结构。[0012原生隔离图](scenes/scan24/stages/joint/diagnostics/COVERAGE_48211_ffb1ea1c_GROUP_0012.png)实为空白，没有相应裁剪。选图核心行集是joint三叶，不能仅凭该隔离图宣称已排除greedy额外两叶的风险；完整上下文也不能消除深度不可辨性。该例保持PARTIAL。

109991两臂相同，276核/3叶，支持62.054p但最长2.646p，域外代理0。51111/51166/113545属于unit006继承案例，不算本轮新增改善。113545支持62.412p但最长6.265p，其0036及109991的0036裁剪触及原生边界。51111/51166的0012上下文也有边界裁切。负例153248/377058的[0036上下文](scenes/scan24/stages/joint/diagnostics/NEGATIVE_153248_377058_CONTEXT_0036_CROP4.png)只是很短的重叠线，不能判定完整深度安全；301451/301459在两视图均空。未逐一人工判读全部300图，不声称四负例全部通过；缺曲线、空图、裁切、不可判的parallel/branch/depth保持未解决。没有相对unit006丢失的成员集，故top3_lost_member_sets为空，不伪造受损例。

**机制边界与下一步。** 现有结果证明模型库覆盖扩大后，能保存大量跨叶的重叠统一及真实greedy/joint分歧；没有证明联合互斥选择带来更好物理身份。完整竞争限于保存overlap候选和前缀模型库；没有成功候选的真实关系无法由MILP创造，也不能把它叫solver失败。支持是映射到辅助模型上的区间代理，钳制/重复覆盖不是新观测；原parent仅作来源。最先需要检验的是该有限模型方法对更明显曲线的适用性，而不是再增加scan24拟合预算。

唯一下一步：**同设置迁移到ficus封存M4和其对应M5-on-M4保存overlap图，成对运行同库greedy/MILP。** 采用unit007冻结数值规则及完整分量，不增加阈值、不增加拓扑轮、不接端点；固定test_r_1/test_r_79，先映射后图。v05 unit016 M4 checkpoint、unit019 M5 ORDERED_CANDIDATES与controls/joint/CANDIDATE_STATUS文件已确认存在，但本分析未加载完整ficus资产，候选计数、版本/metrics与来源hash须下一轮readiness冻结验证。不是宣称scan24已成功再推广，而是检验当前曲线证据不足的场景依赖性。预算仍1800s（600建库、600求解、600交付），限窗口内。需真实跨片段直线及曲线在双视图可辨；仅重复池化、更多assigned、曲线标签或空图均不成功。详见[NEXT](NEXT.json)，尚未执行。

**来源与复现。** 本分析按[PARENT_RUN_FROZEN](PARENT_RUN_FROZEN.json)逐文件核对53个source_snapshot文件及2个helper，全部匹配；不依赖未来工作树HEAD。DECISION SHA256 `fa465ee31e24a23fc30cdc74af2021eda486cea92a55f32359a38ed95e7a5ea5`；CONFIG SHA256 `7bf5b9819a1f380d715baa4f990fe4abbf268799838287a56aaf6986242212f3`，均实核相符。renderer.py SHA `ce24cd30d663e6f421064d83006f097b02a5cf6a74b20c177a905ca514caed93`，libjoint.so SHA `033a973a71dc5364677a5bf0625f23dc4fe445b70257f04de7cb70cdccca84b0`。[GEOMETRY_AUDIT](GEOMETRY_AUDIT.json)保存458490原行、字段hash及unchanged_before_after=true、carrier_geometry_rendered=false；本分析未重读原全资产重算该审计。两臂mapping checkpoint的所有文件hash已复核相符，保存MEMBERSHIP各458490行。本分析另由保存映射核对line_kernel_id=0..458489、M4旧assigned零丢失、零旧组拆分；两臂均成立。joint求解回执1774个optimal、143个FALLBACK_M4。原输入M4 STATE SHA `4f350e3a991c98d7cf011d833be4fc5aebcce1c7d328ae69b39948b5698ec31f`。

父执行命令由[RUN_REQUEST](RUN_REQUEST.json)绑定：指定venv Python `-B /home/u00134/3dgs_line/line_kernel_global_association_v06/reproduction/line_kernel_global_association_v06/coverage_runner.py --config` 本单元CONFIG.json。完整Python路径与helper/input绑定见CONFIG和父回执。分析未改父退出/数值文件、未创建worker SEAL；封存交由父级。
