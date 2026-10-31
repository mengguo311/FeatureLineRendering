scan24 首个完整拓扑合并单元已经交付；工程执行完成，科学结论仍为 PARTIAL。

parent 实际数值子进程 PID 2856548 于 2026-10-31T05:44:09.659421+09:00 启动，2026-10-31T05:47:01.088141+09:00 结束，实际 returncode=0、reason=null；runner 记录耗时 170.692 秒。S0 输入、S2 完整合并状态、S3 冷载原生交付和 S4 诊断均有保存 checkpoint。不是 launcher 的 0，也不再是旧日志中无法恢复的内存进度。[RUN_RESULT.json](RUN_RESULT.json) 与 [实际 child EXIT](/mnt/hdd1/u00134/radegs_paper_reproduction_v01/line_kernel_edge_growth_v05_20261031/orchestration/unit_001/COMPUTE_EXIT.json) 为本次依据。

先前权限冲突和根目录早期 FINAL_REPORT/DELIVERY_STATUS 记录的是“计算尚未启动”的历史时点，予以保留；它们不是这次后来实际完成的计算状态。本单元 [STATUS.json](STATUS.json) 是本次分析状态。v04 的 UNKNOWN/-15 等历史退出不被改写。

| 指标 | 强 L0 | 池化 L1 | 本次 M2 合并 |
|---|---:|---:|---:|
| 原始核数 | 458490 | 458490 | 458490 |
| 已分配 | 210278 | 220726 | 224948 |
| UNKNOWN | 248212 | 237764 | 233542 |
| 主分组数 | 6187 | 6106 | 5884 |

相对 L1 新分配 4222 个核，覆盖率从 48.142% 到 49.063%。保存了 14602 次载体合并、49380 个有限载体和 68 张实际图片；合并数包含 dormant 支持载体，不能解释为 14602 个更大的可用主边实例。读取保存数组确认完整行顺序、224948 已分配和 5884 主组，L1 已有主分配丢失为 0。原始非颜色字段、源文件与固定相机的审计见 [GEOMETRY_AUDIT](scenes/scan24/stages/M2_MERGE_ONLY/GEOMETRY_AUDIT.json)；分析阶段没有重新拟合或渲染。

[MEMBERSHIP](scenes/scan24/stages/M2_MERGE_ONLY/MEMBERSHIP.npz)、[CARRIERS](scenes/scan24/stages/M2_MERGE_ONLY/CARRIERS.npz)、[GROUPS](scenes/scan24/stages/M2_MERGE_ONLY/GROUPS.json)、[LINEAGE](scenes/scan24/stages/M2_MERGE_ONLY/LINEAGE.json) 和合并前导出 checkpoint 均实际保存。主体图片是新成员颜色下的原始 Gaussian 核，不是拟合辅助曲线。

| M2 / camera 0012 | M2 / camera 0036 |
|---|---|
| ![M2 original kernels, camera 0012](scenes/scan24/stages/M2_MERGE_ONLY/0012_FULL.png) | ![M2 original kernels, camera 0036](scenes/scan24/stages/M2_MERGE_ONLY/0036_FULL.png) |

保存指标中 29 组满足冻结的支持增长门槛：23 个 line、6 个 polyline，其中 21 组跨旧 parent。全部 29 组的宿主域外支持大于 1p，21 组至少 4p；这不是仅靠核数增加。最大合格直线 103748：97+110 个 L1 核，去重支持 22.181→29.289p，域外支持 3.231p；其最长连续支持仅 2.721p、总间隙 4.407p。最大合格 polyline 202626：134+108 个 L1 核，支持 25.412→32.966p，域外支持 5.153p；最长连续支持 4.001p、总间隙 7.576p。因此“载体上更多有限支持”仍不等于物理连续长边。

视觉证据没有完成这一增长主张：实际检查了 30 张已保存 PNG，包括两相机 M2/L1 全景、五个固定最大组、同组 L1 对照，以及 parallel、branch、crossing/tangent、gap、ambiguity 和最小接受裕量的双视图。全景仍明显碎片化，没有看到明显整个物体被并成一组的灾难性表现，但这个尺度不能排除局部平行／深度错误。

现有孤立图片的五个选择中，**没有一组满足增长门槛**。308174 增至 741 核、支持增加 7.360p，但域外支持为 0；14128 增至 601 核也为 0；18608 未增长。额外的 line 302154 域外支持仅 0.000080p，polyline 290663 仅 0.082878p，两者均不合格。原选择器按“域外支持>EPS”挑最大组，选中了补充重叠支持／微小重拟合漂移，漏掉真正合格的 103748 和 202626。290663 的原生视图几乎不可见；硬负例也多为少量细像素，不能据此认证没有分支吞并。详细已看图片与判断见 [VISUAL_REVIEW.json](VISUAL_REVIEW.json)。本次不补画、不后改选择；真实直线和曲线向外增长的双视图确认仍缺失。

30000 次拟合上限耗尽，47772 条记录触及 fit_cap，另有 5301 ambiguity、9045 round_conflict、1934 parallel、17 branch 拒绝。候选搜索被截断，未宣称穷尽所有可能关联；这些限制保持固定，不据结果调阈值。

当前仅 scan24 L1→M2_MERGE_ONLY 完成。合并后池化、L3、L4、ficus、scan65 均 NOT_RUN。所有身份暂定；parent ID 仅溯源，未知核仍保留。没有物理真值、独立 held-out 或跨场景泛化结论，也没有把未支持间隙绘成桥。

下一步只推荐一个独立实验：**完全相同科学设置的 ficus 完整资产迁移**，由新单元 REVIEW/BUILD 冻结后交 parent 计算。用已保存 scan24 的合格直线／曲线作为只读对照修复选图，ficus 同样按 growth_gate 选图；不改候选、距离、转角、并行、分支、歧义和激活门槛。先做 L0、两次固定宿主池化 L1、一次 M2 合并，保存状态后再导出；scan65 保留为随后另行冻结的单元。资源与精确阶段见 [NEXT.json](NEXT.json)。本次没有启动它。

9 个源码快照、helper、config 与四个完整 checkpoint 的文件 SHA256 已核对。未来工作树 HEAD 可以变化，本次重现以 `source_snapshot/` 和 [ANALYSIS_PROVENANCE.json](ANALYSIS_PROVENANCE.json) 为准。实际计算命令为：

```text
/mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_8build_part_prior_feasibility_v03/venv/bin/python -B /home/u00134/3dgs_line/line_kernel_edge_growth_v05/reproduction/line_kernel_edge_growth_v05/runner.py --config /mnt/hdd1/u00134/radegs_paper_reproduction_v01/line_kernel_edge_growth_v05_20261031/units/unit_001/CONFIG.json
```

仅原先已冻结的新源码／文档被本地提交，commit `84ce0abdd990e3b2733971e395652609de634b9b`；没有源码编辑、重跑或 push。静态 SEAL 只覆盖本单元已关闭的产物与本分析文件，不封存运行中的 API 日志或 supervisor 状态。分析时间：2026-10-31T05:53:08.780752+09:00。
