# Matched-Precision + Matched-Density Coherence Pareto
# **FROZEN-GATE VERDICT: FAIL — the ≥3× bar is missed at one shared operating point (chair, worst 2.42×)**

Per the frozen three-way gate in `tier1/pareto_spec.md`: *"if density-matching collapses the
gap (advantage <3× at any shared point), that COLLAPSE becomes the headline instead."* It
does, at exactly one kind of point, so it is the headline. The mechanism analysis below shows
the collapse lives in the **statistic**, not in the coherence — the floor-free pooled
statistics at the same failing point read **12.8× (pixel pop-rate)** and **12.2× (pixel
flicker)** — but the gate was frozen before the numbers and its letter stands. The paper
figure survives; the "≥3× everywhere on pooled-mean E_warp" *sentence* does not.

## The measurement (all three axes on the SAME line sets, SAME image domain)

- **Scenes/frames**: chair + lego, the published 240-frame look-at-corrected T1 orbit between
  TEST cams 5→15 (target = median de-floatered gaussian). Precision + density on the 10
  held-out TEST views; coherence on the trajectory. Mesh EVAL-only (precision uses the
  `cache/oracle_*_a30` GT-crease DTs); the line-generation path is mesh-free.
- **Methods (all interior-restricted: α>0.5 eroded 2 px — the banked `--fg_only` control,
  applied to EVERY method so the silhouette warp-drop confound is dead at source; warp-drop
  ≤0.1 % everywhere)**:
  - OURS: the banked f-sweep linelet clouds (`linelets_chair_tc_teed05_f*`,
    `linelets_lego_tc_teed_native_0.5_f*`), chained with the published
    `m1b_stroke_temporal` defaults, projected per frame with the published occlusion test,
    rastered 1 px. f ∈ {0.15…0.50} chair / {0.15…0.70} lego.
  - CANNY: per-frame `cv2.Canny` on the same albedo-gray render, (lo,hi) ∈
    {25/75, 50/150 (the banked baseline), 75/200, 100/250, 150/300}.
  - PIDINET: frozen zero-shot, banked contract (`cmepi_cache_edges.PiDiNetDetector`,
    gray replicated 3-ch), per-frame inference, `nms_thin` ≥ thr ∈ {0.1…0.9}.
- **Pooled E_warp (the spec's normalization, stated explicitly)**: every ON pixel of frame
  t's line mask with finite depth is forward-warped through the rendered depth + the two
  camera poses (exact rigid flow, identical operator for all methods); the distance
  transform of frame t+1's line mask is read at the warped pixel; ALL such distances over
  all 239 transitions are pooled. **No per-line averaging, no matching step** — a vanished
  line's pixels land far from any target pixel, so popping is inside the metric (unlike the
  banked matched-stroke E_warp, which excludes unmatched strokes). Reported: pooled mean
  (cap 20 px), median, p75–p99, pop-rates P(d > k px), and the banked-style 1 px-tolerant
  pixel flicker (XOR/union). Density = mean line px per trajectory frame.

## The frontier (out/pareto_{chair,lego}.png; full tables in out/pareto_{scene}.json)

Chair (excerpt):

| point | P@1.5 | px/frame | E_pool_mean | pop>2px | flicker |
|---|---|---|---|---|---|
| OURS f=0.15 | **0.662** | 4,947 | **0.296** | **0.0049** | **0.009** |
| OURS f=0.50 | 0.558 | 11,311 | 0.277 | 0.0047 | 0.009 |
| CANNY 150/300 | 0.652 | 3,285 | 0.716 | 0.0629 | 0.115 |
| CANNY 100/250 | 0.532 | 5,973 | 0.934 | 0.1039 | 0.177 |
| PIDINET 0.4 | 0.518 | 946 | 1.035 | 0.0981 | 0.160 |

Lego (excerpt):

| point | P@1.5 | px/frame | E_pool_mean | pop>2px | flicker |
|---|---|---|---|---|---|
| OURS f=0.15 | 0.661 | 8,377 | 0.350 | 0.0103 | 0.021 |
| OURS f=0.70 | 0.644 | 24,158 | 0.310 | 0.0075 | 0.016 |
| CANNY 150/300 | **0.727** | 7,603 | 0.685 | 0.0645 | 0.117 |
| PIDINET 0.4 | 0.661 | 2,117 | 1.178 | 0.1227 | 0.203 |

## The gate, evaluated exactly as frozen

"Shared operating point" = a baseline point that at least one OURS point matches-or-beats on
BOTH control axes (P@1.5 AND px/frame). Advantage = the MINIMUM E-ratio over all dominating
OURS points, on the most conservative of {pooled-mean, pooled-median, flicker}.

| scene | shared points | worst conservative advantage | at | verdict |
|---|---|---|---|---|
| chair | 10 of 12 | **2.42×** | CANNY 150/300 (P 0.652, 3.3k px) | **FAIL** |
| lego | 4 of 12 | **3.36×** | PIDINET 0.4 | PASS |
| **overall** | | | | **FAIL** |

Chair also has CANNY 75/200 at 2.99× — a hair under the bar; every PiDiNet point passes
(3.45–6.60× chair, 3.36–3.69× lego). Flicker advantage never drops below **9.8×** at any
shared point on either scene.

## Why the failing statistic collapses — mechanism, measured not asserted

OURS' pooled-mean E_warp is **flat at 0.277–0.297 (chair) / 0.310–0.350 (lego) across every
f and both scenes, with p95 = 1.00 px everywhere**. Our lines are static 3D polylines — their
true inter-frame drift on a rigid scene is zero — so this value is the **shared
rasterization/warp quantization floor** of the operator (integer-pixel warp of an
integer-raster line), not residual instability. At 240-frame (sub-pixel) motion the ratio
`(floor + baseline_instability) / (floor + ~0)` is compressed toward 1 by the floor. The
floor-free pooled statistics at the SAME failing point:

| CANNY 150/300 (chair) vs OURS f=0.15 | ratio |
|---|---|
| pooled-mean E_warp (the gate's statistic) | **2.42×** ← FAIL |
| pop-rate P(d>2px), pooled | **12.8×** |
| pop-rate P(d>3px), pooled | **15.4×** |
| pixel flicker (1px-tol) | **12.2×** |

The collapse is real for the frozen statistic and is reported as the verdict. It is a
property of a mean taken over a floor-dominated distribution, not of the temporal behaviour:
94 % of Canny-150/300's warped pixels also land within 2 px — the coherence difference lives
in the tail (6.3 % vs 0.5 % of pixels popping >2 px), which a floored mean under-weights by
construction.

## Two more honest findings the figure forces into the open

1. **On lego, per-frame Canny on the albedo render is MORE PRECISE than our lines at every
   density** (P@1.5 up to 0.727 vs our ceiling ~0.66) — 5 of 5 Canny points are unshared
   because ours never dominates their precision. Lego's crease-dense geometry makes strong
   image edges mostly-true creases. Our advantage on lego is coherence-only, and the
   coverage/precision story of Phases 0–1d applies with full force.
2. **Ours' coherence is threshold-invariant** (pop>2px 0.0042–0.0049 across the whole
   f-sweep): the acceptance threshold moves precision and density but not stability — the
   stability comes from the object-space parameterization itself. This is the cleanest form
   of the "orthogonal to the supervision ceiling" claim, and it is exactly what the
   per-frame detectors cannot do (their coherence *degrades* as thresholds sparsify them:
   PiDiNet 0.9 pops 3× more than PiDiNet 0.1 on chair).

## What goes in the paper

- The **figure** (both scenes) with flicker and pop-rate panels: the object-space set sits
  an order of magnitude below every per-frame detector at matched precision and density —
  that visual claim survives every control.
- The **sentence** must be the measured one: "at matched precision and density the pooled
  pixel-flicker/pop advantage is ≥9.8× at every shared operating point; the pooled-MEAN
  advantage is floor-compressed at sub-pixel motion and drops to 2.4× at the sparsest
  high-precision Canny point" — not "≥3× on every statistic," which the frozen gate has
  falsified.
- Lego's precision inversion (finding 1) is stated, not hidden.

## Caveats

- The albedo-gray render is flat-lit (SH degree-0); detector operating points on it differ
  from photograph-domain numbers elsewhere in the repo (documented domain shift; all
  comparisons here are within-domain and self-consistent).
- One trajectory (T1 orbit, the published one). Track P showed the ours-vs-per-frame gap
  narrows ~3× on the adversarial spline; the floor-compression above would bite harder
  there for the mean statistic and less for pop/flicker (more motion → floor matters less).
- The banked 7–13× (P_pop, stroke-level) and 3.38–21.62× (matched-stroke E_warp) claims are
  different statistics on different baselines (Canny / TEED); this figure neither reproduces
  nor replaces them — it adds the density-and-precision-controlled pixel-pooled view.
- Nothing committed (per instruction; gate now evaluated — commit is the user's call).

Artifacts: `scripts/pareto_coherence.py`, `scripts/pareto_verdict.py`,
`out/pareto_{chair,lego}.{json,png}`, `out/pareto_verdict.json`, `logs/pareto_run2.log`.
