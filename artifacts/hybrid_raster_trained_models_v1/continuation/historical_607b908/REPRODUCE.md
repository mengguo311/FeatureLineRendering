# 复现与核验

工作区 `/home/u00134/3dgs_line/hybrid_raster_trained_models_v1`。解释器 `/home/u00134/bin/miniconda3/envs/vfsdgs/bin/python`；无需安装或修改环境。所有生产源、输入、参数、检查点均由清单hash约束；原始数据只允许TRAIN。完整设置与边界见PROTOCOL.md。

初始协议冻结提交 `8b3915b5e3211530beefd8606dbdcdd5cdf25e2d`；启动支持修正提交 `9fb46557958e5ec4b3e13df0894b9be747c43e6b`；真正采集使用从immutable git blob恢复的标准源，启动冻结提交 `206b9ebf3e90d4766fb1b3e32ebfba491e390f4e`。三次提交均先推送核对，任何真实场景采集发生在最后一次之后。早期失败只涉及合成基础设施夹具，保留日志及syscall证据；不计入四场景训练。

上游pin为 `472689c0dc70417448fb451bf529ae532d32c095`。只读源目录有一处未提交的4返回值改动；实际采集不用该working-tree内容，而是17个固定git blob加明确seed/TRAIN/I/O补丁。`acquisition/SOURCE_LINEAGE_REVIEW.json`及独立ROUND3检查记录与旧LEGO实际vendor的逐文件比较。既有official vanilla二进制路径/hash见acquisition/ACQUISITION.json；NPR二进制与旧科学源见INHERITED_LOCK。

实际采集逐scene串行调用以下入口；每次先验证远端冻结SHA、manifest、依赖、GPU所有者和空间。该命令是本次执行记录，不应绕过已存在launch claim重新训练。恢复仅接受完全匹配的snapshot与manifest，保留累计2小时限制。

```bash
PYTHONDONTWRITEBYTECODE=1 /home/u00134/bin/miniconda3/envs/vfsdgs/bin/python artifacts/hybrid_raster_trained_models_v1/acquisition/run_training.py --manifest artifacts/hybrid_raster_trained_models_v1/acquisition/manifests/hotdog.json --gpu 0 --freeze-commit 206b9ebf3e90d4766fb1b3e32ebfba491e390f4e
```

顺序为hotdog/materials/mic/ship，均seed1729、30k，原生800、SH3、白背景、标准光度损失/增密；checkpoint7000+30000保留。各场景`out/.../training/SCENE/seed_1729/attempt_000/LAUNCH.json`是含strace的实际命令；`EXIT.json`、`resources.jsonl`、`training.strace`与`train.log`保留退出、资源和访问记录。`losses.jsonl`为逐iteration记录，`diagnostics/iteration_30000`为F1/F41/F79 TRAIN in-sample对照，不能称泛化评估。

检查点封存后，运行transport/adapters.py解析精确相机。四场景CAMERAS.json、检查点lineage及独立PASS证据已在 `26636535ab39c1996493d0088a7a53bb358dbb9a` 提交推送；10:06:08 UTC核对远端后写入 `transport/RENDER_FREEZE.json`，之后才释放NPR启动。详细schema与逐场景render→media顺序见transport/README.md。实际NPR调用使用`strace -f -q -yy -s 4096 -e trace=open,openat,openat2,creat`，保留退出记录；旧`-qq`历史输入审计使用另行hash绑定的退出回执，不能混淆scope。

只读核验入口如下，输出写到本轮独立审阅目录；subset会显式标记未完成全196帧，绝不把部分成功当总实验成功。

```bash
PYTHONDONTWRITEBYTECODE=1 /home/u00134/bin/miniconda3/envs/vfsdgs/bin/python artifacts/hybrid_raster_trained_models_v1/independent_review/verify_acquisition.py --final --output artifacts/hybrid_raster_trained_models_v1/independent_review/ACQUISITION_FINAL_RECHECK.json
PYTHONDONTWRITEBYTECODE=1 /home/u00134/bin/miniconda3/envs/vfsdgs/bin/python artifacts/hybrid_raster_trained_models_v1/independent_review/verify_production.py --output artifacts/hybrid_raster_trained_models_v1/independent_review/PRODUCTION_RECHECK.json
PYTHONDONTWRITEBYTECODE=1 /home/u00134/bin/miniconda3/envs/vfsdgs/bin/python artifacts/hybrid_raster_trained_models_v1/transport/summarize_results.py --output artifacts/hybrid_raster_trained_models_v1/independent_review/DIAGNOSTIC_SUMMARY_RECHECK.json
```

禁止运行旧producer main或fit_normalization；本轮始终用原parameter hash `6c4ef4afa648f54794d7094a7b21368a89e14cdbc792766441aa3d3639d487c9`。原生RGB/line/overlay/matched panels、原始字段和媒体均由SEAL绑定；FINAL.json与REPORT.md记录实际完成范围，不由本复现说明中的期望数量推断成功。

实际交付为49/196帧：Hotdog的8F校准、全部49帧、6视频、15联系表和9首中末图通过独立核验；Materials/Mic/Ship未进入NPR。acquisition核验exit0、`PRODUCTION.json`的exit1及summary的exit2均表示缺147帧，不能当作成功退出。Materials实际预检因工作区空间不足exit3，证据见`transport/STORAGE_BLOCKER.json`。继续需要足够的授权存储，不需重训、重新拟合或重构图。

Hotdog共有两次render实际执行：`launches/hotdog_render_000`异常返回143；保留27个frame、28个raw和arc011中断staging，原trace不完整，原因未知。独立缓存核验后，完全相同的冻结producer由独立session续跑；实际目录为`hotdog_render_003`，目录计数包含outer文件，不能解读为四次执行。第二次exit0，其trace完整；`ABNORMAL_TERMINATION.json`、`RESUME_EXECUTION.json`和`EXECUTION_render.json`绑定原件、预算与命令。媒体单独以同一冻结`--phase media`命令执行，`EXECUTION_media.json`绑定完整trace和退出记录。

最终独立CPU checker首次也异常返回143，原证据保持INVALID；未改checker，以独立session重跑后完整结束。其实际命令/退出见`independent_review/PRODUCTION_VERIFIER_ATTEMPT002_{START,LAUNCH,EXIT}.json`，完整访问审计见`PRODUCTION_ACCESS.json`。不要将恢复后的文件完整性解释为补齐了第一次执行的syscall记录。
