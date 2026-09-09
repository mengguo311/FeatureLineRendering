# GICOSA PILOT — the dd3 pipeline, byte-identical, on a second solid

**MESH EVAL-ONLY**: faint GT crease overlay only. P/R is not computed and not gated.
Direct run, no multi-agent workflow.

---

## VERDICT: NO-GO. Fallback taken, no negotiation.

| pre-registered leg, worded on the image | result |
|---|---|
| outer silhouette **closed**, a continuous polygon | **FAIL** |
| **most visible interior facet edges** drawn | **FAIL** |
| uniform stroke weight, sharp corners, no hairiness | **PASS** |
| no line drawn across a flat facet where no edge exists | **PASS** |
| strip as steady as cadpart's | **PASS** (cut 0.0000) |

The tile is visibly less complete than the cadpart dd3 tile: the black strokes cover roughly
the upper-left third of the silhouette while the rest of the outline and most of the interior
triangulation sit under bare GT overlay. **Per the locked rule the gallery takes the fallback:
the Step-4 zero-knob carrier with Part B polish only, presented as incomplete, not repaired.**

**My pre-registered prior was correct**: "gicosa passes cleanliness and fails completeness."

## 1. Preconditions, both satisfied

**1. No cadpart constant travelled.** `L_px` was derived at run time from gicosa's own trunk:
median half-length 0.01841 world at median depth 3.5194 with f 1111.11, giving
**L_px = 5.8123**. cadpart's 8.632 appears nowhere. The rule travelled, the number did not.

**2. The DexiNed Phase-1b cloud was built first**, with cadpartA's banked arguments exactly
(n_ref 40, K 6, rho 0.2, tau 1.5, thr 0.5, native, halfpix 0.0, resid_max 1.0, rel_eps 0.02).
DexiNed edges for all 100 views were cached first, since those were absent too.

**A third asset was absent and had to be built, as I flagged in the design argue.** The dd2
gate reads the 2DGS normal buffer and no 2DGS model existed for gicosa. One was trained with
the frozen chair/lego/cadpartA recipe, unchanged: **test PSNR 40.83 dB**.

## 2. The paradox: a BETTER cloud produced a WORSE tile

| Phase-1b cloud | points | precision | recall |
|---|---|---|---|
| **gicosa** | 208,677 | **0.7650** | **0.9689** |
| cadpartA (banked) | 220,255 | 0.7302 | 0.8431 |

gicosa's cloud is better on both axes. The tile is worse anyway.

| stage | gicosa | cadpartA |
|---|---|---|
| trunk strokes | **25** | 42 |
| cloud -> NMS -> chains | 208,677 -> 10,952 -> 1,420 | 220,680 -> 7,127 -> 918 |
| after min-length + straightness | 192 | 93 |
| fill candidates after gap-fill | 37 | 28 |
| **after the dd2 dihedral gate** | **12** | 17 |
| merged strokes | **37** | 59 |
| arc vs its own fallback trunk | 1.77x | 1.54x |

## 3. Where it fails, measured — and it is not an artefact

The dd2 gate's median cross-stroke dihedral over gicosa's fill vertices is **0.10 deg**, against
cadpartA's **37.49 deg**. I did not ship that ambiguous, because a zero can mean "flat" or
"unmeasurable" and the code fills unmeasurable with zero. Separated:

| | value |
|---|---|
| fill vertices | 444 |
| **measurable fraction** | **0.9932** |
| median dihedral, measurable only | **0.107 deg** |
| fraction of measurable vertices >= 30 deg | **0.279** |

**Measurability is 99.3 percent, so unmeasurability is not the cause.** The 2DGS buffer
genuinely reads gicosa's fill-candidate locations as flat, and **the gate is behaving
correctly** by rejecting them.

**Why a 0.765-precision cloud yields a 0.28-precision fill.** The fill is what remains after
everything within 3 px of the trunk is removed, and the trunk already covers the strongest
creases. So the true positives are disproportionately already drawn, and **gap-filling
concentrates the cloud's residual false positives**. Cloud precision does not transfer to fill
precision, and on a solid with a sparse trunk the gap population is mostly the cloud's bad 23
percent.

That is a general result about this architecture, not a gicosa quirk, and it predicts the same
squeeze on any solid whose trunk is weak.

## 4. Reported, not gated

| gicosa pilot, 240-frame orbit | value |
|---|---|
| P_pop | 0.0766 |
| unmatched | 0.0766 |
| **cut** | **0.0000** |
| baseline per-frame Canny P_pop | 0.8843 |
| ratio | **11.55x** |

Stability is excellent and the merge cost nothing: `cut` is exactly zero, and the ratio sits
between cadpart's dd3 12.03x and its merge70 8.89x. **Completeness, not stability, is what
failed.**

## 5. What the locked rule costs, stated so the cost is visible

The pilot's merged tile is **strictly more complete** than the fallback: 37 strokes and 1.77x
the arc, against the fallback's 25 strokes. Taking the fallback therefore gives up real drawn
content. That is the price of the no-negotiation rule, and it is reported rather than used to
reopen the decision.

## 6. Files

`out/featviz/stroke_gicosa_pilot_still.png`, `_pilot_strip.png`,
`_pilot_fallback_still.png`, `_pilot_diff_vs_fallback.png` (fallback red, pilot blue, shared
black), all at the same camera and stroke settings as every cadpart carrier.
`out/gicosa_pilot.json`, `out/gicosa_gate_diag.json`,
`out/dexprimary_p1b_gicosa_ref40.json`, `out/dexprimary_p1b_cloud_gicosa_ref40.npz`,
`out/dexined_edges_gicosa/`, `out/2dgs_gicosa/`, `scripts/gicosa_pilot.py`,
`scripts/run_2dgs_gicosa.sh`, `logs/gicosa_pilot.log`, `logs/2dgs_gicosa.log`,
`logs/p1b_gicosa.log`.

**Declared polyhedron-scope limit still stands** on the inherited min-length, straightness and
30 deg crease filters.
