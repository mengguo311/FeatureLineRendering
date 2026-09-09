# 5-SOLID TURNTABLE GALLERY — and a finding that undercuts its own premise

`scripts/turntable_gallery.py`. **MESH EVAL-ONLY in the strictest sense: this script reads no
mesh at all.** Direct run, no multi-agent workflow. Nothing committed.

---

## VERDICT: NO-GO, and not for the reason we pre-registered

I expected gicosa to fail the "name the shape" clause alone. **Two clauses failed, on more
solids than predicted, and one of them inverts the premise of the whole step.**

| clause, worded on the video | result |
|---|---|
| (a) no stroke appears/disappears except at a silhouette crossing | **PASS**, everywhere checked |
| (b) every Canny panel **visibly boils** | **FAIL** on gcube and gicosa |
| (c) uniform stroke weight, sharp corners, no hairiness | **PASS** |
| (d) the sparsest tile still **reads as its solid** | **FAIL** on gicosa and gcube |

## 1. The finding: P_pop measures stroke-identity churn, not visible flicker

On gcube and gicosa the per-frame Canny clip draws a **complete, crisp, visually stable** line
drawing. The gicosa Canny panel renders the whole icosahedron — full silhouette plus all
interior triangulation — and holds it steadily across seven consecutive frames. Ours draws a
partial top edge and a few verticals.

**Canny looks better than us on these solids, decisively.**

Yet the banked ratios say 20.77x and 13.90x in our favour. Both are true, and the
reconciliation is the finding: **Canny's ink is stable while its stroke IDENTITY is not.** Its
271 to 470 short polylines get re-decomposed every frame, so the stroke-level matcher behind
P_pop sees enormous churn, while the drawn pixels barely move. `P_pop` is a stroke-identity
metric. On a flat-shaded polyhedron, image edges are crisp and persistent, so identity churn
and visible flicker come apart completely.

The temporal crown jewel was established on **lego and chair**, textured scenes where Canny
fires on decals and the ink genuinely boils. **Extending that claim to clean solids on the
strength of P_pop was not warranted, and this video is what shows it.** That is the argument I
made for building the video, applied against my own recommendation.

## 2. A correction to my own earlier reading

In `VIDEO_RESULTS.md` I judged cadpartA's Canny panel as visibly boiling. That judgement came
from a contact sheet sampling **every 20th frame**, which exaggerates change. The consecutive
frames here show gcube and gicosa Canny as steady. cadpartA's Canny is genuinely denser and
messier, because of the through-hole and chamfers, so the reading may still hold there — but
**I have not verified it on consecutive frames, and I should not have generalised from
20-frame spacing.**

## 3. Per solid

| solid | strokes | arc | runs/frame ours | strokes/frame Canny | P_pop | cut | ratio | banked from |
|---|---|---|---|---|---|---|---|---|
| cadpartA | 42 | 9.634 | 25–42 | 374–465 | 0.0771 | 0.0002 | 10.50x | Step 3 step3spec |
| gcube | 23 | 5.618 | 17–24 | 271–450 | 0.0381 | 0.0000 | 20.77x | Step 4 |
| gprism | 44 | 6.699 | 25–40 | 285–366 | 0.0459 | 0.0001 | 18.97x | Step 4 |
| gicosa | 25 | 4.093 | 14–24 | 361–470 | 0.0636 | 0.0000 | 13.90x | Step 4 |
| gstep | 57 | 9.346 | 27–57 | 284–474 | 0.0676 | n/a | 11.24x | Step 8 ship |

**Clause-by-clause, and I mark what I did not verify rather than guessing:**

| solid | (a) no popping | (b) Canny boils | (c) weight/corners | (d) names the shape |
|---|---|---|---|---|
| cadpartA | PASS | **unverified on consecutive frames** | PASS | **PASS**, reads as a hex nut |
| gcube | **PASS** verified | **FAIL** verified | PASS | **FAIL**, Canny reads as a cube, ours does not |
| gprism | unverified | unverified | PASS | marginal, partial arc plus verticals |
| gicosa | **PASS** verified | **FAIL** verified | PASS | **FAIL**, unreadable as an icosahedron |
| gstep | unverified | unverified | PASS | marginal-pass, nested rectangles read as a stepped block |

I verified motion clauses on gcube and gicosa in full, and readability on all five from a
single-frame composite. gprism and gstep motion clauses are **not verified** and are reported
as such.

## 4. Carrier-geometry identity, as required

Each solid uses its locked fallback carrier: the Step-4 zero-knob set (f = 1.00, shipped spec
consensus prune, no keep-fraction), chained by the frozen `m1b_stroke_temporal.build_chains`
at the carrier's own half-length from its own npz — the identical call the banked temporal runs
made. Part B polish sets stroke width and taper and touches no 3-D point.

**No endpoint snap was applied.** dd3 snapped endpoints, but snapping moves 3-D points and
would change the metric. Omitting it is the price of the identity guarantee, and it is why
every banked P_pop, cut and ratio above carries to these clips unchanged rather than being
re-measured. With no snap there are no joins, so every stroke end is a true open endpoint and
tapers.

## 5. Nothing withheld, because the failure is not what the rule anticipated

The locked instruction was to ship four and explain the fifth if **gicosa** failed readability.
Two solids fail readability, and a clause I expected to pass everywhere fails on both solids I
could verify. Shipping four under those conditions would present a conclusion the evidence does
not support, so **all five clips are delivered and the gallery is reported NO-GO**, with the
per-clause table above as the honest record. Whether to publish any of it is your call.

## 6. Files

Per solid: `out/featviz/turntable_<solid>_ours.mp4`, `_canny.mp4`, `_strip.png` (top row ours,
bottom row per-frame Canny, seven consecutive orbit frames 100–106 of 240, same camera).
Plus `out/featviz/turntable_GALLERY_5solid.png` (one frame per solid, ours only) and
`out/turntable_gallery.json`, `scripts/turntable_gallery.py`, `logs/turntable_gallery.log`.
