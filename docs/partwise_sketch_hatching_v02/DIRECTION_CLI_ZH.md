本接口为明确命名的 unit003 selected458 台灯资产增加灯罩方向编辑。角度是相对手工周向场的绝对偏移，重复输入15°不会累加为30°。这次仅验证0→15°；接口限制在[-45°,45°]，并不表示其他角度已有质量认证。

260条灯罩路径由固定种子1729、长度0.32、步长0.015的配方确定性重生成。支杆48条、底座150条保存路径原样复用。旧配置的底座150代表种子，不能用它重生成当前底座子集。每个输出保存父资产和父路径SHA、目标前后几何版本、生成器SHA、显式recipe和完整资产包；目标seed ID不变，但路径版本会变化。

在授权工作树执行（已封存单元只读；示例目录在本单元封存前使用）：

```bash
TASK_PY=/mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_8build_part_prior_feasibility_v03/venv/bin/python
TASK_UNIT=/mnt/hdd1/u00134/partwise_sketch_hatching_p1_v02/units/unit_008
export CUDA_VISIBLE_DEVICES=''
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1
export PYTHONDONTWRITEBYTECODE=1
export TMPDIR=/mnt/hdd1/u00134/partwise_sketch_hatching_p1_v02/orchestration/scratch

taskset -c 0,1 "$TASK_PY" experiments/partwise_sketch_hatching_v02/direction_cli.py edit \
  --asset "$TASK_UNIT/inputs/asset.json" --part shade --angle-deg 15 \
  --output "$TASK_UNIT/outputs/user_direction"

taskset -c 0,1 "$TASK_PY" experiments/partwise_sketch_hatching_v02/direction_cli.py regenerate \
  --recipe "$TASK_UNIT/outputs/user_direction/recipe.json" \
  --output "$TASK_UNIT/outputs/user_regenerate"

taskset -c 0,1 "$TASK_PY" experiments/partwise_sketch_hatching_v02/direction_cli.py replay \
  --bundle "$TASK_UNIT/outputs/user_direction" \
  --output "$TASK_UNIT/outputs/user_replay"
```

默认产生512×512的30°、120°、210°、300°全灯预览；可用`--azimuths 30`只生成一幅。`preview --asset ...`显示保存路径；`regenerate --recipe ...`只读取recipe、mesh、retained198和config重新生成灯罩，不需要编辑后灯罩缓存；`replay`加载完整保存路径。实际冷生成使用独立`cold_request/`，其中不含任何目标路径NPZ。

输出目录必须位于当前授权unit008且不存在。`EDIT.json`记录包含加载、生成、保存和绘制的首次预览延迟；外层EXECUTION收据另包含解释器启动。离线预览不等于实时帧率。本实现没有把spacing/length/crossing开放为新的已验证操作，也不是全对象仅凭配置的程序化重生成。

这是GT几何、GT部件和手工方向的工程功能；原完整视觉NO_GO和遮挡／时序覆盖限制仍保留。unit004/005诊断预览没有借此升级，RGB重建、点击辅助标签及H1/H2仍未证明。未来单元须明确迁移输出授权根，不向已封存unit008追加运行。
