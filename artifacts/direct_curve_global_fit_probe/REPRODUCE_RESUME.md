# Resume execution and verification

The frozen PROTOCOL.md and INPUTS.json remain unchanged. This document supersedes only the old execution commands in REPRODUCE.md. The user authorized completion and commit/push after proof on direct-curve-global-fit-probe; the earlier preregistration's administrative no-commit instruction is retained verbatim for provenance.

Current detached session: `out/direct_curve_global_fit_probe/scheduler/resume_20260929_v2/`. LAUNCH.json records scheduler and status-watcher PIDs; each run's PROCESS.json identifies its GPU UUID. `STATUS.md` is updated every 30 seconds. Per-stage START/END/AUDIT JSON, stdout, strace and atomic completion seals are retained under `{run,rerun}/jobs/`. Source checking uses RESUME_IMPLEMENTATION_V2.json before and after each stage. Runtime accounting uses RESUME_BUDGET_BASELINE.json plus the shared job ledger, charging both run and rerun against the 12-hour scene ceiling.

The original launchers are preserved in `out/direct_curve_global_fit_probe/engineering/resume_20260929/`. Their current entrypoints forward to:

```
/home/u00134/bin/miniconda3/envs/vfsdgs/bin/python scripts/schedule_direct_curve_probe.py \
  --run run --gpu 0 --session resume_20260929_v2
/home/u00134/bin/miniconda3/envs/vfsdgs/bin/python scripts/schedule_direct_curve_probe.py \
  --run rerun --gpu 1 --session resume_20260929_v2
```

Both commands completed successfully on 2026-09-29 (rerun 12:16:03 UTC; primary 12:16:45 UTC). They are historical execution commands; do not execute them again. An existing session directory fails exclusive creation. A different session does not authorize a fit retry: the runner validates sealed fits and blocks partial canonical fits. Never reset, clean, delete or overwrite an output directory to make a command run. Existing partial evaluation attempts are archived only after the corrected full-domain calibration succeeds. They remain under `engineering/resume_20260929_v2/{run,rerun}/lego/evaluate_previous/`, with exact original hash inventories.

Build the new replay only into a new binary path if reconstruction is needed; never overwrite the preserved CPU binary:

```
/usr/local/cuda/bin/nvcc -arch=sm_86 -O3 -shared -Xcompiler -fPIC \
  src/direct_curve_quantiles.cu \
  -o out/direct_curve_global_fit_probe/setup/quantiles_cuda_v1.so
```

The current binary already exists and is hashed. Tests additionally use stock_oracle_v1.so, compiled from tests/direct_curve_stock_oracle.cu plus unchanged upstream forward.cu, with the upstream root and third_party/glm include directories. Do not use --use_fast_math or change compiler flags without a new complete calibration/provenance record.

The complete 226-test traced suite and audit are in logs/088_RESUME_COMPLETE_SUITE_226.log and SUITE_ACCESS_AUDIT_RESUME_226.json. Replay regressions are tests/test_direct_curve_replay.py; scheduler contracts are tests/test_direct_curve_scheduler.py. GPU tests must wait for an unowned GPU. The completed evaluation workers held one GPU each; check current ownership before any future GPU work.

The detached finalizer waited for both schedulers to finish. Its first attempt stopped on an audit filename mismatch; the existing passing audit was preserved under the explicit resume filename after its trace hash was checked. See DELIVERY_VERIFICATION_ATTEMPTS.md. The subsequent detached verification command is:

```
/home/u00134/bin/miniconda3/envs/vfsdgs/bin/python \
  artifacts/direct_curve_global_fit_probe/verify_resume_delivery.py \
  --session resume_20260929_v2 \
  --output out/direct_curve_global_fit_probe/scheduler/resume_20260929_v2/verification_v2
```

The proof output is exclusive and must not be reused. VERIFICATION_V2_EXIT.json records the subsequent attempt; the original failed VERIFICATION_EXIT.json and verification.log remain untouched. Final verification does not create a scientific or visual verdict. The report assembler requires passed engineering verification and a separate actual internal visual review covering all eight C views and both complete 33-frame arcs for every scene. Independent human visual approval remains unavailable and must not be invented.

The original summarize.py, verify_delivery.py and write_report.py are retained as historical administrative scripts; they reference superseded implementation/testing/runtime assumptions. Use the resume verification/report scripts for this execution.

Final verification_v2 completed with exit 0 and all 570 checks passing. The completed report and gallery were assembled with:

```
/home/u00134/bin/miniconda3/envs/vfsdgs/bin/python artifacts/direct_curve_global_fit_probe/report_resume.py --proof out/direct_curve_global_fit_probe/scheduler/resume_20260929_v2/verification_v2 --review artifacts/direct_curve_global_fit_probe/VISUAL_REVIEW.json
/home/u00134/bin/miniconda3/envs/vfsdgs/bin/python artifacts/direct_curve_global_fit_probe/curate_resume.py --proof out/direct_curve_global_fit_probe/scheduler/resume_20260929_v2/verification_v2
```

These output paths now exist; exclusive creation intentionally prevents rerunning these commands over delivered evidence. DELIVERY_RESUME.json records actual results and artifact hashes. REPORT_ASSEMBLY_NOTES.md documents the pre-unblinding bookkeeping correction. The audit_resume_suite.py helper now defaults to the explicit resume trace/name and exclusive output creation; audit_suite.py and the older report helpers are retained only as historical scripts.
