# SHIP-PREP MILESTONE 1 — lego threshold-robustness audit

**VERDICT: SURVIVE.** lego's coverage-ceiling conclusion holds at every threshold in the frozen
sweep {30.00, 30.05, 31.0, 45.0}°, and it holds for a stronger reason than expected: raising the
threshold does not make the pipeline better, it deletes the part of the target it was failing.
Recall rises, **precision falls about twice as fast**, F1 is flat-to-down, and the frozen joint
operating gate `P@1.5 ≥ 0.85 ∧ R@1.5 ≥ 0.65` is **never met at any threshold on either scene** —
and gets *further* away as the threshold rises. The `ρ_B2 < 0.30` gate in `out/CAP_RESULTS.md`
also holds at every threshold — including its most adverse visible-only reading, which never
crosses 0.30 (§2b). **Figures are cleared to ship**, subject to the two disclosures in §5.

Script: `scripts/xy_thresh_audit.py`. Results: `out/xy/xy_thresh_audit.json`,
`out/xy/xy_thresh_audit_ext.json`. No GPU was needed for stages 1–2; stage 3 used one small
G-buffer pass per scene on `CUDA_VISIBLE_DEVICES=1`. Mesh EVAL-ONLY. No commits.

---

## 0. Reproduction control — the re-score is exact

Before any sweep, the audit reproduces every committed number it is about to move, from the
frozen inputs (`out/linelets_{lego,chair}_cap_f1.00.npz`, the same rasteriser, the same τ):

| committed value | source | audit recompute at 30.0° |
|---|---|---|
| lego R@1.5 = **0.5572** | `out/CAP_RESULTS.md` §1 | **0.5572** ✔ |
| chair R@1.5 = **0.7908** | `out/CAP_RESULTS.md` §1 | **0.7908** ✔ |
| lego ρ_B2 = **0.0799** (spec-literal) | `out/CAP_RESULTS.md` verdict | **0.0799** ✔ |
| lego ρ_B2 = **0.0483** (B0 folded) | `out/CAP_RESULTS.md` verdict | **0.0483** ✔ |

Exact on all four. The sweep below is therefore a statement about the threshold, not about a
re-implementation.

## 1. Why this audit exists

`src/mesh_oracle.py:24` defines the GT crease set as `face_adjacency_angles >= deg2rad(30)`.
lego's mesh carries **one** family of ~213,711 edges at exactly 30.000°, which that threshold
splits ~52/48: **110,655** fall in `[29.95, 30.00)` and are excluded, **103,056** in
`[30.00, 30.05)` and are included. The median deviation inside the band is **3.19e-3°** — not a
real spread of angles but the .obj's 6-decimal vertex quantisation. So for roughly half of lego,
membership in the ground-truth target set is decided by coordinate rounding in the asset file.
Every mesh-scored cache on disk is `a30` (`cache/oracle_{chair,lego}_a30_v*.npz`,
`cache/dexp0_gt_{chair,lego}_a30.npz`), so **every mesh-scored number in the paper is a 30.0°
number.** chair has no such family (238 edges at 30.000°, 0.1% of its crease set).

## 2. The committed 2D pixel recall R@1.5 vs threshold (the number the paper ships)

Coverage ceiling at f=1.00 (keep every gaussian), held-out TEST, mean over the 10 TEST views.
This is the quantity behind "re-ranking the frozen pool caps pipeline recall at R@1.5 = …".

**lego**

| threshold | GT crease px | **R@1.5** | **P@1.5** | ρ_B2 | joint gate `P≥0.85 ∧ R≥0.65` |
|---|---|---|---|---|---|
| **30.00° (frozen)** | 409,751 | **0.5572** | **0.6360** | 0.0799 | **not met** |
| 30.05° | 215,357 | 0.6408 | 0.3097 | 0.0617 | **not met** |
| 31.0° | 212,750 | 0.6435 | 0.3091 | 0.0623 | **not met** |
| 45.0° | 202,403 | 0.6467 | 0.3004 | 0.0625 | **not met** |

**chair**

| threshold | GT crease px | **R@1.5** | **P@1.5** | ρ_B2 | joint gate |
|---|---|---|---|---|---|
| **30.00° (frozen)** | 120,655 | **0.7908** | 0.3606 | 0.0684 | **not met** |
| 30.05° | 120,473 | 0.7905 | 0.3601 | 0.0684 | **not met** |
| 31.0° | 118,573 | 0.7887 | 0.3570 | 0.0692 | **not met** |
| 45.0° | 88,039 | 0.7737 | 0.2935 | 0.0564 | **not met** |

**The whole lego effect is the first 0.05°** (0.5572 → 0.6408, +0.084 absolute, +15% relative),
after which it plateaus — exactly the signature of one coherent 30.000° family leaving the target
set. **chair is flat** (0.7908 → 0.7905 → 0.7887), confirming the effect is a lego asset property,
not a property of the metric or the method.

## 2b. The frozen ρ_B2 carrier gate, including its most adverse reading

`out/CAP_RESULTS.md`'s actual decision gate is `ρ_B2 < 0.30` → "KEEP the 3D carrier; do NOT pivot
to image-space candidate injection". It is reported there in three readings, of which the
visible-gaussians-only arm is the adverse one — 0.2934 on lego, "comes closest to the gate without
crossing it". That arm is the real gate-crossing risk, so it is swept too:

| threshold | lego ρ_B2 (spec-literal) | **lego ρ_B2 (visible-only)** | crosses 0.30? | chair (visible-only) |
|---|---|---|---|---|
| **30.00° (frozen)** | 0.0799 | **0.2934** | no | 0.3308 |
| 30.05° | 0.0617 | **0.2925** | no | 0.3308 |
| 31.0° | 0.0623 | **0.2946** | no | 0.3301 |
| 45.0° | 0.0625 | **0.2946** | no | 0.3263 |

**lego's most adverse reading never crosses the gate, and barely moves at all** — the full range
across a 15° threshold change is 0.2925–0.2946, a spread of 0.002, because ρ_B2 is a ratio of
miss-classes that scale together. Unlike recall, this gate is intrinsically threshold-stable. The
CAP verdict is therefore robust. (chair sits above 0.30 in this arm at every threshold, which is
already disclosed in `out/CAP_RESULTS.md` — chair is the reference scene, not the gated one.)

*Reproduction note:* lego's visible-only value reproduces the committed 0.2934 exactly; chair's
recomputes to 0.3308 against a committed 0.3311 (Δ 0.0003, same side of the gate, conclusion
unchanged). Every other control in §0 is exact.

## 3. The recall rise is a target-deletion artifact, not a capability change

This is the load-bearing observation. Raising the threshold removes 47% of lego's crease pixels —
disproportionately the ones the pipeline was missing — so recall rises. But the rasterised
segments do not move, so the same strokes now land off a smaller target and **precision collapses
0.6360 → 0.3004**. Net effect on 3D F1 (stage 2, `out/xy/xy_thresh_audit.json`):

| lego | 30.00° | 30.05° | 31.0° | 45.0° |
|---|---|---|---|---|
| 3D recall | 0.2112 | 0.2928 | 0.2942 | 0.2962 |
| 3D precision | 0.1816 | 0.1432 | 0.1430 | 0.1370 |
| **3D F1** | **0.1953** | 0.1923 | 0.1924 | **0.1873** |

F1 is flat-to-declining at every threshold, on both scenes (chair: 0.2634 → 0.2200 at 45°). **No
threshold in the sweep makes the pipeline look better; the joint gate moves monotonically further
out of reach.** That is why the ceiling conclusion survives.

## 4. The frozen SURVIVE/FLIP rule, applied

| SURVIVE criterion | evidence | met? |
|---|---|---|
| coverage-ceiling conclusion holds at EVERY swept threshold | max lego R@1.5 = 0.6467 < 0.65; ≥ 35% of crease pixels unreachable by *any* re-ranking at every threshold | ✔ |
| recall stays materially below the `P@1.5 ≥ 0.85` gate | joint gate never met on either scene at any threshold; distance to P = 0.85 grows 0.214 → 0.550 on lego | ✔ |
| pool-caps-recall / decal-wall narrative does not reverse | ρ_B2 = 0.0799 → 0.0617/0.0623/0.0625, all far below the 0.30 gate; the *most adverse* visible-only reading stays at 0.2925–0.2946, never crossing 0.30 (§2b); CAP's "KEEP the 3D carrier" verdict holds at every threshold | ✔ |

**→ SURVIVE.** Proceed to the crown-jewel figure set.

## 5. Two disclosures that must ship with it

**(a) lego's ceiling number is threshold-fragile and the paper must say so.** A +0.05° nudge —
below the precision at which the asset stores its own vertices — moves lego R@1.5 from 0.5572 to
0.6408. The number is correct at the stated 30° definition, but it is not a robust property of
the object, and a reviewer with `trimesh` reproduces this in an hour. chair is unaffected.

**(b) The sentence "R ≥ 0.65 is unreachable by ANY ranking method" must not ship in that form.**
It lives in `scripts/cap_miss_attribution.py:10-11` and is **already false outside the frozen
sweep**. Extension run (`out/xy/xy_thresh_audit_ext.json`, explicitly *outside* the pre-registered
sweep and reported for honesty, not used in the verdict):

| lego | 45.0° | 60.0° | 80.0° | 89.0° |
|---|---|---|---|---|
| R@1.5 | 0.6467 | **0.6650** | **0.6716** | 0.6705 |
| P@1.5 | 0.3004 | 0.2823 | 0.2774 | 0.2580 |

R crosses 0.65 at ≥60°. The *conclusion* is untouched — recall plateaus near 0.67, a third of
crease pixels stay unreachable, and precision keeps falling so the joint gate is never approached
— but the specific numeric phrasing is not defensible. Good news: that sentence is a script
docstring and **was never propagated into shippable prose**.

## 6. The crown jewel is mesh-free and CANNOT move — verified, not asserted

The 7–13× temporal result is immune to everything above, because the metric never reads the mesh.
Verified two independent ways:

1. **Static.** The transitive import closure of `scripts/m1b_stroke_temporal.py` is 12 modules
   (`temporal_m1b`, `src/{common, linelet, lines_image, render, render2dgs, stroke_metric,
   strokes, view_split, visibility}`). Not one contains an import of `mesh_oracle` or `trimesh`.
   Every textual occurrence of "mesh_oracle" in the closure is a docstring *prohibition*
   (`src/common.py:2`, `src/linelet.py:4`, `src/strokes.py:3`, `src/render2dgs.py:3`,
   `scripts/temporal_m1b.py:3`). The orbit's scene centre is `np.median(g["mu"][keep_g], axis=0)`
   — gaussian-derived (`scripts/temporal_m1b.py:73-96`).
2. **Runtime.** Importing the whole temporal stack loads 1,202 modules and neither `mesh_oracle`
   nor `trimesh` is among them.

One command a skeptical reviewer can run, from `tier1/`:

```
python -c "import sys;sys.path[:0]=['.','scripts'];import m1b_stroke_temporal;\
print([m for m in sys.modules if 'mesh_oracle' in m or m.startswith('trimesh')] or 'MESH-FREE')"
```
→ `MESH-FREE`. **P_pop and Fréchet cannot move with the oracle threshold, at any value.**

## 7. Committed files patched

| file | change |
|---|---|
| `out/RESULTS_MASTER.md` | added a threshold-sensitivity note beside the ceiling row. **No banked numeral altered.** |
| `out/PAPER_DRAFT.md` | added the same note in §5 beside the ceiling sentence. **No banked numeral altered.** |

Both edits are purely additive (`git diff --stat`: 27 insertions, 0 deletions). The drift asserts
in `scripts/render_figs.py:50,59` read `out/cap_miss_attribution_*.json` and
`out/dexprimary_p0_*.json`, neither of which was touched, so `("lego", 0.5572)` and `0.3663`
still pass.

**Not patched, and why.** `paper/body_main.tex:320,458,494` and `paper/abstract.tex` carry the
same numbers; the spec scoped this milestone to the two .md ledgers, and the LaTeX is under the
orchestrator's assembly gate. `scripts/render_figs.py:50,59` hardcodes drift asserts
`("lego", 0.5572)` and `0.3663`; both **still pass**, because no banked number changed.

> ⚠ **The 304/304 md→PDF numeral pin is now stale.** `out/LATEX_ASSEMBLY_CHECK.md` records a
> frozen multiset of 304 occurrences / 133 distinct numerals between `out/PAPER_DRAFT.md` and
> `main.pdf`. The note added to `PAPER_DRAFT.md` introduces numerals not yet in the LaTeX, so the
> gate will report them as *lost* until the tex is re-synced with `scripts/phase1h_md2tex.py` and
> the conservation check is re-run. This is a known, intended consequence of the SURVIVE branch's
> "patch the propagated numbers honestly" instruction — flagged here rather than left to surprise
> the assembly gate.

## 8. Most-exposed sentence, for the figure pass

`out/SEC5_DRAFT.md:10-13` (= `out/PAPER_DRAFT.md:381`, `paper/body_main.tex:322`):
*"the binding form of the ceiling is lego's, where 0.3663 of visible GT crease points have no
carrier within 1.5 px at all"*. Act 1 is deliberately anchored on lego, and 0.3663 is
`1 − coverage` over the 30° crease set — the most threshold-sensitive quantity that actually
ships. It is correct at 30° and the ceiling conclusion survives, but if any single sentence gets
the sensitivity footnote, it is this one.
