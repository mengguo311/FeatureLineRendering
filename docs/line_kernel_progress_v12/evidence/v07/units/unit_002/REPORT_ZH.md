# unit002：覆盖优先种子与逐核自由重归属

工程执行完成；科学结论 **PARTIAL：局部多片段归属与重复支持汇集成立，新的完整长曲线恢复尚未证实**。没有把旧组保持作为目标。全景中的大部分核仍为UNKNOWN，尖刺依然存在。seed家族与分配方式一起改变，不能把效果归因于求解器。

## 实际执行和覆盖范围

父进程实际child **rc=0，reason=null**，2026-11-01 17:51:06.591924—17:52:51.479612 JST；runner报告104.426秒。四个完整阶段FREE_STATIC、FREE_ADAPTIVE_1/2/3均落盘。STATIC和ADAPTIVE_3各有固定test_r_1/test_r_79原生全景；18组诊断共36个视图的bbox均非空。非空不等于可辨或安全通过。

核数285956，原切向有效285956。全体核都参与现有模型的完整有限段竞争；模型发现不完整。扫描29070条旧carrier记录，保存29019个有限种子候选及56条拒绝记录（窗口数不等于carrier数）。完整种子库可兼容102391/102910个有效中心体素；512种子只覆盖17580个，85330个有效体素未被所选种子覆盖。另有27308个未选候选仍有正边际覆盖、1199个边际为零。不能把完整候选库或全行导出冒称完整场景解释。

|阶段|assigned|UNKNOWN|有效模型|
|---|---:|---:|---:|
|STATIC|53176|232780|516|
|ADAPTIVE_1|55499|230457|519|
|ADAPTIVE_2|55989|229967|520|
|ADAPTIVE_3|56185|229771|520|

STATIC原始竞争53188核，支持检验后53176；最终周期原始57248核，支持检验后56185。最终UNKNOWN原因：226926无几何候选、1782竞争/UNKNOWN余量、1063支持不足。这是当前模型可达性不足，不能归因为全部真实核不可归组。第3轮64个出生提案、63个death_piece；93次更新接受、416次window_turn、7次vertex_turn、4次knot_cap拒绝，另1个模型无主成员死亡。拒绝记录和上一有效状态均保留。

## 表示及实际归属自由度

潜在对象是有限、可变形、可生灭/支持拆分的折线。旧q仅提供种子形状与来源，旧行归属不初始化主标签，也不锁定它。原核按距离/切向在全部当前有限段间竞争；辅助模型不渲染。原mean/covariance/opacity/colors/parent/piece/arc_t字段审计逐项一致。

相对STATIC，最终新增3323个已分配、撤回314个、19个旧静态组拆分；净增3009不代表准确率。相对各封存参考：

|参考|参考assigned|新增分配|撤回分配|旧组拆成多个新组|
|---|---:|---:|---:|---:|
|v05 M4|118470|9679|71964|43|
|v05 M5|121965|9100|74880|44|
|v06 overlap joint|121883|8630|74328|42|
|v06 common joint|119860|9559|73234|44|
|unit001 STATIC|4577|53546|1938|4|
|unit001 ADAPTIVE_3|6184|52355|2354|6|

例如M4组19563的53核变为33核归120、14核归246、6核UNKNOWN；确有逐核拆分，而非旧片段换名。numeric_id_changes跨运行不具有身份准确率意义。上述撤回/拆分在本合同中允许，但必须作为视觉得失报告，不能隐藏。

## 实际图像及反例

完整对象双视图显示更多彩色叶缘/短弧，但盆、主干和大量叶线仍灰色；若干原有长尖刺也获得彩色身份。固定几何不能消除尖刺；给它们归组不构成正确边恢复。本轮无源表面遮挡，也没有辅助载体或桥的笔画。

![最终全景1](scenes/ficus/stages/FREE_ADAPTIVE_3/test_r_1_FULL.png)
![最终全景79](scenes/ficus/stages/FREE_ADAPTIVE_3/test_r_79_FULL.png)

实际查看了CURVED_7/15/11的两个隔离视图，7与11的局部上下文，以及7的全对象highlight。7为356核、5个实质M4片段/5个实质parent；11为255核、5个实质M4片段/4个parent；15为212核、3个实质M4片段/4个parent。实质门槛为每个>=12核且>=4p投影支持。这不是大旧弧只附几颗核：其他贡献足够大。但**三个组各自都有一个旧种子覆盖几乎全部现支持域**：7的M4片段284665独自覆盖38.810924p，11的32707覆盖33.466079p，15的65959覆盖33.587728p。其主要收益是已有有限范围内的多来源归属/重复观测汇集，不能称为新外延。STATIC同核图已呈现主要形状；未证实三个自适应周期带来新曲线恢复。

![曲线7](figures/CURVED_7/FREE_ADAPTIVE_3_test_r_79_GROUP_CROP4.png)
![曲线11](figures/CURVED_11/FREE_ADAPTIVE_3_test_r_79_GROUP_CROP4.png)

STRAIGHT_43双视图为短直线，180核、4实质M4片段/5parent，19.470154p；84为122核、3/3，24.248706p，在全景是很小的主干局部。两者也已有单个来源覆盖全长度，不是新增直线外延。辅助曲率代理不等于可见曲率：7累计转角146°，实际图仍只是浅弧。每个crop均为实际原核、原固定相机，未另画连接。

![直线84](figures/STRAIGHT_84/FREE_ADAPTIVE_3_test_r_79_GROUP_CROP4.png)

明确损失：unit001 CURVED_144精确198行在本轮成为150核组55、47核组441、1核UNKNOWN，两个视图可见同一短弧被分色，旧局部正例未保持统一。unit001 CURVED_382有30核UNKNOWN、152核归68；STRAIGHT_482的127核全归6（原本主要单来源，不算新跨片段恢复）。受损13054的96核全UNKNOWN，37737的90核中87核UNKNOWN，9969的87核全UNKNOWN；查看13054与v05 M5同核图，原弧仍在而标签被撤回。

![unit001短弧现在被拆分](figures/UNIT001_CURVED_144/FREE_ADAPTIVE_3_test_r_79_GROUP_CROP4.png)
![原短弧对照](figures/UNIT001_CURVED_144/unit001_ADAPTIVE_test_r_79_GROUP_CROP4.png)
![撤回案例13054](figures/DAMAGED_13054/FREE_ADAPTIVE_3_test_r_79_GROUP_CROP4.png)

六个固定上下文现在均通过CARRIERS行偏移取回，包含UNKNOWN。11/80709有33行且图像非空，修复了前轮空上下文；其图仍灰且很小，不能判安全。16931/18768、112/205435、33117/201172实际图中有彩色局部，但不能由小crop证明平行、分支或深度结构未混入。64355/65064也不足以证完整曲线。保存context为每个成员中心2p内的全部原核，并有全对象highlight；这不等于已经穷尽所有物理解释或验证遮挡。没有把未查看的其余视图标作通过。

## 支持长度与结论边界

支持是沿辅助q的协方差半宽投影代理，不是新测得的连续物理曲线。7/11/15的支持并集与最长代理段相等、代理gap为零，仍不能证明原图观测无间隙。105则并集23.793786p、最长15.383387p、gap0.124777p，清楚说明并集不可当连续长度。原核端点、重复覆盖、深度投影与物理身份仍不同。全对象洁净/完整性、平行/分支安全、时间稳定与held-out泛化均未证实；所有身份provisional。

## 来源、可重放性及下一步

本分析只读取保存产物，没有拟合、重渲染、测试或源码修改。核对12个父级source_snapshot文件及两个只读renderer/libjoint helper哈希，四个完整阶段CHECKPOINT各文件哈希，以及CONFIG/DECISION绑定，均一致。检查保存membership的285956行和原行序；原核几何审计all_fields_exact=true。READINESS.json保存全部资产/相机/参考输入哈希；PARENT_RUN_FROZEN.json保存快照映射。保留实际退出、原RUN_RESULT和所有拒绝，未用分析脚本退出覆盖科学退出。

CONFIG SHA256：`9df62cacc28d37f6cd1ac99c7f75af9908ea7f7e39fb71234b451fecb0b21180`；DECISION：`2e8a7dcc078ecc4dfce3f5e619e2f170b4e1d3c06b243912bb207770c0539611`。核心free_core SHA256：`5fa12b98da4d24000294a760281e3a51054e455d5cf0762ea18b2b1bb4efa81e`，与unit001一致。seed CARRIERS：`813b45f98b34c8f64b21a9655ed72b0da5063f373192e55356e10c8b5e029415`。精确helper和全部source哈希附于STATUS.json；未来引用快照，不依赖worktree最新HEAD。

父进程入口（仅记录，不在分析执行）：
```text
/mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_8build_part_prior_feasibility_v03/venv/bin/python -B /home/u00134/3dgs_line/line_kernel_free_reassignment_v07/reproduction/line_kernel_free_reassignment_v07/coverage_runner.py --config /mnt/hdd1/u00134/radegs_paper_reproduction_v01/line_kernel_free_reassignment_v07_20261101/units/unit_002/CONFIG.json
```

建议继续一个独立新机制：**可撤销的模型合并/共同重拟合，再对全部原核重竞争**。以当前保存的动态模型为可修改解释，对照不启用合并的同状态重竞争；预注册55/441短弧分裂及继承长弧7/11/15，保留完整竞争邻域与全部负例。目标是超过单个种子的真实跨片段续接，而非减少模型数、换色或再加种子。具体模型选择准则、候选完整性与预算须先由下一review冻结；本轮未运行，也没有静默更改阈值。仍在新窗口内，不因前轮弱结果停止研究。见NEXT.json。
