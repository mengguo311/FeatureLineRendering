# GEOLINE STEP 10 — SPEC (frozen before execution)

Comparability test: can a **zero-per-scene-parameter transform** of the multi-view consensus
statistic make its threshold comparable across five clean solids, where no absolute constant
and no percentile constant can?

Direct run, no multi-agent workflow. **MESH EVAL-ONLY**: the GT mesh supplies the oracle
labels and scores rendered segments. Both transforms are **mesh-free**. Nothing committed.

## Standing facts this is built on

Steps 5, 6 and 8, five solids. The statistic ranks good above bad within every solid
(AUC 0.82 to 0.94 on the four measured; the concave solid has never been measured and is
computed here). Its magnitude is not comparable across objects: the realized absolute cut at
each object's own optimum spans **0.30 to 0.68**, a 2.25x spread. The five admissible absolute
intervals are

| solid | admissible absolute interval (raw statistic) |
|---|---|
| gcube | [0.4131, 0.5506] |
| cadpartA | [0.3279, 0.5824] |
| gprism | [0.3563, 0.5253] |
| gicosa | [0.2785, 0.4066] |
| gstep | [0.4993, 0.5361] |
| **intersection** | **EMPTY, gap 0.0927** |

## Amendment accepted before execution

The Stage-1 label-space screen is **NOT a gate**. My own Step-2-to-Step-3 precedent says
label-space agreement does not imply deliverable-metric agreement, so a spread screen could
false-kill a transform whose deliverable intervals do intersect. Stage 1 is reported as a
diagnostic only, and **both transforms go to Stage 2 unconditionally**.

## Transform D — binomial recalibration (PRIMARY hypothesis)

The statistic is a fraction over visible views, `inlier_ratio = k / n` with `n = n_vis`, so its
granularity and variance are set by n. Two candidates at 2 of 3 and 40 of 60 are called
identical by the raw ratio. D replaces the point estimate with a **fixed-confidence lower
bound on the underlying rate**:

    k_i  = round(inlier_ratio_i * n_vis_i)          # exactly recoverable from banked arrays
    n_i  = n_vis_i
    p    = k_i / n_i
    z    = 1.2816                                   # ONE frozen constant, 90% one-sided
    den  = 1 + z^2/n
    ctr  = (p + z^2/(2n)) / den
    hw   = (z/den) * sqrt( p(1-p)/n + z^2/(4 n^2) )
    D_i  = max(0, ctr - hw)                         # Wilson score lower bound

Zero per-scene parameters. One frozen confidence level applied identically to every solid. D
changes the **ordering**, not only the cut, so it can raise discrimination as well as
comparability, and it is the reason the AUC guard below exists.

## Transform A — local-crowding de-confound (PRE-REGISTERED covariate)

Covariate, **mesh-free and pixel-anchored**, no world-scale constant:

    z_i  = median over TRAIN cameras of the candidate's camera-space depth (pure projection)
    r_i  = 5.0 * z_i / f                            # the pull's 5 px capture radius in world
    c_i  = number of OTHER candidates within r_i of candidate i in 3D

De-confound, ten frozen deciles, no hand-set magnitude:

    A_i  = inlier_ratio_i  -  mean{ inlier_ratio_j : j in the same crowding decile as i }

**Disclosed design choice:** the functional form is a choice, not a derivation. Conditional-mean
removal was picked because it divides out the covariate while preserving within-stratum
magnitude, whereas a rank or percentile adjustment would collapse back into the family Step 8
already refuted. It is tested exactly as pre-registered, and a failure is a failure of this
form, not of every possible use of crowding.

## Control

Raw statistic, whose admissible intervals are quoted above and are recomputed inside this run
so the control and the transforms pass through identical code.

## Protocol

Median-residual clause **DISABLED** and `n_vis >= 3` retained, matching the mode in which the
Step 6 and Step 8 intervals were measured. Twenty-five quantile-spaced thresholds per transform
per solid, each scored with `run_m1b.eval_segments` at tau = 1.5 px on held-out TEST at the
published raw half-length. Admissible intervals are then interpolated in the transform's own
absolute space, exactly as the Step 8 LOCK-1 read-off did.

## FROZEN GO/NO-GO

- **GO** for a transform iff the five per-solid admissible intervals, where admissible means
  **R@1.5 >= 0.35 AND P@1.5 >= 0.70**, have a **non-empty intersection**, AND the single value
  at that intersection's **midpoint**, applied identically to all five solids, puts every solid
  at R@1.5 >= 0.35 and P@1.5 >= 0.70.
- **NO-GO** otherwise, reported straight, per transform.
- **AUC GUARD, gated.** Comparability must not be bought with discrimination. The transformed
  statistic's AUC against the oracle labels may not fall more than **0.02** below the raw
  statistic's on any solid. Raw baselines: gcube 0.9404, cadpartA 0.9019, gprism 0.8948,
  gicosa 0.8219, gstep computed here for the first time.
- **REPORTED, NOT GATED.** The intersection gap per transform, against the raw control's
  **0.0927**. A transform that shrinks the gap without closing it is a partial result and is
  reported as one.
- **REPORTED, NOT GATED.** Stage-1 diagnostic: the across-solid spread of each transform's
  oracle-optimal threshold, Youden's J in label space, against the raw statistic's 2.25x.

## Author's prior, recorded so it can be wrong

I expect D to shrink the gap but not close it. The concave solid's ratios are systematically
higher, which is what large flat faces and long isolated 90-degree edges produce, and the
icosahedron's are lower, which is what many oblique crowded edges produce. That points at
per-view edge-evidence quality rather than at view count. If D fails that way, the diagnosis
lands on the pull field's distance-transform maps, which are not saved, so the next step would
be a small field rebuild rather than another object.
