# unit004 保存结果分析：有限重叠模型竞争

**执行完成，科学结论PARTIAL；没有观察到联合选择优于同库贪心。** 两臂选择完全相同的7个假设、全行归属差异0，68对实际PNG逐字节相同。当前可保存为有限重叠归组结果，不能称新增直线与曲线的双视图改善，更不能称物理身份已确认。

父级[实际退出记录](../../orchestration/unit_004/COMPUTE_EXIT.json)为returncode=0、reason=null、actual_child_exit=true；07:21:45.503607至07:22:13.394110 JST。RUN_RESULT记录运行27.088秒，solver累计0.0214秒，0次拟合、0个新空间候选。两份458490行映射已由runner冷载，mapping checkpoint先于图像交付；本分析重新验证两份checkpoint全部文件哈希。双相机全景和诊断共136张真实原核PNG；不包括tests中的合成夹具。没有在分析中重新拟合、渲染、测试或修改源码。

本轮只处理5452条保存成功overlap关系形成的1917个分量中的8个完整分量：42个M4叶、38条关系。其余1909个分量未运行；ficus/scan65未运行。端点续接不在本轮模型内。8个假设库均完成，3个库为空，合计11个可行假设；两臂求解均完成，没有超时或预算截断。连接分量仅用于竞争闭包，不能直接当edge_id。

最早瓶颈在模型库生成：76次有向anchor/donor检查中63次残差拒绝、2次有限域拒绝、11次兼容；随后11个前缀组均通过组守卫。63次残差拒绝全部q95>0.5p，其中38次另有max>1p，10次另有tangent>30°（重叠计数）。例如10976解释273281时max=0.705p但q95=0.660p；反向max=3.302p。保存的成功overlap来自联合拟合，不能据此推断任一原叶q可作为共同模型。这是模型覆盖负结果，尚不是求解器失败；仅2次有限域拒绝也不支持扩大有限域。

两臂assigned=246416、UNKNOWN=212074；相对输入M4新增assigned67、丢失0、改变归属行265。**相对unit003新增54、丢失3726、改变7192行，assigned净减少3672。** 这是冻结设计恢复M4、未继承unit003新路径的结果，不能宣传为其累积升级。M4旧组保留；不声称保留unit003的派生身份。UNKNOWN及最多两个替代解释保留，所有新组仍provisional。

下表为两臂共有的7个组。全部anchor域外支持为0；这是重叠观测统一，不是host外延。支持并集不能代替最长连续观测，有限载体长度更不是完整观察到的边长。

| edge_id | 叶/核 | 支持并集p | 最长段p | 有限载体长度p | 总gap/max gap p | 重复支持p |
|---|---:|---:|---:|---:|---:|---:|
| 10975 | 2/68 | 14.274 | 3.495 | 18.728 | 4.453/0.383 | 1.613 |
| 50830 | 2/70 | 9.742 | 3.622 | 11.726 | 1.984/0.316 | 2.257 |
| 18608 | 3/453 | 108.260 | 4.153 | 134.385 | 26.125/0.358 | 6.976 |
| 57127 | 2/272 | 74.483 | 2.014 | 92.025 | 17.542/0.422 | 0.734 |
| 57133 | 2/43 | 6.814 | 3.484 | 7.156 | 0.342/0.324 | 1.029 |
| 57153 | 3/105 | 21.280 | 3.946 | 26.028 | 4.748/0.335 | 2.602 |
| 113545 | 4/304 | 62.386 | 6.240 | 78.508 | 16.090/0.368 | 8.642 |

完整[GROUP_STATISTICS](scenes/scan24/stages/joint/GROUP_STATISTICS.json)保存parent贡献、bbox/extent、coverage。7组均有至少两个实质原parent贡献，但parent是来源而非真值。18608共有453核，原parent400贡献402核、约106.563p支持，另两parent为24/27核；因此大长度主要继承。其支持并集108.260p、最长段仅4.153p，coverage约0.806。不得把同色长载体描述为新生完整长曲边。

实际全景仍呈现建筑窗口、屋檐、柱边碎裂与尖刺。核参数固定，归组不能消除原几何噪声；未绘制辅助carrier或无支持桥。下图为joint实际全景，两臂文件相同。

![0012原核全景](scenes/scan24/stages/joint/0012_FULL.png)

![0036原核全景](scenes/scan24/stages/joint/0036_FULL.png)

18608是最大polyline-anchor选择例，但两视图都呈近直细线，邻域中存在贴近彩色细段；这不足以确认新的曲线统一或排除深度/平行误吞。单组与完整邻域均已检查；曲线标签不能充当可见曲率证据。

![18608单组0012](scenes/scan24/stages/joint/diagnostics/OVERLAP_18608_cc772950_GROUP_0012_CROP4.png)

![18608邻域0036](scenes/scan24/stages/joint/diagnostics/OVERLAP_18608_cc772950_CONTEXT_0036_CROP4.png)

57153最大line-anchor组在0036只见短红段，在0012单组及完整邻域为空；不能给出双视图直线改善。REFERENCE_201906的浅U形可见，但属于继承参考，且缺成功overlap关系，不能作为本轮新增曲线。REFERENCE_10975使用固定参考行集合，不等同于新假设10975的完整成员，不能混读。没有两臂不同身份，所以top3不同身份选择为空，不是漏渲染。

![57153单组0036](scenes/scan24/stages/joint/diagnostics/OVERLAP_57153_8d4af51f_GROUP_0036_CROP4.png)

![57153单组0012为空](scenes/scan24/stages/joint/diagnostics/OVERLAP_57153_8d4af51f_GROUP_0012.png)

固定负例84842/362883、153248/377058、153427/153430的所查裁剪只呈极细段或小斑点，不能确认parallel/branch/depth安全。301451/301459在两相机的单组与邻域全部为空，gap反例不可判。共36个两臂配对裁剪条目有6个空条目，保留native空图且不换相机；其余30条有裁剪。无物理GT、无新held-out；算法守卫通过不等于真实安全认证。

来源：DECISION SHA256 `fb79a081d1d124e2fa9869359e406544f4147a525c974f0f356f28955465d6c6`；CONFIG SHA256 `8833bdc5483c456e7803effe5b88f82df0d7c730e6d2119fe8b2dd6d9f223b1c`。依据[PARENT_RUN_FROZEN](PARENT_RUN_FROZEN.json)核验28个source_snapshot文件及2个获准外部helper，全部匹配；不用后续可变HEAD替代快照。[GEOMETRY_AUDIT](GEOMETRY_AUDIT.json)记录458490原核、行序及means/covariance/opacity等字段未改变，carrier_geometry_rendered=false。运行入口为冻结snapshot对应的overlap_runner.py，父级批准命令为Python -B SCRIPT --config CONFIG，详见[RUN_REQUEST](RUN_REQUEST.json)。本分析不创建SEAL，由parent封存闭合产物；实际退出不覆盖。

唯一下一步建议：在相同8个完整竞争分量内引入**共同双叶有限模型**，检验“固定旧叶q”是否限制重叠归组。保留旧anchor库为对照；若保存记录无拟合q，仅下一父计算按原冻结拟合规则对38个成功对各生成一次辅助模型，原核不变、模型不渲染。扩充后的同一库继续配对greedy/MILP，有限域及全部几何阈值不放宽。新模型的成员/收益规则须在下一DECISION冻结，不能混入本轮。若仍无可辨跨片段直线及曲线收益，保留负结果；不以更多assigned或更高目标补救。详见[NEXT](NEXT.json)，**PROPOSED/NOT_RUN**。当前授权窗口尚有时间，不因这次负结果停止全部研究。
