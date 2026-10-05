# 独立CPU审计算术说明（C前记录）

原封存audit.py保持不变。三场景的原float64审计中，Lego B_score误差1.6194467775676458e-6、Chair 6.795059050546115e-6、Ficus 3.6188314567198177e-7；原固定绝对界限5e-6，因此Chair的原断言确实失败。其分子9.39115864066753e-12、成本1.50629985914974e-12、foregroundmean7.327506656995553e-13、mass/visible=0误差，均过原界限。失败日志与CPU_AUDIT_DIAGNOSTIC.json保存，不宣称原float64审计全过。

继承生产矩阵从float32 CSR取w与fullalpha，先float32(.5*alpha)，float32 reciprocal，再float32 multiply；foreground/cost则float32 w/fullalpha，再float64聚合。原审计直接float64 w/alpha重算同代数，检查其比率的固定绝对误差，在Chair大B比率上触发界限。这不影响native RGB/depth/alpha/ID校准，也没有改变数学需求或重新归一化截断权重。

新增audit_stored_dtype.py独立从已保存raw CSR以np.add.at求和，重现**实际继承的存储dtype运算**，仍使用原5e-6/1e-9界限，没有放宽任何检查。三scene Bscore最大误差分别3.15e-14/1.42e-14/1.07e-14；分子/成本/denominator误差≤2.52e-17。相同采样IDs（含unknown和所有arm首末IDs），检查每ray没有重复原ID，聚合维持fullalpha原分母。原float64诊断并列在INDEPENDENT_CPU_AUDIT中，`original_float64_all_pass=false`；`all_pass=true`仅指实际stored dtype合同独立验证。

这是明确标注的验证补充，不是科学算法修复：S0、原audit.py、cores、config、全部证据、A/B分数、ordered selectedIDs和全局F封条不变。新增源码/hash和失败记录在POST_S0_VERIFICATION_BINDING.json先于任何新C/arc提交封存。没有因为C结果改配方。

恢复：原pipeline若在audit.py停止，先运行 `python -B artifacts/representative_edge_gaussians_three_v1/code/audit_stored_dtype.py`（指定vfsdgs Python及CPU2环境），再运行原run.sh；补充校验会读已发布的小型诊断采样记录和sealed raw CSR，写真实独立CPU记录，原失败不可删除。机器FINAL和报告必须同时披露原断言失败与补充验证scope；不能把float64原审计称为全过。
