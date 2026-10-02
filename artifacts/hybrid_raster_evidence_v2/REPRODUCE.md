# 复现与核验

以下命令在授权 worktree 中执行。所有 Python 均使用指定解释器；runner 自带绝对 shebang，可直接执行。不要重建已完成的原生构建来绕过 seal/hash 不匹配；已有结果应先运行 verifier。native 源来自只读 sibling，脚本只复制最小源码与许可证到本 worktree 的隔离目录。

```bash
cd /home/u00134/3dgs_line/hybrid_raster_evidence_v2
export PATH=/home/u00134/bin/miniconda3/envs/codex-cli/bin:/home/u00134/bin/miniconda3/bin:$PATH
export PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=.:scripts
export TMPDIR=$PWD/out/hybrid_raster_evidence_v2/tmp
export XDG_CACHE_HOME=$PWD/out/hybrid_raster_evidence_v2/cache
export TORCH_EXTENSIONS_DIR=$PWD/out/hybrid_raster_evidence_v2/torch_extensions
export CUDA_CACHE_PATH=$PWD/out/hybrid_raster_evidence_v2/cuda_cache
```

从尚无该阶段输出的状态构建、测试、校准（GPU guard 会逐次检查所有计算 PID 的归属，检测到任何其他任务即拒绝运行）：

```bash
scripts/build_hybrid_raster_native.sh
/home/u00134/bin/miniconda3/envs/vfsdgs/bin/python -B -m unittest tests.test_hybrid_raster_native -v
/home/u00134/bin/miniconda3/envs/vfsdgs/bin/python -B -m src.hybrid_raster_native --calibrate-primary
```

生产顺序固定。`pilot` 仅 F1/F41；`primary-f` 汇总两主场景全部 F 并创建不可变 `LOCK.json`。在锁之前不能调用 C/arc。主场景全部完成后才允许 `extra`；Drums/Ficus 继承相同的全局尺度。每一帧读取精确 INPUTS 相机重新栅格化，四个校准帧只在相机、checkpoint、构建、内容 hash 一致时复用。

```bash
scripts/run_hybrid_raster_evidence_v2.py --phase pilot
scripts/run_hybrid_raster_evidence_v2.py --phase primary-f
scripts/run_hybrid_raster_evidence_v2.py --phase primary-eval
scripts/run_hybrid_raster_evidence_v2.py --phase extra
scripts/run_hybrid_raster_evidence_v2.py --phase media
```

原生状态与最终 frame 都有 seal；同样的命令重启只跳过完整且哈希正确的结果。残缺/损坏/参数不匹配结果明确报错并保留，不会被静默覆盖。未完成的 staging 留在输出目录。科学参数冻结后，不能为改善 C 图像修改任何源或阈值。

完成后验证所有原生字段有限性、ID/贡献权重、融合与 provenance、墨量控制、精确相机、全部文件 seal、视频完整解码和 distinct 帧：

```bash
scripts/verify_hybrid_raster_evidence_v2.py --full-native
scripts/summarize_hybrid_raster_evidence_v2.py --output artifacts/hybrid_raster_evidence_v2/SUMMARY.json
```

summarizer 的输出为一次性快照；若该文件已存在，应使用另一个快照文件名。它只汇总已验证诊断，不输出视觉质量分数；完整文件验证由 verifier 完成。

新测试与相关回归（运行 GPU 项前确认没有生产进程或其他 GPU 作业）：

```bash
/home/u00134/bin/miniconda3/envs/vfsdgs/bin/python -B -m unittest \
  tests.test_hybrid_raster_native tests.test_hybrid_raster_evidence \
  tests.test_hybrid_raster_io tests.test_hybrid_raster_stage tests.test_hybrid_raster_verifier \
  tests.test_hybrid_dense_v1 tests.test_hybrid_overlay_video \
  tests.test_hybrid_extra_scenes tests.test_hao_mukai_source -v
```

测试 RED/GREEN、构建、原生校准、生产与视频日志均保存；报告注明早期两次测试启动问题，未把它们当成科学失败。C/arc 生产另用 `strace -f -e trace=openat,openat2` 保存输入访问记录。方法仅打开 checkpoint PLY 与 INPUTS 相机元数据，不解码原始 C/DEV/TEST 图像；C/arc 展示来自 frozen GS 的真实重渲染。

输出根目录为 `out/hybrid_raster_evidence_v2`，包含 `raw/`、`frames/`、`media/`、`native/`、`calibration/`、`LOCK.json`、运行时间与 GPU ownership 日志。每帧的 `native.npz` 保留原始 alpha*T，`typed.npz` 另存归一化 top4 weights；`responses.npz` 与 `provenance.npz` 保存全部臂及来源。所有 main A/B/C 都是逐视角 2D 字段，没有旧橙线或固定三维线资产。
