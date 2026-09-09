# GEOLINE STEP 6 — the threshold-family CEILING sweep

`scripts/geoline_step6.py`. Existing artifacts only: the f = 1.00 pooled linelets already on
disk for all four solids. No new pull, no training, no pipeline change, no rule adopted.

**MESH EVAL-ONLY.** The GT mesh is read only by `tune_lib.Harness` to score rendered
segments at tau = 1.5 px on held-out TEST, the same evaluator behind every P/R number in this
campaign, at the published raw half-length. Nothing committed.

**Reproduction check, all four exact.** The frozen rule's point reproduces Step 4 to four
decimals on every solid: cube 0.7375 / 0.4046 at n 5,610; cadpartA 0.8139 / 0.4206 at n 7,208;
prism 0.8226 / 0.3663 at n 5,760; icosahedron 0.8234 / 0.2598 at n 3,828.

---

## VERDICT

> **NECESSARY condition: PASS, but only after a rule change, not a threshold change.**
> With the shipped rule intact the icosahedron's ceiling over every ratio threshold is
> **R 0.2598**, which fails the 0.35 bar. Removing the median-residual clause lifts its
> ceiling to **R 0.4721 at P 0.7200**. The threshold family is not dead, but it is not
> revivable by re-cutting the statistic the frozen rule actually cuts on.
>
> **PRIMARY: GO, at exactly one grid point, and fragile.** A single global keep-fraction of
> **0.22**, applied to each solid's own inlier-ratio distribution with the median-residual
> clause disabled, puts all four solids over R 0.35 at P 0.70 simultaneously. It is the
> **only** value of twenty-five tested that does, and both neighbours fail.
>
> **PRIMARY with the clause active: NO-GO, and for a structural reason.** No keep-fraction
> whatsoever changes any result, because the ratio clause is inert.

## 1. The structural finding that corrects my own Step 5 write-up

In active mode, the keep-fraction sweep, the frozen tau of 0.50 and the Otsu split all return
**bit-identical** P, R and n on every solid. The ratio clause removes **zero** candidates that
`median_resid <= 1.5` has not already removed.

I reported in Step 5 that the two clauses were "near-redundant", cutting 0.877 and 0.879 of the
icosahedron pool. That was directionally right and structurally wrong. It is not symmetric
overlap. **The median-residual set strictly contains the inlier-ratio set, so
`inlier_ratio >= 0.50` never binds and the operative constant in the shipped rule is
`max_med = 1.5 px`, not 0.50.** Step 5's percentile analysis of the 0.50 cut, at the 72.6th on
the cube and the 87.7th on the icosahedron, described a clause that never fires. The finding it
supported still stands, because the two clauses track each other, but the attribution was wrong
and is corrected here.

## 2. Per-solid ceilings — the necessary condition

| solid | ACTIVE ceiling (clause on) | kf | DISABLED ceiling (clause off) | kf | clause cost in recall |
|---|---|---|---|---|---|
| gcube | 0.4046 / P 0.7375 | 1.00 | **0.5156 / P 0.7012** | 0.35 | +0.1110 |
| cadpartA | 0.4206 / P 0.8139 | 1.00 | **0.6144 / P 0.7280** | 0.35 | +0.1938 |
| gprism | 0.3663 / P 0.8226 | 1.00 | **0.5228 / P 0.7188** | 0.28 | +0.1565 |
| **gicosa** | **0.2598** / P 0.8234 | 1.00 | **0.4721 / P 0.7200** | 0.22 | **+0.2123** |

Every ACTIVE ceiling sits at kf = 1.00, which is the frozen operating point itself: with the
median-residual clause on, **no threshold on the ratio can improve any solid at all**. Every
DISABLED ceiling clears the bar, the icosahedron by the largest margin of improvement.

## 3. PRIMARY — one global constant, and how narrow the window is

Global keep-fraction 0.22, median-residual clause disabled:

| solid | P@1.5 | R@1.5 | n | its own ceiling R | **gap paid** |
|---|---|---|---|---|---|
| gcube | 0.7572 | **0.3582** | 4,631 | 0.5156 | 0.1574 |
| cadpartA | 0.8086 | 0.4261 | 7,383 | 0.6144 | 0.1883 |
| gprism | 0.7807 | 0.4113 | 6,791 | 0.5228 | 0.1115 |
| gicosa | **0.7200** | 0.4721 | 6,997 | 0.4721 | 0.0000 |

**The constant is pinned by the icosahedron and paid for by the other three.** At kf 0.22 the
icosahedron is exactly at its own ceiling, gap 0.0000, while the cube, cadpart and prism give
up 0.11 to 0.19 of recall against theirs. Mean price of insisting on one frozen constant:
**0.114 recall**.

**The window is one grid point wide and both margins are thin.** The cube clears the recall bar
by **+0.0082** and the icosahedron clears the precision bar by **+0.0200**. Immediate
neighbours each clear only three of four, and they fail on opposite ends:

| kf | gcube | cadpartA | gprism | gicosa | clears |
|---|---|---|---|---|---|
| 0.28 | 0.733 / 0.424 | 0.777 / 0.530 | 0.719 / 0.523 | **0.650** / 0.570 | 3 of 4 (icosa P) |
| 0.24 | 0.752 / 0.387 | 0.803 / 0.465 | 0.759 / 0.445 | **0.698** / 0.500 | 3 of 4 (icosa P) |
| **0.22** | 0.757 / **0.358** | 0.809 / 0.426 | 0.781 / 0.411 | **0.720** / 0.472 | **4 of 4** |
| 0.20 | 0.768 / **0.340** | 0.833 / 0.388 | 0.807 / 0.384 | 0.746 / 0.428 | 3 of 4 (cube R) |

Raise the fraction and the icosahedron's precision fails; lower it and the cube's recall fails.
The GO is real against the frozen rule and is reported as GO, but a single admissible point
with margins of 0.008 and 0.020 on a twenty-five-point grid is not a robust constant, and
nothing here says 0.22 would survive a fifth solid.

## 4. Read-offs, information only, no rule adopted

**Otsu split.** Computed per solid on its own inlier-ratio distribution: 0.3633 cube, 0.3828
cadpartA, 0.4102 prism, 0.3945 icosahedron. With the clause active it is inert, identical to
the frozen point. With the clause disabled:

| solid | Otsu tau | P@1.5 | R@1.5 | clears R 0.35 at P 0.70 |
|---|---|---|---|---|
| gcube | 0.3633 | **0.6708** | 0.5624 | **no**, precision fails |
| cadpartA | 0.3828 | 0.7411 | 0.5956 | yes |
| gprism | 0.4102 | 0.7445 | 0.4612 | yes |
| gicosa | 0.3945 | 0.7813 | 0.3568 | yes |

**Otsu fails on the cube**, the simplest solid in the set, on precision. Had we built it
instead of measuring the ceiling first, it would have failed there. That is the ceiling-first
decision earning its keep, and it is the clearest vindication in this run of choosing the cheap
falsification over the attractive rule.

**Null-calibrated bar: NOT COMPUTED.** It needs the per-view Canny distance-transform maps of
the pull field to say what inlier ratio a random position would reach at the same visibility
count. Those maps are not saved and regenerating them requires re-running the field build,
which this run explicitly excludes. Reported as not computed rather than estimated.

## 5. What this licenses and what it does not

The deliverable-metric move is real and large: dropping the median-residual clause and
thresholding the ratio lifts the icosahedron from R 0.2598 to R 0.4721 and cadpartA from
0.4206 to 0.6144, both at P above 0.70. That is the answer to the question Step 5 could not
reach, and it is a move in R at 1.5 px, not merely in retention.

But note precisely what changed. **This is a rule change, not a threshold change**: it deletes
a shipped clause. It was measured here as a ceiling, not adopted, and it has not been tested
for temporal cost, on any textured scene, or on any fifth solid. The Step 4 gate also carried a
non-regression leg against cadpartA's 0.4206 / 0.8139 that this run does not evaluate, and
precision at the global constant falls on every solid relative to the frozen rule, by 0.005 on
the icosahedron and 0.042 on cadpartA.

Two standing caveats still apply. The oracle labels behind Step 5's AUCs used a gapped 1.5-to-
3.0 px boundary, which is why this run measured the deliverable metric directly instead of
trusting them. And every number here is on clean textureless solids; nothing in this run speaks
to chair or lego.

## 6. Artifacts

`out/geoline_step6.json`, `scripts/geoline_step6.py`, `logs/step6.log`. Inputs were
`out/linelets_cadpartA_step3pool.npz` and `out/linelets_{gcube,gicosa,gprism}_step4.npz`, all
pre-existing. Nothing committed.
