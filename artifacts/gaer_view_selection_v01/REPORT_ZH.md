# GAER 按视角选核与有界删除诊断 v0.1

已完成 8/8 个实际 800×800 原生视角。输出包含每视角独立分数、原始 ID、仅选中核的原色 SH3 渲染，以及真实 opacity=0 删除对照。主展示为预注册 0.5% 预算诊断；自动阈值状态逐视角记录，不能将诊断预算当作自动选核成功。

Lego 保留全部 310475 行、Chair 全部 256690 行，原始 30k PLY/SH3/opacity/scale/rotation 与相机 metadata 均只读。相机按 r_1、r_14、r_7、r_33 文件名匹配实际 metadata，不按文件名中的数字直接索引。沿用已有隔离 GAER API 和二进制，未构建新 kernel。旧树脏 REPRODUCTION.json 的字节 SHA 被保护，未恢复、编辑或提交旧树。

## 方法与边界

深度为 NOT_AVAILABLE，额外几何数据 NOT_RUN。本次 E=1 是 alpha>0.5 的一像素内轮廓，不代表全部内部几何。法向来自 signed Euclidean distance 的梯度；修正原文 ∇E 在边响应脊线处可能为零的问题。端点 ±1/2/4px 使用固定法向；双线性采样先合并四邻域的 ORIGINAL ID，再做 D_i=|w_i^-−w_i^+|，没有逐槽插值。

raw_i=Σ E D_i；score_i=raw_i/(full_visibility_i+1e−6)，full_visibility 来自原生 RGB feature pass 对独立 precomputed color 的全像素梯度。bg=0、feature=1，各颜色通道相互独立；原始 RGB 始终另用完整 SH3。可见质量<0.25 的核分数置零，raw 最低证据 0.01。全量 raw、floored ratio、full visible mass 按原始模型行输出 NPY/NPZ。CPU 独立逐射线 accepted alpha*T 真值验证此梯度。

top-K 没出现的 ID 是截断未知项。双线性插值后的 R^-+R^+ 给出 |true L1−observed L1| 的界；保存 lower=max(0,L1−Rsum)、upper=L1+Rsum。背景/画面外贡献可为零，positive-alpha 截断遗漏不能称真实零。本阶段 K8 为主，全部 8 视角实际 K16/K32 重渲染并验证精确 K8 前缀。

同数量对照为 GAER raw、full-native alpha*T 在固定轮廓上的参与质量、独立 seed 的可见质量分箱匹配随机组。各方法原色 selected-only 渲染确实移除其他核、T 发生改变；full-T contribution feature pass 保留其他核的遮挡，单独绘制。投影中心与完整 footprint 的位置/质量分别统计。随机组全图质量匹配误差单独报告，不保证逐像素区域匹配。

三个预算为原模型计数的 0.1%、0.5%、1%（向上取整、仅有证据 eligible 核，不补零分核）。它们是诊断档位，没有按真实结果调最优比例。自动 ratio floor 由独立平坦共面 null 的 p99.9×2 与 numerical floor 的最大值固定，随后要求总未知界/L1≤0.1 与 heldout δ4 Jaccard≥0.6。删除结果从未参与阈值选择。

## 合成证据与限制

CPU 射线积分的 full-visibility 最大绝对误差 2.4651469e-06。纹理只改变颜色时，native IDs/weights 逐位相同；RGB 最大变化 0.420062。在独立真值明确无内部几何边的 441 个共面内点上，observed L1 均值 0.883265，最大 1.06795。这是 footprint 平滑导数的反例；自动 ratio floor=1.98611。

B4 standalone detector 为 NOT_RUN；没有用只在候选边处非零的图计算 AUROC/AP。真实图中的轮廓定位来自 alpha，并非 GAER 新检测器。本实验只检验已知固定轮廓上的核参与排序，H1 一般几何版本未验证。

## 八视角结果

|视角|原始核数|诊断选中数|自动状态/候选数|K8 全图质量覆盖|端点未知界/L1|选中 full-T 质量落在 ring4|full-T outside4 质量|
|---|---:|---:|---|---:|---:|---:|---:|
|lego_r_1|310475|1553|REFUSED/0|0.8121|0.3705|0.9723|0.0277|
|lego_r_14|310475|1553|REFUSED/0|0.8078|0.4155|0.9746|0.0254|
|lego_r_7|310475|1553|REFUSED/0|0.8119|0.5245|0.8964|0.1036|
|lego_r_33|310475|1553|REFUSED/0|0.8086|0.4253|0.9548|0.0452|
|chair_r_1|256690|1284|REFUSED/0|0.7630|0.3180|0.9468|0.0532|
|chair_r_14|256690|1284|REFUSED/0|0.7885|0.2404|0.9666|0.0334|
|chair_r_7|256690|1284|REFUSED/0|0.8343|0.2857|0.9344|0.0656|
|chair_r_33|256690|1284|REFUSED/0|0.8279|0.2619|0.9315|0.0685|

宽 footprint 或内部覆盖是应保留的失败情况；中心落在轮廓附近不代表全部贡献只位于轮廓。具体 raw/ratio dispersion、eligible/weak-mass counts、coverage quantiles 与 endpoint bound 均见每视角 JSON。

## 独立真实删除（有界 B）

同数量/质量对照均执行孤立内存 clone opacity=0 后 native 重渲染。target ring2/ring4、outside4=|SDF|>4、exterior4=SDF<−4、interior4=SDF>4 在选分与删除前固定。边 profile 用 −8..8px 原生 RGB：±4px contrast、梯度质量中心 location 与标准差 width。出现空洞意味着 alpha 损失，不视作好线或唯一几何因果责任。

|视角/方法|n|Σ full mass|ring4 RGB MSE|outside4 RGB MSE|alpha 前景损失像素|contrast Δ|location Δpx|width Δpx|
|---|---:|---:|---:|---:|---:|---:|---:|---:|
|lego_r_1/gaer_ratio|1553|2015.26|0.00069099|7.33203e-08|57|-0.00319|0.04015|0.01671|
|lego_r_1/gaer_raw|1553|4944.90|0.00249952|3.80018e-06|259|-0.003186|0.1376|0.05279|
|lego_r_1/alphaT_participation|1553|3903.27|0.0112206|1.17483e-06|1431|0.00442|0.3788|-0.0756|
|lego_r_1/visibility_matched_random|1553|2013.14|2.63498e-05|5.7026e-06|13|-1.967e-05|0.004497|0.003181|
|lego_r_14/gaer_ratio|1553|2399.25|0.000725124|1.52923e-07|94|0.0002973|0.02376|0.0017|
|lego_r_14/gaer_raw|1553|4319.07|0.00109573|1.67471e-06|156|0.002253|0.06096|0.005535|
|lego_r_14/alphaT_participation|1553|3724.66|0.00526068|4.9149e-07|1204|0.001276|0.2616|-0.116|
|lego_r_14/visibility_matched_random|1553|2401.81|2.60113e-05|8.13222e-06|20|0.000223|0.006051|0.0007692|
|lego_r_7/gaer_ratio|1553|1988.86|0.000150777|2.84322e-07|41|0.003043|0.04225|0.0111|
|lego_r_7/gaer_raw|1553|4116.99|0.00175583|1.00889e-06|257|0.005191|0.1952|0.02669|
|lego_r_7/alphaT_participation|1553|2970.50|0.00449598|7.25552e-08|676|0.0005902|0.3222|-0.07699|
|lego_r_7/visibility_matched_random|1553|1987.85|1.31422e-05|6.58933e-06|5|0.0004095|0.006705|0.004789|
|lego_r_33/gaer_ratio|1553|2113.13|0.000682177|1.71024e-07|97|0.0009871|0.0428|0.005283|
|lego_r_33/gaer_raw|1553|4837.39|0.00149491|6.7319e-06|234|0.005942|0.108|0.02985|
|lego_r_33/alphaT_participation|1553|3370.94|0.00364631|9.97132e-07|1166|-0.0009309|0.2301|-0.08579|
|lego_r_33/visibility_matched_random|1553|2114.13|1.33772e-05|8.66027e-06|26|0.0004309|0.007081|0.0008597|
|chair_r_1/gaer_ratio|1284|1496.09|0.00134024|8.23231e-07|25|0.00388|0.0006588|-0.03872|
|chair_r_1/gaer_raw|1284|3134.90|0.00182347|2.52597e-06|255|0.008486|0.01665|-0.07847|
|chair_r_1/alphaT_participation|1284|2582.54|0.00203127|3.04602e-07|693|0.002298|0.05792|-0.08481|
|chair_r_1/visibility_matched_random|1284|1501.48|3.7035e-05|2.73771e-05|9|0.0007448|0.002767|-0.007437|
|chair_r_14/gaer_ratio|1284|1927.10|0.000709494|2.91798e-07|83|-0.0009469|0.002906|-0.006566|
|chair_r_14/gaer_raw|1284|7324.44|0.00185582|1.25172e-05|1069|0.01484|0.03236|-0.008927|
|chair_r_14/alphaT_participation|1284|6235.38|0.0021954|8.76574e-06|1806|0.005995|0.1197|-0.05691|
|chair_r_14/visibility_matched_random|1284|1931.24|2.6247e-05|2.58584e-05|15|0.0004743|0.007398|0.002104|
|chair_r_7/gaer_ratio|1284|2249.14|0.00108529|3.57799e-07|66|0.002612|0.0234|-0.02495|
|chair_r_7/gaer_raw|1284|4966.27|0.00146002|3.90823e-06|552|0.01198|0.1066|-0.007734|
|chair_r_7/alphaT_participation|1284|4032.06|0.00196484|1.37605e-06|1061|0.009438|0.1992|-0.09412|
|chair_r_7/visibility_matched_random|1284|2247.63|9.94579e-05|1.45923e-05|26|0.0004916|0.01813|0.007|
|chair_r_33/gaer_ratio|1284|2236.75|0.00105601|6.65352e-07|79|0.003262|0.007136|-0.01977|
|chair_r_33/gaer_raw|1284|5186.82|0.00140124|4.38553e-06|566|0.01657|0.09258|-0.006634|
|chair_r_33/alphaT_participation|1284|4276.63|0.00207147|2.07476e-06|1207|0.01149|0.212|-0.08949|
|chair_r_33/visibility_matched_random|1284|2241.54|8.08419e-05|1.76208e-05|25|-0.0001304|0.01164|-0.001706|

这些实测支持“边参与”的比较，不能只因删除损伤边就宣布唯一几何责任。完整 alpha 变化、位置/宽度 before/after 与区域维度在 per-view JSON。较小 opacity± 诊断 NOT_RUN。

## K / 端点与性能

|视角|K16 / K32 相对 K8 Jaccard|δ1 / δ4 相对 δ2 Jaccard|native stock / K8 / K16 / K32 median ms|CPU 三个 δ 比较 ms|全 unit 秒|
|---|---|---|---|---:|---:|
|lego_r_1|0.7718 / 0.7113|0.1555 / 0.0940|2.636 / 3.857 / 5.711 / 21.623|1262.6|10.10|
|lego_r_14|0.7678 / 0.6926|0.1254 / 0.0956|2.812 / 3.817 / 5.580 / 24.281|1195.1|9.21|
|lego_r_7|0.7323 / 0.6645|0.1946 / 0.0864|2.775 / 4.016 / 5.639 / 21.131|1113.1|8.42|
|lego_r_33|0.7275 / 0.6373|0.1620 / 0.0725|2.795 / 3.696 / 5.292 / 23.515|1539.9|9.67|
|chair_r_1|0.8059 / 0.7541|0.1662 / 0.0577|2.075 / 3.273 / 4.602 / 18.330|918.4|7.47|
|chair_r_14|0.7933 / 0.7434|0.0900 / 0.0346|2.056 / 3.147 / 5.356 / 17.357|1277.6|8.71|
|chair_r_7|0.8085 / 0.7674|0.2293 / 0.1604|1.893 / 2.610 / 4.069 / 17.032|753.2|6.87|
|chair_r_33|0.8008 / 0.7637|0.2275 / 0.1840|1.937 / 2.865 / 4.387 / 16.560|783.1|6.89|

CUDA 完整 forward 为 3 warmup + 5 event/wall samples，包含 renderer 内部 host 调度空档，未声称单 compositor kernel 的时间。CPU copy、full-visibility backward、sparse comparison 与端到端单位时间分开记录。medium 512 边像素 batches，没有 H×W×N。GPU0 PID-only ownership checks/CPU2/root4GiB/Git1.5GiB/stage8GiB 见 ignored logs。

## 可直接查看的输出

- [Lego 四视角：仅选中核原色](figures/lego_fourview_selected_only.jpg)
- [Chair 四视角：仅选中核原色](figures/chair_fourview_selected_only.jpg)
- [Lego 同相机 full RGB 对照](figures/lego_fourview_full_RGB_vs_selected_only.jpg)
- [Chair 同相机 full RGB 对照](figures/chair_fourview_full_RGB_vs_selected_only.jpg)
- 每视角 downloads/*_scores_ids.npz 含 scene/camera、original_ids、每核 raw/ratio/full_visible_mass、全部预算/方法/K IDs；不含模型副本。
- figures/*_evidence.jpg、*_crops.jpg、*_deletion.jpg、*_score_hist.jpg 与逐视角 800×800 selected-only JPG。MEDIA_MANIFEST.json 记录全部 SHA/尺寸/语义。

## 决策与来源

primary visual GO=HUMAN_PENDING。自动可靠性拒绝与预算图都保留。criteria1 的一般几何条件未验证，criteria3 的 footprint 地域成本实测而不是中心点推断，criteria4 为有界真实删除对照而不是同一权重差值自评。本阶段停止选核/诊断，不进行艺术黑墨、协方差弯曲、训练、完整轨迹或 C/D。

各视角独立计算 S_i(camera)，没有冻结 union mask。不同集合及 ID overlap 只能说明视角选核变化，不证明多视图/时序一致性；所有视角均为以前 GS/实验可见的探索视角，没有 formal blind。

最近先例为 Hao / Mukai 的作者 SIGGRAPH Asia 2026 预印本 [Feature Line Rendering from Rasterization States in 3D Gaussian Splatting](https://mukai-lab.org/content/SA2026PosterHao.pdf)。它保留 top-K 原语 ID 与 alpha*T，并比较相邻 raster states；Eq.3 的 overlap 思路与 attribution/support 比较重合，本阶段不作新颖性声明。作者 PDF 的 DOI/ISBN 为占位符，此处按预印本引用。原始 GAER 指令保存在旧阶段，授权仅对新阶段选核/诊断解除 section25 停止。

完整视角 trace=8/8；缺失=[]。测试与独立进程真实重渲染证据见 results/VERIFICATION.json、results/REPRODUCTION.json；资源/输入 hash 见 PREREGISTRATION.json、PROTECTED_AFTER.json。

## 完成后的核对与明确负结果

8 个契约测试 GREEN，独立进程 8/8 实际 native 重渲染验证通过。四种方法共 32 张主 selected-only 原色 JPG 又逐字节重建通过，见 `results/EXTRA_VALIDATION.json`。连续 Gaussian ratio-score 的 full-native-T feature projection 已输出 `figures/*_ratio_score_projection.jpg`；它是数值可视化，不改变选核或艺术重着色。该 projection 的独立 CPU-ray 真值最大误差 3.8506482e-08。附加代码/配置/产物在 `EXTRA_VALIDATION_FREEZE.json` 与 `seals/EXTRA_VALIDATION.json` 封存。

所有 8 视角都同时触发 NO_ABOVE_INDEPENDENT_NULL_FLOOR、TOPK_L1_AMBIGUITY_TOO_LARGE、HELDOUT_DELTA_UNSTABLE；自动接受数均为 0。heldout δ2/δ4 Jaccard 范围 0.0346–0.1840。随机对照的完整可见质量相对误差范围 0.000472–0.003604。alphaT participation 删除的轮廓 MSE 在全部视角都高于 ratio 组，且完整质量也更高，不能据此声称 GAER ratio 是更强的唯一边责任选择。

K16/K32 sensitivity 保持 K8 主 eligible 域与同数量，用于已有候选排名变化；不会借更高 K 的新增核重新调主阈值。完整质量匹配只对随机组相对于 ratio 组，raw/participation 为同 count、mass 不相等的对照。

先例 Eq.3 用归一化 top-K、union-of-IDs 上的 1−Σ min(p_i,q_i) 支持 overlap；严格单位质量分布时它等于 L1/2。本实现保留原始 alpha*T 总质量并报告截断界，不将 eps 归一化后的关系冒充严格等式；归因机制重合，不作新颖性声明。

本文“不分配 H×W×N”指完整 Lego/Chair pipeline；独立 CPU 真值夹具仅 9×9×12，用于穷举 accepted rays，不是实际场景 dense fallback。

[八个可下载的 per-view NPZ 与计数](DOWNLOADS.md)。人类 visual GO 仍 PENDING；当前自动可靠性结论是拒绝，展示图保持诊断身份。
