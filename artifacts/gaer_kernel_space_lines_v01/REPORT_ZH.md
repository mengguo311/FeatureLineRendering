# GAER 原边缘核 → 纯物空间邻接连线：实际交付

已将 Lego、Chair 的固定原核候选集直接连接成显式三维线段，交付两臂固定 GLB、三角 tube OBJ 与带 `l` 记录的 centerline OBJ。所有中心线端点逐项等于原 PLY 对应行 XYZ，没有二维轮廓排序、回投影布点、深度代理、图像 DT pull、平滑移动或逐帧重选。工程契约通过；科学 verdict 为 **NO_GO_FRAGMENTED / PHYSICAL_EDGES_UNCERTIFIED**。资产只称 **kernel-space candidate graph**。

本次不是上一轮单视角 alpha 升维资产的改名。唯一复用是已测试的 `tube_mesh` 与 `glb_bytes` 数值函数；读取 AST 后只执行这两个定义，没有导入旧 runtime 或 run.py。来源和函数 hash 在 [REUSE_PROVENANCE.json](REUSE_PROVENANCE.json)。所有新点、邻接、边对和管几何均由本次原 ID 输入实际生成。

## 输入与预注册

源交付 commit `e682614a7fedcb529102f67efcf78f7905d3d519`。各场景只将 r_7/r_33 的 `gaer_ratio_0.005_ids` 排序去重一次：Lego 每视角 1553，交集 49，并集 3057；Chair 每视角 1284，交集 615，并集 1953。完整原 NPZ 字节副本在 [sources](sources/)，每 ID 的来源视角见 `inputs/<scene>/SELECTED_ORIGINAL_IDS.json`。原模型 Lego 310475 行，Chair 256690 行，模型路径、确切 SHA256、源 IDs、相机与保护 hash 见 [INPUT_FREEZE.json](INPUT_FREEZE.json)。

四个主输入 NPZ 的 `automatic_accepted_ids` 均为空。旧八视角自动状态 **REFUSED** 保留，未把预算候选宣传为自动认证选核成功。此次连线来自用户的明确授权；没有用全 N 的 C-arm 强度代替边缘核。r_1/r_14 不参与构图，仅后验检查；全部四视角与既定弧线相机此前均被 GS/研究曝光，非真正 blind 或 GS-unseen。

查看真实图之前冻结 [PROTOCOL_ZH.md](PROTOCOL_ZH.md)、[PROTOCOL.json](PROTOCOL.json)，并在构图开始前记录 [ALGORITHM_FREEZE.json](ALGORITHM_FREEZE.json)。两场景参数完全共用：k=12；A 每点最近两个邻居的无向并集；两臂都要求非零长度、d<=3×min(两端原核局部非零最近邻尺度)。B 的 PCA 使用自身加 12 邻居，线性度>=0.45，双端 |t·segment|>=cos45°，互为 kNN；每端每半轴选择最短合格边，最终双端互选，度<=2。等距按原 ID。PCA 是点分布无向轴，不是表面法线；未使用原 covariance。没有 MST、长距离补桥或结果后调参。

## 两场景实际结果

|场景 / 臂|原核中心|线段|孤立点|组件（含孤立）|最大组件点数|最大度|长度中位 / p95（世界单位）|
|---|---:|---:|---:|---:|---:|---:|---:|
|Lego A|3057|3240|99|666|27|6|0.005177 / 0.014205|
|Lego B|3057|1154|1317|1903|17|2|0.005703 / 0.016641|
|Chair A|1953|2166|62|350|39|6|0.005978 / 0.017969|
|Chair B|1953|753|814|1200|9|2|0.007405 / 0.022187|

Lego 21772、Chair 13869 条候选邻接全部保留，包括最终拒绝项。PCA 线性度通过点数分别为 2729、1687；数量不构成质量认证。详尽 degree / length / component 分布、孤立原 IDs、各拒绝 bitmask 和双端 rank / alignment / distance 在 [RESULTS.json](RESULTS.json)、`assets/<scene>/FULL_GRAPH.npz`、`CANDIDATE_ADJACENCY.json` 与各臂 `GRAPH_STATS.json`。拒绝计数可重叠，不能相加当互斥分类。

两臂每场景共用由 selected XYZ 自动确定的一个永久世界 tube 半径：Lego `0.0005002839309215583`，Chair `0.0005812996594434317`，即 0.12×median(非零最近邻尺度)。GLB 是封盖八边截面三角管线；原世界坐标 Z-up，节点无动画和变换。tube 环顶点用于厚度表现，中心线端点仍是原核中心；导出后半径、点和边固定，不随相机变化。

## 可直接查看的文件

- [真三维交互查看器：原核 / A / B / PCA](media/viewer_3d.html)，无需联网，拖动旋转、滚轮缩放；PCA 方向可单独打开。
- [Lego 真三维图与 PCA](media/lego/true_3d_graph_PCA.png)、[Chair 真三维图与 PCA](media/chair/true_3d_graph_PCA.png)。原核和 field 同时提供二进制 PLY，`PCA-direction-glyphs.obj` 为方向展示，并非图的新节点。
- [Lego A GLB](assets/lego/A/candidate_graph.glb)、[Lego B GLB](assets/lego/B/candidate_graph.glb)、[Chair A GLB](assets/chair/A/candidate_graph.glb)、[Chair B GLB](assets/chair/B/candidate_graph.glb)。同目录有 `tube.obj`、`centerline.obj`、`EDGE_PAIRS.json/npz`。
- [Lego 四相机拼图](media/lego/four_camera_inspection_preview.png)、[Chair 四相机拼图](media/chair/four_camera_inspection_preview.png)。完整拼图和各 800×800 单列图均保留；列依次为原生 RGB、原中心、A、B、A 叠加、B 叠加。
- [Lego 33 帧 A/B 视频](media/lego/arc/A_B_fixed_graph_33.mp4)、[Chair 33 帧 A/B 视频](media/chair/arc/A_B_fixed_graph_33.mp4)。[Lego 全帧条带](media/lego/arc/ALL_33_FRAMES.png)、[Chair 全帧条带](media/chair/arc/ALL_33_FRAMES.png)，没有丢弃坏帧。每场景 `arc/FRAME_MANIFEST.json` 保存所有实际相机、背景/帧/固定 geometry hash；`ALL_CAMERA_PROJECTIONS.npz` 保留原节点和 33 个真实矩阵/投影。

四相机和视频都是同一固定图的后验投影。RGB 来自旧阶段同相机原生完整 SH3 图，按原始 800×800 像素使用，并校验旧实际相机记录；没有变形旧二维轮廓。线段显示为 **2px 中心线、x-ray、保留隐藏线**。视频 1600×850、12fps、H264/yuv420p/+faststart。此展示不是 tube 原生 mesh render，不声称画面 width 稳定或隐藏线验证；预览缩小仅是展示。图像绝不反馈边、核位置或门槛。

## 后验视觉与科学判定

Lego 的底板边界和少量上部轮廓在源视角中可辨认；r_1/r_14 下出现穿过可见部件的后方线投影，内部和上部部分仍缺失。Chair 背部外形在 r_7/r_33 中相对可辨认，但 r_1/r_14 的坐面与靠背、扶手过渡更稀疏，轮廓缺口和局部线束更突出。这是可见效果的观察，不是语义真实性标签。

A 的局部邻接出现度 3–6 的分叉、短三角/杂线和局部线团，仍有大量断裂。B 抑制分叉后保留了更少边，但约 43.1% / 41.7% 节点孤立，最大组件仅 17 / 9 点，不能称连续可用的完整轮廓。两臂换视角后都存在轮廓位置偏差、后方线穿越可见面和潜在跨面/跨部件误连；没有表面几何、语义标签与隐藏线消除，不能把这些交叉直接认证为物理跨面错误，也不能宣布错误已消除。三维距离近且 PCA 一致本身无法证明同一表面或真实棱边。

因此工程 **PASS** 与视觉科学 **NO_GO** 分开。此次证明了给定原核中心能够按冻结规则导出固定三维候选线资产；未证明固定轮廓一般可恢复、真实物理棱边/接触线已恢复、selector 已认证、多视角完整性、像素宽度或遮挡正确性，也不作新颖性声明。保留所有负结果，未用参数救图。

## 真实验证与限制

7 项投影 / 原 ID / 原 XYZ / 互选图 / 不桥接 / 空 B / GLB / tube 契约测试先 RED（7 项未实现错误），后 GREEN（7 项全部通过）。一次中间运行因精确浮点 `899.4999999999999==899.5` 断言失败，改为 1e-10 级数值容差；日志保留在 [TDD_INTERMEDIATE_FLOAT_ASSERT.log](TDD_INTERMEDIATE_FLOAT_ASSERT.log)。输入封存的 metadata hash 字段名修正也保留负日志，未改变算法。

独立进程 [VERIFICATION.json](VERIFICATION.json) 状态 PASS：原模型行、原 ID 并集及来源、GLB 独立 chunk/accessor 解析和 trimesh 读回、tube/centerline OBJ 读回、封盖管线、双端环中心与固定世界半径、B 度/距离/双端方向/互为 kNN、四相机实际 metadata 投影、33 实际相机与全帧原 geometry hash 一致。两视频完整解码均 33/33，不同 decoded frame hashes 均 33；[MEDIA_AUDIT.json](MEDIA_AUDIT.json) 证明投影前后所有资产 hash 未变。159 个保护文件前后 SHA 全部一致，包括原模型、旧 NPZ、旧报告、原生 RGB 与复用代码。

全流程 CPU 两线程，不安装、不训练、不使用 GPU、mesh 输入、额外几何或网络数据。资源日志 [RESOURCES.jsonl](RESOURCES.jsonl) 每阶段执行 root>=4GiB / sharedGit>=1.5GiB / stage<=2GiB 守卫，未修改生产 1GiB 守卫。没有 tube 原生渲染或表面遮挡验证，没有人工物理边标签；这是明确限制，不是资产/33 帧缺失。

复现命令与来源见 [REPRODUCE.md](REPRODUCE.md)。[MANIFEST.json](MANIFEST.json) 保存冻结交付文件 hash。最终 commit / 显式 SSH push / remote SHA / clean status 在本地 `DELIVERY.json`；它是 push 后生成的 receipt，按本 stage `.gitignore` 忽略，避免文件包含自身 commit hash 的循环。全部模型/图/媒体/测试/中文文档在同一最终交付 commit 中。
