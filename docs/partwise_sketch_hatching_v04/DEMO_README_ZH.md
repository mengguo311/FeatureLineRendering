# Chair Partwise Hatch Demo

已在原有 Chair 的 256,690 个高斯检查点上真实运行 CPU 渲染、深度筛选、代理提取和三维排线。当前交付是可运行的粗糙工程 demo：不是 GT 台灯，不是新训练模型，也不是完整的 H1/H2 科学验证。

源模型 SHA256：`13e4ecc9ffe9c5ae2a0656e2e5c56a737cfdc90a62ad04799db3c46b0b442f5d`。原模型为 vanilla 3DGS；深度是其协方差平面估计，不能称为 RaDe-GS 训练重建。三块区域来自人工指定的世界高度阈值，不能称为自动语义分割。

## Run saved asset

在工作树根目录运行。输出目录必须是新目录；已有结果不会被覆盖。

```bash
DEMO_PY=/mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_8build_part_prior_feasibility_v03/venv/bin/python
DEMO_UNIT=/mnt/hdd1/u00134/partwise_sketch_hatching_models_v04/units/unit_001
DEMO_CODE=experiments/partwise_sketch_hatching_v04

"$DEMO_PY" "$DEMO_CODE/demo.py" render --scene chair \
  --asset "$DEMO_UNIT/assets/edited" --view train_r_32 \
  --output "$DEMO_UNIT/user_preview_001"
```

程序在导入数值库前关闭 CUDA，固定两核 affinity 和单线程数值库。已保存的资产包含网格、区域样式、三维路径、面 ID 和重心锚点；冷加载渲染不需要访问原始 PLY。

## Edit and view

```bash
"$DEMO_PY" "$DEMO_CODE/demo.py" edit --scene chair \
  --asset "$DEMO_UNIT/assets/baseline" --region 2 \
  --angle 95 --spacing 0.06 --length 0.12 --width 1.8 \
  --output "$DEMO_UNIT/user_asset_001"

"$DEMO_PY" "$DEMO_CODE/demo.py" render --scene chair \
  --asset "$DEMO_UNIT/user_asset_001" --azimuth 47 --elevation 25 --distance 4.6 \
  --output "$DEMO_UNIT/user_edited_preview_001"

"$DEMO_PY" "$DEMO_CODE/viewer.py" \
  --asset "$DEMO_UNIT/assets/baseline" \
  --output "$DEMO_UNIT/user_browser_session_001" --port 8765
```

浏览器打开 `http://127.0.0.1:8765`。选择区域，调整角度、间距、长度或线宽，再按 **Render & save**。Orbit、Zoom 会重新渲染同一个三维资产；Hatching、Regions、Proxy 可切换图层；Download current asset 可导出当前编辑结果。浏览器界面的真实 HTTP 端点和六种操作已运行检查，未做浏览器截图或人工 UI 验收。服务器默认单请求串行运行，退出用 Ctrl+C。

`--region` / `--part`：1 下区域、2 中区域、3 上区域。`angle` 为切割平面角度，不是每处曲面的统一局部切向角。`spacing` 为世界空间平面间距，不是曲面测地间距；`length` 为路径最大弧长，遇孔洞或区域边界会提前停止；`width` 为屏幕像素宽度。

## Orbit and zoom

```bash
"$DEMO_PY" "$DEMO_CODE/demo.py" render --scene chair \
  --asset "$DEMO_UNIT/assets/edited" --trajectory orbit \
  --output "$DEMO_UNIT/user_orbit_001"

"$DEMO_PY" "$DEMO_CODE/demo.py" render --scene chair \
  --asset "$DEMO_UNIT/assets/edited" --trajectory zoom \
  --output "$DEMO_UNIT/user_zoom_001"
```

已有 `media/orbit.mkv` 和 `media/zoom.mkv` 分别为真实渲染的 12 / 6 帧，6 fps，完整无损解码检查通过。短轨迹只证明实际生成了不同相机的图像，不代表完整时序稳定认证，更不代表实时性能。

## Rebuild from the original model

以下单条入口会按冻结协议重新读取真实 PLY、渲染 24 个训练视角、提取代理、生成排线并输出第一幅图。原输入必须仍在记录的位置。

```bash
"$DEMO_PY" "$DEMO_CODE/demo.py" build --scene chair \
  --unit "$DEMO_UNIT" --output "$DEMO_UNIT/user_rebuild_001"
```

Open3D 的 legacy TSDF 在本环境返回空网格，原失败保存在 `logs/build_proxy.log`。交付代码改用 NumPy projective TSDF + skimage marching cubes，继续使用相同深度、相机、筛选条件和体素参数；没有为了通过测试更换模型。源码和失败版本均保留。

## Evidence and limits

- 第一幅真实模型图：`renders/first/frame_000_image.png`。
- 原图、代理、区域、排线四视角：`media/reference_proxy_regions_hatch.png`。
- 局部编辑：`media/local_edit_all_views.png`；非目标两个区域路径文件和渲染层精确不变。
- 所有弱视角：`media/orbit_all_frames.png`、`media/zoom_all_frames.png`。
- 数值与命令：`metrics/VALIDATION.json`、`metrics/VIEWER_SMOKE.json`、`logs/*.receipt.json`。
- 一处 front-view 像素在固定 2px 区域带之外有 0.2 灰度总变化，占该图编辑差异约 0.0056%；严格零残差检查保留为 partial，没有扩大带宽或修改图像来消除记录。

代理损失雕花、细框与部分薄结构，路径在噪声表面上起伏，椅腿排线偏稀，部分角度发生拥挤或留白。高度区域切过物理椅背与扶手，角度编辑可能形成不自然的空白。只验证了相对于本代理的附着；没有独立表面真值、全路径可见性认证、自动分部或 H1/H2 增益结论。

可搬移包位于 `units/unit_001/portable_demo.tar.gz`，含实际资产、源码和预览。解压后用 `DEMO_PY=... ./run.sh preview` 或 `./run.sh viewer`；保存资产演示不需要原模型、旧工作树或原始照片。依赖版本见包内 `requirements.txt`，环境未做安装或全局升级。
