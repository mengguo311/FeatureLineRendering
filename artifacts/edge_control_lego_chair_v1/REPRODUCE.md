# Actual Lego / Chair pilot

Use `/home/u00134/bin/miniconda3/envs/vfsdgs/bin/python`, GPU0, CPU2. No global packages/configuration are installed. Stage-only writes: `experiments/edge_control_lego_chair_v1`, `artifacts/edge_control_lego_chair_v1`, ignored `out/edge_control_lego_chair_v1`. The pre-existing task launch commit follows base `abe73412cb828ad8c3b1fe83cf6f1d238a32d506` and is preserved.

`DATA_FREEZE.json` enumerates all original TRAIN and actual GS TRAIN indices, all prior F/C/arc usage, selected 8/4/8 roles, exact camera matrices/FOV/K at512 (source800), source model/config/manifests and hashes. The requested hybrid `artifacts/hybrid_raster_evidence_v2/INPUTS.json` is absent; the resolved `artifacts/direct_curve_global_fit_probe/INPUTS.json` exactly matches the hybrid parameter-lock input SHA. Original TEST images never enter this stage; edit-holdout uses original TRAIN already seen by GS, scored read-only after authentic scene/model/dev/target/selection seals. It remains exploratory.

RGB matches source TRAIN preprocessing: composite RGBA on white in display RGB with float64, quantize to byte, RGB PIL BICUBIC reduction to512. Alpha coverage is independently bilinear-reduced from original RGBA. Native RGB keeps full degree3 and stock projected covariance0.3 floor; no historical RaDe SH0 render cache is used. `adapter.py` imports the unchanged upstream Graphdeco wrapper bound to v1's isolated `onec_stock_C.so` and KNN binary, read-only. Source training commit is472689c0dc70417448fb451bf529ae532d32c095. Source locations and native binary hashes are recorded in data/source freezes.

Run tests from worktree root:

```bash
OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 MKL_NUM_THREADS=2 PYTHONDONTWRITEBYTECODE=1 /home/u00134/bin/miniconda3/envs/vfsdgs/bin/python -m unittest discover -s experiments/edge_control_lego_chair_v1/tests
```

Actual RED->GREEN logs live in `tests/`; tests cover SH header degree, UID mapping, selected-only DC projection, frozen permissions, holdout seal enforcement, oblique/circle normals, texture and lowcontrast rejection, full-SH real Chair rendering, exact full alpha Jacobian mass, and real coverage-to-scale gradient. `results/*native_calibration.json` additionally verifies both real scenes against stock official Camera/render, Python full-SH conversion, random full-weight adjoint residual, and distinguishes degree3 from degree0.

On a fresh isolated stage, generate metadata without opening edit-holdout images, then launch exactly one independent process:

```bash
OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 MKL_NUM_THREADS=2 PYTHONDONTWRITEBYTECODE=1 /home/u00134/bin/miniconda3/envs/vfsdgs/bin/python -c "import sys;sys.path.insert(0,'experiments/edge_control_lego_chair_v1/src');from data import freeze_data;freeze_data()"
/home/u00134/bin/miniconda3/envs/vfsdgs/bin/python experiments/edge_control_lego_chair_v1/scripts/launch_production.py
```

Launcher uses `subprocess.Popen(..., start_new_session=True)`, records PID, refuses duplicate live PID or existing source seal. Runner holds an exclusive production lock, checks frozen source hashes, and checks live GPU ownership before each unit; foreign GPU0 jobs are waited for and never signalled. Disk gates recalculate root≥4GiB, commonGit≥1.5GiB, aggregate new-stage≤16GiB; current GPU/disk values are recorded every unit rather than treating initial values as constants.

`PRODUCTION.log`, `EVENTS.jsonl`, `STATUS.json`, per-scene progress/FINAL, and epoch edit deltas are durable. All editable payloads are copy-on-write NPZ deltas referencing the source PLY SHA and original row IDs; source full PLY is never modified or uploaded. A failed scene does not suppress initial B0 or the other scene. Completed stage must not be blindly relaunched: inspect seals and logs; for a scientific rerun use a new stage/run identifier preserving all existing evidence. If production fails, preserve existing freezes, explicitly version a source correction, verify dependencies and completed units before resuming; do not overwrite frozen scientific evidence.

Per scene: original B0; zero-step display-DC projection diagnostic; 336-step relative color and color+scale/rotation; same-permission full-image L1/SSIM ordinary controls at336; separate controls matched to actual optimizer wallclock; band2d and visibility/mass-stratified random selectors using the identical bounded covariance operation/count. Position/opacity/higherSH stay byte-exact, labels are unavailable rather than invented. Full 8-view training objective is evaluated every epoch. All development and read-only holdout metrics include full fixed RGB band, nonband/allforeground/AA outline, holes, full parameter audit and common valid normal profiles. No R1 linear full-SH assumption, planar oracle, R4 probe, new TaskB targets, or author COB-GS claim.

Figures include four distinct actual cameras per scene/role with exact subplot keys and native edge crops. Videos reuse the complete prior33-camera arc and additionally render a full360-degree visualization-only orbit33, each for B0, color, covariance and ordinary covariance. Encoding uses read-only v1 FFmpeg, H264/yuv420p/faststart,512 wide. `results/*media*.json` records camera hashes, native PNG hashes and full-frame decode hashes; all33 decoded frames must be distinct. Image RGB is native; overlays are labelled diagnostics based on selected contribution in full-model transmittance. There is no per-frame ink overlay in result RGB.

`SOURCE_MAP.json`, per-scene FINAL and aggregate FINAL enumerate actual runs, checksums, timings and remaining independent human visual review. Curated new code/docs/metrics/media only are published by SSH to exact branch `edge-control-lego-chair-v1`; raw deltas/models/native arrays/log caches stay ignored on server.
