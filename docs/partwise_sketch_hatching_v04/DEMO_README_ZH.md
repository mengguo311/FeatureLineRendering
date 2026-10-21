# 真实旧模型分区排线 Demo

当前提供 **Chair、Lego、Drums** 三个真实旧模型资产。Drums 的入口如下；Lego 人工区域作者说明保留在后面。

```bash
cd /mnt/hdd1/u00134/partwise_sketch_hatching_models_v04/units/unit_005/portable_demo
./run.sh preview
./run.sh viewer
```

浏览器打开终端显示的本机 URL，选择 Style region，修改 Angle、Spacing、Length 或 Width，点击 **Render & save style**。Orbit/Zoom 会从固定3D资产实际重新渲染。下载按钮导出当前资产，`./run.sh orbit`、`./run.sh zoom` 输出保存轨迹。CPU 每帧约2–3秒，不是实时浏览器3D渲染。

Drums 从原360,012个高斯直接串行CPU渲染24个训练视角，再提取16,839顶点/29,999面代理。没有可用的历史Drums源深度缓存，缓存重放明确标记 `NOT_AVAILABLE`；不把无缓存当作核验通过。三个区域是人工世界高度阈值 -0.15 / 0.42，不是鼓或镲片的语义分割。完整对象可辨，但薄支架、鼓沿及孔洞仍有缺失；细节和弱视图见 `unit_005/media/reference_proxy_regions_hatch.png`。

从保存资产编辑和冷加载，不需要原始检查点：

```bash
DEMO_PY=/mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_8build_part_prior_feasibility_v03/venv/bin/python
"$DEMO_PY" source/demo.py edit --scene drums --asset assets/baseline --region 2 --angle 95 --output runs/my_edit
"$DEMO_PY" source/demo.py render --scene drums --asset runs/my_edit --view train_r_7 --output runs/my_preview
```

保留原检查点的本机，还可从工作树一条命令重新执行完整构建（输出目录须为空）：

```bash
cd /home/u00134/3dgs_line/partwise_sketch_hatching_models_v04
DEMO_PY=/mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_8build_part_prior_feasibility_v03/venv/bin/python
"$DEMO_PY" experiments/partwise_sketch_hatching_v04/demo.py build --scene drums --unit /mnt/hdd1/u00134/partwise_sketch_hatching_models_v04/units/unit_005 --output /mnt/hdd1/u00134/partwise_sketch_hatching_models_v04/user_runs/drums_build
```

各模型包位置：Chair=`units/unit_002/portable_demo.tar.gz`，Lego=`units/unit_004/portable_demo.tar.gz`，Drums=`units/unit_005/portable_demo.tar.gz`。可搬移解压；依赖见包内 `requirements.txt`，未捆绑Python环境，其他平台未测。Drums 的 `STATUS.json`、`REPORT_ZH.md`、`REPRODUCE_ZH.md`、`metrics/` 记录实际测试、命令返回码及限制。

## Lego 人工区域作者

Lego 最新版本增加**可预览、保存、撤销的人工三维区域选择**：可以从原来的高度区域里分出前铲斗区域，再单独修改排线角度、间距、长度和线宽。保存的三维路径参与每个相机的深度测试。

这仍是外观部分完成的工程 demo。几何来自旧 vanilla 3DGS 的 CPU 深度估计与 TSDF 代理，不是 GT，也不是重新训练的 RaDe-GS。细杆缺失、孔洞、底板密集波浪线和短片段仍可见。手动框选不是自动语义分割；本示例“Front bucket area”也包含附近的举升支撑。

## 直接运行

本机使用以下入口；输出会写入包内新建的 `runs/` 目录：

```bash
cd /mnt/hdd1/u00134/partwise_sketch_hatching_models_v04/units/unit_004/portable_demo
./run.sh preview
./run.sh viewer
```

浏览器打开终端显示的 `http://127.0.0.1:8765`。默认加载已经有四个区域的 baseline；在 Style region 选择 `Front bucket area (manual)`，改 Angle 后点击 **Render & save style**。Orbit、Zoom 控件实际重新渲染；不是静态帧播放器。区域颜色模式显示所选面所属区域。一次 CPU 渲染约数秒，不是实时帧率。

下载当前资产会导出网格、区域标签、固定路径、风格参数、选择历史与当前相机。撤销恢复本次服务器会话中的上一个资产/相机；重启后仍可加载下载的版本，但撤销栈不会保存。浏览器刷新恢复当前保存的区域选择与相机。

```bash
./run.sh orbit
./run.sh zoom
```

可将 `portable_demo.tar.gz` 解压到其他目录；设置 `DEMO_PY=/path/to/python` 可指定已安装依赖的解释器。要求见包内 `requirements.txt`。保存资产的渲染无需原 PLY；没有捆绑 Python 环境，其他操作系统未验证。

## 在浏览器中创建新区域

若要完整复现本轮区域作者操作，从旧的三个区域开始：

```bash
DEMO_ASSET=original ./run.sh viewer
```

在 **Create a manual region** 选择上区（source region 3），填入以下模型坐标范围：

| Axis | Minimum | Maximum |
|---|---:|---:|
| X | -0.70 | 0.70 |
| Y | -1.20 | -0.35 |
| Z | 0.45 | 1.10 |

命名 `Front bucket area (manual)`，先点击 **Preview box** 检查粉色区域，再点击 **Save new region**。此框选择 3,001 / 5,040 个上区三角面。以面中心判断是否位于框内，隐藏的背面也会选中，不是只涂屏幕可见像素。保留至少一部分原区域；空选择、非法范围和过期预览会被拒绝。选择保存后，新区域自动出现在 Style region 中。

框选操作只改变面标签：顶点/面索引不变；所有未选择的路径段保持原坐标与 ID。原区域在新边界处会留下截短的路径。新区域重新生成自己的路径，后续风格编辑只更新该区域。选择文件保存的是**代理三角面 ID**，不是原高斯行号。

## CLI 复现

在工作树目录执行，选择未使用的输出目录；程序拒绝覆盖已有非空输出。

```bash
cd /home/u00134/3dgs_line/partwise_sketch_hatching_models_v04
DEMO_PY=/mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_8build_part_prior_feasibility_v03/venv/bin/python
DEMO_CODE=experiments/partwise_sketch_hatching_v04
DEMO_UNIT=/mnt/hdd1/u00134/partwise_sketch_hatching_models_v04/units/unit_004
"$DEMO_PY" "$DEMO_CODE/demo.py" author --scene lego --asset "$DEMO_UNIT/assets/original" --region 3 --bounds -.70 -1.20 .45 .70 -.35 1.10 --name 'Front bucket area (manual)' --output "$DEMO_UNIT/user_runs/authored"
"$DEMO_PY" "$DEMO_CODE/demo.py" edit --scene lego --asset "$DEMO_UNIT/user_runs/authored" --part 4 --angle 35 --output "$DEMO_UNIT/user_runs/edited"
"$DEMO_PY" "$DEMO_CODE/demo.py" render --scene lego --asset "$DEMO_UNIT/user_runs/edited" --view train_r_7 --output "$DEMO_UNIT/user_runs/cold_preview"
```

`edit` 另支持 `--spacing`、`--length`、`--width`，`render` 支持 `--trajectory orbit|zoom|static` 或 `--azimuth`、`--elevation`、`--distance`、`--size`。所有本任务入口先关闭 CUDA 并限制两核，数值线程为 1；不需要服务凭据或网络模型。

原始 PLY→CPU 深度→TSDF→路径的重建命令仍沿用 unit003 的冻结几何协议；该完整链在 unit003 已实际验证，本轮固定代理，仅重新运行原 PLY 的八视角渲染并进行区域控制验证。不要将 unit004 的区域协议传给 `build`：它只记录区域拆分。

```bash
"$DEMO_PY" "$DEMO_CODE/demo.py" build --scene lego --unit /mnt/hdd1/u00134/partwise_sketch_hatching_models_v04/units/unit_003 --output /mnt/hdd1/u00134/partwise_sketch_hatching_models_v04/user_runs/lego_build
```

Chair 的独立包仍在 `units/unit_002/portable_demo/`；Lego 旧三分区包仍在 `units/unit_003/portable_demo/`。旧输出不改写。

## 实际证据与边界

本轮的完整对象参考/代理/区域/排线对照位于 `unit_004/media/reference_proxy_regions_hatch.png`，局部编辑八视角位于 `media/local_edit_all_views.png`。轨迹原帧位于 `renders/orbit` 与 `renders/zoom`，视频与全部帧接触图位于 `media/`。真实浏览器截图及操作收据位于 `browser_complete/`。命令和返回码保存在 `logs/*.receipt.json`；最终状态、指标和局限见 `STATUS.json`、`REPORT_ZH.md`、`metrics/VALIDATION.json`。

验证区分：实现相对自身代理的附着/局部性、真实模型来源、视觉粗糙程度与科学假设。有限帧视频完整解码不等于全时序认证；手动区域没有独立语义真值；历史已曝光视角不称盲评。P1 历史 NO_GO 与 P2 ZERO_HEADROOM 不改写，H1/H2 未验证。
