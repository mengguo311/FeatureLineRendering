# STEP-06: NPR vector/stroke renderer + temporal-coherence PAYOFF metric

## Why (state)
Both separation gates are FALSIFIED on held-out TEST:
- geometry gate: fabric dihedral theta_p95=79 vs crease theta_p05=5 (total overlap)
- albedo SH-DC step gate: chair AUC(fabric>crease)=0.31, lego=0.50 (crease step >= fabric step)
Stop chasing a 3rd separation signal. Fabric pseudo-geometry is baked into the frozen splats.
SOLID result to cash in: temporal flicker object-space floor ~ZERO vs image-space 0.71pct (>4-5x, held-out).

## Task: build the vector renderer + make the temporal claim airtight END-TO-END.
Invariants: mesh-never-in-method-path (mesh eval/label ONLY). Held-out TEST views only. Do NOT regress temporal win. NO commit/push unless I explicitly say so.

1. CHAIN DT-pulled linelets -> polylines (stroke graph). Reuse existing DT_pull field. Simple: NMS + hysteresis link + junction split. Render strokes (SVG or raster stroke buffer).

2. HEADLINE METRIC (must report, not just pictures): forward-warped STROKE temporal residual on a moving camera.
   For adjacent frames t,t+1: forward-project each stroke s_i using OBJECT-SPACE carrier motion W(t->t+1); measure min Frechet(or Chamfer) to nearest stroke in frame t+1; PLUS a popping penalty P_pop = fraction of strokes with no match (vanish/appear) + topological-cut count.
   Compare TWO pipelines head to head on the SAME camera path:
     (A) OURS: object-space carrier + sub-pixel DT corrector -> strokes
     (B) BASELINE: naive image-space Canny -> vector strokes (no object-space carrier)
   Report on lego (PRIMARY) and chair (STRESS). Frame counts 30/60/120/240 like temporal table.

3. ABLATION (do NOT put in headline, report separately): carrier-persistence prune — drop stroke-graph components whose 3D carrier fails to project stably across >=k views BEFORE chaining. Show its effect on chair FP-density AND on the popping metric. This is an honest ablation, NOT a fix for the gate. Do NOT reframe texture FPs as intentional hatching in the metrics.

Output: out/m1b_vector_{lego,chair}_{A,B}.svg/png + out/m1b_stroke_temporal_table.{json,md} with Frechet + P_pop for A vs B across frame counts. Print a compact summary table when done.
