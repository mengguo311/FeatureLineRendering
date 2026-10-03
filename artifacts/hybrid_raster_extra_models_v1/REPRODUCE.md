# 本轮库存阻塞的复核

本轮没有合格新checkpoint，故没有合法的render/calibration/media生产命令或stdin运行记录。不要调用旧runner重跑旧场景替代。本文件复现的是库存、锁和零产物状态的核验；将来新增checkpoint必须重新冻结非空清单、逐scene校准后才可生产。本轮输出验证不冒充新scene渲染验证。

在指定工作区使用既有解释器，不安装包、不改全局配置：

```bash
cd /home/u00134/3dgs_line/hybrid_raster_extra_models_v1
export PATH=/home/u00134/bin/miniconda3/envs/codex-cli/bin:/home/u00134/bin/miniconda3/bin:$PATH
export PYTHONDONTWRITEBYTECODE=1
export PYTHONPATH="$PWD:$PWD/scripts"
export TMPDIR="$PWD/out/hybrid_raster_extra_models_v1/tmp"
export XDG_CACHE_HOME="$PWD/out/hybrid_raster_extra_models_v1/cache"
export OMP_NUM_THREADS=1
```

独立checker的显式参数如下，stdin为 `/dev/null`。输出限当前artifact的 `independent_review` 子目录；重放用新文件名，保留本轮证据。

```bash
strace -f -e trace=openat,openat2 \
  -o out/hybrid_raster_extra_models_v1/logs/VERIFIER_REPLAY.trace \
  /home/u00134/bin/miniconda3/envs/vfsdgs/bin/python -B \
  artifacts/hybrid_raster_extra_models_v1/independent_review/verify_blocker.py \
  --root "$PWD" \
  --inventory artifacts/hybrid_raster_extra_models_v1/inventory/INVENTORY_DISCOVERY.json \
  --manifest artifacts/hybrid_raster_extra_models_v1/INPUTS.json \
  --output artifacts/hybrid_raster_extra_models_v1/independent_review/VERIFICATION_REPLAY.json \
  < /dev/null
```

预期状态是 `BLOCKER_CONFIRMED`、`science_executed=false`，不是科学PASS。checker核对四个TRAIN元数据与索引、ship的三个排除checkpoint、继承锁/源码哈希、冻结清单关联、有界发现集合及全部生产产物为零。不会解码图像、导入renderer或启动GPU。若原冻结匹配规则内出现新候选、清单hash变更或伪生产产物则明确失败，不把旧阻塞状态自动复用。`.pt`缺失来自单独的 `inventory/SUPPLEMENTAL_FILENAME_CHECK.json` 快照，当前checker的原集合重放不涵盖以后新出现的`.pt`；恢复任务时需连同补查范围重新盘点。

新增支持代码的RED与GREEN命令、日志hash、退出码在 `independent_review/TDD.json` 与后续强化记录中；运行最终tests：

```bash
/home/u00134/bin/miniconda3/envs/vfsdgs/bin/python -B -m unittest discover \
  -s artifacts/hybrid_raster_extra_models_v1/independent_review \
  -p test_verify_blocker.py -v < /dev/null
```

相关旧CPU回归：以下是实际执行的测试编排，所有fixture临时文件被限制到新out。测试使用的TEST路径字符串是合成trace文本，不会打开对应资产。科学源码与测试文件没有修改；只在当前进程重定向旧测试硬编码临时路径。

```bash
/home/u00134/bin/miniconda3/envs/vfsdgs/bin/python -B - <<'PY'
import os, unittest
from pathlib import Path
root = Path.cwd()
sandbox = root / 'out/hybrid_raster_extra_models_v1/regression_sandbox'
for name in ('out/hybrid_raster_evidence_v2/tmp',
             'out/hybrid_raster_evidence_v2/test_tmp'):
    (sandbox / name).mkdir(parents=True, exist_ok=True)
from tests import test_hybrid_raster_io as io_tests
from tests import test_hybrid_raster_access as access_tests
from scripts import audit_hybrid_raster_access as audit
io_tests.TMP = sandbox / 'out/hybrid_raster_evidence_v2/test_tmp'
access_tests.ROOT = sandbox
audit.ROOT = sandbox
os.chdir(sandbox)
modules = [
    'tests.test_hybrid_raster_evidence', 'tests.test_hybrid_raster_io',
    'tests.test_hybrid_raster_stage', 'tests.test_hybrid_raster_verifier',
    'tests.test_hybrid_raster_access', 'tests.test_hybrid_dense_v1',
    'tests.test_hybrid_overlay_video', 'tests.test_hybrid_extra_scenes',
    'tests.test_hao_mukai_source',
]
cases = ['tests.test_hybrid_raster_native.NativeContractTest.' + name for name in (
    'test_04_exact_native_principal_point',
    'test_05_calibration_rejects_changed_or_nonfinite_buffers',
    'test_06_export_validation_rejects_wrong_id_shape_and_mass')]
suite = unittest.defaultTestLoader.loadTestsFromNames(modules + cases)
result = unittest.TextTestRunner(verbosity=2).run(suite)
raise SystemExit(0 if result.wasSuccessful() else 1)
PY
```

实际45项通过，记录于 `PRIOR_TESTS.json` / `logs/PRIOR_CPU_TESTS.log`。没有运行GPU测试。检查器的最终访问trace及审计覆盖该进程/子进程，不覆盖初次手工发现或整个会话；不能把范围外事实表述成完整syscall证明。

Git核查：

```bash
git branch --show-current
git diff f2a618450e0d0d142a059794149021fe3c2644ab -- src scripts tests native_patches .codex
git status --porcelain
git rev-parse HEAD
git ls-remote origin refs/heads/hybrid-raster-extra-models-v1
```

冻结协议提交为 `f5abb6f44285bfa91104981798855420729386e0`。FINAL记录各前置提交；包含FINAL的最终封存提交由Git自身解析，避免JSON自引用SHA。本轮最终远端/clean-tree回执保留在 `out/hybrid_raster_extra_models_v1/REMOTE_FINAL.json`，其写入时间晚于最终push。
