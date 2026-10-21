# 真实旧模型分区排线 Demo

当前有 Chair、Lego、Drums 的真实旧模型资产。最新 Drums 演示支持**跨视角添加/减去可见面、总选区预览、一次保存为区域**，以及角度、间距、长度、线宽、旋转、缩放、撤销和导出。CPU 每帧约数秒，不是实时渲染。

```bash
cd /mnt/hdd1/u00134/partwise_sketch_hatching_models_v04/units/unit_007/portable_demo
./run.sh preview
./run.sh viewer
```

浏览器打开终端显示的本机 URL。默认加载已保存的四区资产；在 Style region 选择 `Upper cymbal surface (manual)`，调整风格，点击 **Render & save style**。`./run.sh preview` 冷加载角度编辑后的资产并写入包内 `runs/`。

## 跨视角创建一个区域

从原三个高度区域开始：

```bash
DEMO_ASSET=original ./run.sh viewer
```

1. 点击模型选择来源区域，将 Image tool 改成 **Drag a visible rectangle**。
2. 用 **Add visible faces** 拖框添加表面；用 **Subtract visible faces** 减去误选，或用 **Replace selection** 重新开始。
3. 点击 Orbit/Zoom，或调整相机滑条后点 **Update view · keep selection**。已选三维面保持不变，粉色预览随相机重绘。导航不生成新路径或资产副本。
4. **Undo selection step** 撤销一步；**Clear selection** 清空草稿；**Show total selection** 在当前相机检查总选区。
5. 输入名称，按 **Save total selection as region** 一次提交。新区域会成为风格编辑目标，此后可调整四个风格参数。
6. **Download saved asset** 导出网格、面标签、固定路径、参数、选面来源和当前相机。尚未提交的草稿不包含在资产下载中。

草稿存在时，风格保存和资产撤销暂不可用，防止在选面中途更换底层资产。浏览器刷新保留同一服务器中的选面草稿和相机，输入的区域名称保存在当前浏览器标签页。关闭服务器不会自动恢复未提交草稿；请先提交并下载资产。已保存的区域可在服务器重启后冷加载。

选择限于一个来源区内的首命中代理三角面，保存**整个三角面**。没有可见命中的面不会自动补齐；面的一部分可能超出框或原先被遮挡。世界框选 **World box (includes hidden sides)** 仍可用，但需先清空可见选面草稿。两者都是人工编辑区，不是自动语义分割。

本轮由代理图像人工指定四次矩形操作，三个构建视角，选面数640→855→911→718。718面仍有36个索引边连通片，包含邻近镲片/鼓沿/支架的少量碎片和背面遗漏；这个名称表达编辑意图，不是完整语义镲片标签。

## CLI 与冷加载

包内 `SELECTION_RECIPE.json` 保存本轮的相机、矩形、增减顺序和输入网格哈希。以下输出目录必须尚不存在：

```bash
DEMO_PY=/mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_8build_part_prior_feasibility_v03/venv/bin/python
"$DEMO_PY" source/demo.py author --scene drums --asset assets/original --region 3 --selection-recipe SELECTION_RECIPE.json --name 'Upper cymbal surface (manual)' --output runs/my_region
"$DEMO_PY" source/demo.py edit --scene drums --asset runs/my_region --part 4 --angle 35 --output runs/my_edit
"$DEMO_PY" source/demo.py render --scene drums --asset runs/my_edit --view train_r_7 --output runs/my_preview
./run.sh orbit
./run.sh zoom
```

`author` 也支持 `--screen-rect LEFT TOP RIGHT BOTTOM` 配合相机参数，以及 `--bounds XMIN YMIN ZMIN XMAX YMAX ZMAX`；`edit` 支持 `--angle --spacing --length --width`；`render` 支持 `--trajectory static|orbit|zoom` 或独立相机及 `--size`。

下载ZIP解压到 `runs/downloaded` 后，可执行：

```bash
"$DEMO_PY" source/viewer.py --asset runs/downloaded --output runs/reopened --port 8765
```

可搬移包无需原始PLY或旧工作树即可重绘保存资产。可用 `DEMO_PY=/path/to/python ./run.sh viewer` 指定已装依赖的解释器；依赖见 requirements.txt，未捆绑Python环境，其他平台未测试。

## 来源、实跑与限制

Drums 原冻结 vanilla GS：360,012 Gaussian，SHA256 `d4b67123927613ade6b7e2f38ed6bf724fc5e348dbcca84a2be1352ec5113a8b`。unit005 从原PLY串行CPU深度渲染24训练视角，再TSDF提取16,839顶点/29,999面的粗代理。unit007固定该代理，重新执行原PLY八视角参考渲染；没有重建或修补几何，没有GT替代或GPU训练。原三区是世界高度阈值 -0.15 / 0.42。

本轮实跑CLI作者操作、局部编辑、浏览器鼠标拖框/键盘命名/跨视角增减/撤销/刷新/导出、新进程冷加载和搬移包重放。其他区域路径与图层精确保持；八视角局部角度编辑在固定2px边界带之外变化为0。区域创建本身的微小栅格副作用另记在报告中，不宣称作者操作普遍零泄漏。

薄支架断裂、鼓沿噪声、鼓体孔洞和碎短线仍明显。7/8静态视角完整入框；继承test_r_79左缘约1.56px裁切作为负例保留。12旋转/6缩放均完整入框并逐帧解码核对；不代表完整时序认证。附着/局部性相对于同一代理，同模型深度不是独立真值。旧训练/测试视图已有曝光，不称盲评；H1/H2未验证，历史NO_GO保留。

最新包：`units/unit_007/portable_demo.tar.gz`。旧Chair包=`units/unit_002/portable_demo.tar.gz`，Lego=`units/unit_004/portable_demo.tar.gz`，Drums原三区=`units/unit_005/portable_demo.tar.gz`。旧包界面不会自动更新，新工作树viewer可读取其资产。

原PLY→CPU深度→TSDF→路径完整重建由unit005验证；unit007是选区协议，不能用作build协议。原机重建入口：

```bash
cd /home/u00134/3dgs_line/partwise_sketch_hatching_models_v04
DEMO_PY=/mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_8build_part_prior_feasibility_v03/venv/bin/python
"$DEMO_PY" experiments/partwise_sketch_hatching_v04/demo.py build --scene drums --unit /mnt/hdd1/u00134/partwise_sketch_hatching_models_v04/units/unit_005 --output /mnt/hdd1/u00134/partwise_sketch_hatching_models_v04/user_runs/drums_build
```

当前证据在unit007：`selection/selection_all_views.png`、`media/reference_proxy_regions_hatch.png`、`media/local_edit_all_views.png`、`media/orbit.mkv`、`media/zoom.mkv`、`browser_complete/`、`metrics/`。准确命令和返回码见 `REPRODUCE_ZH.md` 与 `logs/*.receipt.json`；状态、失败及边界见 `STATUS.json` / `REPORT_ZH.md`。
