# unit_001 复现与执行记录

本文件记录冻结实现的实际命令及输出语义。**以下 producer 命令是历史命令说明，不能在已封存的 `unit_001` 上重跑。** 当前 `common.py` 的 `OUT` 是硬编码路径；runner 的部分阶段会覆盖输出，只有 `receipt.py` 对同名日志存在拒绝覆盖检查。新的完整重放必须使用新 unit／隔离源码副本，先映射新 `OUT`、冻结相同科学参数并建立新来源锁；不得改写原 `SOURCE_LOCK.json`、原协议、历史源文件或任何旧封存结果。数据只读校验与重新生产应分别记录。

## 版本、目录与输入

- 授权分支：`partwise-sketch-hatching-p1-v02`。
- 工作目录：`/home/u00134/3dgs_line/partwise_sketch_hatching_p1_v02`。
- 协议提交：`7dff4ce4`；实现提交：`cb1ea0b381d042138e8a76b6f9780a2f3a67f25d`；来源锁提交：`7ee407e8`。
- 本轮输出根目录：`/mnt/hdd1/u00134/partwise_sketch_hatching_p1_v02/units/unit_001`。
- 冻结协议：输出根目录 `PROTOCOL.json`，SHA256 `12b052ff14a14697de12a1d68149660defc499a585d7f234d83307b1842b163f`；仓库副本 `docs/partwise_sketch_hatching_v02/PROTOCOL_unit001.json`。
- 冻结来源锁：输出根目录 `SOURCE_LOCK.json`，仓库副本 `docs/partwise_sketch_hatching_v02/SOURCE_LOCK_unit001.json`。`run_unit.py` 每阶段进入时对该锁列出的绝对路径文件逐一校验 SHA256。
- 原始源码副本：输出根目录 `source_snapshot/`；它是来源锁覆盖的 `.py`／`.md` 快照，不是独立可直接运行的完整安装。

只读输入来自 `/mnt/hdd1/u00134/partwise_sketch_hatching_p0p1_v01/rounds/round_002/`，复制到本轮 `inputs/`，没有运行旧 producer：

| 输入 | SHA256 |
|---|---|
| `assets/lamp_mesh.npz` → `inputs/lamp_mesh.npz` | `f8de0de7f1b8199dd3a8e3c1045dddaebc1a71a9419d8625665c17ce869a9d08` |
| `strokes/mixed.npz` → `inputs/mixed.npz` | `ec8a1a3f69e7854751621e77dabd4fcb395f3d042fea403cf9b7227502292f45` |
| `strokes/mixed_shade_edit35.npz` → `inputs/mixed_shade_edit35.npz` | `6268330bd4ad669bf36d8d02400cd3dafa3feb56c24ec85b60e48be18533344c` |

程序实际读取旧 `round_001/PROTOCOL.json` 的资产／风格基础设置，由 `common.load_inputs()` 固定为 512×512、2× 超采样、1 px 三部件基准线宽、0.8 px 轮廓及 0.65 px 结构线。新协议记录本轮编辑与评价约束。输入是人工 GT 台灯与人工部件／方向，不能当作真实 RaDe-GS 重建。

## CPU 环境与命令

解释器只读复用已有环境，不安装或升级共享依赖：

```bash
cd /home/u00134/3dgs_line/partwise_sketch_hatching_p1_v02
p1_python=/mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_8build_part_prior_feasibility_v03/venv/bin/python
export CUDA_VISIBLE_DEVICES=''
export OMP_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
export MKL_NUM_THREADS=1
export NUMEXPR_NUM_THREADS=1
export PYTHONDONTWRITEBYTECODE=1
export TMPDIR=/mnt/hdd1/u00134/partwise_sketch_hatching_p1_v02/orchestration/scratch
```

`common.py` 在 NumPy 导入前再次设置这些限制，并执行 `os.sched_setaffinity(0, [0,1])`；每个子进程继承限制。`receipt.py` 将 stdout/stderr 合并写入 `runtime/<name>.log`，以 590 s 超时串行执行子命令，保存原返回码、日志 SHA 和资源记录到 `EXECUTION_<name>.json`。不得并行启动这些计算阶段。root 空间下限 1 GiB、HDD 下限 10 GiB、本轮输出上限 20 GiB；全程不使用 GPU。

实际包装方式如下。每条命令均需等待上一条结束，且属于前述不可覆盖的历史执行记录：

```bash
"$p1_python" experiments/partwise_sketch_hatching_v02/receipt.py prepare "$p1_python" experiments/partwise_sketch_hatching_v02/prepare.py
"$p1_python" experiments/partwise_sketch_hatching_v02/receipt.py lock "$p1_python" experiments/partwise_sketch_hatching_v02/lock_sources.py
"$p1_python" experiments/partwise_sketch_hatching_v02/receipt.py tests_old "$p1_python" experiments/partwise_sketch_hatching_v02/test_renderer.py --backend old
"$p1_python" experiments/partwise_sketch_hatching_v02/receipt.py tests_new "$p1_python" experiments/partwise_sketch_hatching_v02/test_renderer.py --backend new
"$p1_python" experiments/partwise_sketch_hatching_v02/receipt.py assets "$p1_python" experiments/partwise_sketch_hatching_v02/run_unit.py assets
"$p1_python" experiments/partwise_sketch_hatching_v02/receipt.py stills "$p1_python" experiments/partwise_sketch_hatching_v02/run_unit.py stills
"$p1_python" experiments/partwise_sketch_hatching_v02/receipt.py orbit "$p1_python" experiments/partwise_sketch_hatching_v02/run_unit.py orbit
"$p1_python" experiments/partwise_sketch_hatching_v02/receipt.py zoom "$p1_python" experiments/partwise_sketch_hatching_v02/run_unit.py zoom
"$p1_python" experiments/partwise_sketch_hatching_v02/receipt.py edit "$p1_python" experiments/partwise_sketch_hatching_v02/run_unit.py edit
"$p1_python" experiments/partwise_sketch_hatching_v02/receipt.py probes "$p1_python" experiments/partwise_sketch_hatching_v02/run_unit.py probes
```

该列表给出各阶段冻结入口，不表示所有阶段此刻均已完成；最终执行事实以对应收据、最终 STATUS 与单独验证结果为准。`prepare.py` 和 `lock_sources.py` 分别要求当前协议／来源锁尚不存在。prepare 在协议提交之前执行；来源锁在实现提交之后、评测之前建立。

## 各阶段产物和验证含义

| 阶段 | 产物及实际计算 |
|---|---|
| `assets` | 确定性重新生成全部 mixed 笔触，重新生成灯罩 +35° 编辑；对照历史 digest；保存 `ASSET_VALIDATION.json`、`inputs/cold_regenerated.npz`、`inputs/angle_edited.npz` |
| `stills` | 四个方位 30°/120°/210°/300°，基准／角度／宽度 2 px／旧后端比较；独立解析部件掩码、实际量化 PNG 的非零目标与泄漏控制；`EDIT_METRICS.json`、`stills/`、全灯对比和原分辨率部件裁切 |
| `orbit` | 36 帧，方位 `10*i`，距离 4.5；固定三维路径逐帧投影 |
| `zoom` | 24 帧，方位 30°，距离 `4.8 - 0.8*cos(2*pi*i/23)`；相同场景键可复用已计算图像，轨迹记录 `reused_identical_scene` |
| `edit` | 24 帧，前 12 帧基准、后 12 帧真实灯罩 +35° 配置；两个固定场景各实际渲染一次，其余重复帧明确标为复用，不是 24 次重生成 |
| `probes` | 九个预定 ID、12 个 30° 间隔视角、每笔触 41 个固定弧长位置；保留实际孤立 hatch PNG、解析深度与标签、缺失／位置统计、3 px 位移及完全删墨控制；`TEMPORAL_PROBES.json`、`PROBE_PARTIAL.json`、`probes/` |

每个视频阶段保存 `frames/<name>/`、`TRAJECTORY_<name>.json`、`PARTIAL_<name>.json`、全部帧接触表和首／中／末帧原分辨率拼图。`render_seconds=0` 表示复用了相同场景结果，不能当作真实渲染速度样本。

探针指标测量选定笔触实际量化输出的法向位置及缺失，独立解析深度在像素中心计算后进行双线性采样。相同部件的深度突变可能混合表面分支；隐藏点的孤立墨迹也可能来自同一笔触另一段。41 点包含端点，跨帧汇总是观察数量而非可见弧长比例。相邻探针差只作描述，30° 间隔不是完整视频的连续帧评价，不扩展为整物体时序稳定结论。

## FFmpeg 命令与全帧解码

只读二进制为 `/home/u00134/3dgs_line/partwise_sketch_hatching_p0p1_v01/.runtime_p0/imageio_ffmpeg/binaries/ffmpeg-linux-x86_64-v7.0.2`，SHA256 `e7e7fb30477f717e6f55f9180a70386c62677ef8a4d4d1a5d948f4098aa3eb99`。每种视频采用 12 FPS、FFV1 无损 MKV。以下为 runner 自动调用的同构命令，仍不得用于覆盖封存视频：

```bash
p1_ffmpeg=/home/u00134/3dgs_line/partwise_sketch_hatching_p0p1_v01/.runtime_p0/imageio_ffmpeg/binaries/ffmpeg-linux-x86_64-v7.0.2
p1_output=/mnt/hdd1/u00134/partwise_sketch_hatching_p1_v02/units/unit_001
p1_sequence=orbit
"$p1_ffmpeg" -v error -y -threads 1 -filter_threads 1 -framerate 12 -i "$p1_output/frames/$p1_sequence/%04d.png" -c:v ffv1 -level 3 -threads 1 -pix_fmt bgr0 "$p1_output/videos/$p1_sequence.mkv"
"$p1_ffmpeg" -v error -threads 1 -i "$p1_output/videos/$p1_sequence.mkv" -f rawvideo -pix_fmt rgb24 -threads 1 -
```

最后一条 rawvideo stdout 由 Python 捕获为内存字节，实际没有输出到终端。完整字节数须等于 `frames*512*512*3`，逐帧 RGB 与对应输入 PNG 严格比较，并保存每帧 SHA256、编码／解码原返回码到 `VIDEO_<name>.json`。这验证媒体完整性；视频稳定和画面质量需另外检查。

## 原始失败和当前可证实结果

- `tests_old`：rc=1，六项测试中两项失败、四项通过。失败分别为异部件和同部件前景遮挡，旧宽度扩张把后方墨迹带进前景内部，最大泄漏墨量均 `0.8549019607843137`。这是实际旧后端对冻结新契约的 RED。
- `tests_new`：相同六项测试全部通过，rc=0；测试源码 SHA256 `06a22d29ef48db9ab199c916dd32ed43e806076c59c0a4f5aabce0166f85f121`。
- `assets`：rc=0，wall `9.695019100792706 s`；原始收据为 `EXECUTION_assets.json`。
- `stills`：包装器被观察到的返回码为 **143**；**科学子进程返回码 UNKNOWN**。科学 stdout 显示 `all_gates true`，完整输出存在，但包装器最终收据缺失；事实保存在 `EXECUTION_stills_INTERRUPTED.json`。不得补写原子进程 rc=0，也不能把外层中断误记为科学 NO_GO。独立验证可以确认输出，不会恢复丢失的退出码。
- 初始非科学设置失败（未限定路径的 `python` 不存在、当前 worktree 没有 `.runtime_p0`）保存在 `SETUP_NOTES.json`，之后使用指定解释器和历史只读 ffmpeg。

独立 validator 在实现提交 `b77d35ab`、来源锁提交 `9c1c81fc` 后实际执行，rc=0、42.094秒，七组复核全部通过。`VALIDATION_LOCK.json` 单独绑定该后验校验器，没有改动原生产来源锁。原始收据是 `EXECUTION_validation.json`，详细结果是 `INDEPENDENT_VALIDATION.json`；它是工件一致性复核，最终 producer seal 不等同于独立科学验证。

实际执行命令如下；它们是此次命令记录，不得直接覆盖封存目录：

```bash
PYTHONDONTWRITEBYTECODE=1 CUDA_VISIBLE_DEVICES='' OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 taskset -c 0,1 "$p1_python" experiments/partwise_sketch_hatching_v02/receipt.py validation "$p1_python" experiments/partwise_sketch_hatching_v02/validate_outputs.py
PYTHONDONTWRITEBYTECODE=1 CUDA_VISIBLE_DEVICES='' OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 taskset -c 0,1 "$p1_python" experiments/partwise_sketch_hatching_v02/receipt.py cli_angle "$p1_python" experiments/partwise_sketch_hatching_v02/edit_asset.py --part 1 --angle 35 --output /mnt/hdd1/u00134/partwise_sketch_hatching_p1_v02/units/unit_001/cli/angle35
PYTHONDONTWRITEBYTECODE=1 CUDA_VISIBLE_DEVICES='' OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 taskset -c 0,1 "$p1_python" experiments/partwise_sketch_hatching_v02/receipt.py cli_width "$p1_python" experiments/partwise_sketch_hatching_v02/edit_asset.py --part 1 --width 2 --output /mnt/hdd1/u00134/partwise_sketch_hatching_p1_v02/units/unit_001/cli/width2
```

两个 CLI 的完整输出图分别与冻结角度／宽度静帧逐像素一致。实际命令执行顺序为 cli_angle、cli_width、validation。三视频84帧完成全量解码；最终视觉仍为 NO_GO，见报告与 `VISUAL_REVIEW.json`。

## 新目录重放原则

隔离重放应复制冻结源码与输入到新授权位置，仅重映射输出路径及对应来源锁路径，明确保存差异。保留全部科学参数、旧失败证据、测试源码、随机种子、相机、编辑、2 px 边界带和阈值；新冻结记录应注明继承自 unit_001，而非创建未曝光测试。`common.OUT`、`prepare.py` 的 unit 标识和绝对路径锁均须与新目录一致。按上面的顺序串行运行，用新收据保留所有原始退出码。只对固定科学数组／图像作数值重放比较，UTC 时间、运行时长和新绝对路径不要求逐字节相同。
