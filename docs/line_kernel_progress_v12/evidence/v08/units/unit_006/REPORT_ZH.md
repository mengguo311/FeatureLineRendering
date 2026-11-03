# unit006：扩展种子队列后的局部续接，科学结论仍为PARTIAL

实际子进程rc=0、reason=null，01:45:38至01:47:43 JST；RUN_RESULT交付门通过，fit_calls=0。工程执行完成不等于科学假设成立。BASE仅新增一次接受，HISTORY零接受；没有第二次新增接受，没有新实质曲线恢复。此分析仅读取保存结果和PNG，未运行拟合、渲染或修改源码/配置。

队列由13条line、7条polyline新增种子及4条原种子组成，共24种子/48初始端口。新增种子全部ready；没有按生长结果补选。3543条GROUPS中3471无endpoint事件、48不满足M4贡献、4已占用，20入选；每类16上限没有淘汰合格者，另61条事件输出缺保存GROUPS。全285956行导出，但只搜索该预选队列，不是全场景生长。新增种子保护改变了相对unit005的donor集合，不能把跨单元差异仅归于覆盖量。见[队列](scenes/ficus/COHORT_SELECTION.json)、[初始库](scenes/ficus/INITIAL_LIBRARY_FREEZE.json)。

**用户先验的实际检验。** 47个初始端口没有共同合格者；仅230214-side0存在一项。BASE访问49状态、HISTORY48；不是预算或256前缀容量终止。两臂同状态影子选择显示：BASE接入54189/v20328，HISTORY拒绝。首gap=1.405578p，端口切向28.609564°，连接角17.400974°/24.654022°；全成员max残差0.234420p、q95=0.210669p、最大切向26.933673°。HISTORY预测角26.100612°超过15°，曲率差约1.82e-14。因此这里是两段各自近直、彼此有转向，拒绝来自预测角而非曲率变化项。不能据唯一自筛选案例估计“成功后更可能成功”的物理概率，也不能由多分配17核断言HISTORY错了。见[BASE接受访问](scenes/ficus/visits/BASE/0042.json)。

本轮一次新事件使230214从32核/8 seedlets变为49核/12 seedlets，全部17新增核原为UNKNOWN，没有已分配核被撤回或重分配。新版本20582，next_version20583；原两条历史事件仅继承，不计本轮接受。HISTORY完整成员字段保持起点。此方法实际保护原叶成员，不是v07自由拆分方法；CONFIG范围声明不改变这一事实。

|230214统计，单位p|起点/HISTORY|BASE|
|---|---:|---:|
|去重支持union|6.265153|8.846750|
|最长连续支持|0.846478|2.581598|
|最大无支持gap|0.268361|1.405578|
|总gap|1.821023|3.226601|
|辅助有限长度|8.086175|12.073351|
|相对本轮起点新增域外支持|0|2.581598|

新增映射支持主要是向外延伸，内部填充约零；但有限长度增加3.987176p包含1.405578p无支持连接段，不能称为观测增长。连接段不渲染。M4贡献54189=13核/2.287545p、230214=16/3.208488p、230230=16/3.071094p达到12核/2p，230201=4/0.785159p未达到。三个合格M4贡献并不能弥补域外支持不足4p或曲线视觉缺失。原source-parent仅9210=41核/8.146632p为实质来源，2074=8核/1.764315p不足；不能当多独立来源长曲线恢复。

**接受后确实重新访问前沿，但死端仍在。** 230214新前沿最近54197的有限投影距离0.138401p，端点距离0.201094p；轴夹角14.349748°，连接角145.192806°/130.884064°显示端点关系反向。改走本轮已有重叠关系，固定blend窗口仅0.145889p，完整成员最大残差0.536066p、q95=0.379789p合格，切向53.355854°失败。96009也有切向43.056374°失败。不能放宽连接角硬接；局部接缝参数化是否制造了失败是下一轮可证伪问题，尚未证明。见[接受后死端](scenes/ficus/visits/BASE/0048.json)。候选拒绝发生在提交前，没有真实失败事务回滚事件可据此宣称回滚科学验证。

保存的BASE_000/HISTORY_000/BASE_001/BASE_FINAL/HISTORY_FINAL检查点文件哈希已核对，初始成员字段与NO_FURTHER_GROWTH一致；最后有效接受为BASE_001，最终保留其17核变化。几何审计报告原核未变。原核不消除原尖刺，灰UNKNOWN也未被删掉。

**双视图与反例。** 全景保留完整植株/花盆和侧向长尖刺，未看出整体结构改善。230214在两视图只是很小的近直斜条；同核基线灰尾变为组色，支持归属变化但不足证明深度一致或HISTORY误拒。

![BASE完整视图1](scenes/ficus/stages/BASE_FINAL/test_r_1_FULL.png)
![BASE完整视图79](scenes/ficus/stages/BASE_FINAL/test_r_79_FULL.png)

同核起点、BASE与竞争上下文：
![起点230214](scenes/ficus/diagnostics/230214/NO_FURTHER_GROWTH_test_r_1_ISOLATED_CROP.png)
![BASE230214](scenes/ficus/diagnostics/230214/BASE_test_r_1_ISOLATED_CROP.png)
![BASE另一视图及上下文](scenes/ficus/diagnostics/230214/BASE_test_r_79_CONTEXT_CROP.png)

230214保存49成员核、211上下文核，包含查询竞争者，但SCOPE明确physical_context_complete=false。92122的细长条、26025的小弯斜条以及8820直段均继承；本轮这些成员没有变化。浮点级域外量不作增长。92122支持union22.710948p、最长段1.804386p，也不能以union声称连续长曲线。
![继承曲线92122](scenes/ficus/diagnostics/92122/BASE_test_r_1_ISOLATED_CROP.png)
![92122另一视图上下文](scenes/ficus/diagnostics/92122/BASE_test_r_79_CONTEXT_CROP.png)

四负例11/80709、16931/18768、112/205435、33117/201172均实际看了保存上下文，但图极小，平行/分支/深度判断未解决，不认定安全通过。无源表面遮挡、无辅助墨迹；完整observed_images见FAILURE_ANALYSIS。已有图但有效物理反例证据不足，因此visual_evidence_missing=true明确指证据充分性，不是声称缺PNG。
[负例1](scenes/ficus/diagnostics/negative_11_80709/BASE_test_r_1_CONTEXT_CROP.png)；
[负例2](scenes/ficus/diagnostics/negative_16931_18768/BASE_test_r_79_CONTEXT_CROP.png)；
[负例3](scenes/ficus/diagnostics/negative_112_205435/BASE_test_r_1_CONTEXT_CROP.png)；
[负例4](scenes/ficus/diagnostics/negative_33117_201172/BASE_test_r_79_CONTEXT_CROP.png)。

**成员交叉表。** 下表取保存统计与成员比较；新增/撤回基于assigned状态，拆分基于旧组成员交叉表，不能用ID重编号代替。不同参考彼此独立，绝不相加为累计效果。v06撤回/拆分主要已存在于起点，不归因本轮17核。

|参考|BASE新增/撤回/旧组拆分|HISTORY新增/撤回/旧组拆分|
|---|---:|---:|
|本轮unit005起点|17 / 0 / 0|0 / 0 / 0|
|v05 M5|39 / 0 / 0|22 / 0 / 0|
|v05 M4|3534 / 0 / 0|3517 / 0 / 0|
|v06 overlap|1942 / 1821 / 184|1925 / 1821 / 184|
|v06 common|2318 / 174 / 12|2301 / 174 / 12|

BASE assigned122004、UNKNOWN163952；HISTORY121987、163969。与M5对应的标签变化行数75/58、与v06 overlap为6390/6373、common4249/4232是诊断，不是准确率。四原种子本轮无新接受，64355/137016旧增长不重复记账。依据[BASE统计](scenes/ficus/stages/BASE_FINAL/METRICS.json)及[HISTORY统计](scenes/ficus/stages/HISTORY_FINAL/METRICS.json)。

下一步建议另行冻结局部有限接缝参数化对照，保留原固定blend、相同候选/背景和BASE/HISTORY，检查54197等完整竞争者。保持接缝外曲线、全部原核、有限域及几何阈值；不把最近者当真值，不扫半径、角度或拟合预算。若新接缝仍全成员失败或吸收平行/深度/分支，就保存负结果。本轮没有执行该新机制；07:15前仍可另立科学单元，07:38停止数值。

溯源：CONFIG SHA256=f65f359bddae63265b32f7ed24354aba47527676b43a4d1fbda4b86ab6cdc8cf；DECISION SHA256=3cffdbe4bf4b60f0e7b65f9591c6c923f8723c39a62939fdbf30142c55075f11。原RUN_RESULT、父级实际EXIT、source_snapshot/helper绑定均保留，父级负责封存。本轮不声称物理真值、held-out、时间稳定性或准确率。


元数据恢复说明：本次用户指令报告上一轮rc=0、reason=HARD_DEADLINE，此事实独立保存在STATUS与FAILURE_ANALYSIS。磁盘COMPUTE_EXIT仍记录数值子进程rc=0、reason=null；未覆盖或混同两个退出记录。四份JSON/报告接口已核对，18条实际看过的PNG路径及报告相对链接均存在。只做元数据恢复，没有科学重跑。
