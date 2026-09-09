# BUFFER-EDGE LIFT MEASUREMENT — plan (frozen before execution)

**VERDICT: NO-GO. All three pre-registered legs fail.** The null control you required is what
makes it unambiguous: on lego a RANDOM detector lifted through identical machinery matches the
best real buffer to four decimal places. **My own prior was wrong** — I predicted the union
would land near the banked DexiNed cloud on cadpart; it lands at precision 0.1625 against that
cloud's 0.7302.

## What this measures
Whether 2-D geometric-buffer edges, back-projected to 3-D and kept by multi-view agreement,
produce a candidate cloud competitive with what is already banked. **No pipeline work**: no
DT-pull, no prune, no chaining, no temporal. If the lifted cloud is not competitive here, the
combine is not worth building.

**MESH EVAL-ONLY.** The mesh supplies the GT crease points and the 3-D P/R metric. See the
threshold note below for the one place I deliberately departed from the dispatch to avoid a
mesh leak.

## Frozen buffer set, identical on every scene
`{2dgs_normal, vanilla normal_disc, depth_disc}` — one per parent family. `alpha` excluded as
pure object outline, `depth` excluded as a near-duplicate of `depth_disc`. Parameter-free
union only, no weights, no per-scene selection.

## Arms, all lifted through identical steps
1. `2dgs_normal` alone 2. `normal_disc` alone 3. `depth_disc` alone
4. **UNION** of all three 5. **UNION_no2dgs** (`normal_disc` + `depth_disc`), the
single-reconstruction result, logged because including 2dgs_normal makes this a
TWO-RECONSTRUCTION method and ficus has no 2DGS 6. **NULL**, a random detector at the same
rate, fixed seed.

## Threshold, and a deliberate departure from the dispatch
The dispatch says "FPR 10 pct rule as before". That rule calibrates the threshold on
**off-crease foreground**, which requires the mesh. In the diagnostic that was fine. Here the
threshold would set a **candidate source**, so mesh-calibrating it would be a mesh leak into
the method. I therefore calibrate at the **90th percentile over ALL foreground**, which is
mesh-free and differs negligibly because crease pixels are a small share of foreground. The
**realized FPR on off-crease foreground is reported per buffer** so the substitution is
auditable rather than hidden.

## Lift
Detected pixels are back-projected through the vanilla depth buffer. A 3-D point is kept when
at least **3 views** agree, reusing the pipeline's already-frozen `min_views = 3`: the point
must be un-occluded in that view (depth agreement within `rel_eps = 0.02`, the p1b
`surface_cull` constant) and within **1.5 px** of a detection there. Points are lifted from 20
evenly spaced TRAIN views and support-checked against all 80, which is if anything stricter.

## Metric, reused verbatim from the Phase-1b harness
`recall_3D_r` = fraction of TEST-visible GT crease samples whose nearest cloud point is within
r. `precision_3D_r` = fraction of cloud points whose nearest GT crease sample is within r.
`r = px1.5_equiv = 1.5 * z_med / f`. Reported also at 0.5% and 1.5% of the bbox diagonal.

## FROZEN GO/NO-GO (corrected gate, as converged)
- **No regression**: union recall >= best-single recall − 0.02 on **both** scenes.
- **Real gain**: union recall >= best-single recall + 0.05 on **at least one** scene.
- **Null floor**: the NULL arm must land >= 0.15 recall **below** the best single buffer on
  both scenes, else the detection scale is uninterpretable and nothing here can be read.
- **Reported, not gated**: union against the banked DexiNed triangulated cloud
  (cadpartA P 0.7302 / R 0.8431) and against Step 3's existing-pool oracle ceiling
  (R 0.7271 at P 0.7274).

## Author's prior, recorded so it can be wrong
The union lands near the DexiNed cloud on cadpart and well below it on lego, and the honest
conclusion is that geometric buffers are a redundant second route on clean solids and too weak
on textured ones.

---

# RESULTS

3-D P/R at the px1.5-equivalent radius, Phase-1b metric definition, every arm lifted through
identical steps with an identical 240,000-point budget, support >= 3 views.

## cadpartA (radius 0.00546, 31,004 GT crease samples, 30,998 TEST-visible)

| arm | kept pts | precision | recall |
|---|---|---|---|
| **2dgs_normal** | 227,261 | **0.1625** | **0.5644** |
| UNION (all three) | 193,955 | 0.0882 | 0.5363 |
| **NULL (random)** | 222,586 | **0.0331** | **0.4627** |
| normal_disc | 188,758 | 0.0223 | 0.1655 |
| UNION_no2dgs | 178,680 | 0.0144 | 0.1461 |
| depth_disc | 139,439 | 0.0048 | 0.0580 |
| *banked DexiNed cloud (context)* | *220,255* | ***0.7302*** | ***0.8431*** |
| *Step 3 pool oracle (context)* | — | *0.7274* | *0.7271* |

## lego (radius 0.00536, 971,793 GT crease samples, 886,244 TEST-visible)

| arm | kept pts | precision | recall |
|---|---|---|---|
| **NULL (random)** | 233,404 | **0.1487** | **0.1554** |
| normal_disc | 225,773 | 0.2131 | 0.1555 |
| UNION (all three) | 221,381 | 0.1461 | 0.1467 |
| UNION_no2dgs | 215,158 | 0.1553 | 0.1434 |
| 2dgs_normal | 224,008 | 0.1195 | 0.1072 |
| depth_disc | 190,192 | 0.0776 | 0.0762 |

## Verdict against the frozen gate

| leg | requirement | cadpartA | lego | |
|---|---|---|---|---|
| no regression | union >= best single − 0.02 | −0.0281 | −0.0088 | **FAIL** |
| real gain | union >= best single + 0.05 somewhere | −0.0281 | −0.0088 | **FAIL** |
| null floor | null >= 0.15 below best single | 0.1017 | **0.0001** | **FAIL** |

**NO-GO on all three.**

## 1. The null control is the finding

**On lego a random detector reaches recall 0.1554 against the best real buffer's 0.1555.** Its
precision, 0.1487, beats 2dgs_normal's 0.1195. By my own pre-registration this means the lego
scale is uninterpretable: there is no buffer signal there to combine.

On cadpartA the null reaches 0.4627 recall against the best buffer's 0.5644, so **82 percent of
the best arm's recall is reproducible by random points at the same rate**. The one thing that
survives is precision: 2dgs_normal at 0.1625 against the null's 0.0331 is a real 4.9x
advantage. Recall at a fixed radius with a quarter-million scattered points is simply a weak
discriminator, and the gate was written on recall.

This is exactly the hole I disclosed and you closed. Without the null arm, cadpart's 0.5644
would have looked like a result.

## 2. What the previous step measured, and what it missed

The buffer-edge step measured only "does this buffer fire near the pixels we miss", and 2DGS
normal scored 0.9870 there. **It never measured what fraction of the buffer's firings are near
a crease.** At 10 percent FPR over foreground, most detections are off-crease, which is why the
lifted precision is 0.1625 and not something like 0.9. The bars I set in that step were
therefore one-sided, and this step is where that shows.

## 3. Against the incumbents, the branch is not close

The banked DexiNed triangulated cloud dominates the best buffer arm on **both** axes on
cadpartA: 4.5x the precision, 1.5x the recall, at a comparable point count. Step 3's
existing-pool oracle also dominates it. **My prior was wrong**: I expected the union near the
DexiNed cloud on cadpart, and it is nowhere near.

## 4. The two-reconstruction question, answered

`UNION_no2dgs` collapses cadpartA from recall 0.5363 to **0.1461**, below even the null. On
lego it changes nothing, 0.1434 against 0.1467. So the 2DGS reconstruction is not optional on
clean solids and contributes nothing on textured ones, confirming the scope limitation from
Step 2. A single-vanilla-reconstruction version of this branch has no result at all.

## 5. Why the union never helps

Union recall is at or below the best single buffer on both scenes. With a fixed candidate
budget the union spends part of it on weaker buffers, so a broader detection set converts into
a *diluted* cloud rather than a richer one. The measured Jaccards said the buffers find
different pixels, and that remains true, but the parts only one buffer finds are the parts with
the lowest precision.

## 6. A discarded first pass, disclosed

The first run capped every arm at 60,000 points. That gave the union the same budget as a
single buffer and mechanically forced it at or below the best single, destroying the union's
only mechanism. Its numbers are kept at `out/bufedge_lift_capped60k.json` and are **not** the
result. The reported run uses 240,000 points per arm, comparable to the banked DexiNed cloud's
220,255, so the comparison against that cloud is budget-fair. The verdict is the same either
way, but the first pass could not have supported it honestly.

## 7. One deliberate departure from the dispatch, restated

The FPR-10% rule as written calibrates on off-crease foreground, which needs the mesh. Because
this arm produces a candidate source rather than a diagnostic, I calibrated mesh-free at the
90th percentile over all foreground. Realized off-crease FPR per buffer is stored in
`out/bufedge_lift.json` under `realized_offcrease_FPR` so the substitution is auditable.

## 8. Artifacts

`out/bufedge_lift.json`, `out/bufedge_lift_capped60k.json` (discarded first pass),
`scripts/bufedge_lift.py`, `logs/bufedge_lift.log`. Nothing committed.

## 9. Re-run drift, disclosed

The lift was re-run once with the clouds persisted so the visualization draws exactly the
points these numbers describe. Identical seed and constants, but recall moved by up to about
0.011 (cadpartA best single 0.5644 -> 0.5652, NULL 0.4627 -> 0.4528; lego best single
0.1555 -> 0.1560, NULL 0.1554 -> 0.1548). The cause is 3DGS rasteriser non-determinism from
atomic accumulation order, already documented in Step 6 at the 2e-4 level and amplified here
because a percentile threshold turns small response changes into different detected pixels.

**No leg of the verdict changes**: no-regression still fails on both scenes, real-gain still
fails, and the null floor still fails (0.1124 and 0.0012 against a 0.15 bar). The panels and
the standalone arm images are titled from the re-run's `bufedge_lift.json`, so picture and
number always agree.

## 10. Visualization

`out/featviz/bufedge_lift_{cadpartA,lego}_panel.png` and
`out/featviz/liftarm_<scene>_<arm>.png`. Rendered by `scripts/bufedge_lift_viz.py`, one fixed
held-out TEST view per scene, faint red GT crease underneath (EVAL-ONLY), no metric computed
in that script.

The pictures make the table legible at a glance. Measured ink coverage on cadpartA: the banked
DexiNed reference draws **0.0193** of the frame, a thin clean line structure, while every
buffer arm sits at 0.089 to 0.113 and the NULL arm at 0.115 — dense fog, visually almost
indistinguishable from random. lego has no banked p1b cloud, so its reference tile is a stated
skip rather than a blank.
