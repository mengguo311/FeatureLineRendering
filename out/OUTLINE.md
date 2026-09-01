# OUTLINE — paper skeleton (path C). Frozen ledger: `out/RESULTS_MASTER.md`

Framing (three-way reconciled): a **forensic diagnostic** (Contribution B — why precision is
supervision-bound for frozen post-hoc extraction) + a **surgical, honestly-scoped
stabilization primitive** (Contribution A — interior stability at matched precision and
density). The structure itself counters the "failed system in denial" read: the negative
results are the primary scientific content of §4, and both self-disclosed failures get
dedicated figure real-estate (§5, Fig 3/4).

---

## Abstract
- One system claim: object-space feature lines from a frozen 3DGS are an order of magnitude
  more stable than per-frame 2D detection at matched precision and density, and the residual
  precision gap is characterized — not patched — as supervision-bound. [RESULTS_MASTER §1.1,
  §2 arc → Fig 1]
- Quotes only: ≥9.8× vs memoryless [→ Fig 2], 1.72× conservative lower bound vs an
  oracle-flow accumulator [→ Fig 3], the 4-act ceiling arc [→ Fig 6–8, Tab 3].

## 1. Introduction
- Problem: clean, temporally stable 3D feature lines from a FROZEN 3DGS; the two blockers
  (precision on textured surfaces; per-frame instability). [narrative; no numbers]
- Contribution list (B first as the scientific insight, A as the deployable primitive):
  (i) the coverage-ceiling characterization ending in the supervision-bound falsification
  [§2 → Tab 3, Fig 8]; (ii) interior stability at matched precision/density with a
  measured operational envelope [§1 → Fig 2–4]; (iii) the honesty protocol as method —
  7 frozen gates, all reported, 5 failed/marginal [§3 → Tab 4].
- Fig 1 (teaser): our lines over trajectory frames vs per-frame Canny/PiDiNet flicker
  (existing viz assets, e.g. `out/m1b_vector_*` frames). [qualitative; NO new numbers]

## 2. Related work
- SketchSplat: differentiable multi-view edge sketching; we import its curve-level
  aggregation idea (chains, Phase 1c) and refute its view-consistency premise on textured
  synthetic scenes (texture 0.870 vs crease 0.937 multi-view-consistent)
  [RESULTS_MASTER §2 Act 2 → Tab 3].
- EMAP-style UDF edge fields: multi-view edge fusion is semantics-blind — our Act 3/4 shows
  the missing bit is surface identity, and it is supervision-bound [§2 Act 3–4 → Fig 8].
- Per-frame edge detection + temporal filtering: our PARETO-2 oracle-flow EMA is the
  strongest instance of this family (stronger than RAFT-based; exact flow + occlusion-aware)
  [§1.2 → Fig 3].

## 3. Method
- Object-space carrier (linelet pull → 3D chains → per-frame projection with z-buffer
  visibility) × image-space DT corrector; acceptance threshold f traces the operating curve.
  [construction; numbers live in §5]
- The **mesh-never-in-method-path invariant**, stated once, with the AST-verification
  protocol. [RESULTS_MASTER header]
- The exact-rigid-flow warp operator shared by every metric and every baseline (identical
  operator = the fairness spine of §5). [§1.2]

## 4. The coverage-ceiling characterization (Contribution B — PRIMARY)
The 4-act arc, each act one subsection, each with its frozen gate verdict:
- Act 1 — the ceiling exists: pipeline R@1.5 caps 0.7908 chair / 0.5572 lego; pool coverage
  0.7382/0.6337; lego UNCOVERED 0.3663. [→ Fig 6]
- Act 2 — K_geom≈0: surfel 0.4110 / ribbon2dgs 0.3307 / ribbon3dgs 0.3875 / **GT-mesh
  0.3964** / dispersion 0.4675 with medians 44.52° vs 44.84° (0.32° apart); albedo gate
  LEAKS (0.1235 vs 0.1211); multi-view consistency non-separating (0.870 vs 0.937);
  recovery attempts: single-view lift = chance (0.0952 vs 0.0940), triangulation MARGINAL
  (recall 0.6753 / R_miss 0.6914). [→ Tab 3, Fig 6b]
- Act 3 — the separating signal is semantic surface identity: DINOv2 xsplit 0.8401/0.9044,
  guarded chain 0.8205/0.8913, vs photometric ≈0.71 / geometric ≈0.65. [→ Fig 7]
- Act 4 — supervision-bound: mesh-free collapse 0.8395→0.6371 chair (bar 0.72),
  0.9046→0.6569 lego; transfer asymmetry 0.8245 / 0.5626 as the disclosed asterisk.
  [→ Fig 8]

## 5. Interior stability at matched precision & density (Contribution A — scoped)
- 5.1 The three-axis Pareto protocol (pooled pixel metric, matched-P-and-density dominance
  rule, interior restriction). [§1.2 → Fig 2]
- 5.2 vs memoryless detectors: ≥9.8× flicker at every shared point; ours'
  threshold-invariant pop (0.0042–0.0049); the PARETO-1 mean-statistic FAIL (2.42×)
  disclosed WITH its measured mechanism (0.28 px floor, p95=1.00; floor-free 12.8×/12.2×
  at the same point). [→ Fig 2 + Tab 2]
- 5.3 vs the oracle-flow accumulated ceiling: per-condition worsts 5.19/5.49/8.35/**1.72×**;
  the lego×T3 NO-GO is the FIGURE, not a footnote — frozen conservative lower bound.
  [→ Fig 3]
- 5.4 The operational envelope (disclosed here, in the results section, not in
  Limitations): disocclusion decomposition — ours WORSE inside disocclusion (0.407 vs
  0.300), advantage is interior (1.98× over 93–97 % of px), PARETO-3 NO-GO (33.3 % < 60 %,
  residual = diffuse EMA drift; disocc 7.1× harder but 6.6 % of px) ⇒ no mechanism claim;
  failure boundary predictable (max occlusion-flux condition). [→ Fig 4]
- 5.5 Stroke-level corroboration (banked): Track P E_warp 3.38–21.62× across 2×3
  conditions; survival 37–183 vs 1.0–1.5 mean frames, P(life>32) 0.29–0.83 vs
  0.005–0.009; M1b Fréchet 2.43–29.92×, P_pop 3.44–11.49×; motion-proportional scaling vs
  baseline popping floor. [→ Tab 1 + Fig 5]

## 6. Limitations
- Owned as an **in-vitro geometric characterization**: n=2 NeRF-synthetic scenes, perfect
  geometry, known poses; oracle flow deliberately shares that assumption (it upper-bounds
  every estimated-flow baseline). Not patched; scope stated in §5.1 and here. [no numbers]
- Disocclusion deficit (from §5.4), the lego precision inversion (per-frame Canny more
  precise than our lines on lego at every density [PARETO_RESULTS.md → Fig 2 annotation]),
  and the transfer asymmetry (§4 Act 4).

## 7. Conclusion
- The deployable primitive is A; the transferable insight is B; the method is the honesty
  protocol (Tab 4). [no new numbers]

---

## CLAIM → FIGURE/TABLE MATRIX (every headline number in RESULTS_MASTER §1–3)

| claim | value | source file | fig/tab |
|---|---|---|---|
| Interior pop-rate advantage, hardest cell | 1.98× (0.0425 vs 0.0214) | pareto3_lego_T3_disocc.json | **Fig 4** |
| Pooled pop advantage vs oracle EMA, all shared cells | 1.72–21.4×; worsts 5.19/5.49/8.35/1.72× | pareto2_verdict.json | **Fig 3** |
| Flicker advantage vs memoryless, every shared point | ≥9.8× | PARETO_RESULTS.md | **Fig 2** |
| Ours threshold-invariant pop | 0.0042–0.0049 | pareto_chair.json | **Fig 2** |
| PARETO-1 mean-statistic FAIL + mechanism | 2.42× (2.99×); floor 0.28 px, p95=1.00; pop 12.8×, flick 12.2× | PARETO_RESULTS.md, pareto_verdict.json | **Tab 2** |
| PARETO-2 NO-GO lower bound | **1.72×** (lego×T3) | pareto2_verdict.json, PARETO2_RESULTS.md | **Fig 3** (highlighted cell) |
| Disocclusion regression (ours worse) | 0.407 vs 0.300 | pareto3_lego_T3_disocc.json | **Fig 4** |
| PARETO-3 gate + decomposition | 33.3 % < 60 %; disocc 7.1× harder, 6.6 % of px | pareto3_lego_T3_disocc.json | **Fig 4** |
| Track P E_warp ratios | 3.38–21.62× (6 conditions) | TRACK_P_RESULTS.md | **Tab 1** |
| Stroke survival | mean 37–183 vs 1.0–1.5; P(life>32) 0.29–0.83 vs 0.005–0.009 | TRACK_P_RESULTS.md | **Fig 5** |
| M1b stroke ratios | Fréchet 2.43–29.92×; P_pop 3.44–11.49× (7–13× @240f band) | m1b_stroke_temporal_table{,_tc_tcteed}.md | **Tab 1** |
| Pipeline recall ceiling | R@1.5 0.7908 / 0.5572 | CAP_RESULTS.md | **Fig 6** |
| Pool coverage / UNCOVERED | 0.7382 / 0.6337; lego 0.3663 | DEXPRIMARY_P0_RESULTS.md (repro of LEGO_CEILING_AUTOPSY.md) | **Fig 6** |
| K_geom≈0 AUC family | 0.4110 / 0.3307 / 0.3875 / 0.3964 / 0.4675; 44.52° vs 44.84° | DIAG2DGS_RESULTS.md | **Tab 3** |
| Albedo-step gate leaks | p50 0.1235 vs 0.1211 | m1b_albedo_step_falsify_lego.json | **Tab 3** |
| Multi-view consistency non-separating | 0.870 vs 0.937 | DEXPRIMARY_P1B_RESULTS.md | **Tab 3** |
| Single-view lift = chance | R_miss 0.0952 vs chance 0.0940 | DEXPRIMARY_P0_RESULTS.md | **Fig 6b** |
| Triangulation MARGINAL | recall 0.6753 / R_miss 0.6914 | DEXPRIMARY_P1B_RESULTS.md | **Fig 6b** |
| DINOv2 separation | xsplit 0.8401 / 0.9044; guarded 0.8205 / 0.8913; baselines ≈0.71 / ≈0.65 | dexprimary_p1c_{chair,lego}.json | **Fig 7** |
| Mesh-free collapse | 0.8395→0.6371 (bar 0.72); 0.9046→0.6569 | dexprimary_p1d.json | **Fig 8** |
| Transfer asymmetry | 0.8245 / 0.5626 | dexprimary_p1d.json | **Fig 8** |
| The 7 frozen-gate ledger (incl. 0.095, 0.6753, 0.6371, 0.4110 rows) | verbatim §3 table | RESULTS_MASTER.md §3 | **Tab 4** |

## FIGURE / TABLE LIST (spec only — nothing rendered here)

- **Fig 1** Teaser: line renderings over 3 trajectory frames, ours vs per-frame detector
  (from existing `out/m1b_vector_*` / trajectory viz assets). Qualitative.
- **Fig 2** PARETO-1 frontiers, both scenes (from `pareto_{chair,lego}.json`; base plots
  exist as `pareto_{chair,lego}.png`): P@1.5 vs flicker & pop, marker size = density;
  annotations: ≥9.8×, ours' flat pop line, lego precision-inversion note.
- **Fig 3** PARETO-2: per-condition worst-advantage bars (5.19/5.49/8.35/1.72×) over the
  α-sweep frontier (from `pareto2_*_*.json`, plots exist as `pareto2_*.png`); the 1.72×
  cell visually flagged as the frozen lower bound.
- **Fig 4** PARETO-3 decomposition: per-region pop-rate bars (interior 0.0425/0.0214;
  disocc 0.300/0.407) + the overlay (`pareto3_disocc_overlay.png`) + 33.3 % gate readout
  (from `pareto3_lego_T3_disocc.json`).
- **Fig 5** Track P survival curves P(life>K), 6 conditions (from `TRACK_P_RESULTS.md`
  table; regenerable from `track_p_temporal.json`).
- **Fig 6** Act 1: recall-ceiling bars (0.7908/0.5572; pool 0.7382/0.6337; UNCOVERED
  0.3663). **Fig 6b** recovery attempts: P0 chance-equality bar pair (0.0952 vs 0.0940) +
  P1b marginal point (0.6753/0.6914).
- **Fig 7** Act 3: DINOv2 prob-map panel (exists: `dexprimary_p1c_chair.png`) + AUC bars
  (mesh-supervised vs guarded vs photometric/geometric baselines).
- **Fig 8** Act 4: collapse bars (0.8395→0.6371, 0.9046→0.6569, bar line at 0.72) +
  transfer asymmetry arrows (0.8245 / 0.5626).
- **Tab 1** Stroke-level banked ratios: Track P E_warp (6 conditions) + M1b Fréchet/P_pop
  (30–240 f).
- **Tab 2** PARETO-1 failing-point anatomy: the four statistics at chair Canny 150/300
  (mean 2.42× / median / pop 12.8× / flicker 12.2×) + the floor numbers.
- **Tab 3** K_geom≈0: the five geometric AUCs + dispersion medians + albedo leak +
  multi-view consistency row.
- **Tab 4** The frozen-gate ledger (RESULTS_MASTER §3 verbatim, 7 rows).

## Completeness self-check (frozen gate)
(a) every §1–3 headline number mapped to exactly one fig/tab id — PASS (matrix above; the
    §3 gate-table numbers 0.095/0.6753/0.6371/0.4110 map once via Tab 4; their §2
    appearances map to Fig 6b/Tab 3 as *distinct claims* of the arc);
(b) B positioned PRIMARY (§4 + intro ordering), A scoped to "interior stability at matched
    precision/density" throughout — PASS;
(c) both self-disclosed failures have dedicated real-estate: 0.407-vs-0.300 = Fig 4 (own
    panel), 1.72× NO-GO = Fig 3 highlighted cell + §5.3 prose — PASS;
(d) no claim requires a number absent from the ledger; the only ledger-external content is
    qualitative Fig 1 (existing viz assets, marked) — PASS. No [NO-DATA] markers needed.
