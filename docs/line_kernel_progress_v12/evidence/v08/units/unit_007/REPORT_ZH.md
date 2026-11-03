# unit_007 保存输出分析

四臂均完成工程交付，但**本轮新增接受、事务尝试和域外支持均为0**。Hermite接缝没有产生新的直线或曲线身份，仍不能判断用户的“已接受多片段合并之后，最近外向片段会以小局部转向继续”的先验，也不能证明HISTORY优于BASE。这个结论只覆盖本轮24个种子，不是整个研究方向的否定。

实际子进程 returncode=0、reason=null，2026-11-02 02:06:31至02:09:21 JST；RUN_RESULT记录168.4574秒、delivery_gate=true、fit_calls=0。退出成功不等于科学成功。保存的八个四臂初末检查点文件哈希已核对，原核审计记录unchanged；本次只读保存结果和图片，没有计算重跑或渲染。

## 实际表示、范围与对照

精确起点为unit006 BASE_FINAL：285956行、122004已归属、163952 UNKNOWN、next_version20583、24种子、3条历史接受。保留原叶成员及强M5背景；本示踪没有自由拆分旧叶。已接受合并只是先验，起点含BASE接受，不是HISTORY认证或GT。

单donor重叠及最多3叶endpoint relay的候选、完整1.5p查询、共同守卫不变。LINEAR使用旧线性重叠混合；HERMITE只在原注册通过后替换局部2p窗口，用两端局部切向构造有限三次Bezier，采样间距上界0.25p。辅助q不作为墨迹。HISTORY仍在更新前的曲线/尾部使用1p割线、2p历史和冻结的15°/曲率差条件；后续rollout原则上可能分歧，本轮未发生。

| 臂 | 完整初始前沿 | 共同合格候选 | 新事务/接受 | 最终assigned |
|---|---:|---:|---:|---:|
| LINEAR_BASE | 48 | 0 | 0/0 | 122004 |
| LINEAR_HISTORY | 48 | 0 | 0/0 | 122004 |
| HERMITE_BASE | 48 | 0 | 0/0 | 122004 |
| HERMITE_HISTORY | 48 | 0 | 0/0 | 122004 |

两种表示的初始库均完整，无第257前缀截断或资源超限。停止原因frontiers_exhausted。unit006 BASE0042/0048重放匹配；这仅验证来源与旧行为。最后有效状态仍为起点，保留3条历史事件，无新的接受阶段或失败事务后的成员回滚需要解释。

## 最早失败与接缝作用

endpoint分支仍有方向/connector拒绝：两种表示均109条observed_endpoint_tangent、30条observed_connector、5条whole_member、2条有限域、1条vertex、1条invalid及64条used/seed/cycle记录。重叠分支共同有124条无重叠或尾部、63条距离、14条切向注册拒绝。LINEAR另有22条whole_member和1条window_turn；HERMITE为15条whole_member、1条window_turn、2条有限域、5条self_contact。它们是候选记录数，不是独立成功率分母。

| 当前前沿/候选 | LINEAR | HERMITE | 判断 |
|---|---|---|---|
| 230214侧0 → 54197 | 最大成员切向53.355854° | 30.070360°；max残差0.534380p、q95 0.388844p | 局部接缝改善，但仍严格超过30°；无接受 |
| 230214侧0 → 96009 | 切向43.056374° | 切向37.184276°、q95 0.505381p | 仍双重失败，不能只展示改善的数 |
| 106171 → 106166 | whole_member | 右侧域外0.00580044p | 所有原成员有限域不能豁免 |
| 160304 → 127970 | whole_member | 左侧域外0.00348965p | 不扩大EPS |
| 112780→168654、23216→23209、26025→167360、79841→177351/79855 | 较早whole_member/window拒绝 | self_contact | 需区分真实回折与离散化局部邻近 |

54197注册的s=w=0.145889p、投影距离0.138401p、曲线注册切向10.749792°。Hermite使用19段、最大段长0.217392p；改善并不证明整组正确。其endpoint解释的connector角约145.19°/130.88°，是重叠附近的反向关系，不能硬当正向间隙续接。此提案在成员切向阶段已拒绝，后续几何条件未经通过。

保存源码的contact_bounded仅跳过相邻段，比较从i+2开始；geometry_guard只清除精确共线内点。对连续三个保留的弯曲短段，i与i+2的端点距离至多是中间段长；<=0.25p采样因此可以触发0.5p“自接触”，尽管它们属于同一局部弧段。这是**可审计的采样密度混淆推断**。保存记录没有最近接触点/弧长差，不能断言五例全部是假阳性，更不能直接放行。早于此的成员/域失败仍真实存在于冻结判据中。

## 原核视觉证据

已实际查看16张保存PNG，完整清单见FAILURE_ANALYSIS。原生全景保留完整植株、花盆和大量UNKNOWN；两视图仍有原有尖刺。冻结几何不会消除尖刺；错误把它们吞入身份仍然是反例。本轮零新接受，不能据此认证历史身份无误。

![原核全景 r1](scenes/ficus/stages/HERMITE_BASE_FINAL/test_r_1_FULL.png)
![原核全景 r79](scenes/ficus/stages/HERMITE_BASE_FINAL/test_r_79_FULL.png)

230214孤立图仍是短绿段，54197上下文有邻近灰色竞争，未见新增外延。LINEAR与HERMITE最终映射相同，颜色不是接缝效果。64355可辨为继承的局部弯段；137016为较长细直段；112780只是很小的既有弧，两视图不足以称完整曲线恢复。

![230214完整查询上下文](scenes/ficus/diagnostics/230214/HERMITE_BASE_test_r_1_CONTEXT_CROP.png)
![54197另一视图上下文](scenes/ficus/diagnostics/54197/HERMITE_BASE_test_r_79_CONTEXT_CROP.png)
![继承64355弧](scenes/ficus/diagnostics/64355/HERMITE_BASE_test_r_1_ISOLATED_CROP.png)
![64355另一视图上下文](scenes/ficus/diagnostics/64355/HERMITE_BASE_test_r_79_CONTEXT_CROP.png)
![137016继承直段](scenes/ficus/diagnostics/137016/HERMITE_BASE_test_r_1_ISOLATED_CROP.png)
![112780继承小弧](scenes/ficus/diagnostics/112780/HERMITE_BASE_test_r_79_CONTEXT_CROP.png)

四负例已看，但裁图都是很小的灰/蓝/棕色短迹，不能排除平行、分支、深度混淆。它们不是GT： [11/80709](scenes/ficus/diagnostics/negative_11_80709/HERMITE_BASE_test_r_1_CONTEXT_CROP.png)、[16931/18768](scenes/ficus/diagnostics/negative_16931_18768/HERMITE_BASE_test_r_1_CONTEXT_CROP.png)、[112/205435](scenes/ficus/diagnostics/negative_112_205435/HERMITE_BASE_test_r_1_CONTEXT_CROP.png)、[33117/201172](scenes/ficus/diagnostics/negative_33117_201172/HERMITE_BASE_test_r_1_CONTEXT_CROP.png)。没有新增曲线或损伤可选；不把继承实例填充为top3成功。所有图是原Gaussian墨迹，无辅助曲线/桥，也没有用源表面遮挡掩盖竞争者。

## 支持与来源：全部增益在起点已有

单位为p；支持由区间映射得到，不能称连续观测长度。

| 组 | 原核数 | 支持union | 最长连续段 | 最大gap | 有限extent | 本轮域外新增 |
|---|---:|---:|---:|---:|---:|---:|
| 230214 | 49 | 8.84675 | 2.58160 | 1.40558 | 12.07335 | 0 |
| 64355 | 121 | 17.04325 | 3.44011 | 0.40102 | 19.01785 | 0 |
| 112780 | 50 | 9.82879 | 2.48615 | 1.24134 | 13.17882 | 0 |
| 137016 | 188 | 31.54970 | 9.20871 | 0.35897 | 37.87653 | 0 |
| 48496 | 48 | 8.77774 | 2.24492 | 1.41333 | 11.85844 | 0 |

230214有3个达12核/2p的M4来源(54189、230214、230230)，另230201仅4核；64355和137016也有3个实质M4来源；112780、48496只有2个。相对原M5种子的域外代理230214=2.58160p、64355=2.28020p、137016=3.95194p均为历史所得。没有一个本轮获得>=4p新增，更没有新第二次事务。既有union/继承来源数量不能满足本轮成功条件。

依据保存的成员交叉统计，四臂同值；下表增减是相对于各自独立参考，不能相加，也不是新单位的因果增益。标签差异只描述身份重排；split来自交叉表，不能只比较数值ID。

| 参考 | 新assigned | 撤回到UNKNOWN | 标签差异行 | 参考组拆分 |
|---|---:|---:|---:|---:|
| 本轮起点/unit006 BASE | 0 | 0 | 0 | 0 |
| unit006 HISTORY | 17 | 0 | 17 | 0 |
| v05 M5 | 39 | 0 | 75 | 0 |
| v05 M4 | 3534 | 0 | 5420 | 0 |
| v06 overlap | 1942 | 1821 | 6390 | 184 |
| v06 common | 2318 | 174 | 4249 | 12 |

相对v06存在的损失和拆分不可隐藏，但全部继承自本轮起点。本轮未产生任何新撤回、拆分、改组或重叠池化收益。全部285956行有映射，搜索范围仍只是冻结种子而非全场景；UNKNOWN163952行未被悄悄移除。

## 下一步与可复核性

另行审查并冻结“按内在弧长定义非局部接触”的对照：保持距离0.5p、所有候选、Q、30°切向/有限域/支持条件不变，比较旧段索引排除与弧长分离>=1p的精确线段参数对接触检查；记录最近接触点、段号、弧长差与距离。先用相同折线几何细分的不变性及真实回折/交叉小夹具，再在相同冻结前沿比较BASE/HISTORY。此为接触守卫定义变更，必须另行冻结，不能回改本轮；54197仍按30.07036°拒绝，不放宽30°阈值。

继续窗口仍有效：Nov2 07:15停新单元、07:38停science、07:45交接、08:00硬截止。本报告不启动后续实验。物理身份、held-out、时间稳定性与概率均未认证。

依据：[RUN_RESULT](RUN_RESULT.json)、[READINESS](scenes/ficus/READINESS.json)、[COMPARISON](scenes/ficus/COMPARISON.json)、[保存源码](source_snapshot/geometry_base.py)、[冻结CONFIG](CONFIG.json)。CONFIG SHA256=2dad2b4994628a645dde9cd0d0532298160903cd204020953e90810483a06987；DECISION SHA256=bfad016e8f5a3ba1c95b8c8bb5dd044c86cdc973b7ac6bc93cd60d5ee72dcedf。保留全部旧日志、失败q、替代解释及原始父进程退出。

