# Scan65 continuation_001/unit_003：保存输出分析与阶段恢复

结论：运输分支守卫只新增一次小幅接受；整组保核、整条辅助曲线更新、全库最佳选择及重查均有保存证据，但新增实质直线和曲线恢复、第二次连续接受及物理身份尚未成立。RADIAL对照没有接受。当前科学结果不是HISTORY优势实验。

数值进程实际退出0、reason=null，15:11:53.238–15:13:57.932 JST，运行约123.94秒。RUN_RESULT为completed、delivery_gate=true，科学字段原为UNASSESSED。上一分析阶段另有用户明确报告的rc=0、reason=HARD_DEADLINE；本次只恢复分析元数据，不将该失败改写成成功，也不改原始receipt。

## 整组更新、排名与停止

输入为unit002 WHOLE_FINAL，保留279616行、126423 assigned、153193 UNKNOWN、next_version21668。两臂均WHOLE，只有分支方向解释改变：RADIAL使用空间径向有符号方向；TRANSPORT沿拟合有限Q进行最小旋转。这是科学守卫定义变化，不是等价优化；后续可连接库可以不同。

RADIAL五个初始库与上一单元五个末次WHOLE库逐字段相同（排除新增见证字段），零选择，最终全部membership字段等于START。两个策略共10个初始库在晋级前冻结，全部完整。实际RADIAL访问5库/714解释，TRANSPORT访问10库/1422解释，无top-k、无未完成候选晋级。

TRANSPORT唯一事件：64111吸收donor -202122，新增原行202121–202125，版本21553→21668，endpoint/direction0，J=-0.10260256092400954。在38个邻近donor、228个解释中有8个可连接解释，所选J严格最小；最近donor距离仅0.01719p，所选距离1.18834p，故确实不是遇到最近者就停。五轮全成员IRLS处理209核，原204核完整保留。35个若用LOCAL会固定的模板结点实际发生移动，最大0.299039p；旧曲线对应点最大移动0.320926p，固定模板投影对应下fit-only最大0.078316p。它不是只改标签或只动接缝。不同位移量的对应定义不同，不可混为一个指标。

原子TRANSPORT_BRANCH_0001已保存并与最终状态对应；本轮只有一次事件，第一/中间/最后接受实为同一事件，没有虚构中间增长。提交后重进队列，64111再次查询37 donor/222解释，零可连接：139 endpoint_distance、50无注册对应、21 branch_conflict、5 vertex_degeneracy、3 member_distance、2 parallel_conflict、2 tangent_conflict。五组最终均NO_CONNECTABLE_FRAGMENT；156151无邻居，其他组是有邻居但全部解释不合格。没有本轮接受次数上限触发，没有容量、拟合或时间中断。五组范围内自然停止不能等同全场景或研究问题穷尽。

闭合0；新64111端距37.4062p、长度38.6149p，闭合检查明确unsupported。没有将近端点或辅助连接当作支持闭合。

## 分支见证与最早瓶颈

选中解释的RADIAL在第25号中心（Q弧坐标24.68883p）得到3个合格簇：4/4/7个代表，径向跨度3.10784/2.20026/3.42431p；TRANSPORT遍历53个中心后CLEAR。同一候选中心下G与union的RADIAL见证相同；F两策略CLEAR且检查中心0，单独旧G两策略遍历22中心均CLEAR。故触发差异既依赖方向运输，也暴露拟合后Q/采样中心改变的敏感性，不能直接断言是新增donor带来真实第三臂，或旧G早已物理错误。源行见证包括邻域竞争代表，不仅仅是成员行。

初次接受后21个分支拒绝仍阻断续接；另有早期注册、有限端点和几何失败。运输没有解决普遍增长。真实三臂被运输对齐而掩盖仍是核心反例，目前小投影不足以排除。已保存每个达到分支检查的见证及NOT_REACHED前置失败，不以减少拒绝数判定物理进步。

## 支持、贡献与全部背景

|组|START→FINAL核数|本轮接受|最终union / 最长run / 最大gap（p）|本轮起点域外支持代理（p）|
|---|---:|---:|---|---:|
|5558|275→275|0|72.10814 / 54.74844 / .86311|0|
|22130|216→216|0|61.20312 / 61.20312 / 0|0|
|64111|204→209|1|38.59141 / 36.93476 / .023524|2.16519|
|156151|169→169|0|44.04296 / 44.04296 / 0|0|
|238627|368→368|0|122.81324 / 99.82359 / .337659|0|

64111原union/run均36.36726p，现union增2.22415p、最长run只增.56750p；独特donor支持1.65665p，起点域外代理2.16519p，二者定义不同。支持区间[0,1.65665]与[1.68018,38.61493]之间仍有.023524p空洞，不能把union称连续观测。原协方差有限域裁剪4个端点、最大.5p，属于支持记账，不是新观察。全成员最大距离.61049p、最大角38.88669度；通过只是冻结门限内的几何兼容。

64111仍仅一个实质M4来源：旧64111贡献204核/36.93476p，新202121仅5核/1.65665p，不满足12核/2p代理。238627虽有3个实质M4来源和明显弧形，但均继承，不能算本轮新曲线。5558、22130、156151的旧长线亦非本轮成果。先前unit002的48次接受必须与本轮1次分列。

TRANSPORT最终126428 assigned、153188 UNKNOWN。直接核查START/FINAL：仅5行edge_id改变，均UNKNOWN→64111；已归属核损失0、已归属旧身份吸收0、旧组拆分0；279611行标签未变。合并后的64111恰等于原204行并集新增5行。reason/version等派生元数据按事务更新，不宣称所有成员表字段未变。原行序和primitive等来源字段保持。全映射不等于全场景搜索，五种子以外背景未重新竞争。

参考交叉列联（gained/lost/split）：对START为5/0/0；对原M4为293/0/0，其中288为继承；对M3为8085/0/0；对M4前缀unit009为565/0/0；对M4联合unit014为419/144/15。后两项144损失与15拆分在START已存在，不能归因于本轮。scan65没有已执行M5或v06对照，不以ficus/scan24数字代替。v08U11仅是受哈希约束的代码来源；ficus79841保持外部封存证据，本轮没有重跑。

## 实际视觉观察与证据边界

已实际查看下列27张保存PNG。双全景完整呈现颅骨对象、大量相邻线层、UNKNOWN及既有尖刺；并未用源表面遮挡隐藏竞争。64111在0012隔离图只是一小段近竖线，0036是短弯段；新增5核在两视图ADDED_MEMBERS图中近乎微点，无法可靠认定跨片段身份。QUERY_CONTEXT在0012很稀疏，而FULL_OBJECT_CONTEXT显示密集竖向邻层，两者不能互相替代。5558看似直线，22130/156151略弯或近直，238627明显长弧，但本轮均不变。六类负例和三损伤参考的完整背景裁图存在密集平行、交叉及叠层；本次不能仅由颜色宣称消除了错误，也未从小图确证新增错误吸收。

visual_evidence_missing=true指缺决定性可读新增长/排歧证据，并非没有PNG。没有据微点把5核认证为真实续接，也不能把它判成确定误并。所有最终墨迹只来自原核，无辅助桥或gap墨迹；辅助曲线更新不会清除原核既有尖刺，但其被错误纳入身份仍应计为失败。无物理身份、概率、held-out、时间稳定或新颖性认证。

## 工程核查及时间边界

五份完整checkpoint的20个绑定文件哈希核验通过。GEOMETRY_AUDIT前后means/covariance/opacity/原colors/primitive_id/internal_piece_id/arc_t指纹一致；READINESS验证279616行、71227控制点、62356 pieces、8874 parents，basis中心误差0。核冻结与成员精确并集分别有证据，不能从其中一个推断另一个。

CONFIG SHA256 `f344d0f0f3ee6cd6ef968ab4924440660fd1d0c121ffb8083959d2b2e6c198f1`；DECISION `975796041534773f6f90e8f2bd3caaec9f99c43b04fbb9bd4ecbd8c1389381ab`。31份source_snapshot与PARENT_RUN_FROZEN映射逐项一致；两项helper也一致：renderer `ce24cd30d663e6f421064d83006f097b02a5cf6a74b20c177a905ca514caed93`，native lib `033a973a71dc5364677a5bf0625f23dc4fe445b70257f04de7cb70cdccca84b0`。完整来源见[PARENT_RUN_FROZEN.json](PARENT_RUN_FROZEN.json)，不使用旧U12 WIP。BUILD测试rc0只支持工程接口，不能证明真实分支身份。

初始四文件曾于06:18:00 UTC写出，随后补核查；上一分析阶段仍按实际HARD_DEADLINE失败保留，本次是显式metadata恢复。未重跑、拟合、渲染或修改source/config/旧单元，无包装。

下一步：当前已过2026-11-02 15:15停新单元界限：本窗口只完成保存证据交接，不启动新science。下一另行授权并冻结的实验应针对64111这8个曾可连接解释和接受后21个分支拒绝，在共同固定弧长锚点记录G/F/union的逐中心同一邻域见证，配合预先绑定、投影尺度足够的真实标定双视图，比较当前TRANSPORT与独立第三臂对应确认；保持整组WHOLE、完整候选及J，禁止把曲线自身对齐或放宽角度当第三臂排除证据。当前NOT_RUN，不宣称整个研究问题耗尽。

实际查看图像：

- [scenes/scan65/stages/TRANSPORT_BRANCH_FINAL/0012_FULL.png](scenes/scan65/stages/TRANSPORT_BRANCH_FINAL/0012_FULL.png)
- [scenes/scan65/stages/TRANSPORT_BRANCH_FINAL/0036_FULL.png](scenes/scan65/stages/TRANSPORT_BRANCH_FINAL/0036_FULL.png)
- [scenes/scan65/diagnostics/238627/TRANSPORT_BRANCH_0036_ISOLATED_CROP.png](scenes/scan65/diagnostics/238627/TRANSPORT_BRANCH_0036_ISOLATED_CROP.png)
- [scenes/scan65/diagnostics/238627/TRANSPORT_BRANCH_0036_FULL_OBJECT_CONTEXT_CROP.png](scenes/scan65/diagnostics/238627/TRANSPORT_BRANCH_0036_FULL_OBJECT_CONTEXT_CROP.png)
- [scenes/scan65/diagnostics/64111/TRANSPORT_BRANCH_0036_ISOLATED_CROP.png](scenes/scan65/diagnostics/64111/TRANSPORT_BRANCH_0036_ISOLATED_CROP.png)
- [scenes/scan65/diagnostics/64111/TRANSPORT_BRANCH_0036_QUERY_CONTEXT_CROP.png](scenes/scan65/diagnostics/64111/TRANSPORT_BRANCH_0036_QUERY_CONTEXT_CROP.png)
- [scenes/scan65/diagnostics/64111/TRANSPORT_BRANCH_0036_FULL_OBJECT_CONTEXT_CROP.png](scenes/scan65/diagnostics/64111/TRANSPORT_BRANCH_0036_FULL_OBJECT_CONTEXT_CROP.png)
- [scenes/scan65/diagnostics/64111/START_0012_ISOLATED_CROP.png](scenes/scan65/diagnostics/64111/START_0012_ISOLATED_CROP.png)
- [scenes/scan65/diagnostics/64111/TRANSPORT_BRANCH_0012_ISOLATED_CROP.png](scenes/scan65/diagnostics/64111/TRANSPORT_BRANCH_0012_ISOLATED_CROP.png)
- [scenes/scan65/diagnostics/64111/TRANSPORT_BRANCH_0012_ADDED_MEMBERS_CROP.png](scenes/scan65/diagnostics/64111/TRANSPORT_BRANCH_0012_ADDED_MEMBERS_CROP.png)
- [scenes/scan65/diagnostics/64111/TRANSPORT_BRANCH_0036_ADDED_MEMBERS_CROP.png](scenes/scan65/diagnostics/64111/TRANSPORT_BRANCH_0036_ADDED_MEMBERS_CROP.png)
- [scenes/scan65/diagnostics/64111/TRANSPORT_BRANCH_0012_FULL_OBJECT_CONTEXT_CROP.png](scenes/scan65/diagnostics/64111/TRANSPORT_BRANCH_0012_FULL_OBJECT_CONTEXT_CROP.png)
- [scenes/scan65/diagnostics/5558/TRANSPORT_BRANCH_0012_ISOLATED_CROP.png](scenes/scan65/diagnostics/5558/TRANSPORT_BRANCH_0012_ISOLATED_CROP.png)
- [scenes/scan65/diagnostics/5558/TRANSPORT_BRANCH_0036_FULL_OBJECT_CONTEXT_CROP.png](scenes/scan65/diagnostics/5558/TRANSPORT_BRANCH_0036_FULL_OBJECT_CONTEXT_CROP.png)
- [scenes/scan65/diagnostics/negative_branch/TRANSPORT_BRANCH_0036_FULL_OBJECT_CONTEXT_CROP.png](scenes/scan65/diagnostics/negative_branch/TRANSPORT_BRANCH_0036_FULL_OBJECT_CONTEXT_CROP.png)
- [scenes/scan65/diagnostics/negative_parallel/TRANSPORT_BRANCH_0036_FULL_OBJECT_CONTEXT_CROP.png](scenes/scan65/diagnostics/negative_parallel/TRANSPORT_BRANCH_0036_FULL_OBJECT_CONTEXT_CROP.png)
- [scenes/scan65/diagnostics/64111/TRANSPORT_BRANCH_0012_QUERY_CONTEXT_CROP.png](scenes/scan65/diagnostics/64111/TRANSPORT_BRANCH_0012_QUERY_CONTEXT_CROP.png)
- [scenes/scan65/diagnostics/64111/START_0036_ISOLATED_CROP.png](scenes/scan65/diagnostics/64111/START_0036_ISOLATED_CROP.png)
- [scenes/scan65/diagnostics/22130/TRANSPORT_BRANCH_0036_ISOLATED_CROP.png](scenes/scan65/diagnostics/22130/TRANSPORT_BRANCH_0036_ISOLATED_CROP.png)
- [scenes/scan65/diagnostics/156151/TRANSPORT_BRANCH_0036_ISOLATED_CROP.png](scenes/scan65/diagnostics/156151/TRANSPORT_BRANCH_0036_ISOLATED_CROP.png)
- [scenes/scan65/diagnostics/negative_crossing_tangent/TRANSPORT_BRANCH_0036_FULL_OBJECT_CONTEXT_CROP.png](scenes/scan65/diagnostics/negative_crossing_tangent/TRANSPORT_BRANCH_0036_FULL_OBJECT_CONTEXT_CROP.png)
- [scenes/scan65/diagnostics/negative_gap/TRANSPORT_BRANCH_0036_FULL_OBJECT_CONTEXT_CROP.png](scenes/scan65/diagnostics/negative_gap/TRANSPORT_BRANCH_0036_FULL_OBJECT_CONTEXT_CROP.png)
- [scenes/scan65/diagnostics/negative_ambiguity/TRANSPORT_BRANCH_0036_FULL_OBJECT_CONTEXT_CROP.png](scenes/scan65/diagnostics/negative_ambiguity/TRANSPORT_BRANCH_0036_FULL_OBJECT_CONTEXT_CROP.png)
- [scenes/scan65/diagnostics/negative_accepted_worst_margin/TRANSPORT_BRANCH_0036_FULL_OBJECT_CONTEXT_CROP.png](scenes/scan65/diagnostics/negative_accepted_worst_margin/TRANSPORT_BRANCH_0036_FULL_OBJECT_CONTEXT_CROP.png)
- [scenes/scan65/diagnostics/damage_167509/TRANSPORT_BRANCH_0036_FULL_OBJECT_CONTEXT_CROP.png](scenes/scan65/diagnostics/damage_167509/TRANSPORT_BRANCH_0036_FULL_OBJECT_CONTEXT_CROP.png)
- [scenes/scan65/diagnostics/damage_7786/TRANSPORT_BRANCH_0036_FULL_OBJECT_CONTEXT_CROP.png](scenes/scan65/diagnostics/damage_7786/TRANSPORT_BRANCH_0036_FULL_OBJECT_CONTEXT_CROP.png)
- [scenes/scan65/diagnostics/damage_120042/TRANSPORT_BRANCH_0036_FULL_OBJECT_CONTEXT_CROP.png](scenes/scan65/diagnostics/damage_120042/TRANSPORT_BRANCH_0036_FULL_OBJECT_CONTEXT_CROP.png)
