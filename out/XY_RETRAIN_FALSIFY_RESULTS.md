# RETRAIN-FALSIFY — Experiment X + Experiment Y

Pre-registered kill-test for the "redesign 3DGS training to be line-extraction-favourable"
pivot. Both decision rules were frozen in `tier1/retrain_falsify_spec.md` before any run.
Nothing below is a build; no retraining framework was written.

**COMBINED VERDICT — the retraining pivot is KILLED by the data.**
An *oracle* retrain that is handed the ground-truth creases, on the object that is retraining's
best possible home turf, buys **+0.016 F1** where **+0.15** was required. The kill does not rest
on how hard the oracle was pushed: retraining moves the frozen extractor's *reachable* F1
ceiling — under a perfect cull — by **+0.0001** (§Y.7), and leaves the candidate-to-surface
accuracy the extractor consumes unchanged to six decimal places (§Y.8). The temporal gate is
also triggered (P_pop +0.0185 at matched stroke count) but is mixed in direction and is not what
the verdict rests on (§Y.4).

Every claim below was adversarially red-teamed before being reported; two stated results were
corrected as a result (the temporal reading in §Y.4, and lego's threshold sensitivity in §X.3).

Artefacts: `out/xy/` (json + npz + png), scripts `tier1/scripts/xy_*.py`.
Mesh is EVAL-ONLY throughout. **Condition B was trained on GT-mesh creases: it is a SIMULATED
IDEAL UPPER BOUND, not a proposed method, and must never be reported as one.**

---

## EXPERIMENT X — prize-pool sizing (no GPU)

### X.1 The spec-literal split is a TAUTOLOGY, and that is the finding

`src/mesh_oracle.py` **defines** the GT crease set as
`sel = m.face_adjacency_edges[m.face_adjacency_angles >= deg2rad(30)]`.
The miss-set is a subset of the GT crease set. So the literal test "geometric (dihedral above
threshold) vs decal (dihedral ~0 on a flat region)" returns GEOMETRIC for **100%** of the
miss-set on every scene, with no measurement performed.

| scene | GT crease pts visible in ≥1 TEST view | frozen-pipeline 3D recall @1.5px-equiv | miss-set | **g_literal** | n_decal in miss-set |
|---|---|---|---|---|---|
| lego  | 554,207 | 0.2112 | 437,138 (78.88%) | **1.000** | **0** |
| chair | 225,977 | 0.6753 | 73,371 (32.47%)  | **1.000** | **0** |

Harness validation: the chair number reproduces the banked
`dexprimary_p1b_chair_ref40.json → tri_sup2.recall_3D_px1.5_equiv = 0.6753165145125389` exactly.
lego has no banked p1b cloud; `out/dexprimary_p1c_cloud_lego.npz` (same ref40 config) was used.

**Why it is a category error, not a fixable definition.** "Decal" was never defined on the
miss-set in this project. It was defined on the *precision* side. `scripts/diag2dgs.py:409-411`:
```python
crease = seen & (dmed <= 1.5)                # a linelet that lands ON a GT crease
decal  = seen & (dmed > 3.0) & teed_hi       # a strong image edge FAR from any GT crease
```
A decal is a **detector false positive**. It cannot appear in a set that contains only GT
creases. (This also corrects the spec's provenance: the "GT-mesh dihedral 0.396" figure is
`out/DIAG2DGS_RESULTS.md` arm `mesh3d`, AUC **0.3964**, n_crease 28,826 vs n_decal 3,814 — it is
not in `DEXPRIMARY_P1D_RESULTS.md`.)

**X-DECISION against the frozen rule:** g = 1.000 > 0.40 → **PROCEED TO EXPERIMENT Y.**
The rule fires, but vacuously. Y is the test that carries the decision.

### X.2 What the miss-set is actually made of

3D recall per dihedral band, and each band's share of the miss-set. `photo` = median Sobel
|grad| of the GT render at the crease pixel (undilated, max over TEST views).

**lego** (miss-set 437,138)

| dihedral band | n visible | recall | n missed | % of miss-set | photo p50 |
|---|---|---|---|---|---|
| **EXACTLY 30.0°** | 238,708 (43.1%) | **0.1035** | 214,007 | **48.96%** | **28.3** |
| 30–44° | 33,347 | 0.2648 | 24,517 | 5.61% | 41.8 |
| 44–60° | 56,806 | 0.3418 | 37,387 | 8.55% | 48.2 |
| 60–90° | 59,389 | 0.3896 | 36,253 | 8.29% | 40.5 |
| **EXACTLY 90.0°** (box corners) | 140,965 (25.4%) | 0.2294 | 108,621 | 24.85% | 39.1 |
| >90° | 24,992 | 0.3457 | 16,353 | 3.74% | 44.0 |

**chair** (miss-set 73,371) has no 30° spike at all (238 edges, 0.1% of the crease set); its
mass sits in a broad 30–90° band with recall 0.49–0.72.

**The 30.0° spike.** 104,254 of lego's 186,238 crease edges (55.98%) sit in the single one-degree bin
`[30,31)`, and 103,070 sit in `[29.9,30.1)` — a spike at *exactly* 30.000°, which is where 12-fold
rotational tessellation lands (360/12 = 30) and exactly where the oracle's threshold sits.
lego is built from cylinders (every stud, pin and axle barrel). This band is simultaneously
(i) the largest single block of the crease set, (ii) the worst-recovered by a factor of ~2.2
against the 90° box corners, (iii) the lowest photometric contrast of any band, and (iv) —
see `out/xy/xy_X_stud_zoom.png` — located on studs that the GT renders show as **smooth round
cylinders with no facet lines at all**.

**Honesty on this point.** Two independent attempts to *prove* the tessellation reading were
built and both were rejected by their own controls, so it is reported as a strongly-supported
reading, not a proven statistic:
- reading Blender's smoothing groups / split vertex normals out of `lego_new.obj` — **invalid**:
  the file was re-exported with fully averaged vertex normals and reports even 90° box corners
  as "smooth" (`SMOOTH_frac = 1.0` in every band).
- a rotational-"fan" test on locally-planar patches (`scripts/xy_fan.py`) — **falsified by its
  own control**: the Experiment-Y CAD part, which has zero tessellated curvature by
  construction, also scores 80% "fan", because a hexagonal prism *is* a rotational fan. The
  test cannot separate "6-gon prism (real creases)" from "12-gon cylinder (tessellated curve)";
  only the step size differs, and that is artist intent, not geometry.

### X.3 A first-order caveat on lego: the oracle threshold sits INSIDE the 30° family

The 30.000° edges are not merely *near* the oracle's 30° threshold — they straddle it, and the
threshold cuts the family roughly in half:

| bin | lego edges |
|---|---|
| `[29.95, 30.00)` — **excluded** from the GT crease set | **110,655** |
| `[30.00, 30.05)` — **included** | **103,056** |
| whole `[29.5, 30.5)` band | 216,002, median &#124;θ−30&#124; = **3.19e-3°** |

A median deviation of 0.003° is not a real spread of angles; it is the OBJ's 6-decimal vertex
quantisation. So **which half of one identical 213,711-edge family counts as a "GT crease" is
decided by coordinate rounding in the asset file.** Nudging the threshold by 0.05° — enough to
drop the whole family rather than half of it — moves the frozen pipeline's lego score without
touching the method at all (recomputed from the saved per-point `theta0_pt`):

| oracle threshold | lego n_seen | 3D recall | miss-set |
|---|---|---|---|
| **30.00° (frozen)** | 554,207 | **0.2112** | 437,138 |
| 30.05° | 315,503 | **0.2928** | 223,135 |
| 31.0° | 311,381 | 0.2942 | 219,777 |
| 45.0° | 281,970 | 0.2962 | 198,460 |
| *chair* 30.0° → 31.0° | 225,977 → 223,534 | 0.6753 → **0.6769** | stable |

**+0.05° changes lego recall by +39% relative and halves the miss-set.** lego's Experiment-X
headline numbers are therefore properties of a knife-edge threshold, not of the pipeline.
chair is unaffected and its numbers stand as reported.

This also settles the tessellation reading as far as it can honestly be settled: a *single
coherent family of 213,711 edges at exactly 30.000000°* is the signature of 12-fold rotational
tessellation (360/12), not a coincidence of an organic mesh. It remains an interpretation of
where those edges come from; the arbitrariness of the threshold is a measured fact.

### X.4 Photometric structure (threshold-free)

Rank AUC, >0.5 = first group has higher image gradient. Undilated, on the GT training renders.

| | lego | chair |
|---|---|---|
| hit-set vs miss-set | **0.6907** | 0.6514 |
| hit-set vs random foreground | 0.8461 | 0.8428 |
| miss-set vs random foreground | 0.7153 | 0.7321 |

Missed creases carry measurably weaker photometric contrast than recovered ones, but the split
is not binary: a hard "photometrically invisible" class does not exist on lego, because lego is
texture-saturated (69% of random foreground pixels clear a gradient of 25 within 1.5px).

**Viz:** `out/xy/xy_X_missmap_lego_v{5,25}.png`, `out/xy/xy_X_stud_zoom.png`.
The colouring the spec asked for (geometric vs decal) cannot be drawn — 100% vs 0%; the maps
colour recovered / missed-at-exactly-30° / missed-other instead.

---

## EXPERIMENT Y — retrain ideal-ceiling falsification (small GPU)

### Y.0 The scene, and its self-checks

`scripts/xy_cad_make.py` builds a **chamfered hex nut**: 36 exactly-planar faces (max
non-planarity 2.2e-16), one uniform albedo, flat shading, hexagonal through-hole, 45° chamfers
of different size top and bottom. 60 GT crease edges at dihedral {40.89, 44.42, 49.11, 60, 90}°,
31,004 crease sample points, bbox diag 3.163. Zero decals and zero tessellated curvature by
construction. 100 train / 20 test / **120-frame held-out orbit** views at 800×800.

Three self-checks, all passed and all reported (`out/xy/xy_cad_cadpart.json`):
1. planarity < 1e-9 ✔
2. **every GT crease is a real photometric step**: min |ΔI| across creases = **0.046** luma
   (p05 0.054, median 0.121) — the "home turf" premise is measured, not assumed. Two shading
   models were tried and *rejected* first because they left creases invisible (clamped Lambert
   with 3 lights → min |ΔI| = 0.0000; wrap lighting → 0.0074, and wrap is linear in the normal
   so any number of lights collapses to one).
3. **camera convention round-trip**: silhouette IoU vs `mesh_oracle.render_depth` = **1.00000**
   on 4 views, max |depth diff| 1.3e-5.

### Y.1 Conditions (identical seed, iters, lr, SH and densify schedule; only the intervention differs)

| | gaussians | test PSNR | intervention |
|---|---|---|---|
| **A** vanilla | 75,539 | 39.38 dB | none — the frozen baseline |
| **B** ORACLE | 192,068 | 39.59 dB | **GT-mesh creases used as supervision**: 3×20,000 tangent-aligned anisotropic carriers injected on the GT crease curves at iters 500/2000/3500, plus 4× lower densification threshold within 2px of a GT crease |
| **B'** honest | 93,083 | 39.44 dB | legal, mesh-free: edge-weighted photometric loss + edge-boosted densification from Sobel edges of the training images only |

B was given 2.5× A's capacity and reached slightly *better* PSNR — a generous upper bound.

### Y.2 The oracle intervention DID take effect (positive control)

Measured on the raw gaussian carriers, i.e. exactly what retraining changes:

| arm | A vanilla | **B ORACLE** | B' honest |
|---|---|---|---|
| `gauss_pool` recall | 0.2021 | **0.3419** (+69% rel.) | 0.2090 |
| `gauss_pool` F1 | 0.1060 | **0.1468** | 0.1022 |
| gaussians within 3px of a GT crease | 30,527 | **97,807** (3.2×) | 41,004 |

So B is not a failed intervention. It really did pile carriers onto the creases.

### Y.3 A vs B vs B' — the headline table (held-out TEST views, 3D @1.5px-equiv, radius 0.004860)

| | recall | precision | **F1** | Chamfer GT→pred | Chamfer pred→GT |
|---|---|---|---|---|---|
| **A** vanilla | 0.8431 | 0.7315 | **0.7833** | 0.001071 | 0.002777 |
| **B** ORACLE | 0.8793 | 0.7319 | **0.7989** | 0.001063 | 0.002777 |
| **B'** honest | 0.8463 | 0.7317 | **0.7848** | 0.001071 | 0.002775 |

**ΔF1(B − A) = +0.0156.** Budget-matched (every cloud voxel-deduped to ~19.8k points, the
`dexprimary_p0.voxel_budget` protocol, so the comparison is about the cloud and not about how
many points it has): A 0.4691, B 0.4926, B' 0.4701 → **ΔF1 = +0.0235**.

Required by the frozen rule: **+0.15**. Delivered: **+0.016 (raw) / +0.024 (budget-matched)** —
short by a factor of **6–10×**.

### Y.4 Temporal coherence on the held-out orbit (`src/stroke_metric.py`, 60 frames scored)

**As first run — and why that reading was not trustworthy.** Each condition's chains were
projected through *its own* gaussian z-buffer. `ours_strokes` splits a chain at every occlusion
break, so B's denser reconstruction (192,068 gaussians; 60,773 after de-floatering, vs A's
75,539 / 32,476) fragments the same curves into more strokes: 436 vs 408 per frame. `P_pop`
counts unmatched strokes and `match_strokes` only retrieves the top-6 candidate centroids
within 40 px, so a denser stroke population is charged more popping for the same motion. The
raw gap could therefore have been measuring z-buffer density rather than line stability.

**Controlled re-run** (`scripts/xy_temporal_ctrl.py`): one **shared reference z-buffer**
(Condition A's gaussians) for the occlusion split and the warp, **and** each condition's chain
set randomly subsampled to equalise strokes/frame, 3 seeds:

| (shared z-buffer, stroke-count matched) | strokes/frame | **P_pop** ↓ | Fréchet median ↓ | Fréchet p90 ↓ | unmatched | warp-dropped |
|---|---|---|---|---|---|---|
| A vanilla | 407.9 | **0.27873** | 0.53811 | 1.2806 | 0.2742 | 0.0045 |
| **B ORACLE** | 408.4 | **0.29719 ± 0.00164** | 0.52296 | 1.1743 | 0.2929 | 0.0088 |
| B' honest | 406.9 | 0.27903 ± 0.00062 | 0.52269 | 1.2164 | 0.2740 | 0.0032 |

Stroke counts now agree to **0.45 per frame**, and **ΔP_pop(B − A) = +0.01846**, about 11× the
across-seed SD. **The effect is real, not a stroke-count artifact** — the control was run
precisely because it might have been.

But it does not point one way. B **pops more** (P_pop +6.6% relative; unmatched 0.274 → 0.293;
warp-dropped 0.0045 → 0.0088) while the strokes that *do* match are slightly **steadier**
(Fréchet median −2.8%, p90 −8.3%). P_pop is the metric the banked 7–13× headline is stated in,
so the frozen rule's temporal criterion is triggered — but this is a modest, mixed-direction
result and it is **not** what the KILL rests on. B' is a no-op (+0.0003).

The crown jewel is reproduced and preserved on this scene. Against per-frame Canny (uncontrolled
run, each condition on its own buffer): OURS P_pop 0.2787 vs Canny 0.9071 = **3.26×** (A) and
0.3001 vs 0.9060 = **3.02×** (B); Fréchet 0.538 vs 1.625 = 3.02×. Lower than the banked 7–13×
because this object is far simpler than chair/lego, but the object-space advantage holds in
every condition.

### Y.5 The floater-halo failure mode (agy's prediction) — measured

| near-crease gaussians (within 3px) | A vanilla | **B ORACLE** |
|---|---|---|
| median opacity | 0.1591 | **0.0645** (2.5× lower) |
| fraction with opacity < 0.1 | 43.1% | **56.5%** |
| median anisotropy (max/min scale) | **551.4** | **71.3** (7.7× rounder) |
| median min-axis scale | 0.013 px | 0.063 px (5× fatter) |
| **stripped by `defloat_mask`** | 43.8% | **56.9%** |
| whole model stripped by `defloat_mask` | 57.0% | **68.4%** |

The oracle's 60,000 injected sharp, tangent-aligned carriers **did not survive as sharp 1D
carriers**: they ended up fatter, rounder, more transparent, and more than half of them are
thrown away by the pipeline's own de-floaterer. Vanilla 3DGS, by contrast, already forms
razor-thin crease gaussians on its own (anisotropy 551, min-axis 0.013 px) — there was little
left to win.

**Caveat, stated plainly:** the *render-level* halo signature is NOT present. The fraction of
pixels with 0.02 < alpha < 0.35 is essentially identical (A 0.0349, B 0.0343, B' 0.0342), and
`out/xy/xy_Y_halo_v{0,30}.png` look the same across conditions. The halo shows up in the
gaussian *parameters*, not as a visible glow.

### Y.6 Why retraining cannot move this pipeline — the mechanism

The frozen extractor's candidate set comes from **DexiNed edge pixels in the 40 reference
views**, not from the gaussians. Across all three conditions the raw triangulated cloud has
**exactly 227,018 points** and identical per-view edge-pixel counts, because the images (and
therefore the edge maps) are identical. The 3DGS enters only as (a) a depth-search bracket
initialisation and (b) the free-space / occlusion cull.

Removing the cull collapses the difference entirely:

| `tri_sup2_nocull` | A 0.8076 | B 0.8078 | B' 0.8072 |
|---|---|---|---|

**ΔF1 = +0.0002 without the cull.** The whole +0.0156 that Condition B gains comes through the
occlusion cull being marginally better informed by a denser gaussian field. That is the entire
channel by which retraining can touch this method — and even an oracle saturates it at +0.016.

### Y.7 The absolute ceiling — this is the number that makes oracle strength irrelevant

The obvious objection to a KILL is "your oracle was too weak." That objection can be closed
without building a better oracle. Take each condition's **raw** triangulated pool (227,018
candidates) and apply a **perfect** cull — keep exactly the candidates that lie within the
scoring radius of a GT crease, forcing precision to 1.000. That is the best F1 the frozen
extractor could ever reach on that condition, by any selection or scoring rule whatsoever:

| | ceiling recall | ceiling precision | **ceiling F1** | candidates kept |
|---|---|---|---|---|
| A vanilla | 0.9142 | 1.0000 | **0.9552** | 163,023 |
| **B ORACLE** | 0.9144 | 1.0000 | **0.9553** | 163,123 |
| B' honest | 0.9129 | 1.0000 | **0.9545** | 163,038 |

**ΔF1_ceiling(B − A) = +0.0001.** Retraining moves the *reachable* F1 of this extractor by one
ten-thousandth. Since the 3DGS's only influence on the candidates is where the depth search
places them along their rays, this measures exactly how much better oracle-guided retraining
makes those positions: essentially nothing. No stronger oracle, longer schedule, frozen
carriers or larger capacity can beat a ceiling it does not move.

This also **defends the pre-registered rule against the charge that it was unreachable**: the
bar is A + 0.15 = **0.9333**, which sits *below* the 0.9552 ceiling. A perfect cull clears the
bar comfortably. The +0.15 gate was attainable in principle; retraining simply is not the thing
that gets you there.

### Y.7b THE CLOSING BOUND — what PERFECT geometry would buy

`scripts/xy_gtdepth_limit.py`. The 3DGS reaches this extractor as one thing: the depth buffer
consumed by `tri_edges.surface_cull` (free-space/occlusion vote, `rel_eps=0.02`,
`min_frac=0.5`). The very best any line-favourable retraining could ever do to that buffer is
make it **exact**. So substitute the ground-truth mesh depth — a 3DGS with literally perfect
geometry — keeping the frozen cull rule byte-for-byte over the same 80 TRAIN G-buffer views:

| | recall | precision | **F1** |
|---|---|---|---|
| A vanilla, frozen 3DGS cull | 0.8431 | 0.7315 | 0.7833 |
| **A vanilla + EXACT GT-MESH DEPTH** | 0.8964 | 0.7541 | **0.8191** |
| B ORACLE, frozen 3DGS cull | 0.8793 | 0.7319 | 0.7989 |
| **B ORACLE + EXACT GT-MESH DEPTH** | 0.8965 | 0.7539 | **0.8190** |

**Perfect geometry is worth +0.0358 F1. The gate demands +0.15 — it falls 4.2× short.**
With exact depth the two conditions converge to the same F1 (0.8191 vs 0.8190), which is what
should happen: once the depth is perfect, how the 3DGS was trained stops mattering entirely.

This is the bound that ends the argument. It does not depend on how hard the oracle was pushed,
on the operating point, on the budget, or on anything about Condition B's implementation. **No
3DGS — however retrained, however supervised, even one with perfect geometry — can move this
extractor by +0.15 F1, because the extractor does not consume enough of the 3DGS for that much
signal to flow through it.**

### Y.8 Did retraining improve the geometry the extractor actually consumes? No.

The 3DGS reaches the extractor as a depth prior for the per-ray depth search. So measure the
thing that prior is supposed to improve: the exact distance from every raw triangulated
candidate to the GT mesh **surface** (`out/xy/xy_depthquality.json`, 1 px = 0.003628 world).

| | median surface distance | p90 | within 1 px | within 0.5 px |
|---|---|---|---|---|
| A vanilla | **0.001823** | 0.006414 | 0.7661 | 0.4979 |
| **B ORACLE** | **0.001823** | 0.006383 | 0.7667 | 0.4980 |
| B' honest | **0.001823** | 0.006414 | 0.7662 | 0.4981 |

Identical to six decimal places. Condition B put **3.2× more gaussians within 3 px of the GT
creases** (§Y.2) and that bought the depth search **nothing**. The depth prior was already good
enough that the search converges to the same places.

### Y.9 Robustness of ΔF1, and the caveats that belong on the record

**ΔF1 is not an operating-point artifact.** Sweeping the extractor's own saved knobs
(`support` ∈ 1..6 × `resid` ≤ 0.10..1.50) and scoring each condition at *its own* optimum
(both land on `support≥4, resid≤0.30`): A **0.8332**, B **0.8485** → **ΔF1 = +0.0153**, against
+0.0156 at the frozen operating point. Retuning lifts both conditions by ~0.05 F1 and leaves
the gap between them unchanged.

**A recall-only bound.** At the observed precision (0.7315 / 0.7319 — a spread of 4e-4 across a
2.5× change in gaussian count *and* a GT-crease oracle), even **perfect recall of every
TEST-visible GT crease** gives F1 = 2P/(1+P) = **0.8452**, i.e. ΔF1 ≤ **+0.0619 < 0.15**. To
clear the gate B would need precision ≥ 0.875, and precision is where no condition moves.

**Caveats on the record:**
1. *The +0.15 gate is mis-calibrated for this substrate.* It was frozen before the CAD part
   existed, against the regime the pipeline targets — chair, where `tri_sup2` scores
   R 0.6753 / P 0.1636 / **F1 0.2634** and +0.15 is a modest slice of the headroom. Applied to a
   scene that starts at F1 0.7833, the same absolute delta demands ~70% of all remaining
   headroom. The gate is nonetheless **reachable**: the bar (0.9333) sits below the 0.9552
   perfect-cull ceiling (§Y.7). B misses it by ~10×; the mis-calibration is worth <2×.
2. *Condition B is a stronger oracle than any pre-registered control allows* — its densification
   is not gated on the crease being photometrically evaluable; it is handed every GT crease
   sample unconditionally. That makes the failure more damning, not less, but the run should be
   read as an upper bound on an upper bound.
3. *The de-floaterer filters the oracle's mass.* B's near-crease gaussians have median opacity
   0.0645 against `defloat_mask`'s `opa_min = 0.1`, so 56.9% of them are removed before the
   extractor sees them (A: 43.8%). A threshold tuned for vanilla 3DGS is not neutral between the
   conditions. In absolute terms B still delivers 2.5× more surviving near-crease carriers, so
   the positive control (§Y.2) holds.
4. *Precision is not detector-capped.* The DexiNed 2D detector scores precision 0.977 / recall
   0.971 at 1.5 px against visible GT crease projections on this scene; the ~27% of 3D
   candidates that miss are real image edges placed at the wrong depth, not spurious detections.

### Y-DECISION against the frozen rule

- **F1 gate (B − A ≥ +0.15): FAIL, decisively.** +0.0156 frozen, +0.0153 at matched optima,
  +0.0235 budget-matched — short by 6–10×. Bounded above by +0.0619 even with perfect recall,
  and by **+0.0001** on the achievable frontier (§Y.7).
- **Temporal gate (B must not worsen coherence): triggered, weakly.** P_pop +0.0185 at matched
  stroke count (real, ~11σ), but Fréchet residual improves. Mixed direction; not load-bearing.

**→ KILL retraining permanently.** The verdict rests on the F1 gate, which fails by an order of
magnitude and is robust to operating point, budget, cull tuning and oracle strength. The closing
bound (§Y.7b) makes it unconditional: even a 3DGS with **perfect geometry** reaches F1 0.8191
against a bar of 0.9333.

**Scope, stated honestly.** This kills retraining *for the frozen DexiNed-primary
triangulation*, which is the thesis method and the pipeline the spec named. A hypothetical
extractor that seeded from gaussians instead of image edges would be coupled to the 3DGS and
would respond to retraining — but that is the gaussian-seeded path the project already measured
as much weaker (`gauss_pool` F1 0.106 vs 0.783 here), and rebuilding around it would trade a
0.78-F1 method for a 0.15-F1 one to gain sensitivity to an intervention worth +0.016.

---

## Viz index
- `out/xy/xy_X_missmap_lego_v5.png`, `_v25.png` — GT creases coloured recovered / missed-at-30° / missed-other
- `out/xy/xy_X_stud_zoom.png` — smooth-rendered studs vs the dense red 30° "creases" on them
- `out/xy/xy_Y_lines_v0.png`, `_v30.png` — A vs B(ORACLE) vs B' line drawings, side by side
- `out/xy/xy_Y_halo_v0.png`, `_v30.png` + `out/xy/halo_*_render.png` — floater-halo inspection
- `out/xy/xy_expX_{lego,chair}*.json` — Experiment X, per-scene
- `out/xy/xy_expY.json` — Experiment Y, all conditions + verdict
- `out/xy/xy_ceiling.json` (§Y.7), `out/xy/xy_depthquality.json` (§Y.8),
  `out/xy/xy_temporal_ctrl.json` (§Y.4 control), `out/xy/xy_gtdepth_limit.json` (§Y.7b),
  `out/xy/xy_cad_cadpart.json` (scene self-checks)

## Scripts
`scripts/xy_expX.py` `xy_expY.py` `xy_cad_make.py` `xy_gs_train.py` `xy_ceiling.py`
`xy_depthquality.py` `xy_gtdepth_limit.py` `xy_temporal_ctrl.py` `xy_viz_X.py` `xy_viz_Y.py`
`xy_mesh_geom.py` `xy_shading.py` `xy_fan.py` (the last three are the two rejected mechanism
tests and their calibration — kept because the writeup cites why they were rejected).
