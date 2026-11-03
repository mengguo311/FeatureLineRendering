# Scan24：整组最佳下一碎片聚合的保存输出分析

工程机制已实际运行并得到保存状态支持；科学结论为 **PARTIAL：直边重复外延可辨，新的完整曲边身份与WHOLE物理优越性尚未建立**。不是HISTORY优劣试验，也不是只改标签或局部接缝。

实际子进程于2026-11-02 13:58:47启动、14:19:37结束，returncode=0、reason=null；RUN_RESULT记录耗时1249.20秒、completed。两臂均导出458490原行映射、原生0012/0036全景和诊断图，共1020张保存PNG。本分析实际查看32张，未声称逐张检查全部图片。四份必需元数据在分析开始约61秒已写入，再补充只读审计。未重新拟合、渲染或修改源码/CONFIG。

## 实际主循环与原核不变量

核验94个checkpoint及其376个文件哈希，91次接受的完整成员映射、版本和原子保存阶段。每一步的新组恰好等于旧组与donor的原行并集，未漏核或额外添核；下一次选择确实重新进入循环。原行序、primitive_id及保存来源/代表/旧标签字段核验通过；原Gaussian的means、covariance、opacity、canonical colors、primitive_id、internal_piece_id、arc_t逐字段哈希与GEOMETRY_AUDIT及原输入一致。显示颜色另存；最终墨迹只有原核，无辅助桥、填缝或源表面遮挡。

WHOLE的49/49次接受均在LOCAL原本固定的模板区域发生结点位移，最大0.564671p；LOCAL的42/42次该区域精确不变。保存拟合记录为五轮IRLS/LSQR，接受记录成员数与完整并集一致，冻结源码以这些完整行输入拟合。这是已有段共同调整的实际证据，不能把较低拟合误差解释为物理正确。

|臂|接受次数|各种子次数：53254/132977/200509/201906/202023/210790|完整库|解释记录|已有assigned组被整体吸收|
|---|---:|---|---:|---:|---:|
|LOCAL|42|12 / 10 / 11 / 3 / 1 / 5|78|27708|22|
|WHOLE|49|18 / 11 / 11 / 3 / 1 / 5|114|47844|20|

保存库中每个邻居均有六种注册/接续解释；192个库均complete、无未尝试donor。91/91次选择符合全部可接通解释的score及规定平局顺序。91次所选都不是精确距离最近donor；其中LOCAL37、WHOLE39次最近donor没有可接通解释但仍选择了别的donor。此处核验的是保存库和冻结枚举实现，没有在分析中重算全场景空间邻接。

首/中/末谱系亦一致：LOCAL为53254←53114、132977←5764、53254←UNKNOWN载体12657；WHOLE为53254←185632、53254←UNKNOWN载体53318、53254←UNKNOWN载体12663。所有完整接受状态保留。没有运行中失败事务需要声称回滚成功；被拒候选未改状态，最后有效状态就是FINAL。

两臂六种子均以完整库无可接通者停止；支持闭合0、容量/拟合/时间中断0。不是8次上限，也不是空查询：WHOLE最后六组仍分别有198/170/78/12/3/11个邻居。53254的重叠解释主要受vertex_degeneracy阻断，132977/200509主要gross_tangent_conflict，201906主要parallel_conflict；另有接续端距失败和无注册对应。上述是冻结规则下的范围内死端，不等于不存在真实续接或研究窗口耗尽。

## 覆盖、旧组得失与重分组

|状态|assigned|UNKNOWN|相对START/M5新增|丢失|起点旧组拆分|
|---|---:|---:|---:|---:|---:|
|START=M5|259758|198732|0|0|0|
|LOCAL|259930|198560|172|0|0|
|WHOLE|259985|198505|227|0|0|

LOCAL标签变化1768行，其中1596行为原assigned组整体合并后的改号；WHOLE变化1807行，其中1580行为原assigned改号。数字ID改变不作为独立身份发现。此示踪保护完整已接受组，确实发生整体吸收与UNKNOWN激活，未发生自由核撤回或旧组拆分。未搜索背景保持M5；全行导出不等于全场景搜索。保留UNKNOWN及其原始原因，不将其隐藏或视作已解决。

相对M4，START已继承+13409/-0；LOCAL最终+13581/-0，WHOLE+13636/-0。相对v06 greedy/joint，START已是+10901/-1231及81组拆分；LOCAL最终+11073/-1231，WHOLE+11128/-1231。独立比较确认最终丢失的1231行及81个拆分组的具体集合与START相同，不能算本轮新损伤或本轮新修复。ficus79841及v08U11仅是外部封存来源证据，没有在scan24重跑或把其差异累加为新收益。

## 实际看图、支持与限制

两固定视图全对象可辨，建筑立边、窗格和弯檐及其他深度层都在。完整对象context确实来自全行FULL图裁剪；QUERY_CONTEXT另存，不能替代完整投影背景。所有同框ISOLATED采用最终目标行并集，所以START同框图也包含未来候选行的旧颜色；它不是“起点已拥有全部这些行”的证据。判断实际增长使用单独START_MEMBERS与ADDED_MEMBERS图和行集。

53254从190核增长为LOCAL672/WHOLE685核。WHOLE双视图分别呈细长立边和斜向长边；START_MEMBERS与ADDED_MEMBERS显示沿同一投影边的显著新增范围，具备真实直边外延证据。两视图完整背景中仍有多条邻近平行轮廓，不能据单色认证深度身份。200509从111到990核，在两视图均为长立边，属于实质多片段直线候选；周围尖刺/交叉原核依然可见，未因着色被清除。

201906从282到339核、三次接受，双视图仍是短弯檐。M4实质贡献从两项增到三项：34核/9.515p、248核/41.613p、46核/10.861p；另11新增核不满足同样实质贡献代理。新增第三片段并非只有一两个核，但整个弧仍主要继承248核来源，ADDED_MEMBERS仅见较短/稀疏增量。它支持局部曲边续接，不足以宣称新的完整曲线恢复。210790从159到200核、四实质贡献，但0036看起来近直，polyline标签不是物理弯曲认证。202023从100到113核、第三贡献13核/4.547p，0012完全无墨迹，不能通过双视图判据。

|WHOLE组|核数|实质M4贡献数|支持union p|最长连续run p|最大gap p|相对起点域外代理p|
|---|---:|---:|---:|---:|---:|---:|
|53254|685|10|188.462|86.218|0.227|131.700|
|132977|529|9|147.615|55.614|0.495|91.883|
|200509|990|13|184.367|89.025|0.841|152.929|
|201906|339|3|63.709|53.142|0.081|13.605|
|202023|113|3|41.142|36.595|0.190|5.019|
|210790|200|4|42.304|26.283|0.389|9.857|

上述贡献数与≥4p域外是报告代理，不是接受门或真值。support union不是连续长度，域外由旧曲线投影到新坐标域计算，受整曲线重参数化影响；独特支持也可能填充内部洞，不能把每个接受或每个新增核全算外延。53254 WHOLE域外131.700p比LOCAL92.854p大，但WHOLE仅10个实质M4来源、LOCAL14个，说明接受路径不同，不是简单在LOCAL基础上继续追加。132977 WHOLE最长run55.614p还小于LOCAL64.809p，不能只报增加的union而省略连续性损失。

固定负例全部保留。84842/362883、153248/377058的完整背景显示密集立边/窗格，隔离对象很小；153427/153430只有6核、双视图各4个墨迹像素，301451/301459的10核双视图均空白。因此visual_evidence_missing=true有具体原因，不能以非空背景图假称目标负例可辨。现有图片未提供足以认定某次新增吞并平行/分支/深度结构的确定证据，也未排除这类错误；原已错误的完整donor在monotone union协议中不能拆除。保留全部拒绝和替代解释，不作安全或物理认证。

## 诊断与下一步

最早剩余瓶颈是种子队列的几何形态/可观测性和曲边完整性证据，不是主循环仍被次数上限或HISTORY冻结。WHOLE与LOCAL仅可移动范围不同，但接受后候选和轨迹确实分叉；相对v08则候选、表达与接通机制共同改变，不能作历史条件单因素优越性归因。

下一单元优先只读审计scan65的强M5全行背景和原生双视图，再冻结同一LOCAL/WHOLE协议迁移。种子选择从仅按line/polyline标签及支持长度，改为预先核验实际有限q转弯和两视图可辨的固定直/曲队列；在任何增长前冻结ID/版本及全部排除清单，保留不可辨组为负例。匹配对照仍仅改变可移动结点范围，半径、排名、成员并集、接通守卫、预算均不变。若scan65缺成熟可加载背景或可辨曲线，则该迁移NOT_READY，另审查本轮201906等死端的具体替代解释；不得增半径、放角度或恢复HISTORY。

下一单元仍须新的只读评审及冻结决定；当前没有启动scan65或任何新科学。15:15停新单元、15:38停science、15:45交接、16:00硬截止仍有效；没有旧08:00停止条件。无physical identity、held-out、时间稳定性、概率或新颖性认证。

审计明细见[ANALYSIS_EVIDENCE.json](ANALYSIS_EVIDENCE.json)，包含94个checkpoint、所有选择/成员审计、逐类拒绝和首中末事件。CONFIG SHA256为f165be882ffcadc4bf94a7b89e98e4a5b40cef94fe8e5afff10256117999df99；20份实际父快照及两个原生helper哈希核验通过，DECISION绑定精确。旧源码、输入、失败单位及当前科学输出均未改写。

实际查看的32张保存图（所有路径相对本单位）：

- [scenes/scan24/stages/WHOLE_FINAL/0012_FULL.png](scenes/scan24/stages/WHOLE_FINAL/0012_FULL.png)
- [scenes/scan24/stages/WHOLE_FINAL/0036_FULL.png](scenes/scan24/stages/WHOLE_FINAL/0036_FULL.png)
- [scenes/scan24/diagnostics/53254/WHOLE_0012_ISOLATED_CROP.png](scenes/scan24/diagnostics/53254/WHOLE_0012_ISOLATED_CROP.png)
- [scenes/scan24/diagnostics/53254/WHOLE_0012_FULL_OBJECT_CONTEXT_CROP.png](scenes/scan24/diagnostics/53254/WHOLE_0012_FULL_OBJECT_CONTEXT_CROP.png)
- [scenes/scan24/diagnostics/201906/WHOLE_0036_ISOLATED_CROP.png](scenes/scan24/diagnostics/201906/WHOLE_0036_ISOLATED_CROP.png)
- [scenes/scan24/diagnostics/201906/WHOLE_0036_FULL_OBJECT_CONTEXT_CROP.png](scenes/scan24/diagnostics/201906/WHOLE_0036_FULL_OBJECT_CONTEXT_CROP.png)
- [scenes/scan24/diagnostics/53254/START_0036_ISOLATED_CROP.png](scenes/scan24/diagnostics/53254/START_0036_ISOLATED_CROP.png)
- [scenes/scan24/diagnostics/53254/WHOLE_0036_ISOLATED_CROP.png](scenes/scan24/diagnostics/53254/WHOLE_0036_ISOLATED_CROP.png)
- [scenes/scan24/diagnostics/53254/WHOLE_0036_FULL_OBJECT_CONTEXT_CROP.png](scenes/scan24/diagnostics/53254/WHOLE_0036_FULL_OBJECT_CONTEXT_CROP.png)
- [scenes/scan24/diagnostics/53254/LOCAL_0036_ISOLATED_CROP.png](scenes/scan24/diagnostics/53254/LOCAL_0036_ISOLATED_CROP.png)
- [scenes/scan24/diagnostics/201906/START_0036_ISOLATED_CROP.png](scenes/scan24/diagnostics/201906/START_0036_ISOLATED_CROP.png)
- [scenes/scan24/diagnostics/201906/WHOLE_0036_ADDED_MEMBERS_CROP.png](scenes/scan24/diagnostics/201906/WHOLE_0036_ADDED_MEMBERS_CROP.png)
- [scenes/scan24/diagnostics/201906/WHOLE_0012_ISOLATED_CROP.png](scenes/scan24/diagnostics/201906/WHOLE_0012_ISOLATED_CROP.png)
- [scenes/scan24/diagnostics/201906/WHOLE_0012_FULL_OBJECT_CONTEXT_CROP.png](scenes/scan24/diagnostics/201906/WHOLE_0012_FULL_OBJECT_CONTEXT_CROP.png)
- [scenes/scan24/diagnostics/200509/WHOLE_0036_ISOLATED_CROP.png](scenes/scan24/diagnostics/200509/WHOLE_0036_ISOLATED_CROP.png)
- [scenes/scan24/diagnostics/200509/WHOLE_0036_FULL_OBJECT_CONTEXT_CROP.png](scenes/scan24/diagnostics/200509/WHOLE_0036_FULL_OBJECT_CONTEXT_CROP.png)
- [scenes/scan24/diagnostics/53254/WHOLE_0036_START_MEMBERS_CROP.png](scenes/scan24/diagnostics/53254/WHOLE_0036_START_MEMBERS_CROP.png)
- [scenes/scan24/diagnostics/53254/WHOLE_0036_ADDED_MEMBERS_CROP.png](scenes/scan24/diagnostics/53254/WHOLE_0036_ADDED_MEMBERS_CROP.png)
- [scenes/scan24/diagnostics/201906/WHOLE_0036_START_MEMBERS_CROP.png](scenes/scan24/diagnostics/201906/WHOLE_0036_START_MEMBERS_CROP.png)
- [scenes/scan24/diagnostics/210790/WHOLE_0036_ISOLATED_CROP.png](scenes/scan24/diagnostics/210790/WHOLE_0036_ISOLATED_CROP.png)
- [scenes/scan24/diagnostics/210790/WHOLE_0036_FULL_OBJECT_CONTEXT_CROP.png](scenes/scan24/diagnostics/210790/WHOLE_0036_FULL_OBJECT_CONTEXT_CROP.png)
- [scenes/scan24/diagnostics/202023/WHOLE_0012_ISOLATED.png](scenes/scan24/diagnostics/202023/WHOLE_0012_ISOLATED.png)
- [scenes/scan24/diagnostics/negative_84842_362883/WHOLE_0036_FULL_OBJECT_CONTEXT_CROP.png](scenes/scan24/diagnostics/negative_84842_362883/WHOLE_0036_FULL_OBJECT_CONTEXT_CROP.png)
- [scenes/scan24/diagnostics/negative_153248_377058/WHOLE_0036_FULL_OBJECT_CONTEXT_CROP.png](scenes/scan24/diagnostics/negative_153248_377058/WHOLE_0036_FULL_OBJECT_CONTEXT_CROP.png)
- [scenes/scan24/diagnostics/negative_153427_153430/WHOLE_0036_FULL_OBJECT_CONTEXT_CROP.png](scenes/scan24/diagnostics/negative_153427_153430/WHOLE_0036_FULL_OBJECT_CONTEXT_CROP.png)
- [scenes/scan24/diagnostics/53254/WHOLE_MID_0036_ADDED_MEMBERS_CROP.png](scenes/scan24/diagnostics/53254/WHOLE_MID_0036_ADDED_MEMBERS_CROP.png)
- [scenes/scan24/diagnostics/53254/WHOLE_0036_QUERY_CONTEXT_CROP.png](scenes/scan24/diagnostics/53254/WHOLE_0036_QUERY_CONTEXT_CROP.png)
- [scenes/scan24/diagnostics/201906/WHOLE_0036_QUERY_CONTEXT_CROP.png](scenes/scan24/diagnostics/201906/WHOLE_0036_QUERY_CONTEXT_CROP.png)
- [scenes/scan24/diagnostics/200509/WHOLE_0012_ISOLATED_CROP.png](scenes/scan24/diagnostics/200509/WHOLE_0012_ISOLATED_CROP.png)
- [scenes/scan24/diagnostics/200509/WHOLE_0012_FULL_OBJECT_CONTEXT_CROP.png](scenes/scan24/diagnostics/200509/WHOLE_0012_FULL_OBJECT_CONTEXT_CROP.png)
- [scenes/scan24/diagnostics/negative_301451_301459/WHOLE_0036_ISOLATED.png](scenes/scan24/diagnostics/negative_301451_301459/WHOLE_0036_ISOLATED.png)
- [scenes/scan24/diagnostics/negative_153427_153430/WHOLE_0036_ISOLATED_CROP.png](scenes/scan24/diagnostics/negative_153427_153430/WHOLE_0036_ISOLATED_CROP.png)
