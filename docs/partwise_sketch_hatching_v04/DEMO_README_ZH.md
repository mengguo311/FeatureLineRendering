# Chair / Lego 分区排线 Demo

最新单元 `unit_003` 已在原有 Lego（310,475 个高斯）上生成真实代理、固定三维排线和局部编辑资产。Chair 的既有包保持不变。两个模型均为冻结 vanilla 3DGS 加探索性 TSDF 代理；不是 GT 或 RaDe-GS 训练表面。最终验证、失败与限制见各单元 STATUS / REPORT / metrics。

## Lego quick start — unit003

使用本机目录，或解压 `units/unit_003/portable_demo.tar.gz` 后在包目录运行：

```bash
cd /mnt/hdd1/u00134/partwise_sketch_hatching_models_v04/units/unit_003/portable_demo
./run.sh preview
./run.sh viewer
```

浏览器打开 `http://127.0.0.1:8765`。选择区域，调整 Angle / Plane spacing / Stroke length / Line width，按 **Render & save**。Orbit / Zoom 实际重绘固定三维路径；Regions / Proxy 切换图层；Download current asset 下载 ZIP。Ctrl+C 退出服务器。新结果只写包内 `runs/`。

Lego `baseline` 是原角度资产（viewer 默认）；`edited` 只把中区域角度 45° 改为 95°（preview 默认）。Lego 没有 Chair 的 `original` 平滑前对照版本。可用 `./run.sh orbit`、`./run.sh zoom`，或 `DEMO_ASSET=baseline ./run.sh preview`。可设置 `DEMO_PORT=8766` 和 `DEMO_PY=/path/to/python`。包内 requirements.txt 列出依赖，未捆绑解释器。保存资产的演示不读取原始 PLY、照片或旧工作树；其他操作系统未验证。

在工作树根目录执行自定义编辑与冷加载（输出必须为新目录）：

```bash
DEMO_PY=/mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_8build_part_prior_feasibility_v03/venv/bin/python
DEMO_UNIT=/mnt/hdd1/u00134/partwise_sketch_hatching_models_v04/units/unit_003
DEMO_CODE=experiments/partwise_sketch_hatching_v04
DEMO_OUT=/mnt/hdd1/u00134/partwise_sketch_hatching_models_v04/demo_runs
DEMO_STAMP=$(date +%Y%m%d_%H%M%S)
"$DEMO_PY" "$DEMO_CODE/demo.py" edit --scene lego --asset "$DEMO_UNIT/assets/baseline" \
  --part 2 --angle 95 --spacing .06 --length .12 --width 1.8 --output "$DEMO_OUT/edit_$DEMO_STAMP"
"$DEMO_PY" "$DEMO_CODE/demo.py" render --scene lego --asset "$DEMO_OUT/edit_$DEMO_STAMP" \
  --azimuth 47 --elevation 28 --distance 4.9 --output "$DEMO_OUT/preview_$DEMO_STAMP"
"$DEMO_PY" "$DEMO_CODE/demo.py" build --scene lego --unit "$DEMO_UNIT" \
  --output "$DEMO_OUT/rebuild_$DEMO_STAMP"
```

最后一条命令从协议中的原始 PLY 串行 CPU 渲染24个训练视角、融合代理、生成保存资产和首图，需原始输入仍在协议位置。Lego PLY SHA256：`fa9bea3fa4f8d349fa873a66d892c53cd1263499caec6421c286350a5bb7cbbc`。下载 ZIP 解压后，将目录作为 `--asset` 传入同一 `render` 命令即可。

Lego 的1/2/3区域为 z<-0.20、-0.20≤z<0.45、z≥0.45 的**人工高度风格区**，不等同于完整履带、驾驶室或铲斗语义。Angle 是世界切割平面方向；spacing 是平面间距，不是统一测地间距；length 是最大世界弧长，孔洞/边界会提前截短；width 用屏幕像素。代理顶点/路径编号不是原始高斯索引，编辑目标路径会更新版本，非目标路径保留。

`unit_003/media/` 展示八个完整对象视角、局部编辑和全部轨迹帧。孔洞、底面缺失、薄零件损失与碎线/密线仍在；人工高度规则会切过真实零件。自身代理附着、有限视角编辑保持和完整视频解码都不是独立几何/时序真值。无H1/H2增益、自动语义、交叉排线、LOD或实时帧率声明。

## Chair instructions — unit002

已在原有 Chair（256,690 个高斯）上真实运行。当前可选择区域、修改角度/间距/长度/线宽、旋转/缩放、导出并冷加载三维资产。CPU 单幅约 2–3 秒；这不是实时帧率或 H1/H2 科学成功证明。

unit002 增加一个受限平滑版本，并保留 unit001 原代理。座面/椅背排线更平顺，但源模型深度和轮廓一致性略降，因此平滑版本是**外观选项，不是几何精度提升**。区域仍为人工高度分区，不能叫自动语义分割。源码、原始图像、弱视角和失败日志均保留。

## Quick start

直接使用已准备好的可搬移目录，或解压 `units/unit_002/portable_demo.tar.gz` 后运行：

```bash
cd /mnt/hdd1/u00134/partwise_sketch_hatching_models_v04/units/unit_002/portable_demo
./run.sh preview
./run.sh viewer
```

浏览器打开 `http://127.0.0.1:8765`。选择 **Style region**，调整参数，按 **Render & save**。Orbit / Zoom 按钮会实际重绘保存的三维路径；Regions / Proxy 切换图层；Download current asset 下载当前资产 ZIP。Ctrl+C 退出服务器。每次运行只向包内新的 `runs/` 目录写结果。

- `baseline`：受限平滑代理，原角度配置；viewer 默认。
- `edited`：同一代理，中区域角度 45°→95°；preview 默认。
- `original`：unit001 原代理与路径，供对照。

```bash
DEMO_ASSET=original ./run.sh viewer
DEMO_ASSET=baseline ./run.sh preview
./run.sh orbit
./run.sh zoom
```

可设置 `DEMO_PORT=8766` 或 `DEMO_PY=/path/to/python`。本机默认复用已有 CPU venv，未安装新依赖；其他机器需安装包内 `requirements.txt`。保存资产演示不依赖原 PLY、旧工作树或照片。未验证其他操作系统。

## CLI and saved-asset reload

在授权工作树根目录运行；以下输出均为新目录。`DEMO_OUT` 的父目录是本任务输出根，不向已封存的历史单元写入。

```bash
DEMO_PY=/mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_8build_part_prior_feasibility_v03/venv/bin/python
DEMO_UNIT=/mnt/hdd1/u00134/partwise_sketch_hatching_models_v04/units/unit_002
DEMO_CODE=experiments/partwise_sketch_hatching_v04
DEMO_OUT=/mnt/hdd1/u00134/partwise_sketch_hatching_models_v04/demo_runs
DEMO_STAMP=$(date +%Y%m%d_%H%M%S)

"$DEMO_PY" "$DEMO_CODE/demo.py" edit --scene chair \
  --asset "$DEMO_UNIT/assets/baseline" --part 2 \
  --angle 95 --spacing .06 --length .12 --width 1.8 \
  --output "$DEMO_OUT/edit_$DEMO_STAMP"

"$DEMO_PY" "$DEMO_CODE/demo.py" render --scene chair \
  --asset "$DEMO_OUT/edit_$DEMO_STAMP" --azimuth 47 --elevation 25 --distance 4.6 \
  --output "$DEMO_OUT/preview_$DEMO_STAMP"
```

下载的 ZIP 解压后，将解压目录作为 `--asset` 传给同一 `render` 命令即可冷加载。资产含网格、冻结面标签、样式、路径 ID、三角面 ID 和重心锚点。不同网格版本的数字 path ID 不能当作同一几何笔触；同一资产跨相机与局部编辑的非目标路径保持固定。

`--region` / `--part` 为 1 下、2 中、3 上。Angle 是世界空间切割平面的角度，spacing 是平面间距，不等于全曲面的统一切向角/测地间距。Length 是最大世界弧长，遇孔洞或区域边界会提前停止；width 是屏幕像素宽度。当前没有交叉排线控制、自动分部、细节 LOD 或独立结构曲线恢复。

## Rebuild the actual model

以下单条命令重读精确原始 PLY，真实 CPU 渲染 24 个训练视角并融合原代理，然后执行已冻结的受限平滑、生成保存资产及第一张完整图。需原输入仍在协议记录的位置。

```bash
"$DEMO_PY" "$DEMO_CODE/demo.py" build --scene chair \
  --unit "$DEMO_UNIT" --output "$DEMO_OUT/rebuild_$DEMO_STAMP"
```

源 PLY SHA256：`13e4ecc9ffe9c5ae2a0656e2e5c56a737cfdc90a62ad04799db3c46b0b442f5d`。输入是冻结 vanilla 3DGS，表面来自协方差平面估计深度与 TSDF，不是 GT 网格或 RaDe-GS 训练表面。所有数值程序在导入数值库前禁用 CUDA，限制两核 affinity、单线程数值库并串行运行。

## Evidence and limits

`unit_002/media/` 包含 8 个完整视角的原模型 RGB / 原代理 / 候选代理 / 排线对照，以及局部编辑前后图。`refinement_historical_views.png` 保留原先四个已曝光视角；`refinement_new_views.png` 是本轮输出前冻结的四视角，不能称盲测。

12 帧 orbit、6 帧 zoom 均从同一保存资产逐相机渲染，完整 FFV1 解码与源 PNG 精确。视频只有有限帧工程证据，不是完整遮挡或时序认证。实际浏览器截图与操作收据在 `browser_complete/`；HTTP 六种参数/相机操作另在 `metrics/VIEWER_SMOKE.json`。

平滑不填孔、不改拓扑；全部下区域顶点/路径保留，局部编辑的非目标路径/图层精确不变。前视图继承一处固定 2px 区域带外 0.2 灰度残差，仍标为 partial。稀疏椅腿、局部拥挤、薄结构与雕花损失、人工高度区切过椅背的问题仍在。只验证了相对于当前代理的附着，没有独立几何真值、全路径可见性或 H1/H2 增益结论。
