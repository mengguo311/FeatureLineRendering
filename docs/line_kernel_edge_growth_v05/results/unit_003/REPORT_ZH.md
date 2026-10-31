unit_003 已完成完整 scan65（skull）的 L0→两次L1池化→一次M2拓扑合并，执行状态 **completed**，科学结论 **PARTIAL**。parent实际数值子进程返回码0、reason=null；2026-10-31 06:32:32至06:38:21 JST，runner记录349.319秒。7个请求阶段全部落盘，无缺失请求阶段。没有用launcher退出或未保存内存进度替代实际结果。

279616个原始LINE核全部保留，L0/L1/M2各有全行membership、有限载体/支持区间、谱系及0012/0036两张原生全景。没有M2后池化、L3/L4或旧场景重跑。主图始终是原始核，仅改颜色；原位置、协方差、宽度、opacity、数量和行序未变，不渲染辅助载体或不存在的间隙桥。

|级别|分配核|UNKNOWN|覆盖率|主组数|
|---|---:|---:|---:|---:|
|L0/强v03|97950|181666|35.0302%|3490|
|L1/固定宿主池化|112061|167555|40.0767%|3450|
|M2/一次拓扑合并|114798|164818|41.0556%|3402|

L1比L0增加14111个分配核，M2比L1增加2737核。L1第一pass为19841次fit、3925接受事件，第二pass累计30000次fit、4363事件，预算没有补充重置；M2新一层30000次fit、11076载体合并事件。大量合并涉及未激活seedlet，事件数不是新增主边缘数。L0记录fit_count=0表示初始化不计入该预算，并非没有拟合。

L1/M2分别记录4949/12360次fit_cap拒绝，完成的是冻结截断预算下的流程，不是穷尽候选。M2拒绝/竞争记录包括510 parallel、31 branch、2576 tangent、16682 endpoint_tangent、42744 endpoint_gap、4630 ambiguous和7749 round_conflict。不能据计数直接诊断唯一瓶颈，更不能用放松所有距离解决。

保存的旧片段增长门槛通过17组：10 line、7 polyline。它们有支持域外增长，但其中只有3组跨原始primitive parent，且仅这3组具有至少两个原始parent各≥6核且≥2p支持。v03碎片、L1载体、原始parent必须分开统计。17组不能改写为17个跨原始parent物理实例，≥5实质跨原始parent目标未达成。

|增长组/模型|L1贡献核|最大L1支持→M2并集(p)|域外支持(p)|最长连续段(p)|最大/总间隙(p)|有限载体长度(p)|
|---|---|---|---:|---:|---|---:|
|62791/line|99+60|16.053→27.362|11.321|4.990|1.159/4.853|32.215|
|167261/polyline|35+35|8.698→14.703|5.932|1.856|0.348/4.117|18.848|
|36352/polyline|38+27|7.260→13.521|6.136|1.744|0.347/3.093|16.620|

62791的七个原始parent中五个达到实质支持门槛；167261的次要parent仅11核/2.119p，36352的次要parent仅9核/2.017p，后两者贡献仍高度不平衡。不同parent的支持可能重叠，不能将贡献长度直接求和当总支持。完整bbox、extent、各前驱有限域、parent贡献和间隙见[GROUPS.json](scenes/scan65/stages/M2_MERGE_ONLY/GROUPS.json)，区间数组见[CARRIERS.npz](scenes/scan65/stages/M2_MERGE_ONLY/CARRIERS.npz)。支持并集长度不等于连续物理边缘长度。

已实际查看48张保存的原生/辅助PNG，全单元保存138张。文件散列和逐例观察见[VISUAL_REVIEW.json](VISUAL_REVIEW.json)。本分析没有拟合、重渲染、生成新裁剪或修改源码。两相机全景可见整体仍碎片化；相同核几何导致轮廓相同，着色变化本身不是延伸证据。

|级别|0012|0036|
|---|---|---|
|L0|[原生全景](scenes/scan65/stages/L0/0012_FULL.png)|[原生全景](scenes/scan65/stages/L0/0036_FULL.png)|
|L1|[原生全景](scenes/scan65/stages/L1/0012_FULL.png)|[原生全景](scenes/scan65/stages/L1/0036_FULL.png)|
|M2|[原生全景](scenes/scan65/stages/M2_MERGE_ONLY/0012_FULL.png)|[原生全景](scenes/scan65/stages/M2_MERGE_ONLY/0036_FULL.png)|

62791（直线续接）：0012 [L1](scenes/scan65/stages/M2_MERGE_ONLY/diagnostics/CROP_62791_0012_GROUP_62791_L1_0012.png) / [M2](scenes/scan65/stages/M2_MERGE_ONLY/diagnostics/CROP_62791_0012_GROUP_62791_M2_0012.png) / [parent](scenes/scan65/stages/M2_MERGE_ONLY/diagnostics/CROP_62791_0012_GROUP_62791_PARENTS_0012.png)；0036 [L1](scenes/scan65/stages/M2_MERGE_ONLY/diagnostics/CROP_62791_0036_GROUP_62791_L1_0036.png) / [M2](scenes/scan65/stages/M2_MERGE_ONLY/diagnostics/CROP_62791_0036_GROUP_62791_M2_0036.png) / [parent](scenes/scan65/stages/M2_MERGE_ONLY/diagnostics/CROP_62791_0036_GROUP_62791_PARENTS_0036.png)。

167261（短弧续接）：0012 [L1](scenes/scan65/stages/M2_MERGE_ONLY/diagnostics/CROP_167261_0012_GROUP_167261_L1_0012.png) / [M2](scenes/scan65/stages/M2_MERGE_ONLY/diagnostics/CROP_167261_0012_GROUP_167261_M2_0012.png) / [parent](scenes/scan65/stages/M2_MERGE_ONLY/diagnostics/CROP_167261_0012_GROUP_167261_PARENTS_0012.png)；0036 [L1](scenes/scan65/stages/M2_MERGE_ONLY/diagnostics/CROP_167261_0036_GROUP_167261_L1_0036.png) / [M2](scenes/scan65/stages/M2_MERGE_ONLY/diagnostics/CROP_167261_0036_GROUP_167261_M2_0036.png) / [parent](scenes/scan65/stages/M2_MERGE_ONLY/diagnostics/CROP_167261_0036_GROUP_167261_PARENTS_0036.png)。

36352（小弯段）：0012 [L1](scenes/scan65/stages/M2_MERGE_ONLY/diagnostics/CROP_36352_0012_GROUP_36352_L1_0012.png) / [M2](scenes/scan65/stages/M2_MERGE_ONLY/diagnostics/CROP_36352_0012_GROUP_36352_M2_0012.png) / [parent](scenes/scan65/stages/M2_MERGE_ONLY/diagnostics/CROP_36352_0012_GROUP_36352_PARENTS_0012.png)；0036 [L1](scenes/scan65/stages/M2_MERGE_ONLY/diagnostics/CROP_36352_0036_GROUP_36352_L1_0036.png) / [M2](scenes/scan65/stages/M2_MERGE_ONLY/diagnostics/CROP_36352_0036_GROUP_36352_M2_0036.png) / [parent](scenes/scan65/stages/M2_MERGE_ONLY/diagnostics/CROP_36352_0036_GROUP_36352_PARENTS_0036.png)。

62791在0036中清楚呈短直线，0012中严重缩短；167261的0036可辨短弧，0012仅为很小斜段；36352在0012是小弯段，0036接近端视。它们是暂定续接示例，尚不足以在两个视角都清楚验证直线/曲线拓扑。所有L1/M2分组对照采用同一最终成员行集，轮廓原本就相同；支持域映射和显著贡献提供数值延伸证据，图片用于寻找明显误并，不以改成单色证明增长。

固定最大组238627、61267、67265均查看双视图，能看到较长曲线。但三者M2等于其L1前驱，gain=0、outward=0，属于既有组/池化结果，不能代替新增长曲线。尤其238627虽然支持77.511p、287核，当前轮没有延伸。

六类精确版本上下文全部查看双相机：parallel、branch、crossing_tangent、gap、ambiguity、accepted_worst_margin。它们多数仅几个原生像素；确定性4倍最近邻放大不能恢复不存在的深度或三臂信息。详情与完整成员行引用见[CONTEXT_SELECTION.json](scenes/scan65/stages/M2_MERGE_ONLY/diagnostics/CONTEXT_SELECTION.json)。169208+169213因最大切向30.000381°被拒；29836+180783最差接受例为29.996774°，接近30°上限。间隙拒绝160075+160083距阈值仅0.000030185p。没有把守卫记录、图片存在或看不清楚当成物理正确性；平行/深度/分支视觉否证仍未全面解决，故科学结论PARTIAL。

三个场景的同设置M2现已实际交付。按保存GROUPS字段分别统计如下，不改写任何旧单元结论：

|场景|旧片段增长门槛组|跨原始parent增长组|两个实质原始parent增长组|
|---|---:|---:|---:|
|scan24/unit_001|29|21|19|
|ficus/unit_002|10|4|3|
|scan65/unit_003|17|3|3|

场景间差别明显；这不是独立held-out泛化证据。unit_001初次视觉选择漏掉实际增长例子的历史结论仍保留，unit_002仅增加保存组重放证据。v04仍为历史PARTIAL，其失败/未知退出不会被本轮的0覆盖。

18份parent冻结源码快照、18个配置helper引用（4个允许外部helper和14份旧快照）、17个输入引用、11个完整checkpoint的哈希均验证。三份membership重新读取并验证完整279616行/连续行号/原始primitive_id，L0等于强v03，前级分配没有退回UNKNOWN；保存载体和支持区间为有限值。逐字段bitexact冷载geometry审计及原Gaussian NPZ散列核对通过。详见[ANALYSIS_AUDIT.json](ANALYSIS_AUDIT.json)及[ANALYSIS_PROVENANCE.json](ANALYSIS_PROVENANCE.json)。这没有重新拟合或重算科学判据。

CONFIG SHA256：`f376f26ceeb9676cb6616edc0fcd266dc561c783bbec58d7fd1721722eb49f5c`。DECISION SHA256：`d92a677d4fac60cc2c0388d551b4f6606e5d5e4dbf475e50d0d42b6f11d7e7d4`。实际命令、输入/helper散列与可独立验证的source_snapshot路径见provenance，实际退出见[PARENT_COMPUTE_RECEIPT.json](PARENT_COMPUTE_RECEIPT.json)。未来验证不依赖工作树latest HEAD。真实RED→GREEN及接口测试保留，分析未新增测试或改源码。

下一独立实验建议从scan24已封存M2追加**恰好一轮**M3拓扑合并，不池化、不重做初始化、不改变候选/拟合/守卫参数。单轮每载体仅一次合并可能限制渐进延伸，但这仍是待检验假设，fit-cap也仍存在。scan24有较强的现存跨parent增长基础，可直接检验已有片段能否进一步连成更大的直线/曲线。比较强v03、池化L1、M2和新M3，明确即时前驱为M2，另外统计三段以上L1实质溯源，不能把旧大组或更多事件当新增长。parent预算1800秒，1380秒前保存完整M3状态，最后420秒交付双相机全景/分组；精确输入checkpoint/hash、控制、目标、资源及否证见[NEXT.json](NEXT.json)。本分析没有执行该实验。

单位现有输出约153MB。[SEAL.json](SEAL.json)仅覆盖本单元已关闭静态文件，不包含不断增长的orchestration/API日志和未来parent验收文件。所有分组身份仍为provisional，没有RGB源GS、GPU、训练、几何移动或插入间隙；12:00 JST后不开新单元，science在12:35结束。
