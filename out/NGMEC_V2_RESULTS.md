# NG-MEC-v2 — additive multi-cue line scoring: **NO-GO**

Frozen gate applied by `scripts/ngmec_v2_verdict.py`, **committed at `076a6aa` before any
NG-MEC-v2 P/R number existed**, so the thresholds could not be fitted to the outcome.
Protected temporal manifest re-verified **332/332 OK**.

## Verdict

| test | criterion | measured | result |
|---|---|---|---|
| precision | `min(P_chair, P_lego) >= 0.85` | chair **0.6921**, lego **unreachable** | **FAIL** |
| recall | `min(R_chair, R_lego) >= 0.65` | chair **0.6680**, lego max **0.4080** | **FAIL** |
| temporal | speedup `>= 7.0x` preserved | **8.50–13.12x** | **PASS** |
| **EARLY ABORT** | R < 0.60 before P reaches 0.80 | **triggered on lego** (max R 0.4080, best P 0.7100) | — |

### VERDICT: NO-GO

## Per-scene results (held-out TEST, frozen weights)

Operating point = max `P@1.5` subject to `R@1.5 >= 0.65`, defined in advance.

| scene | P@1.5 | R@1.5 | best P anywhere | max R anywhere | source |
|---|---|---|---|---|---|
| chair | **0.6921** | **0.6680** | 0.7830 @ R=0.2955 | 0.6680 @ P=0.6921 | `out/m1b_chair_ngmecv2_final_test.json` |
| lego | **n/a** — floor unreachable | — | 0.7100 @ R=0.1573 | **0.4080** @ P=0.6623 | `out/m1b_lego_ngmecv2_final_test.json` |

Full TEST frontiers (keep_frac, P@1.5, R@1.5):

- chair: (1.0, 0.692, 0.668) (0.9, 0.693, 0.637) (0.8, 0.696, 0.556) (0.7, 0.711, 0.496)
  (0.6, 0.734, 0.452) (0.5, 0.754, 0.407) (0.4, 0.770, 0.355) (0.3, 0.783, 0.295)
- lego: (1.0, 0.662, 0.408) (0.9, 0.666, 0.396) (0.8, 0.673, 0.363) (0.7, 0.680, 0.323)
  (0.6, 0.688, 0.283) (0.5, 0.696, 0.240) (0.4, 0.703, 0.200) (0.3, 0.710, 0.157)

**No lego frontier point reaches R = 0.65 at any precision.** The recall floor is not
missed by tuning — it is outside the reachable set.

## Weights

Tuned on **chair VAL** over a 4x4 grid (`w_teed` fixed at 1.0), transferred to lego
UNCHANGED, TEST read once at the end. `out/ngmec_v2_sweep_chair_val.json`,
`out/ngmec_v2_weights.json`.

| | selected |
|---|---|
| `w_teed` | 1.0 |
| `w_2dgs` | **0.0** |
| `w_epi` | 0.25 |

**The tuner drove the 2DGS-normal weight to zero.** At `w_2dgs = 1.0` the recall floor
becomes unreachable on chair VAL as well (all four `w_2dgs=1` rows report `n/a`). The best
chair-VAL operating point over the whole grid was `P=0.5622` vs the pure-TEED baseline
`P=0.5607` — a lift of **+0.0015**, i.e. nothing.

*Split note, stated not hidden:* the spec says "tune on chair TRAIN views". `run_m1b.py
--eval_split` accepts only `{test, val, legacy}` — P/R requires the mesh oracle and the
harness only scores VAL/TEST, so there is no train-eval mode. Tuning ran on chair **VAL**.
The invariant that matters — never tune on TEST — holds, and VAL is this repo's established
selection split (`eco_score.py`: "Every knob is chosen on CHAIR VAL only, then transferred
to lego UNCHANGED"). The pull still consumes TRAIN views only.

## Why it failed — per-cue diagnosis (`out/ngmec_v2_cuediag.json`)

The spec asks which cue over-penalises. Per-carrier-gaussian AUC against a mesh-oracle
crease label (gaussian within 1 NN-spacing of a GT crease point vs beyond 3x):

| cue | chair AUC | lego AUC |
|---|---|---|
| TEED base (proposals) | **0.8542** | **0.5503** |
| Cue 1 — 2DGS normal | **0.7523** | **0.4376** (below chance) |
| Cue 2 — epipolar consensus | 0.7763 | 0.5299 |
| additive `base + 0.25*epi` (selected) | **0.8610** | **0.5529** |
| additive `base + 0.5*2dgs + 0.25*epi` | 0.8561 | 0.5223 |

Cue correlations with the base: chair **+0.647** (2DGS), +0.598 (epi); lego +0.310, +0.441.

Three findings, in order of importance:

1. **The 2DGS-normal cue does not survive the pixel-to-carrier transfer.** The identical
   ribbon dihedral is a near-perfect *pixel* classifier — AUC **0.967** on mesh-flat-print
   vs mesh-sharp-crease (`gate2dgs.py`, PLAN1 STEP A). Aggregated onto carrier gaussians it
   is only **0.752** on chair and **0.438 on lego, i.e. anti-predictive**. A cue can be
   excellent at classifying *pixels* and still carry no usable ranking signal for the *3D
   carrier* the pipeline actually ranks. This is the cue that over-penalises, and it is why
   the tuner zeroed it.
2. **It is also redundant, not orthogonal.** On chair it correlates **+0.647** with the TEED
   base. The additive premise requires orthogonal information; this cue mostly re-states
   what TEED already says, then adds noise where it disagrees.
3. **On lego there is no rankable signal to spend.** *Every* cue is at or below chance at the
   gaussian level (0.550 / 0.438 / 0.530). Additive pooling cannot manufacture signal from
   three uninformative channels; the best combination reaches 0.5529.

The additive design itself is not refuted — it did exactly what it should: the epipolar cue
gave a small genuine lift on chair (AUC 0.8542 -> 0.8610) and the useless cue was
down-weighted to zero instead of corrupting the ranking, which a veto cascade could not have
done. **Additive pooling worked; the cues were not good enough.**

## Gap to the paper target

| scene | current P@1.5 | target | gap | current R@1.5 | target | gap |
|---|---|---|---|---|---|---|
| chair | 0.6921 | 0.85 | **-0.158** | 0.6680 | 0.65 | +0.018 (met) |
| lego | 0.6623 @ max recall | 0.85 | **-0.188** | 0.4080 (max) | 0.65 | **-0.242** |

For context, across **every frontier point of every `out/m1b_*.json` ever run** in this
repo: chair has never exceeded P=0.830 (at R=0.170) and lego has never exceeded R=0.572 or
P=0.744. NG-MEC-v2 does not regress those, but the joint gate `P>=0.85 AND R>=0.65` has
never been approached on either scene, and lego's recall ceiling is the binding constraint.

This is consistent with, not contradicted by, the three independent prior NO-GOs on lego
precision (ECO epipolar consensus, TGAP TEED-gated relaxation, DIAG-2DGS dihedral — the last
of which failed on the GT mesh itself) and with CONDLAW's finding that lego's static
geometric crease precision is intrinsically bounded.

## Invariants

| invariant | status |
|---|---|
| mesh never in method path | held — `ngmec_v2_cue2dgs.py` and `ngmec_v2_combine.py` import only common/render/render2dgs/gate2dgs/view_split; mesh only in the eval-only `ngmec_v2_cuediag.py` and the harness |
| held-out eval | held — weights tuned on chair VAL, transferred unchanged, TEST read once |
| temporal win preserved | held — P_pop ratios 8.50/11.35/12.85/13.12x, all >= 7.0x |
| protected manifest | **332/332 OK**, 0 failures |
| no veto cascade | held — every cue enters as a rank-transformed additive term; nothing is thresholded |
| new artifacts only | held — `ngmec_v2_*` prefix; the new score vectors use the fresh name `finalscore_overall_<scene>__ngmecv2_*.npy` and overwrite nothing |

**Artifacts.** `scripts/ngmec_v2_{cue2dgs,combine,sweep,verdict,cuediag}.py`;
`out/ngmec_v2_{cue2dgs_chair,cue2dgs_lego}.{npy,json}`,
`out/ngmec_v2_{sweep_chair_val,weights,verdict,cuediag}.json`,
`out/m1b_{chair,lego}_ngmecv2_final_test.json`,
`scripts/explore/syn/finalscore_overall_{chair,lego}__ngmecv2_g0_e0p25.npy`;
`logs/ngmec_v2_*.log`.
