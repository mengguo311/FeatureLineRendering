# 真实旧模型分区排线 Demo

当前支持 Chair、Lego、Drums。最新 Drums 包增加**直接点选已有区域、拖框预览可见面、保存为新区域**，并保留角度、间距、长度、线宽、Orbit、Zoom、撤销和导出。CPU 每帧约数秒，非实时 3D 浏览器。

```bash
cd /mnt/hdd1/u00134/partwise_sketch_hatching_models_v04/units/unit_006/portable_demo
./run.sh preview
./run.sh viewer
```

打开终端显示的本机 URL。默认包有四个区域；点击对象选择已有区域，再修改风格并按 **Render & save style**。也可在 Style region 下拉框中选 `Visible upper patch (manual)`。选择只改变操作目标，按保存后才把所选区域与风格写入当前资产。

## 从图像创建区域

从原三个高度区域演示：

```bash
DEMO_ASSET=original ./run.sh viewer
```

1. 点击模型上希望编辑的部位，选中其已有 style region。
2. Image tool 改为 **Drag a visible rectangle**，在右侧图像中拖一个矩形。
3. 检查粉色预览和选中面数量，输入名称，按 **Save new region**。
4. 新区域自动成为风格编辑目标；改 Angle、Spacing、Length 或 Width，再按保存。
5. Orbit / Zoom 实际重绘固定 3D 路径。**Download current asset** 导出当前网格、面标签、路径、参数、选择来源和相机。

可见选择只纳入当前相机前方射线首先命中的代理三角面，并限于指定来源区域。完全没有可见命中的面不会被纳入；**保存整个三角面**，因此面的一部分可越出屏幕矩形或原先受遮挡。它不会自动选中整件物体或补齐背面。旋转之后仍编辑这些固定面 ID，不重新按屏幕位置选取。较大的三角面、薄片两面和代理孔洞会限制选择精度。

**World box (includes hidden sides)** 保留旧的模型坐标框选：按面中心选择，包含隐藏侧。两种方式都属于人工编辑区，不是自动语义分割。空选择、非法坐标、过期视图/预览与会清空来源区域的选择会被拒绝。撤销栈只在当前服务器会话有效；浏览器刷新保留当前资产/相机，服务器重启时用下载的资产路径恢复。

本轮固定 Drums 相机 azimuth157°/elevation24°/distance4.9，在512²图像边坐标 `[128,128,260,240]` 拖框，从上区选1,291面。它覆盖部分上方表面，不保证是完整镲片。

## CLI 与冷加载

包内运行以下命令，使用尚不存在的输出目录。保存资产重绘不需要原始 PLY：

```bash
DEMO_PY=/mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_8build_part_prior_feasibility_v03/venv/bin/python
"$DEMO_PY" source/demo.py author --scene drums --asset assets/original --region 3 --screen-rect 128 128 260 240 --azimuth 157 --elevation 24 --distance 4.9 --name 'Visible upper patch (manual)' --output runs/my_region
"$DEMO_PY" source/demo.py edit --scene drums --asset runs/my_region --part 4 --angle 35 --output runs/my_edit
"$DEMO_PY" source/demo.py render --scene drums --asset runs/my_edit --view train_r_7 --output runs/my_preview
./run.sh orbit
./run.sh zoom
```

`author` 另支持 `--bounds XMIN YMIN ZMIN XMAX YMAX ZMAX` 的世界框选；`edit` 支持 `--angle --spacing --length --width`；`render` 支持 `--trajectory static|orbit|zoom` 或独立相机参数与 `--size`。从下载ZIP解压到例如 `runs/downloaded` 后，可运行 `source/viewer.py --asset runs/downloaded --output runs/reopened --port 8765`。换目录解压包后可直接用 `./run.sh`，或设 `DEMO_PY=/path/to/python`；依赖见 requirements.txt，未捆绑Python环境，其他平台未测试。

## 来源与限制

Drums 原冻结 vanilla GS：360,012 Gaussian，SHA256 `d4b67123927613ade6b7e2f38ed6bf724fc5e348dbcca84a2be1352ec5113a8b`。unit005 从原 PLY 串行 CPU 深度渲染24训练视角并TSDF提取16,839顶点/29,999面的粗代理；unit006固定该几何，重新执行原PLY八视角参考渲染。本轮不重建或修补几何。没有 GT 替代、GPU训练或旧 ink 代理。

原三分区为人工世界高度阈值 -0.15 / 0.42；新区域为保存的人工可见面选择。附着和编辑局部性是相对于同一代理的实现检查；同模型深度一致性不是独立几何真值。薄支架断裂、鼓沿粗糙、鼓体孔洞和短碎线仍明显。原test_r_79左缘约1.56px裁切保留为负例。视频完整解码不等于全路径时序认证，历史曝光视角不称盲测，H1/H2未验证，历史NO_GO不改写。

最新包 `units/unit_006/portable_demo.tar.gz`；旧Chair=`units/unit_002/portable_demo.tar.gz`、Lego=`units/unit_004/portable_demo.tar.gz`、Drums原三分区=`units/unit_005/portable_demo.tar.gz`。旧包不会自动更新界面；新工作树viewer可加载其保存资产。

原PLY→CPU深度→TSDF→路径完整重建由unit005实际验证；在原机工作树可复现（输出须为空，unit006是选区协议，不能传给build）：

```bash
cd /home/u00134/3dgs_line/partwise_sketch_hatching_models_v04
DEMO_PY=/mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_8build_part_prior_feasibility_v03/venv/bin/python
"$DEMO_PY" experiments/partwise_sketch_hatching_v04/demo.py build --scene drums --unit /mnt/hdd1/u00134/partwise_sketch_hatching_models_v04/units/unit_005 --output /mnt/hdd1/u00134/partwise_sketch_hatching_models_v04/user_runs/drums_build
```

局部角度编辑的其他区域路径和图层精确不变；创建区域本身在三个视角仍有0.2–0.4灰度L1的远区栅格变化，属于已知部分完成项。没有为此改图或放宽2px边界带。

本轮证据位于unit006：`media/reference_proxy_regions_hatch.png`（八视角完整对象/弱视图）、`media/local_edit_all_views.png`、`media/orbit.mkv`、`media/zoom.mkv`、`browser_complete/`、`metrics/`；精确命令与返回码见 `REPRODUCE_ZH.md`、`logs/*.receipt.json`，最终状态与局限见 `STATUS.json`/`REPORT_ZH.md`。
