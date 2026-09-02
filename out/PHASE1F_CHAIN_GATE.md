# PHASE 1f — chain-level gating diagnostic on the CACHED Phase-1e oracle
# **VERDICT: STRUCTURAL — chain pooling repairs only part of the severing (0.6372 → 0.7481) and the chain topology itself caps the guard at 0.8782 < 0.90; post-hoc thresholding cannot preserve 1D crease continuity even with a perfect ranking**

Spec `tier1/phase1f_spec.md`. APPENDIX-HARDENING DIAGNOSTIC ONLY — path B stays a
PERMANENT NO-GO (Phase 1e, appendix committed at `54454cb`); neither fork branch reopens
it; path-C camera-ready ships unchanged. CHEAP + **CPU-only** (g-buffers rendered with
`render_gbuffer(device='cpu')`, deterministic; no GPU touched, no pipeline restart, NO
new scoring, NO refitting, mesh-free arms NOT re-evaluated). All new files
(`out/phase1f_*`, `scripts/phase1f_chain_gate.py`); banked numbers only quoted. Every
number below is read from a named result file.

---

## Setup (cached artifacts only)

- **Scores**: the Phase-1e in-scene mesh-ORACLE per-point probabilities, loaded verbatim
  from `out/phase1e_scores_chair.npz` (key `oracle`; in-sample AUC 0.9578 — the loosest
  upper bound, labelled as in Phase 1e). Nothing refit.
- **Chains**: the cached P1c/P1d chain components over the SAME 272,366-pt chair ref40
  cloud — `out/dexp1d_feats_chair.npz` key `chain` (3D proximity r=0.005 +
  direction-coherence |cos|≥0.6, min 10 pts): **1,692 chains covering 156,979 points
  (57.64% of the cloud)**, sizes min 10 / median 21 / max 20,349. Row order verified
  bit-identical between the two npz files (`P` arrays equal). (The spec's mention of
  `linelets_chair_p1e_valref.npz` is the topology-guard baseline strokes, used exactly as
  in Phase 1e; the M1b linelets are a different point set and cannot carry the cloud's
  oracle scores.)
- **Gating**: pooled chain score = mean oracle prob over member points (PRIMARY);
  median-pooled as the spec's robustness arm. Keep whole chains with pool ≥ tau;
  unchained points (42.36%) are dropped by any tau. tau grid = ALL 1,692 distinct pooled
  scores (exact, no quantile approximation).
- **Protocol**: identical to Phase 1e — tau on VAL {0,10,…,90} ONLY (argmax VAL P@1.5
  s.t. VAL R@1.5 ≥ baseline VAL 0.6307 from `out/m1b_chair_p1e_valref.json`), frozen to
  `out/phase1f_val_freeze.json`, TEST {5,15,…,95} evaluated exactly once
  (`out/phase1f_test_eval.json`). Metric = the LITERAL `run_m1b` macro segment-raster
  path (fast sweep re-verified mask-identical on all 10 VAL views + value-identical at 3
  spot taus per arm incl. grid ends). Topology guard = the identical Phase-1e definition
  (GT crease 8-conn segments per TEST view, chamfer-DT ≤ 1.5px, denominator =
  baseline-stroke-covered segments, strokes from `out/linelets_chair_p1e_valref.npz`).

## Results — tau frozen on VAL, ONE-SHOT TEST

Sources: `out/phase1f_val_freeze.json`, `out/phase1f_test_eval.json`; quoted rows from
`out/phase1e_test_eval.json` (cached, not re-run) and `out/m1b_chair_gated_test.json`.

| arm | frozen tau (VAL) | kept | VAL P@1.5 / R@1.5 | **TEST P@1.5** | **TEST R@1.5** | TEST P/R@2.5 | **topology guard** |
|---|---|---|---|---|---|---|---|
| banked baseline (QUOTED) | — | 15,091 strokes | 0.5750 / 0.6307 | 0.6573 | 0.5959 | 0.7777 / 0.6719 | (denominator) |
| **Phase-1e point-oracle (QUOTED, cached)** | 0.61508 | 46,160 pts | 0.6222 / 0.6330 | **0.7970** | 0.6337 | 0.8901 / 0.7235 | **0.6372** |
| **chain_mean (PRIMARY)** | 0.18096 | 658 chains / 78,190 pts | 0.4646 / 0.6309 | **0.6458** | 0.6482 | 0.7570 / 0.7443 | **0.7481** ✗ |
| chain_median (robustness) | 0.06673 | 806 chains / 87,447 pts | 0.4429 / 0.6602 | 0.6178 | 0.6755 | 0.7327 / 0.7771 | 0.7970 ✗ |
| all-chains reference (tau→0, ZERO thresholding) | — | 1,692 chains / 156,979 pts | 0.2856 / 0.7147 | 0.4091 | 0.7245 | — | **0.8782** ✗ |

Recall matched honestly: both chain arms' TEST R@1.5 ≥ the banked baseline 0.5959 (and ≥
the Phase-1e point-oracle's 0.6337 for chain_mean's VAL constraint level). Guard
denominator: 1,675 baseline-covered GT segments of 2,595 pooled over the 10 TEST views.

## The diagnostic answer (what a hostile reviewer asked)

1. **Chain pooling DOES repair part of the point-level severing** — guard 0.6372 →
   **0.7481** at matched recall (median pooling 0.7970), so roughly a third to half of
   the Phase-1e collapse was a point-thresholding artifact. The reviewer's proposed fix
   was tried, exactly as proposed.
2. **And it still fails the 0.90 bar — for a two-layer STRUCTURAL reason.** The
   all-chains row is the decisive control: keeping EVERY chain with NO thresholding at
   all already caps the guard at **0.8782 < 0.90**, because the 42.4% of candidates that
   no proximity+direction chain absorbs are precisely the sparse bridging points that
   keep GT crease segments connected. Thresholding then only descends from that ceiling
   (0.8782 → 0.7481 at matched recall). So the severing is not an artifact any pooling
   granularity can undo: (a) chainification itself discards bridge structure, and (b)
   any post-hoc keep/drop decision on top of a fixed candidate set trades coverage for
   precision along 1D manifolds. Full builds need topology-aware CONSTRUCTION
   (connectivity as a constraint, not a casualty), not better thresholding.
3. **Chain pooling also pays real precision for its topology gain**: TEST P@1.5 drops
   0.7970 (point-oracle) → 0.6458 (chain_mean) — pooling drags whole mixed chains over
   or under tau. Even with a near-perfect in-scene ranking, chain-level gating lands
   BELOW the vanilla-M1b baseline's 0.6573 (at higher recall, 0.6482 vs 0.5959):
   thresholded selection from this cloud does not beat the path-C stroke pipeline even
   with oracle supervision — reinforcing, at the cloud level, that the banked path-C
   result is the right deliverable.

**Frozen fork verdict (spec): STRUCTURAL impossibility** — chain-oracle topology guard
0.7481 < 0.90. Appendix conclusion: post-hoc thresholding fundamentally cannot preserve
1D crease continuity; the mesh-free supervision gap (legal transfer AUC 0.5626, Phase 1e)
is a second, independent barrier — fixing either alone is insufficient.

## Honest caveats

- The oracle scores are the Phase-1e in-sample fit (AUC 0.9578, loosest upper bound);
  a weaker ranking would only lower every chain number — the STRUCTURAL verdict is
  conservative in that direction.
- G-buffers were re-rendered on CPU (deterministic) while Phase 1e rendered on CUDA:
  the guard denominator shifted by 2 segments (1,675 vs 1,673 of 2,595, 0.12%) — far
  below the 0.11 gap the verdict rests on. The quoted Phase-1e rows are the cached CUDA
  numbers.
- The `script_md5` field inside the phase1f JSONs stamps the SHARED evaluator module
  (`scripts/phase1e_gate.py`, `98b58715d12487041643deba76562905`, unchanged since the
  Phase-1e freeze); the phase1f driver itself is
  `scripts/phase1f_chain_gate.py` = `7e93fae67db49832e71641940dfbbe4e`.
- Chain membership is the cached P1c structure (r=0.005, |cos|≥0.6, min 10). A different
  chaining radius could absorb more bridge points — but relaxing it merges texture into
  crease chains (P1c chains are 95.6% label-pure at these constants), so this is the
  banked, label-pure operating point, not a tuned-for-1f choice.
- One-shot discipline: taus frozen in `phase1f_val_freeze.json` (write-once) before
  TEST; `phase1f_test_eval.json` write-once; mesh-free arms untouched per spec.

## Artifacts (all NEW)

`scripts/phase1f_chain_gate.py`, `out/phase1f_val_freeze.json` (frozen taus + VAL
curves + all-chains VAL ref), `out/phase1f_test_eval.json` (one-shot TEST + topology
guard + fork verdict). Inputs (read-only, cached): `out/phase1e_scores_chair.npz`,
`out/dexp1d_feats_chair.npz`, `out/linelets_chair_p1e_valref.npz`,
`out/m1b_chair_p1e_valref.json`, `out/phase1e_test_eval.json`,
`out/m1b_chair_gated_test.json`. Nothing committed.
