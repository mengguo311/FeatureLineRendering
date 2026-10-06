# 复现和恢复

固定工作区 `/home/u00134/3dgs_line/gaer_attribution_capacity_v02`，分支 `gaer-attribution-capacity-v02`，科学协议在 GPU 运行前由提交 `0b77071` 冻结。首轮诊断代码/结果在 `c211d9f`，容量代码/结果在 `a7ecab7`；后续原生 shape、独立审计和展示均保留这些原记录。

```bash
cd /home/u00134/3dgs_line/gaer_attribution_capacity_v02
export CUDA_VISIBLE_DEVICES=0 OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 MKL_NUM_THREADS=2 MAX_JOBS=2 PYTHONDONTWRITEBYTECODE=1
/home/u00134/bin/miniconda3/envs/vfsdgs/bin/python -u experiments/gaer_attribution_capacity_v02/run.py --units oracle,roi,probes,capacity
/home/u00134/bin/miniconda3/envs/vfsdgs/bin/python -u artifacts/gaer_attribution_capacity_v02/CAPACITY_FOLLOWUP.py
/home/u00134/bin/miniconda3/envs/vfsdgs/bin/python -u artifacts/gaer_attribution_capacity_v02/CENTER_NATIVE_EXPORT.py
/home/u00134/bin/miniconda3/envs/vfsdgs/bin/python -u artifacts/gaer_attribution_capacity_v02/ORACLE_ROUNDOFF_AUDIT.py
/home/u00134/bin/miniconda3/envs/vfsdgs/bin/python artifacts/gaer_attribution_capacity_v02/RANKING_AUDIT.py
/home/u00134/bin/miniconda3/envs/vfsdgs/bin/python experiments/gaer_attribution_capacity_v02/audit.py
/home/u00134/bin/miniconda3/envs/vfsdgs/bin/python artifacts/gaer_attribution_capacity_v02/FINALIZE.py
```

原生 GPU 单元原子写入 results 与 seals。恢复先验证协议、当前实验 source SHA、已封印下载/媒体结果的 SHA；完成单元 `SEALED_SKIP`，不重跑科学渲染。中断发生在未封印单元时该单元会完整重跑；其临时文件不作为结果。每个场景独立捕获失败，另一场景继续。不要编辑协议或源码来恢复；新的研究协议应另开阶段。

每个 GPU 单元及 probe 方法检查 GPU0 的 PID，仅接受自身 PID；发现外进程时停止而不终止对方。CPU affinity 两核，MAX_JOBS=2，root 4GiB/common Git 1.5GiB reserve，新阶段总量 cap 8GiB。资源记录位于 ignored `out/gaer_attribution_capacity_v02/logs/resources.jsonl`。运行是普通 Python，不依赖编码代理、配额或交互服务。

若需在独立终端等待长科学单元，可运行以下普通 runner。PID仅写入本阶段，不接管任何外部进程：

```bash
nohup /home/u00134/bin/miniconda3/envs/vfsdgs/bin/python -u experiments/gaer_attribution_capacity_v02/run.py --units oracle,roi,probes,capacity > out/gaer_attribution_capacity_v02/logs/resume.log 2>&1 &
printf '%s\n' "$!" > out/gaer_attribution_capacity_v02/runner.pid
```

本轮已全部完成有预算的科学单元，不需要后台运行来补完；四个逐图解仍未达到固定 0.5% gap 阈值，完整日志照实保留。恢复不增加迭代预算。若只看既有结果，打开 REPORT_ZH.md / FINAL.json，无需 GPU。

新算子的测试入口（只测试新数学，不重复旧工程测试）：

```bash
/home/u00134/bin/miniconda3/envs/vfsdgs/bin/python experiments/gaer_attribution_capacity_v02/test_new_math.py
/home/u00134/bin/miniconda3/envs/vfsdgs/bin/python experiments/gaer_attribution_capacity_v02/test_certificate.py
```

验证后的 original/patched 原生库直接从 attribution-buffer 阶段读取，没有安装或生产替换。`query.cu` 是独立稀疏接受序列与 FP64 矩阵自由证书扩展。条件 shape 复制旧 BUILD 中逐文件校验的 source 到 ignored out，唯一功能补丁是 screen covariance override；`native_shape.patch` 在投影协方差逆矩阵/半径/tiles前生效，全部 T 重新渲染。研究许可证在 experiments/.../UPSTREAM_LICENSE.md。

`CAPACITY_FOLLOWUP.py` 执行冻结协议的 any-perview 触发；最初更严格的 r_000-only `*_shape.json` / seal 保留为 NOT_RUN。补充单元 `*_shape_anyview_condition.json` 是实际结果。最初 cancellation 和展示 profile 的数值问题见 tests/ENGINEERING_FAILURES.json；它们不改变科学参数或首轮封印结果。

文件说明：

- `PROTOCOL.json`：相机/模型/输入、自动ROI坐标、指标/幅值/阈值/停止配置及其 SHA。
- `fullN_linear_oracles.npz` / `oracle_FP64_coefficients.npz`：10图×全部原N系数，八源和两保留域的累计系数；无topK截断。
- `*_ROI_full_CSR.npz`：少量整数查询pixel的完整原native接收序列、ID/权重/T、按ID双线性端点、各K赢家/理由/残量/间隔、有效原SH3颜色、逐ROI全N分数。
- `original_parameter_probes.npz` / `results/*_probes.json`：每组原ID、actual ± profiles、全图/外域/其他ROI/alpha指标、匹配误差及半幅导数差。
- `*_perview_strengths.npz` / `shared_strengths.npz`：全部原ID的连续strength、完整view/source SHA；不是紧凑边资产。
- `*_native_RGB.npz`：实际原生白背景 appearance=1−strength 的全800×800输出，不删核。
- `known_target_solver_logs.csv` / `results/*_capacity.json`：全部初值和停止日志、可行上界/FP64 dual下界/gap/PG、活动数量和饱和量。主目标E内连续L、外域压白；原全连续L的MSE另列。
- `shape_ratio*.npz`：临时原ID screen covariance、actual ink/alpha/T；center未动，opacity峰值不补偿。
- `tests/*AUDIT*.json`：独立标量原ID/官方CPU SH3/保存结果/关联/旧字节审计；近零颜色normalizer修正单独保存。
- `MEDIA_MANIFEST.json` / `SOURCE_MAP.json`：媒体/下载/source/protocol SHA。原始代理日志仅在 ignored out，不提交。
