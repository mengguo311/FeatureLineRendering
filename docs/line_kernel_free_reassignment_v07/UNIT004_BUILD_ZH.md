# unit004 BUILD：共享核重叠合并

仅新增overlap_core/runner/delivery、test_overlap/run_overlap_tests及build_overlap_request；unit003的18个源码文件和旧快照保持不变。

完整兼容表按模型存储原行号、最低cost段及弧长，不截断为top2。候选由共享原核的双侧支持产生，记录全部模型对；动态接受后重新构建当前完整关系。重叠域采用定向弧长偏移和有限插值，不把两个重叠参数段串成往返路径。逐核竞争、支持规则及E=sum loss+M不变。

控制直接冷载复制unit003 NO_MERGE。新操作可撤回/拆分旧标签，不把旧parent或旧组当真值。模板只是辅助几何；最终图片使用原核。域外诊断的最大输入按合并前完整输入支持选择，同时保存保留贡献，避免用丢失后的较小子集冒称最大输入。

真实API测试先因缺少overlap_core失败；实现后58项回归通过，随后加入真实63行正向runner/完整兼容成本对照/能量拒绝，61项通过。所有小型资产和日志在unit004；测试不读取完整ficus或渲染。父级计算尚未执行，不能从BUILD声称55/441存在共享证据或方法有视觉收益。

plain入口：批准Python -B overlap_runner.py --config unit004/CONFIG.json。1800秒上限；120秒readiness、360秒完整初始关系、1200秒前停止science，最后600秒交付；19:38绝对截止。失败保留完整前态及试验进度，不能提升不完整关系或试验。冻结后不得再改源码。
