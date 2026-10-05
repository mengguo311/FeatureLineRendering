# 代表性原始 Gaussian 支持组：实际实验报告

本轮实际运行固定 vanilla30k 模型的独立多尺度证据、扩展贡献、联合固定ID选择和原生全模型T属性投影。当前模型为 **gpt-6.1-sol / xhigh**；基点 `.codex/config.toml` 为 **gpt-6-astra / ultra**，历史结果不改名。科学对象是固定原始Gaussian ID组，不是几何边缘恢复。

S0协议提交 `2b980d1807c7f22fdfbd7b186a44830c955c505d`、测试日志提交 `9595396b7736412353eeb9a5cfd210efe678a411` 已经SSH推送并读回。S0封条 `8c407d1247364bd6c3be4d8dc4122b062d9258cc1735f7f0cdef324930fa433b`；全部F选择封条 `b7631663af02cab5bae65cdbc93909dda30eaa89278aa0cb98ce6f3bf5cf182d`。

## S0—S4 实际阶段

| 场景 | S1 F证据 | S2共同容量 | S3五组预算 | S4 F / C / arc 原生姿态 | expanded eligible / unknown |
|---|---:|---:|---|---|---|
| mic | 8/8 | 64 | [336, 1007, 3356] | 8/8 / 8/8 / 33/33 | 55672 / 94213 |
| materials | 8/8 | 64 | [722, 2164, 7213] | 8/8 / 8/8 / 33/33 | 121531 / 26924 |

实际合成CPU测试：S0 8项RED→GREEN，G0扩展共13项通过（pixel/world单位、独立NMS、短组件/DETAIL、raw fullalpha需求、原始ID、饱和冗余、泄漏早停、输出约束）。独立CPU从保存的raw foreground CSR重算每场景64个ID的B分子/分母及offedge成本；全网格质量只交叉核对per-view统计，不冒称独立CUDA实现。native与媒体校验和人类科学验收分开。

## 管线原则与证据差异

RGB/depth/alpha三类各用自身梯度方向NMS；sigma=0.8/1.6/3.2 px，Mic八F各尺度各类正值ROI P99，Materials/C/arc原样继承。masked log median-depth沿用历史双层平滑处理，有效深度尺度不同于单次Gaussian。旧sigma=1.0与新多尺度不是相同证据合同。任意>=2尺度2px内支持形成MAJOR，原0.8 fine未持久响应完整保存DETAIL；短母组件>=3px保留其所有32px空间格片段。1/2px证据保留但不进入chunk目标。每chunk强度归一后等重，每视图/类1/24，空类不转赠。空间块不是自动恢复的物理曲线；网罩与材质纹理仍可跨尺度持久。旧广union/81.49% Mic C alpha容差区域只作历史背景，不是新MAJOR目标。

逐像素需求=0.5×原始full alpha，矩阵保存真实alphaT/demand；U=Σomega min(Σselected alphaT/demand,1)。全foreground网格保留非边缘反证，离MAJOR或DETAIL union>2px为offedge；成本为每F offedge mean(w/fullalpha)，八F均值。A历史TOP4 baseline_union独立排名，B新MAJOR+expanded贡献独立比率，C/D/E联合贪心λ=0/.1/.3。B分子为Σomega w/fullalpha，分母为等视图foreground mean(w/fullalpha)，可大于1，不是概率。三λ及三档固定预算全部显示；无C选英雄参数。懒堆增益按剩余需求精确更新；泄漏使目标可能非单调，不声称经典单调greedy保证。

## S1 实际像素与分块计数

下表是八F逐视图逐类像素实例之和，允许同位置多类出现；不是3D边缘数，不以少数成功。所有16张F预览及逐视图计数留out并列入ledger。

| 场景 | 类 | fine像素实例 | MAJOR像素实例 | DETAIL像素实例 | chunks |
|---|---|---:|---:|---:|---:|
| mic | color | 80222 | 90789 | 16614 | 1828 |
| mic | geometry | 90996 | 93768 | 28020 | 2514 |
| mic | outline | 42652 | 46881 | 2078 | 1726 |
| materials | color | 139450 | 189075 | 18252 | 4209 |
| materials | geometry | 142768 | 150918 | 44315 | 5641 |
| materials | outline | 35295 | 42297 | 2153 | 1431 |

| 类 | 旧sigma1 P99 | 新sigma.8 P99 | 新sigma1.6 P99 | 新sigma3.2 P99 |
|---|---:|---:|---:|---:|
| color | 0.2176102 | 0.271952 | 0.1692729 | 0.131632 |
| geometry | 0.01375083 | 0.01648456 | 0.01109015 | 0.01140937 |
| outline | 0.3689644 | 0.4399407 | 0.2417559 | 0.1231127 |

旧/new均是MicF正值ROI P99，平滑尺度与证据合同不同导致具体归一化值不同；没有从Materials或C/arc重估。旧文件路径与SHA256另列EVIDENCE_COUNTS.json。

mic 的新MAJOR/DETAIL union 2px带占C foreground alpha质量均值为 86.32%。分母是alpha>=.08前景alpha，与历史81.49%广union口径不同；不能直接当作改善量。新证据带仍较广，本轮未通过C缩窄它。
materials 的新MAJOR/DETAIL union 2px带占C foreground alpha质量均值为 76.32%。分母是alpha>=.08前景alpha，与历史81.49%广union口径不同；不能直接当作改善量。新证据带仍较广，本轮未通过C缩窄它。

## S2 截断完整性与校准

| K | 实际校准F | 通过门槛F | 最低weighted MAJOR mass | 最低MAJOR ray p10 |
|---|---:|---:|---:|---:|
| 32 | 16/16 | 15/16 | 0.960329 | 0.894206 |
| 64 | 16/16 | 16/16 | 0.995720 | 0.994315 |

TOP32失败视图及K64扩展真实记录见 COMPLETENESS.json。冻结操作门槛为每F weighted MAJOR mass>=.95且MAJOR射线p10>=.90，ROI alpha>=.08；全部通过也不等于数学全部贡献。完整归因始终 **FULL_ATTRIBUTION_UNDETERMINED**，所有选择是最后共同可用K的条件结果。每F/类foreground、MAJOR、DETAIL、offedge的mean/p10/p05/min/剩余质量保留；unobserved核不是nonedge。完整native投影与截断归因严格区分。

原始RGB/alpha/depth/median-depth与缓存逐元素按原冻结容差校准；前4 ID完全一致、w和depth按原容差。S4全一属性≈alpha，全部field bank的alpha/depth/median-depth与原RGB遍历完全相同。全原模型核位置、形状、opacity、排序保持；未删除核。属性黑底Q=Σ原始alphaT×固定ID指示量；原RGB白底SH0 clipped DC、kernel_size0，高阶45个SH系数未参与渲染，不能当完整材质反射验证。native alpha<=.99、alpha<1/255跳过、T<1e-4提前终止；“完整native”以这些定义为限。

## 所有预算的C定量结果（实际视图均值）

| 场景 | 预算 / 实际IDs | arm | C视图 | MAJOR需求覆盖 | DETAIL需求覆盖 | offedge alpha贡献比例 | offedge占selected质量 |
|---|---|---|---:|---:|---:|---:|---:|
| mic | 336 / 336 | A | 8 | 0.0314 | 0.0004 | 0.0000 | 0.0009 |
| mic | 336 / 336 | B | 8 | 0.0190 | 0.0038 | 0.0005 | 0.0181 |
| mic | 336 / 336 | C | 8 | 0.1886 | 0.2169 | 0.0591 | 0.0717 |
| mic | 336 / 336 | D | 8 | 0.1887 | 0.2176 | 0.0512 | 0.0604 |
| mic | 336 / 336 | E | 8 | 0.1835 | 0.2108 | 0.0321 | 0.0417 |
| mic | 1007 / 1007 | A | 8 | 0.0897 | 0.0071 | 0.0005 | 0.0064 |
| mic | 1007 / 1007 | B | 8 | 0.0592 | 0.0096 | 0.0013 | 0.0201 |
| mic | 1007 / 1007 | C | 8 | 0.3366 | 0.3574 | 0.1282 | 0.0961 |
| mic | 1007 / 1007 | D | 8 | 0.3319 | 0.3524 | 0.1109 | 0.0854 |
| mic | 1007 / 1007 | E | 8 | 0.3256 | 0.3482 | 0.0820 | 0.0667 |
| mic | 3356 / 3356 | A | 8 | 0.2069 | 0.0747 | 0.0027 | 0.0097 |
| mic | 3356 / 3356 | B | 8 | 0.1720 | 0.0412 | 0.0063 | 0.0266 |
| mic | 3356 / 3356 | C | 8 | 0.5747 | 0.5455 | 0.2606 | 0.1180 |
| mic | 3356 / 3356 | D | 8 | 0.5701 | 0.5374 | 0.2183 | 0.1039 |
| mic | 3356 / 3356 | E | 8 | 0.5553 | 0.5219 | 0.1679 | 0.0861 |
| materials | 722 / 722 | A | 8 | 0.0207 | 0.0041 | 0.0005 | 0.0567 |
| materials | 722 / 722 | B | 8 | 0.0160 | 0.0090 | 0.0006 | 0.0655 |
| materials | 722 / 722 | C | 8 | 0.0565 | 0.0683 | 0.0222 | 0.2266 |
| materials | 722 / 722 | D | 8 | 0.0573 | 0.0703 | 0.0188 | 0.2004 |
| materials | 722 / 722 | E | 8 | 0.0564 | 0.0719 | 0.0148 | 0.1759 |
| materials | 2164 / 2164 | A | 8 | 0.0475 | 0.0173 | 0.0014 | 0.0497 |
| materials | 2164 / 2164 | B | 8 | 0.0432 | 0.0302 | 0.0020 | 0.0667 |
| materials | 2164 / 2164 | C | 8 | 0.1376 | 0.1497 | 0.0695 | 0.2551 |
| materials | 2164 / 2164 | D | 8 | 0.1368 | 0.1520 | 0.0588 | 0.2324 |
| materials | 2164 / 2164 | E | 8 | 0.1341 | 0.1564 | 0.0449 | 0.1967 |
| materials | 7213 / 7213 | A | 8 | 0.1309 | 0.0997 | 0.0065 | 0.0491 |
| materials | 7213 / 7213 | B | 8 | 0.1286 | 0.1344 | 0.0099 | 0.0778 |
| materials | 7213 / 7213 | C | 8 | 0.3449 | 0.3607 | 0.1782 | 0.2492 |
| materials | 7213 / 7213 | D | 8 | 0.3411 | 0.3646 | 0.1581 | 0.2320 |
| materials | 7213 / 7213 | E | 8 | 0.3329 | 0.3626 | 0.1255 | 0.2022 |

需求覆盖是渲染证据处所需alpha支持的饱和效用，不是真实边缘准确率。offedge alpha比例是Σoffedge Q / Σoffedge alpha；selected漏出比例分母是Σ全图Q。两个分母不同；不能只看漏出占比或少核数。完整逐视图、class/chunk、宽度、原始mass结果与F/C前沿保留。

## 仅F选择的coverage-match点

| 场景 | arm | 固定IDs | F目标U | C实际views | C MAJOR覆盖 | C offedge alpha比例 |
|---|---|---:|---:|---:|---:|---:|
| mic | A | 1007 | 0.09228 | 8 | 0.0897 | 0.0005 |
| mic | B | 827 | 0.09228 | 8 | 0.0480 | 0.0011 |
| mic | C | 72 | 0.09228 | 8 | 0.0801 | 0.0168 |
| mic | D | 72 | 0.09228 | 8 | 0.0789 | 0.0134 |
| mic | E | 73 | 0.09228 | 8 | 0.0787 | 0.0093 |
| materials | A | 2164 | 0.06318 | 8 | 0.0475 | 0.0014 |
| materials | B | 898 | 0.06318 | 8 | 0.0199 | 0.0008 |
| materials | C | 244 | 0.06318 | 8 | 0.0227 | 0.0060 |
| materials | D | 244 | 0.06318 | 8 | 0.0225 | 0.0056 |
| materials | E | 247 | 0.06318 | 8 | 0.0222 | 0.0041 |

这些点仅用F最短前缀选择，C没有重新匹配覆盖。跨视图C覆盖可以偏离目标，应报告差异。所有标准预算是同数量比较，早停时另有实际同数量基线；本轮实际早停情况见ASSET与selection JSON。

## 实测权衡：本轮不支持目标成功

**mic中档同数量**：A的C MAJOR覆盖为0.0897、offedge alpha比例0.000463；联合λ0为0.3366/0.128167，λ.3为0.3256/0.081978。λ.3相比λ0漏出改变-36.0%，MAJOR覆盖改变-3.3%；相对旧A依然明显增加非边缘贡献。这是覆盖/漏出权衡，不能称全面优势。
仅F选定λ.3 coverage匹配前缀73 IDs，在C的MAJOR覆盖是A的0.877倍，offedge alpha贡献是A的20.189倍。F匹配没有自动保持C的同覆盖，少ID不能当作成功。

**materials中档同数量**：A的C MAJOR覆盖为0.0475、offedge alpha比例0.001408；联合λ0为0.1376/0.069531，λ.3为0.1341/0.044879。λ.3相比λ0漏出改变-35.5%，MAJOR覆盖改变-2.5%；相对旧A依然明显增加非边缘贡献。这是覆盖/漏出权衡，不能称全面优势。
仅F选定λ.3 coverage匹配前缀247 IDs，在C的MAJOR覆盖是A的0.468倍，offedge alpha贡献是A的2.944倍。F匹配没有自动保持C的同覆盖，少ID不能当作成功。

冻结λ惩罚确实改变联合组的漏出/覆盖前沿，但本轮没有证据支持“同时保留主要边界并比独立组减少非边缘泄漏”的总体目标。独立人工视觉判定仍PENDING；工程完成不转译成科学GO。参数、预算、证据、相机与λ均未为这些C结果更改。

## 负结果、工程结论与科学范围

成功诊断需同预算覆盖不崩塌且漏出下降，本报告直接展示两者，不因C调阈值。Gaussian整核足迹可能宽、含非边缘支持，不能用投影剪裁或逐视图mask伪造细线。ink宽度仅area(Q>threshold)/独立ridge像素数与Q加权到证据距离，单位px，不是物理边缘宽度。outline始终视角相关；geometry只是深度/遮挡证据；核在不可见视图不作为负例。未知核不被判nonedge。

模型视觉观察与人类验收另存[VISUAL_REVIEW_ZH.md](VISUAL_REVIEW_ZH.md)；**独立人类科学结论PENDING**。C是归因构造留出，GS训练见过全部TRAIN；旧媒体/demo已知，不称盲测。未使用人工标注、mesh、TEST、重训、中心连接、曲线拟合或几何P/R。未宣称时序优势或第三方方法复现。

内核来自第三方RaDe分支，历史阶段独立插桩，本轮复用TOP32及隔离容量扩展；不是原创RaDe。方法受weighted coverage/set-cover式饱和效用与已有贡献提升启发，不提出未经证明的新颖性或研究博客主张。历史audited core/native/media复制到本阶段，源码来源及SHA256在SOURCE_MAP。

## 实际交付与复现

- **mic**：[全部视图](figures/mic_all_views.jpg) · [全部C](figures/mic_C8.jpg) · [arc首中末](figures/mic_arc_first_mid_last.jpg) · [F选定覆盖匹配C图](figures/mic_C_coverage_match.jpg) · [F/C全部λ前沿](figures/mic_frontier.png) · [Telegram1600视频](media/mic/arc33_telegram1600.mp4) · [固定ID JSON](assets/mic/selected_ids.json)。
- **materials**：[全部视图](figures/materials_all_views.jpg) · [全部C](figures/materials_C8.jpg) · [arc首中末](figures/materials_arc_first_mid_last.jpg) · [F选定覆盖匹配C图](figures/materials_C_coverage_match.jpg) · [F/C全部λ前沿](figures/materials_frontier.png) · [Telegram1600视频](media/materials/arc33_telegram1600.mp4) · [固定ID JSON](assets/materials/selected_ids.json)。

实际大型数组、native视频及逐姿态原始投影保留于 `/home/u00134/3dgs_line/representative_edge_gaussians_v1/out/representative_edge_gaussians_v1`，精确路径/每文件SHA256见 SOURCE_MAP.json；不修改旧demo/report。媒体保留native800所有完整帧，不cut arc；原始gain1，非匹配墨量。每段H264/yuv420p/+faststart，33帧逐帧解码，去标题RGB内容互异、相机hash/尺寸核验。图组12张（每场景6张），完整C所有预算单帧原始图留out。

[复现步骤](REPRODUCE.md)、[协议](PROTOCOL.md)、[机器FINAL](FINAL.json)、[来源ledger](SOURCE_MAP.json)。STATUS原子记录实际阶段；plain runner按per-pose seal恢复；未运行不是0，工程阻碍如实记录。

## 实际耗时与资源

截至2026-10-04T23:52:43.006892+00:00，本轮wall 41.2分钟（预算90分钟），native实际486次调用，CUDA同步调用耗时合计3.52秒；这不是总wall或全部GPU占用。K64隔离编译65.99秒。CPU线程2，阶段时间与空间余量见RUN_TIMINGS.json。

工程实际结论：全部98姿态、32次expanded F容量校准、16F贡献遗漏界限、CPU独立算术及完整媒体检查通过，**engineering GO**。Mic F_079的K32 p10=.894206低于.90，K64容量-only编译一次成功，全16F通过操作门槛；K128未运行（无需扩至该容量），没有工程阻碍被隐瞒。数学完整归因UNDETERMINED；总体科学目标本轮不支持，独立人类视觉判定PENDING。
