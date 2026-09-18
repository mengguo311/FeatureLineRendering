# Reproduction and retained artifacts

This directory is an immutable experiment record. Do not rerun producers into it:
they deliberately reject existing artifacts. A different camera convention,
eligibility resolution, dose, threshold, seed or recipe requires a new registration
and a separate output directory. The post-hoc diagnostic does not amend PREREG.

The starting repository commit was `6b098a5cb538fc4fc09d48d927dc97b77acc0b28`.
Commit `ab40ec9` froze PREREG, config and input hashes before the first training
launch. The config SHA256 is
`199f5a65bd8d3cd2a82fc31fc92c03f6508f98be125845792e2e963c52617e6b`.
The dataset paths, every camera matrix, photographs, split indices and all method
parameters are in config.json. Original inputs and prior reports are byte-hashed
in input_hashes.json. Phase 0 hashed all original TRAIN photographs, including
held-out DEV/TEST indices, without decoding them. Those held-out photographs were
never supplied to training, qualification, fitting or visual review.

## Runtime and exact source

The interpreter was `/home/u00134/bin/miniconda3/envs/vfsdgs/bin/python`:
Python 3.9.25, Torch 2.3.1+cu121, CUDA toolkit 12.6, NVIDIA A6000 GPUs.
All production worker commands, environment choices, timestamps and exit statuses
are retained in training manifests, launch claims and setup worker records.

The isolated clone under `vendor/gaussian-splatting` is pinned to
`472689c0dc70417448fb451bf529ae532d32c095`. It was cloned from Git objects, without
copying the dirty external worktree. Required submodules are rasterization
`59f5f77e3ddbac3ed9db93ec2cfe99ed6c5d121d`, GLM
`5c46b9c07008ae65cb81ab79cd677ecc1934b903`, and simple-knn
`44f764299fa305faf6ec5ebd99939e0508331503`. SIBR is not used.
`setup/seed_injection.patch` is the complete semantic upstream diff: only the
seed argument and Python/NumPy/Torch RNG injection. Every tracked source file and
the loaded binaries are hashed in `setup/training_source.json`.

The existing verified stock rasterization binary is at
`out/vrss/vendor/official_site/diff_gaussian_rasterization/_C.cpython-39-x86_64-linux-gnu.so`,
SHA256 `583e896f3aaa1c2dece9c67eaaa26d919f98aae0597591bf6693b9a19530e9e9`.
The isolated simple-knn extension was built with this environment:

```bash
CUDA_HOME=/usr/local/cuda-12.6 \
NVCC_PREPEND_FLAGS='--pre-include=cstdint --pre-include=cfloat' \
MAX_JOBS=2 TORCH_CUDA_ARCH_LIST=8.6 \
/home/u00134/bin/miniconda3/envs/vfsdgs/bin/python -m pip install \
  --no-build-isolation --no-deps --target out/multiscene_foundation/vendor/training_site \
  out/multiscene_foundation/vendor/gaussian-splatting/submodules/simple-knn
```

The first build lacked FLT_MAX; both build logs are preserved. Header preinclusion
repaired packaging without changing any upstream source. The read-only native
depth-layer helper was compiled with:

```bash
g++ -O3 -std=c++17 -shared -fPIC -fopenmp src/multiscene_layers.cpp \
  -o out/multiscene_foundation/setup/layers.so
```

The native compositing helper and stock wrapper are external dependencies hashed
in MANIFEST. `setup/layers.so` and all build artifacts remain server-side.

## Training execution

`setup/prepare_training.py` records the actual one-time administrative setup.
It calls tested functions in `src/multiscene_training.py`, stages only the 86
optimization and 16 validation images per seed, and writes eight manifests and
entry specifications. No initialization PLY was copied. Each official Scene
created its own 100,000-point random initialization after RNG injection.

For example, the Lego seed 1729 command recorded in its manifest is:

```bash
/home/u00134/bin/miniconda3/envs/vfsdgs/bin/python \
  out/multiscene_foundation/vendor/gaussian-splatting/train.py \
  -s out/multiscene_foundation/inputs/lego/seed_1729 \
  -m out/multiscene_foundation/training/lego/seed_1729/checkpoints \
  --eval --white_background --iterations 30000 --seed 1729 \
  --ip 127.0.0.1 --port 26009 --test_iterations 7000 30000 --save_iterations 7000 30000
```

Actual execution uses `scripts/multiscene_train_entry.py --spec <entry.json>`
under strace and Landlock. CUDA initializes before confinement; official
safe_state resets all RNGs afterward. The first eight launches failed before
Scene construction or optimization, were archived under `attempt_00_runtime_init`,
and were repeated only after the tested packaging repair. No failed-quality seed
was retrained. Only iteration 30,000 enters this experiment; iteration 7,000 is
retained as an unused official save, never selected by appearance.

Two detached Popen workers (`start_new_session=True`) executed these queues:

```bash
/home/u00134/bin/miniconda3/envs/vfsdgs/bin/python scripts/run_multiscene_training.py \
  --root out/multiscene_foundation --gpu 0
/home/u00134/bin/miniconda3/envs/vfsdgs/bin/python scripts/run_multiscene_training.py \
  --root out/multiscene_foundation --gpu 1
```

Each queue serializes four scenes, reserves one new training process per GPU,
checks at least 16 GiB free and 30 GiB disk before each launch, and waits 60 seconds
between insufficient-resource checks. Logs, resource samples and exit statuses
survive disconnects. Four CPU threads are allowed per training job. Other users'
processes were never signaled or modified. The route worker overlaps completed
seed-1729 qualification with the remaining training, using GPU 0 and two threads.

For a new full-training reproduction, make a separate checkout/output root and
clone the pinned source there; apply the exact patch above, build the same
extensions, then call `job_manifests(cfg, fresh_root, python)` and
`stage_training_data(dataset, job['data'], cfg)` for all eight jobs. The exact
administrative template is `setup/prepare_training.py`; change only its ROOT/out
path assignments in that *copied* template. Do not execute it on this archive.
Do not copy `inputs/*/*/points3d.ply`; those are outputs of the independent runs.
The frozen config still points to the original read-only dataset paths. New
training is stochastic GPU work and need not reproduce PLY bytes bit-for-bit.

## Qualification replay using the retained posteriors

The following creates a separate render replay with identical frozen parents.
It neither retrains nor overwrites this run. Run from the repository root; choose
an unused `replay` path. Large original PLY files must remain available.

```bash
replay=/home/u00134/3dgs_line/tier1/out/multiscene_foundation_replay
mkdir "$replay"
cp out/multiscene_foundation/config.json out/multiscene_foundation/config.json.sha256 "$replay/"
for scene in lego chair drums ficus; do
  for seed in 1729 2718; do
    mkdir -p "$replay/training/$scene/seed_$seed"
    cp "out/multiscene_foundation/training/$scene/seed_$seed/completion.json" \
       "out/multiscene_foundation/training/$scene/seed_$seed/completion.json.sha256" \
       "$replay/training/$scene/seed_$seed/"
    CUDA_VISIBLE_DEVICES=0 OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 \
      PYTHONDONTWRITEBYTECODE=1 /home/u00134/bin/miniconda3/envs/vfsdgs/bin/python \
      scripts/run_multiscene_qualification.py --root "$replay" \
      --scene "$scene" --seed "$seed" --stage quality
  done
  CUDA_VISIBLE_DEVICES=0 OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 \
    PYTHONDONTWRITEBYTECODE=1 /home/u00134/bin/miniconda3/envs/vfsdgs/bin/python \
    scripts/run_multiscene_qualification.py --root "$replay" \
    --scene "$scene" --seed 1729 --stage controlled
done
```

Check free GPU memory before each replay renderer and wait if below 6 GiB. The
durable original scheduling code is `scripts/watch_multiscene_routes.py`; its
launch and completion records provide the exact audited invocation for each stage.
The direct commands above show the computation, without reproducing strace logs.
Both background colors, every frozen view and all nine doses must be retained.

`POSTHOC_DIAGNOSTIC_PLAN.md` separately records the native800 and area-resized400
diagnostic. `scripts/watch_multiscene_diagnostic.py` ran all eight fixed posteriors
on GPU 1 after training completed. No diagnostic row contains an eligibility
override. Actual full-resolution panels and all metrics are retained.

## Checks and reports

The final targeted command and full repository command are preserved with exact
environments/times in `setup/final_test_runs.json` and TDD_LEDGER. They passed
28 and 89 tests respectively. Failed attempted GREEN runs are preserved; only
exit-zero runs constitute successful GREEN. Slices 01, 06 and 16 required fixes,
followed by 01_GREEN_FIXED, 07_GREEN and 16_GREEN_FIXED. Test-scoping/string-match
mistakes and the invalid save-sheet keyword were corrected without relaxing gates.
The audit helper extraction was the recorded refactor; no other refactor is claimed.

```bash
CUDA_VISIBLE_DEVICES=1 OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 \
  MKL_NUM_THREADS=4 PYTHONDONTWRITEBYTECODE=1 \
  /home/u00134/bin/miniconda3/envs/vfsdgs/bin/python -m unittest discover -s tests -v
```

Original assembly commands were `scripts/report_multiscene_prerequisites.py
--scene <scene>` for each completed scene, then `--final`. They reject existing
outputs. The final report refuses to complete if any scene has an eligible route
awaiting a local probe. `scripts/audit_multiscene.py --output <unused.json>`
rechecks all 36 native file-open traces. Bootstrap exceptions and the rejected
stale timestamp bytecode cache are disclosed in the audit; source fallback was
observed. No forbidden input was read in those stages.

`scripts/verify_multiscene.py` recomputes eligibility and report totals, checks
source/data/checkpoint hashes and initialization independence, verifies resource
and GPU queue records, decodes PNG pixels, counts actual MP4 frames, and CRC-checks
native NPZ archives. It writes exclusive verification artifacts. After final
documentation is staged, `--manifest` inventories all files; the read-only check is:

```bash
PYTHONDONTWRITEBYTECODE=1 /home/u00134/bin/miniconda3/envs/vfsdgs/bin/python \
  scripts/verify_multiscene.py --check-manifest
```

The successful pass verified 472 original input files, 1,594 tracked upstream
source files, 3,466 PNGs, all eleven existing repository MP4s (240 decoded frames
each), and 936 native NPZ archives. All 36 access traces passed. The first
administrative verification attempt stopped because ffprobe was not on PATH;
the second used the existing executable at
`/home/u00134/bin/miniconda3/envs/ts_diffusion/bin/ffprobe`, with its hash recorded
in VERIFICATION. Both attempt logs are retained. No scientific output changed.

MANIFEST excludes its own two files, Git object stores and transient __pycache__.
It includes exact paths, sizes and SHA256 for ignored checkpoints, arrays,
full-resolution PNGs, staged inputs, binaries and access traces. Small reports,
logs, contact sheets and plots are committed. The final post-push SHA equality is
recorded in `/home/u00134/codex_astra_multiscene_foundation_report.md` to avoid a
self-referential commit hash in this archive.

## Scope of the stop

No eligible registered parent survived reconstruction qualification, so no scene
local probe, surface audit, control comparison, glyph or video was reached.
The synthetic-tested local core is partial infrastructure, not a completed scene
method. End-to-end local controls and visual-stage orchestration were not run or
certified. No curve/UDF/stroke experiment or mesh evaluation was performed.
G2 manual and G5 remain UNCERTIFIED. Actual reached images are linked in
VISUAL_REVIEW.md; no schematic substitutes for an output.
