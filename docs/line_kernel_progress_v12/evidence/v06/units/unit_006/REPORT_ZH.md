# unit006：原核观测域归属分析

计算与交付完成，科学结论仍为 **PARTIAL：少量重叠归属改善，未证明新增直线与曲线的双视图改善，joint未优于同库greedy**。原核中心替代旧辅助载体采样作为有限域见证后，假设从12增至32；两臂最终均选10个假设，主归属零差异，118对对应PNG逐文件SHA相同。相对unit005新增assigned 21、丢失0；这些数字不是准确率，也不是外延增长。

父实际子进程于2026-11-01 07:52:31.425474–07:53:11.116732 JST运行，returncode=0、reason=null、actual_child_exit=true；RUN_RESULT耗时38.941秒。依据为[父退出回执](../../orchestration/unit_006/COMPUTE_EXIT.json)与[保存结果](RUN_RESULT.json)，没有用包装器退出码替代。分析阶段只读保存结果与图片、写本报告及状态/下一步；没有拟合、重跑、渲染或修改源码。

作用范围是scan24的8个完整overlap竞争分量、42个M4叶、38个历史配对模型。全资产458490行映射均保存，但其余区域恢复原M4，不能称全场景新方法覆盖。保存选择清单显示全图有1917个成功overlap分量、5452条关系，其中1909分量未选。本轮fit_calls=0、new_spatial_candidates=0；“recovered_models=38”指重新加载历史恢复模型，非本轮拟合。端点路径、ficus、scan65均未运行。

unit005旧规则12假设及两臂全部membership字段、group/version精确重放；8个新库完成，保留11个旧固定anchor假设，加入21个恢复模型假设。MILP非空分量均返回optimal/gap=0，三个空库的零解另列。求解总时长约0.039秒，含旧控制约0.018秒。不存在本轮超时造成的joint劣势；相同解也不代表其他竞争图上全局优化无价值。

|双臂相同指标|结果|
|---|---:|
|assigned / UNKNOWN|246437 / 212053|
|相对原M4新增 / 丢失 / ID变化行|88 / 0 / 343|
|相对unit005新增 / 丢失 / ID变化行|21 / 0 / 78|
|相对unit003新增 / 丢失 / ID变化行|75 / 3726 / 7270|

相对unit003的3726撤回不能隐藏：本轮是从M4出发的overlap归属实验，未继承unit003端口路径成果，不是单调累积升级。原M4旧组未拆分、旧assigned未丢失。小组57087仅9核/2seedlets，仍不满足激活条件，全部保持UNKNOWN。

有限域诊断揭示18个host从旧q越界拒绝转为通过，14个旧q越界者仍被原核中心越界拒绝，另有1个旧规则通过者转为拒绝；新规则不是简单放宽。38个host中23通过、15因中心越界失败。失败模型的最大越界量约0.0000802–0.003157p；这些是保存的数值诊断，不据此扩大EPS或外推q。donor另有33次residual拒绝。没有证据证明所有剩余失败都是求解器问题。

真正改变成员的案例需要与仅换模型解释分开：

|组|实际改变|支持并集p / 最长段p|总gap p / 最大gap p|解释|
|---|---|---|---|---|
|51111|两叶33核，新增9 UNKNOWN|5.754882 / 1.095652|1.476371 / 0.358274|相对旧host域外仅0.049062p；只有一个原parent达到6核且2p，不能称实质双parent续接|
|51166|两叶62核，均原已assigned|9.971668 / 2.564055|2.387522 / 0.324518|两个原parent分别20核/4.768p、42核/8.494p；相对旧host域外2.825861p，值得核查，但未达到4p且缺独立单组图|
|113545|四叶变五叶，加入390861，新增12 UNKNOWN|62.412488 / 6.264945|16.086652 / 0.369638|支持仅增加0.026947p、最长段增加0.025021p，重复支持增加约2.64249p；域外0，主要是重复覆盖/内部填充|

113545含三个实质原parent，仍由parent2479的247核主导；跨来源不等于物理身份。10975、50830、57133、57153的叶成员未变，换了模型或投影统计不能算新组增长。18608的108.260p支持并集对应最长段仅4.153p；57127的74.483p并集对应最长段2.014p，两者是继承结果。所有支持来自旧区间映射，含钳制诊断，属于投影支持代理，不是新观测。没有运行host-extension或新端点连接，也没有补画间隙。

实际查看的原核全景如下；greedy与joint图片字节相同，故展示joint代表共同结果：

![0012全景](scenes/scan24/stages/joint/0012_FULL.png)

![0036全景](scenes/scan24/stages/joint/0036_FULL.png)

建筑屋面/窗框仍碎裂、重复且有尖刺；固定核参数不能消除原有尖刺。全景没有呈现明确的大尺度新归组优势。

![113545同成员集合单组0012](scenes/scan24/stages/joint/diagnostics/OBS_DOMAIN_113545_4effe5cf_GROUP_0012_CROP4.png)

![113545单组0036](scenes/scan24/stages/joint/diagnostics/OBS_DOMAIN_113545_4effe5cf_GROUP_0036_CROP4.png)

113545呈近竖直、轻微弯折/重叠的细线，0036底端被原生画幅裁切；polyline标签不能证明新增曲线。对应[0036完整邻域](scenes/scan24/stages/joint/diagnostics/OBS_DOMAIN_113545_4effe5cf_CONTEXT_0036_CROP4.png)中的窄平行色带不能排除不同深度/平行结构。57153在0036只是短近水平线，0012为空；10975在0012为短斜线且成员继承。

**视觉交付缺口**：新增成员组51111和51166没有独立GROUP PNG；它们只能在已存18608邻域中间接出现，不能据此认定正确归并。选择器的top3改变被model-key替换占据，所谓“damaged”旧模型例10975/57153不等于损失成员；本轮实际相对unit005丢失行数为0。不得把选择器missing=[]理解为新归组证据齐全。未在分析中补渲染。

查看[153248/377058负例0036邻域](scenes/scan24/stages/joint/diagnostics/NEGATIVE_153248_377058_CONTEXT_0036_CROP4.png)仅见窄近竖直重叠，不能可靠判定深度/分支安全；301451/301459两视图均空。18608在0012、113545在0036存在边界裁切。parallel/branch/depth负例因此仍有未判项，几何守卫通过不等于完整物理安全。没有看到足够证据断言本轮新吞并错误，也没有足够证据将其排除。

出处与完整性：CONFIG SHA256 `bcb3d5e7bf64493888bbf6b29ccbc27d5cdd6d87f52d4ec4258b3764b9f3fbdf`，DECISION SHA256 `7d8a27df4c058abc161983a62b836efa5ec3b27b5c9a819513910c120b8d4eff`；[PARENT_RUN_FROZEN](PARENT_RUN_FROZEN.json)列出的44份source_snapshot全部逐文件匹配，两个只读renderer.py/libjoint.so helper匹配；两臂checkpoint的全部成员、carrier、groups、lineage、solver文件哈希核验通过。采用快照作为出处，不依赖后续latestHEAD。

renderer.py SHA `ce24cd30d663e6f421064d83006f097b02a5cf6a74b20c177a905ca514caed93`；libjoint.so SHA `033a973a71dc5364677a5bf0625f23dc4fe445b70257f04de7cb70cdccca84b0`。原M4 STATE SHA `4f350e3a991c98d7cf011d833be4fc5aebcce1c7d328ae69b39948b5698ec31f`；全部模型/输入绑定见CONFIG。保存GEOMETRY_AUDIT报告原核458490、行序精确、字段前后相同、carrier_geometry_rendered=false。冷载/映射保存先于图像由运行交付记录确认，分析未重新执行数值核验。

父调用形式为批准Python `-B observation_runner.py --config CONFIG.json`，准确路径见[RUN_REQUEST](RUN_REQUEST.json)。测试仅验证实现；真实RED/GREEN及29项通过的回执见[TESTS_RECEIPT](TESTS_RECEIPT.json)，不作为物理成功证据。实际child退出保留，父负责封闭工件seal，本分析不创建包含runtime的SEAL。

下一步只推荐一个实验：**相同模型/观测域/守卫与配对算法，扩大到scan24完整保存overlap图的可处理完整分量**。目前规则确实释放了真实成员变化，而1909分量未覆盖、八例未产生greedy/joint竞争差异；这是覆盖与假设库规模的未知，不能再靠EPS或有限域阈值微调解决。先固定全图分量清单、不得裁竞争叶；每分量≤128，超限/超预算完整记NOT_RUN。沿用已有38模型并精确重放本轮8分量，对新增保存成功配对各恢复一次原拟合并核对历史metrics，不产生新空间候选。共同新库做greedy/MILP，原M4为范围外基线，明确拟合数量增加是覆盖扩展。优先保存全部映射及两全景；展示按实际成员差异去重，固定包含51111/51166、真正新增直/曲组及完整负例。父计算上限1800秒、末600秒交付，1200秒前停止新分量；两臂只比较共同完整处理范围。若无实质可辨直/曲改善，保存负结果并另审候选/共同参数化，不能宣称全局优化成功。具体下一轮仍需父冻结；本分析没有启动该实验。

全部edge身份暂定；无物理真值、独立held-out或全场景parallel/branch/depth安全主张。有限域规则有归属效果，视觉目标尚未达成。
