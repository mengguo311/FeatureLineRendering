# Stage 2：scan24 paper-text pilot 的准备与独立执行

本轮授权已覆盖 Stage 1 的 awaiting-user 限制：允许获取 DTU 数据、创建隔离环境、修改并验证 paper-text 公式，随后在 GPU 真正空闲时自动执行 **仅 scan24 half-resolution 30k** 的完整链路。完整论文 suite 仍是后续目标，本 runner 不能自动扩展第二场景或 68 个训练。

本文记录准备与执行机制，不是训练完成声明。当前观测以 [PILOT_STATUS.json](PILOT_STATUS.json) 和其中指向的 HDD `runner_state.json` 为准；[启动 header](MODEL_LAUNCH/header.json) 也不是科学完成证据。

## 第 1 阶段衔接与源码

[stage1_frozen/SEAL.json](stage1_frozen/SEAL.json) 固定了七份 Stage 1 关键文件的 SHA-256。已重新核对 `stage1completed`、原 validation 的 `passed`、封存哈希、当前研究分支和原 C24 HEAD。补充复制文档所引用的原有证据以保持相对链接有效，原七份封存文件未改；普通只读权限与哈希不等于 WORM 存储。

完整 PDF 文本和原始网页正文仅保留为本机阅读缓存，不随本次提交发布；manifest 保留原 URL、取得记录和哈希。因此缓存类相对链接在本研究工作树有效，新克隆者应使用 manifest 的上游链接重新获取。提交范围是新复现代码、小文档、manifest、静态测试证据；动态日志、环境、数据和模型均不提交。

上游固定 `2d4bc087f1b4bd62c96054fbe89d273490526b81`，原 clone 为 `/mnt/hdd1/u00134/radegs_paper_reproduction_v01/sources/RaDe-GS`。许可证与 upstream Git 历史保留。独立变体在同一 HDD 的 `sources/paper_text_variant`；新 loss、恢复和 runner 源码位于本工作树 `reproduction/radegs_paper_v01/stage2/`。源文件逐项哈希见 [stage2_source_manifest.json](stage2_evidence/stage2_source_manifest.json)，核心变更见 [SOURCE_PATCH.diff](SOURCE_PATCH.diff)。C25/C26 未被用于替代训练方法。

方法约束、明确工程差异、未明示 defaults 与尚待 GPU 检验的限制集中写在 [PAPER_TEXT_DEVIATIONS_ZH.md](PAPER_TEXT_DEVIATIONS_ZH.md)。这是一条 v2 paper-text engineering pilot，不声称找到了作者完整表格对应的提交。

## 实际数据证据

同期 [C24 README #L37-L53](https://github.com/HKUST-SAIL/RaDe-GS/blob/2d4bc087f1b4bd62c96054fbe89d273490526b81/README.md#L37-L53) 指向 2DGS 预处理 DTU 及官方 DTU GT。没有改用 PGSR 预处理或下载训练 checkpoint。三个归档均在 HDD 下载，实做 SHA-256、安全路径/类型预检；DTU 完整解包，GT ZIP 仅提取 scan24 所需项并由 ZIP reader 校验所提取成员 CRC。

| 归档 | 实际字节 | SHA-256 |
|---|---:|---|
| [dtu.tar.gz](https://drive.google.com/file/d/1ODiOu72tAGPTnhVn0cFZ9MvymDgcoHxQ/view) | 3,561,809,006 | `4caf0a4523494dea748c514f718cd3d187956e3ccb511703829e25caa9846da7` |
| [Points.zip](https://roboimagedata2.compute.dtu.dk/data/MVS/Points.zip) | 6,966,262,016 | `85862c8844978e8958040982b0071442d2a47fe67391aa1aca9a743153c9edc1` |
| [SampleSet.zip](https://roboimagedata2.compute.dtu.dk/data/MVS/SampleSet.zip) | 6,905,656,531 | `f719a5259db9257c4716ce014964444c1bb82fbb893e0d100b5fa01b82c029c7` |

SHA 是本次下载的完整性标识，公开源没有提供可比对的发布方 SHA；不能据此宣称发布方签名认证。访问与许可的已知范围保留在 [Stage 1 数据审计](STAGE1_AUDIT_ZH.md)，本轮没有新增数据许可推断。

完整训练包包含论文 DTU 的 15 个 scan，共 3,201 个文件。scan24 实际有 49 张 1554×1162 RGBA 图像；每张都解码并核对 alpha 范围、相机登记名称与尺寸。`-r 2` 是 777×581。COLMAP 是一个 PINHOLE intrinsics 条目、49 个 extrinsics、31,205 个带 RGB 的 SfM 点；Gaussian 参数从这些点重新初始化。已有 vanilla Lego/Chair PLY 不进入配置。

训练只使用 `data/prepared/scan24` 的独立副本；`data/raw/dtu_original` 已设只读。预处理包 README 说明用既有相机姿态配合 COLMAP 生成 SfM；其稀疏 depth 未用于训练。官方几何 GT 与 ObsMask/Plane/cal18 单独位于 `data/eval_gt/dtu_eval_scan24`，不作训练深度、法线或表面监督。scan24 官方 GT PLY 实际 5,169,152 个点；64 个 3×4 标定矩阵、ObsMask/BB/Res、Plane P 的文件和 schema 均已核对。详见 [DATA_STATUS.json](stage2_evidence/DATA_STATUS.json)。没有为全 suite 下载 Mip360/TNT/Synthetic 大包。

## 隔离环境与构建

环境为 `/mnt/hdd1/u00134/radegs_paper_reproduction_v01/envs/c24_py39`。Python 3.9.23、torch 2.3.1+cu121、torchvision 0.18.1、CUDA nvcc 12.1.105、独立 conda GCC 12.4、Open3D 0.18.0、NumPy 1.26.4 均实际安装。完整解析版本和来源见 [environment_lock.json](stage2_evidence/environment_lock.json)、[pip-freeze](stage2_evidence/pip-freeze.txt)、[conda-explicit](stage2_evidence/conda-explicit.txt)。未改共享环境、编译器、binary 或 global config。

构建了变体 rasterizer、simple-knn，以及只用于验证的 C24 原版 rasterizer。原版验证副本的源码与 C24 逐项比对；各 wheel/.so 哈希、nvcc/compiler 与构建日志路径在 [nativebuild_provenance.json](stage2_evidence/nativebuild_provenance.json)。构建固定 `TORCH_CUDA_ARCH_LIST=8.6` 并隐藏 GPU，避免扩展工具探测设备。CPU import 检查实际得到 `torch.cuda.is_initialized()==False`；不调用 `is_available()` 或任何 GPU 计算。

归档约 17 GiB、解包/准备/所需 GT 约 4.5 GiB、环境约 8 GiB、缓存约 2 GiB，均是本次 `du` 观测的舍入值。preflight 保留 root≥10 GiB、HDD≥30 GiB 门槛，实际余量记录于 [preflight](stage2_evidence/preflight.json)。后续模型、checkpoint、导出与 TSDF 预留 30 GiB 是工程预算，不是测量结果；高斯数与最终磁盘占用尚未知。C24 TSDF 的 50,000×16³×2×float32 属性名义容量约 1.64 GB，另有索引/mesh/框架开销。没有虚构 A6000 训练时长；论文 H800 timing 不能直接复现为本机时间。

## 测试与 stage 门槛

RED/GREEN 原始小日志保存在 HDD `stage2/tests`，并复制到 [stage2_evidence/tests](stage2_evidence/tests)。初始 RED 包括尚无目标模块时的 import failure，后续有真实断言失败（N/A GPU query、训练接线、evaluator exit、kernel 接线）；不是把缺依赖失败伪称为 CUDA 数值失败。CPU 完成 5 个 suite、28 个测试，见 [preflight](stage2_evidence/preflight.json)。包括：Eq.23/Eq.24 数学与解析/autograd 梯度、共享 native header 的 CPU recurrence、边界 schedule、median normal gradcheck、Adam/RNG/appearance/filter/buffer 恢复、危险归档、idle/busy/query-failed、原子 seal、损坏输出、flock、真实本人 CPU child 的接管与安全停止。

| stage | 输入与命令来源 | 产物 | 才能推进的门槛 |
|---|---|---|---|
| smoke | 已验证 source/data/env；`gpu_stages.py --stage smoke` | baseline/variant fixtures、比较 JSON、scan24 初始化 forward/backward 报告 | 真正空闲卡；原版非 loss forward/RGB-alpha backward 回归、Eq.23 frozen-weight FD、Eq.24 FD、median normal GPU gradcheck、真实数据 smoke 全部通过。0 optimizer steps。 |
| train | `runner_config.json:train_command`，从 COLMAP 初始化或本 pilot 完整 verified checkpoint 恢复 | 每迭代 loss JSONL、两代 checkpoint、filter-bearing PLY、train_complete | 连续 idle+启动重检；先有 verified smoke seal；1..30000 记录、最终 checkpoint、有限 loss 与最终 PLY/filter 验证。PLY 单独存在不算完成。 |
| export | 30k 变体模型，`--stage export` | 49 份 raw float NPZ，median camera-z/alpha/blended normal/median-depth normal/RGB 及相机元数据 | verified train seal；shape、数量、finite 检验。 |
| tsdf | C24 `mesh_extract.py -s …/scan24 -m …/scan24_paper_text_half_30k -r 2` | `recon.ply` | verified export seal；保留 C24 median+mask+alpha.5、voxel.002、TSDF/marching cubes；mesh 非空且 finite。 |
| eval | C24 `evaluate_dtu_mesh.py`，显式 `--DTU …/dtu_eval_scan24 --iteration 30000 -r 2` | culled/aligned mesh，`vis/results.json` | verified TSDF seal；子 evaluator exit 传播；d2s/s2d/overall 有限且满足算术关系，单位 mm。 |

训练精确命令见 HDD config 的 `train_command`，核心为：

```text
<HDD>/envs/c24_py39/bin/python train.py
  -s <HDD>/data/prepared/scan24
  -m <HDD>/models/scan24_paper_text_half_30k -r 2
  --use_decoupled_appearance --iterations 30000
  --lambda_distortion 100 --lambda_depth_normal 5
  --regularization_from_iter 15001 --test_iterations -1
  --save_iterations 15000 30000
  --pilot_config <HDD>/stage2/state/runner_config.json
```

此处 `<HDD>` 固定为 `/mnt/hdd1/u00134/radegs_paper_reproduction_v01`，执行 cwd 为其 `sources/paper_text_variant`。路径完整展开的 argv 和 source/data/environment hash 由配置封存，不是待手工补齐的训练方案。

## 独立 runner 与恢复语义

runner 是普通 Python 进程，复用已有专属 tmux `radegs-scan24-queue-v01`，不依赖 Codex 配额或当前交互。只用 `nvidia-smi -q -x` 观察 GPU；日志不采集 foreign command line。每 60 秒查询，候选 GPU 必须没有任何 compute/graphics context、显存≤128 MiB、util=0，且至少两次连续有效观测相距≥60 秒。查询缺项、N/A、失败都使 idle 证据清零。持本人 flock 后再次查询，并用 UUID 绑定 `CUDA_VISIBLE_DEVICES`。

flock **不提供 cluster reservation**，无法保证别人不会在重检后进入。stage 运行时每 5 秒监测（查询本身有 20 秒超时）；发现外部 context 或查询失败，只给经过 UID/PGID/内核 start-time 核验的本人进程组 SIGTERM。训练在完整 step 边界保存后 exit 75，再回到等待。不会杀别人，也不会因显存尚够而重叠开工；不可避免存在观测与安全退出延迟，不能声称硬独占保证。超过 180 秒仍在安全退出则持续等待并记状态，不强杀正在写 checkpoint 的本人进程。

checkpoint 每 500 步以及安全停止/最终步保存；数据写入独立 generation 后 fsync，再原子切换校验指针，保留前一代。掉电最多回退到已验证代，可能重算不足 500 步，不从头重训。每个 stage 只在 report/output hash 验证后原子 seal；重启只跳过仍验证通过的 seal。失败状态与独立 attempt 日志保留，未完成训练保留 checkpoint；普通工程失败停为 `ENGINEERING_NOT_READY`，不会擅自改 method 重试。活着的本人 child 可按持久 PID identity 接管，不凭 PID 数字误杀进程。

最终只有五个 seal 均有效时才记 `PILOT_CHAIN_COMPLETE`。这仍仅表示一个 pilot 链路通过，`scientificdone=false`、完整 suite 未完成；之后停止并等用户决定下一步。
