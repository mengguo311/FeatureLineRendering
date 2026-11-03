# unit005：配对有限模型库——已交付的负结果

执行完成，科学结论为 **PARTIAL / 无新增主归属收益**。38个原配对拟合全部复现，但只多出一个未激活的小假设；两臂主归属完全相同，且与unit004完全相同。没有得到新增直线和曲线的双视图证据，不能宣称全局优化成功。

## 实际执行与范围

Parent实际child returncode=0、reason=null、actual_child_exit=true；07:38:40.405214至07:39:11.697629 JST。权威记录为[COMPUTE_EXIT](../../orchestration/unit_005/COMPUTE_EXIT.json)，不是launcher退出。RUN_RESULT记录内部耗时30.632s，readiness、假设库、双臂映射及图像均complete；本次分析没有拟合、测试、渲染或源码修改。

仅处理冻结的8个完整overlap分量、42个M4叶、38个保存配对。原458490核全行导出，但不等于全场景优化；范围外保留M4，ficus/scan65未运行。两臂均已保存MEMBERSHIP、原叶CARRIERS、含辅助模型的GROUPS/LINEAGE、假设选择及solver receipts。映射checkpoint的7个文件哈希逐一核对通过；冷载成功依据实际runner记录，本分析未重新执行加载管线。

## 得失与真正瓶颈

| 项目 | greedy | joint |
|---|---:|---:|
| assigned / UNKNOWN | 246416 / 212074 | 246416 / 212074 |
| 相对M4新增 / 丢失assigned | 67 / 0 | 67 / 0 |
| 相对unit004新增 / 丢失 / 主归属改变行 | 0 / 0 / 0 | 0 / 0 / 0 |
| 相对unit003新增 / 丢失assigned | 54 / 3726 | 54 / 3726 |
| 相对unit003主归属改变行 | 7192 | 7192 |
| 选中假设数（含未激活） | 8 | 8 |

相对M4的67行收益来自原unit004假设，不是本轮新收益。unit003的路径归属没有被本机制保护，其撤回不能隐瞒；M4旧分配保留、无旧组拆分。assigned不是准确率。

11个旧假设保留，38/38配对模型恢复且saved metrics在冻结容差内吻合，无复现失败。新模型兼容记录中，host有限域失败32次、通过6次；后续donor残差失败13次、有限域失败3次、通过1次，最终只增1假设。源码显示这里的finite_domain检查对象是**旧叶q全部采样点在新模型上的未截断弧长**，发生在原核残差/切向已通过之后。因此目前主要是辅助载体有限域与归属模型的兼容性瓶颈，并非拟合器复现失败或MILP求解能力不足。未保存越界幅度，不能武断归为微小数值误差；也不能因此假定这些配对物理正确。

新增57087假设由57087/202203组成：9核、2 seedlets、支持并集和最长段均1.483460p，最大/总gap=0，有限长度1.483460p。未达到3 seedlets及4p支持激活门槛，**9行仍UNKNOWN，激活0**。旧host投影范围外支持0.154926p、新模型范围外0；这不是物理边延长。重复支持0.763022p。两个叶不足以证明实质跨来源长边；旧parent只作来源。诊断标签“changed identity”指模型/假设变化，不可解释成已激活edge_id变化。

旧组18608仍有支持并集108.260p、最长连续段仅4.153p，有限长134.385p、总gap26.125p、最大gap0.358p。聚合重复观测、有限载体跨度、观测连续支持必须分开；本轮没有端点续接，也没有用模型补画空隙。

## 实际图像与可见性

以下均为保存的原核渲染。两臂各74张PNG，74对SHA全部一致；与unit004同名共有68张，68张也全部一致。

![0012全景](scenes/scan24/stages/joint/0012_FULL.png)
![0036全景](scenes/scan24/stages/joint/0036_FULL.png)

全景可见建筑边缘，但窗口、屋顶和竖边仍多色碎裂、重叠及尖刺。原核固定，归组不能清除原几何尖刺；两臂没有可见改善。

![新增假设0012原图为空](scenes/scan24/stages/joint/diagnostics/PAIR_MODEL_57087_70dd0cfd_GROUP_0012.png)
![新增假设0036仅微小灰点](scenes/scan24/stages/joint/diagnostics/PAIR_MODEL_57087_70dd0cfd_GROUP_0036_CROP4.png)
![其0036完整证据邻域](scenes/scan24/stages/joint/diagnostics/PAIR_MODEL_57087_70dd0cfd_CONTEXT_0036_CROP4.png)

57087在0012的单组及邻域均为空；0036原生图肉眼近乎全白，4倍最近邻裁剪才见微小灰点，并非严格空图。邻域可见短条带，不足以建立该组的完整性或曲率。

![继承18608单组0036](scenes/scan24/stages/joint/diagnostics/OVERLAP_18608_cc772950_GROUP_0036_CROP4.png)
![继承曲线参考201906](scenes/scan24/stages/joint/diagnostics/REFERENCE_201906_GROUP_0036_CROP4.png)
![负例84842/362883邻域](scenes/scan24/stages/joint/diagnostics/NEGATIVE_84842_362883_CONTEXT_0036_CROP4.png)

18608在0036近直；其0012单组/邻域碰到原生边界。201906浅弧只是继承参考，不是新增曲组。57153的0012为空；负例301451/301459两视图单组与邻域均为空。84842/362883仅细小重叠条带，不能从该图裁定深度或平行结构安全。所有负例仍属局部、未充分解析；没有新曲线证据，branch/parallel/depth的全面安全、物理身份和held-out泛化均未建立。

## 来源与唯一后续建议

[PARENT_RUN_FROZEN.json](PARENT_RUN_FROZEN.json)绑定的37个source_snapshot文件、两个renderer/libjoint helper及CONFIG/DECISION均核对SHA通过。CONFIG=`0a7e8e75c4a378c6ccaf39d26e9b3cfad5f5f31bf6e13bfb461b58c8db003701`；DECISION=`13696f9b24f479352e4d719f572b9d4acc10627aecc126ea4c59b8d385d5e1eb`。数值fit core字节SHA=`c1565d2c33ee1f75e1a58469f14d8e153a138eb5f3c0dc73fbbcc5a9ab20e512`，接口修复仅将原冻结文件同字节纳入允许源码，原接口失败与真实测试receipt均保留。后续追溯用快照，不要求工作树HEAD永久不变。实际入口为获准Python `-B .../pair_runner.py --config .../unit_005/CONFIG.json`，1800s cap；本报告不重写实际退出。

建议continue，**只推荐观测支持驱动的有限域归属对照**（PROPOSED/NOT_RUN，细节见[NEXT.json](NEXT.json)）：复用38个已保存模型和相同8分量，将有限域证据从旧辅助q全域转为真实原核与已存支持区间，严格保存越界拒绝，不扩大模型、不裁成员、不放宽阈值。若观测本身也越界或仍无实质双视图收益，照常保留负结果。本阶段不实施下一单元，不扩大到全场景，不以本次负结果结束整个授权窗口。物理身份始终暂定；由parent封存，本worker不生成SEAL。
