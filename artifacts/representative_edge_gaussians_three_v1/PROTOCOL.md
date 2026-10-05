# S0：Lego / Chair / tree=Ficus 重复冻结 contributor 实验

基点 d5265b4b71f635bac6563ad12466e4abcd2e1ffb，分支 representative-edge-gaussians-three-v1，实际 CLI gpt-6.1-sol / xhigh。独立目录仅写 artifacts/representative_edge_gaussians_three_v1 和 out/representative_edge_gaussians_three_v1；旧代码、模型、build、归一化、报告均只读。tree 展示别名明确为 tree / Ficus (ficus)，内部原 scene ID 为 ficus；不替换为 drums。

本轮重复已完成 Mic/Materials 方法。原 scientific representative_core.py 与 legacy_core.py 必须逐字节相同；所有继承文件散列和完整差异在 ALGORITHM_BINDINGS.json / ALGORITHM_DIFF.patch。改变仅限场景和输出绑定、旧 Mic 正规化数值导入、日期资源、之前不存在的 A 同算法新计算、场景预算和真实报告。S0 清单和全部代码/配置/测试先提交推送并读回，才读生产 F 像素；S0 不随结果重写。

## 冻结科学合同

每场景 F=[1,14,27,41,53,67,79,93]，C=[7,21,33,47,59,73,86,99]，完整 arc0_000..032；49 姿态/场景，总147。输入 hybrid_raster_evidence_v2 的同一 native800 / SH0、full alpha、depth/median-depth、TOP4 original IDs/alphaT。模型为 tier1 vanilla30k seed1729 原始 PLY；不读取 raw TRAIN 图像、mesh、TEST、2DGS normals，不重训，不人工标注，不中心连接或拟合。

新多尺度归一化直接导入上一轮 persisted Mic 八F P99：sigma0.8=[0.2719520097970962,0.016484559662640084,0.43994068741798414]；1.6=[0.16927293375134467,0.011090149898082007,0.2417559476196766]；3.2=[0.1316320051252842,0.011409368803724632,0.12311269983649253]。类别顺序 color/geometry/outline。不得在新场景/C/arc 重估。RGB、masked log median-depth、alpha 用自身梯度方向 NMS；原深度双层平滑原样保留。阈值.1，任意≥2尺度在2px内支持 MAJOR，原0.8 fine非持久响应全部存 DETAIL。8连通母组件≥3px进入32px绝对空间tiles；每chunk强度归一、chunks等重，每F/class 1/24，空类不转赠。组件长度不是物理曲线标签。

所有原 foreground alpha≥.08 的网格上，距 MAJOR或DETAIL union >2px为offedge。原alphaT/fullalpha，绝不重新归一化截断贡献。需求=.5 fullalpha，U=Σomega min(Σselected alphaT/demand,1)；漏出成本为每F完整foreground offedge mean(alphaT/fullalpha)再八F均值。未知核不是非边缘；raw visibility mass≥1、visible F≥2才eligible。

K32→K64→K128，逐F校准RGB/alpha/depth/median-depth/前4 ID,w,depth，全部容差沿用code/config.json。每F weighted MAJOR capturedmass≥.95且major ray p10≥.90；操作通过仍 FULL_ATTRIBUTION_UNDETERMINED。K64仅经helper验证历史 BUILD、二进制SHA256 57c8ffbe5fb190369548667097a9c9106bd566775747045749a2b2f976a49b5f、capacity-only源码替换及patch后只读引用；无需重建。先完成三个场景全部F容量调度，再选择。门槛/相机失败按场景工程无效处理，不能冒充科学NO-GO；保存已完成阶段并继续合格场景，不跳过相机声称全场景完成。

## A基线与预算：规则在像素前冻结

A不是历史已有科学资产。它是 EXACT historical baseline_union 同算法新算，只用本场景八F TOP4。旧sigma1 Mic-only P99固定 color=.2176101744174957、geometry=.013750831419602035、outline=.3689644494652748；完整历史cfg和normalization文件绑定。调用逐字节原legacy_core.evidence_fields/compute_evidence/view_statistics/aggregate_views。A baseline只依赖中心独立证据 numerator；不生成无关side arm（side_numerator为零，不影响baseline）。每view numerator/denominator均除该view全网格TOP4 raw cached mass后求和比率；不可改为普通raw总比率。保存每F全部统计、未知/不可靠标记，独立float64布尔掩码采样CPU和合成等view质量测试核验。

原rank_tiers代码已核实：从A eligible original IDs中按baseline_union降序、ID升序tie，ceil(eligible人数×p/100)，p=[1,3,10]。具体counts由八F新A生成后写BUDGET_SEAL，先封存再任何选择/C/arc。所有A/B/joint同样original-ID counts，不按expanded eligible另算百分比。

B沿用expanded independent major ratio；C/D/E joint λ=[0,.1,.3]全呈现，净边际≤1e-15早停不填充。若不同count另评同count A/B。coverage-match只在F使用A中档U，取各arm最早达到的前缀，否则null。全部三个场景所有F selectedIDs、counts、normalization、coverage prefixes和全局F_SELECTION_SEAL在C/arc像素首次读取前封存；之后不改。

## 原生评价、交付和资源

投影完整原模型T、排序、opacity，不删其他Gaussian，无per-view mask剪成细线。固定原ID field黑底Q=Σselected原alphaT，全一field校准full alpha，各field alpha/depth必须精确不变。SH0 clipped DC白底RGB，未用高阶SH，保留模型全部字段。native alpha clamp .99、skip<1/255、T<1e-4原样。每场景全部8C和8F三预算、F匹配和实际同count点，全部33arc中档五arms。gain1，不匹配墨量。六图/场景，native及Telegram1600 H264/yuv420p/+faststart完整33帧；独立解码33、去标题RGB内容distinct、精确camera hashes。独立CPU保存CSR算术+full-native残差界限，不声称独立重写CUDA。

C是归因构造留出，相机已GS TRAIN见过，旧媒体已知，非盲测/非GS unseen。报告coverage/leakage连续数值和F匹配C迁移及坏点，不posthoc改参数；工程GO与科学结果分离，人类独立下载查看PENDING。Mic/Materials旧负结果保持原义；不同模型/复杂度和固定Mic归一化不得当理想跨场景公平性。第三方RaDe原内核与历史项目独立插桩分别署名，无新颖性/论文复现claim。

新科学输出≤10GiB，root≥2GiB，commonGit≥1GiB；每大写/native call guard估计未压缩payload、临时副本和available RAM，GPU0只有无任何外国PID（同用户也拒绝）才运行。CPU2，指定vfsdgs Python，无global安装，不删除旧资产。新鲜7200秒deadline见config；atomic perpose seals/status、独立nohup plain runner、恢复只跳过已校验。阻碍时未跑字段null，不伪造0。仅显式git add --sparse新stage/config和适量媒体，SSH push读回commit与文件hash，clean status。
