# Reproduction and artifact access

The final machine decision is `STOP_CORRESPONDENCE` for each core scene. Start with
RESULTS.md, DISCUSSION.md and results.json. Exact scene measurements are in
evaluation/SCENE/metrics.json; VERIFICATION.json checks execution validity, not
scientific success. FINAL_SEAL.json records the final manifest check.

Preregistration commit: `ea3e94d`. Starting HEAD:
`42158159a037fee1b14c5ba2d8a7e5271ec1bc36`. Frozen config SHA256:
`43be7698069b27e36251e4cb377b4309a2e06fea39ee3329b101e0c8e75811fd`.
The preregistration was pushed before scene execution. No generated curve existed
when its thresholds, splits, controls and outcomes were committed.

Use `/home/u00134/bin/miniconda3/envs/vfsdgs/bin/python` (Python 3.9), with versions
in setup/environment.json. Every scientific worker sets OMP, OpenBLAS and MKL to
one thread. strace and Linux Landlock ABI >=3 are required. Scene inference and
visibility queries use CPU and inherited native libraries/caches; the complete
legacy test suite also exercises CUDA. No GS is retrained. No model/agent routing
override was performed or claimed by the scripts.

## Read-only verification of this completed archive

From `/home/u00134/3dgs_line/tier1`:

```bash
PYTHONDONTWRITEBYTECODE=1 /home/u00134/bin/miniconda3/envs/vfsdgs/bin/python out/curve_correspondence_foundation/setup/seal_archive.py --verify
git status --porcelain
git rev-parse HEAD
git rev-parse '@{upstream}'
git ls-remote origin refs/heads/curve-correspondence-foundation
```

The manifest inventories every regular file and symlink inside this experiment,
including large server-side arrays, native-open traces and MP4 files. Symlinks are
inventoried by their literal target strings; they are not recursively followed.
The private repository-suite mirror therefore does not reopen sealed input images.
MANIFEST.json, its SHA sidecar and FINAL_SEAL.json are explicit self-reference
exclusions. The git checkout alone is insufficient for reproduction: obtain the
exact server-side entries in MANIFEST.json and the pinned external inputs in
input_hashes.json and PRESERVED_INPUT_VERIFICATION.json. Never substitute a new
posterior, dose, camera convention or image detector.

## Exact generation sequence in an isolated replica

Workers use exclusive creation and refuse to overwrite existing outputs. Do not
rerun them over this archive. A replay needs an isolated filesystem replica at the
same absolute paths with the frozen input archives present and this experiment's
generated scenes/, evaluation/ and visibility/ directories absent. Retain code,
tests, config, preregistration and input inventory. Replayed run timestamps differ;
compare numeric arrays, curve IDs, topology and hashes of deterministic data.

These are the executed command forms (the scheduler records every expanded child
command, environment, start/end timestamp and exit status in setup/*_exit.json):

```bash
/home/u00134/bin/miniconda3/envs/vfsdgs/bin/python out/curve_correspondence_foundation/setup/worker.py lego
/home/u00134/bin/miniconda3/envs/vfsdgs/bin/python out/curve_correspondence_foundation/setup/worker.py chair
/home/u00134/bin/miniconda3/envs/vfsdgs/bin/python out/curve_correspondence_foundation/setup/evaluation_worker.py lego
/home/u00134/bin/miniconda3/envs/vfsdgs/bin/python out/curve_correspondence_foundation/setup/evaluation_worker.py chair
/home/u00134/bin/miniconda3/envs/vfsdgs/bin/python out/curve_correspondence_foundation/setup/visibility_worker.py lego
/home/u00134/bin/miniconda3/envs/vfsdgs/bin/python out/curve_correspondence_foundation/setup/visibility_worker.py chair
```

Each scene scheduler executes F primary/controls/eight LOO arms, seals F, executes
independent C reconstruction, and applies all qualified posterior vetoes. The
evaluator verifies those seals before opening F/C/DEV photographs. The visibility
worker reads frozen projections and hash-verified inherited contribution layers.
Supplemental visibility is diagnostic and cannot rescue all-in-frame gates.
Lego and Chair use identical thresholds. Drums and Ficus are explicitly ineligible.
The failed first Lego display attempt is retained; all numerical metrics and
sample arrays are byte-identical to the completed display run.

## Tests and audit

TDD_LEDGER.md links exact observed RED/GREEN commands, raw logs and source hashes.
The final targeted suite contains 45 tests; the complete unchanged repository
suite contains 127 tests. The latter recompiles an old binary as part of a test,
so it ran in setup/repository_suite, with all 578 mirrored source files verified
byte-identical and the original repository read-only. The private approved stock
renderer is also byte-identical. No test was filtered or skipped.

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=out/curve_correspondence_foundation/code:out/curve_correspondence_foundation/tests:. OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 /home/u00134/bin/miniconda3/envs/vfsdgs/bin/python -m unittest discover -s out/curve_correspondence_foundation/tests -v
CUDA_VISIBLE_DEVICES=1 PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 /home/u00134/bin/miniconda3/envs/vfsdgs/bin/python out/curve_correspondence_foundation/setup/run_repository_suite.py
```

Use a replica when rerunning tests that mutate the private mirror. The initial
complete-suite wrapper failure and its passing corrected execution are both kept.
In a fresh replica, create that mirror first with `setup/prepare_repository_suite.py`;
it copies the approved renderer and the one recompilable binary while linking
other archive dependencies read-only.
ACCESS_AUDIT.json covers 28 scientific traces including the failed display attempt.
Only exact pre-policy bootstrap exceptions are allowed; nine supplemental-worker
Python caches have independently checked source-equivalent code objects and
recorded hashes. No real TEST bytes or mesh enters matching, fitting or scoring.
Forty sealed TEST paths were deliberately skipped by administrative preservation
hashing; this is not a claim that their bytes were newly verified.

## Review package

`evaluation/SCENE/visual/` contains native, fixed-cardinality and attempted fixed-ink
F/C/DEV projections, stable-color overlays, extraction/candidate/cycle/rejection
sheets, coarse failure regions and 120-frame MP4s. There are 132 randomized images
per scene in `visual/blinded_review/`; keep `visual/review_identity_key.json` away
from reviewers. The MP4s are diagnostic projections of fixed geometry on white,
without new orbit visibility renders or RGB truth. Ink tolerance failures are
explicit in comparison_selection.json. Zero independent reviews have occurred.
