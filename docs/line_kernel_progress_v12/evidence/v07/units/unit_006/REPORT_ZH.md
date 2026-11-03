# unit006 保存结果分析：图像降权没有新增归组收益

**工程执行完成；本轮科学结果为零增益，完整长曲线恢复仍为 PARTIAL。** 最终 MEMBERSHIP.npz、MODELS.npz 以及两个原生全景PNG均与 unit005 逐字节一致。不是只看assigned相等，而是文件哈希相同。本轮不提升任何新的物理身份结论。

实际parent子进程于19:17:07.628602开始、19:21:45.431650结束，returncode=0、reason=null；runner计时277.284540秒，无保存错误。依据[实际退出](../../orchestration/unit_006/COMPUTE_EXIT.json)与[RUN_RESULT](RUN_RESULT.json)，不以wrapper返回码替代。保存NO_BIRTH、15次接受状态、BIRTH_FINAL共17个完整检查点；每阶段均285956原行，映射/模型先于图像保存并冷载。NO_BIRTH和最终态各有两张原生全景，21组案例有42个非空联合bbox；非空不等于清晰可辨。

主表示仍为可生灭的有限辅助折线与可撤回的逐核归属，不是旧M4片段原子，也不是MILP。此次只以真实双视图正向边缘支持修改已保存图内路径代价，原邻接、64种子及每种子的原可达范围R保持冻结；原核参数、赋值/支持/能量规则不变。候选模型未绘入最终图。旧parent仅用于来源诊断。

[图像证据](graph/EVIDENCE.json)覆盖344798条有向边，其中25712条获得两视图三个采样点的正向支持并将代价乘0.5。128份原R及完整证据checkpoint已保存。原路径搜索[精确重放](graph/CONTROL_REPLAY.json)通过；对照是封存unit005 BIRTH_FINAL，其拟合/出生没有重跑。

64个种子中6份搜索回执改变，只有1条规范路径真正改变：candidate1、seed_index2、mode38465，路径的一处模式40152换为40153，长度10.817745→10.843266p。新旧该提案均因vertex_turn拒绝，尚未进入全核重竞争，见[本轮失败](trials/TRIAL_001/TRIAL.json)。其余变化只是路径代价。32条合格候选全部尝试：15次接受、8次window_turn、1次vertex_turn、8次birth_support_not_one_piece；另32个种子因少于6个voxel未成候选。没有隐藏超时提升或临场调阈值。

因此相对unit005，新增/丢失/拆分/重排全部为0。相对共同NO_BIRTH输入，assigned56222→56762、UNKNOWN229734→229194，新增540、丢失0；原模型199的88核中3核改投722，另85核仍归199，真实发生一次旧组拆分。这个自由重分配现象与15个出生模型均已在unit005出现，不能归因于新图像证据。模型519→534，E240874.001485→240384.944691也只是同一旧收益；目标下降不是物理证明。

以下统计均来自[最终COMPARISONS](scenes/ficus/stages/BIRTH_FINAL/COMPARISONS.json)，最终assigned固定56762。允许旧标签丢失和拆分，但必须报告，不能把它们全部称为纠错。跨命名空间数字ID变化不代表身份准确率。

|参考|参考assigned|本结果新增assigned|本结果丢失assigned|旧组拆分数|
|---|---:|---:|---:|---:|
|v05_M4|118470|9797|71505|43|
|v05_M5|121965|9205|74408|45|
|v06_overlap_joint|121883|8748|73869|42|
|v06_common_joint|119860|9677|72775|44|
|unit001_ADAPTIVE|6184|52883|2305|7|
|unit002_ADAPTIVE|56185|581|4|2|
|unit004_OVERLAP_FINAL|56222|540|0|1|
|unit005_BIRTH_FINAL|56762|0|0|0|

实际查看的[全景1](scenes/ficus/stages/BIRTH_FINAL/test_r_1_FULL.png)与[全景79](scenes/ficus/stages/BIRTH_FINAL/test_r_79_FULL.png)仍显示大量灰色碎片、重复线及向树冠外伸出的细长彩色尖刺，整体没有本轮改进。原几何冻结不能清除尖刺；它们是否被错误吸入某个身份仍是风险，不因“原核未变”而安全通过。没有源表面遮挡或辅助桥墨迹。

![实际原核全景](scenes/ficus/stages/BIRTH_FINAL/test_r_79_FULL.png)

可辨的继承弧7有356核、5个实质原parent和5个实质M4贡献者；[视图1](figures/PRIOR_UNIT002_CURVED_7/BIRTH_FINAL_test_r_1_GROUP_CROP4.png)、[视图79](figures/PRIOR_UNIT002_CURVED_7/BIRTH_FINAL_test_r_79_GROUP_CROP4.png)及[完整竞争上下文79](figures/PRIOR_UNIT002_CURVED_7/BIRTH_FINAL_test_r_79_CONTEXT.png)可见局部弧形。但最大旧来源11453的122核已覆盖全部38.810924p支持代理，本轮完全继承；这是重叠支持归组的例子，不是本轮域外长曲线恢复。

717的[视图1](figures/PRIOR_UNIT005_CURVED_717/BIRTH_FINAL_test_r_1_GROUP_CROP4.png)和[视图79](figures/PRIOR_UNIT005_CURVED_717/BIRTH_FINAL_test_r_79_GROUP_CROP4.png)仅为很短的浅弯细段；64核全部来自parent3723，支持17.672510p，不满足多片段标准。720同样47核单parent、支持15.826346p；本次读取其保存metrics，未逐图复检720，不能仅凭89°累计折线转角宣称可见曲线。

722的[放大图](figures/PRIOR_UNIT005_CURVED_722/BIRTH_FINAL_test_r_1_GROUP_CROP4.png)只呈微小点状，[上下文79](figures/PRIOR_UNIT005_CURVED_722/BIRTH_FINAL_test_r_79_CONTEXT.png)很小，无法核实长曲线。55核虽来自4个parent，只有2个达到12核/4p标准，M4贡献全部UNKNOWN。相对模型199的4.698436p域外代理只依赖3个继承核，不等于实质三片段续接。15个出生组中12个单parent，合格新增跨片段曲线为0。

继承直线行集482的[视图1](figures/PRIOR_STRAIGHT_482/BIRTH_FINAL_test_r_1_GROUP_CROP4.png)和[视图79](figures/PRIOR_STRAIGHT_482/BIRTH_FINAL_test_r_79_GROUP_CROP4.png)可见短直段；本轮无成员变化，不能称新增直线恢复。案例选择因此没有CURVED/STRAIGHT新增差异项，这是零结果，不用继承病例填补成功。

旧弧144的[保存行集](figures/PRIOR_CURVED_144/BIRTH_FINAL_test_r_79_GROUP_CROP4.png)仍分为两色，55/441的分裂未解决；旧损伤13054的[保存行集](figures/PRIOR_UNIT002_DAMAGED_13054/BIRTH_FINAL_test_r_1_GROUP_CROP4.png)仍为灰色。四类原负例均保留，本次实际复检[33117/201172](figures/FIXED_5_33117_201172/BIRTH_FINAL_test_r_79_GROUP_CROP4.png)可见小弧，但它不是物理GT。没有由这些小图充分排除平行、分支或深度吞并；其他未逐图检查病例不宣称安全。

统计必须区分有限长度、投影支持并集、最长支持段及gap。15个出生组的union=最长段、代理gap=0，来自协方差投影区间，不能证明真实连续观测。继承712的有限长度12.798399p、union10.647483p、最长段9.039903p、总/最大gap0.147181p，直接说明这些量不可互换。14个出生组没有旧已分配模型贡献，outward_reference_missing=true；其存储0不是测得域外为0，更不能反过来算全部新外延。

两个证据图实际是/home/u00134/cglib/data/full/ficus/val/r_1.png和val/r_79.png，对应本项目test_r_1/test_r_79；原test目录同名图的相机不同。相机核对通过不代表遮挡已知。这里的2px边缘命中可能来自纹理或前景遮挡物，负证据保持UNKNOWN；未核实深度可见性，未运行连续帧，没有held-out或物理身份认证。scan24/scan65本轮未运行。

核验范围：36份父级source_snapshot文件、2个renderer helper、17份阶段checkpoint与133份图checkpoint成员hash全部核对；128个R文件存在。所有保存GEOMETRY_AUDIT均all_fields_exact。本次分析只核对保存审计及hash，没有重载原全资产或重算几何。BUILD最终85项小测试通过；先前真实RED及夹具evidence_images遗漏失败日志均保留，测试不替代科学结果。

来源与复现入口：CONFIG SHA256 `6ef789ee86b78f1e339b399ce390ebaace322ac7aefa1e1a158d97bf89aa8843`；DECISION SHA256 `ff7efdb30373bfe0c292ae9e3aa8e24fd5bb686c9b0c44a0516244d7cd19faf7`。原gaussians SHA256 `c68a8243172e3aa1a1641e0372b483ff82d082a9000d204b5bcb34a7803ba065`；control SHA256 `0010535c3f30ce54021b10b6f284508fd04fb57baa099cdc7da91b540553b20a`；CAMERAS SHA256 `9020d0599f28aaa500b3c24bb28a8c6cc0c6896eda6753b407a9924e970670c4`。renderer.py SHA256 `ce24cd30d663e6f421064d83006f097b02a5cf6a74b20c177a905ca514caed93`，libjoint.so SHA256 `033a973a71dc5364677a5bf0625f23dc4fe445b70257f04de7cb70cdccca84b0`。完整图像及原始输入hash见[CONFIG](CONFIG.json)，所有源码hash与不可变快照映射见[PARENT_RUN_FROZEN](PARENT_RUN_FROZEN.json)。后续以快照为准，不要求最新工作树HEAD保持不变。

最终MEMBERSHIP SHA256 `bbcdc8457c99c14d183370584e82bad93df9cd8add83eda527cca26f1f920ebd`；MODELS SHA256 `1c79b11b25a7e88baf1342575d5a0274a807377e13f02b1c50e46f8949ac58c5`，均与unit005一致。冻结入口见[RUN_REQUEST](RUN_REQUEST.json)，命令为：

```text
/mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_8build_part_prior_feasibility_v03/venv/bin/python -B /home/u00134/3dgs_line/line_kernel_free_reassignment_v07/reproduction/line_kernel_free_reassignment_v07/image_path_runner.py --config /mnt/hdd1/u00134/radegs_paper_reproduction_v01/line_kernel_free_reassignment_v07_20261101/units/unit_006/CONFIG.json
```

分析没有再次执行该命令。旧输出、源码、失败与parent实际退出保持原样；由parent负责后续封存，不把可变运行流混入worker seal。

当前已过19:15停开新单元时间，停止新science并交付。此为当前时间边界，不是整个方法空间耗尽。一个后续待授权方案是“真实多视图有序边缘链对应产生新有限3D候选”，改变候选证据，避免继续对旧图作奖励/半径扫描；先核实连续对应与可见性，保留全部竞争解释，再以同状态不出生为对照。方案未运行，详见[NEXT](NEXT.json)。
