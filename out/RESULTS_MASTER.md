# RESULTS_MASTER — the frozen claim ledger (path-C convergence)

STATUS: experiments FROZEN (three-way consensus). This file is the single canonical source
the paper draws from. FRAMING (A-ANCHOR, reconciled): Contribution A (§1, interior temporal
stability at matched precision/density) is PRIMARY; Contribution B (§2) is the diagnostic
BOUNDARY that scopes A's precision; the honesty protocol (§3) is third. The
supervision-bound result is always stated as the sandwich — the signal EXISTS
(0.8401/0.9044) → collapses under mesh-free supervision through the pre-frozen 0.72 gate
(0.6371/0.6569) → the chair→lego 0.8245 transfer route stays open — never "impossible",
always "supervision-bound under our frozen protocol". Every number carries its source file; nothing here is new. Numbers
that could not be located in a committed result file are marked [NEEDS-SOURCE].

INVARIANT (stated once, holds everywhere): **the GT mesh never enters the method path.**
It labels and scores only (`src/mesh_oracle.py` and the eval scripts); every line-generating
component (linelet pull, chaining, projection, detectors, triangulation, features,
accumulators) is mesh-free, AST-verified per phase
(`DEXPRIMARY_P0/P1B/P1C/P1D_RESULTS.md`, `PARETO{,2,3}_RESULTS.md` §setup).

Scope (frozen): **frozen 3DGS of static NeRF-synthetic scenes with known poses**, held-out
TEST views/trajectories. n=2 scenes (chair, lego) with perfect geometry is the named
limitation; breadth (more scenes, real captures, estimated poses) is future work. The
evaluation trades breadth for a controls lattice: 2 scenes × 3 trajectories (T1 orbit,
T2 orbit+zoom, T3 adversarial spline) × 3 frozen detectors (Canny, PiDiNet, TEED) ×
{memoryless, oracle-flow-accumulated} baselines × matched precision AND density ×
{stroke-level, pixel-pooled} statistics, with every gate frozen before its numbers existed.

---

## 1. Contribution A — interior stability at matched precision/density (CORE)

> Terminology rule: never "temporal coherence" unqualified. The claim is **interior
> stability at matched precision and density**; the operational envelope (§1.4) bounds it.

### 1.1 Headline claims (each with its frozen control)

| claim | value | control it survived | source |
|---|---|---|---|
| Interior pop-rate advantage at the HARDEST cell (lego × T3 spline, vs oracle-flow EMA at matched P & density) | **1.98×** (rate 0.0425 vs 0.0214 over the 93–97 % interior) | disocclusion decomposition | `pareto3_lego_T3_disocc.json` |
| Pixel-pooled pop>2px advantage vs the STRONGEST accumulated 2D baseline (oracle rigid flow + occlusion-aware EMA), across all shared matched-P-and-density points | **1.72× – 21.4×** (per-condition worst: chair-T1 5.19×, chair-T3 5.49×, lego-T1 8.35×, lego-T3 1.72×) | PARETO-2, 4 conditions | `pareto2_verdict.json` |
| Pixel flicker advantage vs MEMORYLESS per-frame detectors at every shared matched point | **≥ 9.8×** (both scenes) | PARETO-1 matched-P + matched-density | `PARETO_RESULTS.md` |
| Stroke-level E_warp ratio vs per-frame TEED, 6 conditions (2 scenes × 3 trajectories) | **3.38× – 21.62×** (worst = lego·spline) | Track P, scorer + thresholds hash-frozen pre-run | `TRACK_P_RESULTS.md` |
| Stroke-level Fréchet / P_pop ratio vs per-frame Canny, 30–240 frames | Fréchet **2.43×–29.92×**, P_pop **3.44×–11.49×** (headline "7–13×" = 240f band across variants) | M1b stroke-temporal + sparsity & silhouette controls (§2a/2b) | `m1b_stroke_temporal_table.md`, `m1b_stroke_temporal_table_tc_tcteed.md` |
| Stroke survival: object-space strokes persist 37–183 frames mean vs 1.0–1.5 for per-frame detection | P(life>32): 0.29–0.83 vs 0.005–0.009 | Track P survival curves (the SECONDARY inf-ratio is degenerate and is NOT quoted) | `TRACK_P_RESULTS.md` |
| Stability is threshold-invariant for OURS (pop>2px 0.0042–0.0049 across the whole f-sweep, chair T1) — stability comes from the parameterization, not from line selection; per-frame detectors DEGRADE when sparsified | direct answer to the fewer-lines confound | PARETO-1 f-sweep | `pareto_chair.json`, `PARETO_RESULTS.md` |

NOTE on the composite range "1.98×–29.9×": these endpoints are DIFFERENT statistics
(1.98× = PARETO-3 interior pop-rate; 29.92× = M1b chair-240f stroke Fréchet). The paper
must quote them per-statistic as above, never as one range.

### 1.2 The measurement (frozen definitions)

- **Pooled E_warp / pop-rate** (`PARETO_RESULTS.md`, `scripts/pareto_coherence.py`): every
  ON line pixel of frame t with finite rendered depth is forward-warped by the exact rigid
  flow (depth + the two poses — identical operator for all methods); the distance transform
  of frame t+1's line mask is read at the landing pixel; distances pooled over all 239
  transitions. No matching step, no per-line averaging — popping is inside the metric.
  pop>k = P(pooled distance > k px). All methods interior-restricted (α>0.5 eroded 2 px),
  which removes the silhouette warp-drop confound at source (drop ≤0.1 % everywhere).
- **Matched comparison rule**: a baseline point is *shared* iff an OURS point matches-or-
  beats it on BOTH P@1.5 and px/frame; advantage = the minimum ratio over dominating OURS
  points. Precision for PARETO-2/3 is measured on the trajectory frames themselves
  (mesh EVAL-only DTs on every 10th frame) because accumulation is trajectory-dependent.
- **Oracle-flow accumulated baseline** (`PARETO2_RESULTS.md`; per-cell numbers in
  `pareto2_{scene}_{traj}.json` + `pareto2_verdict.json`, construction in
  `scripts/pareto2_flowacc.py`):
  A_t = α·backwarp(A_{t−1}) + (1−α)·E_t, rethreshold 0.5, α ∈ {0…0.85}, EXACT rigid
  backward flow with occlusion-aware fallback — deliberately stronger than any RAFT
  variant a reviewer could build. RAFT was deliberately NOT run (weaker baseline would
  inflate our number).

### 1.3 The two failed frozen gates in this contribution (§3 for the full list)

- **PARETO-1 FAIL**: pooled-MEAN E_warp advantage 2.42× < 3× at chair CANNY 150/300
  (and 2.99× at 75/200). Mechanism, measured: OURS' pooled mean is flat at the shared
  ~0.28 px rasterization floor (p95 = 1.00 px, f-invariant), which compresses mean-ratios
  at sub-pixel motion; the floor-free pop-rate at the same point is 12.8×, flicker 12.2×.
  The gate was NOT re-tuned; the paper quotes pop/flicker as primary and discloses the
  mean-statistic collapse. (`PARETO_RESULTS.md`, `pareto_verdict.json`)
- **PARETO-2 NO-GO on the letter**: lego × T3 spline worst shared advantage **1.72×**
  < the 2× floor (5/6 other conditions PASS at 5.19–8.35×). Frozen as a conservative
  lower bound vs the oracle-flow ceiling; the claim is SCOPED, not defended.
  (`pareto2_verdict.json`)

### 1.4 Operational envelope (the failure boundary, stated by us first)

- **OURS is WORSE inside disocclusion regions**: pop-rate 0.407 vs the accumulated
  baseline's 0.300 (`pareto3_lego_T3_disocc.json`) — chain runs split at occlusion
  boundaries and their endpoints shift. The entire advantage is interior (1.98× rate over
  93–97 % of pixels), partially offset at occlusion boundaries.
- The single non-winning cell (lego × T3, 1.72×) is the condition that maximizes
  silhouette/occlusion flux (micro-relief geometry × non-uniform multi-axis motion) —
  the boundary is **predictable, not random**: the win shrinks exactly where per-frame
  line-pixel turnover is dominated by occlusion-boundary churn.
- **PARETO-3 NO-GO (33.3 % < 60 %)**: the accumulated baseline's residual is NOT
  disocclusion-concentrated — it is diffuse interior EMA drift (2/3 of pop mass interior;
  disocclusion regions are 7.1× harder per-pixel but only 6.6 % of pixels). Therefore
  **no disocclusion-mechanism sentence** appears in the paper; the bounded claim stays
  empirical. (`pareto3_lego_T3_disocc.json`, `PARETO3_RESULTS.md`)
- Trajectory scaling: OURS' stroke residual falls ∝ per-frame motion; per-frame baselines
  saturate at a motion-independent popping floor (`m1b_stroke_temporal_table.md` §1).

---

## 2. Contribution B — the precision BOUNDARY: coverage-ceiling characterization (4-act arc, diagnostic)

### Act 1 — the ceiling exists
Re-ranking the fixed vanilla-3DGS pool caps pipeline recall at **R@1.5 = 0.7908 chair /
0.5572 lego** (f=1.00, keep-everything; `CAP_RESULTS.md` §1). The pure gaussian-centre
2D coverage ceiling is 0.7382 / 0.6337 and the visible-carrier UNCOVERED fraction on lego
is 0.3663 (`DEXPRIMARY_P0_RESULTS.md`, reproducing `LEGO_CEILING_AUTOPSY.md` Fig. B exactly).

> **Threshold sensitivity of the lego ceiling (audited; see `LEGO_THRESHOLD_AUDIT.md`).** The GT
> crease set is defined as mesh edges with dihedral >= 30 deg (`src/mesh_oracle.py`). lego's mesh
> carries one family of ~213,711 edges at exactly 30.000 deg, which that threshold splits roughly
> in half through the .obj's 6-decimal vertex quantisation. Nudging the threshold to 30.05 deg
> therefore removes 47% of lego's crease pixels and moves lego's ceiling from R@1.5 = 0.5572 to
> 0.6408; it plateaus thereafter (0.6467 at 45 deg). **This is an artifact of asset quantisation,
> not of the method, and it is not an improvement:** precision over the same rasterised segments
> falls 0.6360 -> 0.3004 across the same range, 3D F1 is flat-to-declining (0.1953 -> 0.1873), and
> the frozen joint operating gate `P@1.5 >= 0.85 AND R@1.5 >= 0.65` is not met at any threshold on
> either scene, moving monotonically further out of reach. chair is stable (0.7908 -> 0.7905 at
> 30.05 deg). The `rho_B2 < 0.30` carrier gate holds at every audited threshold in both its
> spec-literal reading (0.0799 -> 0.0625) and its most adverse visible-only reading
> (0.2934 -> 0.2946). The coverage-ceiling conclusion is therefore threshold-robust; the specific
> value 0.5572 is threshold-specific and should always be quoted with its 30 deg definition.

### Act 2 — geometry cannot discriminate the miss-set (K_geom ≈ 0)
On lego decals every geometric channel is at/below chance for crease-vs-decal: 2DGS surfel
dihedral **0.4110**, 2DGS rendered-normal ribbon 0.3307, vanilla-3DGS ribbon 0.3875,
**GT-mesh dihedral 0.3964**, GT-mesh normal dispersion 0.4675 with class medians 44.52° vs
44.84° — given perfect geometry the two classes differ by 0.32°
(`DIAG2DGS_RESULTS.md`). The SH-DC albedo-step gate **LEAKS** (fabric p50 0.1235 vs crease
p50 0.1211, indistinguishable; `m1b_albedo_step_falsify_lego.json`). Multi-view
consistency also does not separate (texture points 0.870 vs crease 0.937 consistent;
`DEXPRIMARY_P1B_RESULTS.md` §3). Coverage recovery attempts: single-view DexiNed lift =
chance (R_miss 0.0952 vs chance 0.0940, lego; `DEXPRIMARY_P0_RESULTS.md`); multi-view
triangulation = real localization fix but detector-bound MARGINAL (chair 3D recall 0.6753 /
R_miss 0.6914; `DEXPRIMARY_P1B_RESULTS.md`).

### Act 3 — the separating signal exists, and it is semantic surface identity
Phase 1c kill-test **GO**: frozen zero-shot DINOv2 + linear probe separates crease from
texture at per-point xsplit AUC **0.8401 chair / 0.9044 lego**, leakage-guarded chain-AUC
**0.8205 / 0.8913**; photometric ≈0.71, geometric ≈0.65 (`dexprimary_p1c_{chair,lego}.json`,
`DEXPRIMARY_P1C_RESULTS.md`). Honest reading: the probe reads WHICH SURFACE a point lies on
(fabric field vs piping; studs vs decals) — a surface-identity readout, not edge-type
detection.

### Act 4 — the sandwich: the signal exists, and is supervision-bound under our frozen protocol
Phase 1d **NO-GO**: trained on the best mesh-free pseudo-labels, the same probe collapses
**0.8395 → 0.6371** chair (frozen bar 0.72; lego 0.9046 → 0.6569), below even its
photometric baseline — zero label-noise denoising; DINOv2's surface-identity memorization
faithfully learns the pseudo-labels' systematic bias (`dexprimary_p1d.json`,
`DEXPRIMARY_P1D_RESULTS.md`). Asterisk, disclosed: the MESH-supervised probe transfers
chair→lego at **0.8245** (but lego→chair 0.5626) — recoverable with labeled training
scenes, in one direction of two tested; a future-work sentence, not a method.

**The arc in one line**: coverage is bounded by the carrier; the miss-set is geometrically
invisible (K_geom≈0), photometrically reachable but placement-bound, and semantically
separable — the signal EXISTS (0.8401/0.9044) but collapses without mesh supervision
(0.6371, frozen 0.72 gate) with the chair→lego 0.8245 transfer route open — i.e. precision
is supervision-bound under our frozen protocol, which is exactly the boundary that scopes
Contribution A.

---

## 3. Every frozen gate we failed — disclosed up front, none re-tuned

| gate (frozen before numbers) | bar | measured | disposition |
|---|---|---|---|
| PARETO-1 pooled-mean ≥3× at every shared point | 3× | **2.42×** (chair Canny 150/300) | FAIL; floor-compression mechanism measured (pop 12.8× at same point); statistic disclosed, claim carried by pop/flicker | 
| PARETO-2 ≥3×/2× at every shared point vs oracle-flow EMA | 2× floor | **1.72×** (lego T3) | NO-GO on the letter; frozen as conservative lower bound; envelope §1.4 |
| PARETO-3 ≥60 % of baseline residual in disocclusion | 60/40 % | **33.3 %** | NO-GO; no mechanism sentence in the paper |
| Phase 0 R_miss ≥0.50 (coverage via single-view lift) | 0.50/0.35 | **0.095** ≈ chance | NO-GO; direction killed |
| Phase 1b 3D recall >0.79 (triangulation breaks ceiling) | 0.79 | **0.6753** | MARGINAL; localization fix banked, ceiling stands |
| Phase 1d mesh-free FAM-C ≥0.78 (deployable discriminator) | 0.78/0.72 | **0.6371** | NO-GO; path B closed |
| (also disclosed) DIAG2DGS dihedral gate ≥0.80 | 0.80 | **0.4110** | FAIL; K_geom≈0 established |

Why none were re-tuned: the honesty protocol IS the methodology — chance clouds,
spread-matched jitter, paired seeding, budget matching, leakage-guarded splits, and
pre-registered gates evaluated on their letter. Two of the paper's strongest sentences
(the floor-compression mechanism, the ours-worse-at-disocclusion disclosure) exist only
because failed gates were reported instead of defended.

---

## 4. Appendix A — post-lock falsification probes (Phases 1e/1f; ADDITIVE ledger)

Post-camera-ready probes answering "why not just filter the cloud with a discriminator /
chain pooling?" — run with the same discipline (tau frozen on VAL views {0,10,…,90} only,
TEST {5,15,…,95} evaluated once per arm, macro segment-raster P@1.5px = the banked M1b
convention of `m1b_chair_gated_test.json`, its baseline quoted never re-run). Gate SCORES are mesh-free at the target
scene; the in-scene mesh probe appears ONLY as a labelled oracle upper bound. These rows
scope the REPAIR CLASS (post-hoc keep/drop filtering of a fixed candidate cloud); the
precision boundary itself stays supervision-bound (§2), never "impossible".

| arm (chair ref40 cloud, 272,366 pts; baseline 0.6573 / R 0.5959) | TEST P@1.5 | TEST R@1.5 | topology guard (bar 0.90) | source |
|---|---|---|---|---|
| ungated cloud | 0.3189 | 0.9540 | 0.9910 | `phase1e_test_eval.json` |
| transfer gate (method-legal lego→chair, AUC 0.5626 = chance; the banked 0.8245 is the chair-mesh-fit reverse, ILLEGAL as a chair gate) | 0.3216 | 0.9505 | 0.9892 | `phase1e_test_eval.json` |
| in-scene mesh-free vote probe (PL-VOTE refit) | 0.4081 | 0.6365 | 0.8888 | `phase1e_test_eval.json` |
| in-scene mesh-free raw vote (frozen constants) | 0.4458 | 0.6156 | 0.8811 | `phase1e_test_eval.json` |
| **mesh ORACLE, point-gated (labelled upper bound ONLY; in-sample AUC 0.9578)** | **0.7970** | 0.6337 | **0.6372** | `phase1e_test_eval.json` |
| mesh ORACLE, chain-mean-pooled (1,692 P1c/P1d chain components) | 0.6458 | 0.6482 | 0.7481 | `phase1f_test_eval.json` |
| mesh ORACLE, chain-median-pooled | 0.6178 | 0.6755 | 0.7970 | `phase1f_test_eval.json` |
| all chains, ZERO thresholding (the chain-coverage ceiling; 42.36 % of candidates are unchained) | 0.4091 | 0.7245 | **0.8782** | `phase1f_test_eval.json` |

Frozen probe gates: Phase 1e GO required mesh-free P@1.5 ≥ 0.71 at R ≥ 0.5959 AND
topology ≥ 0.90 → **NO-GO** (best mesh-free 0.4458). Phase 1f diagnostic fork →
**STRUCTURAL** for the filtering repair class: chain pooling repairs part of the
point-level severing (0.6372 → 0.7481) but the zero-threshold chain ceiling is 0.8782 <
0.90 — the unchained 42.36 % are the bridge points — and even the oracle's chain-gated
precision (0.6458) lands below the 0.6573 baseline. **The topological trilemma:** no
tested gate — mesh-free or oracle, point- or chain-pooled — attains P@1.5 ≥ 0.71, R@1.5 ≥
0.5959, and topology ≥ 0.90 simultaneously. Probe caveats: chair only (n=1 scene at the
cloud level), oracle bound is in-sample (loosest), cloud rasterised as points inside the
segment-raster convention. Full protocol + caveats: `PHASE1E_GATE_CHECK.md`,
`PHASE1F_CHAIN_GATE.md`.

---

Sources index: `PARETO_RESULTS.md` · `pareto_{chair,lego}.json` · `pareto_verdict.json` ·
`pareto2_{chair,lego}_{T1_orbit,T3_spline}.json` · `pareto2_verdict.json` ·
`pareto3_lego_T3_disocc.json` · `PARETO3_RESULTS.md` · `TRACK_P_RESULTS.md` ·
`m1b_stroke_temporal_table{,_tc_tcteed}.md` · `CAP_RESULTS.md` · `LEGO_CEILING_AUTOPSY.md` ·
`DIAG2DGS_RESULTS.md` · `m1b_albedo_step_falsify_{scene}.json` ·
`DEXPRIMARY_P0/P1B/P1C/P1D_RESULTS.md` · `dexprimary_p1c_{chair,lego}.json` ·
`dexprimary_p1d.json` · `PARETO2_RESULTS.md` (prose write-up of the PARETO-2 run; numbers
verified consistent with `pareto2_*.json` + `pareto2_verdict.json`) ·
`phase1e_test_eval.json` · `phase1e_scores_meta.json` · `phase1f_test_eval.json` ·
`PHASE1E_GATE_CHECK.md` · `PHASE1F_CHAIN_GATE.md` (Appendix-A probes).
