# VERIFY-F100 — does the f=1.00 lego operating point keep the temporal crown jewel?

**VERDICT: NO-GO.** The f=1.00 static domination is real and reproduced, but it does **not**
survive the temporal gate. The gain is **static-only**. Keep the shipped f=0.30.

Executes `tier1/verify_f100_spec.md`. Mesh EVAL-ONLY. No retrain, no re-pull, no re-tune, no
git commit. No shipped pipeline file, banked json, or published figure was modified
(§5). Protected temporal manifest **332/332 OK, 0 FAILED** before and after.

---

## 0. A design correction that had to be made first

The spec says "run the SAME path that produced the shipped lego P_pop 0.063 / Frechet 14.03x".
Grepping that path shows the shipped **temporal** cell and the shipped **P/R** cell come from
**different linelet sets**:

| shipped cell | source npz | `gate` | f | mask used | n |
|---|---|---|---|---|---|
| temporal (P_pop 0.063 / Frechet 14.03x) | `linelets_lego_ungated_test.npz` | **false** | 0.30 | `z["keep"]` (spec prune) | 25,870 |
| P/R (0.6196 / 0.2856) | `linelets_lego_gated_test.npz` | **true** | 0.30 | tuned+len | 20,142 |

`scripts/m1b_stroke_temporal.py:154` loads `linelets_{scene}_{variant}_test.npz` with
`--variant` defaulting to `ungated`, and `build_chains` uses `z["keep"]`. The f=1.00 CAP run is
`gate: true`. So feeding it straight against the shipped cell would confound **f** with
**gating**. A gate-matched f=0.30 control was therefore added, and both f=1.00 mask stages were
run, all through the identical code path with only `--tag` / `--viz_tag` differing.

---

## 1. Inputs — confirmed before running, not regenerated

`out/linelets_lego_cap_f1.00.npz` (13.8 MB, 2026-08-28), 99,721 rows:
`keep` TRUE = **75,326** (spec prune) · `keep_tuned` TRUE = **56,269** (tuned+len) ✔ matches
`out/m1b_lego_cap_f1.00.json` `n_keep` / `n_keep_tuned` exactly.

Two additive inputs were created (new names, nothing overwritten):
- `linelets_lego_capf100_test.npz` — symlink to the original; `keep` = 75,326.
- `linelets_lego_capf100t_test.npz` — derived, faithful to `run_m1b.py:344`
  (`seg_tuned = eval_segments(h, P1, t1, l_mod_t, keep=keep_t)`):
  `keep := keep_tuned` (56,269), `l := l_mod_tuned`, `inlier_ratio := inlier_ratio_tuned`.

## 2. Static P/R — the round-1 finding, reproduced at BOTH prune stages

Banked, held-out TEST, segments @1.5. Nothing here was recomputed.

| run | stage | n | P@1.5 | R@1.5 |
|---|---|---|---|---|
| f=0.30 gated (**SHIPPED row**) | tuned+len | 20,142 | 0.6196 | 0.2856 |
| **f=1.00** | tuned+len | 56,269 | **0.6360** | **0.5572** |
| f=0.30 gated | spec prune | 25,279 | 0.5826 | 0.4168 |
| **f=1.00** | spec prune | 75,326 | **0.5969** | **0.7860** |
| f=0.30 ungated (temporal source) | spec prune | 25,870 | 0.5628 | 0.4193 |

f=1.00 dominates on **both** axes at **both** stages. The static half of the round-1 claim stands.

## 3. Temporal — the newly computed cells (240-frame TEST orbit 5->15, identical warp + Canny)

| arm | linelets | -> NMS | strokes | OURS Frechet | OURS P_pop | BASE Frechet | BASE P_pop | Frechet ratio | P_pop ratio | strokes/frame |
|---|---|---|---|---|---|---|---|---|---|---|
| **SHIPPED** f=0.30 ungated | 25,870 | 14,302 | 1,897 | 0.0857 | **0.06256** | 1.2025 | 0.71907 | **14.03x** | **11.49x** | 1,122 |
| CONTROL f=0.30 gated | 25,279 | 13,998 | 1,895 | 0.0859 | 0.05942 | 1.2007 | 0.71883 | 13.98x | 12.10x | 1,119 |
| **TEST f=1.00 tuned+len** | 56,269 | 49,567 | 4,824 | 0.0567 | **0.25887** | 1.2010 | 0.71873 | 21.17x | **2.78x** | 3,033 |
| **TEST f=1.00 spec prune** | 75,326 | 39,143 | 5,532 | 0.0730 | **0.07344** | 1.2018 | 0.71906 | 16.46x | **9.79x** | 3,159 |

**Byte-comparability self-check (free, and it passes).** The Canny BASELINE is independent of the
linelets, so every arm re-derives it. Across all four arms BASE P_pop = 0.71907 / 0.71883 /
0.71873 / 0.71906 and BASE Frechet = 1.2025 / 1.2007 / 1.2010 / 1.2018 — agreement to 0.05% and
0.15%, i.e. the `render_gbuffer` CUDA-atomics nondeterminism floor. The path is the shipped path.

**The control validates the design.** Gate-matched f=0.30 reproduces the shipped cell
(13.98x / 12.10x, P_pop 0.05942 vs 0.06256): gating is not a confound, and it slightly *helps*.

## 4. Verdict against the FROZEN rule

Shipped reference: Frechet ratio 14.026x, P_pop ratio 11.494x, P_pop absolute 0.062558.
Frozen bars: Frechet >= **12.624x**, P_pop ratio >= **10.345x**, P_pop absolute <= **0.06881**.

| arm | Frechet ratio | P_pop ratio | P_pop absolute | verdict |
|---|---|---|---|---|
| CONTROL f=0.30 gated | 13.98x (99.7%) PASS | 12.10x (105.2%) PASS | 0.05942 (-5.0%) PASS | GO |
| **f=1.00 tuned+len** | 21.17x (150.9%) PASS | **2.78x (24.2%) FAIL** | **0.25887 (+313.8%) FAIL** | **NO-GO** |
| **f=1.00 spec prune** | 16.46x (117.4%) PASS | **9.79x (85.2%) FAIL** | **0.07344 (+17.4%) FAIL** | **NO-GO** |

**=> NO-GO on both f=1.00 arms. The f=1.00 gain is static-only. Keep the shipped f=0.30.**

## 5. Mechanism — it is FRAGMENTATION, not flicker

`P_pop = unmatched + cut` (verified: 0.0370+0.0256 = 0.0626 shipped; 0.0109+0.2480 = 0.2589
tuned; 0.0311+0.0424 = 0.0735 spec). Decomposed:

| arm | unmatched | cut (split/merge) | verts/stroke |
|---|---|---|---|
| SHIPPED f=0.30 ungated | 0.0370 | 0.0256 | 4.97 |
| f=1.00 spec prune | **0.0311** (better) | **0.0424** (+66%) | 4.77 |
| f=1.00 tuned+len | **0.0109** (much better) | **0.2480** (+869%) | 4.57 |

f=1.00 strokes **appear/disappear LESS** than the shipped ones — `unmatched` improves on both
arms, and the matched strokes are *steadier* (Frechet ratio rises to 16.5x / 21.2x). What breaks
is the **topological split/merge term**: nearly tripling the stroke population (1,122 -> 3,159)
into shorter chains multiplies cuts. This is the same mechanism `URS_E2E_RESULTS.md` recorded for
densification ("many more, shorter strokes, and more strokes pop").

The tuned+len arm is far worse than spec prune despite having *fewer* linelets, and the cause is
visible in the NMS column: `l_mod_tuned` shrinks lengths (min 1.54e-4 vs 6.16e-4), and the 3D NMS
radius is proportional to `l`, so 88% of linelets survive NMS (49,567/56,269) versus 52% at spec
prune (39,143/75,326) — the stroke graph is left far more fragmented (max verts/stroke 25 vs 63).
**Note this means the shipped pipeline's choice to run temporal on the SPEC mask is the right one.**

*Not a rescue, and not pursued:* the chaining knobs (`nms_mult`, `gap_mult`, `min_nodes`) were
tuned at the f=0.30 stroke density. Re-tuning them for a 3x denser carrier is a NEW tuning axis
that would need its own pre-registered gate; it cannot be claimed from this run.

## 6. Mandatory caveat — the 30.000-degree stud-tessellation family

lego P@1.5 is partly credited by the exactly-30.000 deg 12-gon stud tessellation, whose facet
edges sit ~3.2 px apart against a 1.5 px tau. From `out/LEGO_THRESHOLD_AUDIT.md` (f=1.00):

| GT threshold | GT crease px | R@1.5 | P@1.5 |
|---|---|---|---|
| **30.00 deg (frozen)** | 409,751 | 0.5572 | **0.6360** |
| 30.05 deg | 215,357 | 0.6408 | **0.3097** |
| 45.0 deg | 202,403 | 0.6467 | **0.3004** |

Precision halves once that family leaves the target set. This is a property of the **GT target
set**, so it applies **equally to both f values** and the domination comparison in §2 stays
internally valid — but the absolute lego numerals are asset-quantisation properties either way.
(The theta>=30.05 re-score is banked only for f=1.00; the f=0.30 equivalent is not on disk and
was not computed, since it cannot change a comparison that moves both arms together.)

## 7. Scope and invariants

- Only the **240-frame** cell was computed — that is where the frozen rule's reference numbers
  (0.063 / 14.03x) live. The 30/60/120 cells were not run.
- `Phi_pop` is **not applicable**: it is the arc-length-weighted metric of the linking gate
  (`out/link/`), not of `m1b_stroke_temporal.py`, which reports P_pop / unmatched / cut.
- Mesh EVAL-ONLY; no method-path file touched. No retrain, no re-pull, no re-tune.
- Protected manifest **332/332 OK, 0 FAILED** after the run. `out/m1b_stroke_temporal_table.{json,md}`
  and `out/m1b_vector_lego_{A_ours,B_baseline}.svg` unmodified (timestamps unchanged).
- New artifacts only: `out/m1b_stroke_temporal_table_vf100_{gate030,f100tune,f100spec}.{json,md}`,
  `out/m1b_vector_lego_vf100{g30,f100t,f100}_*.{svg,png}`,
  `out/linelets_lego_capf100{,t}_test.npz`, `logs/verify_f100.log`, this file.
- Not committed.

## 8. What this means for the round-1 section-6.1 claim

The claim "f=1.00 dominates the shipped lego operating point" is **half right and must be
restated**. It dominates on static P/R at both stages (§2). It does **not** dominate overall:
P_pop degrades +17.4% at best, and the P_pop ratio falls to 85% of shipped, below the 90% bar.

The paper's lego row stays **0.620 / 0.286** with P_pop 0.063 / 11.49x.

What survives, and is worth one honest sentence in the paper, is the weaker form: lego's shipped
recall 0.286 is an **operating-point choice inherited from chair-tuning**, not the carrier
ceiling (0.557) — and buying that recall back costs temporal coherence through stroke
fragmentation. That is a real recall/stability trade on lego, and it is now measured rather than
assumed.
