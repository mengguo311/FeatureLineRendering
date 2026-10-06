# RGB 标注像素强制推核与八视角频率统计：实际结果

两场景均已完成：复用此前 RGB spatial union 显示墨迹，每个有中心可见原始 Gaussian 的标注像素投出恰好一票，再按八视角累计原始像素频率选固定核集合。没有沿用旧自动 REFUSED/平面 null floor，也没有把内部线排除。输出是 **line-support candidate（线像素支持候选核）**，不是永久物理边缘核。

实测判断：**工程映射完成，线绘效果仍是 PARTIAL，没有显示清楚的 D 推核优势。** 两个保留相机合计，TOP500 线域质量召回为 Lego **1.4575%**、Chair **0.8268%**，中心最大 alpha·T 对照为 **1.6409% / 0.8238%**；非线域泄漏为 **86.55% / 81.98%**。TOP2000 也只是 **5.1215% / 3.0596%** 线域质量召回。内部支持已确实存在，但图中仍是稀疏斑块或宽足迹，不能读成完整、干净的物理特征线。

K8→K32 的同四源视角 TOP500 Jaccard 为 Lego **0.4771**、Chair **0.2837**；这一大幅变化与截断残量使主方法大量回退有关。八图主分配回退分别 **209,976（65.53%）/144,140（80.95%）** 个有效像素，回退仍全部接收真实中心核。屏幕内部标注像素分别 **281,706 / 150,015** 个，全部接收一票；这证明内部参与工程分配，不证明内部物理边语义。

## 先看实际图

| 场景 | 四相机原始核子集 TOP100 / TOP500 / TOP2000 / V≥4 | 完整 RGB、旧墨迹、TOP500 子集与 full-T 支持 | V≥2 / 4 / 6 全部核 | 强制中心最大权重对照 | 两个计票保留相机 |
| --- | --- | --- | --- | --- | --- |
| Lego | [四视角 selected-only](media/lego/fourview_selected_only.png) | [完整定位](media/lego/fourview_evidence.jpg) | [跨视角复现](media/lego/fourview_recurrence.png) | [对照](media/lego/fourview_mandatory_baseline.jpg) | [r_001/r_014](media/lego/two_holdout_views.jpg) |
| Chair | [四视角 selected-only](media/chair/fourview_selected_only.png) | [完整定位](media/chair/fourview_evidence.jpg) | [跨视角复现](media/chair/fourview_recurrence.png) | [对照](media/chair/fourview_mandatory_baseline.jpg) | [r_001/r_014](media/chair/two_holdout_views.jpg) |

主集合 TOP500、诊断 TOP100/TOP2000 在实测计票前固定；四行 r_000/r_008/r_018/r_030 使用同一套原始 IDs。V≥4 列包含所有满足四视角出现条件的核，真实数量写在图里。selected-only 图只保留原 SH3/位置/尺度/旋转/透明度，移除其他核会改变 T。full-T contribution 在完整模型不删核时用独立特征通道测量，紫红叠加 gain=6；频率图是 log1p(F)/log1p(maxF) 原始核特征在完整 T 下的贡献，gain=8。它们是诊断展示，不是修改原核颜色，也不是黑色艺术线条。

## 冻结输入与分配

每场景使用 DEV r_007/r_033/r_059/r_086 和固定 r_000/r_008/r_018/r_030，共八个不同外参；没有把 33 个邻近 arc 帧称为独立视角。r_001/r_014 的不同外参在计票前保留，只用于固定集合评价。十个相机均为历史 GS/研究见过的探索性相机，保留相机也不是正式盲测。

标注来自原 float32 `union` 经旧 `ink(gain=1,sigma=.5)` 的显示 darkness>0.2；每个整数像素都保留，没有再侵蚀/NMS/膨胀筛掉标注。弱墨迹 `0<darkness≤.2` 单独保存与计数。旧 RGB-only spatial union 没有混入 temporal 或 alpha 辅助轮廓。八个缓存 RGB 与实际 stock/fullSH3/K8 输出逐位相等，旧四张显示 PNG 对应墨迹逐像素相等；r_000 的同算法重算 union/normal/confidence 逐位相等。完整 K、w2c、800×800 RGBA 与实际 metadata 文件名匹配和哈希在 [生产冻结](PRODUCTION_FREEZE.json)。

使用旧张量 normal（等价旧切线旋转 90°，符号无关），不是二值线图梯度。沿 normal 两侧 δ=2 做四邻居双线性采样，按原始 ID 合并贡献，不插值 top-K 槽位。候选是中心及两侧 ID 并集；主接收核必须在中心有 `w_i(p)>0`。对中心可见候选取最大 `D_i=|w_i(p−2n)−w_i(p+2n)|`。D≤2e−6、旧方向 confidence<.22/不定义、两侧截断残量大于最大 D 或端点越界时，回退到中心最大 alpha·T，等值按最小原始 ID。

这些可靠性条件只决定 D 或回退；不取消有真实贡献的像素的票。中心无可见贡献的标注像素保留在 mask，记 `UNASSIGNABLE_BACKGROUND` 并存坐标/地图。端点最佳核若中心权重为零，只在诊断中记录，不能接收该像素。K8 缺失端点 ID 的质量是未知，所选 D 最优仅针对保留的中心候选，不能宣称全 N 最优或像素因果责任。

## 实际计票

`c_iv=bincount(winnerIDs,minlength=originalN)`；主要排名 `F_i=Σ_v c_iv`，同票按 distinct-view `V_i` 降序再 original-ID 升序。另存 `Σ_v c_iv/marked_pixel_count_v`、曝光次数/可见质量归一化诊断，均不替代主频率。一个核同视角赢一百像素，V 仍只增加一。

| 场景 | 标注像素（8图累计） | 收到一票 | 无中心贡献 | 得票核数 | V≥2 / ≥4 / ≥6 核数 |
| --- | ---: | ---: | ---: | ---: | ---: |
| lego | 320,483 | 320,434 | 49 | 61,114 | 31,348 / 9,532 / 1,571 |
| chair | 178,125 | 178,052 | 73 | 47,303 | 19,925 / 4,152 / 907 |

完整每视角标注/弱墨迹/回退/未知/内外域数据见 [FINAL.json](FINAL.json) 和 `results/*vote*.json`。八视角出现频率与核投影面积、可见质量、遮挡、纹理和图像细节密度混杂；宽核可赢很多像素。强制完整分配是工程契约，不是算法效果的证据。

| 场景 | raw 排名 | original ID | raw 像素票 | 出现视角数 | 回退票比例 |
| --- | ---: | ---: | ---: | ---: | ---: |
| lego | 1 | 18524 | 355 | 6 | 66.48% |
| lego | 2 | 9235 | 336 | 5 | 69.35% |
| lego | 3 | 11272 | 275 | 7 | 73.09% |
| lego | 4 | 7455 | 258 | 6 | 65.89% |
| lego | 5 | 6433 | 256 | 7 | 82.81% |
| lego | 6 | 11277 | 227 | 6 | 82.38% |
| lego | 7 | 524 | 215 | 6 | 91.16% |
| lego | 8 | 6722 | 211 | 6 | 56.87% |
| lego | 9 | 72974 | 186 | 5 | 57.53% |
| lego | 10 | 1058 | 183 | 5 | 87.98% |
| chair | 1 | 67913 | 168 | 6 | 100.00% |
| chair | 2 | 57921 | 164 | 6 | 98.17% |
| chair | 3 | 69965 | 152 | 6 | 100.00% |
| chair | 4 | 643 | 131 | 5 | 100.00% |
| chair | 5 | 25797 | 127 | 5 | 22.83% |
| chair | 6 | 18324 | 124 | 5 | 100.00% |
| chair | 7 | 62642 | 124 | 5 | 100.00% |
| chair | 8 | 178642 | 123 | 4 | 49.59% |
| chair | 9 | 4212 | 118 | 6 | 0.85% |
| chair | 10 | 65196 | 113 | 6 | 100.00% |

[Lego TOP100 CSV](downloads/lego_top100.csv)、[Chair TOP100 CSV](downloads/chair_top100.csv)；[Lego 完整 N 行计数/固定 IDs](downloads/lego_votes_all_original.npz)、[Chair 完整 N 行计数/固定 IDs](downloads/chair_votes_all_original.npz)。`downloads/<scene>/<view>/source_fields.npz` 保存 float32 RGB/union/ink/normal/confidence 和未改二值 mask；`assignment.npz` 保存 int32 winner_map、fallback_map、原始 N 计数、选中中心权重、D、未知残量、端点替代诊断。未保存新模型。

## 保留视角效果与对照

实际 full-model T 支持质量在两保留相机的旧 RGB 标注域上评价；质量召回=所选核在标注域的贡献/完整 alpha 贡献。阈值覆盖率统计 selected/full-alpha>.1 或 .5 的像素比例，独立于质量召回。屏幕内部定义原 alpha>.5 的 SDF>4，轮廓域为 |SDF|≤4，仅区分屏幕覆盖区域，不等于几何或材质语义。

center 对照在每个相同可分配像素强制选最大中心 alpha·T，再按相同 raw 票排名。random 与主集合等数量，按八源视角全模型可见质量的 .1 宽 log bin 逐核匹配，从所有原始核无放回抽样；匹配质量误差和重叠核数如实保留。nofallback 只保留可靠 D 的票，是拒绝/无回退消融，不能满足主强制契约。下表以两个保留视角质量/像素累计计算，未用它们调排名。

| 场景 | 固定集合 | 线域质量召回 | 内部线质量召回 | 轮廓线质量召回 | 线像素覆盖 >.1 / >.5 | 非线域泄漏质量占比 |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| lego | top500 | 1.4575% | 1.3214% | 3.0944% | 5.065% / 0.373% | 86.55% |
| lego | center_top500 | 1.6409% | 1.4411% | 4.0447% | 5.900% / 0.429% | 83.75% |
| lego | random_top500 | 1.2627% | 1.3536% | 0.1689% | 3.793% / 0.156% | 90.34% |
| lego | nofallback_top500 | 1.2917% | 1.3830% | 0.1931% | 3.923% / 0.199% | 89.54% |
| lego | top2000 | 5.1215% | 4.4958% | 12.6495% | 17.622% / 2.237% | 84.35% |
| lego | center_top2000 | 5.2640% | 4.4573% | 14.9694% | 18.159% / 2.638% | 81.47% |
| lego | random_top2000 | 3.8351% | 4.0505% | 1.2429% | 11.663% / 0.691% | 89.16% |
| lego | nofallback_top2000 | 3.8555% | 4.1211% | 0.6595% | 11.729% / 0.828% | 88.43% |
| chair | top500 | 0.8268% | 0.7238% | 2.4982% | 2.584% / 0.223% | 81.98% |
| chair | center_top500 | 0.8238% | 0.7003% | 2.8278% | 2.617% / 0.211% | 80.80% |
| chair | random_top500 | 0.6680% | 0.6504% | 0.9543% | 1.596% / 0.047% | 86.71% |
| chair | nofallback_top500 | 0.7244% | 0.5997% | 2.7488% | 2.082% / 0.329% | 86.77% |
| chair | top2000 | 3.0596% | 2.7689% | 7.7773% | 9.725% / 0.849% | 78.32% |
| chair | center_top2000 | 3.0101% | 2.7352% | 7.4717% | 9.542% / 0.834% | 77.56% |
| chair | random_top2000 | 2.6760% | 2.6917% | 2.4197% | 7.355% / 0.202% | 83.58% |
| chair | nofallback_top2000 | 2.6387% | 2.3476% | 7.3608% | 8.098% / 1.027% | 83.86% |

质量支持来自真实 native 特征渲染，不用投影中心当覆盖。删除其他核后的 selected-only 图不能当 full-T 覆盖图。即使 D 很大，核仍可能支持广阔平面；泄漏和可见质量归一化诊断用来显示这一点。此阶段应以保留视角实际视觉和对照表判断用途，不把 100% 可分配像素投票称为成功。

## 验证、限制与复现

先做 RED 缺接口，再通过九项 CPU 契约测试和独立 CPU 原生射线/full-T 特征检查。每场景 original PLY 解码与官方 GaussianModel 的位置、全 16×3 SH3、opacity/scale/rotation 逐位相等。每视图 stock/K8/fullSH3 RGB 逐位相等；每种渲染后完整原 RGB 再检查。四源视角 r_007/r_000/r_018/r_030 实跑 K16/32，保存每像素赢家变化、票数变化和同四图 TOP500/2000 Jaccard；未把四图敏感性说成八图 K32 实验。drop-one-view 仅从已存计数重排。

独立脚本用保存的原始 ID 缓冲区、标量字典采样和全 N 计数审计，不依赖主 assignment 实现；所有 source/display/eval 单元原子写文件并封 SHA，可恢复验证。运行秒数是每单元真实 wall time，详情见 FINAL。旧模型、metadata、源代码和旧目录已有 dirty reproduction/verification 文件保留原字节；保护审计见 `tests/PROTECTED_AFTER.json`。GPU0 按 PID 检查独占，CPU2、root 4GiB/Git 1.5GiB reserve、新阶段 8GiB cap 固定；无安装、新 kernel、训练、协方差优化或新增 primitives。

结论仅支持强制映射与固定多视角候选集合可运行、可视化。它没有证明永久物理边、3D 曲线或时间稳定性；正式语义/几何 GO 尚无证据。旧 RGB detector 的主要外观来自既有颜色结构张量组件，新增双侧 profile 的作用有限。GAER top-K ID/alpha·T 与邻域 raster-state 归因思想与 Hao/Mukai 作者稿有关；本轮是不同的强制像素映射与计票实验，不宣称方法新颖性。

[复现说明](REPRODUCE.md)、[来源映射](SOURCE_MAP.json)、[媒体与下载哈希](MEDIA_MANIFEST.json)、[独立审计](tests/INDEPENDENT_AUDIT.json)。主代理实际图片审阅单独记录在 `tests/VISUAL_REVIEW.json`；它不是独立人工语义真值。

额外展示：[Lego 频率与 full-T 支持](media/lego/fourview_frequency_and_support.jpg)、[Chair 频率与 full-T 支持](media/chair/fourview_frequency_and_support.jpg)、[Lego 内部原生 ROI](media/lego/fourview_internal_ROI_nearest2x.png)、[Chair 内部原生 ROI](media/chair/fourview_internal_ROI_nearest2x.png)。图中文字已用独立呈现脚本整理；原封印的生产面板保留。原 gain=8 频率图容易饱和，新增统一 gain=1 原始频率特征图，计票/排名/评价完全不变。原封印 ROI 预览采用重采样；新增 `native_ROI_nearest2x.png` 才是精确最近邻 2×。

[Lego 每视角计数](downloads/lego_per_view_counts.csv)、[Chair 每视角计数](downloads/chair_per_view_counts.csv)、[Lego 无贡献像素坐标](downloads/lego_unassignable_background_xy.csv)、[Chair 无贡献像素坐标](downloads/chair_unassignable_background_xy.csv)。

初次两场景实际 runner wall time **181.260 秒**；逐单元工作累计 Lego **92.302 秒**、Chair **76.385 秒**，其余为加载/校验开销。恢复运行 **13.753 秒**，**30 个封印单元跳过、新增生产渲染 0**。独立保存结果审计 **5,696 项通过**，保护 **3,198 个文件** 字节不变。随机集合的源可见质量总量匹配误差均低于 0.12%，但它可与主集合重叠，TOP500 重叠 Lego112/Chair58 个；不把它描述成完全独立的不相交集合。

出处区别：旧图像法已有经典方向场/颜色张量基础，可对照 [Coherent Line Drawing 作者 PDF](https://cg.postech.ac.kr/papers/kang_npar07_hi.pdf)。[Hao/Mukai 作者预印本](https://mukai-lab.org/content/SA2026PosterHao.pdf) §2 保留 top-K ID/alpha·T，并比较邻域原始 ID 支持。它还使用深度/法线等 renderer states；本阶段复用的是已有 GAER 原生贡献缓冲区，通过旧 RGB 标注强制分配与统计，未复现该论文完整检测器。没有新颖性声明。
