# Lego / Chair 边缘责任评分实际验证

状态：`ENGINEERING_NOT_READY`。执行完成：`True`。后续局部优化：`NOT_RUN`。

本轮首先验证评分，未用下游修复代替评分验证。旧评分是相对位置支持代理；有符号变化记账与具体操作作用分开记录。真实内部目标仅为自动质量确认的颜色过渡，未认证几何、材质、纹理或物理接触语义。

原生合成验证：24 帧；存在/缺失检查通过 21；带背景项的有符号恒等式通过 24。构造真值在评分前冻结，未从梯度或评分推导标签。

CPU 回归先在未修改的 v1 接口上 RED（拒绝条纹剖面仍进入主证据），在新接口上 GREEN。初次语法失败和原生失败也保留；日志位于 logs 和 failures。

## 实际场景

### lego

完整 SH3，310475 核，源 SHA256 `fa9bea3fa4f8d349fa873a66d892c53cd1263499caec6421c286350a5bb7cbbc`。
八个 edit-train 视角冻结目标：{'outline': 24, 'clear_color_transition': 14, 'texture_detail_certified': 0}。三个门槛：[False, False, False]。诊断接受核数：384。

固定旧评分、等片段权重的证据替换消融（核数相同；2px/4px 评价带独立固定）：

| 证据 | 核数 | 2px 贡献召回 | 4px 贡献召回 | 2px 选中质量集中度 |
| --- | ---: | ---: | ---: | ---: |
| old_broad | 31048 | 0.064070 | 0.070171 | 0.000248 |
| old_trusted_equal | 31048 | 0.991677 | 0.990756 | 0.004587 |

固定可信证据、每群相同核数，独立新方向/幅度验证：

| 方法 | 目标群 | 独立局部作用均值 | 局部代价通过率 | 诊断接受群 |
| --- | ---: | ---: | ---: | ---: |
| old_relative | 12 | 0.00151079 | 1.0000 | 7 |
| absolute | 12 | 0.00175338 | 1.0000 | 5 |
| signed | 12 | 0.00064551 | 1.0000 | 4 |
| matched_random | 12 | 0.00000747 | 1.0000 | 1 |
| bounded_response | 12 | 0.00199935 | 1.0000 | 6 |

受约束响应与简单贡献/匹配随机中较好对照的配对差异：`{'n': 12, 'mean': 0.00024596198490611505, 'ci95': [0.0, 0.0006103317531288793], 'unit': 'paired target groups; dependent views, exploratory confidence only'}`。
构造分数与独立响应的 Spearman：`0.8684452471352105`。候选群搜索和三个尺度轴探针的计算成本单列，响应法每目标搜索4个候选，不能称其免费。

- [新原生渲染对比 r_001](../../artifacts/edge_responsibility_lego_chair_v2/media/lego/r_001/sheet.png)
- [新原生渲染对比 r_014](../../artifacts/edge_responsibility_lego_chair_v2/media/lego/r_014/sheet.png)
- [新原生渲染对比 r_027](../../artifacts/edge_responsibility_lego_chair_v2/media/lego/r_027/sheet.png)
- [新原生渲染对比 r_041](../../artifacts/edge_responsibility_lego_chair_v2/media/lego/r_041/sheet.png)

门槛3：independent human visual GO and cross-view boundary interpretation pending; costs alone do not certify locality。

### chair

完整 SH3，256690 核，源 SHA256 `13e4ecc9ffe9c5ae2a0656e2e5c56a737cfdc90a62ad04799db3c46b0b442f5d`。
八个 edit-train 视角冻结目标：{'outline': 24, 'clear_color_transition': 3, 'texture_detail_certified': 0}。三个门槛：[False, False, False]。诊断接受核数：320。

固定旧评分、等片段权重的证据替换消融（核数相同；2px/4px 评价带独立固定）：

| 证据 | 核数 | 2px 贡献召回 | 4px 贡献召回 | 2px 选中质量集中度 |
| --- | ---: | ---: | ---: | ---: |
| old_broad | 25669 | 0.050539 | 0.058245 | 0.000390 |
| old_trusted_equal | 25669 | 0.996992 | 0.996356 | 0.003757 |

固定可信证据、每群相同核数，独立新方向/幅度验证：

| 方法 | 目标群 | 独立局部作用均值 | 局部代价通过率 | 诊断接受群 |
| --- | ---: | ---: | ---: | ---: |
| old_relative | 9 | 0.00181165 | 1.0000 | 2 |
| absolute | 9 | 0.00215205 | 1.0000 | 6 |
| signed | 9 | 0.00123109 | 1.0000 | 3 |
| matched_random | 9 | 0.00004010 | 1.0000 | 1 |
| bounded_response | 9 | 0.00217039 | 1.0000 | 5 |

受约束响应与简单贡献/匹配随机中较好对照的配对差异：`{'n': 9, 'mean': 1.834104283192453e-05, 'ci95': [0.0, 4.760947188600626e-05], 'unit': 'paired target groups; dependent views, exploratory confidence only'}`。
构造分数与独立响应的 Spearman：`0.9862934124078326`。候选群搜索和三个尺度轴探针的计算成本单列，响应法每目标搜索4个候选，不能称其免费。

- [新原生渲染对比 r_001](../../artifacts/edge_responsibility_lego_chair_v2/media/chair/r_001/sheet.png)
- [新原生渲染对比 r_014](../../artifacts/edge_responsibility_lego_chair_v2/media/chair/r_014/sheet.png)
- [新原生渲染对比 r_027](../../artifacts/edge_responsibility_lego_chair_v2/media/chair/r_027/sheet.png)
- [新原生渲染对比 r_041](../../artifacts/edge_responsibility_lego_chair_v2/media/chair/r_041/sheet.png)

门槛3：independent human visual GO and cross-view boundary interpretation pending; costs alone do not certify locality。

## 约束与可复核文件

每个核群记录有符号/绝对归因、抵消、完整法向剖面有限差分、平台与平坦区域成本、非目标区域成本、alpha孔洞与轮廓变化、独立扰动预测和跨视角同UID操作。主评分从原生颜色反向获取权重，完整SH3按原生方向和 clamp_min 求值；背景ΔT和总权重恒等式均检查。EOTF只对完整渲染应用。

选中贡献图保留完整模型的遮挡遍历，未选核特征置零。子集图实际移除未选核，使用原始完整SH3色，只能视为无原遮挡的诊断。正负差分采用统一20倍显示增益，原图与float32差分同相机保存。top10%仅是等预算排名参考，诊断接受集合可为空。

八个edit-train用于构造，四个dev用于数值校准和噪声/绝对门槛报告，四个此前GS训练见过的edit-holdout用于探索性跨视角检查；未打开原始TEST RGB。没有人工标签、部件标注、物理接触或正式盲测优势声明。

三项门槛全部通过前，不执行336步color/cov优化和普通同权限对照；此次优化保持NOT_RUN。

保护输入核验：`{'files_checked': 248, 'changed_paths': [], 'all_byte_identical': True, 'old_models_sha256_after': {'lego': 'fa9bea3fa4f8d349fa873a66d892c53cd1263499caec6421c286350a5bb7cbbc', 'chair': '13e4ecc9ffe9c5ae2a0656e2e5c56a737cfdc90a62ad04799db3c46b0b442f5d'}, 'source_hashes_unchanged': True}`。

- [最终机器记录](FINAL.json)
- [冻结输入与源](INPUT_FREEZE.json)
- [源映射](SOURCE_MAP.json)
- [复现](REPRODUCE.md)
- [24帧原生合成图](media/synthetic_24.png)

<!-- CURATED_APPENDIX -->
## 补充实际检验与限制

原始24帧的三项4px定位失败与部分遮挡夹具失败均保留，门槛1没有通过。对同24个冻结构造追加了逐核old relative、绝对贡献、signed、可见mass/投影面积/数量匹配random的等预算完整模型扰动检查；强制top64仅作比较。构造类型来自独立构造记录，不代表自动语义分类器已经通过。

另加两个先冻结的新原生夹具：全画面完全遮挡的后核，其DC、尺度、opacity正负有限差分全图响应严格为0；正负抵消夹具的抵消率为99.801%。后者log-scale原生局部梯度约0.001519，但δ有限差分为-0.058860、δ/2为-0.122630，明确标记unstable_response。不能以新增夹具替换原始失败，也不能将加性恒等式当作操作预测优势。

新增按outline、清楚颜色过渡、unknown分列的2px/4px贡献召回/集中度、selected mass距固定目标段分布、连续覆盖与缺口长度。纹理类别在真实模型中没有独立语义标注，因此保持unknown；不能称其假边缘。距离统计仅覆盖固定少量目标段，不是全物体真值普查。

部分视角找不到满足冻结质量规则的匹配平坦ROI：原始flat_rms字段在空mask时的0是未定义值，不是观测到零代价。附录明确标记UNVERIFIED，原始平台剖面与整个非目标区域成本仍单列；这不满足独立完整局部性认证。Lego平坦负例8群、Chair 4群均未接受。平坦负例有47核和29核的低可见数案例；同一目标四种方法数量严格相同，64为上限而非填满配额。

原始ringing_overshoot字段只是RGB范围变化代理；[RINGING_APPENDIX.json](RINGING_APPENDIX.json)用固定参考方向/对比给出完整native剖面的规范化越界量与反向变化量。原始结果不改写。线性RGB宽度/位置和误差改善仍由对完整渲染EOTF后的原生剖面记录提供。

工程完整性42项检查与5项CPU回归通过，不等于三个科学门槛通过。真实核群构造/独立测试共192个原子单位、3456次完整模型native forward；逐群实际时间区间与搜索成本记录在GROUP_TIME_COST.json。记录只有秒级结束时间，未伪造精确GPU计时。

已查看Lego和Chair对比图：signed排名参考仍覆盖大量表面；诊断接受子集存在团块和跨视角缺口。这是实现者的观察，不能代替独立human visual GO。

- [原始失败明细](FAILURE_CASES.json)
- [独立工程检查](INDEPENDENT_ENGINEERING_AUDIT.json)
- [逐群实际时间与成本](GROUP_TIME_COST.json)
- [合成逐核评分补充](results/synthetic_kernel_score_appendix.json)
- [Lego定位/覆盖附录](results/lego_localization_appendix.json)
- [Chair定位/覆盖附录](results/chair_localization_appendix.json)
- [Lego独立作用/成本图](media/lego/independent_effect_cost.png)
- [Chair独立作用/成本图](media/chair/independent_effect_cost.png)

当前状态仍为ENGINEERING_NOT_READY；两场景门槛2置信区间下界均为0，门槛3人工复核pending，color/cov普通同权限局部优化均为NOT_RUN。
