# DexiNed-primary PHASE 1b — multi-view epipolar triangulation, CHAIR
# **VERDICT: MARGINAL** — triangulation is a real localization fix, but it does not break the coverage ceiling

Spec `tier1/dexprimary_p1b_spec.md`. Held-out TEST {5,15,…,95}. URS-legal: every candidate is
triangulated from **TRAIN views only**; TEST views are scored on and never lifted from.
Mesh EVAL-ONLY — the method path is `src/tri_edges.py`, which imports only
`common`/`render`/`epipolar_consensus` (AST-verified: no mesh import anywhere reachable).
Nothing committed. Only the triangulation generator + the ceiling test were built.

New artifacts: `src/tri_edges.py` (METHOD), `scripts/dexprimary_p1b{,_viz,_paired,_spread,_table}.py`,
`scripts/dexprimary_p1b_sweep.sh`, `out/dexprimary_p1b_chair*.json`,
`out/dexprimary_p1b_cloud_chair*.npz`, `out/dexprimary_p1b_chair.png`, `logs/dexp1b_*.log`.

---

## The method

For each DexiNed edge pixel in a TRAIN reference view, sweep depth along its viewing ray.
A candidate depth traces exactly the epipolar line of that pixel in every neighbour view, so
the sweep **is** the epipolar search and no correspondence is committed to in advance:

```
cost(z) = mean_n  min( DT_n( project_n( C_r + z * dir_r(u) ) ), CAP )
```

`DT_n` = distance transform of neighbour n's NMS-thinned DexiNed edge mask; the truncation at
`CAP = 8 px` is what makes it robust — a neighbour in which the point is occluded, out of
frame, or simply undetected contributes a constant and cannot drag the arg-min. `z*` is found
coarse-to-fine in log depth (levels 65/33/33 → final resolution ~1e-4 world units, ~50× finer
than the 0.00515 scoring tolerance). SUPPORT = number of neighbours with `DT ≤ τ` at `z*`;
"2-view" = support ≥ 1, "K≥3-view bundle" = support ≥ 2. Support is cached per point so every
threshold is free.

The 3DGS median depth (`render_gbuffer(with_median_depth=True)`, Phase 0's best arm) is used
**only** as the centre of the search bracket and as the free-space/occlusion prior — never as
the final position. The bracket is ±20 %, i.e. ±0.76 world units at chair's ~3.8 depth, ~150×
the scoring tolerance. **80.7 % of points end up more than one tolerance away from their
initialisation**, so the optimum genuinely moves.

Free-space cull: in every view where the point is in front of the camera and in frame it must
either be occluded (something nearer — that view abstains) or lie on the surface
(`|z − depth_median| ≤ 0.02 z`); kept if on-surface in ≥ half the views that can see it.
Keeps 87.1 %.

**Reprojection sanity (the spec's pitfall).** Triangulated points land within 1.5 px of a
DexiNed edge in their **neighbour** views **84.9 %** of the time (median DT 0.0000). The same
seed pixels placed by single-view depth manage only **69.4 %** (median DT 1.0000). Multi-view
photometric consistency is genuinely improved — by +15.5 points.

---

## The ceiling test (chair, held-out TEST, n = 1,002,286 visible GT crease points)

Gaussian miss-set at τ=1.5: **262,416 / 1,002,286 = 0.2618**; fixed-pool 2D coverage 0.7382.
Radii: `px1.5_equiv` **0.00515** (= 1.5 px at the median crease depth), `0.5% bbox` 0.01418,
`1.5% bbox` 0.04254. Phase 0 established that only the **1.5 px-equivalent** radius
discriminates — the gaussian pool recovers 100 % of its own miss-set at 1.5 % bbox — so every
headline number below is at that radius.

| cloud (20 TRAIN refs, K=6, ρ=0.2) | n | 2D recall | lift | **3D recall** | **R_miss 3D** | **prec 3D** |
|---|---|---|---|---|---|---|
| **tri_sup2** (K≥3-view bundle) | 135,814 | 0.9212 | **1.55** | **0.5899** | **0.5857** | **0.1690** |
| tri_sup1 (2-view) | 136,439 | 0.9223 | 1.54 | 0.5900 | 0.5860 | 0.1682 |
| tri_sup3 | 132,710 | 0.9179 | 1.60 | 0.5880 | 0.5785 | 0.1723 |
| tri_sup2, no free-space cull | 154,223 | 0.9350 | 1.37 | 0.5899 | 0.5858 | 0.1488 |
| **p0_singleview** (Phase 0's best arm) | 157,709 | 0.9421 | 1.38 | 0.5361 | 0.4712 | 0.1384 |
| ctrl_randfg (chance, matched count) | 157,709 | 0.9566 | 1.14 | 0.4514 | 0.3513 | 0.0649 |
| ctrl_tri_randpix (triangulate random px) | 143,172 | 0.9664 | 1.16 | 0.3256 | 0.3079 | 0.0350 |
| **gauss_pool** (the fixed-pool ceiling) | 370,437 | 0.7382 | — | 0.2766 | 0.0029 | 0.0764 |

Budget-matched to Phase 0's 85,325-point chair cap (voxel-dedup, applied to every cloud), the
ordering is unchanged and the margin widens relative to chance:
tri **0.5318 / 0.5198 / 0.1386** vs single-view **0.4452 / 0.3872 / 0.1098** vs chance
**0.3182 / 0.2795 / 0.0574**.

**What is solidly established:**

- **Triangulation beats single-view depth on recall *and* precision, with fewer points.**
  R_miss 0.4712 → **0.5857** (+0.115, 1.24×), 3D recall 0.5361 → 0.5899, precision
  0.1384 → 0.1690 — at 136 k points versus 158 k. Raising recall *and* precision *and*
  lowering density simultaneously is not something a denser cloud can fake.
- **It beats the density-matched chance control decisively**: R_miss 1.67×, precision 2.6×.
- **The detector matters, not just the machinery.** Running the identical triangulator on
  random foreground pixels (`ctrl_tri_randpix`) gives 3D recall **0.3256** — *worse* than
  simply putting random pixels at the median depth (0.4514). Without real edges to lock onto,
  the epipolar search actively hurts.
- **The free-space cull is worth more than it looks**: it leaves recall untouched (0.5858 →
  0.5857) while lifting precision 0.1488 → 0.1690. It is repairing points triangulation threw
  off-surface.
- **2D coverage remains saturated and unusable**, exactly as in Phase 0: tri scores 0.9212 but
  chance scores 0.9566 and random-pixel triangulation 0.9664. Normalised by density (`lift`)
  tri is best at 1.55 vs 1.14/1.16 — but no GO can rest on the raw 2D number.

### Answering the spec's question: does triangulation close the 0.636 → 0.486 gap?

In this run's configuration the single-view arm gives R_miss **0.4712** and Phase 0's 2D
ceiling for chair (native, half-pixel corrected) is **0.6364**. Triangulation reaches
**0.5857**, i.e. it closes **(0.5857−0.4712)/(0.6364−0.4712) = 69 %** of the localization gap.
That is a real and substantial answer to the question this phase was set to ask.

---

## The three controls that decide it

### 1. The spread control — the gain is NOT scatter

The paired test (below) shows triangulation does not improve *per-point* accuracy, so the
aggregate gain needed explaining: a cloud scattered off the single-view depth surface covers
more of a 3D crease set at a fixed radius regardless of whether any point got better.
`CTRL_JITTER` displaces each single-view point **along its own viewing ray** by a factor drawn
from the triangulation's **own observed displacement distribution**, randomly permuted across
points — identical marginal displacement law, correspondence destroyed (the analogue of Phase
0's `ctrl_shufz`). Same 153,377 seeds throughout:

| cloud | 3D recall | R_miss 3D | prec 3D |
|---|---|---|---|
| p0_singleview | 0.5344 | 0.4692 | 0.1411 |
| **triangulated** | **0.5896** | **0.5858** | **0.1483** |
| CTRL_JITTER (spread-matched) | **0.4839** | **0.4125** | **0.0696** |

**Jitter is worse than doing nothing.** Moving points by the right *amount* in a random
direction costs −0.05 recall and halves precision; moving them by the amount multi-view
consensus dictates gains +0.055 recall. The displacement carries real information. This is the
single strongest result in Phase 1b.

### 2. The paired test — the gain is redistribution, not per-point accuracy

Identical seed pixel, identical initial z, the only difference being whether consensus was
allowed to move it (n = 153,377):

| | median dist. to nearest GT crease | frac within tolerance |
|---|---|---|
| single-view | **0.02160** | 0.1411 |
| triangulated | 0.02746 | **0.1483** |

Triangulation is closer for only **45.2 %** of paired points and its median distance is
*worse*. FIXED (outside → inside tolerance) **6.87 %**, BROKE **6.15 %**, net **+0.72 %**.
So triangulation does not make the average point better — it **redistributes** points, and the
ones it fixes land on creases nothing else covered, which is why recall moves far more
(+0.115 R_miss) than precision does (+0.007). The free-space cull then supplies the rest of
the precision gain (0.1483 → 0.1690).

### 3. Why precision is capped at 0.17 — it is the detector's semantics, not triangulation error

83 % of triangulated points are not within tolerance of a GT crease. Are they mis-triangulated,
or are they correctly-triangulated things that simply are not creases? Splitting the cloud by
that and measuring multi-view consistency:

| | n | mean consistent-neighbour fraction | ≥80 % consistent |
|---|---|---|---|
| ON a GT crease | 22,946 | 0.9366 | 0.9201 |
| **NOT on a crease** | 112,868 | **0.8697** | **0.7799** |

The off-crease points are **almost as multi-view consistent as the on-crease ones**. They are
real, correctly-triangulated 3D structure — chair's **printed floral fabric pattern** and
shading edges — not triangulation failure. **The precision ceiling is a detector-semantics
limit: DexiNed returns photometric edges, the GT asks for dihedral creases, and on chair those
two sets differ by roughly 5×.** Triangulation places the photometric edges correctly; most of
them are simply not creases.

---

## Sensitivity

| arm | 3D recall | R_miss 3D | prec 3D | note |
|---|---|---|---|---|
| **20 refs, K=6, ρ=0.20 (primary)** | 0.5899 | 0.5857 | 0.1690 | |
| ρ = 0.02 | 0.5980 | 0.5905 | 0.1643 | a ±2 % bracket does as well as ±50 % |
| ρ = 0.50 | 0.5907 | 0.5835 | 0.1704 | wide epipolar search buys nothing |
| K = 2 | 0.4961 | 0.4843 | 0.1312 | **worse than single-view** — too few views |
| K = 12 | 0.5716 | 0.5633 | 0.1754 | slightly worse than K=6 |
| **40 refs, K=6** | **0.6753** | **0.6914** | 0.1636 | best arm |
| budget-matched (85,325 pts) | 0.5318 | 0.5198 | 0.1386 | vs single-view 0.4452 / 0.3872 / 0.1098 |

- **ρ is irrelevant** (0.5980 → 0.5835 across a 25× range of search width). The answer is
  already determined within ±2 % of the 3DGS median depth: this is *local refinement*, not
  depth found from scratch. Honest framing — the 3DGS depth does most of the work and
  consensus corrects the last few percent.
- **Consensus needs enough views.** K=2 is *worse than not triangulating at all* (0.4961 vs
  0.5361); K=6 is the sweet spot; K=12 falls back slightly as neighbours get too far apart.
  This is why the spec's "≥2 supporting views" matters — but the support threshold itself is
  nearly free (sup≥1 / ≥2 / ≥3 differ by <0.01), because chair's edge maps are dense enough
  that support is close to saturated (98.6 % at ≥2).
- **More reference views help and the ordering survives**: at 40 refs tri reaches 0.6753 /
  0.6914 against single-view 0.6583 / 0.6331 and chance 0.6100 / 0.5401.

---

## The verdict

| spec condition | threshold | primary (20 refs) | best (40 refs) | |
|---|---|---|---|---|
| 3D recall | GO > 0.79 / MARGINAL [0.64, 0.79] / NO-GO ≤ 0.55 | 0.5899 | **0.6753** | **MARGINAL** |
| R_miss | ≥ 0.40 | **0.5857** | **0.6914** | **PASS** |
| raw precision | not below ~0.30 | 0.1690 @1.5px-eq / **0.3947** @0.5 % bbox | 0.1636 / **0.3855** | radius-dependent |
| better than single-view depth? | (NO-GO's stated rationale) | +0.115 R_miss | +0.058 R_miss | **clearly yes** |

### **MARGINAL.**

The best arm's 3D recall **0.6753 falls inside the spec's MARGINAL band [0.64, 0.79]**; the
primary 20-reference arm at 0.5899 sits just below it, in the unlabelled gap between NO-GO
(≤0.55) and MARGINAL. R_miss passes its bar in every arm by a wide margin. GO is not met in
any arm — no configuration approaches 0.79. NO-GO is not met either, and its stated rationale
("no better than single-view depth") is explicitly false: triangulation beats single-view on
recall *and* precision, at lower density, budget-matched, and against a spread-matched null.

The spec's own MARGINAL caption is exactly what the evidence says:
**"triangulation helps localization but coverage is still 2D-detector-bound."**

### Two caveats on how the thresholds were applied

- **The 0.79 threshold does not live in this metric.** 0.79 is a 2D *pixel* recall from the
  M1b pipeline; the number being compared to it is a 3D chamfer recall at a 1.5 px-equivalent
  radius, a space in which the **gaussian pool itself scores 0.2766**. No cloud in this repo
  has ever reached 0.79 there. In the 2D space where 0.79 actually lives, the triangulated
  cloud scores **0.9212** — but the chance control scores **0.9566**, so that comparison is
  saturated and cannot support a verdict (Phase 0 established this). Reported both ways;
  the verdict is taken in the 3D metric, which is the only discriminative one.
- **The ~0.30 precision bar is radius-dependent** and the spec does not name a radius.
  Triangulation passes it at the 0.5 %-bbox radius (0.3947, above the gaussian pool's 0.2872
  and single-view's 0.3718) and fails it at the 1.5 px-equivalent radius (0.1690).

### What this means for the next lever

The spec's MARGINAL branch asks whether "a stronger / multi-view-fused 2D detector" is the next
lever. The texture analysis says **no, not a stronger one**. DexiNed already sees the structure
and triangulation already places it correctly — 87 % of the off-crease points are multi-view
consistent. What is missing is a **crease-vs-texture discriminator**: something that separates
a dihedral crease from a printed pattern edge. That is a *semantic* problem, not a detection or
a geometry problem, and it is where the remaining 5× of precision lives. Nothing was built
toward it; this is reported for the decision.

## Honest caveats

- Half the localization improvement is contributed by the free-space cull, which uses the 3DGS
  depth. The cull is repairing points that triangulation itself pushed off-surface, so
  "triangulation + cull" is the unit that works, not triangulation alone.
- ρ-insensitivity means the 3DGS median depth is doing most of the placement and consensus is
  correcting the last few percent. Calling this "multi-view triangulation" is accurate but the
  3DGS depth is not incidental to it.
- The 3DGS was fit on all 100 `transforms_train` views including the 10 TEST views; TEST is
  held out from candidate generation, not from the reconstruction.
- `render_gbuffer` is run-to-run nondeterministic (CUDA `index_add_` atomics, pre-existing).
- The cached DexiNed maps were computed on the GT Blender photos, not on a 3DGS render; the
  +0.5 px grid correction is applied throughout (`halfpix=0.5`).
