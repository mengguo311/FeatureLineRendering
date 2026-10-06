# 历史证据与可复用接口审计

审计范围：四个历史 REPORT、中心图 PROTOCOL、两场景 FULL_GRAPH 全候选拒绝位、原始选核 NPZ、原 PLY 的 XYZ/scale、PCA 图、完整四相机图，以及原生伴随/相机/导出实现。只读旧树；本审计没有调用 GPU，没有改变旧科学状态。逐来源 SHA256 见 SOURCE_HASHES.json；历史数值的实际读取与重新计算见 HISTORICAL_NUMERIC_AUDIT.json。

## 结论与失败层次

**旧中心图 NO_GO_FRAGMENTED 不能推出没有可用轮廓支撑核。** 它同时施加了两视角、每视角 0.5% ratio 硬预算、仅核中心、局部最近邻、严格距离门与 B 臂 degree≤2。真实原生共同支持比这个输入域大得多；本轮必须分别检验额外观测、软支撑保留和空间区域表示，不能只改变 k 或 PCA 角度。

1. **原始证据并不等于旧预算集合。** 直接读取历史 r_7/r_33 scores_ids.npz，Lego 两视角 raw>0 并集 18,401，完整原生轮廓参与>0 并集 36,304；Chair 对应 7,406 / 12,006。旧 ratio 0.5% 并集仅 3,057 / 1,953。>0 含弱尾，不能全部视为可靠实体边；完整参与是旧一像素 alpha 轮廓的支持，和 object_contours 的较宽 beta 域也不是同一个集合。
2. **ratio 硬预算丢失大量共同质量。** Lego r_7/r_33 的旧 ratio 集合分别只包含该视角 full-native alphaT 轮廓质量的 6.736% / 6.360%；同数 raw 为 31.386% / 14.911%，同数 alphaT 排序为 63.730% / 50.782%。Chair ratio 为 10.828% / 10.654%，raw 为 29.697% / 30.390%，alphaT 为 60.840% / 64.568%。这些是冻结完整 T 下的质量份额，**不是阈值轮廓覆盖，更不是删除核重渲染质量**。
3. **跨视角互补与重复不同。** Lego ratio 两源交集只有 49，Chair 为 615；完整参与>0 交集却分别为 5,940 / 7,009。Lego r_7 俯视主要描到底板，r_33 才提供挖斗与上方部件外形；Chair r_7/r_33 都主要观察背侧，因此新来源必须增加方向覆盖，仅累加邻近视角票数不会恢复前侧座面/扶手/前腿。
4. **中心替代 footprint 又丢失一层连续支撑。** 两源完整参与核的最近中心距中位 Lego 0.002184、Chair 0.003189；其最大原生 sigma 中位 0.010181 / 0.008295。旧 ratio 集合最大 sigma 中位仍有 0.006023 / 0.006310，而旧 tube 半径仅 0.0005003 / 0.0005813。这不是建议无条件取最大 sigma 当半径：各向异性和深度方向会导致不当膨胀；它表明原生足迹可跨中心间隙，中心折线不保存这个能力。
5. **3D 邻接门本身造成断裂，但放松未必正确。** Lego 21,772 候选边中 16,462 被局部距离门拒绝，Chair 13,869 中 9,414。B 还受到方向/互邻/双端半轴互选限制。A 最大组件仅 27 / 39 点，B 仅 17 / 9，B 孤立 1,317 / 814；因此问题不只是最后上色或显示宽度。近距共线也不能认证同一表面/同一部件；宽区域必须保存 merge 支撑与拒绝理由。

## 真实图观察

已直接读取原尺寸 `true_3d_graph_PCA.png` 与 `four_camera_inspection_FULL.png`（两场景），而非只读摘要；也读取两场景 `fourview_full_RGB_vs_selected_only.jpg` 与 r_7 的 raw selected-only 原尺寸图。

- Lego 的旧中心/PCA 空间图已有底板框、局部驾驶室与挖斗的相对位置，并非随机散点。但 r_1/r_14 的挖斗、细支柱、轮履部分缺失；底板后边在前景车身上穿过。原 ratio selected-only footprint 比旧中心线更有长条连续性，raw 同预算还显示更宽的足迹片；这些图删除了其他核并改变 T，不能直接当完整 T 区域输出。
- Chair 两源中心空间图集中在靠背背面轮廓与后腿；换到 r_1/r_14 前侧后，座面前缘、扶手和前腿不足。B 的细化主要减少线段，未生成新的结构。原 footprint 能给出可辨完整外围形状的部分，但浅色低 opacity、宽尾与真实开口策略仍限制视觉。
- 旧图线宽恒定 2px、x-ray，保留全部隐藏线。它们不能证明 world-space tube 连续性、真实宽度或遮挡通过。没有可复用的已验证 CPU 三角形 mesh rasterizer；本轮必须新增并校准真实三角形投影。

## 旧状态必须保留

`view_selection` 八视角 automatic accepted 全空、ALL8 REFUSED：平坦共面反例证明 D 可以只是 footprint 导数；D 大不等于物理几何边责任。K8 端点未知界/L1 为约 0.24–0.52；K32 仍非完整。新 full-native 规则是新的假设，不得反写旧自动结果。

`object_contours` C 臂全 native beta 可参与核每视角 Lego 28,637–34,937、Chair 15,604–21,411；活动核约 14,920–19,073 / 8,702–12,020，近完整覆盖实际可做，但逐相机联合拟合与 S 的临时 screen covariance 都是视角依赖结果，不能作为本轮固定三维资产。旧报告填充封闭孔洞仅用于外轮廓证据，故 Chair 封闭开口不是该旧目标；本轮应独立记录孔洞与负空间损害，不能继承这个语义而不声明。

`capacity` 的完整 N / 固定 T 证明只作用于既定线域和强度目标。Lego r_000、Chair r_000/r_018/r_014 的 perview 近最优证书仍 MAX_BUDGET_UNCERTIFIED；shared 两场景有证书但在同一个已知四图池，不是泛化。其有限 shape 能力测试不能推出 shape 必要/充分，也不能从未收敛案例给全表示 NO_GO。

## 直接复用路径与陷阱

所有下列路径均为 `/home/u00134/3dgs_line/` 下的只读源；完整绝对路径及字节 hash 见 SOURCE_HASHES.json。

|对象|文件与接口|复用界限|
|---|---|---|
|旧 thin 基线|`gaer_kernel_space_lines_v01/artifacts/gaer_kernel_space_lines_v01/assets/{scene}/FULL_GRAPH.npz`|`xyz` 原 float32 行、`ids` 原ID、`A/B` 为局部 index pair、`radius` 原世界半径；A 有更多覆盖，建议预注册 A 为主 thin 控制，B 保留诊断。不要重跑调参代替原基线。|
|旧来源|`inputs/{scene}/SELECTED_ORIGINAL.npz` 和 `SELECTED_ORIGINAL_IDS.json`|`source_view_mask` 1=r_7、2=r_33、3=两者；`EDGE_PAIRS.npz`/JSON 可交叉核对。|
|原生模型加载|`gaer_attribution_buffer_v01/experiments/gaer_attribution_buffer_v01/src/scene_io.py:load_model(record)`|record 有 model/model_sha256/count；按原行构建完整 SH3，opacity sigmoid、scale exp、quat normalize；直接分配 GPU，仅 root 校准后调用。|
|相机 settings|同文件 `make_settings(module,camera)`|camera 含 w2c、FoVx/y、height/width；viewmatrix 为 w2c.T，projection 为 stock near=.01/far=100；campos=view.inverse()[3,:3]。|
|相机转换|同文件 `freeze_cameras()` 的转换公式；本轮不能直接运行其固定旧视角冻结逻辑|按实际 file_path stem 唯一匹配，Blender c2w 第1/2轴（索引1:3）乘-1，再 inverse 得 w2c。fx=W/(2tan(FoVx/2))、cx=(W-1)/2，y 同理。不能把 r 数字当 metadata index。|
|全 N 原生伴随|`gaer_attribution_capacity_v02/experiments/gaer_attribution_capacity_v02/operators.py:NativeWeights`|构造 NativeWeights(module,settings,model)；`A(x)`→H×W full-T contribution，`AT(y)`→N 原ID完整伴随；`original()` 原SH3 RGB，`ink_rgb(x)` 白背景 1-x。无 H×W×N，无 topK 截断。AT 的几何梯度被丢弃。|
|隔离加载样例|`gaer_object_contours_v01/experiments/gaer_object_contours_v01/adapter.py:read_api`|临时注入 stage-local runtime/binding，再 importlib 执行只读源，finally 恢复 sys.modules。旧 runtime 可能创建目录，不能直接 import。query_extension()/shape_extension() 校验既有 binary hash，只读加载，不构建覆盖。|
|三角管/GLB|`gaer_kernel_space_lines_v01/experiments/gaer_fixed_contour_asset_v01/core.py:tube_mesh,glb_bytes`|仅 AST 抽出这两个纯函数。旧 kernel-space core._reuse_functions() 已示范；不要执行旧 ray lift run.py 或 ray_points/supported_depth。glb_bytes 单 mesh/node，若本轮两层需扩展或独立文件。|
|GLB 独立读回|`gaer_kernel_space_lines_v01/experiments/gaer_kernel_space_lines_v01/core.py:parse_glb`|独立 chunk/accessor 解析，支持 float32 vertices/uint32 indices，原实现只取首mesh/primitive。|
|旧 viewer|同目录 `viewer_template.html`|纯离线 Canvas 原点/线/PCA交互，能做简易控制但不是三角mesh可见性验证；本轮需使用实体mesh旋转与zbuffer。|
|视频审计|同目录 `media.py:encode_and_decode`|ffmpeg H264 yuv420p +faststart、完整流式解码hash和33帧检查可参照；旧硬编码1600×850需与新媒体分辨率一致。|

## 对主空间模型的证据约束

最早应证伪的假设是：原生轮廓共同支持的固定三维局部区域能在未用于构建的相机维持形体覆盖，同时不会在内部/负空间变成大片墨面。便宜测试应先用少量 construction native full-N AT 产生带原 ID 的软支撑，在原 covariance 局部支撑内生成区域，再冻结投影到 DEV；测 coverage、ink、背景/内部及孔洞填充、组件与宽度。若只加宽旧 A 在同 DEV ink 下同样好，新增融合表示的贡献未证；若多视角只是增加黑面，额外覆盖并未换来合格轮廓。

区域能补救核中心稀疏且 footprint 实际相交的间隙；它不能凭空补没看到的结构，不能自动区分近部件，也不能把 rolling silhouette 精确压成全方向单一细曲线。应把新对象明确称 edge occupancy proxy / 轮廓支撑区域，接受固定宽近似与覆盖域限制，不声称真 SDF、表面或物理棱边。
