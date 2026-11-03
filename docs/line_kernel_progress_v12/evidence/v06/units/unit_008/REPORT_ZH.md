# unit008：ficus有限重叠模型归属，科学结论PARTIAL

执行完成，尚未证明联合优化带来可辨的实质直线与曲线归组优势。628个完整重叠分量全部处理，1141个配对模型全部恢复且无记录复现失败；共同假设库1222项。两个方法都比M4新增3413个assigned核、无旧分配丢失，但这些是归属数量，不是准确率或新外延。全景仍有碎片与长尖刺；冻结原核的身份归组不能消除原有几何噪声。

实际父持有子进程08:36:42.615711启动、08:40:36.371123结束，returncode=0、reason=null、actual_child_exit=true；RUN_RESULT耗时233.033秒。权威退出见[COMPUTE_EXIT](../../orchestration/unit_008/COMPUTE_EXIT.json)，未以wrapper退出码代替。分析没有拟合、重跑、渲染、测试或修改源码。

## 实际交付与配对结果

|项目|greedy|joint|
|---|---:|---:|
|全行映射|285956|285956|
|assigned / UNKNOWN|121883 / 164073|121883 / 164073|
|相对M4新增 / 丢失assigned|3413 / 0|3413 / 0|
|相对M4改变edge_id的行|5798|5834|
|选中重叠身份|509|516|

两臂147行edge_id不同；joint相对greedy实际新增assigned **3行、失去3行**，不能因总数相同声称成员相同。共同库选择差异为greedy独有7假设、joint独有14假设。joint的628分量均记录optimal，总solver时间约7.834秒；最优仅针对此有限假设库和收益。两臂M4旧组无拆分、无丢失，完整行序核对通过。没有超时、未完成或超128分量。只运行ficus；本单元没有scan24/scan65结果。

两份映射、carriers、groups、lineage、solver及四张原生全景checkpoint哈希均核对；64份父冻结源码快照、2个批准helper哈希一致。保存340张PNG；56组跨三种着色的联合裁剪记录无空图、无触及原生边界标志。不是逐张人工验收：本次实际查看了两臂四张全景、下列重点单组/上下文、M4曲例及四类负例的选定视角。连续帧未生成、未验证。

## 原核图像证据

[greedy全景1](scenes/ficus/stages/greedy/test_r_1_FULL.png) · [greedy全景79](scenes/ficus/stages/greedy/test_r_79_FULL.png)

![joint原生全景1](scenes/ficus/stages/joint/test_r_1_FULL.png)
![joint原生全景79](scenes/ficus/stages/joint/test_r_79_FULL.png)

全景的细碎枝叶、盆面断续与横向长尖刺仍明显。单组可见并不等于其完整物理身份已确定。

|选定身份|叶数/核数|投影支持并集p|最长投影连续段p|最大/总gap p|判断|
|---|---:|---:|---:|---:|---|
|65959，两臂相同|2 / 122|27.290|1.731|0.344 / 6.303|最大新polyline模型，但主要形状已由M4提供|
|188634，两臂相同|3 / 125|20.388|5.785|0.274 / 3.001|可见小直段，主要为已有支持的池化|
|112780，两臂相同|3 / 45|6.161|2.480|0.249 / 0.450|继承浅弧，不能算新曲线续接|
|80137，greedy|6 / 138|14.229|8.830|0.043 / 0.058|较大同组支持|
|80137，joint|5 / 90|12.912|8.353|0.287 / 1.142|移出152062；原组支持/最长段下降|
|152062，joint|2 / 98|14.372|13.143|0.430 / 0.430|另与215192成组；不是证实物理正确的拆并|

65959包含旧叶65959与106889，新增UNKNOWN6核；原parent7802贡献102核/27.287p，parent2515贡献10核/2.055p，其余更小。这是组内来源统计，不能把旧组已有跨parent误算新整合。188634含parent9245的85核/18.560p和10540的25核/5.892p；新增UNKNOWN10核。它们有实质来源支持，却没有显示joint胜过greedy。

![65959视图1](scenes/ficus/stages/joint/diagnostics/SCENE_65959_3276540c_GROUP_test_r_1_CROP4.png)
![65959视图79](scenes/ficus/stages/joint/diagnostics/SCENE_65959_3276540c_GROUP_test_r_79_CROP4.png)

[M4相同行集合视图79](scenes/ficus/stages/M4_reference/diagnostics/SCENE_65959_3276540c_GROUP_test_r_79_CROP4.png)与[joint完整证据邻域](scenes/ficus/stages/joint/diagnostics/SCENE_65959_3276540c_CONTEXT_test_r_79_CROP4.png)：浅弯外形已存在，新增归属在该尺度不构成清晰的新曲线续接。

[188634视图1](scenes/ficus/stages/joint/diagnostics/SCENE_188634_f5962445_GROUP_test_r_1_CROP4.png) · [视图79](scenes/ficus/stages/joint/diagnostics/SCENE_188634_f5962445_GROUP_test_r_79_CROP4.png)。可辨直段，两臂相同。其anchor_outward代理0.463p而model_outward=0；不是已证明延伸。

[80137相同行集greedy](scenes/ficus/stages/greedy/diagnostics/SCENE_80137_49fe4ea1_GROUP_test_r_79_CROP4.png) · [joint](scenes/ficus/stages/joint/diagnostics/SCENE_80137_49fe4ea1_GROUP_test_r_79_CROP4.png) · [完整邻域](scenes/ficus/stages/joint/diagnostics/SCENE_80137_49fe4ea1_CONTEXT_test_r_79_CROP4.png)。可见颜色分段，尚不能判断哪种身份对应实际边；必须保留上述局部得失。

所有长度来自有限辅助模型上的投影区间。支持并集、最长段、bbox/extent与端点外向代理各有不同含义；它们都不证明真实连续观测或物理延长。本轮没有endpoint路径、没有补画连接、没有删除不利原核。

## 负例、缺失与具体瓶颈

已看[parallel上下文11/80709](scenes/ficus/stages/joint/diagnostics/NEGATIVE_11_80709_CONTEXT_test_r_79_CROP4.png)、[branch上下文16931/18768](scenes/ficus/stages/joint/diagnostics/NEGATIVE_16931_18768_CONTEXT_test_r_1_CROP4.png)、[tangent上下文112/205435](scenes/ficus/stages/joint/diagnostics/NEGATIVE_112_205435_CONTEXT_test_r_1_CROP4.png)、[gap上下文33117/201172](scenes/ficus/stages/joint/diagnostics/NEGATIVE_33117_201172_CONTEXT_test_r_79_CROP4.png)。局部细线与接近/分叉结构可见，但深度关系和真正边身份没有独立真值。旧拒绝原因不是负例真值；本次未证明完整parallel/branch/depth安全，也未凭图宣称确定误吞。

选择器缺少64355、65064、116525的新增overlap后代，参考上下文已保存。直接读取保存候选发现：64355–65064、112780–116525均是accepted **endpoint**；全表756条成功endpoint。本轮1141条成功overlap不包含它们。因此这是本轮关系类型范围的缺口，不是求解器未找到已有overlap解，也不是整份候选图完全缺失正确候选。现有112780浅弧仍为继承参考。

下一步仅建议一个独立实验：同一ficus M4及其保存endpoint图，迁移unit002有限叶复合身份的greedy/MILP端口路径对照，优先上述两对，并保留完整竞争分量、全ambiguity弃权和整路径守卫。输入必须是原M4，不能把M4候选直接套在本轮已组合身份上。unit008仅作overlap外部参考，暂不声称解决overlap与endpoint联合竞争。具体预算、保留与视觉证伪见[NEXT.json](NEXT.json)。尚未启动；不是提高本轮fit预算或调整阈值。

## 来源与边界

CONFIG SHA256：`1a1702f58d22b2146bf7958c39ed2fc156a2953e7d6c19b43e238c94cc5dc852`；decision：`5e0ccb9fed915795b51b3dff1da92767d365bc63be6f1ca40fa38e2d111bbaa7`。

原M4来自v05 unit016，STATE SHA256 `7d1457b144b0c58b8a3fe1fd1f1620e967158c1ace8326c64e6d996671378900`。候选来自v05 unit019的M5-on-M4记录。源码以[PARENT_RUN_FROZEN](PARENT_RUN_FROZEN.json)映射的[source_snapshot](source_snapshot/)为准，不依赖未来latestHEAD。原fit核心SHA `c1565d2c33ee1f75e1a58469f14d8e153a138eb5f3c0dc73fbbcc5a9ab20e512`；renderer.py `ce24cd30d663e6f421064d83006f097b02a5cf6a74b20c177a905ca514caed93`；libjoint.so `033a973a71dc5364677a5bf0625f23dc4fe445b70257f04de7cb70cdccca84b0`。

实际入口见[RUN_REQUEST](RUN_REQUEST.json)：批准venv的python `-B` 调用v06 `scene_runner.py --config` 本单元CONFIG；父持有进程与真实退出。输入/几何证据见[INPUT_HASH_RECEIPT](INPUT_HASH_RECEIPT.json)、[GEOMETRY_AUDIT](GEOMETRY_AUDIT.json)。审计保存原285956核及字段/行序不变，无carrier几何渲染；本分析没有重算原资产。初次ficus方法迁移无历史同方法重放，正确记录NOT_APPLICABLE_FRESH_SCENE。

物理身份一律provisional，旧parent只是来源。没有独立物理真值、未做held-out验证；固定既有两视图也不是新held-out。工程完整交付与科学PARTIAL并存。封存由父级执行，本分析不生成包含可变runtime的SEAL。
