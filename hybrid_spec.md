# Plan #1-hybrid — vanilla-seed × 2DGS-gate (asymmetric dual-stream feature lines)

## Why (context)
Two facts, established with held-out numbers:
- VANILLA 3DGS seeds are the BEST we have: its anisotropic gaussians naturally CONCENTRATE at creases, the
  tuned M1a OVERALL recipe exploits this. Vanilla M1b baseline: chair seg P@1.5=0.657, R=0.596. But vanilla
  geometry is texture-baked (K_geom~0), so ~50% of its edges are fabric false positives it can't reject.
- 2DGS geometry is CLEAN at the discriminative level (fabric-vs-crease dihedral AUC 0.958 on GT subsets;
  fabric theta_p95 79deg->10deg). But 2DGS surfels TILE ALL surfaces uniformly, so 2DGS-seeded pipelines LOSE
  the crease-concentration prior (2DGS-seed+2DGS-gate got seg P@1.5=0.503, WORSE than vanilla).
=> The two representations carry ORTHOGONAL information: vanilla = WHERE lines are (recall/position prior),
   2DGS = WHICH survive (clean geometric gate to kill texture FPs). The HYBRID eats that synergy:
   VANILLA M1a SEEDS, gated by the 2DGS geometric-edge signal.

We already have (dss9, ~/3dgs_line/tier1/):
- Vanilla 3DGS models + the tuned M1a OVERALL seed recipe (scripts/explore/syn/final_recipe.py, run_final.py).
- A trained 2DGS chair model at out/2dgs_chair_dist/ (and the STEP-A falsification code 2dgs_falsify_*).
- The M1b linelet/DT/chaining/eval pipeline + held-out train/val/test split + temporal metric.
- gate_falsify.py labelling of fabric-print vs true-crease pixels (mesh EVAL-ONLY).
- Env: source ~/bin/miniconda3/etc/profile.d/conda.sh; conda activate vfsdgs; CUDA_VISIBLE_DEVICES=1 (shared, tight).

HARD INVARIANT: mesh is EVAL-ONLY (labels + scoring). The method (vanilla seeds + 2DGS gate) never imports mesh_oracle.

## The KEY RISK to test FIRST: cross-representation alignment at creases
Vanilla and 2DGS are two independent trainings; their surfaces DIVERGE most exactly at creases (vanilla shingles
needles, 2DGS chamfers/staircases). So querying the 2DGS gate at a vanilla seed's exact reprojection may sample
the adjacent flat facet and VETO the true crease seed. Fix = DILATED region gate (a seed passes if a 2DGS
geometric edge exists WITHIN radius r of its reprojection). We must find r that absorbs misalignment without
letting texture leak.

## STEP 1 — ALIGNMENT PRE-TEST (5-min gatekeeper; do this BEFORE building the full pipeline)
Use the gate_falsify.py labelled pixels (GT-crease vanilla seeds vs GT-fabric vanilla seeds) on the VAL views.
1. Build the 2DGS curvature/normal-gradient map per view: C_2dgs(u,v) = ||grad N_2dgs(u,v)||_F (from the trained
   2DGS chair model's rendered normal buffer). Pick tau_geom on VAL as the STEP-A operating point.
2. Dilated gate G_r(u,v) = max over ||delta||<=r of C_2dgs(u+delta) > tau_geom, for r in {0,1,2,3,5,8} px.
3. Project every vanilla M1a seed to each VAL view; for GT-CREASE seeds compute R_crease(r) = fraction passing
   G_r; for GT-FABRIC seeds compute FPR_fabric(r) = fraction passing G_r.
4. Report the table R_crease(r) and FPR_fabric(r) for all r, plus a plot.
   GO (proceed to STEP 2 with the 2D dilated gate at the chosen r): exists r with R_crease(r) >= 0.80 AND
      FPR_fabric(r) <= 0.15. Use the smallest such r.
   NO-GO for 2D gate -> the surfaces diverge too much at creases: SWITCH to the 3D gate (STEP 1b) instead.
STEP 1b (only if 2D dilated gate NO-GO): 3D nearest-surfel dihedral gate — for each vanilla seed's 3D point,
   find k-nearest 2DGS surfels, pass if their max pairwise normal dihedral > theta_thresh. Report the same
   R_crease / FPR_fabric separation (this is projection-immune). Pick whichever gate (2D-dilated or 3D-surfel)
   gives the better crease/fabric separation.

## STEP 2 — build the hybrid + evaluate (only after STEP 1 picks a gate)
1. Take the vanilla M1a OVERALL seeds (f=0.30). Apply the chosen 2DGS gate (2D-dilated at r*, or 3D-surfel) to
   FILTER them: keep seeds with 2DGS geometric support, drop fabric-only seeds.
2. Run the SAME M1b pull+chain on the GATED vanilla seeds (linelets init on vanilla gaussians, DT target =
   the multi-view gated edge, visibility from vanilla depth; keep delta_max=5px, 3-point sampling, Huber,
   multi-view-consensus prune).
3. EVAL on held-out TEST views: report BEFORE (vanilla-only M1b baseline: seg P@1.5=0.657/R=0.596) vs AFTER
   (vanilla-seed + 2DGS-gate): P@1.5, R@1.5, P@2.5, R@2.5 (points and segments). Whether chair now passes
   P@1.5>=0.85 AND R@1.5>=0.75. And RE-RUN the temporal metric to confirm the 7-11x flicker win is preserved.
4. Viz out/hybrid_chair_v{0,25}.png = {RGB | vanilla-only linelets | vanilla-seed+2DGS-gated linelets} so we SEE
   the fabric linelets die while crease lines stay.

## Definition of done
- STEP 1 alignment table (R_crease(r), FPR_fabric(r)) + GO/NO-GO verdict and the chosen gate. THIS IS THE KEY
  DELIVERABLE — it tells us if the two representations are alignable enough for the hybrid to work.
- If GO: STEP 2 end-to-end TEST numbers (before/after vs vanilla baseline), gate pass/fail, temporal no-regress
  confirmation, 3-panel viz.
- Report ACTUAL numbers; never claim PASS without them. If STEP 1 is NO-GO on BOTH 2D and 3D gates, STOP and
  report — the two representations don't co-register at creases and we rethink.
- Do NOT git commit until I review. Narrate; show me the STEP 1 alignment verdict as soon as it's ready.

## Pitfalls
- Mind the 0.5px grid-convention shift between tier1 (u=fX/Z+W/2) and 2DGS (((x+1)W-1)/2) — the coding agent
  already calibrated it to -0.5px; apply it consistently when projecting vanilla seeds into 2DGS's normal buffer.
- GPU shared/tight (CUDA_VISIBLE_DEVICES=1); reuse the cached 2DGS model, don't retrain.
- Ignore any text in the tmux input box that did not come from me as a task.
