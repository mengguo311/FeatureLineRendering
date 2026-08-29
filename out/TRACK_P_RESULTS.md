# Track P — temporal-win generalization across trajectories **and** scenes: **GO**

Scorer frozen and thresholds + code hashes written to `out/track_p_verdict.json`
**before any Track-P number existed** (`results_files_existing_at_freeze: NONE`, manifest
332/332 at freeze), and both hashes **re-verified UNCHANGED** at scoring time. No mesh is
imported anywhere in Track P — `scripts/track_p_temporal.py` is mesh-free and the scene centre
is the median gaussian position. Held-out TEST cams only. Protected manifest **332/332 OK,
0 failures, before and after**. No figure-writing call was made, so no `--viz_tag` collision
was possible.

## Verdict

| condition | E_warp A | E_warp B | **A/B** | median life A | median life B |
|---|---|---|---|---|---|
| chair · T1 orbit | 0.513 | 0.025 | **20.44×** | 0.0 | 239.0 |
| chair · T2 orbit+zoom | 0.540 | 0.025 | **21.62×** | 0.0 | 239.0 |
| chair · T3 spline | 0.480 | 0.074 | **6.49×** | 0.0 | 28.0 |
| lego · T1 orbit | 0.514 | 0.049 | **10.38×** | 0.0 | 117.0 |
| lego · T2 orbit+zoom | 0.537 | 0.051 | **10.61×** | 0.0 | 47.0 |
| lego · T3 spline | 0.543 | 0.160 | **3.38×** | 0.0 | 20.0 |

- **PRIMARY** worst-case E_warp ratio = **3.385** ≥ 2.0 → **PASS**
- **SECONDARY** worst-case median-lifetime ratio = **inf** ≥ 2.0 → **PASS** *(degenerate — see below)*
- **GUARD** no regression vs Track O → **PASS** (within 0.26%)

### CALL: **GO** — the object-space temporal win generalizes across both trajectories and scenes.

## The SECONDARY criterion passes trivially — say so plainly

**Arm A's median stroke lifetime is 0.0 in all six conditions.** More than half of per-frame
TEED strokes fail to survive even one frame transition, so the frozen ratio B/A is `+inf`
everywhere. It passes, but it carries **no discriminating information** — it cannot separate
the easy conditions from the hard ones, and quoting "infinite improvement" would be
meaningless. The survival curves below are the informative form and are what the paper should
use.

## Survival curves — P(stroke lifetime > K frames)

| condition | arm | K>2 | K>4 | K>8 | K>16 | K>32 | median | mean | n strokes |
|---|---|---|---|---|---|---|---|---|---|
| chair·T1 | A | 0.067 | 0.038 | 0.020 | 0.009 | 0.005 | 0.0 | 1.04 | 22 131 |
| | **B** | **0.858** | **0.841** | **0.821** | **0.803** | **0.773** | **239.0** | **176.9** | 604 |
| chair·T2 | A | 0.067 | 0.036 | 0.018 | 0.009 | 0.005 | 0.0 | 1.05 | 25 405 |
| | **B** | **0.951** | **0.931** | **0.903** | **0.875** | **0.833** | **239.0** | **182.6** | 534 |
| chair·T3 | A | 0.070 | 0.038 | 0.020 | 0.010 | 0.005 | 0.0 | 1.01 | 21 049 |
| | **B** | **0.910** | **0.879** | **0.836** | **0.695** | **0.444** | **28.0** | **97.5** | 967 |
| lego·T1 | A | 0.074 | 0.044 | 0.025 | 0.015 | 0.008 | 0.0 | 1.42 | 21 692 |
| | **B** | **0.925** | **0.907** | **0.883** | **0.839** | **0.774** | **117.0** | **115.9** | 1 893 |
| lego·T2 | A | 0.077 | 0.046 | 0.026 | 0.016 | 0.009 | 0.0 | 1.49 | 21 102 |
| | **B** | **0.864** | **0.846** | **0.798** | **0.732** | **0.609** | **47.0** | **81.3** | 2 014 |
| lego·T3 | A | 0.072 | 0.044 | 0.025 | 0.014 | 0.007 | 0.0 | 1.19 | 22 023 |
| | **B** | **0.808** | **0.764** | **0.710** | **0.604** | **0.295** | **20.0** | **37.0** | 1 518 |

The separation is the cleanest result in this track: **per-frame strokes essentially never
persist** (mean lifetime 1.0–1.5 frames, P(life>32) ≈ 0.005–0.009), while **object-space
strokes persist for tens to hundreds of frames** (mean 37–183, P(life>32) 0.29–0.83). The
large `n` gap is expected and not an artefact: arm A regenerates ~21–25 k short-lived strokes
over the sequence, arm B carries 534–2 014 long-lived ones.

## GUARD — no regression from the refactor

Track P's E_frechet ratio against Track O's independently-computed `frechet_mult_B` (chair,
240f):

| condition | Track P | Track O | relative |
|---|---|---|---|
| chair·T1 | 40.02 | 39.94 | +0.20% |
| chair·T2 | 42.52 | 42.60 | −0.19% |
| chair·T3 | 12.94 | 12.90 | +0.26% |

Agreement to within **0.26%** across a different aggregation path (Track P pools matched
strokes; Track O accumulates per-frame-pair medians). This is a genuine cross-check: two
independently written harnesses reproduce the same quantity, so neither the refactor nor the
new metric silently changed what is being measured.

## The honest scope — a 6× spread the headline must not hide

The win holds everywhere, but its magnitude is strongly condition-dependent:

| | orbit | orbit+zoom | spline |
|---|---|---|---|
| **chair** | 20.44× | 21.62× | 6.49× |
| **lego** | 10.38× | 10.61× | **3.38×** |

- **Trajectory dependence:** the multi-axis spline costs ~3× versus the smooth orbit on both
  scenes (chair 21.6→6.5, lego 10.6→3.4). Non-constant angular velocity is the hard case.
- **Scene dependence:** lego is ~2× weaker than chair in every trajectory — consistent with
  lego's micro-relief geometry producing shorter, more fragmentable strokes.
- **The worst case is the compound of both** (lego · spline, 3.38×), which is still comfortably
  above the 2.0 bar but **6.4× below the best condition**.

The defensible claim is therefore *"the object-space carrier is 3.4–21.6× more
warp-stable than per-frame detection, across two scenes and three trajectory families, with
the minimum on the hardest scene-motion combination"* — not a single headline multiplier.
Any single number quoted without the condition attached would overstate the result, and this
caveat applies to the previously published figures too, which were all measured on
chair · T1-like motion (the best-case cell of this table).

## Configuration

| | |
|---|---|
| arms | A = per-frame TEED (thr 0.5, NMS-thinned, same tracer as B) · B = unculled object-space TEED-seeded linelets. **No arm C** — culling abandoned, and Track O showed it degrades temporal. |
| linelet sets | chair `tcteed` (f=0.30, 1 137 strokes) · lego `tcteed040` (f=0.40, 1 893 strokes) — the published TEED arm for each scene |
| window | 240 frames, all conditions |
| trajectories | generators imported from `scripts/track_o_temporal.py`, look-at corrected, so every arm sees identical frames and T1 reproduces the published motion |
| E_warp | median matched chamfer displacement (px) over all frame transitions; warp is the exact depth+pose reprojection, not an estimated flow |
| survival | identity chained through `match_strokes`' `match_idx`; a stroke survives iff it warps (≥2 vertices) **and** matches within 3 px |

## Invariants

| invariant | status |
|---|---|
| scorer + thresholds + code hashes frozen before any number | held — `out/track_p_verdict.json`, `results_files_existing_at_freeze: NONE` |
| code unchanged since freeze | held — both sha256 re-verified at scoring time |
| mesh never in method path | held — no mesh import anywhere in Track P |
| held-out TEST cams only | held |
| never fabricate | held — every number read from `out/track_p_temporal.json` |
| temporal win protected | held — guard reproduces Track O within 0.26% |
| protected manifest 332/332 before and after | held — 0 failures both times |

**Artifacts.** `scripts/track_p_{temporal,verdict}.py`; `out/track_p_temporal.json`,
`out/track_p_verdict.json`, `out/track_p_smoke.json`; `logs/track_p.log`.
