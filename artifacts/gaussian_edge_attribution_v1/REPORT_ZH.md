# 冻结 Gaussian 边缘贡献归因：实际实验报告

已完成 Mic 主场景和同配置 Materials 压力场景，共 **98/98 个 native800 姿态**。交付的是原始 Gaussian 固定 ID、连续贡献分数、类别/来源及真实跨视图属性投影；没有恢复、拼接或修复三维曲线。完整模型投影已验证，**完整贡献者归因仍为 UNDETERMINED**。

## 实际结果与边界

| 场景 | 原始核数 | eligible | F TOP4 未观测/未知 | top1% / 3% / 10% / 30% 核数 |
|---|---:|---:|---:|---|
| mic | 311,562 | 33,551 | 228,418 (73.31%) | 336 / 1,007 / 3,356 / 10,066 |
| materials | 282,537 | 72,124 | 134,802 (47.71%) | 722 / 2,164 / 7,213 / 21,638 |

未知表示没有进入这些 F 的 TOP4 缓存，不能解释为一定被遮挡、从未可见或负样本。eligible 仅排除总可见质量<1或可见视图<2的低可靠性估计，不是少核成功目标。所有核的原始连续估计仍可查看；主 P 对不可靠核作零属性弃权。

| C 的平均 lift（2px 固定容差） | 贡献基线 P | 双侧 P | 基线 top10% Q | 双侧 top10% Q | 匹配随机 Q | 单 F1 Q | 平移 null Q |
|---|---:|---:|---:|---:|---:|---:|---:|
| mic | 1.1374 | 1.1042 | 1.2141 | 1.2185 | 1.0204 | 1.1510 | 1.1353 |
| materials | 1.1684 | 1.1319 | 1.3194 | 1.3348 | 1.0728 | 1.0616 | 1.1426 |

lift = 属性质量落在独立二维证据容差区的比例 / 原始 alpha 质量落在同一区的比例，按视图计算后取均值。它描述对渲染证据的集中度，不是几何精度或真实边缘检出率。

| 场景 | C 容差区占 alpha 质量（均值） | top10% Q 集中度 | top10% Q 平均质量 | 随机 Q 平均质量 | 最差 C 的 top10% lift |
|---|---:|---:|---:|---:|---|
| mic | 81.49% | 98.75% | 2056.7 | 3391.3 | C_007: 1.1316 |
| materials | 71.38% | 94.07% | 5837.4 | 7428.7 | C_086: 1.1839 |

Mic 的双侧 top10% 比匹配随机更集中，但相对贡献基线的增量很小；双侧连续 P 反而弱于基线。不能据此宣称双侧扩展整体优越。高集中度同时受证据容差区较大影响；请结合原始 RGB、证据图、投影范围及每视图质量看。未宣称跨帧稳定性或时间上的优势。

| C 的双侧 Q 层级 | top1% lift | top3% lift | top10% lift | top30% lift |
|---|---:|---:|---:|---:|
| mic | 1.2328 | 1.2236 | 1.2185 | 1.2130 |
| materials | 1.3245 | 1.3475 | 1.3348 | 1.2830 |

所有层级均预先声明，未选“英雄图”或因视觉结果改变参数。整颗 Gaussian 选择自然形成较宽支持区域，不以线条细薄判定成败。随机组在 F 的 TOP4 质量与可见视图数分层内匹配数量，实际完整投影质量并不相等；另有同数量/质量缩放控制图，并保存原始质量与缩放系数。单 F1 可用核不足时不填入未知核：

- mic：top30% 主组 10066，单 F1 对照 8074；top10% 主组/单 F1为 3356/3356。
- materials：top30% 主组 21638，单 F1 对照 14531；top10% 主组/单 F1为 7213/7213。

## TOP4 局限与 native 验证

| 场景 | F 缓存/原始 alpha 质量 | C 缓存/原始 alpha 质量 | C top10% 选中组被 top4 捕获的投影质量 |
|---|---:|---:|---:|
| mic | 57.71% | 57.51% | 81.69% |
| materials | 58.31% | 57.98% | 76.47% |

复制到本工作区的 native top32 插桩首轮编译成功，固定 Mic F1/F41 的 RGB、alpha、深度和前4 ID/权重与原缓存完全一致。按主前景阈值，top4 质量覆盖为 56.75%/57.64%，top32 为 97.04%/95.98%。两 F 的 eligible 数从 6,962 增至 15,844；共同 eligible 上双侧 union Spearman=.9533，但各自 top10% Jaccard=.3881。条件排序相似不能证明贡献者集合完整。未扩大 K 或用 top32 改写主资产。详见 [完整性审计](research/COMPLETENESS_ZH.md)。

主图使用完整模型的原生遍历：所有核位置、形状、透明度和排序保持不变，预计算颜色换成固定分数或选择指示量，黑背景输出 `P=Σ_i(alpha_i*T_i)*score_i`、`Q=Σ_selected(alpha_i*T_i)`。未删除未选中核，也未让隐藏层因重合成而出现。全1属性对 alpha 的最大误差<9e-7，属性变化不改变 alpha/深度；98姿态均执行相同校准。这里的“完整”指原生阈值/提前终止定义下全部有效贡献，不是无限支撑积分。分数构建仍是 TOP4 截断估计。

## 协议与来源

先封存 [协议](PROTOCOL.md)、[配置](code/config.json)、[98姿态输入清单](INPUTS_FROZEN.json)，再读取新证据。每场景全部8F分数和选择先封存，C/arc只评价；Materials继承MicF证据尺度和显示增益。F=[1,14,27,41,53,67,79,93]，C=[7,21,33,47,59,73,86,99]；arc33复用预声明相机。所有100TRAIN在冻结GS训练阶段已见，包括C，因此不是盲测。

独立 RGB 梯度、渲染深度梯度、alpha 轮廓分别归因，不用 ID 切换构造主边缘证据。逐核 `ΣwE/Σw` 的分母覆盖完整缓存网格，保留非边缘反证；主分数再以每视图缓存总质量平衡视图影响。双侧使用独立软梯度方向、固定2/4像素偏移、集合重叠和相对深度差，只沉积到适当的前景/缓存最近层。ID切换本身不是几何，缓存最近层不是表面真值。详见 [资产字段](ASSET_SCHEMA_ZH.md)。

Gaussian Grouping 使用 SAM+DEVA、16D 可学习身份、联合重建和空间 KL；本次是冻结核上的解析贡献提升，不是论文复现，也不提出新颖性主张。[ECCV论文](https://www.ecva.net/papers/eccv_2024/papers_ECCV/papers/04195.pdf)、[官方代码](https://github.com/lkeab/gaussian-grouping)、[逐项文献核对](research/RELATED_WORK_ZH.md)。原始3DGS的可见性混合来自[原论文](https://repo-sam.inria.fr/fungraph/3d-gaussian-splatting/3d_gaussian_splatting_low.pdf)；实际使用已校准 RaDe 分支导出深度。

配方：native800，vanilla30k/seed1729，SH0 clipped DC，白背景原图/黑背景属性，kernel_size=0。45个高阶SH系数未参与此渲染，故Materials不是完整视角相关反射的验证。没有重训、曲线拟合、mesh、TEST、人工标注或 covariance-axis 法向。

工作基点 `d5c6d4d114b6b80ec5edb9c1717111e89a191eda`；协议封条 `171c0b88f4eb8276bbbb97a2e025c68e4f40df81f9535bd722ef86107c000edf`。逐来源源码、相机和checkpoint散列均在FINAL/INPUTS中。

## 检查、媒体与交付

CPU 单元/回归测试 38 项通过，另有 native helper 的7项CPU输入检查、实际F1/F41校准及98帧逐视图校准。独立审计每场景从原始F缓存重算32个eligible+16个未知ID，并在全部8C重算512随机+128强选中像素；不复用主归因求和实现。未知/反证、原始权重、封条不变和相机/全帧媒体检查通过。审计范围见 [访问审计](ACCESS_AUDIT.json)，不作超出所跟踪进程的全系统无访问声明。

访问范围偏差：早期独立合成测试曾使用默认 `/tmp` 创建自动清理的临时面板/封条文件；已改到本工作区并重新通过测试，已知临时路径已不存在，其他匿名临时路径的全局清理无法追溯证明。因此只对被跟踪的主 fit/project/calibration 进程报告工作区内持久写入，并明确记录这一偏差，不声称全会话所有临时写入都满足范围约束。

每场景49张五列native800图、49张类别/层级图、49张匹配控制图；两段完整33帧arc各有native与Telegram1600 H264/yuv420p/faststart。全部视频逐帧解码并散列，还检验去除标题后的RGB内容33帧互异。模型检查F/C、arc首中末和完整contacts，详见 [模型视觉复核](VISUAL_REVIEW.json)，不冒充人工GO。Mic预声明arc中段原始相机已有下方支架/电缆出画，未更改相机或后期裁图；完整帧序列不意味着每帧整个物体均入镜。

全C四档对比和可见质量诊断见 [逐C层级图](research/diagnostic_figures/C_lift_all_tiers.png)、[质量/覆盖/分数诊断](research/diagnostic_figures/visibility_mass_score_diagnostics.png)、[定量复核](research/METRIC_REVIEW_ZH.md)。

- **mic**：[完整49视图](media/mic/contact_all49.jpg) · [arc首中末](media/mic/contact_arc_first_mid_last.jpg) · [Telegram视频](media/mic/arc33_telegram1600.mp4) · [可编辑全ID分数](assets/mic/scores.npz) · [各类各档ID](assets/mic/selection.npz)。
- **materials**：[完整49视图](media/materials/contact_all49.jpg) · [arc首中末](media/materials/contact_arc_first_mid_last.jpg) · [Telegram视频](media/materials/arc33_telegram1600.mp4) · [可编辑全ID分数](assets/materials/scores.npz) · [各类各档ID](assets/materials/selection.npz)。

完整逐视图分母/反证/方向/侧/层来源、raw属性、native视频和完整properties的选中PLY保留于：

- `/mnt/hdd1/u00134/hybrid_raster_trained_models_v1/gaussian_edge_attribution_v1/out/gaussian_edge_attribution_v1/mic`：`assets/scores.npz`、`F/*/statistics.npz`、`frames/*/projection.npz`、`media/arc33_native.mp4`、`ply/*.ply` 与同名 `.original_ids.txt`。
- `/mnt/hdd1/u00134/hybrid_raster_trained_models_v1/gaussian_edge_attribution_v1/out/gaussian_edge_attribution_v1/materials`：`assets/scores.npz`、`F/*/statistics.npz`、`frames/*/projection.npz`、`media/arc33_native.mp4`、`ply/*.ply` 与同名 `.original_ids.txt`。

PLY子集保留原模型每个vertex属性和原始ID映射；单独渲染子集会改变遮挡，不能代替本报告的完整模型属性投影。[复现步骤](REPRODUCE.md)、[机器可读FINAL](FINAL.json)包含精确散列、实际计数、资格和未知项。
