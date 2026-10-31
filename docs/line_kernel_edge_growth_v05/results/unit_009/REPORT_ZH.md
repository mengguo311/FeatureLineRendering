# Unit 009：scan65 第三轮合并分析

执行完成，科学结论为 **PARTIAL**。279616行M4映射、有限载体、支持区间、谱系和双相机全资产图已保存并冷载核验。已分配125863、UNKNOWN153753，较M3新增7520个主分配；新增核数不能直接冒充边长度增长。

Parent实际子进程PID2932161，2026-10-31 08:26:12.454741至08:28:53.656607 JST，returncode=0、reason=null；runner耗时160.718秒。[COMPUTE_EXIT](../../orchestration/unit_009/COMPUTE_EXIT.json)为实际退出依据，不是launcher返回。既有v04失败、UNKNOWN退出及review超时记录保持原样；v04只完成L0/L1，仍为PARTIAL。

[原生全景0012](scenes/scan65/stages/M4_MERGE_ONLY/0012_FULL.png) · [原生全景0036](scenes/scan65/stages/M4_MERGE_ONLY/0036_FULL.png) · [全行映射](scenes/scan65/stages/M4_MERGE_ONLY/MEMBERSHIP.npz) · [载体/有限支持](scenes/scan65/stages/M4_MERGE_ONLY/CARRIERS.npz)

| 阶段 | 已分配 | UNKNOWN | 主组数 |
|---|---:|---:|---:|
| L0 strong v03 | 97950 | 181666 | 3490 |
| L1 containment only | 112061 | 167555 | 3450 |
| M2 | 114798 | 164818 | 3402 |
| M3 | 118343 | 161273 | 3443 |
| M4 | 125863 | 153753 | 3665 |

L1为锁定宿主范围的池化；M2/M3/M4分别增加拓扑轮次，同时增加累计计算机会。本次覆盖45.01%，1657次接受合并、18069次fit，未触及30000上限。候选截断36986、样本查询饱和41800；connector拒绝20572、endpoint_gap28604、residual10916、parallel1661、branch34、ambiguity2077。

11组满足冻结增长门槛（3 line/8 polyline），8组有两个实质原parent，9组域外支持至少4p，二者交集6组。只有30579同时具有三实质L1片段和两个实质原parent。下表长度均为p；支持为投影有限区间并集，不包含补画桥接。

| 组 | 模型/核数 | M3贡献核数 | 支持并集 | 增量 | 域外支持 | 最长连续段 | 总/最大间隙 | 有限载体长 | 实质L1/原parent |
|---|---|---|---:|---:|---:|---:|---|---:|---|
| 5558 | line/148 | 106+42 | 29.468 | 7.705 | 7.720 | 2.425 | 8.392/1.215 | 37.860 | 2/2 |
| 30579 | polyline/99 | 76+23 | 20.517 | 5.007 | 5.121 | 5.543 | 3.976/1.125 | 24.510 | 3/3 |
| 61271 | polyline/71 | 38+33 | 17.686 | 7.716 | 7.710 | 1.896 | 4.718/1.335 | 22.424 | 2/2 |
| 46740 | line/155 | 110+45 | 16.680 | 4.271 | 2.933 | 6.528 | 0.705/0.288 | 17.386 | 2/4 |
| 22130 | polyline/84 | 66+18 | 18.520 | 4.335 | 4.401 | 1.801 | 5.612/0.360 | 24.180 | 1/1 |
| 64877 | polyline/121 | 118+3 | 22.970 | 0.035 | 0.000 | 12.331 | 2.783/0.393 | 25.775 | 2/3 |
| 167509 | polyline/104 | 100+4 | 27.573 | 0.843 | 0.002 | 1.585 | 13.098/1.495 | 40.714 | 4/1 |

精确bbox、extent及M3/M2/L1/v03/原parent贡献见[GROUPS](scenes/scan65/stages/M4_MERGE_ONLY/GROUPS.json)。贡献区间可重叠，不能直接求和。5558两个原parent贡献113/35核；30579三个实质原parent贡献20/16/49核；61271两个实质原parent贡献38/29核。

已直接查看338张保存PNG中的62张：双全景、12个固定选择组的全部M4双视图、5个增长例的M3/parent双视图、六类完整精确上下文双视图以及30579/61271双视图highlight。没有声称全部图片均经查看；清单与观察见[VISUAL_REVIEW](VISUAL_REVIEW.json)。

- 5558：[0012 M3](scenes/scan65/stages/M4_MERGE_ONLY/diagnostics/CROP_5558_0012_GROUP_5558_M3_0012.png) / [M4](scenes/scan65/stages/M4_MERGE_ONLY/diagnostics/CROP_5558_0012_GROUP_5558_M4_0012.png) / [parents](scenes/scan65/stages/M4_MERGE_ONLY/diagnostics/CROP_5558_0012_GROUP_5558_PARENTS_0012.png)；[0036 M3](scenes/scan65/stages/M4_MERGE_ONLY/diagnostics/CROP_5558_0036_GROUP_5558_M3_0036.png) / [M4](scenes/scan65/stages/M4_MERGE_ONLY/diagnostics/CROP_5558_0036_GROUP_5558_M4_0036.png) / [parents](scenes/scan65/stages/M4_MERGE_ONLY/diagnostics/CROP_5558_0036_GROUP_5558_PARENTS_0036.png)。
- 30579：[0012 M3](scenes/scan65/stages/M4_MERGE_ONLY/diagnostics/CROP_30579_0012_GROUP_30579_M3_0012.png) / [M4](scenes/scan65/stages/M4_MERGE_ONLY/diagnostics/CROP_30579_0012_GROUP_30579_M4_0012.png) / [parents](scenes/scan65/stages/M4_MERGE_ONLY/diagnostics/CROP_30579_0012_GROUP_30579_PARENTS_0012.png)；[0036 M3](scenes/scan65/stages/M4_MERGE_ONLY/diagnostics/CROP_30579_0036_GROUP_30579_M3_0036.png) / [M4](scenes/scan65/stages/M4_MERGE_ONLY/diagnostics/CROP_30579_0036_GROUP_30579_M4_0036.png) / [parents](scenes/scan65/stages/M4_MERGE_ONLY/diagnostics/CROP_30579_0036_GROUP_30579_PARENTS_0036.png)。
- 61271：[0012 M3](scenes/scan65/stages/M4_MERGE_ONLY/diagnostics/CROP_61271_0012_GROUP_61271_M3_0012.png) / [M4](scenes/scan65/stages/M4_MERGE_ONLY/diagnostics/CROP_61271_0012_GROUP_61271_M4_0012.png) / [parents](scenes/scan65/stages/M4_MERGE_ONLY/diagnostics/CROP_61271_0012_GROUP_61271_PARENTS_0012.png)；[0036 M3](scenes/scan65/stages/M4_MERGE_ONLY/diagnostics/CROP_61271_0036_GROUP_61271_M3_0036.png) / [M4](scenes/scan65/stages/M4_MERGE_ONLY/diagnostics/CROP_61271_0036_GROUP_61271_M4_0036.png) / [parents](scenes/scan65/stages/M4_MERGE_ONLY/diagnostics/CROP_61271_0036_GROUP_61271_PARENTS_0036.png)。

5558双视图显示近直线组合；61271呈短而轻弯的两段组合，但原生分辨率有限。30579在0012可见弯曲，0036却被原生画面下边界截断，不能完成三片段曲线的双视图验证。46740域外仅2.933p；22130中79/84核来自同一原parent，不计实质跨parent成功。13285/24690/112102/84607/25117/198936未入固定选图，仅有数值增长证据。

最大曲线238627/61267/64111/67265的域外增长均为0，形态主要继承自前驱。56133未增长；64877仅新增3核、域外0；167509新增4核、域外0.00248p且只有一个实质原parent。重复支持、内部填补、微漂移均未当作实质延伸。

六类精确上下文均已查看双视图，但branch/gap/ambiguity等仅占很少原生像素，不能据此排除深度分离或分支。最差接受12331(v18865)+32301(v0)的q95=0.4995798p，接近0.5p界限；切向拒绝169208+169213为30.0003806°。完整版本/行集见[CONTEXT_SELECTION](scenes/scan65/stages/M4_MERGE_ONLY/diagnostics/CONTEXT_SELECTION.json)。数值通过不等于物理身份验证。

核验39份parent源快照、44项输入、40项helper引用（含4个获准外部helper）及5个完整检查点。全行顺序、carrier归属、前驱已分配成员保留、贡献核数和均一致；means/covariance/opacity/primitive_id/internal_piece_id/arc_t的dtype、shape及字节哈希一致。颜色之外没有导出或变更新几何。见[ANALYSIS_AUDIT](ANALYSIS_AUDIT.json)。

CONFIG SHA256 `3bbee014bf25d241a6576a43d0162da31700fd1a1dc098f9267e2c0f4f2e2979`；DECISION SHA256 `1a2de64510339186e516c04c782ab080dc8602bd9b855dcd84d30b4c2aefe0e5`。使用[PARENT_RUN_FROZEN](PARENT_RUN_FROZEN.json)中的不可变snapshot映射核验，不依赖以后工作树HEAD。Parent命令：

```text
/mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_8build_part_prior_feasibility_v03/venv/bin/python -B /home/u00134/3dgs_line/line_kernel_edge_growth_v05/reproduction/line_kernel_edge_growth_v05/continuation_level.py --config /mnt/hdd1/u00134/radegs_paper_reproduction_v01/line_kernel_edge_growth_v05_20261031/units/unit_009/CONFIG.json
```

本单元未运行初始化、池化、M5或其他场景。同设置scan24/ficus/scan65 M4现分别保存在unit007/008/009；只作已保存对照，没有重跑。所有身份暂定，间隙不证明物理连续性；无独立held-out或泛化主张。

下一步建议使用相同scan65 M3输入，仅检验歧义重复等价中的局部切向表示，与本单元M4对照。61267有6个有效候选因ambiguity被拒；冻结代码用整条候选的首尾弦比较参考曲线局部切向，可能误判重合曲线。这仍是待验证假设，不保证增长。保持候选、拟合、距离/角度阈值、轮数不变；具体单变量、对照及否证见[NEXT](NEXT.json)。本次未启动该实验。

分析未修改源码或参数。一次报告写入命令因重复关键字产生SyntaxError，解析阶段即退出、未写科学结果；已修正行政写入，实际科学子进程退出码仍为0。静态SEAL仅覆盖已关闭单元文件，不纳入外部orchestration流或API输出。
