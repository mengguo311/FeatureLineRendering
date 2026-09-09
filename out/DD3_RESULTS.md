# dd3 — dd2 adopted as carrier of record; Part A dedup (null-controlled); Part B stroke polish

Executes `out/dd3_spec.md`. Object space only, no per-scene tuning. **MESH EVAL-ONLY**: faint
GT crease overlay only. Nothing committed.

---

## VERDICT: NO-GO on the pre-registered gate, but the roll-back trigger did NOT fire

| gate clause | result |
|---|---|
| as complete as dd2 | **PASS** (carrier identical, arc 14.870 = dd2's) |
| visibly cleaner, **wavy duplicate gone** | **FAIL** — Part A applied nothing, the stroke remains |
| no real crease lost | **PASS** |
| sharp corners | **PASS** |
| strip as stable as dd2, cut within +0.01 | **PASS** (cut 0.0001, identical) |

The gate requires all clauses, so NO-GO. But the spec's roll-back condition is *"roll back if any
real edge is lost or the strip flickers more"*, and **neither happened**. Part B's rendering is
therefore safe to keep on the dd2 carrier; Part A simply contributed nothing.

## 1. Part A — the rule is INERT, and the null says so is not the reason

| | real trunk | rotated-trunk null (5 draws) |
|---|---|---|
| strokes dropped by the AND rule | **0 of 17** | **0, 0, 0, 0, 0** |

Reported and **not applied**, per the spec.

**Why it is inert, measured per leg:**

| leg | threshold | strokes meeting it | extremum seen |
|---|---|---|---|
| REDUNDANT: >= 0.5 of length within 7.8 px of a trunk stroke | F = 0.50 | **3 of 17** | max fraction 0.750 |
| BENT: max perpendicular residual > 2.5 px | 2.5 px | **1 of 17** | max residual 5.14 px |
| **AND of both** | — | **0 of 17** | intersection empty |

Both legs fire on their own. **The intersection is empty: on this carrier the redundant strokes
are straight and the one bent stroke is not redundant.** Neither constant is mis-set; the
conjunction simply does not describe anything present.

**The per-leg null is the informative control.** The AND-null cannot discriminate a rule that
never fires, so I ran the null on the redundancy leg alone: **3 of 17 against the real trunk,
0 of 17 on all five rotated-trunk draws**. The proximity signal is genuinely registration-based,
not a density artefact. The leg is selective; it just never co-occurs with bentness here.

## 2. A correction to my own dd2 write-up

In `DEDEBRIS_V2_RESULTS.md` I wrote that the wavy stroke is *"a wobbly second trace of the
chamfer edge the trunk already draws cleanly, running a few pixels below it"*. **Measured, that
is wrong.** Its redundancy fraction is below the 0.5 bar, so over most of its length it sits
more than three stroke widths from any trunk stroke. It is **a bent stroke on its own path, not
a near-duplicate**. My dd2 diagnosis was an eyeball inference and this run falsifies it.

That also explains why a duplicate-removal rule was never going to catch it.

## 3. Available but deliberately NOT adopted

The **bent leg alone** removes exactly one stroke, at residual 5.14 px against the 2.5 px bar,
and that stroke is the wavy one. Adopting it now would be choosing a rule after seeing which
stroke it kills, which is precisely what the spec forbade ("NOT chosen to kill one stroke") and
what this campaign has refused throughout. It is a clean candidate for its own pre-registration,
with its own null control, in a next step.

## 4. Part B — stroke polish, applied

Constant screen-space width, taper only at **true open endpoints**, never at joins, corners
left sharp by piecewise-linear rendering with no smoothing anywhere.

The join test is object-space and computed once: an endpoint is a **join** iff the 3-D endpoint
snap moved it onto a shared centroid. **8 join endpoints** were identified and rendered with a
flat cap; every other end tapers, including ends created by occlusion, where the line correctly
fades as it wraps behind the object.

Visually the strokes now hold uniform weight along their length and the hex corners and chamfer
junctions read as crisp mitres rather than thinning out.

## 5. Numbers

| | dd2 | **dd3** |
|---|---|---|
| strokes | 59 (42 trunk + 17 fill) | **59 (42 + 17)** |
| drawn arc | 14.870 | **14.870** |
| arc vs trunk-only (9.634) | 1.54x | **1.54x** |
| P_pop | 0.0673 | **0.0673** |
| unmatched | 0.0672 | 0.0672 |
| **cut** | 0.0001 | **0.0001** |
| ratio vs per-frame Canny | 12.03x | **12.03x** |
| join endpoints (no taper) | — | **8** |

Carrier and temporal are identical by construction, since Part A changed nothing and Part B is
rendering only. Reported not gated: mesh P/R unchanged, DexiNed cloud P 0.7302 / R 0.8431,
STEP3 zero-knob P 0.8139 / R 0.4206.

**Declared polyhedron-scope limit, restated.** The inherited min-length and straightness
filters, the 30 deg crease threshold, and the straightness leg above all bake a polyhedron
assumption into the renderer. Defensible for clean solids; none of it will survive ficus or
chair.

## 6. Files

`out/featviz/stroke_cadpartA_dd3_still.png`, `_dd3_strip.png`, `_dd3_diff_vs_dd2.png`, same
camera and parameters as every other carrier. `out/dd3.json` (includes `partA_per_stroke`,
`partA_leg_null`, `temporal_240`), `scripts/dd3.py`, `logs/dd3_temporal.log`. dd2 renders
untouched.
