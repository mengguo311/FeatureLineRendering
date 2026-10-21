# Chair / Lego / Drums 分区排线 Demo

同一界面加载三个真实旧模型的保存资产，支持选择模型、跨视角选面、局部角度/间距/长度/线宽、旋转/缩放、撤销与导出。几何是原冻结GS的CPU深度所提取的粗代理，不是GT或自动语义部件；当前是可运行工程demo，外观仍partial。CPU每帧数秒，不是实时。

## 启动

```bash
cd /mnt/hdd1/u00134/partwise_sketch_hatching_models_v04/units/unit_008/portable_demo
./run.sh preview --scene lego
./run.sh viewer
```

打开终端给出的本机URL。**Model**切换Chair/Lego/Drums；每个模型在当前服务器中保留自己的相机、选择草稿、编辑和撤销记录。页面刷新也可继续当前状态。停止服务器前，对每个需要保留的模型点击 **Download saved asset**；下载只包含已提交资产，不包含尚未保存的选面草稿。不同模型的草稿名称在当前浏览器标签页分别保存。

默认Lego已包含人工`Bucket surfaces (manual)`区域。选择该区域，调四个风格参数，点击 **Render & save style**；**Update view · keep selection**及Orbit/Zoom只改变相机，保持路径与选面。选择包含整个代理三角面，可能超出矩形或覆盖原先遮挡的部分；不是完整语义铲斗分割。

可直接启动其他模型：

```bash
./run.sh viewer --scene chair --port 8766
./run.sh preview --scene drums
./run.sh orbit --scene lego
./run.sh zoom --scene lego
```

输出自动写入包内新`runs/`子目录；可用`--output /搬移后包路径/runs/自定义目录`指定尚不存在的目录。保存资产渲染不需要原PLY或旧工作树。包不含Python环境，依赖见`requirements.txt`；本机Linux环境实测，其他平台未验证。可用`DEMO_PY=/path/to/python ./run.sh viewer`指定解释器。`demo.py build`所需原模型重建工具未放入此精简包，完整构建来源保留在原工作树与unit001/003/005。

## 创建自己的局部区域

从Lego原三个高度区开始：

```bash
DEMO_CATALOG=AUTHORING_CATALOG.json ./run.sh viewer --scene lego
```

1. 在图像上点击来源区域，或选`Select faces from`。将Image tool切换为`Drag a visible rectangle`。
2. 拖框添加可见面；可切换Add/Subtract/Replace，或撤销一步/清空。相机旋转后继续添加另一侧，选中三维面保持不变。
3. `Show total selection`查看当前相机的总选面；输入名字，`Save total selection as region`一次提交。
4. 新区域成为风格编辑目标；调参数、保存并下载。草稿存在时风格更改和资产撤销暂停，避免更换其底层资产。
5. 切换模型不会丢失当前会话的草稿。可回原模型继续，但服务器重启不会自动恢复未提交草稿。

本轮Lego仅一次人工确定三矩形，三个固定构建视角；2030个选面仍可能含举升支撑的局部、边缘漏选和孔洞。没有阈值扫选或几何补洞。Chair为粗高度区；Drums含unit007的人工镲面选区，依然有邻近碎片与隐藏遗漏。

## CLI与冷加载

当前目录下，使用包内同一个入口：

```bash
./run.sh edit --scene lego --region 4 --angle 10 --spacing .06 --length .16 --width 1.6 --output "$PWD/runs/my_edit"
./run.sh preview --scene lego --asset "$PWD/runs/my_edit" --output "$PWD/runs/my_preview"
./run.sh author --scene lego --asset "$PWD/assets/lego_original" --region 3 --selection-recipe "$PWD/SELECTION_RECIPE.json" --name 'Bucket surfaces (manual)' --output "$PWD/runs/my_region"
```

上述输出目录应尚不存在。`--part`是`--region`别名。包内配方固定相机、三个矩形、操作顺序和原网格哈希，重放生成同一选面集合。

把浏览器下载ZIP解压到包内`runs/downloaded`后，在新进程打开：

```bash
DEMO_PY=/mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_8build_part_prior_feasibility_v03/venv/bin/python
"$DEMO_PY" source/viewer.py --asset "$PWD/runs/downloaded" --output "$PWD/runs/reopened" --port 8765
```

单资产viewer保留下载时的模型、区域、参数、路径和相机。三个模型各自的导出均经关闭服务器后新进程重绘验证，图像与数组一致；搬移包也逐模型冷加载，并重放Lego选面→角度编辑→渲染。保存路径和自身代理局部性不代表独立几何精度。

## 实际来源和证据范围

- Chair：原冻结vanilla GS；unit001深度代理、unit002保存路径/风格。
- Lego：原PLY SHA256 `fa9bea3fa4f8d349fa873a66d892c53cd1263499caec6421c286350a5bb7cbbc`，310475 Gaussian；unit003 CPU深度TSDF代理，16543顶点/29999面；本轮固定几何，直接再次渲染原PLY八参考相机。
- Drums：unit005原GS深度TSDF代理；unit007的固定四区路径及人工多视角面选区。

本轮未重新构建三模型几何；未使用GT、GPU、训练、自动语义模型或下载新依赖。模型原始路径/哈希保存在`PORTABLE_DEMO.json`；包内只需真实保存资产。

`previews/three_models.png`为三个真实模型同一入口预览；`reference_proxy_regions_hatch.png`展示Lego全部八组来源/代理/区域/排线；`local_edit_all_views.png`保留所有编辑前后视角，`selection_all_views.png`展示三个构建视角的选区，`orbit.mkv`/`zoom.mkv`及全帧接触图展示真实保存路径的相机变化。视频全帧解码核对只证明有限序列产物，不是全路径时序认证。旧训练/测试相机已有曝光，不称盲评。

Lego仍有底板波浪排线、车体孔洞、短碎线和细杆缺失；Drums支架破碎、鼓沿粗糙；Chair仍为粗代理。人工选区不是语义真值；附着/编辑掩码来自同一代理，不能证明重建正确。H1/H2未测试，历史P1 NO_GO与P2 ZERO_HEADROOM不变。

原机完整状态、实际命令/返回码与限制在`units/unit_008/STATUS.json`、`REPORT_ZH.md`、`REPRODUCE_ZH.md`和`logs/*.receipt.json`。可搬移归档为`units/unit_008/portable_demo.tar.gz`。
