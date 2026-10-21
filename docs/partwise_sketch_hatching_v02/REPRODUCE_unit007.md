# unit007 reproduction

This unit follows unit006 NEXT: one actual rendered temporal audit of the complete GT lamp. The explicit asset is unit003 `inputs/selected.npz` (458 paths:260 shade,48 stem,150 base), the accepted base cleanup used as the unit004 baseline. It is not unit003's original608 `mixed.npz`, and it is not the rejected unit004 stem candidate.

Read the complete original outline and current orchestration BRIEF. The protocol is copied to unit007/PROTOCOL.json and committed before render evaluation. `SOURCE_LOCK.json` binds source and immutable inputs; `source_snapshot/` contains the exact worktree implementation. All cameras,18 geometry-selected IDs and thresholds are frozen; no test tuning. Inputs are authored GT with manual part/direction rules. Independent continuous-lathe geometry shares the authored recipe but never uses the candidate mesh depth to decide eligibility.

Use the authorized interpreter `/mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_8build_part_prior_feasibility_v03/venv/bin/python`. Prefix `PYTHONDONTWRITEBYTECODE=1`; the runners set CUDA visibility empty, one numeric thread and affinity[0,1]. `receipt_unit007.py NAME COMMAND...` captures the exact command, return code, log hash and elapsed seconds under unit007; it refuses log overwrite and limits each child to590 seconds. Execute serially. Historical directories and orchestration are read-only.

Stages:

1. `prepare_unit007.py`: once only; copy inputs, select IDs by geometry, freeze protocol and trajectories.
2. Necessary oracle/metric tests in `test_temporal_audit_unit007.py`; instrumentation regression in `run_unit007.py instrumentation` after source freeze.
3. `run_unit007.py freeze`, then `run_unit007.py render --sequence orbit --start 0 --stop 12` and `--start 12 --stop 24`; zoom uses `--sequence zoom --start 0 --stop 12`.
4. `run_unit007.py metrics`, `run_unit007.py media`, `visualize_unit007.py`, `validate_unit007.py`.
5. Actual image review and independent review; write separate software/temporal/visual/reconstruction claim statuses. Produce STATUS/NEXT/report, then SHA manifest and SEAL. Runtime logs are outside the scientific manifest; receipts bind their hashes.

A per-ID buffer is an actual raster pass using the full scene's depth, including self/other-part hiding. It is not a centerline-only substitute or an output inferred from unchanged anchors. The instrumented renderer is a separate copy; the inherited renderer's SHA remains unchanged. Isolated buffers are regressed against original `selected_ids` renders, and whole-lamp pixels against the original renderer. Equality is an implementation control; temporal criteria concern actual ink positions, missing/reappearance and independent visible-length coverage.

The diagnostic cannot establish H1/H2, reconstruction, whole-lamp perceptual flicker freedom, good density on the stem, or24FPS. Preserve original unit004 orbit19 density failure, inherited17 hidden-profile observations, rim-depth outliers and all original execution failures. No new local edit occurs in this camera-only audit; earlier local edit evidence is inherited, not retested or upgraded.
