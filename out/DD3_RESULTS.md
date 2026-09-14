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
| ratio vs per-frame Canny (fg_only=False, **warp-drop-inflated**: baseline drop 0.468) | 12.03x | **12.03x** |
| **ratio vs per-frame Canny, silhouette control (fg_only)** — `out/dd3_fgonly.json`, 2026-09-15 | — | **5.76x** (OURS P_pop 0.1122, cut 0.0012; BASE 0.6463, 76 fragments/frame) |
| join endpoints (no taper) | — | **8** |

> **CORRECTION (2026-09-15, HYGIENE item 5).** The 12.03x was run without the silhouette
> control the published lego/chair cells carry; 46.8 % of the Canny baseline's strokes are
> unwarpable silhouette strokes charged as pops. Re-scoring the byte-identical persisted
> carrier (`out/carrier_dd3_cadpartA.npz`) with `fg_only=True` gives **5.76x**. Both are
> stroke-identity ratios; ink-level churn on cadpartA is 6.82x (`boiltest.json`) and the
> consecutive-frame strip shows per-frame Canny complete and visually stable on cadpartA
> (`BOILTEST_RESULTS.md`). **No visible temporal superiority is claimed on this solid.**

Carrier and temporal are identical by construction, since Part A changed nothing and Part B is
rendering only.

**Mesh P/R of the dd3 carrier itself (added 2026-09-15, HYGIENE item 6; `out/dd3_meshpr.json`,
`scripts/dd3_meshpr.py`, `logs/dd3_meshpr.log`). MESH EVAL-ONLY, reported not gated.**
Until this date no P/R had been computed for merge70, dd2 or dd3; the two numbers quoted here
("DexiNed cloud P 0.7302 / R 0.8431, STEP3 zero-knob P 0.8139 / R 0.4206") were the P/R of the
INPUT carriers, and they are two different metrics: the 0.7302 / 0.8431 is the **DexiNed
triangulated point cloud** (`dexprimary_p1b_cadpartA_ref40.json`, subset `tri_sup1`, 220,255
points) scored as a **3-D point set at the px1.5-equivalent radius 0.004860**, not the dd3
carrier and not the segment metric; the 0.8139 / 0.4206 is the STEP3 zero-knob linelets scored
by **segment raster at 1.5 px on the 10 held-out TEST views**. The dd3 carrier (59 polylines,
442 edges, fields `pts/offs/open_end` — sufficient, since P/R needs only the 3-D geometry) is
now scored under BOTH conventions; each harness first reproduced its banked input number
exactly (0.8139 / 0.4206 and 0.7302 / 0.8431) before dd3 was scored.

| carrier | metric | P | R | notes |
|---|---|---|---|---|
| STEP3 zero-knob linelets (42-stroke trunk's input, 7,208 linelets) | segment raster @1.5 px, TEST macro | 0.8139 | 0.4206 | banked, reproduced |
| **dd3 carrier of record (59 strokes)** | **segment raster @1.5 px, TEST macro** | **0.8979** | **0.4520** | @2.5 px: 0.9067 / 0.4659; per-view P 0.73–0.98, R 0.31–0.52; edges subdivided to the trunk's median length (no-subdivision sensitivity 0.8961 / 0.4517) |
| DexiNed triangulated cloud, tri_sup1 (fill's input) | 3-D points @ radius 0.004860 | 0.7302 | 0.8431 | banked, reproduced; **NOT a dd3 number** |
| **dd3 carrier of record** | **3-D samples @ radius 0.004860** (spacing radius/5) | **0.9329** | **0.3202** | STEP3 zero-knob segments sampled the same way: 0.8948 / 0.3015 |

Reading, straight: the dd3 drawing is **more precise than the trunk it grew from** (0.898 vs
0.814 at 1.5 px; the dihedral gate and de-hairing removed unsupported content) and only
**modestly more complete in crease terms** (R 0.452 vs 0.421) even though it draws 1.54x the
trunk's arc — much of the added arc lands on creases the trunk already covered or beyond
1.5 px of any GT crease. It draws **under half of the visible GT crease pixels**. The DexiNed
cloud's R 0.843 is the coverage the *input* cloud has, not what the drawing achieves.

**Declared polyhedron-scope limit, restated.** The inherited min-length and straightness
filters, the 30 deg crease threshold, and the straightness leg above all bake a polyhedron
assumption into the renderer. Defensible for clean solids; none of it will survive ficus or
chair.

## 6. Files

`out/featviz/stroke_cadpartA_dd3_still.png`, `_dd3_strip.png`, `_dd3_diff_vs_dd2.png`, same
camera and parameters as every other carrier. `out/dd3.json` (includes `partA_per_stroke`,
`partA_leg_null`, `temporal_240`), `scripts/dd3.py`, `logs/dd3_temporal.log`. dd2 renders
untouched.
