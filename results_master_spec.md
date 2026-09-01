# Path-C convergence milestone: RESULTS_MASTER.md — the frozen claim ledger

STATUS: experiments FROZEN. Three-way consensus (you + agy, this fire) = stop running
controls, converge the paper. No new gates. This task is WRITING/consolidation only —
no new numbers, only numbers already in committed result files. If a number is not in an
existing out/*.json or *.md, DO NOT invent it; flag it as [NEEDS-SOURCE] instead.

DELIVERABLE: write out/RESULTS_MASTER.md — the single canonical claim ledger the paper
draws from. Structure:

## 1. Contribution A — temporal coherence (CORE)
- Lead with INTERIOR STABILITY at matched precision AND density: 1.98x–29.9x pop>2px
  reduction vs oracle rigid-flow EMA (strongest 2D baseline), >=9.8x vs memoryless.
  NEVER write "temporal coherence" unqualified — always "interior stability at matched
  precision/density."
- The controls lattice as the strength (depth-over-breadth, per your synthesis):
  2 scenes x 3 trajectories x 3 detectors x {memoryless, oracle-accumulated} baselines
  x matched precision-and-density. Tabulate every PARETO-1/2/3 cell with its frozen gate
  verdict INCLUDING the two we failed (PARETO-1 chair Canny150/300 mean-ratio 2.42x < 3x;
  PARETO-2 lego T3 spline 1.72x < 2x).
- Operational envelope (agy's directive): state the failure boundary explicitly. OURS is
  WORSE inside disocclusion (0.407 vs 0.300); the single non-winning cell is the one
  dominated by silhouette/occlusion flux => boundary is PREDICTABLE not random. PARETO-3
  33.3% < 60% => no disocclusion-mechanism sentence; residual is diffuse interior EMA drift.
- Scope statement (dss9's directive): claim explicitly scoped to "frozen 3DGS of static
  scenes with known poses"; the n=2 / perfect-geometry limitation named as future work.

## 2. Contribution B — ceiling characterization (4-act negative-result methodology)
Pull the frozen verdicts from committed commits/files:
- Coverage ceiling (re-ranking vanilla-3DGS pool caps recall 0.79 chair / 0.56 lego).
- K_geom~0 (normals/depth/SH-DC/PCA/2DGS/GT-mesh all AUC~0.5 crease-vs-texture on decals).
- Phase 1c discriminator kill-test GO: DINOv2 xsplit 0.840 chair / 0.904 lego, guarded
  chain 0.821/0.891 — but honestly = surface-identity readout, not edge-type detection.
- Phase 1d mesh-free supervision NO-GO: probe collapses 0.8401->0.6371 chair (bar 0.72).

## 3. The two failed gates, disclosed up front (honesty as method)
A short subsection listing every gate we froze and failed, and why we did not re-tune.

RULES: mesh-never-in-method-path invariant stated. Every number cited with its source
file. Mark anything you cannot source as [NEEDS-SOURCE]. This is the paper's spine —
be exhaustive on what is banked, ruthless about not overclaiming. ~60-90 min, no code
execution needed beyond grepping existing result files for exact numbers.
