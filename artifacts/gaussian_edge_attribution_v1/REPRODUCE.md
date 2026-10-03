# 复现与恢复运行

这是已冻结的 Gaussian 边缘贡献归因实验，不执行重训、几何曲线拟合、mesh/TEST 读取、人工标注或全局安装。目标产物是固定原 ID 资产及其全模型可见贡献投影。详细字段和编辑副本方法见 [ASSET_SCHEMA_ZH.md](ASSET_SCHEMA_ZH.md)，冻结统计范围见 [PROTOCOL.md](PROTOCOL.md)。

## 环境和一次性冻结

授权工作区为 `/mnt/hdd1/u00134/hybrid_raster_trained_models_v1/gaussian_edge_attribution_v1`，分支 `gaussian-edge-attribution-v1`，起始 SHA `d5c6d4d114b6b80ec5edb9c1717111e89a191eda`。它的 git common dir 必须是 `/mnt/hdd1/u00134/hybrid_raster_trained_models_v1/mic_fixed3d_standalone/.git`，无 objects alternates 或 `GIT_ALTERNATE_OBJECT_DIRECTORIES`。保护根 Git 的校验快照保存在 `INPUTS_FROZEN.json.root_git_control_snapshot`；只读审计不得写入该根仓库。常规提交产生的新 HEAD 与起始 SHA 不同是正常的，不能重跑一次性冻结脚本来伪造新起点。

主解释器固定为 `/home/u00134/bin/miniconda3/envs/vfsdgs/bin/python`。依赖来自既有环境：NumPy、SciPy、PyTorch、Pillow、OpenCV、plyfile、imageio-ffmpeg；CUDA 与历史 native 构建从已记录位置只读加载。无 `pip install`、`conda install`、系统包安装或 global Git 配置操作。

```bash
cd /mnt/hdd1/u00134/hybrid_raster_trained_models_v1/gaussian_edge_attribution_v1
export PYTHONDONTWRITEBYTECODE=1
export OMP_NUM_THREADS=4
export OPENBLAS_NUM_THREADS=1
export MKL_NUM_THREADS=1
mkdir -p out/gaussian_edge_attribution_v1/runtime_tmp out/gaussian_edge_attribution_v1/runtime_cache out/gaussian_edge_attribution_v1/torch_extensions
export TMPDIR="$PWD/out/gaussian_edge_attribution_v1/runtime_tmp"
export XDG_CACHE_HOME="$PWD/out/gaussian_edge_attribution_v1/runtime_cache"
export TORCH_EXTENSIONS_DIR="$PWD/out/gaussian_edge_attribution_v1/torch_extensions"
```

每次预计写入前确认可用磁盘严格大于 `1 GiB + 本阶段预计负载`。冻结时总预计负载 20 GiB，fit 的保守阶段负载 3 GiB，project 6 GiB；native build 另采用 2 GiB 预留与 2 GiB 负载。产物、临时文件、复制构建均限本工作区。外部 transport、checkpoint、数据、历史 native build 和其他 worktree 保持只读。

当前实验已有 `INPUTS_FROZEN.json` 与 `PROTOCOL_SEAL.json`，**不要覆盖或重新运行 `freeze.py`**。后者只适用于同一授权新实验在尚未冻结、尚未读取像素时的一次性起始操作，而且检查起始 HEAD。当前 seal 包含配置、协议和 98 个输入文件/相机来源记录，驱动每阶段验证它。

可以只读验证冻结文件，不加载像素：

```bash
/home/u00134/bin/miniconda3/envs/vfsdgs/bin/python -B - <<'PY'
import sys
sys.path.insert(0, 'artifacts/gaussian_edge_attribution_v1/code')
from run_experiment import validate_protocol
validate_protocol()
print('protocol/input byte hashes verified')
PY
```

## 先运行 CPU 合成测试

此处不读取真实场景数组，不启动 GPU。RED、修复 RED 和 GREEN 历史日志位于 `artifacts/gaussian_edge_attribution_v1/logs/`；不覆盖这些历史记录。

```bash
CUDA_VISIBLE_DEVICES='' /home/u00134/bin/miniconda3/envs/vfsdgs/bin/python -B -m unittest discover -s artifacts/gaussian_edge_attribution_v1/tests -p test_core.py -v
CUDA_VISIBLE_DEVICES='' /home/u00134/bin/miniconda3/envs/vfsdgs/bin/python -B -m unittest discover -s artifacts/gaussian_edge_attribution_v1/code -p tests_verify.py -v
CUDA_VISIBLE_DEVICES='' /home/u00134/bin/miniconda3/envs/vfsdgs/bin/python -B -m unittest tests.test_hybrid_raster_evidence tests.test_raster_state -v
```

## Mic：F 归因、全遍历投影、媒体、资产导出

按顺序执行尚未完成的阶段；不要并发启动 GPU 阶段。`fit` 仅访问 F，它先用 Mic F 建立全局证据尺度，再计算八 F 与 F1、固定平移 null、匹配随机对照。平移固定 `dy=37, dx=53`，越界补零，仅一次、不搜索。

```bash
CUDA_VISIBLE_DEVICES='' /home/u00134/bin/miniconda3/envs/vfsdgs/bin/python -B artifacts/gaussian_edge_attribution_v1/code/run_experiment.py fit mic
CUDA_VISIBLE_DEVICES=0 /home/u00134/bin/miniconda3/envs/vfsdgs/bin/python -B artifacts/gaussian_edge_attribution_v1/code/run_experiment.py project mic
CUDA_VISIBLE_DEVICES='' /home/u00134/bin/miniconda3/envs/vfsdgs/bin/python -B artifacts/gaussian_edge_attribution_v1/code/run_experiment.py media mic
CUDA_VISIBLE_DEVICES='' /home/u00134/bin/miniconda3/envs/vfsdgs/bin/python -B artifacts/gaussian_edge_attribution_v1/code/run_experiment.py export mic
```

上例设备 0 必须与实际授权、空闲设备相符。每次 native 调用前 `native_attributes.gpu_guard` 查询设备 UUID、PID、进程所有者；任何不是当前进程的 GPU compute PID（包括同一用户其他作业）都会阻止启动。guard 写 `GPU_GUARD.jsonl`，实际同步 CUDA 时间写 `RENDER_TIMES.jsonl`。不要通过停止外来进程、并发另一渲染或修改 guard 来绕过。总预算为 GPU 4 小时、wall 6 小时。

`project` 使用完整模型和原相机、黑背景属性颜色，计算原始 alpha*T 加权 P/Q；所有 Gaussian 都保留以维持透射率。分数训练仍为 TOP4-TRUNCATED。前八 F 的 P 确定 Mic 显示增益并封存后，才读取 C/arc 当前证据；C/arc 当前证据只做比较和评价。原缓存 recipe 是 native800、SH0、白背景、kernel_size=0、冻结 30k/seed1729；不能把该 RGB 校准描述成高阶 SH 视角依赖外观的复现。

`media` 为全部 49 姿态生成完整五列图、类别/四档图与 matched controls；编码完整 arc33 native 与 Telegram1600 的 H264/yuv420p/faststart 视频，并实际解码、记录每帧散列。`export` 保存原 vertex properties 未改的 PLY 子集及 ID sidecar，紧凑资产与摘要；subset 单独渲染会改变遮挡。

## 有界 Materials 压力场景

仅在 Mic 工程有效后运行；不以 Mic 视觉好坏为选择条件。Materials 使用自己的八 F、自己的 checkpoint ID 命名空间，算法、参数、Mic F 全局证据尺度和显示增益不变，不扩展其他场景。

```bash
CUDA_VISIBLE_DEVICES='' /home/u00134/bin/miniconda3/envs/vfsdgs/bin/python -B artifacts/gaussian_edge_attribution_v1/code/run_experiment.py fit materials
CUDA_VISIBLE_DEVICES=0 /home/u00134/bin/miniconda3/envs/vfsdgs/bin/python -B artifacts/gaussian_edge_attribution_v1/code/run_experiment.py project materials
CUDA_VISIBLE_DEVICES='' /home/u00134/bin/miniconda3/envs/vfsdgs/bin/python -B artifacts/gaussian_edge_attribution_v1/code/run_experiment.py media materials
CUDA_VISIBLE_DEVICES='' /home/u00134/bin/miniconda3/envs/vfsdgs/bin/python -B artifacts/gaussian_edge_attribution_v1/code/run_experiment.py export materials
```

目标每场景 F8+C8+arc33=49 面板，两场景共 98。实际完成计数以输出 audit／最终 JSON 为准，不因请求数而填充或复制帧。历史训练已见全部 TRAIN 视图，包括 C；这里 C 仅表示本次归因未使用，不能称盲测或 TEST。

## 可选、有界 top32 贡献完整性工程复现

本轮仅允许 Mic 固定 F1、F41；完整800网格导出 top32，随后从相同遍历取 top4/16 前缀，用相同 Mic F 尺度重新计算两 F 的截断分数和档位。该结果单独保存，不能修改主八 F 资产。最多 3 个工程修复回合、90 分钟，不因结果不理想继续扩大 K。

以下是脚本的真实入口。已有 `BUILD_TOP32.json`、校准和审计产物时先只读检查其 SHA；不要为恢复运行覆盖既有构建或校准产物。新复制构建仅写 `native_extension/`，不会修改历史 build；build_ext 不执行 install。

```bash
/home/u00134/bin/miniconda3/envs/vfsdgs/bin/python -B native_extension/build_top32.py
PYTHONDONTWRITEBYTECODE=1 CUDA_VISIBLE_DEVICES=0 XDG_CACHE_HOME="$PWD/native_extension/cache" strace -f -e trace=openat,creat,rename,unlink,mkdir -o native_extension/calibration_file_trace.log /home/u00134/bin/miniconda3/envs/vfsdgs/bin/python -B native_extension/calibrate.py > native_extension/calibration_stdout.log 2>&1
PYTHONDONTWRITEBYTECODE=1 CUDA_VISIBLE_DEVICES='' OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 /home/u00134/bin/miniconda3/envs/vfsdgs/bin/python -B native_extension/completeness.py --normalization out/gaussian_edge_attribution_v1/mic/NORMALIZATION.json > native_extension/completeness_stdout.log 2>&1
```

build 脚本设置局部 `TMPDIR`、`XDG_CACHE_HOME`、`TORCH_EXTENSIONS_DIR`，CUDA_HOME 为既有 `/usr/local/cuda`，架构 `8.6`、MAX_JOBS=2。它核验历史 source manifest，只扩展 topK 槽位及相关循环容量。运行它前也应确认资源空闲；calibrate 的每次 native 调用受相同 GPU guard 保护。GPU 校准与主 project 必须串行。

`strace` 记录的是这次校准进程的文件调用范围，不是整个会话的全系统读取审计。`calibrate.py` 同时固定校验本轮协议 seal `171c0b88f4eb8276bbbb97a2e025c68e4f40df81f9535bd722ef86107c000edf`；seal 不同不能删掉此检查继续运行。

校准比较原 RGB/alpha/depth 与历史缓存，并验证全 1 属性等于原 alpha、top32 前四槽等于原 top4。top32 遗漏仍单独报告，不能据此称所有贡献均已导出。审计包含固定 stride16、offset(4,4) 网格，以及独立边缘/非边缘分层；其两 F 排名稳定性不等于八 F 完整性证明。工程失败时完整归因仍为 UNDETERMINED，不否定可交付的 top4 便宜实验。

归一化 JSON 的数据在顶层 `normalization` 字段内，其字节 SHA 位于同目录 `NORMALIZATION_SEAL.json`。脚本支持此包装格式：

```text
out/gaussian_edge_attribution_v1/mic/NORMALIZATION.json
native_extension/F_001_top32.npz
native_extension/F_041_top32.npz
native_extension/completeness_twoF_scores.npz
artifacts/gaussian_edge_attribution_v1/research/NATIVE_CALIBRATION.json
artifacts/gaussian_edge_attribution_v1/research/COMPLETENESS_AUDIT.json
```

## 恢复、独立验证与主要产物

`STATUS.json` 原子更新。NPZ 先写 `.partial.npz` 再原子替换；partial 文件不是有效封存结果。

- fit：若有效 `assets/ASSET_SEAL.json` 已存在则核验、确认 core SHA 不变并跳过；若未形成最终资产封条则重做 F 归因，不把半成品视为完成。
- normalization：恢复时核验 core SHA 与 `NORMALIZATION_SEAL.json`，Materials 只能继承已有 Mic F 尺度。
- project：仅跳过有有效 `frames/{pose}/SEAL.json` 且相同资产 seal 的帧；源 raw SHA、相机身份、F-only 显示封条继续校验。完成后写 `PROJECTION_COMPLETE.json`。
- media/export：这些入口会重写派生产物；已经最终封存的交付优先审计读取，不要当成恢复计算的必要步骤。若确需变更，建立新派生输出命名空间并记录原因，不能覆盖最终研究资产或协议。
- 任意封条、代码或输入散列不匹配应停止并保存错误；不得手工刷新 seal 来掩盖改变。工程修复记录应说明原因及影响阶段，不得根据 C/arc 结果修改统计定义或选档。

在 F 资产封存后可先做独立 F 算术检查；完整面板完成后运行全部输出检查：

```bash
CUDA_VISIBLE_DEVICES='' /home/u00134/bin/miniconda3/envs/vfsdgs/bin/python -B artifacts/gaussian_edge_attribution_v1/code/audit_outputs.py mic --f-only
CUDA_VISIBLE_DEVICES='' /home/u00134/bin/miniconda3/envs/vfsdgs/bin/python -B artifacts/gaussian_edge_attribution_v1/code/audit_outputs.py mic
CUDA_VISIBLE_DEVICES='' /home/u00134/bin/miniconda3/envs/vfsdgs/bin/python -B artifacts/gaussian_edge_attribution_v1/code/audit_outputs.py materials
```

该独立 CPU 审计从源 F 对随机原 ID 重新求和全网格分子/分母，并对 C 的固定随机像素和强贡献像素重新计算 top4 P/Q；它还检查 full≥top4 的非负贡献界、49 相机/面板、arc33 相机互异、C 首读晚于资产封存、检查后资产不变和保护根 Git 控制文件。它**没有独立重写证据提取或完整 CUDA 光栅器**，不能将其通过解读为所有算法都有独立实现验证。

```text
artifacts/gaussian_edge_attribution_v1/STATUS.json
artifacts/gaussian_edge_attribution_v1/SUMMARY_{scene}.json
artifacts/gaussian_edge_attribution_v1/assets/{scene}/
artifacts/gaussian_edge_attribution_v1/media/{scene}/
out/gaussian_edge_attribution_v1/READ_EVENTS.jsonl
out/gaussian_edge_attribution_v1/{scene}/assets/
out/gaussian_edge_attribution_v1/{scene}/F/F_NNN/
out/gaussian_edge_attribution_v1/{scene}/frames/{pose}/projection.npz
out/gaussian_edge_attribution_v1/{scene}/frames/{pose}/METRICS.json
out/gaussian_edge_attribution_v1/{scene}/panels/
out/gaussian_edge_attribution_v1/{scene}/classes_tiers/
out/gaussian_edge_attribution_v1/{scene}/matched_controls/
out/gaussian_edge_attribution_v1/{scene}/media/MEDIA.json
out/gaussian_edge_attribution_v1/{scene}/media/arc33_native.mp4
out/gaussian_edge_attribution_v1/{scene}/media/arc33_telegram1600.mp4
out/gaussian_edge_attribution_v1/{scene}/ply/
out/gaussian_edge_attribution_v1/{scene}/INDEPENDENT_VALIDATION.json
```

报告中的源 SHA、媒体 SHA、相机来源及实际完成数均应从这些封存元数据计算。小 JPEG/Telegram 视频、紧凑 ID 分数和中文报告可版本控制；原始投影、逐视角数组、大 PLY/native 视频保留在列出的精确本地路径。提交/推送只在授权 worktree 中操作，使用既有 origin/SSH，不改 origin 或 global config。
