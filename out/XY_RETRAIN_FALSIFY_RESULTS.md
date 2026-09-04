# RETRAIN-FALSIFY — Experiment X + Experiment Y

Pre-registered kill-test for the "redesign 3DGS training to be line-extraction-favourable"
pivot. Both decision rules were frozen in `tier1/retrain_falsify_spec.md` before any run.
Nothing below is a build; no retraining framework was written.

**COMBINED VERDICT — the retraining pivot is KILLED by the data.**
An *oracle* retrain that is handed the ground-truth creases, on the object that is retraining's
best possible home turf, buys **+0.016 F1** where **+0.15** was required, and makes temporal
popping **worse**. Both halves of the frozen rule fail. And the kill does not rest on how hard
the oracle was pushed: retraining moves the frozen extractor's *reachable* F1 ceiling — under a
perfect cull — by **+0.0001** (§Y.7).

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

### X.3 Photometric structure (threshold-free)

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

### Y.4 Temporal coherence on the 120-frame held-out orbit (60 frames scored, `src/stroke_metric.py`)

| | **P_pop** (flicker ↓) | Fréchet median ↓ | unmatched | strokes/frame |
|---|---|---|---|---|
| A vanilla — OURS | **0.2787** | 0.5381 | 0.2741 | 408 |
| **B ORACLE — OURS** | **0.3001** | 0.4725 | 0.2961 | 436 |
| B' honest — OURS | 0.2804 | 0.5182 | 0.2761 | 414 |
| per-frame Canny baseline (A) | 0.9071 | 1.6248 | 0.9064 | 392 |

**B worsens P_pop: 0.2787 → 0.3001.** The crown jewel is reproduced on this scene and B erodes
it: OURS-vs-Canny P_pop ratio **3.26× (A) → 3.02× (B)**. Fréchet residual improves slightly
under B (0.538 → 0.472), so the temporal harm is modest and partly tracks B's larger stroke
population; the F1 gate is what fails decisively.

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

### Y-DECISION against the frozen rule

- F1 gate (B − A ≥ +0.15): **FAIL** (+0.0156 raw, +0.0235 budget-matched).
- Temporal gate (B must not worsen coherence): **FAIL** (P_pop 0.2787 → 0.3001).

**→ KILL retraining permanently.** Both halves fail. Because B is a GT-supervised oracle, this
bounds every non-oracle retraining scheme from above; B' (the honest, legal version) confirms
it empirically at +0.0015 F1, i.e. a no-op.

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
- `out/xy/xy_expX_{lego,chair}*.json`, `out/xy/xy_expY.json`, `out/xy/xy_cad_cadpart.json`
