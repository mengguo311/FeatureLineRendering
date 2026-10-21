# 显式资产编辑 CLI（unit005）

本接口加载用户指定的资产，选择灯罩／支杆／底座，修改屏幕线宽，保存完整资产包并渲染预览。当前授权输出范围是 `unit_005` 下尚不存在的目录；已存在目录拒绝覆盖。

两份输入保留不同身份与历史判定：

| 输入清单 | 路径数 | 来源和判定 |
|---|---:|---|
| `inputs/unit003_baseline.asset.json` | 458 | unit003 底座清理基线；完整视觉仍 NO_GO |
| `inputs/unit004_diagnostic_preview.asset.json` | 418 | unit004 三风格诊断预览；支杆可读性 GO，冻结密度契约 NO_GO |

这些是人工 GT 台灯、人工部件和方向，尚非 RGB 重建结果。清单含网格、重心路径、配置的 SHA256，以及原始 provenance 和 verdict_metadata。保存路径是权威输入；继承配置中的旧生成数量不能用来重建当前子集。本接口只提供 `--width`，不调用旧生成器。路径、ID、部件与墨量保持原样，局部改动仅作用于所选部件线宽。

在授权 worktree 中执行。以下输出目录为新的使用示例，实验实际命令及返回码见 unit005 的 `EXECUTION_*.json`：

```bash
TASK_PY=/mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_8build_part_prior_feasibility_v03/venv/bin/python
TASK_UNIT=/mnt/hdd1/u00134/partwise_sketch_hatching_p1_v02/units/unit_005
export CUDA_VISIBLE_DEVICES=''
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1
export PYTHONDONTWRITEBYTECODE=1
export TMPDIR=/mnt/hdd1/u00134/partwise_sketch_hatching_p1_v02/orchestration/scratch

taskset -c 0,1 "$TASK_PY" experiments/partwise_sketch_hatching_v02/asset_cli.py preview \
  --asset "$TASK_UNIT/inputs/unit004_diagnostic_preview.asset.json" \
  --output "$TASK_UNIT/outputs/user_preview"

taskset -c 0,1 "$TASK_PY" experiments/partwise_sketch_hatching_v02/asset_cli.py edit \
  --asset "$TASK_UNIT/inputs/unit004_diagnostic_preview.asset.json" \
  --part shade --width 1.5 --output "$TASK_UNIT/outputs/user_edit"

taskset -c 0,1 "$TASK_PY" experiments/partwise_sketch_hatching_v02/asset_cli.py replay \
  --bundle "$TASK_UNIT/outputs/user_edit" --output "$TASK_UNIT/outputs/user_replay"
```

部件名称为 `shade`、`stem`、`base`。线宽是像素直径，接口接受有限正数至 64px；这个输入上限并非质量认证。本轮仅验证灯罩 1.0→1.5px。默认渲染 30°、120°、210°、300° 四个方位，可用 `--azimuths 30` 输出一个预览。相机固定仰角20°、距离4.5，继承512×512配置。

每个输出包包含 `asset.json`、`mesh.npz`、`strokes.npz`、`config.json`、`EDIT.json` 和 `renders/`。包内清单使用相对路径，可作为下一次显式输入。`replay` 在新进程中加载保存后的配置，不会重新应用编辑，也不重新生成路径。异常时保留已产生的文件及 `FAILURE.json`，再次运行需选择新目录。

`EDIT.json` 报告加载、保存和实际渲染所需时间；首次预览计时从 Python 模块入口开始，解释器启动另由实验的外层执行收据覆盖。离线预览和视频不代表实时 FPS。保存编辑不会改变源资产的质量判定；unit004 密度失败始终保留。

已封存实验目录应继续只读。后续授权单元需显式迁移 CLI 的输出授权根并重新记录执行，不能直接向历史 unit005 增写实验结果。
