# GEOLINE STEP 8 — LOCK 1 absolute-threshold read-off, and a concave fifth solid

Executes `out/GEOLINE_STEP8_SPEC.md`. Direct run, no multi-agent workflow.

**MESH EVAL-ONLY.** The GT mesh is read for the crease labels behind `run_m1b.eval_segments`
and for the builder self-checks. No mesh quantity enters any method-path signal. Nothing
committed.

---

## VERDICT

> **PRIMARY: FAIL.** The concave fifth solid reaches **P 0.8364 / R 0.2254** at the unchanged
> keep-fraction 0.22 with the median-residual clause off, against a bar of R ≥ 0.35 at
> P ≥ 0.70. It misses on **recall by 0.1246**.
>
> **LOCK 2 pivot, as frozen:** the four-solid GO was a coincidence. The inlier-ratio
> threshold family does not transport to concave geometry. Percentile-thresholding the ratio
> is abandoned for solids and the next work pivots to a different candidate seed statistic.
>
> **LOCK 1: Candidate B was already dead before the solid was built**, and the fifth solid
> buries it further.
>
> My Step-7 prior was stated as falsifiable and turned out correct in both parts: I predicted
> the fifth solid would fail, and that it would fail on recall rather than precision.

---

## 1. LOCK 1 — absolute-threshold read-off, zero GPU, reported first

Admissible absolute inlier-ratio interval per solid, meaning every threshold value at which
that solid alone reaches R ≥ 0.35 at P ≥ 0.70, interpolated from the Step 6 sweep's recorded
thresholds:

| solid | admissible absolute threshold | width |
|---|---|---|
| gcube | [0.4131, 0.5506] | 0.1375 |
| cadpartA | [0.3279, 0.5824] | 0.2545 |
| gprism | [0.3563, 0.5253] | 0.1690 |
| gicosa | [0.2785, 0.4066] | 0.1281 |
| **intersection** | **[0.4131, 0.4066]** | **EMPTY** |

**No single absolute value clears all four.** The cube's floor of 0.4131 exceeds the
icosahedron's ceiling of 0.4066, so the interval is empty, though only by **0.0065**. That
near-miss is disclosed: the absolute rule is not viable, but it is not absurd either.

Confirmed against exactly evaluated, non-interpolated points: at a threshold of 0.50 the
icosahedron returns R 0.2671, well under the bar.

**With the fifth solid added, the failure widens.** gstep's admissible interval is
**[0.4993, 0.5361]**, pushing the intersection to [0.4993, 0.4066], now empty by **0.0927**,
a fourteen-fold larger miss. **Candidate B, a physically meaningful absolute threshold, is
dead**, and would have been dead on the existing four alone.

## 2. The fifth solid, and its self-checks

`gstep`, a three-tier axis-aligned stepped block. It is the first non-convex solid in the set:
each ledge meets the tier above it at a reflex edge.

| check | result |
|---|---|
| max face non-planarity | 2.91e-18 |
| GT crease edges at 30 deg | 36 of 66 adjacencies, all at 90 deg |
| **concave crease edges** | **8 of 36** |
| min crease luma step | 0.1894, against a > 0.02 premise |
| camera round-trip silhouette IoU | 1.00000 over 4 views |
| max depth difference | 3.58e-06 |
| 3DGS, identical recipe | 66,325 gaussians, test PSNR 39.438 dB |

PSNR sits inside the range of the other four, 39.38 to 40.01 dB.

**One construction fix, disclosed.** The first build split each ledge annulus as a picture
frame, whose inner edges are strict supersets of the sides of the tier above. That leaves
T-junctions, and trimesh registered only **4 of the 8** reflex edges as face adjacencies. It
was rebuilt with a trapezoid split so each inner edge is exactly one side of the inner
rectangle. Rendering was unaffected either way, since silhouette IoU was already 1.00000, so
this is a topology fix rather than a tuning decision, and it was made before any P/R existed
for this solid.

## 3. PRIMARY — the frozen candidate, out of sample

| solid | P@1.5 | R@1.5 | n | bar |
|---|---|---|---|---|
| gcube | 0.7572 | 0.3582 | 4,631 | PASS |
| cadpartA | 0.8086 | 0.4261 | 7,383 | PASS |
| gprism | 0.7807 | 0.4113 | 6,791 | PASS |
| gicosa | 0.7200 | 0.4721 | 6,997 | PASS |
| **gstep** | **0.8364** | **0.2254** | **6,365** | **FAIL** |

Precision is the highest of any solid and recall is the lowest. The rule is cutting far too
hard on this object, not failing to discriminate.

## 4. Robustness and non-regression

**No keep-fraction clears all five.** Scanning the full grid, 0.22 remains the best at four of
five, and nothing reaches five. The admissible window is now empty.

**Non-regression against each solid's own shipped-rule point:**

| solid | shipped R | kf 0.22 R | dR | shipped P | kf 0.22 P | dP |
|---|---|---|---|---|---|---|
| gcube | 0.4046 | 0.3582 | **−0.0464** | 0.7375 | 0.7572 | +0.0197 |
| cadpartA | 0.4206 | 0.4261 | +0.0055 | 0.8139 | 0.8086 | −0.0053 |
| gprism | 0.3663 | 0.4113 | +0.0450 | 0.8226 | 0.7807 | −0.0419 |
| gicosa | 0.2598 | 0.4721 | +0.2123 | 0.8234 | 0.7200 | −0.1034 |
| **gstep** | **0.3718** | **0.2254** | **−0.1464** | 0.7007 | 0.8364 | +0.1357 |

**Two of five regress beyond the 0.02 allowance.** The standing non-regression fail is now
worse than when it was only the cube.

## 5. The mechanism: the percentile fails in BOTH directions

The absolute threshold that keep-fraction 0.22 actually applies, per solid:

| solid | realized threshold at kf 0.22 |
|---|---|
| gicosa | **0.3000** |
| gprism | 0.4545 |
| cadpartA | 0.5000 |
| gcube | 0.5439 |
| **gstep** | **0.6765** |

**A 2.25x spread.** The icosahedron's ratio distribution is shifted down, so a fixed
percentile cuts leniently there; the concave solid's is shifted up, so the same percentile
cuts brutally. That is why neither family survives: an absolute constant cannot span 0.30 to
0.68, and a percentile constant cannot span the distributions that produce them.

**On the concave solid, deleting the clause does not help at all.** gstep's clause-off ceiling
is R 0.3668 at P 0.7083, which is *worse* than its shipped-rule point of R 0.3718 at P 0.7007.
Its clause-on ceiling **is** the shipped rule. The Step 6 finding that clause deletion unlocks
recall was itself a property of the four solids it was measured on.

## 6. Temporal, ungated, trip-wire 3x

| gstep operating point | strokes | OURS P_pop | BASE P_pop | ratio | Frechet ratio | cut |
|---|---|---|---|---|---|---|
| kf 0.22, clause off | 38 | 0.0708 | 0.7598 | **10.74x** | 45.21 | 0.0057 |
| shipped rule | 57 | 0.0676 | 0.7601 | **11.24x** | 33.07 | 0.0011 |

Both far above the trip-wire. **Temporal is not what kills this**, and the concave solid holds
the object-space advantage as well as the convex ones did.

## 7. A file-handling disclosure

Running the sweep with `--solids gstep` **overwrote `out/geoline_step6.json`** with
gstep-only content. No measurement was lost: the four-solid frontiers were recovered verbatim
from `logs/step6.log`, 25 points each, matching the original counts exactly, and every Step 6
number quoted here reproduces. The gstep content was preserved to
`out/geoline_step8_gstep.json`. But `geoline_step6.json` no longer holds the four-solid sweep,
and that is stated rather than quietly repaired.

## 8. What survives

The shipped rule still clears the bar on four of five solids: cadpartA 0.4206, gcube 0.4046,
gprism 0.3663, gstep 0.3718, and fails only on the icosahedron at 0.2598. The proposed
replacement clears four of five too, but a *different* four, and regresses two of them. **After
five solids there is no rule in this family, frozen or adaptive, absolute or percentile, that
clears all five.**

The open question is unchanged from Step 5 and is now sharper: the consensus statistic ranks
well everywhere, at AUC 0.82 to 0.94, but its distribution is not comparable across objects.
Any fix must make the statistic itself comparable rather than search for a cut on it.

## 9. Artifacts

`out/geoline_step8_gstep.json`, `out/xy/geoline_solid_gstep.json`,
`out/m1b_gstep_step4.json`, `out/linelets_gstep_step4.npz`,
`out/linelets_gstep_{step8kf22,ship}_test.npz`,
`out/m1b_stroke_temporal_table_s8{step8kf22,ship}.{json,md}`,
`~/cglib/data/full/gstep/`, `~/cglib/outputs/gstep_static/`,
`~/3dgs_line/bcr/meshes/NeRF_Mesh/gstep_new.obj`, `logs/step8_*.log`.
`scripts/geoline_solids_make.py` gained the `gstep` builder; `scripts/xy_cad_make.py` remains
unmodified. Nothing committed.
