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

- 08 **RED** 2026-09-18T11:00:58.283672+00:00: `PYTHONPATH=.:tests CUDA_VISIBLE_DEVICES=1 OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 PYTHONDONTWRITEBYTECODE=1 /home/u00134/bin/miniconda3/envs/vfsdgs/bin/python -m unittest -v test_foundation.FoundationTests.test_08_load_full_SH_asset_without_filtering` → exit 1; [08_RED.txt](tdd/08_RED.txt).

- 08 **GREEN** 2026-09-18T11:01:29.915206+00:00: `PYTHONPATH=.:tests CUDA_VISIBLE_DEVICES=1 OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 PYTHONDONTWRITEBYTECODE=1 /home/u00134/bin/miniconda3/envs/vfsdgs/bin/python -m unittest -v test_foundation.FoundationTests.test_08_load_full_SH_asset_without_filtering` → exit 0; [08_GREEN.txt](tdd/08_GREEN.txt).

- 08 **SUITE** 2026-09-18T11:01:30.168237+00:00: `PYTHONPATH=.:tests CUDA_VISIBLE_DEVICES=1 OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 PYTHONDONTWRITEBYTECODE=1 /home/u00134/bin/miniconda3/envs/vfsdgs/bin/python -m unittest -v test_foundation` → exit 0; [08_SUITE.txt](tdd/08_SUITE.txt).

- 09 **RED** 2026-09-18T11:01:33.450358+00:00: `PYTHONPATH=.:tests CUDA_VISIBLE_DEVICES=1 OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 PYTHONDONTWRITEBYTECODE=1 /home/u00134/bin/miniconda3/envs/vfsdgs/bin/python -m unittest -v test_foundation.FoundationTests.test_09_clone_split_deterministic_parent_mass_and_moments` → exit 1; [09_RED.txt](tdd/09_RED.txt).

- 09 **GREEN** 2026-09-18T11:02:04.924850+00:00: `PYTHONPATH=.:tests CUDA_VISIBLE_DEVICES=1 OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 PYTHONDONTWRITEBYTECODE=1 /home/u00134/bin/miniconda3/envs/vfsdgs/bin/python -m unittest -v test_foundation.FoundationTests.test_09_clone_split_deterministic_parent_mass_and_moments` → exit 0; [09_GREEN.txt](tdd/09_GREEN.txt).

- 09 **SUITE** 2026-09-18T11:02:05.126498+00:00: `PYTHONPATH=.:tests CUDA_VISIBLE_DEVICES=1 OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 PYTHONDONTWRITEBYTECODE=1 /home/u00134/bin/miniconda3/envs/vfsdgs/bin/python -m unittest -v test_foundation` → exit 0; [09_SUITE.txt](tdd/09_SUITE.txt).

- 10 **RED** 2026-09-18T11:02:08.587455+00:00: `PYTHONPATH=.:tests CUDA_VISIBLE_DEVICES=1 OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 PYTHONDONTWRITEBYTECODE=1 /home/u00134/bin/miniconda3/envs/vfsdgs/bin/python -m unittest -v test_foundation.FoundationTests.test_10_qualification_uses_frozen_roi_and_all_thresholds` → exit 1; [10_RED.txt](tdd/10_RED.txt).

- 10 **GREEN** 2026-09-18T11:02:49.500319+00:00: `PYTHONPATH=.:tests CUDA_VISIBLE_DEVICES=1 OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 PYTHONDONTWRITEBYTECODE=1 /home/u00134/bin/miniconda3/envs/vfsdgs/bin/python -m unittest -v test_foundation.FoundationTests.test_10_qualification_uses_frozen_roi_and_all_thresholds` → exit 0; [10_GREEN.txt](tdd/10_GREEN.txt).

- 10 **SUITE** 2026-09-18T11:02:49.744792+00:00: `PYTHONPATH=.:tests CUDA_VISIBLE_DEVICES=1 OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 PYTHONDONTWRITEBYTECODE=1 /home/u00134/bin/miniconda3/envs/vfsdgs/bin/python -m unittest -v test_foundation` → exit 0; [10_SUITE.txt](tdd/10_SUITE.txt).

- 11 **RED** 2026-09-18T11:02:53.408428+00:00: `PYTHONPATH=.:tests CUDA_VISIBLE_DEVICES=1 OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 PYTHONDONTWRITEBYTECODE=1 /home/u00134/bin/miniconda3/envs/vfsdgs/bin/python -m unittest -v test_foundation.FoundationTests.test_11_prerequisite_gate_never_calls_invalid_a_scientific_failure` → exit 1; [11_RED.txt](tdd/11_RED.txt).

- 11 **GREEN** 2026-09-18T11:03:27.644813+00:00: `PYTHONPATH=.:tests CUDA_VISIBLE_DEVICES=1 OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 PYTHONDONTWRITEBYTECODE=1 /home/u00134/bin/miniconda3/envs/vfsdgs/bin/python -m unittest -v test_foundation.FoundationTests.test_11_prerequisite_gate_never_calls_invalid_a_scientific_failure` → exit 0; [11_GREEN.txt](tdd/11_GREEN.txt).

- 11 **SUITE** 2026-09-18T11:03:27.851305+00:00: `PYTHONPATH=.:tests CUDA_VISIBLE_DEVICES=1 OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 PYTHONDONTWRITEBYTECODE=1 /home/u00134/bin/miniconda3/envs/vfsdgs/bin/python -m unittest -v test_foundation` → exit 0; [11_SUITE.txt](tdd/11_SUITE.txt).

- 12 **RED** 2026-09-18T11:03:31.170254+00:00: `PYTHONPATH=.:tests CUDA_VISIBLE_DEVICES=1 OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 PYTHONDONTWRITEBYTECODE=1 /home/u00134/bin/miniconda3/envs/vfsdgs/bin/python -m unittest -v test_foundation.FoundationTests.test_12_native_open_audit_separates_denials_and_violations` → exit 1; [12_RED.txt](tdd/12_RED.txt).

- 12 **GREEN** 2026-09-18T11:04:07.987293+00:00: `PYTHONPATH=.:tests CUDA_VISIBLE_DEVICES=1 OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 PYTHONDONTWRITEBYTECODE=1 /home/u00134/bin/miniconda3/envs/vfsdgs/bin/python -m unittest -v test_foundation.FoundationTests.test_12_native_open_audit_separates_denials_and_violations` → exit 0; [12_GREEN.txt](tdd/12_GREEN.txt).

- 12 **SUITE** 2026-09-18T11:04:08.172359+00:00: `PYTHONPATH=.:tests CUDA_VISIBLE_DEVICES=1 OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 PYTHONDONTWRITEBYTECODE=1 /home/u00134/bin/miniconda3/envs/vfsdgs/bin/python -m unittest -v test_foundation` → exit 0; [12_SUITE.txt](tdd/12_SUITE.txt).

- 13 **RED** 2026-09-18T11:04:11.716625+00:00: `PYTHONPATH=.:tests CUDA_VISIBLE_DEVICES=1 OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 PYTHONDONTWRITEBYTECODE=1 /home/u00134/bin/miniconda3/envs/vfsdgs/bin/python -m unittest -v test_foundation.FoundationTests.test_13_deterministic_png_contact_sheet` → exit 1; [13_RED.txt](tdd/13_RED.txt).

- 13 **GREEN** 2026-09-18T11:04:29.639779+00:00: `PYTHONPATH=.:tests CUDA_VISIBLE_DEVICES=1 OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 PYTHONDONTWRITEBYTECODE=1 /home/u00134/bin/miniconda3/envs/vfsdgs/bin/python -m unittest -v test_foundation.FoundationTests.test_13_deterministic_png_contact_sheet` → exit 0; [13_GREEN.txt](tdd/13_GREEN.txt).

- 13 **SUITE** 2026-09-18T11:04:29.882158+00:00: `PYTHONPATH=.:tests CUDA_VISIBLE_DEVICES=1 OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 PYTHONDONTWRITEBYTECODE=1 /home/u00134/bin/miniconda3/envs/vfsdgs/bin/python -m unittest -v test_foundation` → exit 0; [13_SUITE.txt](tdd/13_SUITE.txt).
