# 复现 / 查看

推荐直接打开 [INDEX.html](INDEX.html)，或在Blender等独立工具导入 `assets/{lego,chair}/fused/tubes.glb`。原3DGS世界坐标、Z-up；线模型不包含原物体表面/贴图。GLB/OBJ中的tube为实体三角面，centerlines.obj的`l`元素为1D中心线。有些OBJ导入器忽略`l`，因此另提供实体tube OBJ。离线viewer无网络依赖，可切换三臂和24份源线；切换对照不修改任何资产。

## 环境与保护

工作树 `/home/u00134/3dgs_line/gaer_multiview_contour_lift_v01`，分支 `gaer-multiview-contour-lift-v01`。
Python `/home/u00134/bin/miniconda3/envs/vfsdgs/bin/python`。使用现有numpy/scipy/cv2/PIL/plyfile/trimesh/imageio_ffmpeg、g++、node，**不安装**。保留继承`.codex/config.toml` gpt-6-astra/ultra。CPU-only、2线程；不运行launch.sh启动第二个Codex，不等待/抢占GPU，不读凭据。

所有写入只在当前stage的experiments/artifacts/out；缓存和临时文件仅out。root空闲≥4GiB、共享Git空闲≥1.5GiB、stage总量<4GiB；稀疏贡献申请保留1GiB守卫。原PLY/metadata及历史文件只读，路径与SHA见INPUT_FREEZE。缺少历史sealed RGB/alpha缓存时本脚本拒绝，而不是写回旧tree重建；须在新stage显式另做重建审计。

## 验证现有交付（先做）

```bash
cd /home/u00134/3dgs_line/gaer_multiview_contour_lift_v01
source experiments/gaer_multiview_contour_lift_v01/env.sh
"$PYTHON" experiments/gaer_multiview_contour_lift_v01/test_tracers.py
"$PYTHON" experiments/gaer_multiview_contour_lift_v01/test_extended.py
"$PYTHON" experiments/gaer_multiview_contour_lift_v01/audit.py
```

audit会重新写本stage的审计JSON/resource日志，但不会改动sealed geometry；若只想检查提交clean，勿在交付后重新运行有写入的审计。来源、GLB/OBJ/PLY/JSON、全部seal、保护文件和旧branch均核对。当前sample管线只支持冻结居中对称内参；独立core射线/三角化测试覆盖非居中/skew full-K。

## 原生产顺序 / verified-skip

```bash
"$PYTHON" experiments/gaer_multiview_contour_lift_v01/freeze.py
"$PYTHON" experiments/gaer_multiview_contour_lift_v01/pipeline.py build
"$PYTHON" experiments/gaer_multiview_contour_lift_v01/pipeline.py eval
"$PYTHON" experiments/gaer_multiview_contour_lift_v01/width_audit.py
"$PYTHON" experiments/gaer_multiview_contour_lift_v01/pipeline.py video
"$PYTHON" experiments/gaer_multiview_contour_lift_v01/supplement.py
"$PYTHON" experiments/gaer_multiview_contour_lift_v01/width_tails.py
"$PYTHON" experiments/gaer_multiview_contour_lift_v01/report.py
"$PYTHON" experiments/gaer_multiview_contour_lift_v01/audit.py --protection-only
```

每阶段atomic seal绑定文件及producer code。完整stage已存在时verified-skip；任何hash不符即拒绝覆盖。不要删除seal让旧结果被静默重算，不要单独调用绕过source/fusion依赖的内部函数。CLI可用`--scene lego`或`--scene chair`恢复；每个大stage分别捕获scene异常，因此第一scene评价失败不阻塞第二scene构建。实际执行日志保留在logs，测试日志在tdd。真实RED/扩展测试时序见EXECUTION_NOTES_ZH，不能把后补测试伪称事前完成。

从零重跑必须在授权的新stage整体迁移路径，不能覆盖当前历史负结果；这里的命令以本交付已经存在的verified-skip为默认。旧缓存绑定通过真实file_path/camera hash及old seal链，r_33不是metadata index33。

## 数据索引

- `sources/{scene}/{camera}.npz/.json`：有序像素、outer/hole类别、原链ID、xyz、edge、条件中心z proxy的q10/median/q90/mean/mass、accepted CSR原核IDs/αT/中心z、相机/hash及断边拒绝。
- `fusion/{scene}/fused.npz/.json`：控制点、连接、raw→cluster、所有匹配/拒绝/三角化、逐source位移及重投影、未合并源节点、每个输出node/edge多来源。
- `assets/{scene}/{single,rawunion,fused,sources/*}`：GLB、实体OBJ、中心线OBJ/NPZ、PLY、JSON路径与radius。rawunion保存全部24份源图，未根据heldout删线。
- `SOURCE_INDEX.json` + `PROVENANCE_NAMESPACES.json`：global node offsets和global edge offsets、局部edge命名空间。先按这些表解释来源，不能把single局部edge ID直接当rawunion全局edge ID。
- `original_kernel_support.ply`：参与源采样的原核中心/原ID；它们是支撑证据，不是输出曲线表面点或法线。
- `media/{scene}/reserved/{camera}`：全部800px图和edgezoom；FULL板每tile保留800px。所有三臂线图都是真实tube raster，不是二维屏幕画线。
- `media/{scene}/arc`：全部33帧、H264 yuv420p/faststart、full-decode manifest、camera/geometry hashes。编码fps=6，不插帧、不丢失败帧；这只是较短历史弧段。
- `results/*WIDTH*/*EDGE*/*contract_audit*`：完整宽尾、源边一致性与导出检查。candidate-isolated profile允许同path折返残留，不能充作严格独立stroke宽度；WIDTH_TAILS单独raster同一管线解释该差异，未改资产。

## 解释限制

depth始终是Gaussian中心贡献proxy；没有surface depth GT。rolling silhouette不同位置不能都强合为固定线。当前local-track符号投票不等于严格monotonic，端点多源不等于整edge多源，融合后短边可能变向/伸长。报告保留这些实际失败，不能把数学/工程测试PASS当视觉GO。内部RGB detail未实现。

最终提交/push/remote readback/clean及推荐路径在ignored `out/gaer_multiview_contour_lift_v01/DELIVERY.json`，由push后生成，避免tracked报告自引用commit。
