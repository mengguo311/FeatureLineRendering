# GEOLINE STEP 10 — comparability transforms, measured on the deliverable metric

Executes `out/GEOLINE_STEP10_SPEC.md`, frozen before the run. Direct execution, no
multi-agent workflow.

**MESH EVAL-ONLY.** The GT mesh supplies the oracle labels and scores rendered segments at
tau = 1.5 px on held-out TEST. **Both transforms are mesh-free.** Nothing committed.

---

## VERDICT

> **Both transforms are NO-GO under the frozen rules, for opposite reasons.**
>
> **D, binomial recalibration: NO-GO on the intersection.** The five admissible intervals
> still do not overlap. The gap shrinks from **0.1021 to 0.0727**, a 29 percent reduction,
> and the AUC guard passes comfortably. A partial result, exactly as I predicted.
>
> **A, crowding de-confound: NO-GO on the AUC guard, and this one needs reading carefully.**
> Its five intervals **do intersect**, and the midpoint value 0.1929, applied identically,
> puts **all five solids over R 0.35 at P 0.70**. That is the first single constant in this
> entire campaign to clear all five. It fails only because the transformed statistic's AUC
> against the oracle labels drops by more than 0.02 on every solid.
>
> **I am reporting the NO-GO as frozen and not moving the bar.** But the guard is built on
> the gapped 1.5-to-3.0 px label boundary that this campaign has twice measured as
> non-predictive of the deliverable metric, and the deliverable metric improved on all five
> solids. Section 4 lays out that conflict without resolving it. Whether to re-register the
> guard is the user's call, not mine, and it must be decided before any re-run.

---

## 1. Per-solid results

| solid | median n_vis | median crowding | raw AUC / interval | D AUC / interval | A AUC / interval |
|---|---|---|---|---|---|
| gcube | 65 | 40 | 0.9404 [0.413, 0.551] | 0.9416 [0.330, 0.473] | 0.9086 [0.101, 0.316] |
| cadpartA | 49 | 31 | 0.9019 [0.328, 0.583] | 0.9047 [0.249, 0.498] | 0.8545 [0.125, 0.380] |
| gprism | 52 | 31 | 0.8948 [0.356, 0.525] | 0.8973 [0.272, 0.439] | 0.8667 [0.133, 0.328] |
| gicosa | 54 | 30 | 0.8219 [0.279, 0.397] | 0.8258 [0.208, 0.323] | 0.7170 [0.132, 0.253] |
| **gstep** | 54 | 38 | **0.9108** [0.499, 0.536] | 0.9120 [0.396, 0.447] | 0.8504 [0.130, 0.269] |

**The concave solid's ranking AUC is measured here for the first time: 0.9108**, second
highest of the five. It was never a discrimination problem there. Its interval is also by far
the narrowest, 0.037 wide against 0.128 to 0.255 elsewhere, which is why it binds so hard.

| transform | intersection | gap | AUC guard | verdict |
|---|---|---|---|---|
| raw (control) | [0.4993, 0.3972] | **+0.1021** | reference | NO-GO |
| **D_wilson** | [0.3961, 0.3233] | **+0.0727** | **PASS**, +0.0012 to +0.0038 | **NO-GO** |
| **A_crowd** | [0.1332, 0.2525] | **−0.1193 (overlap)** | **FAIL** | **NO-GO** |

## 2. Transform D — the binomial argument has real content, just not enough

Wilson recalibration **improves ranking on every solid**, by 0.0012 to 0.0038 of AUC. That is
small but uniformly positive, which is what a correct de-noising should look like: treating
2-of-3 and 40-of-60 as different genuinely helps. It also shrinks the comparability gap by 29
percent.

It does not close it. My pre-registered prior said exactly this, and the reason it gave was
that the visible-view count is not the driver. The data support that: median n_vis spans only
49 to 65 across the five solids, a 1.33x range, against the 2.25x spread in realized cut. The
denominator was never large enough to explain the shift.

## 3. Transform A — comparability is achievable, and it is not free

The crowding de-confound produces the intersection nothing else has. At the midpoint 0.1929,
applied identically to all five solids:

| solid | A_crowd P / R | shipped rule P / R | dP | dR |
|---|---|---|---|---|
| gcube | 0.7717 / **0.5757** | 0.7375 / 0.4046 | +0.0342 | **+0.1711** |
| cadpartA | 0.7789 / **0.5728** | 0.8139 / 0.4206 | −0.0350 | **+0.1522** |
| gprism | 0.7603 / **0.5219** | 0.8226 / 0.3663 | −0.0623 | **+0.1556** |
| gicosa | 0.7599 / **0.4334** | 0.8234 / 0.2598 | −0.0635 | **+0.1736** |
| gstep | 0.7253 / **0.4958** | 0.7007 / 0.3718 | +0.0246 | **+0.1240** |

It **dominates the shipped rule outright on the cube and the concave block**, and trades about
0.06 of precision for about 0.16 of recall on the other three. Every solid clears the bar.

**The mechanism is not an object-level offset.** Median crowding varies only from 30 to 40
across the five solids. The comparability comes from removing the **within-scene** crowding
gradient, not from subtracting a per-object constant.

**The cost is real.** Crowding is itself predictive of goodness, since candidates cluster near
creases, so removing the crowding-conditional mean removes genuine signal along with the
confound. AUC falls by 0.0281 on the prism up to **0.1049 on the icosahedron**. That is a
measured loss, not an artifact of the transform being badly implemented.

## 4. The conflict I am flagging rather than resolving

The AUC guard exists because I argued comparability must not be bought with discrimination. It
fired on all five solids, so A_crowd is NO-GO and I have not moved the bar.

But two things are simultaneously true and I will not paper over either. The guard's AUC is
computed on the label boundary that excludes the 1.5 to 3.0 px band, and this campaign has
twice measured that quantity failing to forecast deliverable performance: Step 2 banked a
verifier at 0.9294 that Step 3 showed losing to the shipped prune, and Step 5's AUC-based
threshold analysis pointed at a clause that Step 6 then showed never fires. Against that, the
deliverable metric here is measured directly and improves on all five solids at a single
global constant.

So the frozen verdict stands, and the instrument behind it has a documented record of being
wrong in this exact way. The honest options are to re-register the guard on a quantity that
has predicted the deliverable metric, or to accept the NO-GO and abandon the crowding route.
That decision belongs to the user and must be made before any re-run, not after seeing which
answer is preferred.

## 5. Stage-1 diagnostic, reported not gated

| transform | Youden thresholds across the five | range |
|---|---|---|
| raw | +0.2105, +0.2222, +0.1842, +0.1833, +0.0441 | 0.1781 |
| D_wilson | +0.1353, +0.1647, +0.1202, +0.1221, +0.0306 | 0.1341 |
| A_crowd | −0.0115, +0.0099, −0.0097, +0.0500, −0.0306 | 0.0806 |

The label-space ordering matches the deliverable ordering, A best, D middle, raw worst, so the
screen would not in fact have false-killed anything here. **The decision to remove the gate was
still correct, and for a second reason I had not anticipated**: the screen as I specified it
was a *ratio* of oracle-optimal thresholds, which is undefined for a centred transform whose
thresholds straddle zero. It could not have been applied to A_crowd at all.

## 6. Caveats

The raw control's gap reads 0.1021 here against 0.0927 in Step 8, because this run used a
different threshold grid, denser near the extremes. Both are interpolated from sampled sweep
points, so the gap is precise to roughly 0.01 and the conclusion, an empty intersection, is
unaffected.

Transform A's functional form, conditional-mean removal within ten crowding deciles, was
disclosed in the spec as a design choice rather than a derivation. Its failure on the guard is
a failure of this form, not of every possible use of crowding.

## 7. Artifacts

`out/geoline_step10.json`, `out/GEOLINE_STEP10_SPEC.md`, `scripts/geoline_step10.py`,
`logs/step10.log`. Inputs were the pooled linelet arrays already on disk for all five solids.
Nothing committed.
