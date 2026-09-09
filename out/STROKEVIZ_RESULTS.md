# STROKE-VIZ — visual-first stroke rendering on cadpartA (plan, frozen before execution)

**DONE.** Both carriers rendered and timed. **On the judge we agreed — `cut` plus the visible
frames — the STEP3 carrier wins by 664x** (cut 0.0002 against 0.1328). The DexiNed carrier has
far better coverage but its 4,007 over-segmented chains split and merge constantly.
**My prior was half wrong**: I predicted DexiNed would give the cleaner still. It gives the
more COMPLETE still, but a visibly hairier one.

## Framing
The deliverable is a LINE DRAWING for NPR, so the judge is the rendered frames and their
frame-to-frame steadiness. **P/R against the GT mesh is REPORTED, never gated** — kept for the
same reason P_pop is kept: so a pretty still cannot fool us about correctness, exactly as
P_pop stops a pretty still fooling us about stability.

**MESH EVAL-ONLY**: faint GT crease overlay, plus reported-not-gated P/R. Nothing else.

## Two carriers, one identical downstream path
- **Carrier 1, DexiNed (headline)**: the banked Phase-1b triangulated cloud
  `dexprimary_p1b_cloud_cadpartA_ref40.npz` at `surface_keep`, banked P 0.7302 / R 0.8431.
  It has positions only, so PCA tangents over a kNN ball plus a pixel-anchored length and a
  confidence are added to feed the chainer. **Never chained or timed before; its temporal
  behaviour is unknown.**
- **Carrier 2, STEP3 geometric ranker**: `linelets_cadpartA_step3pool.npz` at its spec-prune
  `keep`, the zero-knob point P 0.8139 / R 0.4206, banked temporal 10.50x.

Both go through the **identical frozen `strokes.chain_linelets_3d`** (3D NMS, tangent-consistent
linking, collinear merge with gap). No new clustering code.

## Rendering rules, as converged
- **Piecewise-linear polylines with explicit corner preservation. NO spline smoothing** —
  cadpart's creases are straight segments meeting at sharp vertices and rounding them is the
  first thing a viewer reads as wrong.
- **Width constant in SCREEN space**, pixel-anchored `l = L_px * z / f`.
- **Taper only at TRUE endpoints** (corner or silhouette), never at a chain break, because a
  dash end moves when chaining flips between frames.
- **Bridge gaps FIRST, hidden-line removal SECOND** — never bridge an occluded span into a
  line drawn through the object.

## Deliverable and judge
Per carrier: a strip of **consecutive** orbit frames (adjacent, not spaced, because flicker is
frame-to-frame), a **difference frame** marking strokes that appear or vanish, and one clean
still. Baseline strip = the per-frame Canny image-space drawing from the temporal harness.

**Judge on `cut` and on the visible frames.** On clean solids nearly all of P_pop is
`unmatched`, which is largely correct hidden-line removal: lines *should* vanish behind the
object. Chasing P_pop to zero would mean disabling correct occlusion. `cut`, the split/merge
term, is what actually looks like flicker. Both are reported.

## Author's prior, recorded so it can be wrong
The DexiNed cloud gives the cleaner still and the worse `cut`, because 220k unorganised points
will over-segment into many short chains; the STEP3 carrier gives the steadier video.

---

# RESULTS

## 1. Temporal, decomposed — the number the judge rests on

240-frame orbit, identical warp and per-frame Canny baseline, both carriers through the
identical frozen chainer.

| carrier | strokes | P_pop | = unmatched | + **cut** | baseline P_pop | ratio | Frechet |
|---|---|---|---|---|---|---|---|
| DexiNed cloud | 4,007 | 0.1693 | 0.0365 | **0.1328** | 0.8098 | 4.78x | 36.7x |
| **STEP3 ranker** | 42 | 0.0771 | 0.0770 | **0.0002** | 0.8097 | **10.50x** | 37.2x |

**This is why the decomposition mattered.** Total P_pop says DexiNed is 2.2x worse. The `cut`
term says it is **664x** worse. For the STEP3 carrier 99.7 percent of popping is `unmatched`,
which is correct hidden-line removal: lines *should* vanish behind the object. For the DexiNed
carrier 78 percent of popping is `cut`, genuine topological churn as 4,007 short chains split
and merge between frames. Judging on total P_pop alone would have understated the gap by two
orders of magnitude.

The STEP3 arm reproduces the banked Step-3 cell exactly, P_pop 0.0771 and 10.50x, which
confirms the viz path and the metric path are seeing the same strokes.

## 2. What the frames show

- **STEP3 still**: clean, thick, tapered strokes with **sharp preserved corners**, sitting on
  the faint GT crease underneath. Sparse — the lower silhouette and several edges are simply
  absent, which is recall 0.4206 made visible.
- **DexiNed still**: the whole part is drawn, silhouette, hole and interior edges, but every
  stroke carries a fuzzy fringe. It reads as a scratchy sketch rather than CAD linework.
- **STEP3 difference frame**: almost entirely black, meaning both frames agree, with only thin
  red/blue fringes from sub-pixel camera motion. **No isolated single-colour strokes**, so
  nothing appears or vanishes. That is cut 0.0002 visible directly.

## 3. Reported, NOT gated: mesh P/R

DexiNed cloud P 0.7302 / R 0.8431. STEP3 zero-knob P 0.8139 / R 0.4206. Kept for the same
reason P_pop is kept: so a pretty still cannot fool us about correctness, exactly as P_pop
stops a pretty still fooling us about stability. Neither number gates anything here.

## 4. The synthesis, and the actual blocker

Neither carrier is the finished answer. STEP3 is clean and steady but draws less than half the
part. DexiNed draws essentially all of it but churns. **The blocker is not carrier point
quality, it is chain organisation**: 220,680 points collapse to 29,673 after NMS and then
fragment into 4,007 chains of median 4 vertices, where STEP3's 7,208 points give 42 chains of
median 5. The DexiNed cloud has the coverage; what it lacks is a chaining that produces long
persistent strokes instead of short ones.

That makes the next question concrete and cheap: can the frozen chainer's gap and collinearity
settings, or a merge pass over its output, turn 4,007 fragments into tens of long strokes
without touching the carrier? If yes, DexiNed's coverage and STEP3's steadiness are compatible.
If no, the carrier is not usable for NPR at any coverage.

## 5. Implementation notes, disclosed

- Clustering is the frozen `strokes.chain_linelets_3d` through
  `m1b_stroke_temporal.build_chains`, at that module's own defaults, so viz chains and metric
  chains are identical. Projection with occlusion splitting and the Canny baseline are the
  frozen `frame_data`. Only the stroke rendering is new.
- **Piecewise-linear throughout, no smoothing of any kind**, so corners survive.
- Width is constant in screen space; carrier length is pixel-anchored at L_px = 2.681, the
  chair-calibrated value, frozen and disclosed.
- **Taper is applied only where a stroke end sits on a depth discontinuity**, tested at the
  97th percentile of the depth-gradient magnitude, which is the silhouette/occlusion reading
  of "true endpoint". A chain break gets a flat cap.
- Gaps are bridged in 3-D by the chainer before projection; hidden-line removal happens after,
  in the projection, which is the required order.
- Strip frames are consecutive orbit frames 100 to 106 of 240, adjacent rather than spaced.

## 6. Files

`out/featviz/stroke_cadpartA_{dexined,step3}_strip.png` (3220x504),
`out/featviz/stroke_cadpartA_canny_strip.png`,
`out/featviz/stroke_cadpartA_{dexined,step3}_diff.png` (1700x1700),
`out/featviz/stroke_cadpartA_{dexined,step3}_still.png` (1700x1700),
`out/strokeviz.json`, `out/m1b_stroke_temporal_table_sv{dexined,step3}.{json,md}`,
`scripts/strokeviz.py`. Nothing committed.
