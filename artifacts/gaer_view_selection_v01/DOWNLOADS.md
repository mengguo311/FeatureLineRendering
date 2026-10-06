# 每视角分数与原始 IDs 下载

主展示是预注册 0.5% 诊断预算；所有视角 automatic=REFUSED，accepted automatic IDs 为空。NPZ 包含每个原始 Gaussian 的 score/raw/full_visible_mass，original_ids，以及四方法×三档预算和 K16/K32 的原始模型行 IDs。未存储任何修改模型。

|scene/camera|主诊断核数|完整归档|
|---|---:|---|
|lego_r_1|1553|[lego_r_1_scores_ids.npz](downloads/lego_r_1_scores_ids.npz)|
|lego_r_14|1553|[lego_r_14_scores_ids.npz](downloads/lego_r_14_scores_ids.npz)|
|lego_r_7|1553|[lego_r_7_scores_ids.npz](downloads/lego_r_7_scores_ids.npz)|
|lego_r_33|1553|[lego_r_33_scores_ids.npz](downloads/lego_r_33_scores_ids.npz)|
|chair_r_1|1284|[chair_r_1_scores_ids.npz](downloads/chair_r_1_scores_ids.npz)|
|chair_r_14|1284|[chair_r_14_scores_ids.npz](downloads/chair_r_14_scores_ids.npz)|
|chair_r_7|1284|[chair_r_7_scores_ids.npz](downloads/chair_r_7_scores_ids.npz)|
|chair_r_33|1284|[chair_r_33_scores_ids.npz](downloads/chair_r_33_scores_ids.npz)|

原始 float64 分数与 native top-K/endpoint/bounds 位于 ignored out/units；NPZ 使用 float32 score/raw 紧凑导出。每个 scene/camera 的 selected IDs 独立计算，没有 union 固定集合。
