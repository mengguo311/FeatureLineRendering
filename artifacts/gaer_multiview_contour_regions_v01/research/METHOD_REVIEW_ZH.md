# 实验前独立方法审阅

审阅范围：本 stage `protocol.py / fusion.py / regions.py / pipeline.py`，并检查 `freeze.py / contracts.py / runtime.py / run.py / metrics.py` 的调用链。只读静态审阅；没有运行真实提取，没有改代码，没有查看 reserved 新图。现有四个 r_7/r_33 CPU/native-cache 校准记录已经存在；本审阅不重新认证其数值。下述问题针对文末 SHA256 快照，随后主实现若修改，应按新快照复核。

**结论：当前主数据流符合“多视角原核支撑 → 一次物空间区域 → 固定 mesh 投影”，没有发现 reserved 泄漏或独立二维轮廓升维。最需修正的是断点续跑与校准的代码版本绑定；部分来源统计和方法命名需要准确限定。视觉是否成功仍须等两场景真实结果。**

## 可能使执行链失去可复现性的缺口

1. **当前代码改变后，旧产物仍可被 resume 接受。** `runtime.py:38–43` 只验证 seal 内产物与 INPUT/PROTOCOL 的文件 hash；`pipeline.seal()` 把方法 hash 写入结果，但 `resume()` 不把它与当前代码比较。`protocol.freeze()` 若已有文件也直接返回。后续修 bug、改变 region 参数或计算规则时，旧产物可能被跳过，而新阶段使用新代码，形成混合算法。建议 freeze 后验证当前方法 manifest；每个 seal 包含/核对真正依赖的代码与输入。仅“结果 JSON 内存有 hash”不等于已验证它。

2. **校准 PASS 尚未绑定当前 renderer 实现。** `run.py:6–9` 只读四个校准 JSON 的 `status`；审阅时这些记录有输入 hash，但没有由 gate 检验当前 `cpu_native.py` / 内嵌 CPP 的 hash。若 CPU renderer 在校准后变化，旧 PASS 可被复用。应绑定源代码/编译产物或等价实现指纹。现有结果并未因此被宣布失效；问题是缺少防止后续失效的检查。

3. **单独从中间阶段恢复时，没有逐项核验上游 seal。** `fusion_arm()` 直接加载 source NPZ，`build_arm()` 直接加载 fusion NPZ，`seal_scene()` 直接加载 develop JSON。默认 `all` 按顺序运行时，上游自身的 resume 会检查；但 `run.py fuse/develop/seal` 从中间启动不保证这一点。必须核验依赖 seals/输入 hashes，才能兑现“只跳过 hash 通过产物”的端到端来源链。

以上是执行契约风险，应在主协议 seal/长运行前处理。没有用这些风险替代科学 NO_GO。

## 来源与方法必须精确说明的事项

- **多尺度提取尚不等于多尺度融合。** `evidence()` 生成 1.5px、3px 两层和 hole map；`fusion_arm()` 实际只读取 `rim_wide` 进入分数与选核。可准确称“双尺度证据保存、3px 主选核”，不能宣称两尺度共同稳定选核。
- **fusion 候选与最终 region 支撑 ID 不同。** `regions.py:13` 额外保留 `score>.100001`；但 `write_support()` 和评估 full-T footprint 使用未经过该 level 过滤的 `selected_ids`。部分 weak hysteresis ID 因而只存在于候选图而不在区域。应单列 candidate count、region support count、被 level 排除 ID；展示列明确是候选 footprint，或按最终 support IDs 渲染，不能让额外核的贡献背书资产覆盖。
- **`width_world_floor` 不是最终半径下限。** `width*spacing` 先作为 covariance 方差膨胀，再乘 `sqrt(2 log(score/.1))`，最后被 `.025*diag` 截顶和 `.55*spacing` 托底。实际厚度需从导出 axes/几何与图像测量报告。原 orientation 保留，但原尺度已放大、加宽、裁剪，不能称原 footprint 完全不变。
- **顶点最近中心并不必然是产生该区域的核。** `vertex_anchor_ids` 来自欧氏最近中心，可能落在另一较远大椭球的真实支撑内。因此 nearest-center displacement/Mahalanobis 只是诊断，不是 occupancy 因果 witness。局部 fill 的 owner CSR 更接近实际见证；owner 又只保存局部竞争的一个胜者，不能叫所有重叠原核的完整支持集合。
- **merge 表是候选/影响关系，不是最终 surviving 拓扑。** overlap/fill pairs 在 foreground veto 前已有记录；其中一些连接后来被裁掉。代码结果已说明这一点，最终报告及图不能把全部 `merge_ids` 当最终连通边。若要审计每个最终连通组件，应另对应 post-carve occupancy。

## 对照归因与不可据此夸大的结论

two-source 与 multi24 使用同一规则和同一 DEV 选择的 voxel width multiplier；但各臂从各自所选点 bbox 定义 spacing，各自执行 2/24 源的 foreground veto。它们同时改变了观测覆盖、物空间离散尺度及 carving 约束，**不是严格的“只有选核视角数量改变”消融**。可以作为实际 two-source→multi-source pipeline 对照；世界宽度与 grid spacing 须分别报告。若要独立归因 representation，需要共享网格/物尺度以及固定 carving 域的另一个控制，此轮预算不足时明确未做即可。

旧 A 图 thin 和 widened 保留相同中心、边对及固定世界 tube 半径；`tube_mesh` 默认八边截面。widened 半径只在 DEV 匹配平均 ink，未使用 reserved。其搜索上限可能使 ink 无法完全匹配；代码保存 residual，报告应如实说明。没有发现屏幕后处理加粗、动态像素宽度或按 heldout 图调位。

本法 max-over-views 分数是多源候选的软 union，不是每个核都得到多视角独立支持。`distinct_views` 按不同 camera 的 weak threshold 计数，不重复算像素票，且允许单源强核，这对 rolling rim 合理；但不能把 single-source 区域称共识。绝对 mass floor 与饱和因子可抑制极小质量的 ratio，但 `.1/.01/.05` 是冻结启发式阈值，并非经过独立物理真值认证。32px 前景连通分量过滤可能去掉细碎部件；完整性适用于这个自动证据域。

## 已检查符合约定的部分

- 输入确实遍历 metadata 的 86 frames，以 `Path(file_path).stem` 建字典；r 数字未被当 index。r_1/r_14 强制 reserved；24/4/8 划分仅使用相机方向，roles 无交集。camera matrices 与旧四视角记录逐项比较。
- `extract_view()` 经 construction gate；`dev_scene()` 只取 DEV。`build_arm()` 的所有图像约束来自各臂 construction sources。`eval_scene()` 先核验 asset seal，才读 reserved；33arc 同样先取固定 asset。
- 几何只由原 ID 的 μ/Σ 支撑、软分数、固定三维体素 closing 和 construction foreground veto 构成。没有逐相机复制线、二维路径排序/回投影新中心；α 前景只在离线对象空间约束中使用，符合用户授权，但应称有限 silhouette feasibility carving，不能隐去它对最终形状的作用。
- DEV 从事前三个 width 档位选择并一次 seal；eval/arc 只载同一个 mesh。媒体调用真实 triangle rasterizer，而不是 2px 中心线。
- 全程只 self-zbuffer，没有给 `render_mesh` 传原对象 occluder depth，也没有按评价视角隐藏 mask。故明确属于相对原 GS 物体的 **x-ray**：后方区域会投到前表面，不能声称物体遮挡正确。
- runner 按阶段遍历两个场景并捕获单场景失败，不因 Lego 单个 eval 异常直接跳过 Chair；错误标 `INVALID_EXECUTION_NOT_SCIENTIFIC_NO_GO`，没有把 exit0 当视觉 GO。

最终必须报告：camera 覆盖域，单源/多源支撑，最终世界 axes 与墨量，孔洞及开放负空间误填，后方杂线，未实现独立物体遮挡与内部纹理层。若多源 union 接近整个物体外壳，只能判断为宽区域草模/部分完成，不能称完整轮廓模型成功。

## 审阅代码快照

|文件|SHA256|
|---|---|
|protocol.py|60a68918061ccec34cecb4df5d90a08647332c65f915f5a5a699740fa56ee017|
|fusion.py|23b78a3341348ae956fa211ad43c1c3bbe99abd2b4363aebc59b3a4069a08cd1|
|regions.py|ff8a2bd8f9fa806f9705da51d163583cafdea3624ddf013968aea7cb8816118d|
|pipeline.py|a3c21e997f4fb456ca5081d301e254dc51e41d95b6de8755bc14c851f0870da8|
|freeze.py|6ab0e1662f0124a02680b6760646b42099ef97f1f7892e5d5065ca1b398513a9|
|runtime.py|7e03c6191f258ea93546df338480d36a4e0185559ffb26e0289ac095447657ff|
|run.py|727512bd8e62cdec2efb888716dee08efddf2af4169feec56111eb32587f6d85|
