# Unit002：固定路径驱动原始 Gaussian 控制与 Lego 第二场景

**状态 partial；科学范围 UNCERTIFIED_CPU_MAPPING。** 本轮已实际执行 Chair／Lego 原核路径改色和 opacity 衰减，完成同预算对照、逐ID责任值验证和冷加载重放。窄路径局部性总体失败：linked改色仅1/6视角通过，opacity为0/6；不能宣称优于简单空间选择。

完整读取BRIEF、大纲M1/贡献追踪/代理附着/比较矩阵，复核实际v04适配器、接受位置、代理锚点和编辑代码。unit001原始7视角、每行membership和实际改色均独立复算通过，旧证据锁保持不变。旧Ficus源代码采用另一个q<=9/.999 cap/1e-5 stop近似，不能套用为本轮渲染器的逐ID校准；其357/284835支持核、reserved几乎全UNKNOWN及NO_GO结论保留。旧PartField k3是无语义聚类，未完成reserved原GS部件编辑；没有拿它冒充当前路径绑定。

协议在2026-10-22 17:20 JST冻结。每场景4个BUILD、3个仅对本次binding保留的评估相机，384px、固定stride3网格；Chair评估视点已在unit001曝光，底层GS训练覆盖未独立审计。没有盲测或独立语义GT。人工region4分别是座面patch和bucket surfaces，不保证完整语义部件。

| Scene | 原始行数 | M1 UNKNOWN | region4支持行 | 路径控制原核 | 段/实际stroke IDs |
|---|---:|---:|---:|---:|---:|
| chair | 256690 | 218027 | 18278 | 1418 | 128/23 |
| lego | 310475 | 253082 | 8782 | 191 | 93/24 |

预先均匀冻结24个保存stroke ID，再限制最多128个原段；Chair最终128段只覆盖23个ID，Lego93段覆盖24个。这个范围在评估前已记录，未按效果删样本。所有锚点保留原segment_index、stroke_id、face/bary、世界点、相机、完整CSR原ID/alpha×T、接受深度、保留/拒绝质量与UNKNOWN。相同像素/原ID的重复锚点在每视角选择累积中仅计一次。M1仍使用原6通道规则，Lego第5通道不用；Chair所有M1数组与unit001精确相同。

路径选择只作用于M1支持region4的原行；至少两视角、接受质量>=.02、保留比例>=.7，强度为fraction×min(accepted/.1,1)。其余保留UNKNOWN/拒绝原因。权重是渲染曝光证据，不是校准语义概率，更不是物理同面证明。

改色在完整SH3评估和下界clamp之后混合蓝色；原SH数组不写回，剩余(1-strength)部分保留全部高阶视角依赖。opacity编辑仅在副本中执行opacity_i×(1-strength_i)，重新渲染完整模型、重算T与接受列表。均值、协方差、旋转、原始行数/顺序与源PLY全部不变。selected-only单独存图，重算T，不能当作完整模型贡献。

最近路径控制按核中心到冻结段中点的距离取相同核数；这只是空间控制，不作为表面绑定。shuffle在BUILD曝光十分位内以seed1729置换强度。改色按BUILD固定网格真实未裁剪RGB L1线性匹配；opacity用实际完整源渲染做10步有界匹配，要求目标误差<=1%，评估相机不再调强度。PNG显示裁剪到0–1，原始指标另保存clipped结果。

| Scene | BUILD tint L1（三臂相同） | BUILD opacity L1 linked/nearest/shuffle | opacity目标最大相对误差 |
|---|---:|---|---:|
| chair | 86.396080640 | 11.150605828/11.170079283/11.153123278 | 0.1064% |
| lego | 15.641630106 | 0.973359980/0.971779935/0.969157499 | 0.2301% |

窄路径目标是冻结3D段的可见3px半径capsule，代理深度容差.02；固定2px边界带。下表保留三臂目标变化及远变化比例。门槛为目标内部mean L1>=.02且far<=2%；属于同一作者代理的意图自洽，不是语义正确率。完整region意图指标也保存在SUMMARY中，不能用宽region通过替代窄路径失败。

| Scene/view | Operation/arm | Target mean L1 | Far other mean L1 | Far background mean L1 | Far fraction | Total L1 | Gate |
|---|---|---:|---:|---:|---:|---:|---|
| chair/orbit_43_28_4.9 | tint_path_linked | 0.1446880 | 0.0009450 | 0.0000012 | 14.611% | 135.5905 | False |
| chair/orbit_43_28_4.9 | tint_nearest_path | 0.2014012 | 0.0000785 | 0.0000002 | 1.143% | 145.0388 | True |
| chair/orbit_43_28_4.9 | tint_shuffled | 0.0084102 | 0.0065526 | 0.0000551 | 88.683% | 161.4486 | False |
| chair/orbit_43_28_4.9 | opacity_path_linked | 0.0149592 | 0.0001825 | 0.0000004 | 22.167% | 17.3784 | False |
| chair/orbit_43_28_4.9 | opacity_nearest_path | 0.0204318 | 0.0000209 | 0.0000001 | 3.078% | 14.4023 | False |
| chair/orbit_43_28_4.9 | opacity_shuffled | 0.0005230 | 0.0008103 | 0.0000083 | 91.680% | 19.5167 | False |
| chair/orbit_133_28_4.9 | tint_path_linked | 0.1437991 | 0.0004268 | 0.0000009 | 14.052% | 51.5108 | False |
| chair/orbit_133_28_4.9 | tint_nearest_path | 0.1921556 | 0.0000228 | 0.0000015 | 1.005% | 56.6447 | True |
| chair/orbit_133_28_4.9 | tint_shuffled | 0.0079853 | 0.0050425 | 0.0000470 | 92.745% | 97.2636 | False |
| chair/orbit_133_28_4.9 | opacity_path_linked | 0.0128870 | 0.0000457 | 0.0000002 | 16.919% | 4.6848 | False |
| chair/orbit_133_28_4.9 | opacity_nearest_path | 0.0217877 | 0.0000097 | 0.0000008 | 3.769% | 6.9156 | False |
| chair/orbit_133_28_4.9 | opacity_shuffled | 0.0006117 | 0.0003861 | 0.0000056 | 91.111% | 7.8657 | False |
| chair/orbit_223_28_4.9 | tint_path_linked | 0.1330341 | 0.0003113 | 0.0000018 | 18.992% | 30.4924 | False |
| chair/orbit_223_28_4.9 | tint_nearest_path | 0.1124884 | 0.0000187 | 0.0000010 | 2.103% | 22.1209 | False |
| chair/orbit_223_28_4.9 | tint_shuffled | 0.0012951 | 0.0047334 | 0.0000581 | 93.421% | 98.4793 | False |
| chair/orbit_223_28_4.9 | opacity_path_linked | 0.0109973 | 0.0000458 | 0.0000005 | 22.838% | 3.8506 | False |
| chair/orbit_223_28_4.9 | opacity_nearest_path | 0.0124162 | 0.0000078 | 0.0000006 | 7.570% | 2.8538 | False |
| chair/orbit_223_28_4.9 | opacity_shuffled | 0.0003012 | 0.0004114 | 0.0000079 | 92.033% | 9.0869 | False |
| lego/orbit_282_28_5.1 | tint_path_linked | 0.0779526 | 0.0000130 | 0.0000007 | 3.086% | 14.4475 | False |
| lego/orbit_282_28_5.1 | tint_nearest_path | 0.0652007 | 0.0000446 | 0.0000004 | 3.975% | 31.9596 | False |
| lego/orbit_282_28_5.1 | tint_shuffled | 0.0000000 | 0.0008167 | 0.0000255 | 98.073% | 26.0302 | False |
| lego/orbit_282_28_5.1 | opacity_path_linked | 0.0004761 | 0.0000020 | 0.0000003 | 12.207% | 0.7826 | False |
| lego/orbit_282_28_5.1 | opacity_nearest_path | 0.0005123 | 0.0000027 | 0.0000004 | 3.327% | 3.6353 | False |
| lego/orbit_282_28_5.1 | opacity_shuffled | 0.0000000 | 0.0000431 | 0.0000043 | 99.391% | 1.7134 | False |
| lego/orbit_12_28_5.1 | tint_path_linked | 0.2071334 | 0.0003198 | 0.0000000 | 12.780% | 57.6712 | False |
| lego/orbit_12_28_5.1 | tint_nearest_path | 0.0950057 | 0.0000222 | 0.0000113 | 5.319% | 35.8389 | False |
| lego/orbit_12_28_5.1 | tint_shuffled | 0.0005821 | 0.0010344 | 0.0000039 | 97.972% | 24.8210 | False |
| lego/orbit_12_28_5.1 | opacity_path_linked | 0.0140539 | 0.0000453 | 0.0000000 | 22.328% | 4.6725 | False |
| lego/orbit_12_28_5.1 | opacity_nearest_path | 0.0044827 | 0.0000010 | 0.0000028 | 15.029% | 2.4380 | False |
| lego/orbit_12_28_5.1 | opacity_shuffled | 0.0000183 | 0.0000374 | 0.0000003 | 98.780% | 0.9159 | False |
| lego/orbit_102_28_5.1 | tint_path_linked | 0.3502776 | 0.0000099 | 0.0000001 | 1.219% | 22.8676 | True |
| lego/orbit_102_28_5.1 | tint_nearest_path | 0.2797164 | 0.0000187 | 0.0000003 | 2.167% | 24.7787 | False |
| lego/orbit_102_28_5.1 | tint_shuffled | 0.0000000 | 0.0008879 | 0.0000077 | 99.731% | 24.6032 | False |
| lego/orbit_102_28_5.1 | opacity_path_linked | 0.0012559 | 0.0000011 | 0.0000001 | 8.689% | 0.4826 | False |
| lego/orbit_102_28_5.1 | opacity_nearest_path | 0.0029989 | 0.0000021 | 0.0000001 | 5.835% | 1.2430 | False |
| lego/orbit_102_28_5.1 | opacity_shuffled | 0.0000000 | 0.0000451 | 0.0000006 | 99.739% | 1.2721 | False |

Chair linked改色远泄漏14.1%–19.0%，最近路径约1.0%–2.1%；opacity linked为16.9%–22.8%。Lego linked改色3.09%/12.78%/1.22%，仅102度通过；opacity目标mean L1约0.00048/0.01405/0.00126，变化明显弱于.02门槛。不存在“几乎没改而低损伤即成功”的解释。Lego局部个别视角linked较好，不能覆盖Chair与其他视角的失败。

| Scene/view | Supported/attempted | Proxy-visible | Visible retained mass | UNKNOWN |
|---|---:|---:|---:|---:|
| chair/orbit_0_65_4.7 | 119/128 | 122 | 90.20% | 9 |
| chair/orbit_180_65_4.7 | 98/128 | 104 | 85.66% | 30 |
| chair/orbit_90_45_4.9 | 88/128 | 91 | 90.68% | 40 |
| chair/orbit_-90_45_4.9 | 103/128 | 107 | 88.52% | 25 |
| chair/orbit_43_28_4.9 | 96/128 | 105 | 82.59% | 32 |
| chair/orbit_133_28_4.9 | 46/128 | 57 | 73.06% | 82 |
| chair/orbit_223_28_4.9 | 27/128 | 31 | 73.72% | 101 |
| lego/orbit_237_35_4.9 | 28/93 | 37 | 70.05% | 65 |
| lego/orbit_327_35_4.9 | 40/93 | 40 | 95.16% | 53 |
| lego/orbit_147_35_4.9 | 38/93 | 39 | 91.14% | 55 |
| lego/orbit_57_35_4.9 | 41/93 | 42 | 91.37% | 52 |
| lego/orbit_282_28_5.1 | 26/93 | 32 | 73.99% | 67 |
| lego/orbit_12_28_5.1 | 32/93 | 37 | 81.41% | 61 |
| lego/orbit_102_28_5.1 | 30/93 | 37 | 73.96% | 63 |

10项针对性trace/membership/path测试通过，其中新功能先RED(rc1模块未实现)后GREEN；另1项断点匹配等价测试通过。两场景独立读回核验原ID剔除/排序映射、接受alpha阈值、完整T链、质量和完整SH RGB；所有M1及路径分布逐行重算一致。新opacity trace独立重建编辑RGB/alpha；Chair linked新增接受像素–ID对为1242/571/268，Lego为104/202/99。原生CUDA逐ID校准仍不可用；历史CPU median/expected depth偏差原样保留，协方差平面深度不是物理真值。

Chair长命令收到SIGTERM(-15)，Lego首次启动也收到SIGTERM(-15)，信号来源未确定；不把它们归因于科学失败。原始目录逐字节封存于interrupted_chair和interrupted_lego_start，退出码单独保留。工程恢复仅缓存同一opacity effect调用和恢复已完成数组，未改阈值/相机/选择；Chair原中断目录全部npz数组与恢复结果一致。随后保持命令等待并分段运行正常完成；没有隐藏第一次非零退出。

已实际查看两场景全部三视图面板、Chair对照和14帧接触表：原GS对象完整入画，代理波纹、碎排线、薄结构缺损仍在。8个不同相机矩阵构成40度短arc；固定相机6级opacity真实重渲染。两条视频完整解码，FFV1逐帧完全一致；这不证明全时序稳定性或局部编辑质量。四个独立冷进程（两场景、两操作、含Chair弱背视点）与保存数组完全一致。query_lego段0列出60个原核，保留质量0.927101、拒绝0.072799；CSV包含所有事件，不把单个原核当一条线。

M1两场景软分布partial；M2有限路径支撑partial；M3路径驱动真实原GS两种诊断已执行，但科学局部性失败；M4持久化/CLI重放partial。没有UI工作、新训练、GPU、环境转储、凭据访问、嵌套模型、push/merge。数值串行、两核亲和、数值线程1。orchestration及旧证据未写；仅封存验证过的有限工程证据，scientific_seal=false。

**NEXT=continue。** Use the saved BUILD traces to measure each candidate original kernel's full-footprint responsibility inside versus outside the frozen path capsules. Freeze a specificity-aware selection or abstention rule, then repeat actual source tint/opacity with the same visible-effect budget, nearest-path and shuffled controls on Chair rear views and Lego. Preserve unit002 locality failures; do not loosen gates or add UI.

重点文件：`results/<scene>/SOURCE_BINDING.npz`、`PATH_BINDING.npz`、`EDIT_SELECTION.npz`、各视角`trace/path_support`及opacity新trace、`VALIDATION_chair.json`、`VALIDATION_lego.json`、`FINAL_AUDIT.json`。完整图见`results/<scene>/ALL_EVALUATION_VIEWS.png`，复现见`REPRODUCE_ZH.md`。

收尾补充：报告收集器首次因要求自身未结束时的完成回执而rc1；仅排除当前报告PID后rc0，失败日志独立保留。区域改色六视角RGB重建最大误差<6e-8，报告路径指标与保存RGB复算一致（VALIDATION_SUPPLEMENT.json）。代码提交中的分段runner仅清理空行尾空格，实际执行的精确源码仍保存在engineering_recovery_source和delivery_source。
