# DE-DEBRIS v2 — cross-stroke dihedral gate. RESULTS

Executes `out/DEDEBRIS_V2_SPEC.md`, frozen before the run. Trunk byte-identical throughout.
**MESH EVAL-ONLY**: faint GT crease overlay only.

---

## VERDICT: NO-GO under the frozen conjunction — but the discriminator worked as argued

| pre-registered leg | result |
|---|---|
| (1) **all three named features survive** | **PASS** |
| (2) wavy front stroke AND mid-face stubs gone | **FAIL** — the wavy stroke survives |
| (3) cut <= 0.0102 | **PASS**, cut 0.0001 |

The gate is required to pass all three, so the verdict is NO-GO. **But this is not v1's
failure.** The a-priori argument held: a test of *what the stroke sits on* keeps weak-evidence
content that a strength test destroyed. The one survivor is survivable for a reason the
support concept cannot address, diagnosed in section 3.

## 1. Which of the three named features survived — explicitly

Read from `dd2_diff_vs_step3.png`, trunk in black, kept fill in **green**:

| named feature | v1 (strength gate) | **v2 (dihedral gate)** |
|---|---|---|
| **ledge line**, left corner running right | dropped | **SURVIVED** (green) |
| **top-hole edges**, dashes round the inner hexagon | dropped | **SURVIVED** (green, both arcs) |
| **right-face verticals** | dropped | **SURVIVED** (green, four of them) |

**Three of three.** v1 dropped three of three.

## 2. The arms side by side

| arm | strokes | fill kept | drawn arc | vs trunk | P_pop | **cut** | ratio |
|---|---|---|---|---|---|---|---|
| STEP3 trunk | 42 | — | 9.634 | 1.00x | 0.0771 | 0.0002 | 10.50x |
| merge70 (current best) | 70 | 28/28 | 18.299 | 1.90x | 0.0910 | 0.0001 | 8.89x |
| de-debris v1 | 50 | 8/28 | 11.797 | 1.22x | 0.0743 | 0.0001 | 10.90x |
| **de-debris v2** | **59** | **17/28** | **14.870** | **1.54x** | **0.0673** | **0.0001** | **12.03x** |

v2 keeps **17 of 28** fill strokes against v1's 8, retains **1.54x** the trunk's arc against
v1's 1.22x, and posts the **best temporal ratio of any arm built so far**, 12.03x, with cut at
0.0001. Median cross-stroke dihedral over all fill vertices measured **37.49 deg**, comfortably
above the 30 deg threshold, which is direct confirmation that most of the fill really does sit
on dihedral creases rather than on flat faces.

## 3. Why the wavy stroke survived, and why no support test can remove it

It sits on a **real dihedral**. It is a wobbly second trace of the chamfer edge the trunk
already draws cleanly, running a few pixels below it, and the 3 px gap filter did not suppress
it because it is further than 3 px from the trunk polyline. So it has genuine geometric support
and correctly passes a support test.

**That reclassifies it.** It is not debris in the "line drawn where no edge exists" sense that
motivated this step. It is a **redundant, low-quality duplicate** of a line already drawn.
No support test of any threshold will remove it, because the premise of the test is exactly
what it satisfies. Removing it needs a different discriminator: proximity-to-existing-stroke at
a larger radius, or a stroke-quality test on curvature, since a true crease on a polyhedron is
straight and this one visibly is not.

**I have not applied either.** Picking a new test after seeing which stroke survived is the
retro-fitting this campaign refuses, and it would need its own a-priori argument and
pre-registration.

## 4. Recommendation

**Keep the 70-stroke merge as the current best carrier**, per the standing decision, OR adopt
v2 if you judge the trade acceptable: v2 gives up 0.36x of arc against merge70 while removing
11 genuinely unsupported fill strokes and improving the temporal ratio from 8.89x to 12.03x.
That is a judgement about the picture, which is yours. My reading is that v2 is the better
drawing and merge70 is the more complete one.

## 5. Reported, not gated

Mesh P/R unchanged and unused as a gate: DexiNed cloud P 0.7302 / R 0.8431, STEP3 zero-knob
P 0.8139 / R 0.4206. Stroke count 59, median vertices 5, arc 14.870.

**Declared polyhedron-scope limit, restated.** The inherited min-length and RANSAC straightness
filters, and now the 30 deg crease threshold, bake a polyhedron assumption into the renderer.
Defensible for clean solids; none of it will survive contact with ficus or chair.

## 6. Files

`out/featviz/stroke_cadpartA_dd2_still.png`, `_dd2_strip.png`,
`_dd2_diff_vs_merge70.png` (kept black, dropped fill red),
`_dd2_diff_vs_step3.png` (trunk black, kept fill green). Same camera and stroke settings as
every other carrier. `out/dedebris2.json`, `scripts/dedebris2.py`,
`logs/dedebris2_temporal.log`. The merge70 renders are untouched. Nothing committed.
