# SHIP-PREP MILESTONE 1 — lego threshold-robustness audit (de-risk before figures)

CONTEXT: X+Y retrain-falsify is DONE and KILLED the retraining pivot (committed b04be95).
We now SHIP the frozen thesis. Your own synthesis flagged an unexploded shell: lego's GT
crease set has a single ~213,711-edge family at exactly 30.000 deg, split ~half by the oracle's
30 deg threshold via 6-decimal vertex rounding in lego_new.obj; a +0.05 deg nudge moved lego
3D recall 0.2112 -> 0.2928 and halved the miss-set (§X.3 of out/XY_RETRAIN_FALSIFY_RESULTS.md).
That knife edge is inherited by ALREADY-COMMITTED lego claims (out/CAP_RESULTS.md,
out/cap_miss_attribution_lego.json, out/LEGO_CEILING_AUTOPSY.md, and propagated copies in
out/RESULTS_MASTER.md, out/PAPER_DRAFT.md). We audit BEFORE cutting figures so there is zero
rework risk. Mesh EVAL-ONLY, held-out, never fabricate.

TASK (cheap-first, no GPU where possible):
1. FREE PRE-CHECK (no GPU): from the banked per-point arrays out/xy/xy_expX_lego_p1c.npz and
   out/xy/xy_expX_chair_ref40.npz (keys theta0_pt, rec3, seen_idx), recompute lego + chair
   3D recall vs oracle threshold on {30.00, 30.05, 31.0, 45.0} deg. This needs no re-render.
2. IF the pre-check shows the lego ordering could flip, do the minimal re-score sweep using the
   already-parameterized src/mesh_oracle.py::MeshOracle(angle_deg=), scripts/tune_lib.py::
   Harness(angle_deg=), scripts/dexprimary_p0.py::gt_labels(angle_deg=) over {30,30.05,31,45},
   regenerating only cache/dexp0_gt_lego_a*.npz + cache/oracle_lego_a*_v*.npz and re-scoring the
   frozen clouds out/dexprimary_p1c_cloud_lego.npz + out/dexprimary_p1b_cloud_chair_ref40.npz.
   Touch ONLY u00134 procs, CUDA_VISIBLE_DEVICES=1.
3. Explicitly VERIFY (and state) that the crown-jewel temporal 7-13x is mesh-free and CANNOT move
   with the oracle threshold, since src/stroke_metric.py + scripts/m1b_stroke_temporal.py never
   read the mesh. Preempt the reviewer.

FROZEN GO/NO-GO (decide from the sweep, report straight):
- SURVIVE: if lego's qualitative "coverage-ceiling" conclusion holds at EVERY threshold in the
  sweep (recall stays materially below the P@1.5>=0.85 precision gate; the pool-caps-recall /
  decal-wall narrative does not reverse) -> convert into a ONE-paragraph robustness note + a
  supplementary recall-vs-threshold table (both scenes), and PATCH the propagated numbers in
  out/RESULTS_MASTER.md + out/PAPER_DRAFT.md to report the threshold-sensitivity HONESTLY
  (state the +0.05 deg effect and that it is asset-quantization, not method). Then the crown-jewel
  figure set is cleared to ship next fire.
- FLIP: if at any audited threshold lego's coverage-ceiling conclusion no longer holds
  (recall rises enough to break the ceiling narrative) -> STOP, do NOT cut figures, write
  out/LEGO_THRESHOLD_AUDIT.md flagging exactly which committed claims need revision, and hold.

DELIVERABLE: out/LEGO_THRESHOLD_AUDIT.md with the two-scene recall-vs-threshold table, the
SURVIVE/FLIP verdict against the rule above, the mesh-free-temporal confirmation, and a list of
any committed files patched. Write scripts under scripts/xy_thresh_audit.py. No commits by you;
the orchestrator commits after review.
