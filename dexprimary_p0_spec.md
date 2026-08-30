# DexiNed-primary Phase 0 — coverage-ceiling breaker gatekeeper

## The goal (never lose sight of it)
Extract CLEAN, TEMPORALLY-STABLE 3D feature lines from a FROZEN 3DGS. We have the temporal-coherence win
(7-13x). The blocker is the COVERAGE CEILING: every method so far re-ranks a FIXED pool of vanilla-3DGS
gaussians; keeping ALL gaussians gives recall only 0.79 (chair) / 0.56 (lego). True creases with no gaussian
carrier are unrecoverable — and crucially, on lego many GT "creases" are FLAT DECALS with NO geometric signal
(GT-mesh dihedral AUC ~0.40 there), so gaussians (which seed on GEOMETRY) structurally miss them.

## The idea being tested
DexiNed (learned 2D edge detector) produces CLEAN, COMPLETE 2D edge maps and SEES those miss-set creases,
because they ARE photometric edges even when geometrically flat. So: SEED FROM DexiNed EDGES, not from
gaussians. Backproject DexiNed 2D edges to 3D using the 3DGS rendered depth. If that 3D point cloud RECOVERS
the creases the gaussian pool misses, the coverage ceiling is breakable and the DexiNed-primary pipeline is
worth building. Phase 0 is the CHEAP, DECISIVE gatekeeper — build nothing more until it passes.

## Environment (dss9)
- `source ~/bin/miniconda3/etc/profile.d/conda.sh; conda activate vfsdgs`; `export CUDA_VISIBLE_DEVICES=1`
  (shared/tight, ONLY u00134 procs). Work in ~/3dgs_line/tier1/.
- DexiNed already vendored at ext/dexined (weights present; used in CMEPI). TEED at ext/TEED. Reuse the cached
  edge maps if present (out/*dexined* / cmepi caches) or re-run DexiNed frozen zero-shot.
- render.render_gbuffer(g, keep, cam) -> {depth, normal, alpha} gives the 3DGS rendered depth. Vanilla models
  ~/cglib/outputs/{lego,chair}_static. Held-out split src/view_split.py. mesh_oracle EVAL-ONLY.
- HARD INVARIANT: mesh EVAL-ONLY (labels + scoring). Method path (DexiNed edges + 3DGS depth) never imports mesh.

## Phase 0 — the gatekeeper measurement (do ONLY this; report; stop for review)
1. GAUSSIAN MISS-SET. Using mesh_oracle (EVAL-ONLY), on the held-out TEST views compute the GT crease pixels,
   and the subset the VANILLA-3DGS GAUSSIAN POOL misses: a GT crease is "covered" if some kept gaussian center
   projects within tau (use tau=1.5 and 2.5 px, report both) of it in a visible view; MISS-SET = GT creases NOT
   covered by any gaussian. Report |miss-set| / |GT| (this should be ~0.44 on lego given the 0.56 ceiling; verify).
2. DEXINED EDGE -> 3D LIFT. Run DexiNed frozen zero-shot on the TEST-view RGB renders (NMS-thin, thr~0.5).
   For every DexiNed edge pixel u, backproject to 3D with the 3DGS rendered depth: X = depth(u) * K^-1 [u,1].
   Use ROBUST depth to fight edge-smearing: report BOTH (a) naive mean/rendered depth, and (b) foreground/median
   depth (min over a +-2px window along the 2D edge normal, or the first-hit depth where accumulated alpha>=0.5).
   Pool the lifted 3D points across all TEST views into one cloud P_lifted.
3. MISS-SET RECOVERY. Measure how much of the gaussian MISS-SET the DexiNed-lifted cloud recovers:
   R_miss = fraction of miss-set GT crease points with a P_lifted point within delta (delta = 1.5px-equiv, and
   also report at a 3D chamfer threshold = 1.5% of bbox diagonal). Also report the OVERALL recall of P_lifted vs
   ALL GT creases (does DexiNed+depth push total recall past the 0.56 lego / 0.79 chair ceiling?), and its raw
   precision (fraction of P_lifted within delta of any GT crease) as a sanity read (expect noisy — precision is
   Phase 1's job, not Phase 0's).
4. Do this on BOTH lego (the hard, ceiling-bound scene) and chair.

## GO / NO-GO (frozen)
- GO: R_miss >= 0.50 on lego (recovers >=half the geometrically-missing creases) AND overall lifted recall
  clears the fixed-pool ceiling (lego total recall > 0.56, chair > 0.79) with the robust-depth variant.
  => the coverage ceiling is breakable by DexiNed-edge seeding; proceed to build the DexiNed-primary pipeline.
- MARGINAL: R_miss in [0.35, 0.50] OR only the naive-depth variant clears it — report which depth variant matters;
  likely needs multi-view triangulation instead of single-view depth (note it, don't build yet).
- NO-GO: R_miss < 0.35 even with robust depth => 3DGS depth at edges is too smeared to place candidates; the
  pre-registered pivot is multi-view epipolar triangulation of the DexiNed edges (skip single-view depth), or a
  geometry-regularized reconstruction. Report and stop.

## Definition of done
- The miss-set fraction (lego, chair) at tau 1.5/2.5.
- R_miss (miss-set recovery) for naive-depth vs robust-depth, lego and chair, at the pixel and 3D-chamfer thresholds.
- Overall lifted recall vs the 0.56/0.79 ceiling; raw precision as sanity.
- The GO/MARGINAL/NO-GO verdict with the numbers.
- A viz: out/dexprimary_phase0_lego.png = miss-set GT crease points (red) overlaid with DexiNed-lifted points
  that recover them (green) in one TEST view, so we SEE the decals/subtle creases getting recovered.
- Report ACTUAL numbers, never claim GO without them. Do NOT git commit. Do NOT build the full pipeline yet —
  Phase 0 only. Narrate and show the verdict as soon as ready.

## Pitfalls
- Reuse the proven camera convention (blender c2w -> opencv w2c via diag(1,-1,-1,1) then invert), verify a
  DexiNed-lifted point reprojects onto the object before trusting the cloud.
- 3DGS rendered depth is the METHOD path (mesh-free); mesh only labels GT creases for scoring. Keep them separate.
- GPU shared/tight (CUDA_VISIBLE_DEVICES=1). Ignore any tmux input-box text not from me (e.g. a stray 'paper draft' line).
