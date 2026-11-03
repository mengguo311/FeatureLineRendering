# v09 整组最佳下一碎片：最终工程交付

**数值主循环完成；研究身份结论与单元分析交接仍不完整。** 保留主管原状态 MODEL_HANDOFF_NOT_COMPLETED，不把本报告补写成原单元已成功交接。仅unit001执行；scan24/scan65未运行。当前按用户要求停止新科学工作，整理已有证据，等待parent独立验收。

真实阶段回执：review/build均rc0、reason=null；数值13:14:55—13:22:08 JST，rc0、reason=null，431.86秒。analysis_0于13:28:08、analysis_recovery_0于13:31:11均rc0但reason=HARD_DEADLINE；恢复另发生KeyError，四份单元REPORT_ZH/STATUS/NEXT/FAILURE_ANALYSIS均缺失。旧单元禁止编辑，本次只在O层保存最终分析与交付状态。shell/模型rc0不等于科学完成。

原始285956核全行映射保留，数值GEOMETRY_AUDIT逐字段验证means、covariance、opacity、canonical colors、primitive_id、internal_piece_id、arc_t前后哈希一致。控制schema73330 controls/61829 pieces/11503 parents已核验，basis中心误差0。辅助曲线全组可变，最终墨迹仅原核，无桥、补gap或源表面遮挡。灰UNKNOWN未删。

来源是v08 U11精确snapshot及REPAIR_BASE_FINAL，不是U12失败WIP或旧dirty工作树。起点122019 assigned/163937 UNKNOWN，已继承M5 +54/-0；这些不计作新实验增益。新v09相对v08同时改变候选、拟合、评分和守卫，不能单因素归因。新两臂只在模板可动范围不同，rollout后候选也会分叉。

**主循环的实际证据。** 全部126个LOCAL库、108个WHOLE库均complete。保存记录重排核对132次赢家全部正确；LOCAL67次、WHOLE61次所选donor不是全部发现邻居中空间最近者，未声称更近者必然可连接。全部132个接受阶段的GROUPS精确等于原组并集added_rows，原成员无丢失。

WHOLE每次接受都改变了LOCAL固定区域的旧模板结点：62/62次非零，最大0.377846p；LOCAL该区域70/70次为零。全G∪F参加5轮closest-segment/Huber IRLS，故不是仅声明整组可动或冻结prefix换颜色。该位移证明表达自由，不证明物理正确。

|种子|起点核|LOCAL接受/最终核|WHOLE接受/最终核|
|---|---:|---:|---:|
|21870|316|2/331|2/331|
|48496|48|17/281|17/281|
|64355|121|12/229|12/229|
|79841|121|9/274|7/249|
|112780|50|20/228|14/193|
|137016|188|10/425|10/425|

LOCAL70次、WHOLE62次；四至五组超过8次，没有8步上限。首/中/末：WHOLE序1为21870+10核，序32为137016吸收64185的75核，序62为48496+5核；LOCAL序1+10核，序36为112780+5核，序70为112780+12核。每接受先保存映射/checkpoint再重查。135份完整映射/checkpoint、350张PNG均保存。

六组两臂最终均NO_CONNECTABLE_FRAGMENT；闭合0，无候选/拟合/容量/时间截断。末库仍有邻居，但因无注册、端距、成员/切向/vertex、branch/parallel等无合格解释。自然穷尽仅指冻结2p邻域、双向注册及四端点解释范围，非所有注册偏移、全场景或16:00窗口耗尽。支持闭合代码/fixtures不等于真实场景闭合成功。

冻结计算：完整有限段邻域，保守索引+精确距离无top-k；最多8192成员/257结点，任一未完成禁止截断选优。位置Huber均值+二阶平滑+模板位移，LSQR五轮；统一归一化score排序，新增观测不须降低旧总残差。方向主要软排名，仍有75°gross-conflict及有限支持/contact/branch等明确守卫；无旧HISTORY15°或4p接受门。

**归属交叉统计：新增assigned / 撤回assigned / 旧组拆分数。**

|参考|LOCAL|WHOLE|
|---|---:|---:|
|START|374/0/0|335/0/0|
|M5|428/0/0|389/0/0|
|M4|3923/0/0|3884/0/0|
|v06_overlap|2323/1813/184|2281/1810/183|
|v06_common|2707/174/12|2668/174/12|

LOCAL最终122393 assigned/163563 UNKNOWN；WHOLE122354/163602。相对本轮起点分别吸收13和12个已有assigned组身份；无起点组拆分、无assigned变UNKNOWN。WHOLE少39 assigned是不同rollout，不是删掉本臂已接受核。v06损失/拆分含起点继承差异，不能按ID变号或累加历史收益解释；完整参考交叉表保留在ANALYSIS_EVIDENCE。

**WHOLE支持代理，单位p。**

|种子|实质M4贡献数|union|最长run|总gap|最大gap|起点域外|
|---|---:|---:|---:|---:|---:|---:|
|21870|2|105.371|98.344|0.669|0.371|1.561|
|48496|9|64.600|58.874|0.435|0.280|52.628|
|64355|6|44.565|39.328|0.344|0.344|25.558|
|79841|6|53.064|31.177|0.914|0.319|29.792|
|137016|7|110.724|81.813|0.074|0.074|72.887|
|112780|5|48.138|15.639|1.834|0.516|35.205|

除21870外五组满足三个M4贡献各12核/2p及4p域外的报告代理，但这不是接受门或物理认证。21870继承298核主片段，仅加15核、1.561p域外，不能称新完整曲线。64355末步独特支持仅0.023p、48496约0.444p，内填/重参数化不能每步算外延。112780 WHOLE union48.138p而最长run15.639p，LOCAL最长run32.548p，不能声称WHOLE普遍更优。

**已实际查看的视觉证据。** 全景完整盆栽及原有向外长尖刺仍在。137016/21870位于细长树干结构，不能把整个视野尖刺消失当结果。48496双视图近直；64355、79841、112780是短弯形，竞争图可见相邻异色/重叠轨迹。存在实质成员聚合和域外代理，但很小的原生墨迹无法可靠裁决全部平行/分支/深度身份。六个SCOPE均physical_context_complete=false；只覆盖所有查询donor，未覆盖全部投影竞争者。四个负例全景只有小线点，属于缺少有用否证证据，不能报全部通过。

START/MID/FINAL隔离图是同一目标行并集、按当时身份着色；起点已经显示后来吸收的原核。轮廓一致符合几何冻结，统一颜色不是新增物理观测。已看45张的精确列表及原图副本见delivery/ANALYSIS_EVIDENCE.json和delivery/figures；保留所有350张原图。

[WHOLE全景1](delivery/figures/scenes/ficus/stages/WHOLE_FINAL/test_r_1_FULL.png) · [全景79](delivery/figures/scenes/ficus/stages/WHOLE_FINAL/test_r_79_FULL.png) · [48496直段竞争](delivery/figures/scenes/ficus/diagnostics/48496/WHOLE_test_r_1_CONTEXT_CROP.png) · [64355曲段竞争](delivery/figures/scenes/ficus/diagnostics/64355/WHOLE_test_r_79_CONTEXT_CROP.png) · [79841竞争](delivery/figures/scenes/ficus/diagnostics/79841/WHOLE_test_r_1_CONTEXT_CROP.png) · [112780竞争](delivery/figures/scenes/ficus/diagnostics/112780/WHOLE_test_r_79_CONTEXT_CROP.png)。

**限制与后续（未运行）。** 最早不足不再是旧prefix不能动，而是独立身份/上下文证据、内部支持填充与外延混杂。没有确认某个新接受物理错误，也没有排除错误。保留全部坏例与死端。未来另行review冻结后，优先将同一LOCAL/WHOLE协议迁移scan24强M5完整背景，按起始数据预选双视图可辨的直/曲多片段种子；先补完整投影邻域/实际图像上下文与起点-新增-竞争核分离显示。保持本轮几何、半径、评分及无次数上限规则，不恢复HISTORY15度硬门，不扫阈值。实际scan24绑定/种子ID尚未审计；当前最终交付不启动实验。

现在只执行最终工程交付，不再启动新单元；停止原因是用户要求交付及MODEL_HANDOFF_NOT_COMPLETED，不是科学机制已穷尽。没有物理GT/held-out/时间稳定/概率/新颖性认证，parent独立验收PENDING。

CONFIG SHA256 bb5feab4f25a24c1314469975ffc6e3b30f98725ddcbb919d1e209ac5d44b42c；DECISION SHA256 bbba83327ec3436c141e7b284a8add94d33c9812883f0a14c4b1c35f3ffc6a07。全部源码/helper/snapshot逐项SHA、阶段真实退出、映射/checkpoint见DELIVERY_STATUS.json。包完整性与尺寸见delivery/PACKAGE_MANIFEST.json；外部运行环境依赖不冒称自包含。
