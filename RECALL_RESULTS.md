# Recall-bottleneck experiments — 2DGS-ridge redundancy gate + TEED learned-edge upgrade

Chair, NeRF-synthetic. Split frozen as `src/view_split.py` (TRAIN 80 / VAL {0,10,..,90} /
TEST {5,15,..,95}). Mesh is EVAL-ONLY throughout: `grep -rn "mesh_oracle\|trimesh" src/*.py`
finds it only in `mesh_oracle.py` itself and in docstrings; `final_recipe.py` (the method
path this work modifies) contains no mesh reference beyond `np.meshgrid`. Nothing committed.

New code (all additive; the published Canny path is bit-identical, verified):
`scripts/recall_trackA_redundancy.py`, `scripts/recall_trackB_teed.py`,
`scripts/recall_trackC_{detector,seeds,viz,table}.py`,
`scripts/recall_trackC_{m1b,m1b_ext,m1b_ext2,post,control}.sh`,
`ext/TEED/` (cloned), plus an `EDGE_SOURCE` flag and a `--score` override in
`scripts/explore/syn/final_recipe.py` / `scripts/run_m1b.py`.

---

## Executive summary

- **TRACK A: 2DGS-ridge additive seeding is DEAD.** At a matched pixel budget it recovers
  **12.8%** of the photometric miss-set (bar: 25%), it is strictly dominated by a
  *re-tuned Canny* at every non-degenerate operating point, and its unique contribution over
  that cheap Canny is <= 9.4% — and only at a mask painted over 55% of the object.
- **The recall gap is PHOTOMETRIC, not geometric — the spec's hypothesis, confirmed.** An
  unblurred permissive Canny recovers **90.5%** of the pixels the M1a Canny misses. The
  signal was in the image all along; the M1a recipe's heavy blur (sigma 2.0/2.5) destroyed it.
- **TRACK B: TEED installed with in-repo pretrained BIPED weights.** 58,910 params,
  100 views x 2 scales cached in 10.9 s.
- **TRACK C: GO.** dRecall **+0.270**, miss-set recovery **49.0%**, precision drop **15.6%**
  (pooled 20 eval views). At M1b on held-out TEST the f-frontier moves **OUTWARD**: 4/7 arms
  above it plus 2 at recalls Canny cannot reach at any f, best **LIFT_P +0.0607** — against
  the 2DGS hybrid's 14/15 *below* and +0.0004. Temporal coherence does not regress; the
  flicker win *improves* from 8.3-10.7x to **8.5-13.1x**.
- **The control that matters most: un-blurring the Canny DOES NOT WORK.** Although a
  permissive Canny recovers 90.5% of the miss-set in 2D, through the pipeline it lands
  **0/3 arms above the frontier at LIFT_P -0.16 to -0.23**. Raw 2D recall is cheap and
  useless; converting it into rankable seeds is what the learned detector actually buys.

---

## TRACK A — 2DGS-ridge redundancy gate

Pure 2D pixel-mask intersection on eval views. `S_photo_miss` = visible GT crease pixels
(mesh dihedral >= 30 deg, depth-culled) with no M1a Canny edge within tau=2 px.

The photometric recall cap, measured at pixel level:

| split | GT crease px | Canny photo-recall | miss-set |
|---|---|---|---|
| VAL (10 views) | 93,099 | **0.385** | 57,292 |
| TEST (10 views) | 120,655 | **0.326** | 81,284 |

VAL, tau=2, all GT (`cover_fg` = fraction of foreground the dilated mask covers;
`lift` = recall_miss / cover, i.e. how much better than painting at random;
`prec_GT` = fraction of the mask's pixels within tau of a GT crease):

| arm | cover_fg | Rec_miss | lift | prec_GT | uniq vs cheap-Canny | px/view |
|---|---|---|---|---|---|---|
| canny_m1a (defines the miss-set) | 0.024 | 0.000 | — | 0.554 | — | 4,141 |
| **2dgs_q99 — MATCHED BUDGET** | 0.034 | **0.128** | 3.74 | 0.218 | 0.005 | 6,400 |
| 2dgs_q95 | 0.100 | 0.648 | 6.46 | 0.281 | 0.031 | 32,000 |
| *canny_sharp* (cheap, LESS cover) | 0.103 | **0.786** | 7.62 | 0.313 | — | 19,708 |
| 2dgs_q90 | 0.158 | 0.884 | 5.61 | 0.260 | 0.062 | 64,000 |
| **canny_sharp_low** (cheap, 26% LESS cover) | **0.125** | **0.905** | 7.25 | 0.284 | — | 24,645 |
| 2dgs_q50 (degenerate) | 0.549 | 0.988 | 1.80 | 0.073 | 0.094 | 319,985 |
| 2dgs depth-ridge q90 | 0.194 | 0.228 | **1.18** | 0.059 | 0.013 | 64,000 |

### VERDICT: KILL 2DGS-ridge additive seeding, permanently

Three independent reasons, all replicated on held-out TEST:

1. **Matched budget: 12.8% < 25%.** The gate fails by half.
2. **Strictly dominated by a re-tuned Canny.** At *less* foreground cover, a cheap unblurred
   Canny recovers *more* of the miss-set (0.905 @ 0.125 vs 2DGS 0.884 @ 0.158; 0.786 @ 0.103
   vs 0.648 @ 0.100), at equal-or-better GT precision.
3. **Unique recovery over that cheap Canny <= 0.094**, and that figure occurs only at q50 —
   a mask covering 55% of the object at lift 1.80x, i.e. barely above chance, prec_GT 0.073.
   At any usable density unique recovery is 0.5–6%.

The 0.98–0.99 `Rec_miss` figures are the degenerate regime the chance/matched-density
controls exist to dismiss. The 2DGS **depth** ridge is separately dead at lift 1.1–1.2x
(chance). No 3D seeder code was written, and none should be.

### The transferable finding

`Recall_miss(canny_sharp_low) = 0.905`. The miss-set is not geometrically invisible — it is
**photometrically present** and not picked up by the M1a recipe's blurred Canny. That is what
redirects the effort to a stronger 2D detector, and it is also why the TEED result below must
be benchmarked against a *re-tuned Canny*, not only against the published blurred one.

That benchmark is run in the last section, and it inverts the naive reading of this number:
recovering the miss-set in 2D turns out to be *necessary but nowhere near sufficient*.

---

## TRACK B — TEED install

`github.com/xavysp/TEED` @ `40fa4b1`. Pretrained BIPED checkpoints ship **inside the repo**
(`checkpoints/BIPED/5/5_model.pth`, 249 KB — main.py's own default), so no external weight
download and no DexiNed/PiDiNet fallback was needed. **58,910 parameters.**

Contract read off the repo, not guessed (`dataset.py:401-435`, `main.py:127-168`,
`utils/img_processing.py:39-151`): input BGR uint8 -> float32 minus
`mean_bgr = [104.007, 116.669, 122.679]`, **no /255**; `TED.forward` returns
`[out_1, out_2, out_3, block_cat]` and the fused map is the **last**; output `sigmoid`.
The repo then min-max stretches per image — we cache the **raw sigmoid** instead, because a
per-image contrast stretch is not comparable across views and the M1a aggregate is multi-view.
RGBA composited over **white** (what `photo_edge_map` and the 2DGS `white_background=True`
model both use). Two scales cached (native 800, and 0.64 -> 512 = train resolution).

100 views x 2 scales in **10.9 s** (109 ms/view), 34.4 MB -> `out/teed_edges_chair/`.
Deps added to `vfsdgs`: `kornia`, `scikit-learn`.

---

## TRACK C — the detector go/no-go

### Two things that had to be fixed before any number meant anything

1. **Stroke width was a confound.** A raw thresholded TEED map is 7–10x Canny's pixel count;
   after canonical edge-NMS (local max along the gradient, which Canny does by construction
   and TEED does not) it is 1.5–1.8x. Every px/view and precision figure inherited that. All
   numbers below are NMS-thinned.
2. **The precision guard is split-noisy.** It fires on VAL (27.5%) and not on TEST (4.0%) for
   the same arm; per-view sd is 0.05–0.12, so a 25% bar read off 10 views sits inside the
   between-split spread. Reported pooled over all 20 eval views.

### The spec's rule, pooled over VAL+TEST (20 views), tau=2

| criterion | bar | replacement `teed@0.5` | union `canny ∪ teed@0.5` |
|---|---|---|---|
| dRecall | >= +0.18 | **+0.270** PASS | **+0.318** PASS |
| Canny miss-set recovered | >= 35% | **49.0%** PASS | **49.0%** PASS |
| seed count | < 2.5x | **1.00x** PASS | **1.00x** PASS |
| dRecall NO-GO | < +0.10 | not tripped | not tripped |
| GT-edge precision drop | > 25% NO-GO | **15.6%** ok | **12.3%** ok |

R_GT 0.352 -> **0.621** (replacement) / **0.670** (union).

The seed-count guard is automatically satisfied and carries no information: the M1a
keep-fraction fixes the count at `round(f*M)` whatever detector fed the DT. The informative
version (edge pixels) is 1.65x / 2.26x, under 2.5x anyway.

### Why the precision drop is not "texture hallucination dominates"

Every non-GT-crease edge pixel was triaged with the same mesh oracle:

| arm | FP: occluding contour | FP: sub-30deg fold | FP: **hallucination** | P_line |
|---|---|---|---|---|
| canny_m1a | 0.474 | 0.169 | **0.358** | 0.841 |
| nms_native_0.5 | 0.448 | 0.109 | **0.444** | 0.735 |
| nms_native_0.9 | 0.504 | 0.102 | **0.393** | 0.766 |

TEED's hallucination *fraction* is barely above Canny's, and precision against **all**
legitimate feature lines (crease | occluding contour | shallow fold) falls only
0.841 -> 0.735. Most of the "lost precision" is TEED correctly drawing occluding contours
and sub-30-deg folds that a 30-deg-dihedral oracle refuses to credit.

### Seed level — the measurement the pipeline actually consumes

Only the photometric edge source changed. Self-checks: the recomputed Canny DP reproduces
the cached evidence **exactly** (`max|d| = 0.000000`), and the Canny arm reproduces
`HYBRID_RESULTS.md` to 4 dp (f=0.30 -> P 0.6555 / R 0.7669 on VAL).

| held-out TEST | best LIFT_P | best LIFT_R | max seed recall | above frontier |
|---|---|---|---|---|
| teed_native_0.5 | +0.0665 | +0.0937 | 0.9334 | 6/17 |
| teed_native_0.9 | +0.0578 | +0.0952 | 0.9342 | 6/17 |
| **union_native_0.5** | **+0.0807** | +0.0880 | 0.9319 | 7/17 |
| union_native_0.9 | +0.0795 | +0.0918 | 0.9322 | 7/17 |
| *canny (baseline)* | — | — | *0.8803* | — |
| *2DGS hybrid, same harness* | *+0.0262* | — | *<= canny by construction* | *1/26* |

Four TEED operating points (f = 0.50/0.45/0.40/0.35) reach seed recalls **Canny cannot
reach at any f**. That is the qualitative break: a veto can only slide along or below the
frontier — it cannot move the ceiling. TEED moves it by **+0.053**.

---

## TRACK C — full M1b, held-out TEST

Every arm runs the identical `run_m1b.py` path with the identical published-baseline flags;
only `--score` differs. **Reproduction control is exact**: canny f=0.30 returns
17065/16039/15091 seeds and seg P@1.5 0.6573 / R@1.5 0.5959.

### Segments, stage `pull+prune[tuned+len]` (the published headline stage)

| arm | f | n_seed | n_keep | seg P@1.5 | seg R@1.5 | seg P@2.5 | seg R@2.5 | canny P@same R | LIFT_P | LIFT_R |
|---|---|---|---|---|---|---|---|---|---|---|
| **canny BASELINE** | 0.30 | 17065 | 15091 | 0.6573 | 0.5959 | 0.7777 | 0.6719 | — | — | — |
| canny | 0.50 | 28442 | 22633 | 0.5522 | 0.7224 | 0.6568 | 0.7959 | — | — | — |
| canny | 0.45 | 25598 | 20888 | 0.5768 | 0.7008 | 0.6855 | 0.7743 | — | — | — |
| canny | 0.40 | 22754 | 19066 | 0.6045 | 0.6714 | 0.7163 | 0.7445 | — | — | — |
| canny | 0.35 | 19909 | 17173 | 0.6335 | 0.6396 | 0.7498 | 0.7128 | — | — | — |
| canny | 0.22 | 12514 | 11548 | 0.6877 | 0.5334 | 0.8084 | 0.6071 | — | — | — |
| canny | 0.15 | 8533 | 8094 | 0.7057 | 0.4678 | 0.8286 | 0.5399 | — | — | — |
| teed05 | 0.50 | 28442 | 22362 | 0.5726 | **0.7560** | 0.6801 | **0.8358** | *beyond canny's reach* | — | +0.0515 |
| teed05 | 0.45 | 25598 | 20670 | 0.5925 | **0.7348** | 0.7040 | 0.8204 | *beyond canny's reach* | — | +0.0507 |
| **teed05** | **0.40** | 22754 | **18838** | **0.6148** | **0.7207** | 0.7294 | **0.8072** | 0.5541 | **+0.0607** | **+0.0607** |
| teed05 | 0.35 | 19909 | 16865 | 0.6297 | 0.6982 | 0.7462 | 0.7864 | 0.5792 | +0.0504 | +0.0544 |
| teed05 | 0.30 | 17065 | 14770 | 0.6417 | 0.6759 | 0.7578 | 0.7665 | 0.6001 | +0.0416 | +0.0515 |
| teed05 | 0.22 | 12514 | 11140 | 0.6595 | 0.6230 | 0.7767 | 0.7206 | 0.6425 | +0.0170 | +0.0317 |
| teed05 | 0.15 | 8533 | 7753 | 0.6701 | 0.5535 | 0.7896 | 0.6498 | 0.6779 | −0.0078 | −0.0160 |
| teed09 | 0.30 | 17065 | 14452 | 0.6425 | 0.6759 | 0.7611 | 0.7678 | 0.6002 | +0.0424 | +0.0530 |
| teed09 | 0.22 | 12514 | 10899 | 0.6573 | 0.6299 | 0.7754 | 0.7278 | 0.6388 | +0.0186 | +0.0341 |
| union05 | 0.30 | 17065 | 14945 | 0.6424 | 0.6704 | 0.7599 | 0.7636 | 0.6053 | +0.0371 | +0.0471 |
| union05 | 0.22 | 12514 | 11312 | 0.6621 | 0.6161 | 0.7827 | 0.7139 | 0.6463 | +0.0158 | +0.0301 |
| *CONTROL* cannysharp | 0.40 | 22754 | 20906 | 0.4525 | 0.6516 | 0.5389 | 0.7379 | 0.6225 | **−0.1700** | — |
| *CONTROL* cannysharp | 0.30 | 17065 | 16123 | 0.4843 | 0.5926 | 0.5741 | 0.6713 | 0.6589 | **−0.1746** | — |
| *CONTROL* cannysharp | 0.22 | 12514 | 12029 | 0.5245 | 0.5453 | 0.6177 | 0.6162 | 0.6819 | **−0.1575** | — |
| *CONTROL* cannysharplow | 0.40 | 22754 | 20076 | 0.4127 | 0.6180 | 0.4907 | 0.7007 | 0.6452 | **−0.2325** | — |
| *CONTROL* cannysharplow | 0.30 | 17065 | 15408 | 0.4423 | 0.5723 | 0.5228 | 0.6461 | 0.6688 | **−0.2265** | — |
| *CONTROL* cannysharplow | 0.22 | 12514 | 11520 | 0.4772 | 0.5382 | 0.5624 | 0.6125 | 0.6853 | **−0.2081** | — |

### FRONTIER SHIFT

| arm | above frontier | beyond canny's max recall | best LIFT_P | best LIFT_R | R_max | verdict |
|---|---|---|---|---|---|---|
| **teed05** | 4/7 | **2** | **+0.0607** | +0.0607 | **0.7560** | **OUTWARD** |
| teed09 | 2/2 | 0 | +0.0424 | +0.0530 | 0.6759 | above, range not extended |
| union05 | 2/2 | 0 | +0.0371 | +0.0471 | 0.6704 | above, range not extended |
| *cannysharp* | **0/3** | 0 | **−0.1575** | — | 0.6516 | **far below** |
| *cannysharplow* | **0/3** | 0 | **−0.2081** | — | 0.6180 | **far below** |
| *2DGS hybrid (HYBRID_RESULTS)* | *1/26* | *0* | *+0.0004* | — | *<= canny* | *below* |

canny frontier spans R [0.4678, 0.7224], P [0.5522, 0.7057]. teed05 reaches R 0.7560 —
**a recall the Canny dial cannot buy at any f.**

The statement that needs no interpolation is matched-f:

| | n_seed | n_keep | seg P@1.5 | seg R@1.5 |
|---|---|---|---|---|
| **teed05 f=0.40** | 22754 | **18838** | **0.6148** | **0.7207** |
| canny f=0.40 | 22754 | 19066 | 0.6045 | 0.6714 |
| **teed05 f=0.50** | 28442 | **22362** | **0.5726** | **0.7560** |
| canny f=0.50 | 28442 | 22633 | 0.5522 | 0.7224 |

Identical seed count, TEED keeps **fewer** linelets after pruning, and wins on **both**
axes. Not a draw-more artifact.

### Points, same stage

| arm | f | P@1.5 | R@1.5 | P@2.5 | R@2.5 | canny P@same R | LIFT_P |
|---|---|---|---|---|---|---|---|
| canny | 0.40 | 0.6948 | 0.5782 | 0.8080 | 0.6889 | — | — |
| canny | 0.30 | 0.7353 | 0.5033 | 0.8519 | 0.6106 | — | — |
| teed05 | 0.40 | 0.6942 | 0.6197 | 0.8091 | 0.7477 | 0.6538 | **+0.0404** |
| teed05 | 0.35 | 0.7047 | 0.5949 | 0.8204 | 0.7249 | 0.6804 | +0.0243 |
| teed05 | 0.30 | 0.7127 | 0.5690 | 0.8276 | 0.7014 | 0.7019 | +0.0108 |
| teed05 | 0.22 | 0.7197 | 0.5090 | 0.8355 | 0.6466 | 0.7332 | −0.0135 |

Same shape: positive above f=0.30, negative below. The learned detector buys recall in the
high-coverage regime and costs precision in the high-purity regime.

### The end-to-end gate

`P@1.5 >= 0.85 AND R@1.5 >= 0.75` **FAILS** for every arm, as it does for the baseline
(0.6573 / 0.5959). The best TEED arm reaches 0.6148 / 0.7207.

### Caveats, stated because they bound the claim

1. **The M1a evidence views are 25 spread views** (`final_recipe.N_VIEWS`), which include 3
   VAL and 3 TEST views. That is a property of the published recipe, not of this experiment;
   the Canny and TEED arms consume the identical view set, so the Canny-vs-TEED comparison
   is unaffected. The absolute TEST P/R inherits it, for both arms equally.
2. **TEED is frozen and off-the-shelf** — BIPED-pretrained, never fine-tuned, never shown
   this scene or this dataset. There is no fitting to the chair anywhere in the pipeline, so
   the gain is a clean zero-shot transfer result rather than a tuned one.
3. **The TEED threshold was chosen on VAL** (and the arm is flat across 0.5–0.9, so the
   choice barely matters: `teed09` and `teed05` differ by <0.001 in seg P@1.5 at f=0.30).
4. **The gain is regime-dependent and reverses.** Above f≈0.30 TEED buys recall the f dial
   cannot; below f≈0.22 it is *worse* than Canny (LIFT_P −0.008 at f=0.15). If the target
   operating point is high-purity/low-recall, this change is not indicated.

### Viz

`out/teed_chair_v{5,25}.png` = {RGB | Canny linelets | TEED linelets | recovery map}.
Held-out TEST views. GT-crease coverage by the drawn linelets:

| view | canny n | canny GTcov | teed n | teed GTcov | delta |
|---|---|---|---|---|---|
| TEST v5 | 12,440 | 0.7374 | **12,240** | **0.8551** | **+0.1177** |
| TEST v25 | 11,330 | 0.7688 | **11,020** | **0.8482** | **+0.0794** |

Fewer drawn linelets, higher GT coverage, on both views. The green (TEED-only) pixels
cluster on the carved back-frame contour, the seat piping and the leg/arm frame edges —
subtle creases with a faint photometric signature, exactly the predicted population.

---

## Temporal no-regress

`scripts/m1b_stroke_temporal.py`, chair, held-out TEST trajectory 5->15, look-at-corrected
orbit. Both arms at f=0.30, identical everything except the edge source. `P_pop` = fraction
of strokes with no forward-warped match plus the split/merge rate (lower = less flicker);
BASELINE = naive image-space Canny re-traced every frame, and it is identical for both arms
(0.788/0.770/0.755/0.755), which is the cross-check that the harness is unchanged.

| frames | CANNY P_pop | **TEED P_pop** | BASE P_pop | canny ratio | **TEED ratio** | canny Frechet | teed Frechet |
|---|---|---|---|---|---|---|---|
| 30 | 0.096 | **0.093** | 0.788 | 8.25x | **8.50x** | 0.322 | 0.347 |
| 60 | 0.079 | **0.068** | 0.770 | 9.74x | **11.35x** | 0.160 | 0.174 |
| 120 | 0.072 | **0.059** | 0.755 | 10.43x | **12.85x** | 0.080 | 0.087 |
| 240 | 0.071 | **0.058** | 0.755 | 10.71x | **13.12x** | 0.040 | 0.043 |

**No regress — the flicker win improves**, from 8.3-10.7x to **8.5-13.1x**. Frechet median
is marginally worse (+0.003 to +0.025 px), which is negligible against a 1.5 px tolerance.
Strokes/frame 723-727 (TEED) vs 754-759 (Canny): again fewer strokes, better numbers.

---

## THE CONTROL — is a *learned* detector needed, or would un-blurring the Canny do?

This is the control the entire TEED claim depends on, and it is the same discipline TRACK A
applied to 2DGS. TRACK A established that the M1a Canny's miss-set is **photometrically
present**: a permissive unblurred Canny recovers 90.5% of it. So the obvious cheap fix is to
stop blurring. Three re-tuned Canny configurations were pushed through the IDENTICAL pipeline:

| arm | cfgs | 2D miss-set recovery (TRACK A) | seed f-frontier, TEST | M1b LIFT_P, TEST |
|---|---|---|---|---|
| canny (M1a, published) | (2.0,100,200)+(2.5,75,150) | — (defines it) | — | — |
| cannysharp | (0,50,150) | 0.786 | **1/17 above**, best +0.0023 | **−0.158 to −0.175** |
| cannysharplow | (0,20,60) | **0.905** | **0/17 above**, best −0.0249 | **−0.208 to −0.233** |
| cannyunblur | (0,100,200)+(0,75,150) | — | 1/17 above, best +0.0110 | not run (dominated) |
| **teed_native_0.5** | learned | 0.786 | **6/17 above**, best **+0.0665** | **+0.0416 to +0.0607** |

Seed P/R at f=0.30 on held-out TEST:

| arm | seed P | seed R |
|---|---|---|
| canny (M1a) | **0.796** | 0.731 |
| cannyunblur | 0.645 | 0.724 |
| cannysharp | 0.628 | 0.721 |
| cannysharplow | 0.533 | 0.700 |
| **teed_native_0.5** | 0.770 | **0.860** |

**Un-blurring does not just fail to help — it is catastrophic**, costing 15-23 points of
segment precision at matched recall and *lowering* the maximum reachable recall
(0.6516 / 0.6180 vs canny's 0.7224). Every re-tuned Canny arm lands below the frontier the
published blurred Canny already reaches.

### What this means

The two facts have to be held together:

1. The missing creases **are** in the image — a threshold sweep reaches 90.5% of them (TRACK A).
2. Reaching them with a threshold sweep is **worthless downstream** — the recovered pixels
   arrive buried in so much non-crease edge that the multi-view DT aggregate can no longer
   rank crease gaussians above the rest, and the whole score degrades.

So the binding constraint was never *recall of the 2D detector* and never *3D geometry*. It
was **selectivity at high recall** — the ability to fire on faint true contours without also
firing on everything else faint. That is exactly the quantity a learned edge detector has and
a threshold does not, and it is why TEED is the only arm tested that converts the available
2D recall into better feature lines.

The M1a blur, incidentally, is now explained rather than blamed: it is a crude selectivity
device (it suppresses fine texture along with fine creases). TEED replaces it with a better
one instead of simply removing it.

---

## Where this leaves the two routes

- **2DGS-ridge additive seeding: closed.** Buried on three independent grounds, on both
  splits. No 3D geometric seeder should be built on this evidence.
- **TEED edge source: adopt, at f >= 0.30.** It is the first change in this arc to move the
  M1b f-frontier OUTWARD rather than slide along it, it survives held-out TEST, it improves
  temporal coherence, and it beats the cheapest alternative by 0.2 of segment precision.
  Below f ~= 0.22 it is worse than Canny and should not be used.
- **Still open: the `P@1.5>=0.85 AND R@1.5>=0.75` gate fails** (best 0.6148 / 0.7207). The
  recall side is now within reach; precision at that recall is the remaining gap.
