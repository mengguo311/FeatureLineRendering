# 执行记录

- 在专用工作树开始时 HEAD=05e29d4f392afb3c57e687133cd23cc569945274，已包含任务范围提交；untouched基点为a58c76bd8a03f1d04afcf8e8dde455d2f806629c。继承 .codex/config.toml 保持 gpt-6-astra / ultra。
- 不启动外部 coding/research agent。只调用一个继承保护的内部只读审查，检查缓存链与代码；没有与主进程重叠的生产科学计算。所有生产与测试由单一主进程顺序执行，CPU affinity两个逻辑CPU，数值库及ffmpeg两线程，无GPU访问，无安装/训练。
- RED真实失败为缺少core模块；随后实现后8项tracer GREEN。稀疏accepted查询另有每个实际construction相机逐采样点对旧sealed alpha完整和校验，及full-K升维重投影校验；后者不证明表面深度正确。
- 旧cached RGB/alpha实际文件通过旧seal、result、INPUT_FREEZE逐相机绑定。旧construction结果没有model hash字段，通过其seal绑定的INPUT_FREEZE核查model。所有metadata按实际file_path映射，r_33实际index28。
- 继承renderer支持本轮冻结的对称居中K；full-K射线/三角化独立实现。对任意skew相机不能直接使用当前三角面renderer，这是非本轮相机域的限制。
- Stage上限4GiB，root空闲下限4GiB/sharedGit空闲下限1.5GiB。稀疏accepted数组保留生产1GiB单次申请守卫。所有cache/tmp/build在新stage。没有触碰旧runtime与共享binary。

## 冻结后内部审查发现与处置

没有改动已冻结的合并规则或几何；所有发现作为候选局限保留。新增7项扩展测试在两scene资产产生后、开封评价前运行，是真实后置扩展，不能改写为全部事前通过。它们调用实际production pair/cluster融合路径，检查三相机解析边、条件median与绝对T crossing区别、终止核拒绝、并列深度、嵌套孔洞、无跨桥源拓扑，并显式复现“多源端点不等于多源edge”。原8项中can_match辅助测试不是production完整匹配覆盖；扩展测试补上真正垂直路径。

原导出single/每source的edge_sources用局部edge index，rawunion/fused用全局raw edge index，而node_sources均全局；新增各scene PROVENANCE_NAMESPACES.json提供明确命名空间与edge offsets，避免错误解释。原封印字节不覆盖。

源tangent采用闭环±3点，因此可能跨过随后被切开的深度断口。冻结local-track是anchor窗口内符号投票，不保证全轨迹严格单调，最终accepted集合也可能不足3个邻点；METHOD_DESIGN中的“顺序连续”是设计意图，实际保证须以代码及SOURCE/EDGE审计为准。逐簇所有source端点重投影/位移上限确实检查，但两端各多源不等于整条边有多个source camera；融合后边长和方向也可能改变。后置审计完整报告这些实际代价，不据heldout图裁线或调整坐标。

当前顺序生产检查前序阶段seal；CLI单独调用collect/build_asset的依赖链检查不够强。独立audit补查全部source→fusion→asset及FUSION_FREEZE代码一致性。复现入口应先执行audit/verified-skip检查，勿绕过前序阶段单独拼接未sealed输入。

后续扩展到10项production-path测试（distinct-support rolling拒绝、near-parallel拒绝、反向source顺序等价），实际在评价之后通过；原7项日志及后续10项日志分别保留，没有覆盖时间证据。原始固定CPU/mesh两个shared binary均与历史build manifest SHA一致，见SHARED_BINARY_READONLY_AUDIT.json。
