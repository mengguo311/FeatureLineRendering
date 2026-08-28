# Stage 2 REDIRECT — Cross-Model Edge-Prior Invariance (CMEPI)

## Why NOT the two proposals on the table
1. **"Apply learned selectivity to permissive Canny base"** = a re-derivation of TRACK-M's
   TEED-mask-on-Canny (+0.2673 dP@1.5, chair f0.40). Zero new degrees of freedom. SKIP.
2. **Depth-free ELT (epipolar line triangulation)** = REJECTED. Your own NG-MEC Stage 1 proved
   geometric consensus is a ~7x weaker selectivity device than the learned prior (+0.0394 vs
   +0.2673), and is structurally anti-selective on lego (cull-purity ratio culled>kept,
   crease_recall_kept 0.70->0.27). ELT is more geometric-lifting apparatus on the same defective
   3DGS multi-view geometry; the risk/reward is bad and it endangers the temporal win.

## The frozen thesis this experiment tests
The peak finding is that a FROZEN ZERO-SHOT LEARNED edge prior (TEED/BIPED) buys rankable seeds
that move the f-frontier outward. OPEN QUESTION the paper must answer: is the lift a property of
**learned edge priors in general**, or is it **TEED-specific overfitting**? This is the single
highest-value, lowest-cost next result — it hardens the core claim and needs NO new geometry.

## Experiment: CMEPI
Swap the TEED detector for 2+ OTHER frozen zero-shot learned edge detectors, keep the ENTIRE
downstream pipeline (seeder, DT-pull, chaining, gates, eval) bit-identical. Candidates already
plausibly installable: **PiDiNet** and **DexiNed** (zero-shot, published weights). If a weight
download is blocked, fall back to any 2nd learned detector you can obtain zero-shot; do NOT
fine-tune anything (frozen-only, mesh-never-in-method-path preserved).

For each detector D in {TEED(control), PiDiNet, DexiNed}:
- Cache edges zero-shot (same white-bg compositing, same 100 views, same val/test split as TEED).
- Run the identical held-out f-frontier + LIFT_P computation on chair AND lego.
- Report per-detector: best LIFT_P and the f-range where LIFT_P>0; miss-set recovery; precision
  drop; and re-confirm the temporal win is untouched (published paths bit-identical).

## FROZEN GO/NO-GO (decide before running)
- **GO (invariance CONFIRMED)**: at least ONE non-TEED learned detector reproduces LIFT_P>0 for
  f in [0.30,0.50] on chair AND non-negative best-LIFT_P on lego. => the lift is a property of
  learned priors, not TEED. Strong paper claim.
- **NO-GO (TEED-specific)**: all non-TEED learned detectors give LIFT_P<=0 across f in [0.30,0.50]
  on chair. => the effect is TEED-specific; report honestly as a scoping caveat.
- **CONDITIONAL**: lift holds on chair but reverses on lego for all detectors => confirms the
  hard-surface headroom limit already seen; frame as texture-stress-specific.

## Invariants (do NOT violate)
- mesh only in mesh_oracle.py (EVAL only); method never imports it.
- held-out TEST eval for all headline numbers; val for tuning only.
- protect the temporal-coherence win (8.5-13.1x); published stroke paths must stay bit-identical.
- never fabricate; every number from a real result json/md.

## Reporting
Write out/CMEPI_RESULTS.md with the per-detector frontier table + the GO/NO-GO verdict.
