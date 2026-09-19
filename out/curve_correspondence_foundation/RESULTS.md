# Curve correspondence foundation results

Core machine verdict: **STOP_CORRESPONDENCE**.

One frozen non-learning correspondence formulation; no mesh, neural field, GS retraining, ICP or per-asset scaling.

| Scene | Route | Segments | Candidate pairs | Selected pairs | Identity hypotheses | Image curves | GS curves | Verdict |
|---|---|---:|---:|---:|---:|---:|---:|---|
| lego | CONTROLLED_ONLY | 967 | 23039 | 295 | 7 | 3 | 1 | STOP_CORRESPONDENCE |
| chair | BOTH | 878 | 24845 | 305 | 3 | 2 | 1 | STOP_CORRESPONDENCE |
| drums | NONE | 0 | 0 | 0 | 0 | 0 | 0 | INSUFFICIENT_POSTERIOR_QUALITY |
| ficus | NONE | 0 | 0 | 0 | 0 | 0 | 0 | INSUFFICIENT_POSTERIOR_QUALITY |

## Exact primary and execution totals

| Quantity | Count |
|---|---:|
| arms | 75 |
| blinded_images | 264 |
| candidates | 47884 |
| canonical_mp4s | 14 |
| canonical_pngs | 2030 |
| core_scenes | 2 |
| gs_tracks | 2 |
| identities | 10 |
| image_tracks | 5 |
| independent_reviews | 0 |
| independent_seed_repeats | 1 |
| ineligible_stress_scenes | 2 |
| pairs | 600 |
| qualified_controlled_repeats | 18 |
| segments | 1845 |

These are primary F counts; repeated/ablation curves are not independent primary tracks. All arm counts and rejection reasons are in the per-scene records. Empty denominators cannot pass a gate.

## Machine gates

| Scene / arm | G1 yield | G2 prediction | G3 repeatability | G4 identity/nulls |
|---|---|---|---|---|
| lego / gs | FAIL | FAIL | FAIL | FAIL |
| lego / image_only | FAIL | FAIL | FAIL | FAIL |
| chair / gs | FAIL | FAIL | FAIL | FAIL |
| chair / image_only | FAIL | FAIL | FAIL | FAIL |

## Interpretation and review status

Necessary machine-gate failure is determinate even while visual review is pending. Zero independent reviews have occurred. The randomized review package is prepared, with keys outside it; no internal inspection is described as independent.

GS is a post-identity support/visibility veto in this formulation. Retained geometry is unchanged by construction; only error/coverage benefit could justify a frozen-GS claim. Image-only posterior invariance is structural, not measured GS evidence.

C and DEV score frozen outputs. All-in-frame scoring is conservative about occlusion, with denominators retained. Detector residuals are not geometric truth or independent semantic precision. Prior internal challenge boxes are coarse diagnostics only.

Drums and Ficus remain INSUFFICIENT_POSTERIOR_QUALITY; neither blocks the per-scene core machine verdict. Lego cannot claim independent-seed invariance. The failed corrected local-pixel baseline yielded zero accepted positions in both core scenes, including image-only.

This result tests the registered minimal formulation, not the impossibility of classical curve SfM. There was no threshold rescue, detector change, hand selection of successful tracks, gap completion or final UDF/stroke investment.

## Artifact access

See `scenes/SCENE/F/` for ordered extraction, every proposed candidate, alternatives, cycles, accepted/rejected fits, LOO arms and the F seal. `scenes/SCENE/C/` is the independent C reconstruction; `repeats/` holds every eligible posterior veto. `evaluation/SCENE/` contains per-view held-out predictions, repeatability, actual PNG/MP4 and review packages. Large compressed arrays/traces stay server-side and are exactly inventoried in MANIFEST.json.

Verification, access audit, raw RED/GREEN evidence and reproduction instructions are separate artifacts.
