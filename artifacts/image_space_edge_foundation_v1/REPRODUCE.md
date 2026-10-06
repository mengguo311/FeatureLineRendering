# 图像空间边界场复现

本轮使用既有 `vfsdgs` Python 环境、stock Graphdeco renderer、已归档 stock/knn 扩展和 FFmpeg；未安装依赖。模型与照片位置从旧 `DATA_FREEZE.json` 解析，原生扩展位置从旧 runtime 的字面量解析，不需要复制 PLY、修改旧文件或读取凭据。只有本实验的 experiments、artifacts、ignored out 三个目录可写。

在本工作区根目录顺序执行：

```bash
export PYTHONDONTWRITEBYTECODE=1 CUDA_VISIBLE_DEVICES=0
export OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 MKL_NUM_THREADS=2
ISBF_PY=/home/u00134/bin/miniconda3/envs/vfsdgs/bin/python
mkdir -p out/image_space_edge_foundation_v1
printf '*\n' > out/image_space_edge_foundation_v1/.gitignore
"$ISBF_PY" -m unittest discover -s experiments/image_space_edge_foundation_v1/tests -v
"$ISBF_PY" experiments/image_space_edge_foundation_v1/run.py dev
"$ISBF_PY" experiments/image_space_edge_foundation_v1/run.py production
"$ISBF_PY" artifacts/image_space_edge_foundation_v1/tests/CONTROL_RED.py
"$ISBF_PY" artifacts/image_space_edge_foundation_v1/POST_CONTROL_GUARD.py
"$ISBF_PY" artifacts/image_space_edge_foundation_v1/POST_CONTROL_ANCHORED.py
"$ISBF_PY" artifacts/image_space_edge_foundation_v1/POST_LAYER_CLASSIFICATION.py
"$ISBF_PY" artifacts/image_space_edge_foundation_v1/TEMPORAL_CONTROL_AUDIT.py
"$ISBF_PY" artifacts/image_space_edge_foundation_v1/POST_ABLATIONS.py
"$ISBF_PY" artifacts/image_space_edge_foundation_v1/INDEPENDENT_CHECK.py
"$ISBF_PY" artifacts/image_space_edge_foundation_v1/CURATE.py
```

`CONTROL_RED.py` 对原候选预期失败，保留这个退出码与日志后继续运行守卫修正；它不是生产成功门槛。亮度基线的预期行为 RED 可另用 `experiments/image_space_edge_foundation_v1/tests/intensity_baseline_red.py` 复现。正常 foundation unittest 应通过。

原生产宽度候选还有已知界面反向梯度，`tests/INDEPENDENT_AUDIT_INITIAL.json` 保留该失败。`POST_CONTROL_GUARD.py` 仅补充无新裁剪与非边缘回退；最终可选控制来自 `POST_CONTROL_ANCHORED.py`，先验证既有 DEV 与解析合成界面，再以独立 `ANCHORED_CONTROL_FREEZE.json` 应用于已经研究见过的固定图。它端点固定、单调拟合重组，同时保留原 RGB 残差。最终 RGB 图在 `media/*/guarded_RGB_v2/fixed`，所有原候选/v1 图仍保留。该修正不更改冻结主空间方法或时间视频。

DEV 为每场景 r_007、r_033、r_059、r_086；固定评价为 r_000、r_008、r_018、r_030。生产冻结在这些固定图与连续相机渲染前落盘，匹配阈值/增益是两场景共享的一组 DEV 参数。完整 33 帧使用旧 `arc0_000…arc0_032` 顺序、原 w2c 和 FoV；原生分辨率 800×800，K 随原生尺寸恢复，stock 投影与协方差像素下限未变。该 arc 是历史有限角度轨迹，不能称 360° 全周测试。它们均不是新的盲测视角，未读取原始 TEST 照片。

runner 使用文件锁与普通进程。每个 GPU 相机单元查询 GPU0 PID 和 UID；其他 PID 占用时失败并留存状态，不终止进程。每单元检查固定 4 GiB 根分区、1.5 GiB common Git 保留量和 8 GiB stage 上限。场景失败不阻止另一场景的尝试。`out/.../STATUS.json`、`EVENTS.jsonl` 和 `logs` 保留实际状态与资源记录。

每场景每阶段的 `seals/*.json` 校验输入冻结与所有输出 SHA256；重复运行验证后跳过已有单元。改变已冻结源码或参数会拒绝恢复，不会覆盖成同一实验。DEV 与生产冻结分别保存源码哈希。`POST_CONTROL_FREEZE.json` 单独冻结后续 RGB 无新裁剪守卫；它是发现固定图候选问题后的工程修正，不能冒充原生产的盲测改善。

`media/*/fixed/*` 保存原生图、原 TRAIN 对比图、独立线稿、叠加、原生 crop、2× 最近邻 zoom、证据图、float16 原生软场和 float32 法向剖面。out 保存全部视角的 float32 场、完整剖面采样、2D chains、native alpha、flow 和 RGB 控制数组；精确哈希位于 seals 与 MANIFEST。classmap 0=无显著 RGB ridge，1=合格颜色过渡剖面支持，2=detail/unknown；native alpha 轮廓是独立辅助文件。没有材质/几何语义标注或持久 3D 路径。

每场景有 lines 和 overlays 两条 33 帧视频，布局为原生 RGB / Canny / 相同空间方法 OFF / 相同空间方法加 temporal ON。3200×844、H264、yuv420p、12 fps、faststart。首次/中间/末帧和所有 33 帧联系表均保留；独立审计再次解码全部帧，并去掉文字栏检查每帧原生 RGB 的实际变化及与 native PNG 的误差。

`INDEPENDENT_CHECK.py` 是主代理单独执行的 CPU 后审计：检查保护输入、旧分支、冻结源码/封印、完整 native RGB、字段关系、剖面、弧长、RGB 守卫和实际视频。它的 PASS 表示工程/接口与媒体完整性通过，不能代替人工语义/视觉 GO。`REPORT_ZH.md` 与 `FINAL.json` 区分科学阶段判断和工程结果。
