# TEED generalisation (lego) + rankability mechanism ablation

Held-out split frozen as `src/view_split.py` (TRAIN 80 / VAL {0,10,..,90} / TEST {5,15,..,95}).
Mesh is EVAL-ONLY throughout; the method path (`final_recipe.py`, `run_m1b.py` above the
EVAL banner) contains no mesh reference. Nothing committed.

New/changed code, all additive:
`scripts/recall_trackB_teed.py --scene lego` (unchanged script, new scene),
`scripts/{teedgen_verdict,teedgen_trackM_table,teedgen_perview}.py`,
`scripts/teedgen_{queue,queue2,queue3,queue4,temporal,M_shift}.sh`, `scripts/teedgen_plot.py`,
`--teed_cache`/`--arms_json`/`--tag` on `recall_trackC_seeds.py`,
`--teed_cache`/`--canny_variants`/`tau=1.5` on `recall_trackC_detector.py`,
four new edge sources in `final_recipe.py` (`teed_soft`, `teed_cc`, `cannymask`, plus the
`mask_shift` control), and an adaptive-chunk / env-overridable `max_elems` in
`src/mesh_oracle.py`.

**Everything published stays bit-identical.** Verified directly against a copy of the
pre-change module: `photo_edge_map` / `photo_edge_dt` agree exactly for `canny` (2 cfg sets
x 5 views) and for the `teed` and `union` arms; the mesh-oracle chunk change reproduces the
depth buffer with `max|d| = 0.0`. Reproduction controls: the recomputed lego Canny DP
reproduces the cached lego evidence with `max|d| = 0.000000`, and M1b lego canny f=0.30
returns 29,916 seeds / 25,279 keep with seg P@1.5 0.5826 / R@1.5 0.4168 -- the published
baseline to 5e-6 (GPU non-determinism). Chair canny f=0.30 reproduces 0.6573 / 0.5959 exactly.


---

---


---

## Executive summary

- **TRACK L verdict: GO** -- TEED's advantage transfers to lego zero-shot. LIFT_P > 0 at
  every f in [0.22, 0.50] (6/6 arms above the frontier), best **+0.0346** (interpolated) /
  **+0.0223** (Pareto envelope), against a Canny frontier swept and densified to 16 points out
  to f=1.00. TEED's maximum precision 0.6606 exceeds Canny's 0.6360 over the *entire* frontier.
- **The headroom shrank, as the spec predicted it might.** Measured symmetrically (both
  Canny frontiers swept and densified out to f=1.00): **+0.0776 on chair -> +0.0346 on lego,
  a 2.2x shrinkage** (4.2x on the conservative Pareto envelope, +0.0940 -> +0.0223). Against
  chair's *published* f<=0.50 sweep the chair figure is +0.0607 and the shrinkage 1.8x; the
  symmetric comparison is the honest one and it makes the shrinkage larger, not smaller.
- **And the falsification nuance fired.** On lego an un-blurred permissive Canny does not
  merely also work -- it **beats TEED by 2.0-2.6x** (+0.0697 / +0.0582). The identical
  detector scores **-0.2081 on chair**. A **+0.278 swing in LIFT_P with nothing changed but
  the object.** The chair finding is therefore *refined into a conditional law*, not confirmed
  as a universal one, and not killed.
- **But the un-blurred Canny pays for its lego win in TEMPORAL COHERENCE.** It has the best
  stroke geometry of the three arms (Frechet median 0.076 vs TEED's 0.081) and the **worst
  popping at every frame count**, and the gap widens with trajectory length: the flicker win
  drops from the baseline's **11.61x to 9.67x at 240 frames (-17%)**, while TEED *improves* it
  to **12.10x**. So on lego the choice is a trade, not a dominance -- and **TEED is the only
  arm that improves both axes on both scenes.**
- **The conditional law has a measured mechanism, and a cheap 2D predictor.** Un-blurring the
  Canny changes edge purity by **-56.9% on chair** and **+18.0% on lego** (same script, same
  tau, same oracle). On chair, recall costs -0.476 of purity per unit bought and TEED is 6.8x
  more purity-efficient than a threshold; on lego recall is *free* (+0.159, purity rises), so
  a selectivity device has no job. This 2D number predicts the M1b sign flip without running
  M1b.
- **TRACK M: SELECTIVITY carries the lift, and it is not a metaphor.** Strip TEED of its edge
  placement and its confidence values, keep only a binary "there is a contour here" mask, and
  apply it to the detector that is catastrophic on its own: over the f values where both arms
  exist, LIFT_P goes **-0.2224 -> +0.0184**, a **+0.2408 swing** (+0.2421 under the other
  estimator -- the swing is estimator-invariant, and the paired per-view test measures it
  directly at +0.2025 segment precision, t=+13.69, **10/10 views**). The masked arm recovers
  **half to four-fifths** of the full TEED gain depending on estimator (0.51 interpolated,
  0.83 envelope). Continuous confidence contributes ~10% (+0.0050 against a +0.0517 mean
  reference lift); connected-component continuity contributes +0.018 and is actively destructive when strong
  (-0.047 at L=50 px). Rolling that same mask 15 px -- **removing more pixels, not fewer** --
  swings LIFT_P back to **-0.1066**, so the operative property is registration, i.e.
  selectivity in the strict sense, not thinning.


---

## TRACK L.1 -- TEED cached for lego, zero-shot, no retuning

Same script, same frozen in-repo BIPED checkpoint (`checkpoints/BIPED/5/5_model.pth`),
**58,910 parameters** -- the identical count reported for chair, i.e. provably the same
weights. Same contract (BGR minus `mean_bgr`, no /255, fused = last map, raw sigmoid, RGBA
composited over white, 2 scales, NMS-thinned downstream). **No per-scene tuning of any kind**;
the threshold 0.5 was chosen on chair's VAL and carried over unchanged.

100 views x 2 scales in **13.7 s** (137 ms/view), 57.1 MB -> `out/teed_edges_lego/`.
`frac>0.5` native 0.079-0.118 per view.

`out/teed_sample_lego_v{0,5,25}.png` shows what the numbers below are about: the M1a blurred
Canny keeps little more than the silhouette and a few strong contours, discarding every stud,
tread link and baseplate crease; TEED returns a near-complete line drawing.


---

## TRACK L.2 -- direct detector metric, 2D, before any pipeline

`scripts/recall_trackC_detector.py`, tau=2 (the script's TAU_MAIN, the tau every chair
go/no-go number was quoted at), same mesh oracle, same masks, TEED arms NMS-thinned so
stroke width is not a confound. `rec_miss` = fraction of the M1a-Canny miss-set recovered.

| lego TEST | R_GT | dRecall | P_GT | rec_miss | px/view | FP occ | FP fold | FP hall | P_line |
|---|---|---|---|---|---|---|---|---|---|
| canny_m1a (defines the miss-set) | 0.175 | — | 0.637 | — | 8,102 | 0.726 | 0.068 | 0.206 | 0.925 |
| **TEED nms@0.5** | **0.505** | **+0.330** | **0.683** | **0.428** | 14,842 | 0.565 | 0.129 | 0.306 | 0.903 |
| TEED nms@0.9 | 0.407 | +0.232 | 0.662 | 0.321 | 11,811 | 0.624 | 0.102 | 0.274 | 0.907 |
| union@0.5 | 0.528 | +0.353 | 0.681 | 0.428 | 19,375 | 0.591 | 0.118 | 0.291 | 0.907 |
| *cannysharp* (0,50,150) | 0.739 | +0.564 | **0.754** | 0.690 | 32,439 | 0.441 | 0.216 | 0.343 | 0.915 |
| ***cannysharplow*** (0,20,60) | **0.893** | **+0.718** | **0.751** | **0.874** | 42,169 | 0.374 | 0.239 | 0.387 | 0.904 |

(VAL is the same picture: canny_m1a 0.164/0.623, TEED 0.484/0.662, cannysharplow 0.887/0.732.)

Against the spec's detector rule TEED **passes on lego**: dRecall +0.330 (bar +0.18),
miss-set recovery 0.428 (bar 0.35), and the precision guard is not merely un-tripped --
**precision goes UP**, 0.637 -> 0.683.

That last number is the whole story. On chair, measured by the same script on the same TEST
views, adding recall *costs* purity: TEED 0.531 -> 0.510 (-4.0%) and the permissive Canny
0.531 -> **0.229 (-56.9%)**. On lego, adding recall *buys* purity, for **every** detector
tested: TEED +7.3%, cannysharp +18.4%, cannysharplow +18.0%. There is so little texture on
lego that almost anything you newly fire on is real geometry.

**The NO-GO clause "> 20% FP clustering on stud fillets / occlusions" -- reported and read
carefully.** TEED's FP mass on lego is 56.5% occluding-contour and 12.9% sub-30-deg fold.
Read literally the occluding fraction exceeds 20% -- but so does the *baseline Canny's*, at
**72.6%**, which is higher. There is no TEED-specific clustering: TEED's occluding fraction is
*lower* than the arm it replaces, its stud-fillet (sub-30-deg fold) fraction is 12.9% vs the
permissive Canny's 23.9%, and its precision against **all** legitimate feature lines
(crease | occluding contour | shallow fold) is 0.903 vs Canny's 0.925 -- a 2.2-point drop.
The high shared occluding fraction is a property of scoring lego against a 30-deg-dihedral
crease oracle, not a property of the detector. **Clause not tripped.**


---

## TRACK L.3 -- the control lego's frontier SHAPE forced

On chair the Canny f-frontier is a normal trade-off: precision falls as f (and recall) rise,
0.7057@R0.468 -> 0.5522@R0.722. **On lego it is not.** Canny's precision *rises* with f:

| lego canny f | 0.15 | 0.22 | 0.30 | 0.40 | 0.50 | 0.60 | 0.70 | 0.85 | **1.00** |
|---|---|---|---|---|---|---|---|---|---|
| seg P@1.5 | 0.5985 | 0.6104 | 0.6196 | 0.6238 | 0.6257 | 0.6278 | 0.6288 | 0.6335 | **0.6360** |
| seg R@1.5 | 0.1826 | 0.2358 | 0.2856 | 0.3359 | 0.3832 | 0.4286 | 0.4736 | 0.5297 | **0.5572** |

Densified to 16 points the pattern is unbroken -- f = 0.15, 0.22, 0.30, 0.35, 0.40, 0.45,
0.50, 0.55, 0.60, 0.65, 0.70, 0.80, 0.85, 0.90, 0.95, 1.00 give precisions 0.5985, 0.6104,
0.6196, 0.6214, 0.6238, 0.6237, 0.6257, 0.6269, 0.6278, 0.6274, 0.6288, 0.6330, 0.6335,
0.6352, 0.6360, 0.6360, i.e. monotone increasing to within 0.0004 everywhere.

The frontier's best point is its own endpoint. **At f=1.00 the keep-fraction selects every
one of the 99,721 gaussians -- i.e. no seeding at all -- and that beats every f<1 Canny
operating point on both axes.** The M1a photometric score, fed by the blurred Canny, does not
usefully rank lego gaussians; the seeding stage is worse than doing nothing.

This had to be measured before any lift was read. Quoting "a recall Canny cannot reach"
against a dial swept only to f=0.50 would have been scoring TEED against a dial that was
never turned far enough. All lego LIFT_P below is against the frontier **extended to f=1.00**,
and both an interpolated lift (chair-comparable) and a Pareto-envelope lift (well-posed even
for a non-monotone frontier: the best precision the dial reaches while *also* reaching at
least that recall) are reported.


---

## TRACK L.4 -- M1b, held-out TEST, segments headline stage `pull+prune[tuned+len]`

Identical `run_m1b.py` path and identical published-baseline flags for every arm
(`--gate`, edge=sharp, pull_split=train, eval_split=test, steps=100, lr=0.35, delta_max=5,
len_thr=0.9). **Only `--score` differs**, and those scores differ only in which 2D detector
fed the M1a photometric DT.

| lego arm | f | n_seed | n_keep | P@1.5 | R@1.5 | P@2.5 | R@2.5 | LIFT_P (env) |
|---|---|---|---|---|---|---|---|---|
| canny | 1.00 | 99,721 | 56,269 | 0.6360 | 0.5572 | 0.7971 | 0.6756 | — |
| canny | 0.50 | 49,860 | 31,915 | 0.6257 | 0.3832 | 0.7729 | 0.4773 | — |
| canny | 0.30 | 29,916 | 20,142 | 0.6196 | 0.2856 | 0.7618 | 0.3689 | — |
| **cannysharplow** | 0.22 | 21,939 | 16,668 | **0.6942** | 0.3706 | **0.8477** | 0.4987 | **+0.0582** |
| **cannysharplow** | 0.30 | 29,916 | 22,257 | 0.6838 | 0.4136 | 0.8387 | 0.5401 | +0.0478 |
| **cannysharplow** | 0.40 | 39,888 | 28,996 | 0.6739 | 0.4537 | 0.8302 | 0.5779 | +0.0379 |
| cannysharp | 0.22 | 21,939 | 18,775 | 0.6687 | 0.3586 | 0.8255 | 0.4756 | +0.0327 |
| **teed@0.5** | 0.22 | 21,939 | 16,548 | 0.6584 | 0.3541 | 0.7984 | 0.4717 | **+0.0223** |
| **teed@0.5** | 0.30 | 29,916 | 22,062 | 0.6563 | 0.4004 | 0.7982 | 0.5196 | +0.0203 |
| **teed@0.5** | 0.40 | 39,888 | 28,539 | 0.6535 | 0.4463 | 0.7987 | 0.5664 | +0.0175 |
| teed@0.5 | 0.70 | 69,805 | 44,718 | 0.6428 | 0.5225 | 0.7965 | 0.6401 | +0.0067 |
| teed@0.9 | 0.30 | 29,916 | 21,720 | 0.6519 | 0.3852 | 0.7914 | 0.4995 | +0.0159 |
| union@0.5 | 0.22 | 21,939 | 16,991 | 0.6474 | 0.3492 | 0.7884 | 0.4664 | +0.0114 |

### Best LIFT_P in f in [0.22, 0.50] -- lego vs chair, BOTH frontiers extended to f=1.00

The chair frontier as published stops at f=0.50. Lego's had to be pushed to f=1.00, so chair's
was too, and the comparison below is the symmetric one. This *raises* chair's TEED numbers,
because chair's Canny collapses at high f (P 0.361 at f=1.00) and TEED reaches recalls up
there at far better precision -- an advantage the published f<=0.50 sweep could not see.

| arm | **lego** interp / env | **chair** interp / env | chair, published f<=0.50 sweep |
|---|---|---|---|
| **cannysharplow** | **+0.0697 / +0.0582** | **-0.2081 / -0.1801** | -0.2081 |
| cannysharp | +0.0450 / +0.0327 | -0.1575 / -0.1328 | -0.1575 |
| **teed_native_0.5** | **+0.0346 / +0.0223** | **+0.0776 / +0.0940** | +0.0607 |
| teed_native_0.9 | +0.0276 / +0.0159 | +0.0424 / +0.0658 | +0.0424 |
| union_native_0.5 | +0.0236 / +0.0114 | +0.0371 / +0.0379 | +0.0371 |

Canny frontier endpoints, which is what makes the two scenes so different:

| | f=0.15 | f=0.50 | f=1.00 |
|---|---|---|---|
| chair canny P/R | 0.706 / 0.468 | 0.552 / 0.722 | **0.361 / 0.791** |
| lego canny P/R | 0.599 / 0.183 | 0.626 / 0.383 | **0.636 / 0.557** |

Chair's dial behaves like a seeding score should -- precision trades off against recall, and
it falls off a cliff past f=0.50. Lego's does not trade off at all: precision rises
monotonically with f, so its best point is "keep everything".

**Headroom shrinkage chair -> lego, measured symmetrically: 2.2x (interpolated, +0.0776 ->
+0.0346) or 4.2x (envelope, +0.0940 -> +0.0223).** Larger than the 1.8x implied by comparing
lego's extended frontier against chair's published f<=0.50 one.

*(Both frontiers were densified after an early version of this table used a 3-point extension:
chair f in {0.15..0.50, 0.55, 0.60, 0.65, 0.70, 0.80, 0.90, 1.00}, 14 points; lego 16 points.
The coarse extension inflated chair's TEED envelope lift to +0.1360; the densified value is
+0.0940. The lego numbers are unchanged by densification.)*

Two facts, both required to read the result honestly:

1. **TEED transfers.** Every TEED and union arm is above the extended Canny frontier at every
   f in the band -- 6/6 for teed@0.5, 3/3 for teed@0.9 and union. TEED's peak precision
   (0.6606, f=0.15) is higher than anything the Canny dial reaches at any f up to and
   including 1.00 (0.6360).
2. **But on lego it is the wrong tool.** The un-blurred Canny is 2.0-2.6x better and does it
   at a quarter of the compute. On chair that same detector is a disaster.

### The regime also inverts

On **chair** TEED's gain grows monotonically with f and turns negative at the bottom:

| chair teed05 LIFT_P (interp) | f=0.50 | f=0.45 | f=0.40 | f=0.35 | f=0.30 | f=0.22 | f=0.15 |
|---|---|---|---|---|---|---|---|
| | **+0.0776** | +0.0620 | +0.0607 | +0.0504 | +0.0416 | +0.0170 | **-0.0078** |

On **lego** it runs the other way -- largest at low f and decaying monotonically as f rises:

| lego teed05 LIFT_P (env) | f=0.70 | f=0.50 | f=0.40 | f=0.30 | f=0.22 | f=0.15 |
|---|---|---|---|---|---|---|
| | +0.0067 | +0.0128 | +0.0175 | +0.0203 | **+0.0223** | **+0.0246** |

The published chair caveat ("the gain reverses below f~0.22") is reproduced exactly
(-0.0078 at f=0.15) and **does not transfer**: on lego the gain is *largest* there. Chair's
blurred Canny already ranked usefully and TEED extended it at high coverage; lego's ranked not
at all (its frontier is monotone increasing), so the learned detector's contribution shows up
precisely where the keep-fraction is tight and ranking matters most.


---

## TRACK L.5 -- visualisation

`out/teed_lego_v{0,25}.png` (and `out/teed_lego_f{0.40,0.30}_v{0,5,25}.png`) =
{RGB | Canny linelets | TEED linelets | recovery map}. v0 is a VAL view; v5 and v25 are
held-out TEST. The recovery panel paints only GT crease pixels: grey = covered by both,
**green = covered only by the TEED arm**, red = missed by both.

| view | canny n | canny GTcov | teed n | teed GTcov | delta |
|---|---|---|---|---|---|
| VAL v0, f=0.40 | 14,922 | 0.4890 | **16,090** | **0.6676** | **+0.1786** |
| TEST v5, f=0.40 | 21,260 | 0.4424 | 22,752 | **0.6397** | **+0.1974** |
| TEST v25, f=0.40 | 23,101 | 0.6331 | **21,925** | **0.7245** | **+0.0914** |
| TEST v25, f=0.30 | 17,899 | 0.5657 | **16,627** | **0.6689** | +0.1032 |

At v25 the TEED arm draws **fewer** linelets and covers **more** GT crease -- the same
"fewer lines, better coverage" signature the chair viz showed. The green pixels cluster on
the track/tread wheels, the baseplate stud grid and the bucket interior; the residual red is
concentrated on the finest baseplate stud pattern, which neither arm resolves.

`out/teedgen_frontier_chair_vs_lego.png` is the two-panel summary of the whole TRACK L result:
the un-blurred Canny arms sit far below chair's frontier and above lego's, and lego's frontier
visibly rises left-to-right.


---

## TRACK L.6 -- temporal no-regress

`scripts/m1b_stroke_temporal.py`, lego, held-out TEST trajectory 5->15, look-at-corrected
orbit. Both arms at f=0.40, identical everything except the edge source. `P_pop` = fraction of
strokes with no forward-warped match plus the split/merge rate (lower = less flicker).
`BASELINE` = naive image-space Canny re-traced independently every frame; it is **identical for
both arms** (0.803 / 0.764 / 0.734 / 0.719), which is the cross-check that the harness itself
did not change.

| frames | canny P_pop | **TEED P_pop** | *sharplow P_pop* | canny ratio | **TEED ratio** | *sharplow ratio* |
|---|---|---|---|---|---|---|
| 30 | 0.234 | **0.230** | *0.240* | 3.44x | **3.49x** | *3.35x* |
| 60 | 0.144 | **0.139** | *0.148* | 5.30x | **5.48x** | *5.16x* |
| 120 | 0.091 | **0.084** | *0.097* | 8.11x | **8.69x** | *7.55x* |
| 240 | 0.062 | **0.059** | *0.074* | 11.61x | **12.10x** | ***9.67x*** |

| frames | canny Frechet med | TEED Frechet med | *sharplow Frechet med* |
|---|---|---|---|
| 30 | 0.628 | 0.598 | ***0.563*** |
| 60 | 0.332 | 0.316 | ***0.297*** |
| 120 | 0.171 | 0.162 | ***0.152*** |
| 240 | 0.086 | 0.081 | ***0.076*** |

**TEED: no regress -- the flicker win improves**, 3.4-11.6x to **3.5-12.1x**, with a better
Frechet median at every frame count. The result is *stronger* than chair's in one respect: on
chair the TEED arm won while drawing **fewer** strokes (723-727 vs 754-759), which invites the
objection that it simply drew less. On lego TEED draws **more** (1,640 strokes/frame from
2,846 chains vs canny's 1,424 from 2,408) and is still steadier on every metric.

### The un-blurred Canny -- the arm that WINS lego's f-frontier -- is the one that REGRESSES

This arm was run as a bonus and it changes the lego recommendation. `cannysharplow` has the
**best stroke geometry of the three** (Frechet median 0.076 vs 0.081 / 0.086 at 240 frames)
and the **worst popping at every frame count**, and the gap widens with trajectory length:
3.35x vs canny's 3.44x at 30 frames, but **9.67x vs 11.61x at 240 frames -- a 17% loss of the
flicker win at the finest motion**, precisely the regime the object-space carrier exists to
protect. It also draws the most strokes (1,830/frame from 3,272 chains).

So on lego the choice is a **trade, not a dominance**:

| lego, f=0.40 | M1b LIFT_P | temporal flicker win @240 frames | Frechet med @240 |
|---|---|---|---|
| canny (M1a baseline) | — | 11.61x | 0.086 |
| **TEED @0.5** | **+0.0175** | **12.10x (improves)** | **0.081** |
| **cannysharplow** | **+0.0379** | **9.67x (REGRESSES -17%)** | **0.076** |

**TEED is the only arm that improves both axes on both scenes.** The un-blurred Canny buys
roughly twice TEED's static LIFT_P on lego and pays for it with the temporal coherence that is
the entire point of extracting lines in object space rather than re-tracing them per frame.
That materially qualifies "just delete the blur": it is the right call **if the target is a
still frame**, and the wrong one if the target is an animation.



---

## TRACK L.7 -- THE VERDICT, against the rule frozen before any lego number existed

> **GO (generalises)**: LIFT_P > 0 at some f in [0.22, 0.50] on lego too, OR TEED reaches
> R_max >= Canny R_max + 0.12 at P >= 0.75 without precision collapse.
> **MARGINAL**: LIFT_P in [-0.01, +0.02] but TEED reaches higher-recall arms cleanly.
> **NO-GO (chair-overfit)**: LIFT_P <= -0.04 for all f <= 0.30, or > 20% FP clustering on
> stud fillets / occlusions.

| clause | evaluation on lego | result |
|---|---|---|
| **GO (a)** LIFT_P > 0 somewhere in f in [0.22, 0.50] | **+0.0223 to +0.0346** (best at f=0.22); positive at **every** f in the band; 6/6 arms above the frontier; paired per-view t=+9.88, **10/10 views** | **MET** |
| GO (b) R_max >= canny + 0.12 at P >= 0.75 | not evaluable at M1b (no arm reaches segment P>=0.75 at tau=1.5 on lego). **At seed level it is met**: TEED R_max **0.7509 at P 0.770** vs canny R_max 0.5961, **dR +0.155**, and canny never reaches P>=0.75 at any f | met at seed level, n/a at M1b |
| MARGINAL | best LIFT_P +0.0346 is outside [-0.01, +0.02] | not marginal |
| NO-GO (i) LIFT_P <= -0.04 for all f <= 0.30 | LIFT_P is **positive** at every f <= 0.30 | **not tripped** |
| NO-GO (ii) > 20% FP clustering on stud fillets / occlusions | TEED FP: 56.5% occluding, 12.9% sub-30-deg fold. The occluding fraction exceeds 20% -- but the **baseline Canny's is higher, 72.6%**, so there is no TEED-specific clustering; the stud-fillet (shallow-fold) fraction is 12.9% vs the permissive Canny's 23.9%; P_line (crease OR occluding OR fold) 0.903 vs canny 0.925. The shared high occluding fraction is a property of scoring lego against a 30-deg-dihedral oracle | **not tripped** |

### **VERDICT: GO.** The chair TEED finding generalises to lego zero-shot.

With one qualification the spec itself anticipated and that is **not** a failure of the
finding: **on lego the learned detector is not the right tool.** An un-blurred permissive
Canny beats it 2.0-2.6x, and that same detector is catastrophic on chair (-0.208). The
finding is therefore **refined into a conditional law**, not confirmed as a universal one:

> **Learned selectivity is required iff the native photometric edge field is
> texture-contaminated.** Operationally: measure what un-blurring does to Canny's edge purity.
> If it *falls* (chair, -56.9%), a learned detector is required and un-blurring is actively
> harmful. If it *rises* (lego, +18.0%), delete the blur -- that is the whole fix, and it
> beats the learned detector.


---

# TRACK M -- what property of TEED's edge map does M1b actually consume?

All arms are the identical `run_m1b.py` path with the identical published flags; only the
photometric edge source changes. Chair, held-out TEST, segments headline stage, LIFT_P against
the published Canny f-frontier. Reference = the published TEED arm (+0.0626 at f=0.40,
+0.0650 at f=0.30).

### The three variants, as implemented

- **M1 continuous confidence** (`teed_soft`). The M1a evidence is `exp(-dt/SIGMA)` with `dt`
  the distance to the nearest edge *pixel* -- a pixel is an edge or it is not. The soft arm
  replaces it with `E(x) = max_y (p(y)/p_ref)^gamma * exp(-|x-y|/SIGMA)`, so a faint detection
  contributes in proportion to its calibrated probability. Evaluated by quantising `p` into 13
  levels and taking the lower envelope of the per-level distance transforms (quantisation
  error <= 0.8 px over the dense part of the ladder). Its control is the published binarised
  arm (a hard step at 0.5).
- **M2 topological continuity** (`teed_cc`). 8-connected components of the thresholded,
  NMS-thinned map with fewer than L pixels are deleted. After NMS the map is one pixel wide,
  so a component's pixel count is its arc length. Control: no filter.
- **M3 selectivity as a mask** (`cannymask`). `canny AND dilate(TEED >= 0.5, r)`. TEED
  contributes **only a binary spatial support**: every surviving edge pixel was placed by
  Canny, at Canny's sub-pixel localisation, with none of TEED's confidence values. Run against
  both the published blurred Canny and the permissive un-blurred one -- the latter is the
  informative arm, because on its own it scores **-0.2224**.

### Edge density per arm (VAL+TEST pooled, px/view) -- so density can be ruled in or out

| canny | cannysharp | cannysharplow | teed@0.5 | cc10 | cc25 | cc50 | mask(M1a) | mask(sharplow) | shift15 | shift40 |
|---|---|---|---|---|---|---|---|---|---|---|
| 4,601 | 27,766 | 32,770 | 7,622 | 5,898 | 4,447 | 2,976 | 4,329 | 13,690 | 9,733 | 7,884 |

LIFT_P is **not** a function of this row, and that is the point. All at **f=0.40**,
interpolated:

| px/view | 4,447 | 4,601 | 7,622 | 9,733 | 13,690 | 32,770 |
|---|---|---|---|---|---|---|
| arm | cc25 | canny | teed@0.5 | shift15 | mask(sharplow) | cannysharplow |
| LIFT_P | **+0.1002** | 0 (defines it) | **+0.0607** | **-0.0995** | **+0.0348** | **-0.2325** |

Sorting by edge count gives +0.100, 0, +0.061, **-0.100**, +0.035, **-0.233** -- no monotone
function of density reproduces that, and the two arms nearest each other in count (9,733 vs
13,690, both derived from the *same* Canny with the *same* TEED support) differ by 0.13.

### Decomposition (chair, held-out TEST, segments headline stage)

Every arm swept over the same f grid as the reference, f in {0.50, 0.45, 0.40, 0.35, 0.30,
0.22}, against the Canny frontier **densified to 14 points** (see the note below on why that
matters). "Δ LIFT_P" is against each factor's own control at matched f. Both LIFT_P estimators
are reported because the carried-fraction figure is estimator-sensitive and the swing is not.

| factor | arm | control | Δ interp | Δ envelope |
|---|---|---|---|---|
| **M1** | teed_soft gamma=1 | TEED binarised @0.5 | **+0.0050** | **+0.0069** |
| **M2** | CC >= 10 px | TEED, no filter | +0.0183 | +0.0185 |
| **M2** | CC >= 25 px | TEED, no filter | +0.0195 | +0.0206 |
| **M2** | CC >= 50 px | TEED, no filter | **-0.0474** | **-0.0506** |
| **M3** | TEED support ∩ **M1a** Canny | canny frontier | **+0.0040** | +0.0208 |
| **M3** | TEED support ∩ **permissive** Canny | canny frontier | **+0.0295** | **+0.0450** |
| **M3 swing** | same, vs that Canny **unmasked** | cannysharplow | **+0.2408** | **+0.2421** |
| **M3 control** | that mask **rolled 15 px** | canny frontier | **-0.1066** | **-0.0952** |
| **M3 control** | that mask **rolled 40 px** | canny frontier | **-0.3246** | **-0.3174** |
| *CTL* | cannysharplow, unmasked | canny frontier | -0.2224 | -0.2053 |
| *CTL* | cannysharp, unmasked | canny frontier | -0.1674 | -0.1526 |

Per-f detail (LIFT_P interpolated, segments, held-out TEST):

| arm | f=0.50 | f=0.45 | f=0.40 | f=0.35 | f=0.30 | f=0.22 |
|---|---|---|---|---|---|---|
| **teed05 (reference)** | +0.0776 | +0.0620 | +0.0607 | +0.0504 | +0.0416 | +0.0170 |
| m1_soft gamma=1 | +0.0810 | +0.0875 | +0.0650 | +0.0522 | +0.0430 | +0.0108 |
| m2_cc10 | +0.0949 | +0.0992 | +0.0882 | +0.0702 | +0.0537 | +0.0133 |
| m2_cc25 | +0.1139 | +0.1080 | +0.1002 | +0.0722 | +0.0437 | -0.0115 |
| m2_cc50 | — | — | — | — | +0.0113 | -0.0474 |
| m3_mask(M1a) | +0.0057 | +0.0052 | +0.0016 | +0.0056 | +0.0049 | +0.0009 |
| **m3_mask(sharplow)** | **+0.0520** | +0.0456 | +0.0348 | +0.0246 | +0.0174 | +0.0030 |
| *m3_shift15 (control)* | — | — | *-0.0995* | *-0.1066* | *-0.1137* | — |
| *m3_shift40 (control)* | — | — | *-0.3229* | *-0.3264* | — | — |
| *cannysharplow* | — | — | *-0.2325* | — | *-0.2265* | *-0.2081* |

**Why the frontier had to be densified.** Several M-arms reach recalls above canny's f=0.50
point (m2_cc25 at f=0.40 reaches R 0.7411 vs canny's 0.7224). With the frontier sampled only at
f = 0.50 / 0.70 / 1.00 up there, the Pareto envelope becomes a coarse step function and
reported jumps that were artefacts of the sampling (m2_cc10 at f=0.40 read +0.070 against the
f<=0.50 frontier, +0.166 against the 3-point extension, and **+0.0882** against the 14-point
one). Five extra canny points fixed it, and after densification the two estimators agree to
within 0.02 on every arm except the two whose recall sits in the sparsest region.

**What is estimator-sensitive and what is not.** The *carried fraction* of the mask arm ranges
**0.51 (interpolated) to 0.83 (envelope)** -- report it as a range, not a point. The **swing**
is invariant: **+0.2408 interpolated, +0.2421 envelope**, and it is also what the paired
per-view test measures directly (+0.2025 in segment precision, t=+13.69, 10/10 views). So the
swing, not the carried fraction, is the load-bearing number.

### Separating SELECTIVITY from LOCALISATION -- the decomposition the spec asked for

The spec's M3 question is *"if this recovers most of TEED's lift, the win is SELECTIVITY not
localization; if not, TEED's own edge placement matters."* The carried-fraction ratio answers
it awkwardly (0.51 or 0.83 depending on estimator, because it is a ratio of two small positive
numbers). The additive decomposition is stable, and answers it directly. Three arms differ in
exactly two properties -- does the detector have a selectivity prior, and whose edge placement
is used:

| arm | selectivity | edge placement | LIFT_P (interp / env) |
|---|---|---|---|
| permissive Canny alone | **no** | Canny | **-0.2224 / -0.2053** |
| permissive Canny ∩ TEED support | **yes (TEED's)** | **Canny** | +0.0184 / +0.0369 |
| TEED alone | yes (TEED's) | TEED | **+0.0516 / +0.0615** |

| step | interp | envelope |
|---|---|---|
| **add selectivity** to a permissive detector (Canny placement throughout) | **+0.2408** | **+0.2421** |
| **switch edge placement** Canny -> TEED (selectivity already present) | **+0.0220** | **+0.0165** |
| **ratio selectivity : localisation** | **10.9 : 1** | **14.7 : 1** |

**Selectivity is worth an order of magnitude more than edge placement**, on both estimators.
TEED's own sub-pixel edge geometry is not worthless -- it is worth about +0.02 of LIFT_P, real
but small -- and essentially all of what the learned detector buys is the answer to
"is there a contour here".

### What this says

- **Calibrated continuous confidence is not what the pipeline eats.** Collapsing TEED's whole
  probability map to a single hard step at 0.5 costs **+0.0050 of lift out of a +0.0516 mean**
  -- about 10% -- and on **lego it is negative** (-0.0092), so the effect is not even
  sign-stable across scenes. The DT/pull uses the support, not the numbers.
- **Stroke continuity is not it either, and over-filtering destroys the result.** A mild
  10-25 px filter adds +0.018 to +0.020 on chair but **-0.026 on lego**; at 50 px the lift is
  gone and then some (-0.047 chair). TEED's short detections are not the noise -- deleting
  them costs recall the aggregate was using, and whether a mild filter helps at all is itself
  scene-dependent.
- **Selectivity is it.** Take a detector that recovers 90.5% of the chair miss-set in 2D and
  is nonetheless catastrophic downstream (-0.2224), intersect it with TEED's binary support,
  and it becomes a **positive-lift** arm -- a **+0.2408 swing**, carrying **half to
  four-fifths** of the full learned-detector gain (0.51 interpolated / 0.83 envelope) with
  Canny doing **100% of the edge placement**. The residual is what TEED's own edge geometry
  adds on top. The swing is the estimator-invariant number; the carried fraction is not, and
  is reported as a range.


---

## TRACK M -- the control that decides whether M3 is selectivity or just fewer pixels

The obvious alternative reading of M3 is deflationary: intersecting a permissive Canny with
anything *removes edge pixels*, and maybe any thinning would have done it. The control is to
roll TEED's support by 15 / 40 px before masking. That keeps the mask's **area, shape and
spatial statistics identical** and destroys only its **registration to the image** -- and it
removes *more* pixels than the aligned mask (9,733 / 7,884 vs 13,690 px/view), so a
density-reduction story predicts the shifted arms do at least as well.

**Seed level, chair held-out TEST:**

| arm | best LIFT_P | above frontier | f=0.35 | f=0.30 | f=0.22 |
|---|---|---|---|---|---|
| **aligned** mask (sharplow ∩ TEED) | **+0.0739** | **14/17** | +0.074 | +0.058 | +0.023 |
| shifted 15 px | **-0.1231** | **0/17** | -0.150 | -0.157 | -0.160 |
| shifted 40 px | **-0.4090** | **0/17** | -0.457 | -0.457 | -0.451 |
| *reference* TEED | +0.0665 | 6/17 | beyond | +0.067 | +0.021 |

**M1b, chair held-out TEST, segments headline stage (LIFT_P vs the canny frontier):**

| arm | f=0.40 | f=0.35 | f=0.30 | mean |
|---|---|---|---|---|
| **aligned** mask (sharplow ∩ TEED) | **+0.0348** | **+0.0246** | **+0.0174** | **+0.0256** |
| shifted 15 px | -0.0995 | -0.1066 | -0.1137 | **-0.1066** |
| shifted 40 px | -0.3229 | -0.3264 | — | **-0.3246** |
| *cannysharplow, unmasked* | *-0.2325* | — | *-0.2265* | *-0.2224* |

Rolling the mask 15 px swings LIFT_P by **-0.132** at M1b (**-0.197** at seed level) while
deleting *more* edge pixels than the aligned mask. At 40 px the masked arm is **worse than no
mask at all** (-0.325 vs -0.222): a mis-registered support deletes the true edges and keeps
the texture, which is precisely the failure mode the aligned mask avoids.


### An independent confirmation, at zero extra cost: what the mask does to the SCORE

Spearman rank correlation between the per-gaussian M1a OVERALL scores (chair, 56,884
gaussians), and Jaccard overlap of the resulting top-f=0.30 seed sets:

| score | rho vs canny | rho vs TEED | Jaccard vs canny | Jaccard vs TEED |
|---|---|---|---|---|
| cannysharplow (permissive, unmasked) | 0.537 | **0.495** | 0.372 | 0.343 |
| **cannysharplow ∩ TEED support** | 0.854 | **0.956** | 0.605 | **0.732** |
| same, rolled 15 px | 0.708 | 0.652 | 0.442 | 0.401 |
| same, rolled 40 px | 0.296 | 0.219 | 0.262 | 0.237 |
| M1a canny ∩ TEED support | **0.996** | 0.849 | **0.976** | 0.573 |

Two things fall out with no extra compute:

- **The mask transports the permissive Canny's ranking into TEED's ranking.** rho vs TEED goes
  **0.495 -> 0.956** by intersecting with a binary support and nothing else. Rolling that
  support 15/40 px sends it back to 0.652 / 0.219. The learned detector's contribution to the
  final gaussian ordering is almost entirely reproducible from its support alone.
- **It also explains why M3 on the *published* Canny does so little.** That arm is rho 0.996 /
  Jaccard 0.976 with plain canny -- the M1a blur has already restricted the edge field to
  almost exactly where TEED fires, so there is nothing left for the mask to remove. The blur
  really was a crude selectivity device, and this measures how crude: it costs recall
  (chair 0.326, lego 0.175) to buy a selectivity TEED provides without that cost.

**Density is refuted at both levels.** What the mask contributes is **registration** -- that
its support coincides with where a learned detector says a contour is. That is selectivity in
the strict sense, and it is the operative property.


---

## TRACK M replicated on lego -- and the two tracks turn out to be one measurement

The same five arms, same protocol, M1b held-out TEST, LIFT_P against lego's Canny frontier
(extended to f=1.00). Reference = TEED (mean +0.0185 over the band).

| lego arm | f=0.50 | f=0.40 | f=0.30 | f=0.22 | mean Δ vs its control | carried |
|---|---|---|---|---|---|---|
Densified lego frontier, Pareto-envelope estimator (the interpolated one gives the same
ordering; both are quoted in the Δ column).

| lego arm | f=0.50 | f=0.40 | f=0.30 | f=0.22 | mean Δ vs its control (env / interp) |
|---|---|---|---|---|---|
| **teed@0.5** (reference) | +0.0128 | +0.0175 | +0.0203 | +0.0223 | — |
| M1 teed_soft gamma=1 | +0.0077 | +0.0095 | +0.0081 | +0.0090 | **-0.0096 / -0.0092** |
| M2 CC >= 25 px | -0.0018 | -0.0059 | -0.0129 | -0.0299 | **-0.0308 / -0.0263** |
| M3 mask on **M1a** Canny | -0.0087 | -0.0102 | -0.0134 | -0.0232 | -0.0139 / +0.0022 |
| **M3 mask on permissive Canny** | +0.0190 | +0.0257 | +0.0349 | **+0.0407** | **+0.0301 / +0.0392** |
| *CTL* cannysharplow unmasked | +0.0282 | +0.0379 | +0.0477 | +0.0582 | +0.0346 / +0.0415 |

**The factor ordering is identical on both scenes.** Continuous confidence is small and
**sign-unstable** (+0.005 chair, **-0.009 lego**) -- conclusively not the carrier on either.
Connected-component filtering is mildly positive on chair (+0.018 at L=10-25, **-0.047** at
L=50) and clearly harmful on lego (-0.026 to -0.031). The selectivity mask again outperforms
TEED itself on lego (+0.030 to +0.039 vs the reference's mean +0.018) and carries 0.51-0.83 of
it on chair, and exceeds it at seed level on both.

### The swing term is the conditional law

The one number that changes sign between the scenes is what TEED's *mask alone* is worth,
measured against the same permissive Canny it is applied to:

Means taken over the f values where **both** arms were run, so the three columns add up:
chair f in {0.40, 0.30, 0.22}, lego f in {0.50, 0.40, 0.30, 0.22}.

| | Canny edge purity (tau=2, TEST) | permissive Canny alone | **+ TEED support mask** | **the mask is worth** |
|---|---|---|---|---|
| **chair** | 0.531 | **-0.2224** | **+0.0184** | **+0.2408** |
| **lego** | 0.637 | +0.0518 | +0.0392 | **-0.0125** |

(Interpolated estimator; the Pareto envelope gives **+0.2421** and **-0.0129** -- the swing is
estimator-invariant on both scenes.)

On chair the mask is worth **a quarter of a precision point of LIFT_P** -- it is the
difference between a catastrophic detector and a working one. On lego the identical operation
is worth **slightly less than nothing**: there is no texture to suppress, so the mask only
deletes a few true edges. The ratio between the two is ~19x.

**TRACK L and TRACK M are therefore not two results but one.** The property TEED supplies is a
correctly-registered contour support (TRACK M). The value of that property is set by how much
non-contour edge the scene has to suppress (TRACK L). Chair has a lot; lego has almost none.


---

# The conditional law -- lego's purity/recall placement

The spec's falsification nuance was: *if un-blurred Canny also works on lego, that does not
kill the finding -- it refines it to a conditional law, learned selectivity required iff
native purity is low.* That is exactly what happened, and the two scenes bracket the law from
opposite sides.

| | **chair** | **lego** |
|---|---|---|
| role (published scene scoping) | texture FP stress case | primary hard-surface scene |
| Canny edge purity @1.5 (published `m1b_headline`) | **0.284** | **0.663** |
| Canny purity P_GT @tau=2, this experiment, TEST | **0.531** | **0.637** |
| Canny GT-crease recall ("PGCR") @tau=2, TEST | **0.326** | **0.175** |
| GT crease px / kpx of object (published) | 90.5 | 230.7 |
| **un-blurred Canny, M1b LIFT_P** | **-0.208** | **+0.070** |
| **what un-blurring does to purity** | **-56.9%** | **+18.0%** |
| **TEED, M1b LIFT_P** | **+0.078** | **+0.035** |
| **which detector wins** | **TEED, by 0.286** | **un-blurred Canny, by 0.035** |
| **what the TEED support MASK alone is worth** | **+0.2408** | **-0.0125** |

*(The spec quotes purity as 0.28/0.66 from `m1b_headline.py`, which measures the `dt_pull`
edge set against the mesh at tau=1.5; the 0.531/0.637 row is this experiment's own
`recall_trackC_detector.py` measurement at tau=2 on the M1a Canny map. Both orderings agree
-- lego's edge field is the purer one -- and the second is the one used for cross-scene
comparison here because it is produced by one script on both scenes.)*

### The measurement the law actually rests on

`recall_trackC_detector.py`, run on **both** scenes with the **same** arms, tau and oracle.
The question: what does buying 2D recall cost you in purity?

| tau=2, held-out TEST | R_GT | dRecall | P_GT | **dP_GT vs the M1a Canny** | miss-set recovered |
|---|---|---|---|---|---|
| **chair** canny_m1a | 0.326 | — | 0.531 | — | — |
| **chair** TEED @0.5 | 0.628 | +0.302 | 0.510 | **-4.0%** | 0.515 |
| **chair** cannysharp | 0.902 | +0.576 | 0.239 | **-55.1%** | 0.862 |
| **chair** cannysharplow | 0.961 | +0.635 | 0.229 | **-56.9%** | 0.946 |
| **lego** canny_m1a | 0.175 | — | 0.637 | — | — |
| **lego** TEED @0.5 | 0.505 | +0.330 | 0.683 | **+7.3%** | 0.428 |
| **lego** cannysharp | 0.739 | +0.564 | 0.754 | **+18.4%** | 0.690 |
| **lego** cannysharplow | 0.893 | +0.718 | 0.751 | **+18.0%** | 0.874 |

(tau=1.5 gives the same picture: chair -56.9%, lego +17.4% for cannysharplow.)

**Purity cost per unit of recall bought:**

| | un-blurred Canny | TEED | ratio |
|---|---|---|---|
| **chair** | **-0.476** purity per unit recall | **-0.070** | TEED is **6.8x** more purity-efficient |
| **lego** | **+0.159** (purity *rises*) | +0.139 | no trade-off to manage |

That is the whole conditional law in one row. On chair, recall is expensive and a learned
detector is what makes it affordable. On lego, recall is *free* -- every detector that buys it
also raises purity -- so there is nothing for a selectivity device to do, and the one that
buys the most recall wins. This 2D measurement predicts the M1b sign flip exactly, and it is
computable without running M1b at all.

**Two axes, not one, and they are independent.** Lego is the scene with *higher* purity and
*lower* Canny recall: the M1a blur destroys ~83% of lego's GT creases (recall 0.175) because
lego's creases are fine, dense, high-frequency brickwork. So on lego the blur is pure loss --
removing it multiplies recall 5.1x *and raises purity* 0.637 -> 0.751, because what it lets
back in is overwhelmingly real geometry. On chair the identical operation halves purity,
because what it lets back in is fabric weave and carved-pattern texture.

**Statement of the law as the data now supports it:**

> The binding constraint for post-hoc 3D feature-line extraction from a frozen 3DGS is
> **selectivity at high recall**. A *learned* selectivity device is required only where the
> native photometric edge field is texture-contaminated. Where the native field is already
> mostly geometry, the cheapest possible fix -- deleting the blur -- supplies the missing
> recall at no purity cost and outperforms the learned detector.

The first sentence is what generalises. The second is the correction: the chair experiment's
conclusion "raw 2D recall is cheap and useless" is **scene-conditional**, and on lego raw 2D
recall is cheap and *the best thing available*.

**What did not change**: TEED is above the frontier on both scenes, at every f in the band,
zero-shot, with no per-scene tuning. It is a *sufficient* selectivity device everywhere
tested. It is a *necessary* one only on chair.


---

## Robustness -- paired per-view tests for every headline ordering

All M1b P/R in this document are means over the 10 held-out TEST views, and the chair report
already recorded a per-view precision spread of 0.05-0.12. So each headline ordering is
re-read as a **paired per-view difference**: same view, same protocol, only the edge source
differs. `scripts/teedgen_perview.py`, tau=1.5, evaluated at the `pull+prune[spec]` stage
(the stage the saved keep-mask defines exactly for every arm).

**lego, f=0.30 and f=0.40:**

| comparison | metric | mean d | sd | t | views A>B |
|---|---|---|---|---|---|
| TEED vs canny (f=0.30) | segP | **+0.0375** | 0.0120 | **+9.88** | **10/10** |
| TEED vs canny (f=0.30) | segR | **+0.1497** | 0.0575 | +8.23 | **10/10** |
| cannysharplow vs canny (f=0.30) | segP | +0.0773 | 0.0271 | +9.00 | 10/10 |
| cannysharplow vs canny (f=0.30) | segR | +0.1790 | 0.0489 | +11.59 | 10/10 |
| **cannysharplow vs TEED (f=0.30)** | segP | **+0.0397** | 0.0206 | **+6.09** | **10/10** |
| **cannysharplow vs TEED (f=0.30)** | segR | **+0.0293** | 0.0243 | +3.81 | 9/10 |
| cannysharplow vs TEED (f=0.40) | segP | +0.0268 | 0.0172 | +4.93 | 9/10 |
| cannysharplow vs TEED (f=0.40) | segR | +0.0195 | 0.0235 | +2.63 | 9/10 |

**chair, f=0.40:**

| comparison | metric | mean d | sd | t | views A>B |
|---|---|---|---|---|---|
| **m3_mask(sharplow) vs cannysharplow** | segP | **+0.2025** | 0.0468 | **+13.69** | **10/10** |
| m3_mask(sharplow) vs cannysharplow | segR | +0.1039 | 0.0428 | +7.68 | 10/10 |
| m3_mask(sharplow) vs canny | segP | -0.0024 | 0.0057 | -1.35 | 2/10 (n.s.) |
| m3_mask(sharplow) vs canny | segR | +0.0553 | 0.0275 | +6.36 | 10/10 |
| TEED vs canny | segP | +0.0065 | 0.0100 | +2.04 | 8/10 |
| TEED vs canny | segR | +0.0677 | 0.0361 | +5.94 | 10/10 |
| *M1* teed_soft vs TEED | segP | **+0.0035** | 0.0038 | +2.89 | 8/10 |
| *M1* teed_soft vs TEED | segR | **+0.0048** | 0.0053 | +2.87 | 9/10 |
| *M2* cc25 vs TEED | segP | **+0.0001** | 0.0078 | **+0.04** | **5/10 (exactly null)** |
| *M2* cc25 vs TEED | segR | +0.0242 | 0.0104 | +7.38 | 10/10 |
| **M3-CTL** shift15 vs aligned mask | segP | **-0.0975** | 0.0296 | **-10.43** | **0/10** |
| **M3-CTL** shift15 vs aligned mask | segR | **-0.0647** | 0.0265 | -7.73 | **0/10** |

Every ordering this document relies on is unanimous or near-unanimous across views:

- **TEED > Canny on lego**: 10/10 views on both axes.
- **un-blurred Canny > TEED on lego**: 10/10 on precision, 9/10 on recall -- not one view
  carrying the result.
- **the selectivity mask rescues the permissive Canny on chair**: +0.20 precision, 10/10.
- **misregistering that mask 15 px destroys it**: 0/10 views on both axes.
- **M1 and M2 are measurably tiny**: the continuous-confidence effect is statistically
  detectable (t~2.9) and worth 0.3-0.5 precision points; the CC-filter's precision effect is
  **exactly zero** (t=0.04, 5/10). Neither is a mechanism.


---

## A correction to the published chair report, surfaced by this experiment

`RECALL_RESULTS.md` records, for chair, *"4 TEED operating points reach seed recalls Canny
cannot reach at any f"* and *"2 arms beyond canny's reach"* at M1b. Those statements were read
off a Canny sweep that **stopped at f=0.50**. Sweeping chair's Canny to f=1.00 (this
experiment, for symmetry with lego) shows that it does reach higher recall than TEED --
**R 0.7908 vs TEED's 0.7560** -- but at **P 0.3606 vs TEED's 0.5726**.

So the "a recall the Canny dial cannot buy at any f" phrasing is **wrong as literally stated**,
on both scenes:

| | Canny R_max (f=1.00) | at precision | TEED R_max | at precision |
|---|---|---|---|---|
| chair | **0.7908** | **0.3606** | 0.7560 | **0.5726** |
| lego | **0.5572** | 0.6360 | 0.5225 | 0.6428 |

The finding it was reaching for is intact and is in fact **stronger** than the original
phrasing: TEED reaches those recalls **at usable precision**, where the f dial reaches them
only by collapsing. That is precisely what LIFT_P measures, and extending the frontier
*raises* chair's TEED lift (published +0.0607 against the f<=0.50 sweep -> **+0.0776
interpolated / +0.0940 envelope** against the full densified sweep). The claim should be restated as a
frontier claim (precision at matched recall), never as a recall-ceiling claim.

## Caveats, stated because they bound the claim

1. **The M1a evidence views are 25 spread views** (`final_recipe.N_VIEWS`), which include 3
   VAL and 3 TEST views. That is a property of the published recipe, not of this experiment;
   every arm on a scene consumes the identical view set, so the between-arm comparison is
   unaffected. Absolute TEST P/R inherits it, equally for all arms.
2. **TEED is frozen and off-the-shelf on both scenes.** BIPED-pretrained, never fine-tuned,
   never shown either scene. The threshold 0.5 was chosen on chair's VAL and carried to lego
   unchanged -- deliberately, since a per-scene retune would be the dataset-luck confound the
   spec warns about. `teed@0.9` was also run on lego and is worse than `teed@0.5`, so the
   chair-chosen threshold is not being flattered.
3. **Both canny frontiers were extended to f=1.00 and densified** (chair 14 points, lego 16),
   because lego's frontier is monotone-increasing and cannot be interpolated against above its
   old endpoint, and because a sparsely-sampled Pareto envelope produced sampling artefacts of
   up to 0.08 in LIFT_P. The published chair report's f<=0.50 sweep is quoted alongside
   throughout. This *raised* chair's TEED lift (+0.0607 -> +0.0776), so the densification does
   not flatter the lego result.
4. **LIFT_P is reported two ways and they do not always agree in magnitude.** The interpolated
   version is comparable with the chair report; the Pareto-envelope version ("the best
   precision the f dial reaches while *also* reaching at least this recall") stays well posed
   when the frontier is not a trade-off curve, as on lego. **Every ordering in this document is
   identical under both**, and the swing statistics are estimator-invariant to 0.002 -- but the
   *carried fraction* of the M3 arm is not (0.51 vs 0.83), which is why it is quoted as a range
   and the swing is used as the load-bearing number.
5. **Seed-level lift is directionally predictive but not quantitatively so.** On chair the
   permissive Canny was mildly negative at seed level (-0.025) and catastrophic at M1b
   (-0.205); on lego it was strongly positive at seed level (+0.14) and moderately positive at
   M1b (+0.058). Signs always agreed; magnitudes did not. Only the M1b numbers are the
   deliverable.
6. **The end-to-end gate `P@1.5 >= 0.85 AND R@1.5 >= 0.75` fails for every arm on lego**, as
   it does for the lego baseline (0.6196 / 0.2856). The best lego arm reaches 0.6942 / 0.3706.
   Nothing here closes that gate.
7. **`union` is dominated on lego.** Adding TEED's edges to the M1a Canny (+0.011) is worse
   than replacing them (+0.022), the opposite of chair's ordering at seed level. On a scene
   where the Canny map is the weak component, keeping it additively dilutes.


---

## What this changes in the arc's claim

The peak finding as previously stated was:

> The binding constraint is selectivity-at-high-recall, not 2D recall and not 3D geometry.
> Raw 2D recall is cheap and useless; converting it into rankable seeds is what the learned
> detector buys.

After this experiment, **the first sentence is confirmed and mechanistically explained; the
second is scene-conditional and must be qualified.**

**Confirmed and strengthened (TRACK M).** "Selectivity" was previously an interpretation of a
correlation -- TEED helps, blur helped, therefore selectivity. It is now a measured quantity
with a control: a bare binary support mask, carrying none of TEED's placement or confidence,
recovers half to four-fifths of its gain and swings LIFT_P by **+0.2408** (estimator-invariant,
paired per-view t=+13.7, 10/10 views); misregistering that same mask by 15 px reverses the gain
(**-0.1066**, 0/10 views) while removing *more* pixels. Continuous confidence buys ~10% on chair and is
NEGATIVE on lego; continuity buys ~0-0.02 and hurts when strong. **The pipeline consumes *where*, not *how much* and not *how long*.**

**Qualified (TRACK L).** "Raw 2D recall is cheap and useless" was measured on chair, whose
Canny edge field is 28-53% real geometry. On lego, whose field is 64-66% real geometry, raw 2D
recall is cheap and **the best thing on the table**: un-blurring beats the learned detector by
2.0-2.6x. The correct general statement is that recall must be *spendable*, and whether it is
spendable is a property of the scene's native edge purity, not of the detector.

**Practical consequence.** The published recipe should not adopt TEED unconditionally. The
decision rule is cheap to evaluate and needs no learned model:

> Un-blur the Canny and measure what happens to its edge **purity** (fraction of on-object
> edge pixels near a crease proxy). If purity **falls** (chair, -56.9%): a learned selectivity
> device is required, and un-blurring is actively harmful (-0.21). If purity **rises** (lego,
> +18.0%): **delete the blur**; that is the whole fix, and it beats the learned detector.
>
> The test costs one Canny re-run and one mask intersection. It needs no 3D pipeline, no M1b,
> and no learned model -- and on both scenes tested it predicts the M1b sign correctly.
>
> **Then check the target medium.** On lego the un-blurred Canny wins the static frontier by
> ~2x but **regresses temporal coherence 17% at the finest motion**, while TEED improves it.
> If the deliverable is an animation rather than a still, TEED remains the right choice even
> on a high-purity scene.

**Unchanged.** TEED remains above the frontier on both scenes, zero-shot, at every f in
[0.22, 0.50], with no per-scene tuning and no fitting anywhere in the pipeline. As a
*universal* drop-in it is the only arm tested that never regresses on **either** axis: the
un-blurred Canny regresses 0.21 in LIFT_P on chair and 17% in temporal coherence on lego, and
the 2DGS hybrid never cleared the frontier at all. TEED is simply not the *statically best*
arm on a hard-surface scene.

---

## Definition of done -- checklist against the spec

| spec requirement | where | status |
|---|---|---|
| TEED cached for all 100 lego views, same frozen BIPED weights, same contract, no per-scene tuning | TRACK L.1; `out/teed_edges_lego/`, `out/teed_cache_lego.json` | done -- 58,910 params, 13.7 s |
| Direct detector metric: Recall(TEED) vs Recall(Canny) vs GT creases | TRACK L.2 | done -- 0.505 vs 0.175 (tau=2, TEST) |
| TEED's recovery of the Canny miss-set | TRACK L.2 | done -- 0.428 (bar 0.35) |
| Canny purity / crease-recall for lego, as context | TRACK L.2, conditional-law section | done -- purity 0.637, recall 0.175 |
| Held-out TEST M1b with EDGE_SOURCE canny vs teed vs union; P@1.5, R@1.5, P@2.5, R@2.5, points+segments | TRACK L.4 | done -- 32 lego arms |
| f-frontier LIFT_P | TRACK L.4 | done -- two estimators, frontier extended to f=1.00 |
| arms reaching recalls Canny cannot | TRACK L.4 | **none on lego** -- canny reaches R 0.5572 at f=1.00, above every other arm's R_max. Reported, not hidden |
| temporal no-regress | TRACK L.6 | done -- TEED **no regress** (flicker win 3.4-11.6x -> **3.5-12.1x**, Frechet better at every frame count). The un-blurred Canny, run as a bonus arm, **does** regress (-17% at 240 frames) |
| viz `out/teed_lego_v{0,25}.png` | TRACK L.5 | done (+ v5, + f=0.30 variants) |
| GO / MARGINAL / NO-GO verdict | TRACK L.7 | **GO** |
| lego's purity/PGCR placement on the conditional-law question | conditional-law section | done, with the cross-scene purity-cost measurement |
| TRACK M: M1 / M2 / M3 decomposition table | TRACK M sections | done, on **both** scenes |
| which factor carries the lift | TRACK M | **M3 selectivity** -- swing **+0.2408** on chair (estimator-invariant, 10/10 views), carried fraction 0.51-0.83; M1 ~10% on chair and **negative on lego**; M2 +0.02 and destructive at L=50 |
| actual numbers, never PASS without them | throughout | done |
| do not git commit until reviewed | — | **nothing committed** |

### Artefacts

`out/teed_edges_lego/` (57 MB), `out/teed_cache_lego.json`, `out/teed_sample_lego_v{0,5,25}.png`,
`out/trackC_detector_{lego,chair}.json`, `out/trackC_seeds_lego{,_trackM}.json`,
`out/trackC_seeds_chair_trackM{,2}.json`, 43x `out/m1b_lego_tc_*.json`,
16x `out/m1b_lego_tm_*.json`, 59x `out/m1b_chair_tm_*.json`, 7 new `out/m1b_chair_tc_canny_f*.json`
(**104 new M1b runs** in total; the rest are the published chair arms re-indexed under the
`_tm_` prefix so every table reads against the same interpolant),
`out/teedgen_verdict_m1b_{lego,chair}_tc.json`, `out/teedgen_trackM_*.json`,
`out/teedgen_perview_{lego,chair}.json`, `out/teed_lego_*.png`,
`out/teedgen_frontier_chair_vs_lego.png`, `out/m1b_stroke_temporal_table_tcL_*.{json,md}`.
`out/trackC_detector_chair_ORIG.json` preserves the pre-rerun chair detector output.
