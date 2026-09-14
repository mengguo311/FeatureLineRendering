# POSTER REPRODUCTION — rasterisation-state feature-line fields on one lego view

Reproduction of the pipeline described to me as Hao Weiren / Mukai, *3D Gaussian Splatting
rasterisation-state feature line rendering*, SIGGRAPH Asia 2025 poster. One held-out lego view.

* script `scripts/poster_repro.py` — direct run, `conda vfsdgs`, `CUDA_VISIBLE_DEVICES=1`
* numbers `out/poster_repro_lego.json`
* **mesh EVAL-ONLY is not even exercised: this is pure image-space and reads no mesh at all.**
* per-frame image-space, so it **will** flicker. Temporal is **reported, not gated**.
* no git commit.

---

## 0. THE HONEST SCOPING, FIRST

**I have never seen the poster or its Figure 3.** Everything here is reconstructed from the
user's description of the method. I can therefore state what this pipeline *does*, but I
**cannot** assess fidelity to the source, and nothing below should be read as "matches the
poster". The comparison to Figure 3 is deferred to whoever has the figure.

Choices that are **RECONSTRUCTED, not sourced**:

| choice | what we used | why, and what is unknown |
|---|---|---|
| lego **view** | `cams[5]` (`r_5`) | first held-out TEST view and the anchor of the banked 240-frame orbit — pre-committed, not hand-picked. The poster's view is unknown. |
| **k** | 8 emitted, fields at k=4 **and** k=8 | both reported so k-sensitivity is visible rather than asserted. The poster's k is unknown. |
| top-k weight **normalisation** | renormalised *within* the retained top-k (a pixel's k weights sum to 1) | the alternative — normalise by the pixel's full accumulated weight — leaks "how much mass top-k captured" into the dissimilarity. The poster's convention is unknown. |
| per-channel **operators** | Sobel magnitude (opacity, depth); 4-neighbour max (normal angle, Lab dE, top-k) | the poster's operator forms are unknown. |
| **fusion** | rank-normalise each field to [0,1], then MAX | **OUR PARAMETER-FREE STAND-IN. The poster's real fusion rule is UNKNOWN.** |
| **threshold** to ink | top-n of the support, n matched to the per-frame Canny ink count; plus a disclosed richer top-5% | the poster's line-rendering threshold is unknown. |
| depth **background fill** | `inf` -> `1.05 x max finite depth` | needed so a Sobel is defined at the silhouette. |
| tie-break | raster order (see §5 bug 2) | arbitrary but deterministic and disclosed. |

Also disclosed: `index_add_` on CUDA accumulates in nondeterministic float order, so the
composited albedo — and hence the Canny reference ink count — varies by **~0.6% run to run**
(6431–6517 px across five runs of the identical command). No conclusion here turns on it.

---

## 1. GAUSSIAN-ID PLUMBING — the claim was half true

The per-pixel front-to-back ordering and the normalised blend weights **already exist** in
`src/render.py`: fragments are lexsorted by `argsort(fz)` then `argsort(pix)`, and the weight
is `w = T * fa` with `T = exp(excl - base)` from a segmented exclusive cumsum of
`log1p(-fa)` (`src/render.py:124-143`).

**The Gaussian ID is not.** `gi, pi = torch.nonzero(m, as_tuple=True)` (`src/render.py:97`)
produces the per-fragment Gaussian index and uses it to gather `zs[gi]`, `ns[gi]`, `cs[gi]` —
then discards it. There is no `frag_id`. Emitting IDs is additive, but it is an addition.

`src/render.py` is **NOT modified** (standing constraint: do not touch the shipped pipeline).
`render_state()` in `scripts/poster_repro.py` is a faithful copy of the shipped fragment
build + lexsort + compositing with exactly one array added, `frag_gid`.

Two traps that would have produced plausible-but-wrong IDs, both handled explicitly:

* **(a) triple index remap.** `gi` is local to the radius bucket, which indexes the `ok`-culled
  set, which indexes the `keep_mask` subset. Carried back to the original ply row via
  `gid0 = np.nonzero(keep_mask)[0]` before any bucketing. Get this wrong and the IDs name the
  wrong primitives with no visible symptom.
* **(b) top-k by weight is NOT the front-most k.** `w = T*alpha` and `alpha` varies per
  fragment, so weight is not monotone in depth. A **second** stable lexsort (descending `w`,
  then pixel) is required; slicing the existing front-to-back order would be wrong.

Measured on this view: **166,044 gaussians, 99,721 after the de-floater, 8,762,739 fragments**.
Mean top-8 occupancy over object pixels **7.56 of 8**; **89.5%** of object pixels have a full 8.
So k=8 is not starved on lego — the top-k sets are genuinely populated.

## 2. THE FIVE FIELDS

1. **opacity** — Sobel magnitude of the accumulated alpha
2. **depth** — Sobel magnitude of the mean depth (background filled)
3. **normal** — 4-neighbour max of `arccos(n_p . n_q)` in degrees
4. **colour/tone** — 4-neighbour max of CIE-Lab dE76 on the composited **view-independent
   SH degree-0 albedo** (rasterisation state, not the photograph)
5. **top-k Gaussian**, at k=4 and k=8 — 4-neighbour max of **weighted-overlap dissimilarity**

$$D(p,q) \;=\; 1 - \sum_{i \in \mathcal{S}_p \cup \mathcal{S}_q} \min\!\big(w_p(i),\, w_q(i)\big)$$

over the **union** of the two pixels' top-k ID sets, with each pixel's weights renormalised to
sum to 1 within its own top-k. Because IDs are unique within a pixel,
`sum_{i,j} [id_p(i)==id_q(j)] * min(w_p(i), w_q(j))` equals the union sum exactly, which is how
it is computed. Chosen over Jaccard and over top-1-ID-changed for the reason argued before the
build: gaussians project to ~2.8 px half-length on lego, so the dominant Gaussian turns over
*everywhere*, and a hard ID comparison would paint the whole surface. A gaussian merely fading
out of the top-k still carries weight in both pixels, so weighted overlap stays low there and
saturates only where the contributing mixture is replaced wholesale.

## 3. FUSION — labelled as ours, and it has a real defect

Per-frame **rank-normalise each field to [0,1], then MAX**. Rank-normalisation is
`rn(v) = #{pixels strictly below v} / N`, which is tie-safe: a tied block of zeros maps to
exactly 0 rather than floating up to mid-range as an average rank would. No hand-set weights,
nothing per-scene. **This is OUR PARAMETER-FREE STAND-IN; the poster's rule is UNKNOWN.**

**It does not produce a good line drawing, and the reason is measurable.** Fraction of each
field's top-q detections lying within 2 px of the `alpha>0.5` boundary:

| q | opacity | depth | normal | colour | top-k k=4 | top-k k=8 | **FUSED** |
|---|---|---|---|---|---|---|---|
| 0.01 | **1.000** | 0.429 | 0.477 | 0.409 | 0.478 | 0.505 | **0.621** |
| 0.02 | **1.000** | 0.369 | 0.436 | 0.350 | 0.408 | 0.415 | **0.614** |
| 0.05 | **0.985** | 0.298 | 0.298 | 0.275 | 0.271 | 0.332 | **0.604** |

Two findings:

* **The opacity channel is a pure silhouette detector** — 100.0% of its top 1% and 2% lies
  within 2 px of the outline. On a frozen 3DGS the accumulated alpha is ~1 across the whole
  object and falls only at its boundary, so this channel contributes the outline and nothing
  else.
* **The fused field is MORE silhouette-dominated than four of its five inputs** (0.62 vs
  0.27–0.51). Rank-normalisation equalises the channels' *distributions* but not their
  *spatial support*: the silhouette is top-ranked in all five, so a MAX puts it first, and a
  2–3 px-wide band around a long perimeter eats the whole ink budget before any interior crease
  is reached. At Canny-matched density (6,436 px) the rendering is essentially an outline
  (panel tile 9); the interior lines are plainly present in the individual normal, colour and
  top-k fields but the union does not surface them first.

That is a defect of the stand-in I proposed, not of the channels. The obvious repair —
non-maximum suppression to thin each contour to 1 px before thresholding — is standard, would
cut the silhouette's pixel cost ~3x, and is **not implemented here** because it is one more
reconstruction I cannot justify against an unseen source.

## 4. IS THE NOVEL TOP-K CHANNEL REDUNDANT? — measured, and my prediction was wrong

Jaccard of top-q detection sets, top-k(k=8) against every other channel, each with its own
**rotated null** (the same mask rotated 90°: identical cardinality, alignment destroyed), plus
the fraction of top-k detections farther than 3 px from the other channel's nearest detection.

| q | vs depth | vs **normal** | vs colour | vs opacity | vs top-k k=4 | null (all) |
|---|---|---|---|---|---|---|
| 0.005 | 0.137 | 0.260 | 0.301 | 0.013 | 0.644 | 0.0000 |
| 0.010 | 0.336 | **0.564** | 0.493 | 0.024 | 0.655 | ≤0.0008 |
| 0.020 | 0.566 | **0.764** | 0.663 | 0.030 | 0.589 | ≤0.0043 |
| 0.050 | 0.389 | 0.443 | 0.402 | 0.066 | 0.606 | ≤0.0125 |

fraction of top-k(k=8) detections >3 px from the nearest other-channel detection:

| q | vs depth | vs normal | vs colour | vs opacity |
|---|---|---|---|---|
| 0.010 | 0.134 | **0.208** | 0.223 | 0.470 |
| 0.020 | 0.140 | **0.110** | 0.137 | 0.526 |

**Verdict.** Every real Jaccard is 50–200x its rotated null, so the overlaps are structure, not
chance. The top-k channel is **substantially but not completely redundant**, and — correcting
the prediction I made before the build — **its closest partner is the NORMAL channel, not
depth** (0.764 vs 0.566 at q=2%). The mechanism is straightforward in hindsight: the composited
normal is the weight-weighted mixture of the contributing gaussians' normals, so the normal
already encodes mixture turnover, which is exactly what weighted-overlap measures. It is close
to **disjoint from opacity** (J ≤ 0.066), i.e. it is not merely a silhouette detector. Between
11% and 21% of its detections at q=1–2% are more than 3 px from any normal detection, so it does
carry some structure no other channel places — but it is not an independent fifth signal.

**k-sensitivity is real:** J(k=4, k=8) is 0.59–0.66, so roughly a third of the detection set
changes between k=4 and k=8. Reporting the channel without stating k would be under-specified.

## 5. TWO BUGS FOUND AND FIXED DURING THE BUILD (both would have produced confident nonsense)

**Bug 1 — empty-vs-empty pixel pairs manufacture maximal responses.** The rasterisation state is
undefined where nothing is rendered, and the two set-valued channels return their *maximum*
there by accident: two zero normals give `arccos(0) = 90°`, and two empty ID sets share nothing,
so weighted overlap gives exactly 1. Unmasked, the background does not read as "no feature", it
reads as "maximal feature". First symptom was cosmetic (purple backgrounds in the normal and
top-k tiles); the real damage was a large tied block sitting at the *top* of both fields. Fixed
by zeroing any edge whose **both** endpoints lack coverage, while keeping object-vs-empty edges,
which are genuine silhouettes.

**Bug 2 — a quantile threshold plus `>=` admits an entire tied block.** With `thr =
quantile(v, 1-q)` and `field >= thr`, if the tied block at the top is larger than q, the
detection set is the *whole block at every q*. Symptom: Jaccards constant to three decimals
across a 10x sweep of q — J(top-k, normal) read **0.954 at every single q**, which is what
prompted the check. Had I reported that number it would have been a fabricated finding
("the top-k channel is a 95% duplicate of the normal field") produced entirely by the
thresholding artefact. Fixed by selecting exactly n pixels via a stable argsort. After the fix
that same comparison reads 0.26 / 0.56 / 0.76 / 0.44 across q.

## 6. FREE INSTRUMENT — ink_churn (REPORTED, NOT GATED)

8 **consecutive** frames (100–107) of the banked 240-frame lego orbit, ink-matched per frame to
the Canny stroke render so the comparison is like-for-like at equal ink budget. `ink_churn` =
fraction of ink pixels with no ink pixel within 1.5 px in the adjacent frame, symmetrised.

| pipeline | ink_churn (mean over 7 adjacent pairs) | vs Canny |
|---|---|---|
| per-frame Canny — **banked** | 0.5359 | 1.00x |
| per-frame Canny — recomputed here | **0.5354** (max 0.5562) | 1.00x |
| **poster fused composite (this build)** | **0.1780** (max 0.1826) | **3.01x steadier** |
| our object-space strokes — banked | 0.0584 | 9.18x steadier |

The recomputed Canny lands on the banked value to within 0.0005, which is the sanity check that
this harness reproduces the banked baseline.

The poster composite sits **between** the two, and the placement is explicable rather than
lucky: the ~62% of its ink that lands on the silhouette is geometrically stable frame to frame,
while its interior detections turn over like any per-frame image-space detector. **This is
reported, not gated** — the method is per-frame image-space by construction and was never
claimed to be temporally stable.

## 7. FILES

| file | what |
|---|---|
| `out/featviz/poster_repro_lego_fields.png` | **3720 x 1478** labelled 11-tile panel: RGB, the 5 fields (top-k at k=4 and k=8), fused rank-max, both line renderings, redundancy overlay |
| `out/featviz/poster_repro_lego_composite_still.png` | composite still alone, richer top-5% budget (12,784 ink px) |
| `out/featviz/poster_repro_lego_composite_still_inkmatched.png` | composite still at Canny-matched budget (6,436 ink px) |
| `out/featviz/poster_repro_lego_consecutive_strip.png` | 8 consecutive orbit frames, fused (top) vs per-frame Canny (bottom) |
| `out/poster_repro_lego.json` | every number above |
| `scripts/poster_repro.py` | the build |

## 8. WHAT I WOULD SAY IF ASKED "DID WE REPRODUCE IT?"

We reproduced **the pipeline**: rasterisation state including per-pixel top-k Gaussian IDs and
normalised blend weights, five per-channel discontinuity fields, and a fused composite, from a
frozen vanilla 3DGS with no custom CUDA rasteriser and no modification to the shipped renderer.

We did **not** verify it against the poster, because we have not seen the poster.

On the substance: the four conventional channels behave as expected; the novel top-k channel is
real, is far above its null, is **more redundant with the normal channel than with depth**, and
adds 11–21% of detections that no other channel places. The weak link is the **fusion**, which
is mine and not the poster's — a rank-max union is silhouette-dominated by construction and
throws away interior lines that its own inputs clearly contain.
