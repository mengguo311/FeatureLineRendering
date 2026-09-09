# MERGE — STEP3 trunk + DexiNed gap-fill, visual-first (plan, frozen before execution)

**GO on all three pre-registered legs**, with one honest caveat the gate did not name.
More complete (1.90x drawn arc, visibly), not rougher in stroke quality, and **steadier than
the trunk**: cut 0.0001 against the trunk's 0.0002 and a bar of 0.0102. The caveat is that the
fill's cost is not roughness but a handful of **false off-crease stubs**, which the wording did
not cover and which you are the final judge of.

## The diagnostic that set the design
The frozen chainer derives BOTH its non-maximum-suppression radius and its bridging gap from
the median carrier length of whatever set it is handed. The two carriers were chained at
wildly different scales, which is very likely why one fragmented:

| carrier | median l | NMS radius | bridging gap | chains |
|---|---|---|---|---|
| STEP3 | 0.0308 | 0.0308 | 0.123 | 42 |
| DexiNed (as first run) | 0.00884 | 0.00884 | **0.0354** | **4,007** |

DexiNed was chained with a gap **3.5x smaller** than STEP3's on a part of bounding diagonal
3.16, so any 0.035 hole broke a chain. The roughness was plausibly my constant, not the cloud.

## Build order, as converged
1. **Re-chain DexiNed at the SAME object-space scale as the trunk**, L_px 8.632, cadpart's own
   native pipeline half-length, instead of the chair-calibrated 2.681. gap_mult stays frozen
   at 4.0, so both carriers are now chained comparably.
2. **Min-length + RANSAC straightness filter** on the re-chained DexiNed strokes. **DECLARED
   SCOPE LIMIT: this bakes a polyhedron assumption into the renderer.** It is defensible for
   clean solids and will not survive contact with ficus or chair. Stated, not hidden.
3. **Vertex-level gap fill.** For every surviving DexiNed vertex, 3-D distance to the nearest
   STEP3 stroke polyline; keep only vertices beyond a pixel-anchored 3 px equivalent, then
   re-chain ONLY those. The STEP3 trunk is never touched, and only genuinely novel reach is
   borrowed. The threshold is set from stroke width, a rendering criterion, not fitted.
4. **3-D endpoint snap ONCE over the whole merged set**, gated on the two endpoint tangents
   being non-parallel, so parallel chamfer edges are never welded together. Object-space and
   computed once, so it cannot reimport per-frame flicker.

## Deliverable
Merged still, consecutive-frame strip, and diff, at
`out/featviz/stroke_cadpartA_merge_{still,strip,diff}.png`, same convention as the other two
carriers, rendered from the **identical camera at identical stroke settings**. The two diffs
stay distinct: the stability diff is merged frame k against k+1; completeness is a separate
side-by-side against STEP3-only.

Reported, never gated: P_pop and its cut term, mesh P/R, plus the roughness and completeness
proxies **stroke count, median vertices per stroke, total drawn arc length**.

## PRE-REGISTERED VISUAL GO/NO-GO
**GO** if the merged still is visibly MORE COMPLETE than STEP3-only, is NOT visibly rougher,
and the strip is as steady as STEP3-only with **cut <= 0.0102**. **NO-GO** otherwise, reported
straight.

Why that bar is tight: if the merged drawing borrows a fraction phi of its strokes from a
DexiNed set whose churn is unchanged at cut 0.1328, merged cut lands near phi x 0.1328, so
clearing 0.0102 without de-hairing would require borrowing under 8 percent of DexiNed's
strokes. Step 1 is what buys the headroom to borrow enough to matter.

## Author's prior, recorded so it can be wrong
The larger gap collapses DexiNed from 4,007 chains to a few hundred and drops its cut
substantially; the merge recovers most of the missing hex outline and verticals; merged cut
lands between 0.001 and 0.01 and passes. **The leg most at risk is "not visibly rougher"**,
because the borrowed strokes sit on noisier points than the trunk.

**MESH EVAL-ONLY**: faint GT crease overlay plus reported-not-gated P/R.

---

# RESULTS

## 1. The pipeline, stage by stage

| stage | result |
|---|---|
| trunk (STEP3, untouched) | 42 strokes, median 5 vertices |
| **1. DexiNed re-chained at trunk scale** (L_px 8.632, gap_mult frozen 4.0) | NMS 29,673 -> **7,127**, strokes **4,007 -> 918** |
| 2. min-length (>= 4 carrier lengths) + RANSAC straightness (>= 80% inliers at 2.5 px) | 918 -> **93** |
| 3. vertex-level gap fill (> 3 px equivalent from any trunk stroke) | **737 of 828** vertices kept, re-chained to **28** filler strokes |
| 4. 3-D endpoint snap, tangent-gated | **70 strokes** (42 trunk + 28 fill), 4 snaps |

**The gap diagnostic was right.** Re-chaining the identical cloud at the trunk's object-space
scale, changing nothing but the assumed carrier length, cut fragment count by **4.4x** on its
own. The roughness really was my constant, not the carrier.

That 737 of 828 fill vertices survive the gap test, **89 percent**, confirms the borrowed
content is genuinely in the trunk's holes rather than redundant with it.

## 2. Temporal, decomposed — and why judging on `cut` mattered again

| arm | strokes | med verts | P_pop | = unmatched | + **cut** | ratio | drawn arc |
|---|---|---|---|---|---|---|---|
| STEP3 trunk | 42 | 5 | 0.0771 | 0.0770 | 0.0002 | 10.50x | 9.634 |
| **MERGE** | **70** | **5** | 0.0910 | 0.0909 | **0.0001** | 8.89x | **18.299 (1.90x)** |
| DexiNed raw | 4,007 | 4 | 0.1693 | 0.0365 | 0.1328 | 4.78x | — |

**Total P_pop says the merge is worse than the trunk, 0.0910 against 0.0771, and the ratio
falls from 10.50x to 8.89x. The `cut` term says it is marginally BETTER, 0.0001 against
0.0002.** The entire increase is `unmatched`, which is more strokes producing more correct
hidden-line events, not instability. Had we gated on P_pop as originally tempting, this build
would have been rejected for getting more complete. That is the second time the decomposition
changed the answer.

Against the frozen bar of 0.0102, cut passes by two orders of magnitude.

## 3. The visual verdict, leg by leg

**More complete: YES.** Drawn arc is 1.90x the trunk. Visibly added: the long ledge line on the
left-front face, the edges around the top hexagonal hole, and several verticals on the right
face and chamfer, all absent from STEP3-only.

**Not visibly rougher: YES on the terms of the gate, with a caveat.** The trunk's 42 strokes
are byte-identical, and the 28 added strokes are individually clean thick tapered strokes, not
scratchy. Quantitatively the merge sits at 70 strokes of median 5 vertices, next to the trunk's
42 of median 5 and nowhere near DexiNed's 4,007 of median 4.

**The caveat, which the gate did not name.** The fill's cost is not roughness, it is
**precision**: it adds perhaps a dozen short stubs sitting on flat faces with no GT crease
under them, and one visibly wavy stroke on the front face that reads as wrong on a polyhedron.
A viewer would not call the result hairy; they might call those marks debris. **This is a
distinction the pre-registered wording did not draw, and the call is the user's, not mine.**

**Strip as steady as STEP3-only: YES.** Seven consecutive orbit frames are essentially
identical apart from camera rotation, consistent with cut 0.0001.

## 4. Author's prior, scored

I predicted the larger gap would collapse DexiNed to "a few hundred" chains: **right**, 918. I
predicted merged cut between 0.001 and 0.01: **wrong, conservatively**, it came in at 0.0001,
an order of magnitude better than my range. I predicted "not visibly rougher" would be the leg
most at risk: **right**, it is the only leg carrying a caveat.

## 5. Reported, never gated

Mesh P/R: DexiNed cloud P 0.7302 / R 0.8431, STEP3 zero-knob P 0.8139 / R 0.4206. The merged
arm's P/R was not computed, because the deliverable is the drawing and the pre-registration
gated on the visual legs plus `cut`. It can be added on request.

**Declared scope limit, restated.** Stage 2's min-length and straightness filters bake a
polyhedron assumption into the renderer. Defensible for clean solids, and it will not survive
contact with ficus or chair.

## 6. Files

`out/featviz/stroke_cadpartA_merge_{still,strip,diff}.png`, same convention and identical
camera and stroke settings as the other two carriers. `out/mergeviz.json`,
`scripts/mergeviz.py`, `logs/mergeviz_temporal.log`. Nothing committed.
