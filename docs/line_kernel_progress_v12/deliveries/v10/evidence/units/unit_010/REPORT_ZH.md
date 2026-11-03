# unit010：有限接触软代价改变赢家，但未带来第二次增长

实际数值子进程 **rc=0、reason=null**，05:00:26.332499—05:03:22.321444 JST。RUN_RESULT为completed；readiness9.03s、共同初库45.70s、BASE14.02s、SOFT27.77s、交付78.64s。两臂均重新搜索完整库后自然NO_CONNECTABLE_FRAGMENT；没有超时、容量、配额中断，没有SUPPORTED_CLOSED。这里的“穷尽”仅限主动30579及冻结候选/剩余规则，不代表整个06:00窗口结束。

起点严格是unit009第71步，279616原核、127000已归属、152616 UNKNOWN；30579已有586核。1799历史+71事件均继承，原74步终态未改写。全部11组恢复，NO_FURTHER_GROWTH与原checkpoint四文件及CHECKPOINT逐字节相同。只比较本次两个新rollout；历史ROW_FIT未重新执行。

| 保存结果 | BASE_J | CONTACT_SOFT_J |
|---|---:|---:|
| 首个donor/关系 | -30821，endpoint/1 | 67269，overlap/0 |
| 最低分 | 0.061348696 | 0.063473616 |
| 增加行数/来源 | 10，全部UNKNOWN | 18，原已归属组整体 |
| 最终30579核数 | 596 | 604 |
| 全资产assigned | 127010 | 127000 |
| 接受次数/第二次接受 | 1 / 0 | 1 / 0 |
| 自接触/纯池化 | 是 / 否 | 否 / 是 |
| 新增START丢行/旧组拆分 | 0 / 0 | 0 / 0 |
| 动态独特donor支持U | 2.284709p | 0p |
| 动态union=最长run | 135.013937p | 130.977071p |
| 固定START union=run | 131.447509p | 131.447509p |
| 固定START新减继承支持 | 0p | 0p |
| 动态最大gap | 0p | 0p |
| 域外支持代理 | 4.299810p | 0.001603p |

初始库85donor/510解释、40可连接，真实重放旧0091库通过：全部原评分/拒绝/162个几何数组/选择327精确匹配。两策略共享初始几何和合法性；0.01把-30821端点解释从0.061348696加到0.071348696，因此无接触67269以0.063473616成为选择450；同-30821重叠原分0.07514767没有胜出。保存库的最低J选择已独立核对。接触解释仍合法且有限，并未恢复R6硬拒绝。

两个接受后都原子保存完整checkpoint再重查。BASE终库83donor/498解释完整：118无注册、329端点距离、50退化/急折（vertex_degeneracy）、1分叉；SOFT终库84donor/504解释完整：121无注册、330端点距离、7退化/急折、46分叉。每臂仅一个事件，第一/中间/最后为同一事务，不虚构中段。初库不能连接的理由与终库理由均保存，零选择不是截断库挑赢家。

最早科学负例是软项把端点解释替换为纯池化，却仍没有第二次接受。BASE动态长度/union较起点增加3.566428p，但新10核在固定原Q上只覆盖已有4.305778p；SOFT新18核覆盖已有7.286194p，新增独特区间均0。动态域外代理与支持区间属于辅助投影统计，不能证明真实外延；零gap也不是连续物理观测认证。起点已有5项实质M4来源，BASE仍5项，SOFT多1项67269（18核/7.237155p）；它是内部池化，不能把继承长组或贡献计数当新曲线成功。

规则2/4/6在两臂都关闭。两次实际接受没有超原1.5p/75度的核，因此本轮不能单独声称R2关闭带来收益。BASE最大距离1.217185p、角70.9813度；SOFT1.216942p、41.1576度。四对平行冲突为起点并集中已有叶对；SOFT新增 **67265/67269** 一对。BASE接受接触距离0.491071p（segments1/7），SOFT接受U=0，证明R4/R6没有隐性回门。二者gap均0，不能冒称本轮检验了跨大gap收益。

SOFT后续首个可构造但分叉拒绝记录12（donor-276185、overlap/0）的TRANSPORT见证：原G在自己的旧Q上CLEAR，投到新拟合Q后G和union都在中心34触发BRANCH，F为CLEAR。说明整组曲线更新会改变剩余分叉守卫；不等于新donor已经引入真实第三臂，也不能据此解除规则5。BASE相应早期记录在规则3处失败，分叉为NOT_REACHED，不能伪造“分叉通过”。后续单元应保留同中心见证，不能把拟合曲线自己对齐当物理分叉证据。

原核means/covariance/opacity/colors/primitive_id/internal_piece_id/arc_t的前后哈希一致，完整279616行顺序保持。保存membership的line_kernel_id等来源字段一致；reason、前版本和组版本按事务改变，不能把身份字段变化当核几何变化。逐行核验30579最终集合精确等于原586行与donor的并集，另外10个跟踪组成员均保留。整条辅助曲线确实更新：BASE旧域最大移动0.535967p（仅拟合0.369977p），SOFT0.538514p（仅拟合0.508883p）；全部成员参与五轮拟合。辅助曲线不用于最终墨迹，无补桥或源表面遮挡。原有几何尖刺不会因改标签消失。

参考contingency应区分继承差异：对实际START，两臂lost/split均0；BASE gained10，SOFT gained0但并入18已归属行。对强M4，起点gained865/lost0/split0，BASE875/0/0，SOFT865/0/0。对M3分别起点8657、BASE8667、SOFT8657，lost/split均0。对unit014联合参考，起点已lost144/split15，两臂仍144/15；这些是不同历史分支的既存差异，不是本次丢行。对封存unit009最终态，起点少16个assigned及3个参考组拆分，BASE少6/拆2、SOFT少16/拆3，同样是匹配起点回退及范围选择，不可藏作净增长。scan65没有已执行M5/v06对照，不伪造它们。

实际查看的全景保留面具整体及杂散原核；0012隔离图两臂都仅窄细曲段，SOFT新增图仅少数细像素；BASE0036新增图近乎空白。0036完整对象裁剪和查询背景狭长且多条同向结构紧邻，无法排除平行或深度混入。visual_evidence_missing=true表示**缺少足够辨别身份的尺度与视角证据**，不是没有PNG。没有双视图可辨的新增实质直线及曲线示范；没有物理、held-out、时间稳定或准确率结论。

实际已查看图：
- [scenes/scan65/stages/CONTACT_SOFT_J_FINAL/0012_FULL.png](scenes/scan65/stages/CONTACT_SOFT_J_FINAL/0012_FULL.png)
- [scenes/scan65/worst_events/BASE_J/0001/0012_ISOLATED_CROP.png](scenes/scan65/worst_events/BASE_J/0001/0012_ISOLATED_CROP.png)
- [scenes/scan65/worst_events/CONTACT_SOFT_J/0001/0036_FULL_OBJECT_CONTEXT.png](scenes/scan65/worst_events/CONTACT_SOFT_J/0001/0036_FULL_OBJECT_CONTEXT.png)
- [scenes/scan65/stages/BASE_J_FINAL/0036_FULL.png](scenes/scan65/stages/BASE_J_FINAL/0036_FULL.png)
- [scenes/scan65/diagnostics/30579/CONTACT_SOFT_J_0012_ISOLATED_CROP.png](scenes/scan65/diagnostics/30579/CONTACT_SOFT_J_0012_ISOLATED_CROP.png)
- [scenes/scan65/worst_events/CONTACT_SOFT_J/0001/0012_ADDED_CROP.png](scenes/scan65/worst_events/CONTACT_SOFT_J/0001/0012_ADDED_CROP.png)
- [scenes/scan65/worst_events/BASE_J/0001/0036_ADDED_CROP.png](scenes/scan65/worst_events/BASE_J/0001/0036_ADDED_CROP.png)
- [scenes/scan65/diagnostics/30579/CONTACT_SOFT_J_0036_QUERY_CONTEXT_CROP.png](scenes/scan65/diagnostics/30579/CONTACT_SOFT_J_0036_QUERY_CONTEXT_CROP.png)

下一另冻单元：另冻新范围而非继续30579权重/预算扫描：以本单元BASE_J_FINAL完整11组为起点，新增主动line8765/v21440（44核）、polyline61271/v21494（71核），原选择账均有两项实质M3贡献；先核验其完整行集/原M4版本未变，失败NOT_RUN不补选。保留11复合组为整组donor，新增两origin只做队列标记、不分配版本，checkpoint覆盖13origin。仅运行原BASE_J组均衡拟合/评分，[2,4,6]继续关闭，CONTACT_SOFT_J=.01只作同状态影子；NO_FURTHER_GROWTH精确复制起点。候选2p、五轮整组IRLS、规则1/3/TRANSPORT5、完整库最佳并重查、8192/257容量与闭合支持均不变。新观察范围不是接触软项优越性对照。

建议预算780s（readiness60、初库120、新增长240、交付360），只在05:15前ready并启动；05:35停止science。若来不及，则仅交接，不冒称整个科学问题耗尽。所有原结果、失败和原库保持不可变。证据索引见[SAVED_OUTPUT_AUDIT.json](SAVED_OUTPUT_AUDIT.json)。
