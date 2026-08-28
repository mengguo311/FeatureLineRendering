# NG-MEC — normal-gated multi-view epipolar consensus culling: **NO-GO** (all three criteria)

Scorer and thresholds frozen and committed at **`3ec17d5`, before any NG-MEC number existed**.
Carrier **not grown** — NG-MEC only removes proposals from the frozen `teed_native_0.5` set.
Mesh never imported in the gate/consensus/seed/pull/prune path. Held-out TEST only; `tau_n`
and `c_thr` swept on **chair VAL** and transferred to lego unchanged. All temporal/figure calls
used `--viz_tag ngmec_v1`. Protected manifest **332/332 OK before and after, 0 failures**.

## Verdict

| criterion | required | chair | lego | result |
|---|---|---|---|---|
| P@1.5 at R≥0.65 | ≥ 0.85 | **0.6815** (f=0.50, R=0.6612) | — | **FAIL** |
| R | ≥ 0.65 | 0.6612 ✓ reachable | **R_max 0.3722** — floor unreachable | **FAIL** |
| temporal regression vs `teed_native_0.5` | ≤ 5% at every frame | — | **worst −8.41%** | **FAIL** |

### CALL: NO-GO

## 1. The precision mechanism *does* work — on chair, and only on chair

Per the spec, P/R is reported even though temporal failed, so the mechanism can be judged on
its own. NG-MEC vs the `teed_native_0.5` reference at **matched f**, held-out TEST:

**chair — a real gain that grows with f, at essentially zero recall cost**

| f | points dP | points dR | segments dP | segments dR |
|---|---|---|---|---|
| 0.22 | +0.0044 | +0.0008 | +0.0050 | +0.0005 |
| 0.30 | +0.0071 | +0.0034 | +0.0077 | −0.0002 |
| 0.40 | +0.0114 | −0.0003 | +0.0121 | −0.0006 |
| 0.50 | **+0.0203** | +0.0033 | **+0.0273** | +0.0004 |
| **mean** | **+0.0108** | ~0 | **+0.0130** | ~0 |

**lego — nothing, and it costs recall**

| f | points dP | points dR | segments dP | segments dR |
|---|---|---|---|---|
| 0.22 | +0.0017 | −0.0052 | +0.0023 | −0.0084 |
| 0.30 | +0.0002 | −0.0100 | +0.0024 | −0.0155 |
| 0.40 | +0.0003 | −0.0130 | +0.0022 | −0.0178 |
| 0.50 | **−0.0007** | −0.0171 | +0.0019 | **−0.0234** |
| **mean** | **+0.0004** | −0.011 | **+0.0022** | −0.016 |

The consensus cull removes texture false positives on chair essentially for free, and the
benefit grows as f admits more marginal proposals. On lego it removes **real creases** —
recall falls monotonically with f while precision does not move. This is the Conditional Law
again: chair has a separable non-crease class to cull, lego does not.

## 2. The "normal-gated" half of NG-MEC is counterproductive

Chair-VAL sweep, f=0.40, vs the un-culled reference (`out/ngmec_sweep_chair_val.json`):

| tau_n | c_thr | survivors | points dP |
|---|---|---|---|
| **0.00** | **0.93** | 0.695 | **+0.0051** ← selected |
| 0.00 | 0.90 | 0.762 | +0.0032 |
| 0.20 | 0.93 | 0.676 | +0.0011 |
| 0.30 | 0.00 | 0.902 | −0.0201 |
| 0.40 | 0.00 | 0.768 | **−0.0621** |
| 0.40 | 0.93 | 0.519 | −0.0500 |

**Every `tau_n > 0` makes precision worse**, monotonically. Honest selection therefore turned
the normal gate **off** (`tau_n = 0`, culling exactly 0 proposals), leaving NG-MEC as a
consensus-only cull. Survivors at the selected point: chair 39 516/56 884 (69.5%), lego
77 066/99 721 (77.3%), all culled by consensus, none by the normal gate.

Why it fails: the frozen-3DGS normal at a genuine crease is itself ill-defined — a crease is
where the normal is *discontinuous*, so |n·v| there is arbitrary rather than large. The gate
was built on the premise that occluding contours have |n·v|≈0 while creases do not; the data
say creases are not reliably distinguishable from contours by that statistic on this carrier.

## 3. The recall floor is unreachable on lego by construction, not by tuning

lego's maximum recall **ever achieved**, at f=1.00 with *zero* culling:

| stage | lego max R | vs 0.65 |
|---|---|---|
| points / `[tuned]` | **0.4661** | **−0.1839** |
| segments / `[tuned+len]` | **0.5572** | **−0.0928** |

Both from `out/m1b_lego_cap_f1.00.json`. NG-MEC only *removes* seeds, so f=1.00 is its
absolute ceiling. An independent audit of the whole corpus confirms culling can never help:
**recall is monotone non-decreasing in `keep_frac` in 2989/2989 adjacent frontier pairs, zero
counterexamples** — every frontier point is a strict subset of the f=1.00 prune mask. The repo
already recorded this in `cap_spec.md:5-7`: *"Lego's full pool (f=1.0) yields only
R@1.5 = 0.5572, so R>=0.65 is UNREACHABLE by any re-ranking (ECO, veto, oracle)."*

On chair the floor **is** reachable (R_max 0.6612), but the precision there is 0.6815 against
a required 0.85 — a gap of **−0.169** that a +0.011 cull cannot close.

## 4. Temporal — a real cost, but far smaller than URS-E2E's

| frames | NG-MEC | baseline (`teed_native_0.5`) | relative |
|---|---|---|---|
| 30 | 3.52× | 3.49× | **+0.93%** |
| 60 | 5.28× | 5.48× | −3.73% |
| 120 | 8.11× | 8.69× | −6.70% |
| 240 | 11.09× | 12.10× | **−8.41%** |

Worst −8.41% against a 5% tolerance → **FAIL**, but note the contrast: URS-E2E's carrier
growth cost −15.7% to −37.6%. Culling on the frozen carrier is **~4× gentler** on temporal
coherence than growing it, and it is temporal-neutral at short horizons (+0.9% at 30 frames).
The regression grows with horizon, consistent with a slightly sparser stroke set drifting more
over long sequences.

## 5. Honest summary

Three independent failures, each for a different reason:

1. **chair precision** — the mechanism works but is an order of magnitude too small
   (+0.011 against a −0.169 gap).
2. **lego recall** — unreachable by construction; a culling operator cannot exceed the
   no-cull ceiling, which is 0.4661/0.5572 against a 0.65 floor.
3. **temporal** — −8.41% exceeds the 5% tolerance, though it is far gentler than densification.

What is genuinely new and worth keeping: **consensus culling buys free precision on chair**
(+0.0108 points / +0.0130 segments at matched f, ~zero recall cost, growing with f), and
**the normal gate is refuted** — every non-trivial `tau_n` hurt, so the "normal-gated" half of
the method should be dropped rather than retuned. That is a negative result about a specific
mechanism, measured rather than assumed.

This is the fifth independent NO-GO on lego's joint gate, and the recall half of it is now
proven impossible rather than merely unachieved.

## Invariants

| invariant | status |
|---|---|
| scorer + thresholds frozen before any NG-MEC number | held — `3ec17d5`, verified no `ngmec` artifact existed |
| mesh never in gate/consensus/seed/pull/prune path | held — `ngmec_build.py` imports no mesh |
| held-out TEST only; knobs tuned on chair VAL, never TEST | held — `out/ngmec_sweep_chair_val.json` |
| carrier NOT grown | held — cull only; survivors 69.5% chair / 77.3% lego |
| `--viz_tag ngmec_v1` on all temporal/figure calls | held — figures went to `m1b_vector_legongmec_v1_*`, published paths untouched |
| protected manifest 332/332 before **and** after | held — 332/332, 0 failures, both checks recorded in the verdict json |

**Artifacts.** `scripts/ngmec_{verdict,build,sweep}.py`; `out/ngmec_verdict.json`,
`out/ngmec_mechanism.json`, `out/ngmec_sweep_chair_val.json`, `out/ngmec_selected.json`,
`out/ngmec_build_{chair,lego}_ngmec_sel.json`, `out/ngmec_normalgate_{chair,lego}.npy`;
`out/m1b_{chair,lego}_ngmec_ngmec_f*.json`;
`out/m1b_stroke_temporal_table_ngmec_v1.json`; `logs/ngmec_*.log`.
