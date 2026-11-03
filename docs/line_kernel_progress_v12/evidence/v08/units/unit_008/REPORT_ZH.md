# unit_008 保存输出分析

**工程完成；ARC接触定义带来实际跨组外延，但两臂都只接受一次，没有后续第二次增长，也未证明HISTORY更好。** 物理身份与完整直/曲双类型恢复仍为PARTIAL。实际子进程rc=0、reason=null，02:25:24至02:29:24 JST；RUN_RESULT耗时238.732秒、fit_calls=0、delivery_gate=true。不能把退出成功当科学成功。

本次只读保存JSON、检查点与PNG，未拟合、重算候选、渲染或改源码/config。12个拓扑/成员检查点的全部文件哈希已核对。原核审计记录means/covariance/opacity及行序数量等前后相同；辅助Q没有墨迹。48个旧HERMITE初始库控制重放匹配，96个新初始策略/前沿库完整；四臂均frontiers_exhausted，无容量截断、超时或运行异常。

## 实际方法与用户假设

起点是unit007 HERMITE_BASE_FINAL：24种子、285956行、122004 assigned、3条历史事件、next_version20583。原M5强背景保留；本轮是保护原叶成员的示踪，不是自由拆分实验。既有接受只是先验，不是GT。

四臂保持Hermite有限接缝、完整1.5p候选及成员/parallel/branch/支持守卫。只把最终Q的接触判定从非相邻**索引段**改为内在弧长相隔至少1p的点对最小距离，距离门槛仍0.5p。这属于守卫定义变更。BASE/HISTORY各自共享同策略完整库，随后状态分歧不能再声称候选相同。

| 臂 | 新事务/接受 | 79841所吸收donor | assigned | UNKNOWN | 第二次新接受 |
|---|---:|---|---:|---:|---:|
| INDEX_BASE | 0/0 | 无 | 122004 | 163952 | 0 |
| INDEX_HISTORY | 0/0 | 无 | 122004 | 163952 | 0 |
| ARC_BASE | 1/1 | 177351，65核 | 122004 | 163952 | 0 |
| ARC_HISTORY | 1/1 | 79855，15核 | 122019 | 163937 | 0 |

BASE合并已归属的完整donor，实际改变65行组身份而assigned不增加；HISTORY激活原UNKNOWN的15核。两臂互差80行，是真实不同成员选择，不能仅解释为ID重编号。每臂接受后先保存_001，最终均next_version20584、4条事件；拒绝的后续候选不提交，最后有效状态为对应_001，未丢失接受成果。

## 接触修正及更早/更晚的失败

五个原self_contact案例的INDEX最小接触都在局部弧上，距离/弧距约0.203–0.234p；ARC非局部最小距离约0.986–0.999p，均不触发0.5p。这明确区分了索引邻接与物理弧邻域，不能进一步推出合并正确。

| 前沿→donor | INDEX局部距离p | ARC非局部距离p | ARC最终结果 |
|---|---:|---:|---|
| 112780→168654 | 0.211445 | 0.985962 | 仅2核/0.581861p外向支持 |
| 23216→23209 | 0.231980 | 0.998633 | 6核但仅1.029606p |
| 26025→167360 | 0.203412 | 0.993979 | 仅2核/0.488639p |
| 79841→177351 | 0.233670 | 0.994388 | 共同合格；BASE接受 |
| 79841→79855 | 0.234495 | 0.999338 | 共同合格；HISTORY接受 |

其他较早失败没有被接触规则救场，包括54197的30.07036°切向拒绝及有限域超界。三条支持不足不能包装为完整曲线增长。

79841侧1的共同库有两个候选，gap分别0.203961p与0.367880p，差0.163919p大于共同歧义门槛0.15p，所以两臂没有共同弃权。BASE取177351；HISTORY的预测角为15.730963°，超过15°，拒绝它并取预测角9.520381°的79855。两者曲率差都约1e-14，源q的k也约0，当前历史主要在筛方向，不构成实测“缓变曲率提高续接概率”的证据。

随后BASE新外端查询到50407(0.844270p)，两方向均overlap_distance失败；83549(1.272510p)无有效重叠尾部且端点切向失败。HISTORY新外端的79865约0.267p有切向/距离拒绝；177351约0.847738p再接时全成员q95=0.519927p、切向32.334937°失败。这里是完整当前库的死端，不能放宽门槛或把它归咎于接触检查。另一端也无共同候选。

## 支持、贡献与真实外延

79841原始41核来自M4的79841(21核/3.938754p)和79846(20核/2.721446p)。所有长度为投影支持代理。

| 79841状态 | 核数 | union p | 最长连续段p | 最大gap p | 总gap p | 有限extent p | 较本轮起点域外支持p |
|---|---:|---:|---:|---:|---:|---:|---:|
| 起点/INDEX | 41 | 6.660199 | 1.547917 | 0.584200 | 1.236860 | 7.897059 | 0 |
| ARC_BASE | 106 | 19.404528 | 2.753343 | 0.584200 | 3.599173 | 23.003701 | 12.759243 |
| ARC_HISTORY | 56 | 8.842083 | 2.189919 | 0.584200 | 1.517372 | 10.359456 | 2.207394 |

BASE新增第三M4来源177351=65核/12.961053p；HISTORY新增79855=15核/2.670107p。各有3个达12核/2p的M4来源，但原parent层面BASE仅1个实质来源(6943，80核/18.430461p)，HISTORY仅2个(3111和6943)。M4来源数不等于独立物理来源数。

BASE有实质域外代理，并非重复池化；保存内部填充代理0、支持端点钳制0。HISTORY新增域外仅2.207394p，低于4p成功门槛。事件的严格外向半空间支持分别12.739518p、2.150955p，和整体起点域外映射代理略有差异，不能混称。union19.4p更不等于连续19.4p观测。两者都没有第二次接受。

## 实际原核图及证据边界

已实际查看16张保存图；总共1164张PNG，完整清单在RUN_RESULT。全植株与花盆、灰色UNKNOWN及原有长尖刺都保留，不能把冻结几何理解成已经清除尖刺。没有辅助桥或源表面遮挡。全景保持原始上下文，局部候选上下文包含空间上分离的另一短迹，不能裁掉后宣称唯一解释。

![原核全景r1](scenes/ficus/stages/ARC_BASE_FINAL/test_r_1_FULL.png)
![原核全景r79](scenes/ficus/stages/ARC_BASE_FINAL/test_r_79_FULL.png)

同核比较中，BASE把小弧的原另一颜色部分归入种子，HISTORY仅吸收小量核，颜色结果与起点非常接近。成员及域外统计证明有结构性归组变化，但图像只有少量原生像素；只能称局部外延候选，不能从同色判断物理身份或称完整长曲线。seed旧model=line的分类也不自动证明本次是成功直线或曲线。

![起点同核](scenes/ficus/diagnostics/79841/NO_FURTHER_GROWTH_test_r_1_ISOLATED_CROP.png)
![BASE同核r1](scenes/ficus/diagnostics/79841/ARC_BASE_test_r_1_ISOLATED_CROP.png)
![HISTORY同核r1](scenes/ficus/diagnostics/79841/ARC_HISTORY_test_r_1_ISOLATED_CROP.png)
![BASE同核r79](scenes/ficus/diagnostics/79841/ARC_BASE_test_r_79_ISOLATED_CROP.png)
![HISTORY同核r79](scenes/ficus/diagnostics/79841/ARC_HISTORY_test_r_79_ISOLATED_CROP.png)
![完整竞争上下文](scenes/ficus/diagnostics/79841/ARC_BASE_test_r_79_CONTEXT_CROP.png)

112780仍是很小的继承弧，137016仍是继承长细直段；不能拿它们补齐本轮直/曲双类型成功。[112780](scenes/ficus/diagnostics/112780/ARC_BASE_test_r_1_ISOLATED_CROP.png)、[137016](scenes/ficus/diagnostics/137016/ARC_BASE_test_r_79_ISOLATED_CROP.png)。四个负例上下文都已看但很小且模糊：[11/80709](scenes/ficus/diagnostics/negative_11_80709/ARC_BASE_test_r_1_CONTEXT_CROP.png)、[16931/18768](scenes/ficus/diagnostics/negative_16931_18768/ARC_BASE_test_r_1_CONTEXT_CROP.png)、[112/205435](scenes/ficus/diagnostics/negative_112_205435/ARC_BASE_test_r_1_CONTEXT_CROP.png)、[33117/201172](scenes/ficus/diagnostics/negative_33117_201172/ARC_BASE_test_r_1_CONTEXT_CROP.png)。没有可辨的新平行/分支/深度误吞证据，也没有足够图像将这些风险排除。HISTORY拒绝BASE较长续接是待核实反例，不可预称误拒。

## 参考得失：不累加、不隐藏旧损失

保存的METRICS与成员交叉表支持下表。单元起点与INDEX相同。各格为“新增assigned/撤回到UNKNOWN/标签变化行/参考组拆分”，不是准确率。

| 参考 | INDEX两臂 | ARC_BASE | ARC_HISTORY |
|---|---|---|---|
| 本轮起点 | 0/0/0/0 | 0/0/65/0 | 15/0/15/0 |
| v05 M5 | 39/0/75/0 | 39/0/140/0 | 54/0/90/0 |
| v05 M4 | 3534/0/5420/0 | 3534/0/5485/0 | 3549/0/5435/0 |
| v06 overlap | 1942/1821/6390/184 | 1942/1821/6455/184 | 1957/1821/6405/184 |
| v06 common | 2318/174/4249/12 | 2318/174/4314/12 | 2333/174/4264/12 |

本次另直接冷读保存MEMBERSHIP核对变化行交叉表：ARC_BASE唯一转移为177351→79841共65行；ARC_HISTORY唯一转移为UNKNOWN(-1)→79841共15行。本轮没有原叶拆分、撤回或种子成员损失；BASE整组合并一组既有标签，HISTORY激活一组UNKNOWN。相对v06存在的撤回/拆分是继承的，既不能隐瞒，也不能算成当前接触修正造成。全行导出不等于全场景搜索，其他未处理背景仍是强M5派生状态。

## 下一步

另行审查并冻结观察切向历史对照：从本轮NO_FURTHER_GROWTH共同起点重开同24种子，保留ARC接触、Hermite表示、完整候选及所有成员/支持阈值；比较BASE、原q割线HISTORY、原核control导数HISTORY。后者在同一有限弧坐标的两段1p窗口各统计原核轴向外积，按原观察端口规则定向并要求足够核数/谱间隔，缺证据则UNKNOWN；仍用原15°和2sin7.5°门槛，不调角度救177351。先冻结79841两竞争者的同状态影子选择，再运行双端续接；保存每bin行ID、轴谱和候选差异。该建议尚未执行，须单独review/DECISION；重点检验当前几乎零曲率是否仅源于直线辅助q，而非真实核切向历史。

该改变将保持近邻前沿目标，专门检验局部历史的证据来源；不保证突破后续成员几何死端。当前窗口继续有效，Nov2 07:15停新单元、07:38停science、07:45交接。物理身份、held-out、时间稳定性与合并概率均未验证。

来源：[RUN_RESULT](RUN_RESULT.json)、[GEOMETRY_AUDIT](GEOMETRY_AUDIT.json)、[COMPARISON](scenes/ficus/COMPARISON.json)、[ARC_BASE成员统计](scenes/ficus/stages/ARC_BASE_FINAL/METRICS.json)、[ARC_HISTORY轨迹](scenes/ficus/stages/ARC_HISTORY_FINAL/LINEAGE.json)。CONFIG SHA256=4daa7ec8ca77cef0c144618c1830942970bd18a6e86761decfff236f48da2e39；DECISION SHA256=a2e643c0d98aa4ed8410bf88d9c7bde53d126365c761f90ce642a3ceebce836c。实际退出与旧失败均原样保留。
