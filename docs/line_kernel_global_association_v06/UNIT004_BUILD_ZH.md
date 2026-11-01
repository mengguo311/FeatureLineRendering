# unit004 BUILD：固定有限 anchor 的重叠观测联合归属

实现只新增 v06 模块，旧 v06 数值模块、旧实验目录和快照均不修改。输入为封存 scan24 M4；成功 overlap 候选仅来自保存记录，无新空间候选、拟合或端点续接。完整成功 overlap 分量先冻结，再用相同有限 anchor 假设库比较收益排序 greedy 和 SciPy MILP 互斥集合选择。

每个 anchor 保持原 q。兼容 donor 必须全原核残差/切向通过，原 q 的≤1p采样在 anchor 有限域内且投影单调。假设枚举成本排序 donor 的所有非空前缀；不跳过组守卫拒绝的中间成员。三臂检查沿用原谓词及 anchor knots，成员顺序为 anchor、自低成本到高成本 donor、各叶内部原 seedlet 顺序。contact 检查保留原 check-only 冗余共线点处理，不改变保存 q。

假设选择不消耗拓扑端口。原 M4 叶不可拆分，未选和范围外恢复 M4。继承辅助字段不覆盖，新假设替代引用另存；UNKNOWN 激活仍需3seedlets/6kernels/4p。组统计明确 duplicate support pooling 与载体外延不同，固定 anchor 域外支持恒为0。unit003新增身份不在本轮保护范围，相对回退另列。

父持有唯一正式命令：批准 Python `-B overlap_runner.py --config CONFIG.json`。本 BUILD 未启动该数值命令。1800秒上限，建库累计600秒、solver总600秒、末600秒交付。组件银行、配对选择、双臂全行映射均先闭合 checkpoint；仅哈希验证的完整阶段可续读。后续渲染失败保留映射。原核全景先于组统计/诊断；没有辅助线/桥绘制。

测试实况在 unit004/TESTS_RECEIPT.json：新接口实现前 RED；额外零预算断言真实失败后修复；25项 GREEN 包括集合选择陷阱、四个重叠观测、有限域/parallel/branch/UNKNOWN/超限、映射优先、续读/损坏拒绝，以及9个真实有限载体35seedlets的纯几何回归和9条保存候选记录的schema回归。完整资产未加载作实验，渲染器在24行vertical fixture中明确拒绝调用。工作目录错误日志保留且不计作行为RED。测试通过不提供物理身份结论。
