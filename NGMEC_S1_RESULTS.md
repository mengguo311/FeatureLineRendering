# NG-MEC Stage 1 — isolating the epipolar-consensus selectivity gain over raw TEED

Held-out TEST throughout. Mesh EVAL-ONLY. No per-scene retuning: the TEED threshold is
chair's VAL 0.5 on both scenes, and lego runs the *identical* (K, m, tau, rho) selected on
chair. Nothing committed.

New code, all additive:
`src/epipolar_consensus.py` (METHOD PATH, mesh-free),
`scripts/ngmec_s1_{build,build_prop,dump_proposals}.py` (method-path drivers, mesh-free),
`scripts/ngmec_s1_{table,cullprobe}.py` (analysis / EVAL-ONLY diagnostic),
`scripts/ngmec_s1_{m1b,lego,diag_chain}.sh`,
and **one** additive line-pair in `final_recipe.py` adding the source name `teed_epi`.

**Nothing published changed.** Re-verified against a copy of the *original* pre-TRACK-M
`final_recipe.py`: `photo_edge_map` / `photo_edge_dt` are bit-identical on **both scenes** for
the `canny` path (3 cfg sets x 5 views) and for the `teed` and `union` arms (2 thresholds x
2 views). The `teed_epi` source is deliberately implemented as *the existing TEED cache path
pointed at a different cache directory* — the consensus module writes its surviving edges in
the TEED file layout (key `native`, values in {0,1}, already NMS-thinned because the arm is a
subset of the thinned TEED map), so it reads through `teed_edge_map` with `nms=False`,
`thr=0.5` and no existing source's behaviour can change.

Geometry self-check before any number was produced: back-project a rendered-depth pixel and
re-project it into its own view — **3.3e-5 px** round-trip error, depth error 4.4e-8; the
torch and numpy projection routes into a neighbour view agree to **1e-4 px**.

---

## What was built

For every proposal edge pixel `x` in view `v`:

1. read the 3DGS-rendered depth `d(x)` (G-buffer — mesh-free; holes filled from the nearest
   valid pixel, so silhouette edges are not silently deleted),
2. sample the viewing ray at S depths spanning `[d/(1+rho), d*(1+rho)]` — an **epipolar
   segment** in every neighbour view, whose length is set by `rho`,
3. project those samples into each of the `K` nearest **TRAIN-split** neighbour cameras and
   read that view's proposal-edge distance transform,
4. a neighbour **supports** `x` if the segment passes within `tau` px of one of its edges,
5. keep `x` iff at least `m` of `K` neighbours support it.

`rho` is the knob that decides what "epipolar" means. `rho=0` is pure reprojection at the
rendered depth; `rho=7` (d/8..8d) is effectively the whole epipolar line, i.e. the depth-free
reading of "epipolar band". The support **count** (0..K) is cached, so every `m` is free.

Neighbours are drawn from the **TRAIN split only** (80 views) — strictly cleaner than the
published M1a recipe, which consumes 25 spread views including 3 VAL and 3 TEST.

### First result, before any pipeline: what each setting actually removes (chair, K=4)

| arm | keeps % of TEED | px/view (TEED 7,765) |
|---|---|---|
| t1.5_r0_m2 | 80.3% | 6,248 |
| **t1.5_r0_m3** | **62.9%** | 4,894 |
| t1.5_r0_m4 | 41.0% | 3,160 |
| t2.5_r0_m3 | 80.1% | 6,243 |
| t1.5_r0.2_m4 | 71.9% | 5,582 |
| **t1.5_r7_m4** | **73.7%** | 5,744 |
| *t1.5_r7_m2* | *99.3%* | *7,719* |
| *t2.5_r7_m2* | *99.9%* | *7,755* |

**The literal, depth-free reading of "epipolar band" is nearly vacuous.** At `rho=7` and
`m=2` the gate removes **0.7%** of TEED's pixels, because an epipolar line crossing an
800x800 image with ~1.2% edge density passes within 1.5 px of *some* edge essentially always.
Only the depth-anchored variants (`rho=0`, `rho=0.2`) are discriminating at all. Every number
below therefore uses depth-anchored epipolar segments, and the `rho=7` arm is retained purely
as the honest control showing why.

---

## The 2D mechanism works — the gate is genuinely selective

`scripts/ngmec_s1_cullprobe.py` (EVAL-ONLY) partitions each eval view's TEED edge set into
KEPT and CULLED and measures the GT-crease purity of each part. The spec's own NO-GO language
names the failure mode to look for — *"consensus is culling true creases = localization not
selectivity"* — and this measures it directly.

**chair, tau=2, held-out TEST (raw TEED edge purity 0.510):**

| arm | % culled | purity(KEPT) | purity(CULLED) | ratio | crease recall kept | culled FP: occ / fold / **HALL** |
|---|---|---|---|---|---|---|
| t2.5_r0_m3 | 18.8% | **0.556** | **0.315** | **0.57** | **0.884** | 0.273 / 0.071 / **0.655** |
| t1.5_r0_m2 | 21.0% | 0.549 | 0.365 | 0.66 | 0.850 | 0.282 / 0.080 / **0.638** |
| t1.5_r0_m3 | 38.1% | 0.566 | 0.420 | 0.74 | 0.687 | 0.334 / 0.095 / 0.571 |
| t1.5_r0_m4 | 60.4% | 0.570 | 0.471 | 0.83 | 0.442 | 0.378 / 0.109 / 0.513 |
| *t1.5_r7_m4* | *21.0%* | *0.517* | *0.484* | ***0.94*** | *0.800* | *0.543 / 0.116 / 0.341* |

(VAL is the same shape: raw purity 0.402, t2.5_r0_m3 keeps at 0.429 and culls at 0.303.)

**The gate does what it was designed to do.** At its mildest useful setting it raises TEED's
2D edge purity from **0.510 to 0.556** while retaining **88.4%** of TEED's crease pixels, and
**65.5%** of what it deletes is hallucination-class false positive. The `rho=7` control again
behaves as the null: ratio 0.94, i.e. it deletes almost at random with respect to creases.

So the failure that follows is **not** the failure the spec's NO-GO clause anticipated. The
gate is not culling true creases. It is culling the right pixels — and the pipeline does not
care.

## Why the 2D gain does not survive — two hypotheses, both tested

**Hypothesis 1: the DT barely moves, so the score cannot reorder. REFUTED.**
The M1a evidence is `exp(-dt/SIGMA)` with `SIGMA = 16` px, so a filter only matters if it
moves the distance transform. It does — by as much as the TRACK M intervention that produced
a +0.24 swing:

| arm | % px culled | mean \|dDT\| | p90 | max | mean \|d evidence\| |
|---|---|---|---|---|---|
| epi t1.5_r0_m2 | 25.4% | 2.036 | 7.000 | 47.15 | 0.061 |
| epi t2.5_r0_m3 | 23.3% | 2.446 | 8.784 | 47.58 | 0.071 |
| epi t1.5_r0_m3 | 44.7% | 3.983 | 12.581 | 48.38 | 0.114 |
| epi t1.5_r0_m4 | 65.9% | 8.375 | 23.375 | 68.39 | 0.206 |
| **TRACK M's M3 mask, which DID work** | — | **3.816** | 12.193 | 35.19 | **0.163** |

`epi_t1.5_r0_m3` moves the DT by 3.98 px mean against M3's 3.82 px, and the evidence by 0.114
against 0.163. The intervention is the same order of magnitude. "Too small to matter" is dead.

**Hypothesis 2: the movement is not in the right PLACE. Partly true, and quantified.**
Stratifying the DT movement by distance to the nearest GT crease (EVAL-ONLY, cached oracle
crease DTs), a gate that helps must move the DT *far* from creases and leave it alone *on*
them:

| mean \|dDT\| in bins of distance-to-GT-crease | [0,2) | [2,5) | [5,10) | [10,20) | [20,inf) | **far/near** |
|---|---|---|---|---|---|---|
| epi t1.5_r0_m2 | 0.380 | 0.409 | 0.751 | 1.719 | 3.856 | 10.16 |
| epi t2.5_r0_m3 | 0.404 | 0.494 | 0.908 | 2.055 | 4.672 | 11.58 |
| epi t1.5_r0_m3 | 1.065 | 1.198 | 1.754 | 3.461 | 7.236 | 6.79 |
| epi t1.5_r0_m4 | 3.411 | 3.707 | 4.551 | 7.151 | 14.363 | 4.21 |
| **TRACK M's M3 mask** | 0.418 | 0.563 | 1.716 | 4.051 | 6.815 | **16.31** |

The mild arms *are* spatially discriminating (10-12x) and not far off M3's 16.3x — but they
move the DT less far from creases (3.9-4.7 px vs 6.8) for the same on-crease disturbance
(~0.40 px vs 0.42). The strict arms buy more far-field movement and pay for it on the crease
itself (3.4 px at m=4). Neither profile is as clean as M3's, but the *direction* is right, so
this is a difference of degree — which on its own does not explain a 10x smaller downstream
effect.

---

## The measurement the gate is defined on — chair, held-out TEST, M1b

Identical `run_m1b.py` path and identical published-baseline flags for every arm (`--gate`,
edge=sharp, pull_split=train, eval_split=test, steps=100, lr=0.35, delta_max=5, len_thr=0.9).
Only `--score` differs, and those scores differ only in whether the TEED edge map was
epipolar-consensus filtered. Segments, headline stage `pull+prune[tuned+len]`.

| arm | f | P@1.5 | R@1.5 | **dP@1.5** | **dR@1.5** | dP@2.5 |
|---|---|---|---|---|---|---|
| raw TEED | 0.45 | 0.5925 | 0.7348 | — | — | — |
| raw TEED | 0.40 | 0.6148 | 0.7207 | — | — | — |
| raw TEED | 0.30 | 0.6417 | 0.6759 | — | — | — |
| **epi t1.5_r0_m3** | **0.45** | **0.6167** | **0.7391** | **+0.0242** | **+0.0044** | +0.0275 |
| epi t1.5_r0_m3 | 0.50 | 0.5918 | 0.7527 | +0.0192 | -0.0033 | +0.0229 |
| epi t1.5_r0_m3 | 0.40 | 0.6301 | 0.7236 | +0.0153 | +0.0029 | +0.0175 |
| epi t1.5_r0_m3 | 0.35 | 0.6436 | 0.6985 | +0.0139 | +0.0003 | +0.0154 |
| epi t1.5_r0_m3 | 0.30 | 0.6513 | 0.6748 | +0.0096 | -0.0012 | +0.0125 |
| epi t1.5_r0_m3 | 0.22 | 0.6605 | 0.6181 | +0.0010 | -0.0049 | +0.0045 |
| epi t1.5_r0_m4 | 0.45 | 0.6160 | 0.7338 | +0.0234 | -0.0009 | +0.0276 |
| epi t2.5_r0_m3 | 0.45 | 0.6081 | 0.7440 | +0.0156 | **+0.0092** | +0.0178 |
| epi t1.5_r0.2_m4 | 0.45 | 0.6074 | 0.7387 | +0.0149 | +0.0040 | +0.0170 |

Summary over f in [0.22, 0.50]:

| arm | best dP@1.5 | at f | dR there | mean dP | **worst dR** |
|---|---|---|---|---|---|
| **epi t1.5_r0_m3** | **+0.0242** | 0.45 | +0.0044 | +0.0139 | **-0.0049** |
| epi t1.5_r0_m4 | +0.0234 | 0.45 | -0.0009 | +0.0128 | -0.0337 |
| epi t2.5_r0_m3 | +0.0156 | 0.45 | +0.0092 | +0.0108 | -0.0026 |
| epi t1.5_r0.2_m4 | +0.0149 | 0.45 | +0.0040 | +0.0092 | -0.0107 |

The gain is **real, monotone in f, and free**: at the best operating point the gate improves
precision *and* recall simultaneously, and the worst recall cost anywhere in the band for the
best arm is **-0.005** against a ceiling of -0.05. The "additive-not-destructive" requirement
is met with a factor of ten in hand.

It is also **about half the size the gate demands**: +0.024 against a +0.05 bar.

---

## Temporal — the third gate clause

`scripts/m1b_stroke_temporal.py`, chair, held-out TEST trajectory 5->15, look-at-corrected
orbit. Winning arm `epi_t1.5_r0_m3` at f=0.30 (the f the published TEED temporal was measured
at, so the comparison is like-for-like). `P_pop` = fraction of strokes with no forward-warped
match plus the split/merge rate. BASELINE = naive image-space Canny re-traced every frame.

| frames | epi P_pop | **epi flicker win** | TEED P_pop | **TEED flicker win** | d ratio | epi Frechet med |
|---|---|---|---|---|---|---|
| 30 | 0.097 | 8.09x | 0.093 | 8.50x | -0.41x | 0.342 |
| 60 | 0.073 | 10.55x | 0.068 | 11.35x | -0.80x | 0.172 |
| 120 | 0.064 | 11.86x | 0.059 | 12.85x | -0.99x | 0.086 |
| **240** | 0.062 | **12.19x** | 0.058 | **13.12x** | **-0.93x** | 0.043 |

**The TEED baseline was re-run in this same session** rather than quoted across runs, because
the clause passes by only 0.19x. Both arms, identical harness, identical run:

| frames | epi P_pop | epi flicker win | TEED P_pop | TEED flicker win | d ratio | published TEED |
|---|---|---|---|---|---|---|
| 30 | 0.097 | 8.09x | 0.093 | 8.50x | -0.41x | 8.50x |
| 60 | 0.073 | 10.55x | 0.068 | 11.35x | -0.80x | 11.35x |
| 120 | 0.064 | 11.86x | 0.059 | 12.86x | -1.00x | 12.85x |
| **240** | 0.062 | **12.19x** | 0.058 | **13.13x** | **-0.94x** | 13.12x |

The in-session baseline reproduces the published figures to **0.01x** at every frame count, so
the cross-run comparison was sound and the within-run one confirms it.

**This clause passes on its number and fails on its intent, and both readings are reported.**
The spec's text is *"flicker-win ratio stays >= 12.0x at 240 frames on chair (temporal
no-regress vs the TEED baseline)"*. The arm reaches **12.19x**, so the frozen numeric bar is
met — by 0.19x. But it is a **7.1% regression** against the TEED baseline's 13.12x, so the
parenthetical "no-regress" is not met. The NO-GO floor (< 11.0x) is not tripped.

---

## lego — the same configuration, carried over with no retuning

`epi_t1.5_r0_m3` is the arm selected on chair. Per the spec's no-retune rule it is applied to
lego unchanged (same K, m, tau, rho; same TEED threshold 0.5 from chair's VAL).

| lego arm | best dP@1.5 | at f | dR there | **mean dP** | **worst dR** |
|---|---|---|---|---|---|
| epi t1.5_r0.2_m4 (mildest) | +0.0093 | 0.30 | +0.0008 | **+0.0085** | -0.0007 |
| **epi t1.5_r0_m3 (the chair pick)** | +0.0010 | 0.50 | -0.0280 | **-0.0058** | -0.0492 |
| epi t2.5_r0_m3 | +0.0025 | 0.45 | -0.0126 | -0.0003 | -0.0214 |
| epi t1.5_r0_m4 | **-0.0056** | 0.50 | -0.0573 | **-0.0215** | **-0.1007** |

**The gate does not transfer.** The chair-selected setting is worth **-0.0058 mean dP** on
lego and costs up to 0.049 recall; the stricter setting is actively harmful (-0.0215 mean dP,
recall -0.10, blowing the -0.05 ceiling). Only the *mildest* arm is positive there, at
+0.0085 — a third of chair's already-sub-threshold gain.

The reason is visible in the build statistics: **at identical parameters the gate is far more
aggressive on lego than on chair.**

| keeps % of proposals | chair | lego |
|---|---|---|
| t1.5_r0_m2 | 80.3% | 70.7% |
| t1.5_r0_m3 | 62.9% | **48.5%** |
| t1.5_r0_m4 | 41.0% | **26.3%** |
| t2.5_r0_m3 | 80.1% | 71.6% |

Lego's TEED map is twice as dense (15,797 vs 7,765 px/view) and its features are fine, dense
brickwork -- stud rims, tread links, baseplate grid. The 3DGS-rendered depth at a sub-pixel
stud edge is a blend across the discontinuity, so the reprojected sample lands off the
corresponding edge in the neighbour view and the true crease loses its support. That is the
**localization failure the spec's NO-GO clause names**, and on lego it is what happens: the
same knob that removes 37% of chair's proposals removes 52% of lego's, and the extra 15
points come disproportionately out of real creases.

**Conditional-law placement.** The spec's CONDITIONAL branch anticipated "fires on lego (hard
surface, epipolar bands clean) but not chair". The observed pattern is the **opposite**: it
fires weakly on **chair**, the texture-stress scene, and not at all on lego. That direction is
at least consistent with TRACK L's purity-conditional law -- a selectivity device has
something to remove only where the edge field is texture-contaminated -- but the effect on
chair is half the bar, so the conditional branch does not rescue the result.

---

## The diagnostic that explains the size of the effect

TRACK M measured that a selectivity mask applied to an **already-selective** detector is worth
almost nothing (+0.0040, carrying 0.08 of the lift) while the **same** mask on a permissive
detector is worth **+0.2408**. TEED is already selective. So gating TEED is structurally the
first of those two cases, and Stage 1 as specified could not have produced a large number
whatever the geometry did.

That is a testable claim, not a rationalisation. `src/epipolar_consensus.py` was generalised
to accept any proposal cache, and the **identical** gate was run on the permissive un-blurred
Canny (0,20,60) — a detector with no selectivity prior at all. Chair, held-out TEST, segments
headline stage:

| arm | f=0.40 dP / dR | f=0.30 dP / dR | f=0.22 dP / dR |
|---|---|---|---|
| epiSL t1.5_r0_m2 | +0.0033 / +0.0088 | +0.0035 / +0.0010 | +0.0047 / -0.0012 |
| epiSL t1.5_r0_m3 | +0.0174 / +0.0157 | +0.0190 / +0.0022 | +0.0208 / -0.0116 |
| **epiSL t1.5_r0_m4** | **+0.0394 / +0.0310** | **+0.0550 / +0.0004** | **+0.0713 / -0.0247** |
| epiSL t2.5_r0_m3 | +0.0104 / +0.0099 | +0.0109 / -0.0001 | +0.0100 / -0.0117 |

**On a base that lacks selectivity the same geometric gate is worth up to +0.071** — three
times what it is worth on TEED — and at f=0.40 it improves precision *and* recall together.
The structural prediction holds.

**But the calibration is the real finding.** On the *same* base, at the *same* f, with the
*same* metric:

| selectivity source applied to the permissive un-blurred Canny | dP@1.5 at f=0.40 |
|---|---|
| **learned (TEED support mask, TRACK M)** | **+0.2673** |
| **geometric (epipolar consensus, this experiment)** | **+0.0394** |
| ratio | **6.8x weaker** |

And in absolute terms the gated permissive Canny reaches P 0.4521 at f=0.40, still far below
raw TEED's 0.6148. Multi-view epipolar consensus **is** a genuine selectivity device — it
removes the right pixels (culled purity 0.32 vs kept 0.56) and it helps where selectivity is
missing — but it is roughly **one seventh** as strong a one as a 58,910-parameter learned edge
detector, and TEED has already taken most of what there is to take.

---

## Why lego fails, measured — and a 2D probe that predicts the downstream result

The same cull-probe on lego (held-out TEST, raw TEED purity 0.683):

| lego arm | % culled | purity(KEPT) | purity(CULLED) | **ratio** | crease recall kept |
|---|---|---|---|---|---|
| t1.5_r0.2_m4 | 18.8% | 0.684 | 0.683 | **1.00** | 0.812 |
| t1.5_r0_m2 | 27.4% | 0.649 | 0.773 | **1.19** | 0.690 |
| t2.5_r0_m3 | 26.5% | 0.651 | 0.773 | **1.19** | 0.700 |
| t1.5_r0_m3 | 49.6% | 0.607 | 0.761 | **1.25** | 0.448 |
| t1.5_r0_m4 | 69.9% | 0.547 | 0.742 | **1.36** | 0.241 |
| *t1.5_r7_m4* | *8.0%* | *0.702* | *0.466* | *0.66* | *0.945* |

**On lego the gate is ANTI-selective.** Every depth-anchored setting deletes a set that is
*more* crease-pure than the set it keeps (ratio > 1), and the strict one retains only 24% of
lego's crease pixels. That is exactly the failure the spec's NO-GO clause names — "consensus
is culling true creases = localization not selectivity" — and it is a property of the scene,
not of the code: lego's features are sub-pixel stud rims and tread links, so the
3DGS-rendered depth there is a blend across the discontinuity, the reprojected sample lands
off the corresponding edge, and the true crease loses its support. Coarse occluding contours,
which are geometrically robust, survive — 54-59% of what the gate keeps as non-crease is
occluding contour.

### The 2D probe predicts the 3D outcome

Pooling all eight (scene, arm) pairs that have both measurements, held-out TEST on both sides:

| scene | arm | purity(CULLED)/purity(KEPT) | crease recall kept | **mean dP@1.5** | worst dR |
|---|---|---|---|---|---|
| chair | t2.5_r0_m3 | 0.57 | 0.884 | **+0.0108** | -0.0026 |
| chair | t1.5_r0.2_m4 | 0.71 | 0.797 | **+0.0092** | -0.0107 |
| chair | t1.5_r0_m3 | 0.74 | 0.687 | **+0.0139** | -0.0049 |
| chair | t1.5_r0_m4 | 0.83 | 0.442 | **+0.0128** | -0.0337 |
| lego | t1.5_r0.2_m4 | 1.00 | 0.812 | **+0.0085** | -0.0007 |
| lego | t2.5_r0_m3 | 1.19 | 0.700 | **-0.0003** | -0.0214 |
| lego | t1.5_r0_m3 | 1.25 | 0.448 | **-0.0058** | -0.0492 |
| lego | t1.5_r0_m4 | 1.36 | 0.241 | **-0.0215** | -0.1007 |

**Pearson r = -0.866 (p = 0.0055, n = 8); Spearman rho = -0.810.** The sign of the downstream
effect is set by whether the gate's 2D cull is crease-selective, and the crossover sits at
ratio = 1 exactly where it should. This is a cheap, mesh-free-*able* screening statistic: the
ratio needs a crease proxy to compute here (it is an EVAL-ONLY diagnostic as run), but it
means a Stage 2 gate can be *rejected in 2D* before any 3D pipeline is run.

---

## Paired per-view tests — the effect is small but it is not noise

`scripts/teedgen_perview.py`, tau=1.5, `pull+prune[spec]` stage (the stage the saved keep-mask
defines exactly for every arm), 10 held-out TEST views, paired by view.

**chair, `epi_t1.5_r0_m3` vs raw TEED:**

| f | metric | mean d | sd | t | views A>B |
|---|---|---|---|---|---|
| 0.45 | segP | **+0.0181** | 0.0028 | **+20.60** | **10/10** |
| 0.45 | segR | -0.0019 | 0.0057 | -1.03 | 3/10 (n.s.) |
| 0.40 | segP | **+0.0129** | 0.0030 | **+13.76** | **10/10** |
| 0.40 | segR | +0.0056 | 0.0055 | +3.19 | 8/10 |
| 0.30 | segP | **+0.0098** | 0.0035 | **+8.95** | **10/10** |
| 0.30 | segR | +0.0047 | 0.0070 | +2.15 | 6/10 |

**lego, at f=0.30:**

| arm | metric | mean d | sd | t | views A>B |
|---|---|---|---|---|---|
| epi t1.5_r0.2_m4 (mild) | segP | +0.0096 | 0.0040 | +7.62 | **10/10** |
| epi t1.5_r0.2_m4 (mild) | segR | +0.0029 | 0.0031 | +2.98 | 9/10 |
| **epi t1.5_r0_m3 (chair pick)** | segP | **-0.0112** | 0.0044 | **-8.01** | **0/10** |
| **epi t1.5_r0_m3 (chair pick)** | segR | **-0.0515** | 0.0102 | **-15.98** | **0/10** |

The chair precision gain is **unanimous across all ten views at every f tested**, with t up to
20.6 — this is a real effect, not a one-view artefact, and it costs no recall. It is simply
small. The lego harm from the same configuration is equally unanimous in the other direction
(0/10 on both axes).

---

# FROZEN GO / NO-GO — the verdict

The rule, as frozen in `ngmec_s1_spec.md` before any number existed:

> **GO**: dP@1.5 >= +0.05 over raw TEED on chair held-out, at cost of <= 0.05 absolute recall
> drop, AND flicker-win ratio >= 12.0x at 240 frames on chair (temporal no-regress vs the
> TEED baseline).
> **NO-GO / rethink**: dP@1.5 < +0.02 on chair, OR recall drop > 0.05, OR flicker-win < 11.0x.

Evaluated on the best chair arm, `epi_t1.5_r0_m3`, segments headline stage, held-out TEST:

| clause | required | measured | result |
|---|---|---|---|
| **GO** dP@1.5 | **>= +0.05** | **+0.0242** (f=0.45; 10/10 views, t=+20.6) | **NOT MET** — half the bar |
| **GO** recall cost | <= 0.05 absolute | **-0.0049** worst in band | **MET**, with 10x margin |
| **GO** flicker-win @240f | >= 12.0x | **12.19x** | **MET by 0.19x** (but -7.1% vs TEED's 13.12x, so the parenthetical "no-regress" is *not* met) |
| **NO-GO** dP < +0.02 | — | +0.0242 | not tripped *(but 2 of the 4 chair arms are below +0.02)* |
| **NO-GO** recall drop > 0.05 | — | 0.0049 | not tripped *(tripped on lego: -0.1007 for t1.5_r0_m4)* |
| **NO-GO** flicker-win < 11.0x | — | 12.19x | not tripped |

## VERDICT: the gate returns **neither GO nor NO-GO** — it lands in the undefined interval.

dP@1.5 = **+0.0242** sits between the NO-GO floor (+0.02) and the GO bar (+0.05). Since **GO
is what authorises Stage 2 and GO is not met, the operational answer is: do not proceed to
Stage 2 as specified.** Reported as **MARGINAL / rethink**, which is the branch the spec
reserves for exactly this.

Three things should be held together in reading that:

1. **The effect is real.** +0.018 segment precision at f=0.45, unanimous across 10/10 held-out
   views at t=+20.6, at zero recall cost — in fact precision and recall improve *together* at
   the best operating point. This is not a null result.
2. **The effect is half the size required, and the requirement was not arbitrary** — the arc
   has never reached P@1.5 >= 0.85 and the best arm here reaches 0.6167.
3. **It does not transfer.** On lego the identical configuration is worth **-0.0058** mean dP
   and is unanimously harmful per-view (0/10 on both axes). A Stage 1 component that only
   works on one of two scenes, at half its bar, does not earn a Stage 2.

## What the diagnostics say Stage 2 should and should not do

- **Do not gate TEED.** The measurement that explains the size of the result is that a
  selectivity device applied to an already-selective detector buys ~nothing (TRACK M: +0.0040)
  while the same device on a permissive one buys a lot (+0.2408). Stage 1 as specified is
  structurally the first case. Confirmed here: the identical epipolar gate is worth **+0.0242
  on TEED** and **up to +0.0713 on the permissive Canny**.
- **Geometric consensus is a ~7x weaker selectivity device than the learned prior.** On the
  same base, same f, same metric: learned mask **+0.2673**, epipolar consensus **+0.0394**.
  Stacking a 7x-weaker second device on top of the strong one is not a route to +0.05.
- **The 3DGS depth is the limiting factor, and Stage 2's normal anchor inherits it.** The gate
  fails on lego because the rendered depth at sub-pixel stud rims is a blend across the
  discontinuity, so reprojection misses the true crease. Any Stage 2 component that reads
  3DGS geometry *at fine features* — including the proposed additive normal anchor — meets
  the same wall. The spec already records that vanilla-3DGS normals are AUC~0.5 for
  fabric-vs-crease; this adds that the *depth* is also unreliable exactly where lego's
  features live.
- **There is now a cheap 2D screen.** purity(CULLED)/purity(KEPT) predicts the sign and rough
  size of the downstream effect at **r = -0.866 (p = 0.0055)** across both scenes and all
  arms, with the crossover at ratio = 1. Any future gate can be rejected in 2D before a single
  M1b run.

---

## Caveats, stated because they bound the claim

1. **"Epipolar" had to be given a depth prior to mean anything.** The literal depth-free
   reading (rho=7) removes 0.7% of TEED's pixels at m=2 and is a measured null (cull ratio
   0.94 on chair, 0.66 on lego, i.e. it deletes nearly at random w.r.t. creases). Every
   positive number in this document comes from a **depth-anchored** epipolar segment, which
   uses the 3DGS G-buffer. That is still mesh-free, but it is a stronger assumption than the
   spec's wording, and it is why the gate inherits the depth's failure modes on lego.
2. **The sweep selected on chair; lego was never tuned.** m/K/tau/rho were chosen by chair
   behaviour and carried to lego unchanged, per the spec. The mildest arm (t1.5_r0.2_m4) is
   in fact lego's best (+0.0085) and chair's worst (+0.0092) — so a per-scene retune would
   have produced a slightly better lego number and a *worse* headline, and was not done.
3. **The temporal clause is measured at f=0.30, not at the best-dP f=0.45**, because f=0.30
   is where the published TEED temporal baseline exists and the comparison had to be
   like-for-like. The gate's precision gain is larger at f=0.45; its temporal cost there is
   not measured.
4. **The GO bar is evaluated on the segments headline stage.** The points protocol and the
   spec-prune stage are in `out/ngmec_s1_table_{chair,lego}.json`; the orderings agree, the
   magnitudes differ slightly, and no reading of them reaches +0.05.
5. **Neighbour views are TRAIN-split only** (80 views), which is stricter than the published
   M1a recipe's 25 spread views (3 VAL + 3 TEST among them). The consensus therefore uses no
   held-out imagery, though the M1a photometric aggregate it feeds still does, as before.
6. **The `teed_epi` source is not a new code path.** It is the existing TEED cache reader
   pointed at a different directory. This was deliberate: it makes "did anything published
   change?" answerable by construction rather than by inspection.

## Definition of done

| spec requirement | where | status |
|---|---|---|
| epipolar-consensus gate as a NEW additive edge source, existing sources untouched | `src/epipolar_consensus.py` + one line-pair in `final_recipe.py` | done; published paths **bit-identical on both scenes**, re-verified against the original module |
| K nearest neighbours, support in >= m of K, sweep m in {2,3,4}, tau in {1.5,2.5} | build stats table | done — plus a `rho` sweep that turned out to be the load-bearing knob |
| no mesh in the method path | `grep -n "mesh_oracle\|trimesh"` on `src/epipolar_consensus.py`, `scripts/ngmec_s1_{build,build_prop,dump_proposals}.py` | clean (only the docstring banner matches) |
| no per-scene retuning; carry TEED 0.5 | both scenes | done |
| dP@1.5 / dR@1.5 vs raw TEED across f in [0.22,0.50], chair AND lego | gate tables | done, 6 f values x 4 arms x 2 scenes |
| temporal Frechet + flicker-win at 240 frames for the winning arm | temporal section | done (12.19x vs baseline 13.12x) |
| per-view paired stats | per-view section | done, t up to +20.6, 10/10 views |
| GO / NO-GO / CONDITIONAL verdict | verdict section | **neither GO nor NO-GO → MARGINAL/rethink; Stage 2 not authorised** |
| results to out/*.json + this document | — | done |
| do not commit until reviewed | — | **nothing committed** |

### Artefacts

`out/epi_edges_{chair,lego}_t*_r*_m*/` (18 arms x 2 scenes), `out/prop_edges_chair_cannysharplow/`,
`out/epi_edges_chair_cannysharplow_t*_r*_m*/`, `out/ngmec_s1_build_{chair,lego}.json`,
`out/ngmec_s1_buildprop_chair_cannysharplow.json`, `out/trackC_seeds_chair_ngmec{,SL}.json`,
`out/trackC_seeds_lego_ngmec.json`, 24x `out/m1b_chair_ng_*.json`, 24x `out/m1b_lego_ng_*.json`,
12x `out/m1b_chair_ngsl_*.json`, `out/ngmec_s1_table_{chair,lego}.json`,
`out/ngmec_s1_cullprobe_{chair,lego}.json`, `out/ngmec_s1_perview_{chair,lego}.json`,
`out/m1b_stroke_temporal_table_{ngepi,ngbase}.{json,md}`.
