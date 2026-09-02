# PHASE 1e — CHEAP go/no-go: discriminator-gated Phase-1b cloud precision check
# **VERDICT: NO-GO — no mesh-free gate converts the cloud to method-legal precision; the mesh ORACLE converts precision (0.80) but severs topology (0.64)**

Spec `tier1/phase1e_spec.md`. EXPLORATORY probe BEYOND the locked path-C paper
(camera-ready `4856be7`). No banked paper number was altered, recomputed, or unfrozen;
every file this probe produced is NEW (`out/phase1e_*`, `out/m1b_chair_p1e_valref.json`,
`out/linelets_chair_p1e_valref.npz`, `scripts/phase1e_gate.py`, `logs/p1e_valref.log`).
The banked TEST baseline is QUOTED from `out/m1b_chair_gated_test.json`, never re-run.
**Nothing committed.** Every number below is read from a named result file.

---

## Protocol (as frozen by the spec)

- **Cloud**: the Phase-1b chair ref40 triangulated DexiNed cloud, the same 272,366
  candidates Phase 1c/1d scored (`out/dexp1d_feats_chair.npz`, key `P`; 3D recall 0.6753 /
  R_miss 0.6914 banked in Phase 1b).
- **Metric**: the EXACT vanilla-M1b macro segment-raster convention — per-view rasterise,
  P@1.5px over drawn pixels vs the mesh-oracle crease DT, R@1.5px over GT crease pixels,
  macro-averaged over views (`run_m1b.eval_segments` / `raster_segments`, angle-30 oracle
  cache, 3DGS-depth visibility). The cloud is rasterised through the LITERAL baseline code
  path as l=0 degenerate segments (one pixel per visible point; a fast sweep evaluator was
  used only for tau selection and was verified mask-identical on all 10 VAL views and
  value-identical to 1e-9 against the literal evaluator at spot taus including grid ends).
- **tau**: picked on VAL views {0,10,…,90} ONLY — per arm, tau = argmax VAL P@1.5 subject
  to VAL R@1.5 ≥ baseline VAL R@1.5 — then frozen (`out/phase1e_val_freeze.json`) before
  any TEST contact. TEST views {5,15,…,95} evaluated exactly once per arm
  (`out/phase1e_test_eval.json`). Script md5 stamped identical in both files
  (`98b58715d12487041643deba76562905`).
- **Baseline VAL reference** (NEW number, not banked): the banked M1b configuration re-run
  with `--eval_split val --dump_tuned` (`out/m1b_chair_p1e_valref.json`): segments
  tuned+len **P@1.5 0.5750 / R@1.5 0.6307**, n=15091. The reproduction's method side
  matches the banked run exactly at the count level (17065 seeds → 16039 spec-prune →
  15091 tuned), which also validates using its dumped tuned+len strokes as the
  topology-guard baseline raster (the banked run never persisted them).

## The gate arms — mesh-free at chair, per the SACRED invariant

**Direction reconciliation (matters):** the spec motivates the transfer gate with "banked
transfer AUC ~0.8245 chair<-lego". Per `out/dexprimary_p1d.json` the 0.8245 is
`transfer_chair_to_lego` — a probe FIT ON CHAIR MESH labels applied to lego, which would
put target-scene mesh in the gate and is therefore ILLEGAL as a chair gate. The only
method-legal transfer direction at chair is fit-on-lego → chair, whose banked AUC is
**0.5626** (near chance). This probe runs the legal direction and reproduces the banked
number bit-exactly (0.5626483971694244, `out/phase1e_scores_meta.json`), so the PRIMARY
arm enters far weaker than the spec's premise suggests — that is a finding, not a bug.

| arm | supervision at chair | AUC sanity vs banked |
|---|---|---|
| (i) **transfer** (PRIMARY) | lego mesh labels only (P1d fit-half protocol, StandardScaler+LR C=1.0, max_fit 60k, seed 0) | 0.5626 = banked 0.5626 (bit-exact) |
| (ii) **raw_vote** (guarded, pure paper constants) | none — a-priori percentile vote (normal_angle, depth_curv, luma_step; frozen in P1d) | eval-half 0.6329 = banked 0.6329 (bit-exact) |
| (ii) **vote_probe** (guarded, mesh-free REFIT) | PL-VOTE pseudo-labels only (q_pos 0.85 / q_neg 0.50 frozen a priori); deployed form fit on ALL pseudo-labeled rows — a refit, not a frozen constant | all-rows 0.6383 (banked xsplit ref 0.6371) |
| **oracle** (labelled UPPER BOUND, never a GO trigger) | in-scene chair mesh labels, fit on ALL labeled rows → in-sample AUC 0.9578 (the spec's "~0.90 probe"; banked honest xsplit ceiling 0.8395) | — |

The gate SCOREs are mesh-free; the gate THRESHOLD is VAL-mesh-tuned via the sanctioned
"pick tau on VAL" protocol — i.e. the deployed gate is score-mesh-free with a
VAL-supervised operating point, exactly what the spec words allow, stated here precisely.

## Results — VAL (tau selection) and the ONE-SHOT TEST

Sources: `out/phase1e_val_freeze.json`, `out/phase1e_test_eval.json`.

| arm | frozen tau (VAL {0,10,…,90}) | kept | VAL P@1.5 / R@1.5 | **TEST P@1.5** | **TEST R@1.5** | TEST P/R@2.5 | topo guard |
|---|---|---|---|---|---|---|---|
| banked baseline (QUOTED) | — | 15,091 strokes | 0.5750 / 0.6307 (valref) | **0.6573** | **0.5959** | 0.7777 / 0.6719 | (defines denominator) |
| ungated cloud | — | 272,366 | 0.2343 / 0.9535 | 0.3189 | 0.9540 | 0.3948 / 0.9856 | 0.9910 |
| (i) transfer | 4.778e-14 | 256,578 | 0.2409 / 0.9360 | **0.3216** | 0.9505 | 0.3978 / 0.9826 | **0.9892** ✓ |
| (ii) vote_probe | 0.09682 | 109,964 | 0.3446 / 0.6321 | **0.4081** | 0.6365 | 0.5029 / 0.6992 | **0.8888** ✗ |
| (ii) raw_vote | 0.61531 | 86,886 | 0.3821 / 0.6315 | **0.4458** | 0.6156 | 0.5439 / 0.7050 | **0.8811** ✗ |
| **oracle (upper bound ONLY)** | 0.61508 | 46,160 | 0.6222 / 0.6330 | **0.7970** | 0.6337 | 0.8901 / 0.7235 | **0.6372** ✗✗ |

Recall was matched honestly: every arm's TEST R@1.5 ≥ the banked baseline 0.5959 (no
recall starvation at any frozen tau; the starvation NO-GO branch was armed but not hit).

**Topology guard** (`topology_guard` in `out/phase1e_test_eval.json`): GT crease pixels
per TEST view grouped into 8-connected segments (2,595 pooled over the 10 views); a
segment counts as covered iff any of its pixels has chamfer-DT ≤ 1.5px to the raster in
question. The baseline strokes cover 1,673/2,595 (0.6447); the guard number is the
fraction of those 1,673 baseline-covered segments retaining ≥1 surviving gated point
(bar ≥ 0.90). The ungated cloud covers 0.9910 of them.

## Verdict against the FROZEN bars (one line, as demanded)

**NO-GO** — best mesh-free gated P@1.5 = **0.4458** (raw_vote) vs the 0.71 GO bar at
matched recall, and both in-scene mesh-free arms also breach the 0.90 topology guard
(0.8888 / 0.8811); the transfer arm keeps topology (0.9892) but converts nothing
(P 0.3216 ≈ ungated 0.3189).

Per-arm (all three pre-registered mesh-free arms evaluated once; reporting best-of-3 —
moot here since all fail): transfer NO-GO (precision), vote_probe NO-GO (topology,
and P 0.41 < 0.71 regardless), raw_vote NO-GO (topology, and P 0.45 < 0.71 regardless).

## What the probe established (the appendix-worthy content)

1. **The in-scene AUC does not convert to method-legal precision — now quantified at the
   cloud level, in the paper's own headline convention.** Mesh-free gating tops out at
   P@1.5 **0.4458** vs the vanilla-M1b 0.6573 and the 0.71 bar. The method-legal transfer
   probe (lego→chair 0.5626) is precision-inert: +0.003 over ungated at −4% recall.
2. **The supervision-bound story holds with a large margin.** The in-scene mesh ORACLE
   probe — the same 384-d DINOv2 descriptors, only the labels differ — lifts the cloud to
   **P@1.5 0.7970 at R 0.6337** (would clear even the 0.78 STRETCH bar): oracle 0.797 vs
   mesh-free ≤ 0.446 is the Phase-1d 0.84-vs-0.64 AUC gap converted into deliverable
   pixels. The information is in the descriptors; it is unreachable without labels.
3. **NEW failure mode the AUC never showed: even the oracle severs topology.** At its
   matched-recall operating point the oracle retains only **0.6372** of baseline-covered
   GT crease segments (guard bar 0.90) — per-point semantic gating drops bridging points
   and fragments chains even when the per-point ranking is nearly perfect (in-sample AUC
   0.958). agy's trap caught exactly what it was set for: a hypothetical full build would
   need chain-level (not point-level) gating, independent of the supervision problem.
4. Consistent with all of the above, the locked path-C paper stands as the deliverable,
   unchanged.

## Honest caveats

- The topology-guard baseline strokes are a fresh reproduction (banked run never dumped
  the tuned+len stage), validated by exact keep-count match (17065/16039/15091) but not
  bit-identical geometry (`render_gbuffer` CUDA nondeterminism, pre-existing); this can
  perturb only the guard's denominator, not any P/R number.
- vote_probe is a mesh-free REFIT (self-training deployment of the paper's frozen
  PL-VOTE constants), a slightly stronger reading of spec option (ii) than "constants
  only"; the constants-only reading is raw_vote, reported alongside — same verdict.
- The oracle is fit in-sample on all labeled rows (AUC 0.9578) — deliberately the loosest
  upper bound; the banked honest ceiling is 0.8395 (xsplit). It is labelled everywhere
  and excluded from the verdict logic by construction.
- The cloud is rasterised as points (l=0) inside the segment-raster convention while the
  baseline draws length-modulated strokes; identical GT, DT, visibility, macro-averaging
  and code path. Points cannot interpolate between samples, but at 272k points the
  ungated recall is 0.954, so the NO-GO is not a rasterisation artifact — and the oracle
  arm reaches 0.797 precision under the identical point-raster.
- VAL→TEST generalisation of the frozen taus was clean (every arm's TEST P above its VAL
  P; recall within 0.02 of VAL), so the one-shot was not a lucky draw.
- A pre-TEST adversarial audit (3 independent lenses) found and fixed, before freezing:
  a sweep-index inversion (would have failed loudly on its own assertions), a dead
  recall-starvation branch caused by a −inf grid sentinel, and a cv2 fixed-point corner
  case for u∈[−0.5,0); all frozen numbers come from the literal baseline evaluator.

## Artifacts (all NEW)

`scripts/phase1e_gate.py` (3 stages: scores / sweep / test, write-once-guarded),
`out/phase1e_scores_chair.npz` + `out/phase1e_scores_meta.json` (per-candidate gate
scores + sanity AUCs), `out/phase1e_val_freeze.json` (frozen taus + VAL curves),
`out/phase1e_test_eval.json` (the one-shot TEST + topology guard + verdict),
`out/m1b_chair_p1e_valref.json` / `out/linelets_chair_p1e_valref.npz` (baseline VAL
reference + reproduced tuned strokes), `logs/p1e_valref.log`. Nothing committed.
