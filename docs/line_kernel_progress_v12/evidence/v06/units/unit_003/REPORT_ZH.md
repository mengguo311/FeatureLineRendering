# unit_003：执行完成，科学证据仍为 PARTIAL

本轮已保存两臂各458490行映射及真实原核全景，父进程实际子退出码为0、reason=null。全局反事实弃权规则相对unit002新增421行分配，未丢失旧分配；**没有证明joint优于greedy，也没有交付双视图可辨的新增实质跨parent曲线续接**。更多认证或同色不能替代视觉证据。

实际运行07:01:43.565—07:02:21.441 JST；RUN_RESULT记载耗时37.125秒、求解2.550秒，fit_calls=0、new_candidates=0。分析仅读取保存输出及PNG，不拟合、不重跑、不渲染、不改源码。实际退出见[COMPUTE_EXIT](../../orchestration/unit_003/COMPUTE_EXIT.json)。

## 处理范围与归属结果

使用原M4有限叶载体及保存的2279条成功endpoint记录。先完整闭合竞争分量，再整体排除有成功overlap入射的分量；本轮仅处理73个含旧masked边的endpoint-only分量，最大9叶。5452条成功overlap的观测多重性未解决。范围外保留unit002结果，不将连通分量直接当身份。

73/73分量完成最优原解及反事实认证，无超时回退。75次禁止选中边的反事实求解得到71条认证边；两臂每个处理分量的raw选择均相同。共同认证器使baseline是greedy加全局弃权，而不是纯局部greedy。新0.15交换收益规则不等价于旧局部歧义规则。

| 保存结果 | greedy | joint |
|---|---:|---:|
| assigned / UNKNOWN | 250088 / 208402 | 250088 / 208402 |
| 相对unit002新增 / 丢失assigned | 421 / 0 | 421 / 0 |
| 相对M4新增 / 丢失assigned | 3739 / 0 | 3739 / 0 |
| 复合路径 | 370 | 371 |
| 相对unit002新路径 | 69 | 69 |

两臂主归属差异为0；路径数差异继承unit002未激活UNKNOWN的选择差异，并非本轮新优势。相对unit002有503行主ID改变，无旧复合组拆分，范围外全部membership字段精确保留。76对PNG逐字节相同。69条新增路径中67条为两叶、2条为三叶；34条无实质原parent，32条仅一个，3条有两个。后3条136463/151021/242344的域外支持分别2.784/2.204/1.818p，均不足4p。原parent只表示来源，不是真值。

## 实际图片与有限支持

下图是保存的原核渲染，原covariance、宽度、opacity不变；没有渲染辅助载体或无观测连接。建筑全景仍有大量碎裂、重叠和离群尖刺；冻结几何的归组不能清除原尖刺。

![原核全景 0012_FULL](scenes/scan24/stages/joint/0012_FULL.png)
![原核全景 0036_FULL](scenes/scan24/stages/joint/0036_FULL.png)

| 新路径 | 核 / 叶 | 支持并集p | 最长连续段p | 有限长度p | 总 / 最大gap p | 相对最大叶域外p |
|---|---:|---:|---:|---:|---:|---:|
| 251530 | 73 / 2 | 16.871 | 2.175 | 24.857 | 7.959 / 1.448 | 8.087 |
| 213491 | 72 / 3 | 16.421 | 0.700 | 27.349 | 10.928 / 1.371 | 5.457 |
| 129661 | 60 / 2 | 10.798 | 0.590 | 16.688 | 5.889 / 1.030 | 2.192 |

251530是最大新增含polyline叶路径，但0012组图及上下文空白，0036只见短而淡、近水平的线段，不能认定新增曲线。其主要parent贡献67核，另一个仅6核/1.671p，不够实质。213491最大新增全直叶路径只有一个parent；两固定视图组图/上下文均空白，不能给视觉成功。129661只有一个parent，双视图可见短细线，邻近其他结构仍不能凭颜色消除深度/分支疑问。

![251530：0036原核局部](scenes/scan24/stages/joint/diagnostics/PATH_251530_c633a521_GROUP_0036_CROP4.png)
![251530完整证据邻域：0036](scenes/scan24/stages/joint/diagnostics/PATH_251530_c633a521_CONTEXT_0036_CROP4.png)
![213491：0036真实空白原图](scenes/scan24/stages/joint/diagnostics/PATH_213491_1ddf8897_GROUP_0036.png)
![129661：0036邻域](scenes/scan24/stages/joint/diagnostics/PATH_129661_f6dff5fd_CONTEXT_0036_CROP4.png)

选图账本44对视图/类型中14对无前景：251530的0012、213491两视图、最大歧义上下文213473两视图、gap负例301451/301459两视图的对应GROUP/CONTEXT。保留空白native图，没有换相机或伪造crop。top3受损unit002路径不存在，是未出现损失而非漏交付。三条新增双实质parent小组未被固定选择器逐组渲染，本轮不补渲染，不据统计宣布视觉正确。

原参考53254/201906/10975属于继承结果，不能算本轮增长。53254支持并集44.292p但最长连续仅3.460p，说明并集、有限范围和连续观测必须分开。此方法不池化overlap；连接只参与检查且无观测支持，域外支持也不等于填满间隙。

负例84842/362883、153248/377058、153427/153430的已看邻域裁剪都短小且模糊，分别不能确证parallel、branch或tangent/深度安全；gap负例空白。保存的几何拒绝和完整行上下文是审计证据，不是物理负例真值。全路径oracle执行不证明跨独立路径物理安全。所有身份仍provisional，无held-out或物理准确率主张。

## 下一步与溯源

建议继续一个独立机制：**有限重叠观测的全局身份分区，与同证据greedy配对；端点拓扑保持固定**。优先围绕可见曲线参考201906与直线参考53254检查完整overlap竞争邻域；以有限弧长对应/共同观测支持形成身份证据，明确parallel/branch分离，未知关系保持中立。重复观测不消耗拓扑端口。不能将所有成功overlap直接union，也不能将所有拟合拒绝变成cannot-link。确切目标和证据规则需下一决策冻结；[NEXT.json](NEXT.json)仅建议，尚未实施。本轮结果不支持继续扫认证阈值或加求解预算。

已核验PARENT_RUN_FROZEN指向的21个source_snapshot文件、2个外部helper及decision/config绑定，双臂checkpoint的全部8个闭合文件哈希均一致。使用快照而非未来可变HEAD。CONFIG SHA256：`739636ada8e953befbb72aa4dc82c95a9536a0e849216fa3b31eafd2d2ec5e2f`；decision：`8efa3116a50eabe0f41081c46d51a7fedfda7abb80a40da07061136b9e24595c`。输入M4 state：`4f350e3a991c98d7cf011d833be4fc5aebcce1c7d328ae69b39948b5698ec31f`。

执行入口为冻结RUN_REQUEST中的`ambiguity_runner.py --config CONFIG.json`，父以批准Python `-B`启动。helper为AST隔离renderer.py及libjoint.so，确切路径/哈希见[PARENT_RUN_FROZEN](PARENT_RUN_FROZEN.json)。构建曾发生旧测试类导入产生新fixture目录的问题，已记录[BUILD_INCIDENT](BUILD_INCIDENT.json)，旧封存文件2609项复核未变；本分析不修改构建或数值产物。闭合产物由parent最终封存，本worker不创建包含可变运行状态的SEAL。
