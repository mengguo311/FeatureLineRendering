# unit_010：局部切向等价判定的完整 scan65 对照结果

执行完成；科学结论是 **相对 unit009 没有增益**。整体更大、连贯直线/曲线的物理证据仍为 PARTIAL。本单元没有因为测试通过或保存文件增多而取得新的分组进展。

实际数值子进程 PID2939044 于2026-10-31 08:52:05.683885至08:55:03.110238 JST运行，实际 returncode=0、reason=null；runner记录176.762456秒。权威记录为 ../../orchestration/unit_010/COMPUTE_EXIT.json，未用launcher退出码替代。RUN_RESULT.json原样保留。

## 保存结果与对照

全部279616个原始核已经保存、冷载并交付固定0012/0036全资产图；125863分配、153753 UNKNOWN、3665组。18069次拟合、1657次合并，未到30000上限；歧义拒绝2077。共有434张实际PNG，本分析直接查看38张，精确路径见VISUAL_REVIEW.json；其余不声称已目视检查。

1078个竞争选择中，旧全局弦方向与新局部切向的等价判定改变0项。原规则影子重现unit009的事件、载体、aux和主成员/原因，额外拟合0次。独立冷载检查确认全部11个membership字段、15个carrier字段逐数组相等；STATE.pkl字节相同，两张全景PNG字节相同。没有新分配、丢失分配、改变成员分区、额外合格增长组或额外域外支持。因此局部切向虽通过构造曲线夹具，却没有解释本次真实完整资产的停滞；不能推广为所有数据上无效。

相对M3仍有11个既有增长门槛组（3 line、8 polyline），其中8个有两个实质原parent、1个有三个实质L1、9个域外支持>=4p、6个同时有两个实质原parent和>=4p域外支持。这些全部已存在于unit009，**不是本次改动收益**。精确支持并集、最长连续段、有限长度、bbox、间隙和每层贡献保存在GROUPS.json。支持并集不等于载体长度；空隙不计支持，也没有补画。

## 真实图片判断

5558在两视图呈近直线，M3与parent配色显示两段贡献；61271是短而轻微弯曲的续接，两视图可见但原生像素少。它们的control/variant图片一致。30579在0012可见弯曲，0036原图底部裁切，不能满足双视图曲线证据。较大的238627、61267、64111曲线可见，但为既有组，域外增益为0。没有可供展示的changed-equivalence例子，诊断明确NO_CHANGED_EQUIVALENCE。

六类最小裕量上下文均已查看双视图：parallel、branch、crossing/tangent、gap、ambiguity和最差接受例。多数仅数个原生像素，4倍最近邻裁剪不能产生新证据；不据此宣布平行/深度/分支均正确。没有因这轮改动新吞并的结构（成员完全相等），但既有物理误合并风险并未由相等性消除。身份全部暂定，无物理真值或held-out泛化主张。

本单元未运行scan24、ficus、初始化、池化或M5；不是丢失的已请求阶段。旧v04仍为历史PARTIAL，旧失败/UNKNOWN退出不变。

## 来源、闭合性与限制

CONFIG SHA256：633342073a031b1a39de2025a960c164d1d82da1ffc30d848e572f58e876ddcd。
DECISION SHA256：a7cc7da2c1050d67a7cb88ec85138ed6262aebf7ad56a07ea56f4d2df7a4326e。
使用PARENT_RUN_FROZEN.json指向的46份不可变source_snapshot；61输入与43helper引用（含4外部helper）哈希验证通过。六个科学检查点及所列文件均通过。原gaussians.npz哈希及6个非颜色字段、数量/行序审计通过；核位置、协方差、宽度/opacity不变。只读核验见ANALYSIS_AUDIT.json。以后不依赖工作树latestHEAD。

父进程请求命令：
`/mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_8build_part_prior_feasibility_v03/venv/bin/python -B /home/u00134/3dgs_line/line_kernel_edge_growth_v05/reproduction/line_kernel_edge_growth_v05/local_runner.py --config /mnt/hdd1/u00134/radegs_paper_reproduction_v01/line_kernel_edge_growth_v05_20261031/units/unit_010/CONFIG.json`。
历史实现以snapshot/local_runner.py及其同目录冻结依赖为准。BUILD的11项测试实际rc0、真实RED rc1保留；分析没有重跑测试、拟合或渲染，没有源码改动。分析首次只读命令因通用python不在PATH返回127，随后使用批准venv读取；该管理命令失败不覆盖实际科学rc0。

下一独立建议：完整scan24同一M3→M4，原规则、相同候选顺序和几何守卫，仅将单轮fit cap30000提高到40000，和unit007封存结果比较。unit007实际记录3767次fit_cap拒绝，而本轮局部等价修改零效果；这提供了具体未覆盖工作。共享拟合的前30000影子必须精确重现原对照，再完成全部竞争后提交。优先报告新增及丢失的实质域外支持和双视图，不把更多fit或核数当成功。详见NEXT.json；本阶段没有启动下一实验。

SEAL.json只列本单元已关闭静态文件（含本报告及不可变快照），不把外部orchestration/API运行输出纳入封存映射，也不包括SEAL自身。旧资产、源文件、实际退出和失败记录均保留。

