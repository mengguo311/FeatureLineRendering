# r07: source SH angular-appearance counterfactual

Three native source-only render arms keep geometry, effective covariance, filter,
opacity, sorting and camera identical: full SH, DC-only color evaluation and
full SH evaluated at a fixed DEV direction. Original PLYs and C8 lines are read-only.
DC is not recovered albedo. The RGB conditional classifier, proxy seed UVs and
masks are inherited unchanged from r03. No new source group or styled model.

Use the existing official_code_fix_v01/env/bin/python with `-B`.
Commands and complete results are in the HDD round07 RUN_COMMANDS.md and REPORT_ZH.md.
`verify.py --readonly --replay` independently repeats 36 renders, nine density
fits, 36 predictions and 12 correspondence checks. Never overwrite a sealed receipt;
redirect stdout to a new task-owned file.

25 new tests: `test_runner_final.py`. All five feature API groups retain actual
RED/GREEN logs. Display-only failures are preserved. Original delivery.py is frozen;
deliver_repair.py adds white padding to mixed native sizes without resampling.
Early DTU figure legend is erroneous; use delivery/native/*/FULL_CORRECTED.jpg.
Class 1 is peripheral-horizontal proxy, class 2 central-nonhorizontal proxy,
not object foreground/background ground truth.

Scientific result PARTIAL: DC improves some Ficus pot glare misclassification,
but test79 worsens UNKNOWN, anchor can degrade severely, and DTU whole-subject gates
remain failed. No C/D/NPR promotion. Original baseline remains the rollback entry.
The next scalar-illumination hypothesis is a proposal only; do not execute it from
this round. The runner may resume after checking the sealed status, until 07:40 JST;
08:00 JST is the hard overnight stop. Local commit only; no push/merge.
