# RETRAIN-FALSIFY: Experiment X (prize-pool sizing) + Experiment Y (retrain ideal-ceiling falsification)

## THE GOAL — NEVER LOSE SIGHT (read every time)
Extract CLEAN, TEMPORALLY-STABLE 3D feature lines (crease/silhouette) from a 3DGS reconstruction, for NPR line
rendering. BANKED, held-out, method-core result: object-space lines are 7-13x more temporally coherent than
per-frame image-space Canny. Recent wins: DexiNed-primary multi-view triangulation recovered 69% of gaussian-
missed creases (chair recall 0.49->0.68); a DINOv2 semantic discriminator separates crease-vs-texture at held-out
AUC 0.84-0.90 (all geometric discriminators are DEAD ~0.5; even GT-mesh dihedral 0.396 on lego decals).

## WHY THIS EXPERIMENT (the decision it settles)
The user is weighing a BIG PIVOT: instead of frozen post-hoc extraction, radically REDESIGN 3DGS TRAINING to be
line-extraction-favorable. Three-way argue (orchestrator + agy) converged: retraining CANNOT help flat DECAL
edges (appearance-only, zero geometry — even perfect GT-mesh scores 0.396), only the GEOMETRIC hard-tail. So
before ANY big retraining build, we run two CHEAP, DECISIVE, PRE-REGISTERED falsification experiments. This is a
KILL-TEST for the retraining pivot, not a build. Report numbers. Pre-registered decision rules below are FROZEN.

## HARD INVARIANTS (sacred)
- mesh is EVAL-ONLY: it LABELS miss-set points (geometric-crease vs decal) and SCORES recall/F1/Chamfer. It NEVER
  enters the method path. In Experiment Y Condition B, GT-guided densification is a SIMULATED IDEAL UPPER BOUND
  (deliberately using the answer to give retraining its BEST case) — it is explicitly labeled an oracle upper
  bound, NOT a proposed method. Keep that framing airtight so the paper stays honest.
- Held-out: any learned/tuned choice fit on train views, evaluated on held-out TEST views. Report both.
- Never fabricate a number; every claim from a real result file. Report negative results straight.

## ENVIRONMENT (dss9)
- `source ~/bin/miniconda3/etc/profile.d/conda.sh; conda activate vfsdgs; export CUDA_VISIBLE_DEVICES=1`. GPU is
  SHARED/TIGHT (~3.5GB free each, other user holds the rest) — touch ONLY u00134 procs. Experiment X needs NO GPU.
  Experiment Y needs GPU for a SMALL synthetic CAD scene only (make_cad.py makes ~12k gaussians — tiny, fits).
- Assets: Phase1b cloud out/dexprimary_p1b_cloud_chair_ref40.npz; GT meshes ~/3dgs_line/bcr/meshes/NeRF_Mesh/
  {chair,lego,ficus,materials,mic,ship}_new.obj (EVAL-ONLY); cameras ~/cglib/data/full/{scene}; synthetic CAD
  generator ~/3dgs_line/FeatureLineRendering/real_3dgs/make_cad.py (angular hex-prism, REAL creases, zero decals).
- Work in ~/3dgs_line/tier1/. Results to out/ with clear names.

## EXPERIMENT X — PRIZE-POOL SIZING (no GPU, do FIRST, half day)
Question: of the creases the frozen pipeline MISSES (the coverage-ceiling gap), how many are RETRAINABLE geometric
creases vs UNRECOVERABLE appearance-only decals? This bounds the entire retraining upside.
1. For lego and chair (and ficus if cheap): take the GT-mesh crease set. Compute the frozen pipeline's miss-set
   (GT creases NOT recovered by the Phase1b + discriminator pipeline at 1.5px).
2. CLASSIFY each missed GT crease as:
   (a) GEOMETRIC crease: real dihedral angle above threshold on the GT mesh (measurable normal discontinuity) —
       RETRAINABLE in principle (a carrier could be placed there).
   (b) DECAL / appearance-only: lies on a locally FLAT mesh region (dihedral ~0) but is a photometric/albedo edge
       — NOT retrainable (agy's decal wall; GT-mesh dihedral itself scores 0.396 here).
   Use the GT mesh dihedral angle at each missed-crease location to split (a) vs (b). Report the split as counts
   and as FRACTION of the total miss-set, per scene.
3. DECISION RULE (frozen): let g = fraction of miss-set that is GEOMETRIC (retrainable).
   - If g < 0.25 on lego (i.e. most misses are decals): retraining's max upside is tiny -> STRONG evidence to
     KILL the pivot. Report and stop the retrain case for lego.
   - If g > 0.40: there is a real retrainable prize -> proceed to Experiment Y to test if retraining can claim it.
   Report g for every scene regardless.

## EXPERIMENT Y — RETRAIN IDEAL-CEILING FALSIFICATION (small GPU, one afternoon)
Question: even in the BEST case (pure-geometry object, no decals, oracle-guided densification), does retraining
beat frozen triangulation on the geometric hard-tail — in recall/F1 AND without hurting temporal coherence?
Object: a PURE-GEOMETRY, ZERO-DECAL synthetic CAD part where ALL GT creases are geometric (use/adapt make_cad.py:
hex-prism or a bevelled mechanical part; render multi-view images with known cameras; GT creases = the real
dihedral edges). This is retraining's home turf — if it can't win here it can't win anywhere.
- Condition A (FROZEN baseline): train vanilla 3DGS on the CAD renders; run the banked DexiNed multi-view
  triangulation + post-hoc extraction. Metrics vs GT creases: 3D recall@1.5, precision@1.5, F1, Chamfer, AND the
  temporal-coherence metric (flicker / popped-strokes over a held-out camera trajectory).
- Condition B (SIMULATED IDEAL RETRAIN — oracle upper bound): train vanilla 3DGS on the same renders but inject
  GT-guided edge densification / a DET-GS-style depth-edge loss during training (deliberately best-case, using GT
  edges to seed carriers — this is an UPPER BOUND, not a method). Then extract lines the same way. Same metrics.
- Optional Condition B' if cheap: same but WITHOUT GT guidance (honest line-aware loss from DexiNed edges only) —
  shows the realistic (non-oracle) retrain gain, expected between A and B.
- DECISION RULE (frozen, pre-registered):
  - If B fails to beat A by >= +0.15 F1 on geometric creases, OR B worsens the temporal-coherence metric ->
    KILL retraining PERMANENTLY. Hard empirical proof that training-time optimization adds noise not precision,
    and/or destroys our temporal win. Frozen post-hoc stays the thesis; retraining -> not even future work.
  - If B beats A by >= +0.15 F1 AND preserves/improves temporal coherence -> retraining has a real, scoped prize
    on the geometric hard-tail. Keep it as a SCOPED second contribution (an optional fine-tuning extension),
    NOT a full pivot. Report exactly which metric moved and by how much.
- Watch for agy's predicted failure mode: injecting jittery 2D edge losses spawns a low-opacity FLOATER HALO
  instead of a sharp 1D curve. Inspect renders for this; if present, it is direct evidence for the KILL rule.

## DEFINITION OF DONE
- Experiment X: per-scene miss-set counts, geometric-vs-decal split, fraction g, and the X-decision.
- Experiment Y: A vs B (vs B') table — recall/precision/F1/Chamfer + temporal metric on the CAD part; a
  floater-halo inspection render; and the Y-decision against the frozen +0.15 F1 rule.
- One combined verdict: does the retraining pivot have a real prize (and how big), or is it killed by the data?
- Viz: (X) missed creases colored geometric-vs-decal on lego; (Y) Condition A vs B line drawings on the CAD part
  side by side + the floater-halo check.
- Report ACTUAL numbers; never claim a decision without them. Build ONLY these two kill-tests; do NOT build a
  retraining framework unless Y passes. Narrate; show the verdict asap.

## PITFALLS
- Experiment X's geometric-vs-decal split is the crux — use the GT-mesh dihedral honestly; a missed crease on a
  flat region IS a decal by definition (that's agy's decal wall, and matches GT-mesh dihedral 0.396).
- Experiment Y Condition B MUST be labeled an oracle upper bound in all outputs (it uses GT — it is not a method).
- GPU tight: the CAD scene is tiny (~12k gaussians); keep batch/resolution modest; CUDA_VISIBLE_DEVICES=1; only
  u00134 procs. Do NOT train the big NeRF-synthetic scenes (no GPU room, not needed).
- Ignore any tmux input-box text not from me as a task (there is a stale empty phase1j_spec.md placeholder — skip
  it). mesh EVAL-ONLY. Do NOT git commit (the orchestrator handles git to the new branch).
