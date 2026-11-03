# unit009：新六组连续增长，保核与排序成立，身份及停止范围仍有限

实际数值子进程rc=0、reason=null，04:30:59.782435至04:41:12.644917；RUN_RESULT=partial。readiness26.91秒、初始库15.84秒、增长452.21秒、交付117.11秒。增长阶段450秒预算耗尽；不是容量、quota或物理无连接证明。完成74次接受、76个完整checkpoint（起点+74事务+终态）、两视图原核全景和诊断；末态等于第74次提交，next_version21782。

从相同START比较：279616行保持，assigned126616→127016、UNKNOWN153000→152600。947个donor成员改变身份，其中400来自UNKNOWN、547原本已归属；lost0、旧组split0。1799历史事件及旧五组完整成员均保留，不能计入本轮。新六组均READY，3670项选择账本产生4条line和10条polyline合格项，6选中/8未选；polyline标签不认证曲率。

每次事务均核对完整库最低J（含donor/关系/方向平局）、donor行恰为新增行、旧成员全留、拟合证据G/F各半、五轮IRLS权重、最终Q等于保存候选、顺序版本；304个checkpoint文件哈希一致，78份冻结源码与helper绑定核验通过。旧区fit-only移动范围0.06215–1.29443p，证明整组辅助模型实际调整；GEOMETRY_AUDIT七数组前后哈希一致、原行序不变。没有重拟合、重跑或新渲染。

|组|接受|起点→末态核数|动态union/run/gap(p)|M4实质贡献数|动态域外代理(p)|固定起点新增内部支持(p)|
|---|---:|---:|---|---:|---:|---:|
|13285|15|72→188|52.096/52.096/0.000|3|27.978|0.410|
|30579|16|99→596|135.014/135.014/0.000|5|110.409|0.125|
|84607|16|55→190|52.054/50.825/0.075|6|34.704|0.000|
|136538|8|75→116|30.386/30.386/0.000|2|7.033|0.339|
|162227|3|83→95|26.703/26.703/0.000|1|2.069|0.491|
|233067|16|45→191|35.806/35.806/0.000|6|21.538|0.000|

这些动态域外值由已拟合Q和原起点在其上的投影定义，仍是代理。固定有限起点裁剪只能测内部填充：30579只新增0.125p内部支持，却有135.014p动态run；并不能把差值当实测新曲线长度。13285/84607/233067也存在大量端点裁剪；extended_s仅方向代理。74次中8次U=0池化，并非全部只有池化；原核影像确实可见30579从很短起点变为较长细线，但双视图身份尚未确认。

规则2/4/6继续关闭，未改变阈值或硬恢复。17次接受带平行对，首次第30步30579←-274295（10核），对30422/274294；这是潜在平行身份吸收，不能仅凭谓词称已证实错误。第62步84607←-33638（3核）使已接受行214901的方向偏差达83.06°，伤的是旧成员；四次事件超过75°，没有距离超过1.5p。第72步30579←-30821（10核）出现非局部接触距离0.49107p，仍以有限J=.06134870接受。相同donor重叠解释可连接但J=.07514767；另一donor67269无接触纯池化解释J=.06347362。没有闭合认证。这个低分端点选择保留为明确表示/排序反例，不能用最终连续支持掩盖。

中断库0097_30579：83个donor，457条记录，其中最后一条未完成；当前67315及其后共7个donor未完成，已保存部分有47个vertex_degeneracy、1个branch_conflict，零可连接不等于全库零可连接，未晋级截断赢家。0096_13285的完整30解释无可连接；0093_136538、0094_162227当时完整空邻域；84607/233067接受后尚未完成下一轮。STOP只保留最新13285无连接，不得把六组或整个窗口称为穷尽。零支持闭合、零因接受次数上限停止。

实际看图：两幅777×581全景保留完整对象与原尖刺；30579起点短段、中期长段及新增原核均可见，0012竞争框含多条邻近斜线，0036框触及底边。84607在0012显出弯折小弧，0036更接近短直段；13285在0036仅32像素墨迹，不能作为双视图实质曲线成功。162227保存收据显示0036仅13墨迹像素，未把它当可辨成功。旧parallel背景仍展示紧邻线，保持负例。原核冻结、没有源表面遮挡或辅助桥墨；局部颜色连贯不能排除不同深度或第三臂，未作物理/held-out/时间稳定认证。

参考contingency：相对M4原强基线，START gain481/loss0、末态gain881/loss0，新增400；相对M3，8273→8673 gain、loss0。相对unit014联合参考，START gain607/loss144/split15，末态1007/144/15；这144核差异和15拆分在本轮起点已存在，不是新增损失。同理unit004/005/006不同历史分支各118/104/20核相对损失及2拆分是继承差异。scan65不存在已执行M5/v06匹配对照；不假造。ROW_FIT仅同状态完整影子库，旧17步rollout为历史、非新六组匹配实验，不能声称拟合优越性。

下一单元建议：下一次只读review应优先冻结针对第72步的有限软排序对照，而非仅给末库追加时间：从本单元GROUP_BALANCED_FIT_0071共同冷载，仅激活30579，完整保留其余十个跟踪组和全部背景；原J对照与J_contact=J+0.01*I(原ARC自接触诊断为true)两臂，各300秒增长，先重放0091_30579完整510解释/40可连接库。只改有限软评分，所有[2,4,6]仍关闭，contact候选仍可胜出并接受，无新硬门；WHOLE、组均衡拟合、完整2p候选、规则1/3/5和闭合认证不变。保存两影子赢家、后续急折拒绝、同donor重叠/端点竞争、已接受行214901损伤和原核双视图完整竞争背景；不能用多池化冒充更好延伸。该提案须下一review再冻结；当前NOT_RUN。原74步终态与截断末库全部保留，不撤销。05:15停新单元、05:35停science。

实际查看PNG（未打包）：

- [scenes/scan65/stages/GROUP_BALANCED_FIT_FINAL/0012_FULL.png](scenes/scan65/stages/GROUP_BALANCED_FIT_FINAL/0012_FULL.png)
- [scenes/scan65/diagnostics/30579/GROUP_BALANCED_FIT_0012_ISOLATED_CROP.png](scenes/scan65/diagnostics/30579/GROUP_BALANCED_FIT_0012_ISOLATED_CROP.png)
- [scenes/scan65/diagnostics/30579/GROUP_BALANCED_FIT_0012_FULL_OBJECT_CONTEXT_CROP.png](scenes/scan65/diagnostics/30579/GROUP_BALANCED_FIT_0012_FULL_OBJECT_CONTEXT_CROP.png)
- [scenes/scan65/diagnostics/30579/GROUP_BALANCED_FIT_0036_ISOLATED_CROP.png](scenes/scan65/diagnostics/30579/GROUP_BALANCED_FIT_0036_ISOLATED_CROP.png)
- [scenes/scan65/worst_events/GROUP_BALANCED_FIT/0072/0012_ISOLATED_CROP.png](scenes/scan65/worst_events/GROUP_BALANCED_FIT/0072/0012_ISOLATED_CROP.png)
- [scenes/scan65/worst_events/GROUP_BALANCED_FIT/0072/0012_FULL_OBJECT_CONTEXT.png](scenes/scan65/worst_events/GROUP_BALANCED_FIT/0072/0012_FULL_OBJECT_CONTEXT.png)
- [scenes/scan65/stages/GROUP_BALANCED_FIT_FINAL/0036_FULL.png](scenes/scan65/stages/GROUP_BALANCED_FIT_FINAL/0036_FULL.png)
- [scenes/scan65/diagnostics/84607/GROUP_BALANCED_FIT_0012_ISOLATED_CROP.png](scenes/scan65/diagnostics/84607/GROUP_BALANCED_FIT_0012_ISOLATED_CROP.png)
- [scenes/scan65/diagnostics/84607/GROUP_BALANCED_FIT_0036_ISOLATED_CROP.png](scenes/scan65/diagnostics/84607/GROUP_BALANCED_FIT_0036_ISOLATED_CROP.png)
- [scenes/scan65/diagnostics/84607/GROUP_BALANCED_FIT_0036_FULL_OBJECT_CONTEXT_CROP.png](scenes/scan65/diagnostics/84607/GROUP_BALANCED_FIT_0036_FULL_OBJECT_CONTEXT_CROP.png)
- [scenes/scan65/diagnostics/13285/GROUP_BALANCED_FIT_0012_ISOLATED_CROP.png](scenes/scan65/diagnostics/13285/GROUP_BALANCED_FIT_0012_ISOLATED_CROP.png)
- [scenes/scan65/diagnostics/13285/GROUP_BALANCED_FIT_0036_ISOLATED_CROP.png](scenes/scan65/diagnostics/13285/GROUP_BALANCED_FIT_0036_ISOLATED_CROP.png)
- [scenes/scan65/diagnostics/30579/START_0012_START_MEMBERS_CROP.png](scenes/scan65/diagnostics/30579/START_0012_START_MEMBERS_CROP.png)
- [scenes/scan65/diagnostics/30579/GROUP_BALANCED_FIT_MID_0012_ISOLATED_CROP.png](scenes/scan65/diagnostics/30579/GROUP_BALANCED_FIT_MID_0012_ISOLATED_CROP.png)
- [scenes/scan65/diagnostics/30579/GROUP_BALANCED_FIT_0012_ADDED_MEMBERS_CROP.png](scenes/scan65/diagnostics/30579/GROUP_BALANCED_FIT_0012_ADDED_MEMBERS_CROP.png)
- [scenes/scan65/diagnostics/84607/GROUP_BALANCED_FIT_0012_FULL_OBJECT_CONTEXT_CROP.png](scenes/scan65/diagnostics/84607/GROUP_BALANCED_FIT_0012_FULL_OBJECT_CONTEXT_CROP.png)
- [scenes/scan65/diagnostics/13285/GROUP_BALANCED_FIT_0036_FULL_OBJECT_CONTEXT_CROP.png](scenes/scan65/diagnostics/13285/GROUP_BALANCED_FIT_0036_FULL_OBJECT_CONTEXT_CROP.png)
- [scenes/scan65/diagnostics/negative_parallel/GROUP_BALANCED_FIT_0012_FULL_OBJECT_CONTEXT_CROP.png](scenes/scan65/diagnostics/negative_parallel/GROUP_BALANCED_FIT_0012_FULL_OBJECT_CONTEXT_CROP.png)

完整逐步审计：[SAVED_OUTPUT_AUDIT.json](SAVED_OUTPUT_AUDIT.json)。本报告只分析保存结果；下一提案未运行。
