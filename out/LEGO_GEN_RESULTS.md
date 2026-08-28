# LEGO-GEN — does the chair frontier-lift generalize to lego? **GO** (with one caveat stated up front)

Scorer and thresholds frozen and committed at **`4eef815`, before any lego number was read**.
Metric is the **exact chair XMEP primary metric, unchanged** — no lego-specific recall-band
renormalisation. Held-out TEST views only, nothing tuned on TEST. Mesh strictly eval-only
(`tune_lib.Harness` → `mesh_oracle`); method path mesh-free. Protected temporal manifest
**332/332 OK**.

This is **decoupled from the absolute P≥0.85 ∧ R≥0.65 gate**, which the lego ceiling autopsy
showed is unreachable in principle (36.6% of visible GT creases have no frozen-3DGS carrier
within τ). That ceiling is its own finding; it is not chased here.

## Verdict

| criterion | threshold | measured | result |
|---|---|---|---|
| mean LIFT_P over f∈[0.22,0.50] | ≥ +0.030 (GO), < +0.010 (NO-GO) | **+0.0346** | **PASS** |
| per-view consistency, dP>0 at matched f | ≥ 80% of TEST views | **100% (10/10)** | **PASS** |

### CALL: **GO** — the rankable-seed lift is scene-general, not a chair-only artifact.

## The caveat, stated before the good news

**The mean rests on a single in-reach f value.** Of the 6 in-band rows, **5 are excluded** by
the frozen metric because TEED reaches recalls Canny cannot reach at any f≤0.50, so the
interpolated `canny P@same R` is undefined there. Only f=0.22 survives, so "mean" = one point.

If instead **all 6 in-band rows** are counted via the honest lower bound `LIFT_P_lb`
(Canny's precision at its own maximum recall), the mean is **+0.0281 → PARTIAL**, below the
+0.030 bar.

| accounting | mean LIFT_P | n rows | call |
|---|---|---|---|
| **frozen/spec metric** (interpolated, beyond-reach excluded) | **+0.0346** | 1 | **GO** |
| lower-bound variant (all in-band rows via `LIFT_P_lb`) | +0.0281 | 6 | PARTIAL |

The spec mandated the first and I froze it before reading, so **GO is the spec-compliant
call** — but the verdict is one accounting choice away from PARTIAL and should not be
reported as comfortable. The per-view evidence below is what actually makes it solid.

## Why 5 rows fell out — this is the real result

Canny's segment recall on lego **saturates at R = 0.3832** (f=0.50). TEED passes straight
through it:

| f | TEED segP | TEED segR | beyond Canny's reach? | LIFT_P | LIFT_P_lb |
|---|---|---|---|---|---|
| 0.15 | 0.6606 | 0.2966 | no | +0.0402 | +0.0349 |
| **0.22** | **0.6584** | **0.3541** | **no** | **+0.0346** | +0.0327 |
| 0.30 | 0.6563 | 0.4004 | **yes** | — | +0.0306 |
| 0.35 | 0.6557 | 0.4253 | **yes** | — | +0.0301 |
| 0.40 | 0.6535 | 0.4463 | **yes** | — | +0.0278 |
| 0.45 | 0.6500 | 0.4621 | **yes** | — | +0.0244 |
| 0.50 | 0.6488 | 0.4797 | **yes** | — | +0.0231 |
| 0.60 | 0.6445 | 0.5038 | yes (out of band) | — | +0.0189 |
| 0.70 | 0.6428 | 0.5225 | yes (out of band) | — | +0.0171 |

Canny frontier (f≤0.50), segments: (0.183, 0.599) (0.236, 0.610) (0.286, 0.620)
(0.311, 0.621) (0.336, 0.624) (0.360, 0.624) **(0.383, 0.626)** ← its maximum recall.

**TEED at f=0.50 reaches segR 0.4797 — 25% more recall than Canny achieves at any f — while
holding segP 0.6488 vs Canny's best-ever 0.6257.** That is frontier *extension*, not merely
elevation: it is a region of the P/R plane the Canny dial cannot enter at all. Every one of
those five rows also has a positive lower bound (+0.0231 to +0.0306), so they are above the
frontier even under the most conservative accounting.

This mirrors chair, where `RECALL_RESULTS.md` recorded 2 such beyond-reach rows for teed05.
On lego there are 5 — the effect is *stronger* here, and the frozen metric's exclusion rule
paradoxically discards the strongest evidence.

## Per-view consistency — this is what makes the call solid

Matched f = 0.40, τ = 1.5, segment precision, computed with the harness's own
`run_m1b.eval_segments(..., per_view=True)` on `out/linelets_lego_tc{canny,teed}040_test.npz`:

| view | 5 | 15 | 25 | 35 | 45 | 55 | 65 | 75 | 85 | 95 |
|---|---|---|---|---|---|---|---|---|---|---|
| dP | +0.041 | +0.041 | +0.017 | +0.044 | +0.043 | +0.019 | +0.020 | +0.052 | +0.057 | +0.030 |

- **fraction dP > 0 = 1.000 (10/10 views)** — the frozen bar is 0.80
- median dP **+0.0411**, mean **+0.0364**
- median dR **+0.1504**

TEED beats Canny at matched f on **every single held-out TEST view**, with no view even close
to zero. Unlike the single-row LIFT_P mean, this is ten independent observations all pointing
the same way, and it is the strongest part of the result.

## Context numbers requested by the spec

| | value |
|---|---|
| lego TEED best LIFT_P | **+0.0346** |
| at f | **0.22** |
| segP there | **0.6584** |
| segR there | **0.3541** |
| per-view dP median | **+0.0411** |
| per-view fraction dP > 0 | **1.000** |

Source rows: `out/m1b_lego_tc_teed_native_0.5_f*.json` and `out/m1b_lego_tc_canny_f*.json`
(segments / `AFTER   pull+prune[tuned+len]`), via `teedgen_verdict.analyse()`.

## Honest summary

The rankable-seed mechanism **does** generalize from chair to lego. On lego it shows up less
as precision-at-matched-recall (a modest +0.023…+0.040) and more as **reach**: TEED accesses a
band of recall Canny cannot reach at any f, at equal or better precision. The per-view
evidence is unanimous (10/10). The headline mean is fragile — one accounting choice moves it
from GO to PARTIAL — so the claim worth publishing is the conjunction: *a positive lift on
every held-out view, plus frontier extension beyond Canny's reachable range*, rather than the
single scalar +0.0346.

Note also what this does **not** say: lego's absolute P/R gate remains unreachable, and this
experiment does not bear on it.

## Invariants

| invariant | status |
|---|---|
| scorer + thresholds frozen before any lego number | held — `4eef815`, no `lego_gen_*` artifact existed |
| metric identical to chair XMEP primary | held — `teedgen_verdict.analyse()` imported, not copied |
| no lego-specific recall-band renormalisation | held |
| held-out TEST only, no TEST tuning | held |
| mesh eval-only | held — mesh reached only through `tune_lib.Harness` |
| protected temporal manifest | **332/332 OK**, 0 failures |

**Artifacts.** `scripts/lego_gen_verdict.py`, `out/lego_gen_verdict.json`,
`out/LEGO_GEN_RESULTS.md`, `logs/lego_gen.log`.
