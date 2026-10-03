# 继承源与相机规则只读审计

**继承 LOCK、科学源、隔离 native 构建及16个 primary-F 封存记录核验通过；没有运行 GPU，也没有创建新场景图像。** 本次库存无可用新 scene，因此生产停止为 `STOP_INPUT_BLOCKED`；这些校验不代表新增场景实验已执行或运行兼容性已经通过。

已读旧 `PROTOCOL.md`、`REPORT.md`、`REPRODUCE.md`、真实未跟踪 `out/hybrid_raster_evidence_v2/LOCK.json`、原始 `INPUTS.json`、native loader/runner、科学读出、封存与相关测试源码。读取路径及 SHA256 见 `READ_REFERENCES.json`；没有打开 TEST 数据、mesh 或新结果图像。审计只写当前 worktree 的本目录。

`INHERITANCE_AUDIT.json` 记录：

- 旧 LOCK 文件 SHA256 为 `d5ec038e8ebc8a7160bc9e31ebb6ac8ce755fdbf1677a32ad55102a48c6a0926`，canonical lock hash 为 `543666726d9fe38adcf85bcc8c56ace57bb0121e4598e7fb0a312302af2c3dbf`，参数 hash 为 `6c4ef4afa648f54794d7094a7b21368a89e14cdbc792766441aa3d3639d487c9`，均重算一致。
- LOCK 的六个 source 文件在旧 worktree、当前 worktree 与锁内 hash 全部一致；科学计算未改动。
- 旧 native 的 patched/unpatched 两个二进制与 BUILD 匹配；每版449个源码文件、共898个与 SOURCE_MANIFEST 全部一致。BUILD hash 为 `54acc2fe19d2665f171014c134a50c1fe286aed66dc37ee86a8ee3af132aed8c`，与 LOCK 一致。使用同一个 CPython3.9 指定解释器。实际新输入运行兼容性仍需 patched/unpatched 校准，当前未执行。

`PRIOR_F_SEAL_AUDIT.json` 另核验 Lego/Chair 精确16个 F 封存文件：SEAL.json hash 与 LOCK 匹配、sidecar 匹配、context 与其 hash 一致，每帧27项 payload 路径真实存在。仅对 payload 做存在性检查；未重新读取其图像/raw内容，不能称为重验16帧全部数据。

继承 normalization scales 固定为 delta_D=`0.08261344276368612`、delta_A=`0.7444546544551854`、delta_N=`0.9862916707992548`、delta_C=`0.6385581493377686`、delta_G=`1.0`、visibility_raw=`1.0`；作者展示分母 `author_scale=0.7533644223213196`。全部来自既有 Lego/Chair 16F，禁止新增 scene 自适应或重新拟合。六通道 OUR B 与作者独立重建原式是不同读出。SH0、白背景、kernel_size=0、原始 PLY row ID 与 raw alpha*T 语义保持冻结。

## 相机与33帧轨道

旧 `INPUTS.json` 仅含 chair/drums/ficus/lego，没有 hotdog/materials/mic/ship。

如后续具备新增 frozen checkpoint，TRAIN 外参转换必须为 `w2c = inv(transform_matrix @ diag(1,-1,-1,1))`。水平焦距为 `fx = 0.5*W/tan(camera_angle_x/2)`；方像素令 `fy=fx`，`FoVy=2*atan(H/(2*fy))`。原生 K 主点为 `((W-1)/2,(H-1)/2)`，800×800时为399.5，匹配 CUDA `ndc2Pix`；不能使用旧 `src.common.load_cameras` 的400主点。原生尺寸必须由实际 TRAIN metadata/grid 确认，不能强制猜800。

旧轨道来自 `artifacts/direct_curve_global_fit_probe/freeze.py` 第21–27行：冻结中心为已有资格box两角均值；box来源是 PLY `mu.astype(float)` 逐轴 `.001/.999` quantile，并对称扩张 `0.1*norm(high-low)`，扩张不改变中心。取相机中心相对该中心的单位方向作球面插值、半径作线性插值，旋转以 SciPy `Rotation`/`Slerp` 独立插值；`t=np.linspace(0,1,33)`，组回 c2w 后取逆。它不是 look-at 重建。新增场景用户指定端点是 C7→C33，选择规则替换为这对端点，构造公式保持同一套。

`ARC_RECONSTRUCTION_CHECK.json` 用纯旧 INPUTS 元数据重建四场景全部8条轨道，共264个 pose；每条33个独立 pose，w2c最大绝对误差均为0。这只是构造核验，没有重渲染旧场景。

## 最小适配与相关回归

若输入具备，最小新增支持仅需：新scene/TRAIN相机冻结清单与域校验；新输出/状态/封存上下文；逐scene F校准；使用原 `compute_evidence(raw, lock['normalization'])`；新媒体布局/Telegram压制及独立核验。现阶段无输入，以上生产适配没有实施。

旧 renderer 文件可原样导入，由新增支持层在进程内将 `STAGE` 指向本次输出、`NATIVE` 指向旧只读构建；不能调用原 `calibrate_primary()` 或原生产 main（它们有旧scene/路径假设）。`render_native()` 每次已调用 GPU guard；新scene仍需同输入 patched/unpatched 数值校准：RGB/alpha/normal max_abs≤3e-6；depth/median_depth可用 max_abs≤1e-5且max_rel≤3e-6。异常为工程无效，不是科学 NO_GO。filter_3D缺失不可补造；法线仅是 native camera-space splat/ray-plane normals，未验证真实表面法线。

相关 CPU 回归为 `tests.test_hybrid_raster_evidence`、`tests.test_hybrid_raster_io`、`tests.test_hybrid_raster_stage`、`tests.test_hybrid_raster_verifier`、`tests.test_hybrid_raster_access`、`tests.test_hybrid_dense_v1`、`tests.test_hybrid_overlay_video`、`tests.test_hybrid_extra_scenes`、`tests.test_hao_mukai_source`。需要 GPU 的 native contract 和旧包装器测试必须等空闲且采用本次日志路径，不能直接运行会写旧out的默认入口。本只读审计未执行这些测试；实际本轮测试与最终结果由主报告单列。
