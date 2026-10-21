# 完整 GT 台灯的支杆疏密 CLI

`density_cli.py` 给显式 selected458 资产增加支杆种子预算控制。本轮唯一视觉配置是密度 1→0.5：保留原 48 条短轴向支杆路径中的 24 条，灯罩 260 条、底座 150 条原样保留，结果为 434 条。密度不是最小几何间距，也不是 LOD。保留路径的三角面、重心坐标、ID 和墨色不变；不通过补偿墨色抵消稀疏化。

选择重放 `SeedSequence([1729,2])` 的原始面积采样种子，并核对种子属于原路径。先选字典序第一个种子，再逐次选择离已选集合最近距离最大的种子；距离为三维欧氏距离，平局取字典序。密度为原 48 种子的绝对比例，计数 `floor(48*density+0.5)`，每个低密度集合是高密度集合的前缀子集。API 范围 0–1；只对 0.5 进行本轮视觉评价，0 是负控制，不是可用画面。

以下为本轮实际使用的命令形式。每次运行须使用新的输出目录；本版写入范围严格限制在 unit009，历史单元和已有目录会被拒绝。封存后不应继续向该单元追加输出；后续单元应明确绑定新的授权输出位置。

```bash
PY=/mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_8build_part_prior_feasibility_v03/venv/bin/python
SCRIPT=experiments/partwise_sketch_hatching_v02/density_cli.py
ASSET=/mnt/hdd1/u00134/partwise_sketch_hatching_p1_v02/units/unit_008/outputs/baseline/asset.json
UNIT=/mnt/hdd1/u00134/partwise_sketch_hatching_p1_v02/units/unit_009
"$PY" -B "$SCRIPT" edit --asset "$ASSET" --part stem --density 0.5 --output "$UNIT/outputs/edited"
"$PY" -B "$SCRIPT" reselect --recipe "$UNIT/cold_request/recipe.json" --output "$UNIT/outputs/cold_reselect"
"$PY" -B "$SCRIPT" replay --bundle "$UNIT/outputs/edited" --output "$UNIT/outputs/cold_replay"
```

`edit` 接受原始 458 条路径；不能在已经稀疏的 434 条路径上连续删减。`recipe.json` 保存原始 458 路径、网格、配置的 SHA、选择器 SHA、NumPy 版本、完整种子次序、选中 ID、父资产与路径版本。`reselect` 在新进程从原始路径重新选取，没有读取选好的 434 路径缓存；这不是过程式曲线重生成。`replay` 则直接读取保存的结果路径。

输出包含完整资产、配置、原始来源路径、选择配方、四视角 PNG/分层数组/相机、实际耗时。`EDIT.json` 的首次预览时间包含导入、读取、校验、选择、保存和渲染；外部 `EXECUTION_*.json` 另记录解释器启动至结束的真实 wall time。不声称实时或 24 FPS。

所有结果均为 GT 网格、GT 部件、人工方向的工程诊断。完整视觉 P1、真实 RaDe-GS 输入和 H1/H2 的结论须按 unit009 STATUS 与实际审计读取，不能仅因配方可重放就宣布成功。
