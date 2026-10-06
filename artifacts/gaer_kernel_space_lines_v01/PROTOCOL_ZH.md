# 原核物空间邻接连线：查看真实图之前冻结的协议

两场景共用同一参数和实现规则，仅运行一次主协议；不得因投影效果更改点、边或门槛。源 commit=e682614a7fedcb529102f67efcf78f7905d3d519；主输入是各场景 r_7/r_33 NPZ 的 gaer_ratio_0.005_ids 排序去重并集。automatic_accepted_ids 必须为空；旧 REFUSED 不变。本次是用户授权诊断候选的 kernel-space candidate graph，不是 selector 认证或真实物理边恢复。

节点是原 PLY 行的原始 float32 XYZ，逐项一致。每点记录两个来源 bit（r_7=1，r_33=2）。不使用图像、alpha、RGB、深度、额外几何或 covariance 构图。r_1/r_14 仅检查；所有相机此前 GS/研究曝光。

邻域为每点 12 个最近其他原 ID；距离相同时按原 ID 排序。候选无向边为这些有向近邻的并集。计算 float64 欧氏距离。eps=max(selected XYZ 包围盒对角线×1e-12,1e-15)；每点尺度 s_i 为与其他节点的最小大于 eps 距离。若全体重合则拒绝所有边并用包围盒 eps 作为展示半径基数，不构造假边。零距边拒绝；所有臂都要求 d<=3×min(s_i,s_j)，不做 MST 或额外桥接。

A：每点最近两个邻居（k=12 的前两名）的无向并集，应用上述距离门控；不限制最终度数。这是简单局部近邻基线。

B：PCA 使用本点和 12 个邻居，去均值经验 covariance（除以样本数），特征值降序 lambda1>=lambda2>=lambda3；最大特征值方向为无向切线，最大绝对分量置正仅便于序列化。线性度 (lambda1-lambda2)/max(lambda1,eps²)>=0.45。双端 abs(t·unit_segment)>=cos(pi/4)，且双方互为 k=12 邻居。满足这些基础条件后，每点在切线两个半轴各选最短一条 admissible 边，等距按对端原 ID；仅保留双端均选择的边。这使度<=2，不为完整性跨部件。所有候选保留完整拒绝 bitmask，包括最终未互选。PCA 是点分布方向，不是表面法线。

两臂共用每场景单一自动世界 tube 半径 r=0.12×median(s_i)。半径仅由主输入点决定，导出永久冻结，管截面 8 边、独立每条线封盖。中心线端点必须是原 XYZ；环顶点是表现厚度所需的管几何，并非新核点。B 空则输出明确空资产，保留 A 诊断，不救图。

导出 A/B GLB、tube OBJ、centerline OBJ、原核中心 PLY、原 ID edge pairs JSON/NPZ、PCA field NPZ/PLY 和三维交互查看器。只读复用上阶段 core.py 的 tube_mesh/glb_bytes 函数，记录源/hash；不导入其 run.py，不调用 ray_points/supported_depth 或旧 runtime。

后验四相机同一固定图检查：原生完整 SH3 RGB、中心、A、B、A/B RGB 叠加。33 帧各用 INPUT_FREEZE 的实际 arc 相机与对应原生 RGB；固定中心线投影宽 2px，x-ray，无隐藏线消除，不声称 tube 原生 render、画面宽度稳定或物理遮挡通过。完整保留所有帧，H264/yuv420p/+faststart，完整解码；校验 33 个 distinct camera hashes 及固定 geometry hashes。图像绝不反馈构图。

工程通过要求：严格 RED→GREEN 投影/图/GLB/ID 单测，独立 GLB 顶点/面解析，原 ID/XYZ/度/门控/端点/静态性校验，视频全解码，输入前后 hashes，stage 范围提交并显式 SSH 推送读回。科学 verdict 另行报告；无人工语义标签不宣称真实棱边/接触线，不以数量当质量，不声称一般固定轮廓可恢复或新颖性。

资源每阶段 root>=4GiB、sharedGit>=1.5GiB、整个新 stage<=2GiB；生产 1GiB 守卫不动。仅 CPU 两线程、禁 pycache、缓存/TMP 全在新 stage。不使用网络数据、不安装、不训练、不占外来 GPU；唯一授权网络操作是最后 SSH push/remote SHA 读回。
