# Corrected multiscene foundation results

Core synthetic scope: **STOP_B**. Lego and Chair are evaluated separately; no averaging rescues either.
Expanded cross-scene scope: **INSUFFICIENT_POSTERIOR_QUALITY**.

This is a known post-hoc sampling correction, not a blind experiment. The previous run remains permanently UNDETERMINED. No posterior was retrained.
Preregistration commit: `fb4488e`. Frozen configuration SHA256: `b8e0ed851a16d4529f93fafafc3727346f2203a7e966a662adabf32cfa0463f6`.

## Per-scene outcomes

| Scene | Eligible | Route A | Route B | Qualified doses | Invariance scope | Machine verdict | Queries | Modes | Accepted |
|---|---|---|---|---:|---|---|---:|---:|---:|
| lego | True | False | True | 9 | CONTROLLED_ONLY | STOP_B | 256 | 7368 | 0 |
| chair | True | True | True | 9 | BOTH | STOP_B | 256 | 8079 | 0 |
| drums | False | False | False | 8 | NONE | INSUFFICIENT_POSTERIOR_QUALITY | 0 | 0 | 0 |
| ficus | False | False | False | 8 | NONE | INSUFFICIENT_POSTERIOR_QUALITY | 0 | 0 | 0 |

## Machine gates

| Scene | G0 | G1 | G2 machine | G3 | G4 machine | G2/G4 benefit/G5 manual |
|---|---|---|---|---|---|---|
| lego | PASS | FAIL | FAIL | FAIL | FAIL | PENDING_INDEPENDENT_REVIEW |
| chair | PASS | FAIL | FAIL | FAIL | FAIL | PENDING_INDEPENDENT_REVIEW |
| drums | NOT_ELIGIBLE | NOT_ELIGIBLE | NOT_ELIGIBLE | NOT_ELIGIBLE | NOT_ELIGIBLE | NOT_REACHED |
| ficus | NOT_ELIGIBLE | NOT_ELIGIBLE | NOT_ELIGIBLE | NOT_ELIGIBLE | NOT_ELIGIBLE | NOT_REACHED |

G1 requires at least 64 spatially separated accepted positions. Empty outputs cannot pass repeatability or non-null controls through a 0/0 statistic. Manual gates are pending independent review; this does not defer a valid necessary machine-gate failure. No independent reviewer is claimed.

## Exact totals

| Quantity | Count |
|---|---:|
| DEV_calibration_views | 84 |
| DEV_controlled_rows | 144 |
| dose_rows | 1152 |
| doses | 36 |
| eligible_posteriors | 3 |
| eligible_scenes | 2 |
| local_accepted | 0 |
| local_ambiguous | 1417705 |
| local_arms | 175 |
| local_modes | 1585408 |
| local_queries | 44800 |
| local_raw_accepted | 0 |
| local_rejected | 1585408 |
| local_rejected_nonambiguous | 167703 |
| posteriors | 8 |
| qualification_calibration_views | 896 |
| qualified_doses | 34 |
| quality_rows | 512 |

Rejected counts include ambiguous modes; ambiguity and rejection-reason counts overlap other rejection reasons. Raw accepted modes precede delta separation; accepted positions follow it.

## Scope and limitations

- The native800/area400 correction was motivated by a known post-hoc diagnostic. Thresholds, scenes, seeds, all 36 doses and checkpoint identities remain frozen.
- Lego and Chair are separate core tests. Expanded generality requires at least three eligible scenes including Drums or Ficus; ineligible scenes are scope limitations, not scientific negatives for B.
- All image-quality groups and backgrounds remain required. A stock/native equality pass does not waive a separate native replay calibration failure.
- Image-only, old PCA, shifted-association and random-axis controls are reported with original denominators. Empty image-only output cannot support PIVOT_IMAGE_ONLY.
- The copied TRAIN annotations were authored by the implementing assistant and are not independent. G2 manual precision, G4 independently measured GS benefit and G5 review remain pending.
- The video stage is reached only when the per-scene G1 and G2 machine gates pass. Failure PNGs, all-mode projections and full-depth profiles are generated regardless.
- Resource-only interrupted attempts are retained. The final single-thread forked execution is compared with completed serial arms; the earlier four-thread eigensolver attempt has separately quantified floating-point differences.
- Local surface-sample fits are diagnostic only. They neither generate nor rescue any accepted linelet. No subsequent UDF or curve investment is authorized by a STOP_B result.

## Artifacts and verification

The full per-view quality, dose, calibration and eligibility records are in `quality/`, `controlled/`, and `scenes/`. Every completed local arm retains queries, all depth profiles and modes, accepted records, rejection reasons and coverage denominators under `local/`. Large arrays are server-side and inventoried in MANIFEST.json.
Per-scene `evaluation/SCENE/visual/` contains actual glyph contact sheets, fixed views, rejection/profile diagnostics and the blinded review package. The identity key is outside each package. Video status records whether the frozen per-scene G1/G2 trigger was reached. Empty output is displayed as empty output.
Native-open access audit: passed=True; forbidden successful opens=0. See ACCESS_AUDIT.json, VERIFICATION.json, TDD_LEDGER.md and REPRODUCE.md. All hash and media checks are machine-generated.
No UDF training, curve extraction, connection/smoothing, Bezier fitting, final strokes, mesh input or old-selector modification was performed.
