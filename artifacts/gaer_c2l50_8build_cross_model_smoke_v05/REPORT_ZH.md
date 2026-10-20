# 3DGS 原核跨模型参数 / PartField 冒烟：chair、lego、drums

结论：这次**真正运行了**除 Ficus 以外的三个冻结 3DGS 模型。9 个高斯参数臂与 PartField 特征均能在所有原始 PLY 行生成 K=3 标签；CPU 原核关簇重渲染也已完成。**但三部件分别编辑尚未验证成功**，且这组三模型的前景 native 校准不及 Ficus，跨方法视觉图只能作为诊断，不能据此声称 native 编辑排名。

## 冻结资产与方法

- chair：seed_1729 iteration_30000；256,690 原核；PLY SHA256 `13e4ecc9ffe9c5ae2a0656e2e5c56a737cfdc90a62ad04799db3c46b0b442f5d`。
- lego：310,475 原核；SHA256 `fa9bea3fa4f8d349fa873a66d892c53cd1263499caec6421c286350a5bb7cbbc`。
- drums：360,012 原核；SHA256 `d4b67123927613ade6b7e2f38ed6bf724fc5e348dbcca84a2be1352ec5113a8b`。
- 每个 `labels[i]` 仅对应**不变的原 PLY 第 i 行**；PLY 无显式 source_index 字段。投影只用各场景原训练相机 `train_r_79`、`train_r_7`；所有原核在两 FIT 相机下几何有效，故 UNKNOWN=0 **仅是此 K=3 强制归属算法的性质**。`test_r_14`、`test_r_79` 的参考像素只用于聚类完成后的渲染校准／观察，并非新盲测相机。相机 OpenGL→CV 变换与 Ficus 固定 registry 的 train_r_80 数值吻合（单测）。
- 参数九臂与 Ficus v04 一致：A 世界最长轴；B 距离加权主轴；C 投影协方差主轴；D SH0 RGB；E/F 两 FIT 完整 SH RGB 串接／均值；G XYZ；H 三尺度＋opacity；I XYZ＋完整 SH＋投影轴等权块融合。统一 `KMeans(k=3,n_init=3,max_iter=100,seed=0)`，再用 seed=1 诊断初始化。完整逐臂 counts／ARI／SHA 在各场景 `SUMMARY.json`，不跨特征维度比较 inertia。
- PartField 使用**同一公开预训练权重**，从各模型固定随机抽取 8,192 个原核中心供编码，查询全部原核中心的 448 维特征，原行 K=3；这不是官方全点云推理，也不是同训练成本参数基线。仅 `xyz` 输入 PartField，未在这些场景训练语义标签。
- `best_axis_null` 为与**已观察的 PartField 某簇等数量**的世界 X/Y/Z 高／低端单阈值中 Jaccard 最大者。这是**事后 oracle 空对照**；Jaccard 衡量原核掩码重合，非语义真值。为避免把弱簇藏掉，图中展示全部三个 PartField 簇；参数对比图另外显示与预选 PartField 簇原行 IoU 最大的 G 和 I 簇（不同大小）。预选规则为 PartField 三簇中单轴 null Jaccard 最低者，选择发生在首次读取 reserved 图像前。三个视角原始核复制并仅将掩码内 opacity 置 0 后，用相同 CPU EWA／完整 SH／透射重新渲染。

## 实际结果

- **chair**：PartField counts `[51,766, 78,514, 126,410]`。预选簇 1（78,514 核）与最佳同数量世界 Z 低端切的 Jaccard **0.240**；在 `test_r_79` 关后，椅背软垫主要消失，座垫／扶手大致仍在；同数量高度空对照主要切掉座垫和下部。XYZ K3 与融合 K3 的相应簇关后呈横向破坏或几乎不动，不是同一种边界。**但**椅背上缘/框架有残留和混合，不能称独立精确编辑。参数 I 第二种子 ARI 0.991，非语义正确率。
- **lego**：PartField counts `[104,376, 115,177, 90,922]`。预选簇 0 与最佳同数量世界 Y 高端切 Jaccard **0.513**；`test_r_79` 关后车体／履带与部分底座消失，吊臂与部分底板仍可见；高度／Y 空对照保留相当车体、破坏部分底板；XYZ 簇则主要去掉吊臂。可看到部件层级信号，但车体和底板被混选，不能说“分离了铲斗/底盘/吊臂”。参数 I ARI 0.988；**D SH0 RGB 两种子 ARI 仅 0.301**，尤其不能以它的三簇作稳定颜色分类。
- **drums**：PartField counts `[175,742, 99,944, 84,326]`。预选簇 0 与最佳同数量 Y 低端切 Jaccard **0.411**；`test_r_79` 关后中央鼓、支架大幅减少，左右镲/部分鼓仍在；XYZ／融合簇关后造成破碎、残影更明显。PartField 其余簇关后可分别影响左右器件，但同时混入鼓/架子，尚不是完整物理件。参数 I ARI 0.998。
- 相比 Ficus 的 PartField 盆簇几乎与低 Z 截断重合（Jaccard 0.99957），这三景的预选簇**不等同于任一单轴等数量切分**，且部分关簇图视觉上更接近结构化部件。但这是非常弱的正面证据：没有控制旋转坐标系、组合轴/空间分类器/多阈值空间基线；不代表编码器提供超出全部廉价几何的增益。预选“最不轴向”的簇本身也会使这些数值低于随机挑选簇。

## 渲染校准与科学门槛

用 frozen 原核 CPU EWA 未编辑图对历史 native 渲染 `rgb_1`（400×400）计算整图 RGB MAE／对象 ROI RGB MAE：

- chair：FIT `train_r_79` **0.0061 / 0.0339**；reserved `test_r_14` **0.0109 / 0.0412**；弱 reserved `test_r_79` **0.0131 / 0.0453**。
- lego：**0.0131 / 0.0340**、**0.0137 / 0.0334**、**0.0131 / 0.0348**。
- drums：**0.0128 / 0.0263**、**0.0152 / 0.0484**、**0.0106 / 0.0259**。

若沿用 Ficus v04 的整图 RGB≤0.015、前景 RGB≤0.03 门限，**每个场景至少有一幅失败**；drums 的 `test_r_14` 连整图门也略超。这里没有 native 逐核 alpha*T 对照／ROI alpha 校准，不能把 CPU 画面等同 GPU native 的精确编辑效果。也没有改变颜色/软归属/UNKNOWN/人工三部件原核真值、独立持出模型上的预注册成功率。颜色标签数和高 ARI 只是分簇稳定性，不是语义验证。

## 文件与复核

- `transfer.py`、`compare.py`、`test_transfer.py`：CPU≤2、禁 CUDA；4 个新单测通过；v04 的 14 个原测试未在这组三模型上重新定义真值。所有九臂和 PartField 标签文件、counts、SHA 与三视角对比 PNG 已重新逐个读回验证。
- 原始特征和每臂 `.npy` 在 HDD `.../c2l50_8build_cross_model_smoke_v05/{chair,lego,drums}/`。本报告同目录的每场景 `SUMMARY.json`、`PARAMETER_COMPARISON.json`、`*_original_vs_off.png`（三簇全对照）、`*_parameter_comparison.png`（选中簇与 XYZ/融合对照）是压缩后的可复核产物。图题/图例用英文。
- `source_index` 没有被重训、重排、拆分或删核改变；源资产与 v03/v04 worktree 只读。新实验隔离在 `gaer-c2l50-8build-cross-model-smoke-v05`，无 GPU 占用／无 push／无 merge。
- 本轮**没有获得事前 Astra ultra 审查**。事后尝试独立审阅时，当前远端会话的 `codex` 命令不可用（exit 127）；故不能把结果表述为经 Astra 放行。四项新单测、旧 Ficus 相机一致性检查和产物哈希读回不替代科学审查。
