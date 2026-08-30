# URS — Unprojected Ridge Seeding: lego carrier-coverage upper-bound probe

## Why
NG-MEC-v2 = 4th independent NO-GO on lego's joint gate (P>=0.85 & R>=0.65).
Lego ceiling autopsy: recall gap is 61.9% UNCOVERED (carrier never places a
linelet near the GT crease = REPRESENTATIONAL) + 31.5% covered-but-culled.
Pipeline already realizes 91.2% of what it covers-and-ranks. So the binding
term is CARRIER COVERAGE, not ranking. Before we abandon the gate quest and
frame the paper as temporal-core + K_geom + negative characterization, run ONE
decisive representational upper-bound: can post-hoc carrier densification even
COVER the lego creases, given an unlimited-ranking budget?

## Experiment
Seed carrier linelets from MULTI-VIEW EPIPOLAR INTERSECTIONS of TEED ridges,
DECOUPLED from Gaussian splat centroids (do NOT snap seeds to gaussians; place
them where the triangulated TEED ridges land in object space). NO ranking, NO
culling, NO precision filtering — this is a pure coverage ceiling probe.

- Scene: lego, held-out TEST views (same split the harness scores).
- Coverage metric: fraction of visible GT crease points within tau=1.5px of a
  projected carrier linelet (mesh oracle, EVAL-ONLY — method path imports no mesh).
- Budget cap: total linelet count <= 3x the current OVERALL-recipe baseline.
- Report current baseline coverage (~38.1%) recomputed with THIS metric as the
  control, plus the URS coverage, plus linelet counts for both.

## FROZEN go/no-go (commit the verdict script + threshold BEFORE scoring, as with 076a6aa)
- GO  : lego raw geometric coverage >= 0.75 at <= 3x baseline linelet count.
- NO-GO: coverage < 0.75. => Empirical proof of a splat-carrier resolution
  limit; kill the lego gate quest; the paper's negative result is now measured,
  not asserted. Next compute goes to cross-model edge-prior invariance
  (PiDiNet/DexiNed zero-shot) to harden the temporal CORE.

## Invariants (all must hold)
- mesh NEVER in method path (epipolar TEED intersection uses no mesh; mesh only
  in the eval-only coverage scorer).
- held-out TEST eval; freeze threshold + scorer BEFORE any coverage number exists.
- protected temporal manifest must re-verify OK (this probe adds carriers; do
  not touch the protected linelet sets — new artifacts only, `urs_` prefix).
- report chair coverage too as a sanity control (expect it already high).

Write results to out/URS_RESULTS.md + out/urs_verdict.json. Commit the frozen
verdict script first, then results.
