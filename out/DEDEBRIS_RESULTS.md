# DE-DEBRIS — object-space support gate on the merge fill

Executes `out/DEDEBRIS_SPEC.md`. Direct run, no multi-agent workflow. Trunk byte-identical
throughout. **MESH EVAL-ONLY**: faint GT crease overlay only.

---

## VERDICT: NO-GO

Per the spec's own rule, *"NO-GO if it also strips real completeness or the debris survives"*.
**The gate removed the debris and the real completeness together.**

| pre-registered leg | result |
|---|---|
| (a) no longer shows the flat-face stubs or the wavy front stroke | **PASS** |
| (b) still keeps the ledge line, top-hole edges, right-face verticals | **FAIL** |
| (c) strip stays steady, cut <= 0.0102 | **PASS** (cut 0.0001) |

**Keep the merge as-is.** The support gate as pre-registered is not usable.

## 1. What the gate did

| quantity | merge | de-debrised |
|---|---|---|
| strokes | 70 (42 trunk + 28 fill) | **50 (42 trunk + 8 fill)** |
| fill strokes dropped | — | **20 of 28** |
| total drawn arc | 18.299 | **11.797** |
| arc vs trunk-only (9.634) | 1.90x | **1.22x** |
| P_pop | 0.0910 | 0.0743 |
| unmatched | 0.0909 | 0.0742 |
| **cut** | 0.0001 | **0.0001** |
| ratio vs per-frame Canny | 8.89x | **10.90x** |

The spec expected arc to "drop slightly". It dropped by **36 percent**, removing **75 percent
of everything the merge had added** over the trunk. That is not a polish, it is a partial
revert.

## 2. Leg (a): the debris did go

The `dedebris_diff` marks dropped fill strokes in red on the kept drawing. Confirmed removed:
the **wavy front-face stroke** the spec named, and most of the mid-face vertical stubs.

One precision on the still: a few short T-shaped marks remain. Those belong to the **trunk**,
not the fill, and were present in the STEP3-only still from the start. The gate never touches
the trunk, by design, so they are out of its reach.

## 3. Leg (b): so did all three named must-keep features

The same diff shows in red, i.e. dropped:

- the **left ledge line** running from the left corner,
- the **top-hole edges**, the dashes around the hexagonal hole,
- the **right-face verticals**, and the long right-edge vertical.

Those are exactly the three features the spec listed as must-keep. The gate did not
discriminate debris from weak-but-real edges; it discriminated **strong evidence from weak
evidence**, and the real new content is weak by construction.

## 4. Why it failed — a flaw in MY threshold rule, not in the spec's idea

The support field is the 2DGS normal-discontinuity under each vertex, and I set the reference
to **the median trunk vertex**, measured at **21.56 degrees**, arguing it was scale-relative
and unfitted. It is both of those, and it is still the wrong reference.

**The trunk is, by selection, the strongest-evidence content in the scene** — it is what the
STEP3 ranker kept. The fill exists precisely because it lies on edges the trunk's ranker was
not confident enough to keep. Requiring fill strokes to carry as much support as the median
trunk vertex therefore requires weak edges to look as strong as strong ones. The rule is
structurally self-defeating, and the 20-of-28 drop rate is what that looks like.

The idea in the spec is sound: a flat-face stub has no geometric discontinuity under it. What
is wrong is my calibration point.

**The principled fix, stated but NOT applied here**: reference the trunk's *lower tail* rather
than its median, for example its 10th percentile, on the argument that the weakest stroke we
already trust sets the floor for what else we will trust. I am not re-running with that
threshold and reporting it as the result, because changing the number after seeing the picture
is exactly the retro-fitting this campaign has refused everywhere else. It should be
pre-registered as its own step if you want it.

## 5. Reported, not gated

**Density, which I argued against and should own.** I pushed back that local DexiNed-cloud
density would be weak because the fill vertices are themselves cloud points. Measured, kept
strokes sit at density **7.75** against dropped at **4.36**, a 1.8x separation. That is not
nothing. The honest reading is narrower than "density works": the two signals **correlate**,
since the kept/dropped split was made by the discontinuity gate, so this does not by itself
show density separates debris from weak real edges. It does show my dismissal was too strong.

Mesh P/R unchanged and unused as a gate: DexiNed cloud P 0.7302 / R 0.8431, STEP3 zero-knob
P 0.8139 / R 0.4206.

**Declared polyhedron-scope limit, restated.** The min-length and RANSAC straightness filters
carried over from the merge bake a polyhedron assumption into the renderer. Defensible for
clean solids; it will not survive contact with ficus or chair.

## 6. Files

`out/featviz/stroke_cadpartA_merge_still.png` and `_merge_strip.png` (overwritten with the
de-debrised render, prior version in git), `out/featviz/stroke_cadpartA_dedebris_diff.png`
(kept in black, dropped fill in red, same camera and stroke settings), `out/dedebris.json`,
`scripts/dedebris.py`, `logs/dedebris_temporal.log`. Nothing committed.
