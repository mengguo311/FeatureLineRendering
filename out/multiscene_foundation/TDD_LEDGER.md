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
