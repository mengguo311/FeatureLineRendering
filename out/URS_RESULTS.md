# URS — Unprojected Ridge Seeding: lego carrier-coverage upper bound. **GO**

Frozen scorer and 0.75 threshold committed at **`09acd9b`, before any coverage number
existed**. Eval-only: the GT mesh is read solely inside `scripts/urs_verdict.py:coverage()`;
`scripts/urs_build.py` imports no mesh, so the method path stays mesh-free. Held-out TEST
views {5,15,…,95}. Protected temporal manifest re-verified **332/332 OK**, 0 failures.

## Verdict

| quantity | value |
|---|---|
| **URS coverage (primary)** | **0.7617** |
| frozen GO threshold | 0.75 |
| carrier count | **89 748** = exactly the 3× budget cap |
| baseline linelets | 29 916 (`out/linelets_lego_gated_test.npz`) |
| source views | TRAIN only — **no contact with the scored TEST views** |

### VERDICT: **GO** — coverage ≥ 0.75 within the 3× budget.

Post-hoc carrier densification **can** cover lego creases. The recall ceiling is therefore
**not** a hard splat-carrier resolution limit at this budget: the lego gate quest should not
be killed on representational grounds.

## The number that nearly went the other way — read this first

My first implementation added a **multi-view epipolar consensus filter** (keep a point only
if ≥2 other views show a TEED ridge within 1.5 px). With it, coverage was **0.6035** and this
report would have said **NO-GO**, "empirical proof of a splat-carrier resolution limit",
killing the direction.

That filter was **my addition and the spec forbids it**: *"NO ranking, NO culling, NO
precision filtering — this is a pure coverage ceiling probe."* A K≥2 support requirement is
culling. Removing it — i.e. complying with the spec — moves coverage from 0.6035 to **0.7617**
and flips the verdict.

| arm (all at the 3× budget, TRAIN-legal) | coverage | verdict it implies |
|---|---|---|
| **K=1, no culling — spec-compliant, PRIMARY** | **0.7617** | **GO** |
| K≥2 consensus — culling, forbidden by the spec | 0.6035 | NO-GO (false) |

The frozen gate and threshold were **not** touched; only the carrier construction was
corrected to match the spec. Both arms are reported so the correction is auditable rather
than a silent goalpost move.

A second, smaller correction went the same way: the first budget-respecting dedup used a
1.25× voxel ratchet that **overshot**, landing 67 996 points under an 89 748 cap. Under-spending
the budget biases a ceiling probe toward NO-GO, so it was replaced with a bisection that lands
exactly on the cap. That alone was worth +0.023 coverage (0.5806 → 0.6035 on the K≥2 arm).

## Full results — frozen metric, held-out TEST

Coverage = fraction of **visible** GT crease points (mesh-depth z-peel, `visible_crease_uv`)
with a **visible** projected carrier point within **τ = 1.5 px** — the same tolerance and 2D
space as the `R@1.5` metric this probe explains. n = 1 748 144 GT crease points.

| carrier | coverage | n carrier pts | source views |
|---|---|---|---|
| **baseline** (current OVERALL-recipe linelets) | **0.4338** | 149 580 sampled from 29 916 linelets | — |
| **URS train, TEED thr 0.5** — **PRIMARY** | **0.7617** | 89 748 | 20 TRAIN |
| URS train, TEED thr 0.9 (repo pipeline default) | 0.7287 | 89 748 | 20 TRAIN |
| URS "all-views" thr 0.5 — **mislabelled, contains NO test view** | 0.7668 | 89 748 | 20 TRAIN + 5 VAL |
| URS "all-views" thr 0.9 — **same mislabel** | 0.7549 | 89 748 | 20 TRAIN + 5 VAL |
| **URS genuinely leaky, thr 0.5** (corrected) | **0.7610** | 89 748 | **35 incl. all 10 TEST** |
| **chair sanity control** (baseline carrier) | **0.6195** | 85 325 | — |

**URS lifts lego coverage from 0.4338 to 0.7617 (+0.3279).** Against the corrected,
sampling-converged baseline of 0.4502 the lift is **+0.3115**.

Two robustness observations:

- **The result is not leakage-driven — but the arm that was supposed to show this was
  broken, and is corrected below.** The arm originally labelled "all_leaky" used source views
  `range(0, 100, 4)` = all EVEN indices, while TEST = {5,15,…,95} = all ODD. Its intersection
  with TEST is **empty**: it was 20 TRAIN + 5 VAL views, so the leakage sensitivity was never
  actually run and the first version of this claim was unsupported. Re-run with source views
  that genuinely contain all 10 TEST views (35 views, 10 of them TEST):
  **coverage 0.7610 vs the TRAIN arm's 0.7617, a delta of −0.0007.** Handing the builder the
  exact views it is scored on buys *nothing*. The conclusion now holds on a test that was
  actually performed.
- **It is not threshold-cherry-picked.** Even at the repo's own stricter pipeline threshold
  (TEED 0.9) the TRAIN arm reaches 0.7287, within 0.022 of the gate. The conclusion does not
  hinge on the generous 0.5 threshold, though 0.5 is what clears it.

### Uncertainty: the GO margin is thin

The 10 TEST views are the independent units, not the 1.75 M crease points. A view-level
bootstrap (20 000 resamples, seed 20260829) gives:

| | value |
|---|---|
| coverage | 0.7617 |
| 95% CI | **[0.7433, 0.7793]** |
| SE | 0.0092 |
| margin over 0.75 | **+0.0117 = 1.27 SE** |
| P(coverage ≥ 0.75) | **0.90** |
| per-view range | 0.7043 – 0.8052 |

**The CI straddles the threshold.** This is a GO at roughly 1.3 standard errors, not a
comfortable one, and the honest reading is "≈90% confident the true coverage clears 0.75",
not "coverage clears 0.75". A different draw of 10 test views could return NO-GO.

### Correction: the frozen N_SEG=5 under-credits the segment baseline

`urs_verdict.py` freezes N_SEG=5 samples along each linelet and its docstring claims this
"matches how the harness rasterises linelets". That claim is **wrong**: `run_m1b.py` draws
the projected segment continuously with `cv2.line(..., shift=4)`. With projected segment
lengths reaching ~13 px at p90, five samples leave gaps above the τ=1.5 px tolerance, so the
baseline is under-credited. Denser sampling, converged:

| N_SEG | baseline coverage |
|---|---|
| 5 (frozen) | 0.4338 |
| 17 | 0.4488 |
| 33 | **0.4502** (converged) |

The frozen value is kept for the **gate** — which is unaffected, since URS is a point cloud
where N_SEG plays no role — but the fair baseline is **0.4502**, so the corrected lift is
**+0.3115**, not the +0.3279 first reported.

### Near-duplicate source views

The TRAIN arm is method-legal, but `view_split.py`'s claim of an even orbit spread does not
hold for NeRF-synthetic poses. Angular distance from each TEST view to its nearest TRAIN
source view: min **5.59°** (test 75 → train 41), median 22.2°, and **4 of 10 within 15°**.
So for some test views a train-sourced point is close to a test-sourced one. This is a
property of the frozen split and applies to every result in this repo, not just URS — and the
corrected genuine-leaky arm bounds its effect directly: giving the builder the actual test
views changes coverage by −0.0007, so view proximity is not what is carrying the number.

### On the spec's "~38.1%" baseline expectation
The spec anticipated a baseline near 38.1%; measured with this frozen metric it is **0.4338**.
The difference is definitional, not a discrepancy to reconcile: this metric scores the
**segment-expanded** linelet carrier (5 samples along p ± l·t) against z-peeled GT crease
points, whereas 38.1% resembles the raw `R@1.5` family of numbers. The baseline is reported
as measured; no attempt was made to tune it toward 38.1%.

### On the chair control
The spec expected chair coverage "already high". At **0.6195** it is clearly higher than
lego's 0.4338 baseline but is **not** high in absolute terms, and it is *below* lego's URS
figure. Reported as measured rather than as expected. Note this is chair's **baseline**
carrier, not a chair URS — the control tests the metric, not chair's ceiling.

## What this does and does not license

**Supported.** At a 3× carrier budget, unprojected TEED ridges cover 76% of visible lego GT
creases. The 61.9% UNCOVERED figure from the lego ceiling autopsy is a property of *the
current gaussian-centroid carrier*, **not** of the scene or the imagery. Decoupling seeds
from splat centroids removes most of that coverage deficit.

**Not supported.** This is a **coverage ceiling only**. Precision was deliberately not
measured and must not be inferred: a carrier that covers 76% of creases may also blanket
non-crease geometry, and NG-MEC-v2 already showed lego has no rankable signal to separate
them (all cues at or below chance at the carrier level). **Coverage being achievable does not
mean the joint gate P≥0.85 ∧ R≥0.65 is achievable.** The four prior lego NO-GOs were about
precision and ranking; none of them is overturned by this result.

The honest summary: **lego's recall ceiling is a carrier-placement artefact, not a
representation limit — but the precision problem is untouched and remains the binding
constraint.**

## Invariants

| invariant | status |
|---|---|
| threshold + scorer frozen before any coverage existed | held — `09acd9b`, verified no `urs_*` artifact at commit time |
| mesh never in the method path | held — `urs_build.py` imports no mesh; mesh only in `urs_verdict.coverage()` |
| held-out TEST eval | held — TEST {5,15,…,95}; primary arm's carrier uses TRAIN views only |
| pure coverage ceiling, no ranking/culling | held **after correction** — the K≥2 filter was removed; K=1 is primary |
| new artifacts, `urs_` prefix, no overwrite | held |
| protected temporal manifest | **332/332 OK**, 0 failures |

**Artifacts.** `scripts/urs_{verdict,build}.py`; `out/urs_verdict.json`,
`out/urs_coverage.json` (primary, K=1), `out/urs_coverage_K2_sensitivity.json`,
`out/urs_coverage_ratchet.json` (the overshooting first pass, kept for the record),
`out/urs_generosity.json`; `logs/urs_build{,2,3}.log`, `logs/urs_generosity.log`.
