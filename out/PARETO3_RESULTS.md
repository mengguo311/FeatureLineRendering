# PARETO-3 — disocclusion decomposition of the accumulated-baseline residual
# **FROZEN-GATE VERDICT: NO-GO — 33.3% < 40%. The residual is diffuse interior instability, not a disocclusion-correspondence limit. No mechanism sentence goes in the paper.**

Spec `tier1/pareto3_disocc_spec.md`. The hypothesis under test: the 1.72× pop advantage at
the PARETO-2 worst cell (lego × T3_spline, CANNY 50/150 @ α=0.85 vs OURS f=0.22) is a
STRUCTURAL disocclusion-correspondence limit that no 2D accumulation can bypass. The frozen
gate asked whether ≥60 % of the baseline's residual pop>2px pixels lie in disocclusion
regions. **They do not: 33.3 %.** Per the pre-registered NO-GO branch, the bounded temporal
claim stays purely empirical — the paper gets the measured numbers, not a causal story.

## Setup (all frozen before tallying)

- Operating point: lego, T3 spline, 240 frames; baseline = `CANNY 50/150 α=0.85`
  (oracle-flow EMA, occlusion-aware fallback; P 0.6360, 12,166 px/fr, pop>2px 0.05952);
  OURS = `f=0.22` — the unique row with P ≥ baseline (0.6364) and px ≤ baseline (10,521);
  advantage 0.05952/0.03462 = **1.719×**.
- ε (occlusion test) = 2 % of the median finite scene depth over the trajectory =
  **0.0754** (median depth 3.7685) — computed and printed before any tally.
- DISOCC pixel := its exact-rigid-flow warp lands off the eroded interior, on empty
  background, or behind the frame-(t+1) rendered depth by > ε. INTERIOR := everything else.
  Population = the identical pooled population PARETO-2 scored (in-frame warped line px).
- **Consistency check passed**: recomputed overall pop>2px = 0.05955 / 0.03457 vs the
  PARETO-2 json's 0.05952 / 0.03462 — same population, same operator, to the 4th decimal.
- No mesh anywhere in this analysis (disocclusion mask = rendered depth + poses only).

## The decomposition

| | baseline (Canny+EMA) | OURS |
|---|---|---|
| pooled warped line px | 2,914,371 | 2,515,085 |
| overall pop>2px | 0.0595 | 0.0346 |
| fraction of px in DISOCC regions | 6.60 % | 3.41 % |
| **fraction of POP pixels in DISOCC** | **33.3 %** ← the gate | 40.1 % |
| pop RATE inside DISOCC | 0.300 | 0.407 |
| pop RATE in INTERIOR | 0.0425 | 0.0214 |

## Honest reading — three findings, two of them against our own preferred story

1. **The gate fails because the mass is interior.** Two-thirds of the accumulated baseline's
   popping happens in ordinary interior pixels. The mechanism there is visible in the
   overlay (`out/pareto3_disocc_overlay.png`): diffuse EMA drift/lag over the whole body and
   baseplate under the spline's non-uniform motion — the accumulator's memory is slightly
   stale everywhere, not catastrophically wrong somewhere. The pre-registered causal
   sentence ("2D accumulation fails *at disocclusions*") is not supported at this cell and
   will not be written.
2. **Disocclusion regions are still 7.1× harder for the baseline** (rate 0.300 vs 0.0425) —
   but they are only 6.6 % of pixels, so a 7× rate cannot carry 60 % of the mass. This is
   reported as a rate observation, not smuggled in as the gated mechanism claim.
3. **OURS is *worse* than the baseline inside disocclusion regions** (rate 0.407 vs 0.300)
   — our visibility test splits chains at occlusion boundaries and the resulting run
   endpoints shift frame to frame. The entire 1.72× advantage is an **interior-stability
   advantage** (rate 0.0214 vs 0.0425 = 1.98× over the 93–97 % of pixels that are
   interior), partially offset by a disocclusion deficit. We report this first, before a
   reviewer finds it.

## What the paper says (per the frozen NO-GO branch)

The bounded empirical claim from PARETO-2 stands unchanged and un-narrated: at matched
precision and density, OURS' pooled pop advantage is ≥1.72× at the single adversarial worst
cell (lego × spline vs the oracle-flow EMA ceiling) and ≥3× at every other shared point,
with the ≥9.8×-vs-memoryless result intact. No disocclusion-mechanism sentence. The
per-region rates above may appear in an analysis appendix as measurements, with finding 3
included.

## Caveats

- One operating point, per the frozen spec — the decomposition characterizes the worst
  cell, not the whole frontier.
- ε sensitivity untested (frozen a priori; a looser ε moves px from INTERIOR to DISOCC and
  could shift the 33 % upward — that test was not in the spec and was not run post hoc).
- The occlusion-aware EMA fallback (locally α=0 where memory is untrusted) already removes
  the grossest disocclusion ghosting from the baseline; a naive EMA would look worse at
  disocclusions — our baseline's strength is exactly why the residual is interior-dominated.

Artifacts: `scripts/pareto3_disocc.py`, `out/pareto3_lego_T3_disocc.json`,
`out/pareto3_disocc_overlay.png`, `logs/pareto3.log`. Nothing committed (per instruction).
