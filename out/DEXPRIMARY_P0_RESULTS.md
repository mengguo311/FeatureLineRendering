# DexiNed-primary PHASE 0 — coverage-ceiling gatekeeper.
# **VERDICT: NO-GO on lego (the gate scene) — MARGINAL on chair**

Spec `tier1/dexprimary_p0_spec.md`. Held-out TEST views {5,15,…,95}, no tuning, nothing
committed. Mesh EVAL-ONLY: it is read by `scripts/dexprimary_p0.py:gt_labels()` (labels) and
by the scorer; the method path (`lift_view()` = cached DexiNed maps + `render.render_gbuffer`
depth) imports no mesh — `grep -n "mesh\|trimesh" src/{render,common,visibility,epipolar_consensus}.py`
returns only docstrings.

New artifacts: `scripts/dexprimary_p0.py`, `scripts/dexprimary_p0_{viz,table}.py`,
`scripts/dexprimary_p0_sweep{,2}.sh`, `out/dexprimary_p0_{lego,chair}_*.json`,
`out/dexprimary_phase0_{lego,chair}.png`, `cache/dexp0_gt_{lego,chair}_a30.npz`,
`logs/dexp0_*.log`. One additive method-path change: `render.render_gbuffer(...,
with_median_depth=True)` returns the alpha≥0.5 first-hit depth the spec asks for (default off).

---

## Verdict

| gate (frozen in the spec) | required | measured (lego, robust depth) | |
|---|---|---|---|
| **R_miss** — 3D chamfer @ 1.5 px-equiv, robust depth, **best of 8 arms** | ≥ 0.50 GO / < 0.35 NO-GO | **0.0952** (chance 0.0940) | **NO-GO** |
| R_miss — 2D, DexiNed's own view (the *2D ceiling*, no depth tested) | — | **0.385** (chance 0.353) | below GO |
| overall lifted recall vs the fixed-pool ceiling (3D, matched radius) | > pool 0.152 | 0.225 at chance 0.232 | **does not clear** |

**NO-GO on lego**, at chance, in every arm. chair reaches R_miss **0.4888** — inside the spec's
**MARGINAL** band and 1.3–1.4× its chance control — so the failure is scene-dependent, not
uniform. The pre-registered pivot (multi-view epipolar triangulation) is the registered next
step, but the evidence says it is aimed at chair's gap and **not** at lego's; see "On the
pre-registered pivot". Nothing beyond Phase 0 was built.

Two findings behind the verdict matter more than the verdict:

1. **On lego the DexiNed lift is statistically indistinguishable from a random surface cloud.**
   A density-matched cloud of *random foreground points* on the same 3DGS surface, lifted with
   the same depth, matches or beats it on every **recovery** metric:

   | lego, best case (arm D) | DexiNed (median depth) | chance (`ctrl_randfg`) |
   |---|---|---|
   | R_miss 3D @1.5 px-equiv | 0.0897 | **0.0880** |
   | recall 3D | 0.2112 | **0.2219** |
   | R_miss 2D LOO | 0.6632 | **0.6887** |
   | 2D coverage of all GT creases | 0.7763 | **0.8269** |
   | *precision 3D* | **0.1825** | 0.1533 |

   The one place DexiNed does separate is **3D precision, 1.19×** chance — so the signal is not
   literally zero, it is simply an order of magnitude too weak to break a coverage ceiling.
   Any R_miss quoted on lego without this control is not evidence.
2. **A hard cardinality bound, independent of depth.** At thr 0.5 + NMS, DexiNed emits
   **11,697 edge px/view on lego** against a **12,937 px/view** miss-set — ratio **0.904**. The
   edge map is *smaller than the set it must cover*, before a single point is backprojected.
   On chair the ratio is **4.33**, and chair behaves completely differently. This, not the
   depth, is the binding constraint on lego.

---

## Step 1 — the gaussian miss-set (and a correction to the spec's expectation)

"Covered" = some **visible** de-floatered gaussian centre projects within τ px of the visible
GT crease point, in that view. Population = visible GT crease **points**, pooled over the 10
TEST views (n = 1,748,144 lego / 1,002,286 chair) — the same population `LEGO_CEILING_AUTOPSY`
Figure B and `URS_RESULTS` use.

| scene | τ | miss-fraction (2D pts) | (2D unique px) | (3D, any view) | pool coverage | raw-ply coverage |
|---|---|---|---|---|---|---|
| **lego** | 1.5 | **0.3663** | 0.3157 | 0.2508 | 0.6337 | 0.6945 |
| lego | 2.5 | 0.1573 | 0.1370 | 0.1108 | 0.8427 | 0.8911 |
| **chair** | 1.5 | **0.2618** | 0.1557 | 0.1208 | 0.7382 | 0.8225 |
| chair | 2.5 | 0.0985 | 0.0508 | 0.0287 | 0.9015 | 0.9376 |

lego 0.3663 **reproduces `LEGO_CEILING_AUTOPSY.md` Figure B (UNCOVERED = 0.3663) exactly** —
an independent re-derivation, which validates the eval path used for everything below.

**The spec's "should be ~0.44 on lego given the 0.56 ceiling" is the wrong number for the
spec's own definition, and 0.56/0.79 is the wrong ceiling to compare against.**

- 0.44 is `CAP`'s miss vs the post-`pull+prune` **linelet** set, not vs gaussian centres.
- 0.5572 / 0.7908 is `R@1.5` **after pull+prune at f=1.00** — the ceiling of the *prune*, which
  still discards 43.6 % of the pool (99,721 → 56,269 lego). The **fixed-pool** ceiling in this
  metric is **0.6337 (lego) / 0.7382 (chair)**. Both are quoted below; the pool number is the
  one the "coverage ceiling is breakable" claim has to beat.

---

## Step 2 — the lift

Frozen zero-shot DexiNed (kornia, `DexiNed_BIPED_10.pth`, 35.2 M params, BIPED, sha256
`bd4c603e…`), cached maps `out/dexined_edges_{scene}/`, canonical `nms_thin`, thr 0.5.
Backprojected with `X_c = [z(u−cx)/f, z(v−cy)/f, z]` (the G-buffer depth is camera-space **z**,
not ray length), world = `Rᵀ(X_c − t)`. Five depth arms:

| arm | depth used |
|---|---|
| `naive` | transmittance-weighted **mean** depth at the pixel (the spec's naive arm) |
| `naive_fill` | mean depth, holes filled from nearest finite (`epipolar_consensus.fill_depth`) |
| `fgmin` | min of the mean depth over ±2 px **along the 2D edge normal** (foreground bias) |
| `median` | **alpha ≥ 0.5 first-hit depth** — new, additive `render_gbuffer(with_median_depth=True)` |
| `medmin` | min of the median depth over ±2 px along the edge normal (**the spec's robust arm**) |

`median`/`medmin` are the spec's "foreground/median depth". The new median-depth code is
unit-tested against an analytic two-splat case (6/6 exact, including the <0.5-opacity fallback).

**Lift sanity (the spec's pitfall):** every lifted point reprojects into its source view at
median **0.0000 px**, p99 0.0001 px, max 0.0001 px, and **100 %** fall inside the gaussian
bbox. The camera convention is the proven one (`blender c2w → diag(1,−1,−1,1) → invert`).

---

## Step 3 — recovery, with the controls that decide it

Three controls, all scored by the **identical** measurement:

| control | what it isolates |
|---|---|
| `ctrl_randfg` | N random **foreground** pixels (α≥0.5), same N, same depth arm → chance at matched density on the same surface |
| `ctrl_shufz` | the **same DexiNed edge pixels** with their depths randomly permuted → does the depth lift do any work? |
| `gauss_pool` | the visible gaussian centres themselves → calibrates every radius |

### Three of the spec's own metrics turn out to be degenerate. Reported, not suppressed.

1. **2D "own-view" recovery is circular.** Lifting with view *v*'s depth and scoring in *v*
   reprojects onto the edge pixel it came from (round-trip 0.0000 px). It measures only
   *"does DexiNed SEE it in 2D"* — reported as the **2D ceiling**, never as the headline.
2. **2D leave-one-out is saturated.** Nine views of lifted points cover **cov_fg ≈ 0.50** of the
   foreground within 1.5 px. `lift = R_miss / cov_fg` is **1.06–1.15 on lego** (chance = 1.0),
   and on lego `ctrl_shufz` — depth deliberately destroyed — scores **higher** (0.692) than the
   real lift (0.531). The metric is measuring point density, not placement.
3. **The spec's 3D radius, 1.5 % of the bbox diagonal (0.0442 lego), is vacuous.** The gaussian
   pool recovers **81.9 % (lego) / 100 % (chair)** of *its own* miss-set at that radius. At
   0.5 % it still self-recovers 0.449 / 0.867. Only the **1.5 px-equivalent** radius
   (0.00508 lego / 0.00515 chair, = δ·z̄/f) discriminates: the pool self-recovers 0.009 / 0.003
   there. **All headline 3D numbers use the 1.5 px-equivalent radius**, with the looser radii
   reported for completeness.

### The gate numbers

`R_miss` at the 1.5 px-equivalent 3D radius, robust depth (`median`/`medmin`), best over every
arm run. Chance = the density-matched random-foreground cloud measured identically.

| scene | best robust R_miss (3D) | chance (`ctrl_randfg`) | ratio | 2D ceiling (own-view) | GO bar |
|---|---|---|---|---|---|
| **lego** | **0.0897** | 0.0880 | **1.02×** | 0.385 | 0.50 → **NO-GO** |
| chair | **0.2488** | 0.1664 | **1.50×** | 0.636 | 0.50 → below bar |

**lego fails every reading of the gate**, and fails it at chance. chair has a real, measurable
effect (1.5× the null, and its lifted cloud beats the gaussian pool in 3D — recall 0.360 vs
0.277, precision 0.141 vs 0.076) but still lands under 0.35.

### Which depth variant matters — the spec's explicit question

The **median (α≥0.5 first-hit) depth is the best 3D arm on both scenes**, beating the naive
mean depth (chair 0.249 vs 0.198; lego 0.090 vs 0.087 at best-case). The crude
foreground-min-along-the-normal (`fgmin`/`medmin`) **hurts** in 3D — it over-shoots toward the
foreground at internal creases where both sides sit at the same depth. So: the principled
robust depth helps, the crude one does not, and **neither changes the verdict**.

`ctrl_shufz` (same edge pixels, depths permuted) collapses in 3D — lego 0.043 vs 0.090, chair
0.042 vs 0.249. **The depth lift does real work**; it is simply not enough to beat a random
cloud on lego.

### Why lego and chair differ — the mechanism

| | lego | chair |
|---|---|---|
| DexiNed edge px / view (thr 0.5 + NMS) | 11,697 | 8,132 |
| miss-set px / view | 12,937 | 1,878 |
| **ratio (edge px : miss-set px)** | **0.90** | **4.33** |

`out/dexprimary_phase0_lego.png` shows it directly: DexiNed returns a **clean, sparse
12,336-pixel contour** — the silhouette and the major part boundaries — while lego's miss-set
lives on the **dense stud/tread field**, where DexiNed emits nothing. On chair the miss-set is
smooth curvilinear piping along the seat and back rim, which DexiNed traces, and recovery in
the displayed view reaches 0.889.

**The property that makes DexiNed attractive — clean, complete, thin contours — is exactly why
it cannot enumerate lego's high-frequency crease set.** The spec's premise ("the miss-set is
flat decals that DexiNed sees because they are photometric") holds for chair-like structures;
on lego the miss-set is dominated by fine *geometry* too dense for a contour map, not by decals.

### Does DexiNed see the lego miss-set at *any* threshold? No.

Precision is Phase 1's job, so this arm spends it freely: `ms` maps, half-pixel corrected,
20 TRAIN source views, threshold dropped from 0.5 to 0.05.

| thr | edge px/view | edge : miss-set ratio | R_miss 3D (median) | chance (`ctrl_randfg`) |
|---|---|---|---|---|
| 0.50 | 12,407 | 0.96 | 0.0897 | 0.0880 |
| 0.20 | 13,019 | 1.01 | 0.0941 | 0.0911 |
| 0.05 | 13,311 | 1.03 | 0.0952 | 0.0940 |

A 10× threshold drop buys **+7 % edge pixels and +0.006 R_miss**, and the chance control moves
by exactly as much. **The binding constraint is NMS ridge count, not the threshold**: NMS keeps
only ridge maxima, so the cardinality of the edge map is set by how many distinct contours
DexiNed produces, and DexiNed does not produce contours on lego's stud field at any confidence.

### Arms that could have rescued it, and what each was worth (lego, R_miss 3D, robust depth)

| arm | R_miss | Δ |
|---|---|---|
| base (native, thr 0.5, 9-view LOO) | 0.0735 | — |
| A + half-pixel grid correction (+0.5 px) | 0.0768 | +0.003 |
| B + multi-scale `ms` maps | 0.0734 | −0.000 |
| C src = 20 TRAIN views (URS-legal) | 0.0876 | +0.014 |
| D best case (ms + half-pix + TRAIN20) | 0.0897 | +0.016 |
| E–F D at thr 0.20 / 0.05 | 0.0941 / 0.0952 | +0.022 |

Every knob, all together, moves lego from 0.074 to 0.095 against a **0.50** GO bar and a
**0.35** NO-GO floor, with the chance control at 0.094. There is no configuration in which
this passes.

### The budget-matched arm, and a calibration of prior work in this repo

`URS_RESULTS.md` reports **lego 2D coverage 0.7617** for TEED ridges lifted through the same
3DGS depth (89,748 pts, 20 TRAIN views, voxel-dedup to a 3x budget) and calls it **GO** against
a frozen 0.75 threshold — but it has **no density-matched chance control**; it compares only
against baseline linelets (0.4338), which are thin curves rather than a surface-spread cloud.
So I re-ran with URS's own protocol — voxel-dedup by bisection to the identical 89,748 cap —
applied to **every** cloud including the controls:

| lego, budget = 89,748, 20 TRAIN views | 2D coverage | cov_fg | lift | R_miss 3D | recall 3D |
|---|---|---|---|---|---|
| **DexiNed-lifted, naive depth** | **0.7707** | 0.668 | 1.11 | 0.0468 | 0.0913 |
| DexiNed-lifted, median depth | 0.7066 | 0.631 | 0.93 | 0.0597 | 0.1355 |
| *URS reference (TEED, same cap)* | *0.7617* | — | — | — | — |
| **chance: random foreground, same cap** | **0.7116** | 0.697 | 0.82 | 0.0559 | 0.1196 |
| depth destroyed (`ctrl_shufz`) | 0.5645 | 0.499 | 1.16 | 0.0093 | 0.0095 |
| the gaussian pool | 0.5040 | 0.463 | — | 0.0085 | 0.1499 |

**The budget cap de-saturates the metric** (cov_fg 0.77 → 0.67) and a real signal appears:
DexiNed 0.7707 vs chance 0.7116. **URS's 0.7617 is therefore not a pure density artifact** —
it beats a matched random surface cloud. But the honest margin is **≈ +0.05, not the +0.33**
that the comparison against baseline linelets implies, and the chance cloud alone reaches
**0.712 against URS's frozen 0.75 GO threshold**. That is a calibration of the earlier result,
not a refutation of it; my uncapped arms overstated the case and are superseded by this one.

**It changes nothing for Phase 0.** Budget-matched, lego's 3D numbers are still dead: R_miss
0.060 vs chance 0.056, and the gaussian pool's own 3D recall (0.150) is *higher* than the
DexiNed cloud's (0.136). chair holds up under the same cap — R_miss 0.324 vs chance 0.242
(1.34x), recall 0.417 vs the pool's 0.277 (1.51x), precision 0.106 vs chance 0.057 (1.87x).

---

## "Does overall lifted recall clear the 0.56 / 0.79 ceiling?" — answered literally

Yes numerically, and the answer is worthless, because the chance control clears it too.

2D coverage of ALL visible GT creases at τ=1.5, best case (ms + half-pix + 20 TRAIN views):

| | lego | chair |
|---|---|---|
| pipeline ceiling `R@1.5` f=1.00 (the spec's 0.56 / 0.79 — a *prune* ceiling) | 0.5572 | 0.7908 |
| all-gaussian-centre coverage (the actual *fixed-pool* ceiling) | 0.6337 | 0.7382 |
| **DexiNed-lifted cloud** | **0.8551** | **0.9495** |
| **chance: random foreground points, matched count** | **0.8269** | **0.9507** |
| **depth destroyed (`ctrl_shufz`)** | **0.9057** | **0.9100** |
| foreground painted within 1.5 px (`cov_fg`) | 0.77 | 0.67 |

On chair the chance cloud scores **higher** than the real lift; on lego the depth-destroyed
cloud scores highest of all. At this point density the 2D coverage metric is saturated and
cannot support a GO in either direction. **The 3D chamfer at the 1.5 px-equivalent radius is
the only measurement in this report that separates the arms**, and it is where the verdict is
taken. In that metric the lifted cloud clears the pool on chair (0.541 vs 0.277) and does not
on lego (0.225 vs 0.152, chance 0.232).

## chair — the idea does work here, and lands in the MARGINAL band

Same measurement, same controls, best case (ms + half-pixel + 20 TRAIN source views):

| cloud (chair, arm D) | R_miss 3D | recall 3D | precision 3D |
|---|---|---|---|
| **DexiNed-lifted, median depth** | **0.4857** | **0.5413** | **0.1351** |
| naive depth | 0.4634 | 0.5096 | 0.1220 |
| chance (`ctrl_randfg`, matched count) | 0.3446 | 0.4420 | 0.0668 |
| depth destroyed (`ctrl_shufz`) | 0.1028 | 0.1054 | 0.0092 |
| **the gaussian pool itself** | 0.0029 | 0.2766 | 0.0764 |

At thr 0.05 the best chair R_miss is **0.4888** (chance 0.3696).

- **1.41× the chance control, with 2.0× its precision at higher recall.** Density alone raises
  recall *and* lowers precision; this raises both. The effect is real.
- **The lifted cloud roughly doubles the gaussian pool's 3D coverage** (0.541 vs 0.277) at
  1.8× its precision (0.135 vs 0.076). On chair, the fixed-pool ceiling *is* broken in 3D.
- R_miss **0.489 < 0.50** — it lands in the spec's **MARGINAL** band [0.35, 0.50], just under
  the GO line, and only with 20 source views. At the spec's literal 10-TEST-view setup it is
  0.249.

The frozen gate is stated on lego, so the overall verdict is NO-GO. But the honest reading is
not "the 3DGS depth at edges is too smeared" — the spec's NO-GO caption. It is:

> **DexiNed-edge seeding is a structure-dependent coverage-ceiling breaker, not a general one.**
> It works where the miss-set is smooth curvilinear contour (chair: edge:miss-set ratio 4.3,
> R_miss 0.49, 1.4× chance, 2× the pool). It fails at chance where the miss-set is a dense
> high-frequency crease field that no thin-contour detector enumerates (lego: ratio 0.9–1.0,
> R_miss 0.095, 1.0× chance).

## On the pre-registered pivot

The spec pre-registers multi-view epipolar triangulation of the DexiNed edges, on the reading
that single-view depth is too smeared. The evidence does not support that reading **on lego**:

- lego's **2D ceiling is 0.385** — already below the 0.50 GO bar *before any depth is used*.
  Triangulation improves where a point lands, not which edges exist.
- `ctrl_shufz` shows the depth **is** doing work (3D 0.090 → 0.043 when destroyed), so it is
  noisy rather than useless.
- The `median` (α≥0.5) depth already recovers most of what a better depth could buy, and
  changes lego's R_miss by +0.02.

On **chair**, where the 2D ceiling is 0.636 and the 3D number (0.486) sits well below it,
triangulation is aimed at the actual gap and is the sensible next probe. That asymmetry is the
useful output of Phase 0. **Nothing was built; this is reported, not acted on.**

## Honest caveats

- The cached DexiNed maps were computed on the **GT Blender photos**, not on a 3DGS RGB render
  (no tier1 code renders full-SH RGB from the vanilla model). This is the same input every
  prior repo number used, it is not a mesh leak, but it is not literally "the TEST-view render"
  the spec names. It carries the +0.492 px grid offset, which arm A isolates: worth +0.003
  (lego) / +0.039 (chair).
- The 3DGS was fit on **all 100** `transforms_train` views including the 10 TEST views. TEST is
  held out from the line-extraction pull, **not** from the reconstruction.
- `render_gbuffer` is **run-to-run nondeterministic** (CUDA `index_add_` atomics): two calls with
  identical arguments differ by up to 8e-2 on a few pixels. Pre-existing; measured here because
  the new flag would otherwise look like the cause (OFF-vs-OFF differs as much as OFF-vs-ON).
- `ctrl_randfg` samples non-edge pixels, where the rendered depth is most reliable, while the
  method is forced to sample exactly at the depth discontinuities. That asymmetry is part of
  what the comparison is measuring and is stated rather than corrected away.
