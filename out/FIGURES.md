# FIGURES.md — path-C figure notes (rendered from FROZEN jsons; drift gate 27/27 vs RESULTS_MASTER.md)

Every plotted value was asserted against the ledger to its stated precision before rendering
(`scripts/render_figs.py`, log in the run output: 27 checks, 0 mismatches). Rendered:
`fig3_pareto2.png`, `fig4_pareto3.png`, `fig6_ceiling.png`, `fig8_supervision.png`.

- **Fig 3** (`fig3_pareto2.png`, from `pareto2_verdict.json`): OURS' worst-shared pop>2px
  advantage over the *strongest possible* temporally-accumulated 2D baseline (exact rigid
  flow + occlusion-aware EMA — an upper bound on every RAFT variant): 5.19× / 5.49× /
  8.35× per condition, with the lego×T3 **1.72×** cell flagged in red as the **frozen
  conservative lower bound** — even against an oracle accumulator, object-space lines are
  never worse, and the one sub-2× cell is the maximum-occlusion-flux condition, disclosed
  as the claim's boundary, not buried.

- **Fig 4** (`fig4_pareto3.png`, from `pareto3_lego_T3_disocc.json`): where the 1.72×
  lives — the advantage is **interior stability** (rate 0.0425 vs 0.0214 = 1.98× over the
  93–97 % interior), while inside disocclusion regions **OURS is worse** (0.407 vs 0.300,
  self-disclosed); the right panel shows the mechanism gate landing at **33.3 %** (NO-GO):
  the accumulator's residual is diffuse interior EMA drift, so the paper makes no
  disocclusion-mechanism claim — the bound is empirical and honestly scoped.

- **Fig 6** (`fig6_ceiling.png`, from `cap_miss_attribution_*.json`,
  `dexprimary_p0_*_native.json`, `dexprimary_p0_lego_ms_thr005.json`,
  `dexprimary_p1b_chair_ref40.json`): Act 1 — the frozen carrier caps pipeline recall at
  0.7908 / 0.5572 (pool coverage 0.7382 / 0.6337, lego UNCOVERED 0.3663); Fig 6b — the
  recovery ladder: single-view photometric lifting is chance-equal (0.0952 vs 0.0940),
  multi-view triangulation is a real localization fix yet stays detector-bound MARGINAL
  (0.6753 / 0.6914) — the ceiling is a property of the representation, not of any one
  recovery trick.

- **Fig 8** (`fig8_supervision.png`, from `dexprimary_p1d.json`): Act 4 — the
  **existence proof plus its falsification**: the crease-vs-texture signal EXISTS in
  frozen DINOv2 features (mesh-supervised 0.8395 / 0.9046; Act-3 xsplit 0.8401 / 0.9044)
  and we falsified our own success — under the best mesh-free supervision it collapses to
  0.6371 / 0.6569, through the frozen 0.72 bar. This is a fundamental supervision bound
  characterized by construction, not a failed attempt: the right panel's asymmetric
  transfer (0.8245 chair→lego vs 0.5626 back) marks the one future-work route the bound
  leaves open.
