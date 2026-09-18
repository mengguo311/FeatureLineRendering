# Observed TDD evidence

Each slice records its exact command and raw stdout/stderr, exit code and timestamps. RED is run before implementation; tests are not rewritten to bless outputs. Relevant suite is rerun after each GREEN.

- 01 **RED** 2026-09-18T10:56:04.141717+00:00: `PYTHONPATH=.:tests CUDA_VISIBLE_DEVICES=1 OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 PYTHONDONTWRITEBYTECODE=1 /home/u00134/bin/miniconda3/envs/vfsdgs/bin/python -m unittest -v test_foundation.FoundationTests.test_01_freeze_json_is_canonical_and_exclusive` → exit 1; [01_RED.txt](tdd/01_RED.txt).

- 01 **GREEN** 2026-09-18T10:56:14.720853+00:00: `PYTHONPATH=.:tests CUDA_VISIBLE_DEVICES=1 OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 PYTHONDONTWRITEBYTECODE=1 /home/u00134/bin/miniconda3/envs/vfsdgs/bin/python -m unittest -v test_foundation.FoundationTests.test_01_freeze_json_is_canonical_and_exclusive` → exit 0; [01_GREEN.txt](tdd/01_GREEN.txt).

- 01 **SUITE** 2026-09-18T10:56:14.918266+00:00: `PYTHONPATH=.:tests CUDA_VISIBLE_DEVICES=1 OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 PYTHONDONTWRITEBYTECODE=1 /home/u00134/bin/miniconda3/envs/vfsdgs/bin/python -m unittest -v test_foundation` → exit 0; [01_SUITE.txt](tdd/01_SUITE.txt).

- 02 **RED** 2026-09-18T10:56:25.961696+00:00: `PYTHONPATH=.:tests CUDA_VISIBLE_DEVICES=1 OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 PYTHONDONTWRITEBYTECODE=1 /home/u00134/bin/miniconda3/envs/vfsdgs/bin/python -m unittest -v test_foundation.FoundationTests.test_02_verified_read_detects_tampering` → exit 1; [02_RED.txt](tdd/02_RED.txt).

- 02 **GREEN** 2026-09-18T10:56:44.163036+00:00: `PYTHONPATH=.:tests CUDA_VISIBLE_DEVICES=1 OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 PYTHONDONTWRITEBYTECODE=1 /home/u00134/bin/miniconda3/envs/vfsdgs/bin/python -m unittest -v test_foundation.FoundationTests.test_02_verified_read_detects_tampering` → exit 0; [02_GREEN.txt](tdd/02_GREEN.txt).

- 02 **SUITE** 2026-09-18T10:56:44.329616+00:00: `PYTHONPATH=.:tests CUDA_VISIBLE_DEVICES=1 OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 PYTHONDONTWRITEBYTECODE=1 /home/u00134/bin/miniconda3/envs/vfsdgs/bin/python -m unittest -v test_foundation` → exit 0; [02_SUITE.txt](tdd/02_SUITE.txt).

- 03 **RED** 2026-09-18T10:56:44.513577+00:00: `PYTHONPATH=.:tests CUDA_VISIBLE_DEVICES=1 OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 PYTHONDONTWRITEBYTECODE=1 /home/u00134/bin/miniconda3/envs/vfsdgs/bin/python -m unittest -v test_foundation.FoundationTests.test_03_landlock_denies_native_forbidden_reads_and_writes` → exit 1; [03_RED.txt](tdd/03_RED.txt).

- 03 **GREEN** 2026-09-18T10:57:21.531337+00:00: `PYTHONPATH=.:tests CUDA_VISIBLE_DEVICES=1 OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 PYTHONDONTWRITEBYTECODE=1 /home/u00134/bin/miniconda3/envs/vfsdgs/bin/python -m unittest -v test_foundation.FoundationTests.test_03_landlock_denies_native_forbidden_reads_and_writes` → exit 0; [03_GREEN.txt](tdd/03_GREEN.txt).

- 03 **SUITE** 2026-09-18T10:57:21.854693+00:00: `PYTHONPATH=.:tests CUDA_VISIBLE_DEVICES=1 OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 PYTHONDONTWRITEBYTECODE=1 /home/u00134/bin/miniconda3/envs/vfsdgs/bin/python -m unittest -v test_foundation` → exit 0; [03_SUITE.txt](tdd/03_SUITE.txt).

- 04 **RED** 2026-09-18T10:57:22.195167+00:00: `PYTHONPATH=.:tests CUDA_VISIBLE_DEVICES=1 OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 PYTHONDONTWRITEBYTECODE=1 /home/u00134/bin/miniconda3/envs/vfsdgs/bin/python -m unittest -v test_foundation.FoundationTests.test_04_full_K_projection_and_analytic_jacobian` → exit 1; [04_RED.txt](tdd/04_RED.txt).

- 04 **GREEN** 2026-09-18T10:57:47.482601+00:00: `PYTHONPATH=.:tests CUDA_VISIBLE_DEVICES=1 OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 PYTHONDONTWRITEBYTECODE=1 /home/u00134/bin/miniconda3/envs/vfsdgs/bin/python -m unittest -v test_foundation.FoundationTests.test_04_full_K_projection_and_analytic_jacobian` → exit 0; [04_GREEN.txt](tdd/04_GREEN.txt).

- 04 **SUITE** 2026-09-18T10:57:47.657832+00:00: `PYTHONPATH=.:tests CUDA_VISIBLE_DEVICES=1 OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 PYTHONDONTWRITEBYTECODE=1 /home/u00134/bin/miniconda3/envs/vfsdgs/bin/python -m unittest -v test_foundation` → exit 0; [04_SUITE.txt](tdd/04_SUITE.txt).

- 05 **RED** 2026-09-18T10:57:47.981132+00:00: `PYTHONPATH=.:tests CUDA_VISIBLE_DEVICES=1 OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 PYTHONDONTWRITEBYTECODE=1 /home/u00134/bin/miniconda3/envs/vfsdgs/bin/python -m unittest -v test_foundation.FoundationTests.test_05_native_anisotropic_full_K_stock_buffers` → exit 1; [05_RED.txt](tdd/05_RED.txt).

- 05 **GREEN** 2026-09-18T10:58:41.715602+00:00: `PYTHONPATH=.:tests CUDA_VISIBLE_DEVICES=1 OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 PYTHONDONTWRITEBYTECODE=1 /home/u00134/bin/miniconda3/envs/vfsdgs/bin/python -m unittest -v test_foundation.FoundationTests.test_05_native_anisotropic_full_K_stock_buffers` → exit 0; [05_GREEN.txt](tdd/05_GREEN.txt).

- 05 **SUITE** 2026-09-18T10:58:44.697519+00:00: `PYTHONPATH=.:tests CUDA_VISIBLE_DEVICES=1 OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 PYTHONDONTWRITEBYTECODE=1 /home/u00134/bin/miniconda3/envs/vfsdgs/bin/python -m unittest -v test_foundation` → exit 0; [05_SUITE.txt](tdd/05_SUITE.txt).

- 06 **RED** 2026-09-18T10:59:15.668183+00:00: `PYTHONPATH=.:tests CUDA_VISIBLE_DEVICES=1 OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 PYTHONDONTWRITEBYTECODE=1 /home/u00134/bin/miniconda3/envs/vfsdgs/bin/python -m unittest -v test_foundation.FoundationTests.test_06_native_replay_weights_layers_cutoff_and_termination` → exit 1; [06_RED.txt](tdd/06_RED.txt).

- 06 **GREEN** 2026-09-18T10:59:52.737903+00:00: `PYTHONPATH=.:tests CUDA_VISIBLE_DEVICES=1 OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 PYTHONDONTWRITEBYTECODE=1 /home/u00134/bin/miniconda3/envs/vfsdgs/bin/python -m unittest -v test_foundation.FoundationTests.test_06_native_replay_weights_layers_cutoff_and_termination` → exit 0; [06_GREEN.txt](tdd/06_GREEN.txt).

- 06 **SUITE** 2026-09-18T10:59:53.434146+00:00: `PYTHONPATH=.:tests CUDA_VISIBLE_DEVICES=1 OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 PYTHONDONTWRITEBYTECODE=1 /home/u00134/bin/miniconda3/envs/vfsdgs/bin/python -m unittest -v test_foundation` → exit 0; [06_SUITE.txt](tdd/06_SUITE.txt).

- 07 **RED** 2026-09-18T11:00:21.256263+00:00: `PYTHONPATH=.:tests CUDA_VISIBLE_DEVICES=1 OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 PYTHONDONTWRITEBYTECODE=1 /home/u00134/bin/miniconda3/envs/vfsdgs/bin/python -m unittest -v test_foundation.FoundationTests.test_07_calibration_detects_rgb_and_alpha_errors` → exit 1; [07_RED.txt](tdd/07_RED.txt).

- 07 **GREEN** 2026-09-18T11:00:35.301115+00:00: `PYTHONPATH=.:tests CUDA_VISIBLE_DEVICES=1 OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 PYTHONDONTWRITEBYTECODE=1 /home/u00134/bin/miniconda3/envs/vfsdgs/bin/python -m unittest -v test_foundation.FoundationTests.test_07_calibration_detects_rgb_and_alpha_errors` → exit 0; [07_GREEN.txt](tdd/07_GREEN.txt).

- 07 **SUITE** 2026-09-18T11:00:35.498430+00:00: `PYTHONPATH=.:tests CUDA_VISIBLE_DEVICES=1 OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 PYTHONDONTWRITEBYTECODE=1 /home/u00134/bin/miniconda3/envs/vfsdgs/bin/python -m unittest -v test_foundation` → exit 0; [07_SUITE.txt](tdd/07_SUITE.txt).
