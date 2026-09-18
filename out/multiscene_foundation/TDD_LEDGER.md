# Observed RED / GREEN / REFACTOR ledger

Tests precede production implementations. Raw output and exact commands are linked
below. Synthetic fixtures do not tune scene outcomes. Refactoring is recorded only
when performed; failure logs are never replaced by later runs.

- 01 **RED** 2026-09-18T18:48:14.908700+00:00: `PYTHONPATH=.:tests CUDA_VISIBLE_DEVICES=1 OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 PYTHONDONTWRITEBYTECODE=1 /home/u00134/bin/miniconda3/envs/vfsdgs/bin/python -m unittest -v test_multiscene_training` → exit 1; [01_RED.txt](tdd/01_RED.txt).

- 01 **GREEN** 2026-09-18T18:49:29.643726+00:00: `PYTHONPATH=.:tests CUDA_VISIBLE_DEVICES=1 OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 PYTHONDONTWRITEBYTECODE=1 /home/u00134/bin/miniconda3/envs/vfsdgs/bin/python -m unittest -v test_multiscene_training` → exit 1; [01_GREEN.txt](tdd/01_GREEN.txt).

- 01 **GREEN_FIXED** 2026-09-18T18:49:41.934842+00:00: `PYTHONPATH=.:tests CUDA_VISIBLE_DEVICES=1 OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 PYTHONDONTWRITEBYTECODE=1 /home/u00134/bin/miniconda3/envs/vfsdgs/bin/python -m unittest -v test_multiscene_training` → exit 0; [01_GREEN_FIXED.txt](tdd/01_GREEN_FIXED.txt).

- 02 **RED** 2026-09-18T18:50:07.539012+00:00: `PYTHONPATH=.:tests CUDA_VISIBLE_DEVICES=1 OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 PYTHONDONTWRITEBYTECODE=1 /home/u00134/bin/miniconda3/envs/vfsdgs/bin/python -m unittest -v test_multiscene_training.TrainingTests.test_training_entry_preserves_arguments_and_blocks_unstaged_reads` → exit 1; [02_RED.txt](tdd/02_RED.txt).

- 02 **GREEN** 2026-09-18T18:50:39.706541+00:00: `PYTHONPATH=.:tests CUDA_VISIBLE_DEVICES=1 OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 PYTHONDONTWRITEBYTECODE=1 /home/u00134/bin/miniconda3/envs/vfsdgs/bin/python -m unittest -v test_multiscene_training` → exit 0; [02_GREEN.txt](tdd/02_GREEN.txt).

- 03 **RED** 2026-09-18T18:51:08.893385+00:00: `PYTHONPATH=.:tests CUDA_VISIBLE_DEVICES=1 OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 PYTHONDONTWRITEBYTECODE=1 /home/u00134/bin/miniconda3/envs/vfsdgs/bin/python -m unittest -v test_multiscene_training.TrainingTests.test_job_manifests_enumerate_eight_fixed_runs_without_recipe_drift` → exit 1; [03_RED.txt](tdd/03_RED.txt).

- 03 **GREEN** 2026-09-18T18:51:46.850983+00:00: `PYTHONPATH=.:tests CUDA_VISIBLE_DEVICES=1 OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 PYTHONDONTWRITEBYTECODE=1 /home/u00134/bin/miniconda3/envs/vfsdgs/bin/python -m unittest -v test_multiscene_training` → exit 0; [03_GREEN.txt](tdd/03_GREEN.txt).

- 04 **RED** 2026-09-18T18:53:32.144352+00:00: `PYTHONPATH=.:tests CUDA_VISIBLE_DEVICES=1 OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 PYTHONDONTWRITEBYTECODE=1 /home/u00134/bin/miniconda3/envs/vfsdgs/bin/python -m unittest -v test_multiscene_training.TrainingTests.test_training_entry_preserves_arguments_and_blocks_unstaged_reads` → exit 1; [04_RED.txt](tdd/04_RED.txt).

- 04 **GREEN** 2026-09-18T18:53:47.401647+00:00: `PYTHONPATH=.:tests CUDA_VISIBLE_DEVICES=1 OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 PYTHONDONTWRITEBYTECODE=1 /home/u00134/bin/miniconda3/envs/vfsdgs/bin/python -m unittest -v test_multiscene_training` → exit 0; [04_GREEN.txt](tdd/04_GREEN.txt).

- 05 **RED** 2026-09-18T18:55:13.036856+00:00: `PYTHONPATH=.:tests CUDA_VISIBLE_DEVICES=1 OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 PYTHONDONTWRITEBYTECODE=1 /home/u00134/bin/miniconda3/envs/vfsdgs/bin/python -m unittest -v test_multiscene` → exit 1; [05_RED.txt](tdd/05_RED.txt).

- 05 **GREEN** 2026-09-18T18:56:28.232332+00:00: `PYTHONPATH=.:tests CUDA_VISIBLE_DEVICES=1 OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 PYTHONDONTWRITEBYTECODE=1 /home/u00134/bin/miniconda3/envs/vfsdgs/bin/python -m unittest -v test_multiscene` → exit 0; [05_GREEN.txt](tdd/05_GREEN.txt).

- 06 **RED** 2026-09-18T18:57:21.218372+00:00: `PYTHONPATH=.:tests CUDA_VISIBLE_DEVICES=1 OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 PYTHONDONTWRITEBYTECODE=1 /home/u00134/bin/miniconda3/envs/vfsdgs/bin/python -m unittest -v test_multiscene.MultisceneTests.test_qualification_runner_keeps_all_doses_and_stock_calibration` → exit 1; [06_RED.txt](tdd/06_RED.txt).

- 06 **GREEN** 2026-09-18T18:58:34.912906+00:00: `PYTHONPATH=.:tests CUDA_VISIBLE_DEVICES=1 OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 PYTHONDONTWRITEBYTECODE=1 /home/u00134/bin/miniconda3/envs/vfsdgs/bin/python -m unittest -v test_multiscene.MultisceneTests.test_qualification_runner_keeps_all_doses_and_stock_calibration` → exit 1; [06_GREEN.txt](tdd/06_GREEN.txt).

- 07 **RED** 2026-09-18T18:58:54.544184+00:00: `PYTHONPATH=.:tests CUDA_VISIBLE_DEVICES=1 OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 PYTHONDONTWRITEBYTECODE=1 /home/u00134/bin/miniconda3/envs/vfsdgs/bin/python -m unittest -v test_multiscene.MultisceneTests.test_grid_png_decodes_and_is_deterministic` → exit 1; [07_RED.txt](tdd/07_RED.txt).

- 07 **GREEN** 2026-09-18T18:59:12.128984+00:00: `PYTHONPATH=.:tests CUDA_VISIBLE_DEVICES=1 OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 PYTHONDONTWRITEBYTECODE=1 /home/u00134/bin/miniconda3/envs/vfsdgs/bin/python -m unittest -v test_multiscene` → exit 0; [07_GREEN.txt](tdd/07_GREEN.txt).

- 08 **RED** 2026-09-18T19:00:12.016560+00:00: `PYTHONPATH=.:tests CUDA_VISIBLE_DEVICES=1 OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 PYTHONDONTWRITEBYTECODE=1 /home/u00134/bin/miniconda3/envs/vfsdgs/bin/python -m unittest -v test_multiscene.MultisceneTests.test_quality_renders_compare_both_backgrounds_to_frozen_rgba` → exit 1; [08_RED.txt](tdd/08_RED.txt).

- 08 **GREEN** 2026-09-18T19:01:01.157383+00:00: `PYTHONPATH=.:tests CUDA_VISIBLE_DEVICES=1 OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 PYTHONDONTWRITEBYTECODE=1 /home/u00134/bin/miniconda3/envs/vfsdgs/bin/python -m unittest -v test_multiscene` → exit 0; [08_GREEN.txt](tdd/08_GREEN.txt).
