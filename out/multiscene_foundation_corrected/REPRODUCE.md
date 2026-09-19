# Reproduction and artifact map

This is the corrected, explicitly non-blind experiment. The previous experiment
remains UNDETERMINED. The frozen configuration SHA256 is
`b8e0ed851a16d4529f93fafafc3727346f2203a7e966a662adabf32cfa0463f6`.
Commit `fb4488e` froze and pushed PREREG.md, config.json, original input hashes and
unchanged TRAIN annotations before the first corrected qualification command.

## Environment and immutable dependencies

Use `/home/u00134/bin/miniconda3/envs/vfsdgs/bin/python` on this server. Exact
Python/library/compiler/GPU versions are recorded in setup/environment.json.
The stock rasterizer, pinned stock source, native replay and native layer query
libraries are the read-only archived dependencies in `out/vrss/`,
`out/point_feature_foundation/setup/` and `out/multiscene_foundation/`.
PRESERVED_INPUT_VERIFICATION.json hashes both archived experiments, all eight
iteration-30000 checkpoints, every frozen camera image and metadata input. No
posterior training is part of reproduction. Checkpoint paths/hashes are also in
config.json and MANIFEST.json. TEST remains sealed to scientific processes.

New native libraries are built with the exact commands in setup/build_native.sh.
That script refuses to overwrite live libraries. Independent rebuilds in
setup/build_verification/ matched all three original binary hashes exactly.
The optional fast_query binary is tested but is not used by scene inference.

## Execution order

All commands below run from the repository root. Do not rerun them over this
archive: scientific outputs use exclusive creation and intentionally fail if a
stage already exists. Use an isolated reproduction checkout with an empty
`out/multiscene_foundation_corrected/`, copy the frozen PREREG/config/hash files
and annotations into it, and provide the same read-only dependency paths. Keep
this archive intact. Do not rerun freeze_protocol.py to create new timestamps or
new scientific settings.

Set the following environment for scene stages:

```bash
export PYTHONDONTWRITEBYTECODE=1
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
export OMP_WAIT_POLICY=PASSIVE CUDA_CACHE_DISABLE=1 CUDA_MODULE_LOADING=EAGER
```

The durable execution records in setup/*_exit.json contain exact argv, environment
policy, timestamps and status. Each scientific child runs under a native-open
strace and installs its stage-specific Landlock allowlist before scientific
decoding of photographs or assets. Approved input bytes may be hashed while
constructing that allowlist; those opens are audited too. Use the worker scripts to preserve that confinement and
logging, rather than invoking an untraced fit as scientific evidence.

1. Run setup/qualification_worker.py with queue0 and queue1. Queue0 covers Lego
   and Drums; queue1 covers Chair and Ficus. Each evaluates both seeds at all
   16 TRAIN and 16 validation views on both backgrounds, followed by all nine
   unchanged controlled doses on all 16 TRAIN views and both backgrounds.
2. Run setup/local_worker.py with queue0 and queue1. It waits for qualification,
   computes per-scene eligibility, and runs every eligible route. Native layer
   precomputation can also use setup/precompute_layers.py; it reads native states
   only and never opens local photographic evidence. The main queue skips a
   completed layer stage without changing its contents.
3. For each eligible scene, the local order is parent layers, F primary, C, then
   layers/repeats for the eligible independent seed and every qualified dose.
   F contains GS, no-GS, shifted, shifted/no-GS, all eight LOO fits for both
   methods, and four nonzero query offsets for both methods. C contains the
   same-query GS/no-GS fits, independent C-native queries and both methods'
   offsets. Each posterior repeat contains GS plus all four nonzero offsets.
   Every fit uses the full wide box and unchanged search/refinement rules.
4. Run setup/evaluation_worker.py with queue0 and queue1. It waits for all local
   fits, then runs machine evaluation, surface diagnosis and actual visual
   diagnostics. Evaluators cannot write back into local outputs. DEV photographs
   are opened only by the visual evaluator after all F outputs are frozen.

Primary F processes initially used four isolated single-thread arm workers;
subsequent C/repeat stages use eight. These call the identical inference function.
Synthetic serial/eight-worker comparisons and completed scene serial/fork
comparisons are retained. All interrupted resource-repair attempts remain under
local/SCENE/attempt_* and setup/attempt_*; they are not pooled into scientific
totals. The earlier four-thread Chair run has tiny recorded eigen-derived numeric
differences but identical profiles, acceptance and rejection decisions. No result
was selected for improved science.

## Final independent verification

The end-of-run targeted and complete suites run in separate Python processes:

```bash
/home/u00134/bin/miniconda3/envs/vfsdgs/bin/python out/multiscene_foundation_corrected/tdd/record.py final_targeted VERIFY discover -s tests -p 'test_corrected*.py' -v
/home/u00134/bin/miniconda3/envs/vfsdgs/bin/python out/multiscene_foundation_corrected/tdd/record.py final_complete VERIFY discover -s tests -v
```

Every actual RED/GREEN command, status, test/source hash and raw log is recorded
in tdd/commands.jsonl and TDD_LEDGER.md. REFACTOR and regression-only checks are
identified honestly and are not retroactively called RED tests.

After all worker processes have finished, run these stages once in order:

```bash
/home/u00134/bin/miniconda3/envs/vfsdgs/bin/python scripts/verify_corrected_archive.py
/home/u00134/bin/miniconda3/envs/vfsdgs/bin/python scripts/snapshot_corrected_sources.py
/home/u00134/bin/miniconda3/envs/vfsdgs/bin/python scripts/audit_corrected.py --output out/multiscene_foundation_corrected/ACCESS_AUDIT.json
/home/u00134/bin/miniconda3/envs/vfsdgs/bin/python scripts/summarize_corrected.py
/home/u00134/bin/miniconda3/envs/vfsdgs/bin/python scripts/verify_corrected.py
```

The archive-hash stage may run earlier because its inputs are immutable; do not
rerun it over its existing exclusive output. SOURCE_PROVENANCE.json resolves
every stage's recorded repository Python source bytes to Git and preserves each exact
version, plus exact native binaries and the pinned vendor source. Later administrative and scheduling changes are not misrepresented as
having existed in earlier processes.

The final verifier checks all per-scene labels, complete local arm counts,
accepted/rejected/ambiguous totals and profile arrays, frozen F/C/repeat contents,
F-before-C/DEV timestamps, every access policy and interrupted attempt, original
hashes, PNG decoding and decoded MP4 frame counts. The 120-frame video trigger is
applied separately per scene; an unreached stage is explicit, never replaced by a
synthetic clip. The video encoder's regression fixture is not experiment evidence.

## Storage and review

Small reports, contact sheets, review packages, hashes, logs and source snapshots
are in Git. Full-resolution image sets, all native states/contribution layers,
all depth-profile arrays/mode records, large surface details, native-open traces
and any reached videos remain server-side. MANIFEST.json inventories every file,
its exact SHA256, byte size and storage class. Its own hash and the final reports
are sealed in FINAL_SEAL.json; these self-reference exclusions are explicit.

Each `evaluation/SCENE/visual/blinded_review/` contains randomized A/B copies,
references, preserved internal TRAIN annotations and a limitations inventory.
The identity key is `evaluation/SCENE/visual/review_identity_key.json`, outside
the package. Do not send that key to independent reviewers. Zero independent
reviews are claimed. G2 manual/G4 GS-benefit/G5 remain pending; necessary machine
failures remain determinate without those reviews.

The final external report records the final clean worktree and exact equality of
local HEAD, upstream and the remote branch after the last commit and push.

## Preserved continuation after the import repair

The original F fits all completed before a late old-PCA import failed. The exact
failed stage logs remain. setup/finish_controls_worker.py runs the separately
confined finish_corrected_F.py: it verifies all28 original arms, computes only
missing controls and checks every prior F artifact hash before/after. The final
F seal follows that completion, before C or DEV. The fix preloads the unchanged
PCA module; slice21 reproduces the directory-cache invalidation failure under
Landlock and then passes. Its first unsuccessful reproduction attempt is retained.

For the actual continuation, setup/repeat_worker.py queues C and all posterior
repeat jobs after the successful control-completion exit. Four independent jobs
per scene use24 CPUs per scene; each scientific arm remains single-threaded.
Every job retains the same confined runner and exact argv/status log. The original
local worker is retained as the sequential recipe; on a fresh checkout the fixed
preload avoids the historical error. Neither continuation reuses C evidence in F.
