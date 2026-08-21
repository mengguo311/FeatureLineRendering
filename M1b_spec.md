# Tier-1 / M1b — 3D Linelet DT-Pull (the hero: sub-pixel NPR feature lines from frozen 3DGS)

**Context:** M1a is done. It produces object-space CREASE SEEDS (gaussian subset) from a FROZEN vanilla
3DGS, mesh-free. Validated finding: the C_N normal-structure-tensor is DEAD on vanilla 3DGS (≈chance);
the working seed proposer is the "OVERALL recipe" (rendered dihedral-ridge + planarity C0 residual +
multi-view Canny-DT + local competition). Seeds are a HIGH-RECALL PROPOSAL (an RPN for 3D curves):
their CENTERS sit within a 5px basin of the true crease (precision 0.77@2.5px but 0.91@5px — the 22%
"miss" at 2.5px is carrier JITTER, not false positives; measured by tolerance sweep + BCR CR@5=1.0).
M1b's job: take each seed, attach a 3D LINELET, and PULL it to sub-pixel alignment using the multi-view
2D-edge distance transform, so the residual jitter is removed and the output is a temporally-coherent
NPR line rendering. This is the whole thesis: coarse object-space carrier × image-space sub-pixel corrector.

**HARD INVARIANT — mesh-never-in-method-path.** The method touches ONLY the 3D gaussians + the training
RGBs + cameras. The GT mesh is used EXCLUSIVELY in eval (mesh_oracle.py) to score precision/recall.

## Environment & assets (dss9)
- conda env `vfsdgs`: `source ~/bin/miniconda3/etc/profile.d/conda.sh; conda activate vfsdgs`
  (torch2.3+cu121, cv2, plyfile, trimesh, scipy). `CUDA_VISIBLE_DEVICES=1` (GPU tight ~3GB free).
- Working dir: `~/3dgs_line/tier1/`. M1a code already there:
  - `src/render.py` render_gbuffer(g, keep, cam) -> {depth,normal,alpha}
  - `src/visibility.py` visible_mask(pts, cam, depth) -> (mask, uv, z)
  - `src/common.py` load_cameras(scene), ply load (sigmoid opacity, exp scale, quat->R)
  - `src/mesh_oracle.py` EVAL-ONLY: GT crease pixels per view, precision/recall harness
  - `scripts/tune_lib.py` Harness(scene): .X (defloatered centers), .opa, .cams, .rgb_paths,
    .gbufs, .evaluate(pos, extra_mask, tau_p, tau_r, per_view)
  - the seed recipe: `scripts/explore/syn/final_recipe.py` (score_from_evidence, mode="overall")
    and `scripts/explore/syn/run_final.py` (end-to-end driver, caches final_evid_{scene}.npz,
    writes finalscore_overall_{scene}.npy). Reuse these to GET the seeds; don't rebuild.
- Scenes: chair (dev), lego (stress), ficus (failure-analysis). 100 NeRF-synthetic views, 800x800, f=1111.

## The seed set (M1a output you consume)
Run/reuse run_final.py to get, for a scene, the OVERALL score per de-floatered gaussian; take the top
**f=0.30** fraction as seeds S (chair: recall≈0.80 @2.5px, precision@5px≈0.88). Each seed = a 3D point
p0_i (gaussian center). This is your linelet initialization set.

## M1b method — implement under src/ and scripts/

### src/linelet.py — linelet representation + init
- Linelet L_i = (p_i ∈ R^3, t_i ∈ S^2 unit tangent, l_i half-length). p_i init = seed center p0_i.
- l_i init = local splat scale (median exp(scale) of the seed's kNN gaussians).
- t_i init = **local 3D PCA** of neighboring SEED positions within radius R=3×median-splat-scale
  (first principal component). (C_N tangent is dead — do NOT use it.)
- Keep p0_i stored (needed for the trust-region constraint).

### src/dt_pull.py — the optimizer (torch autograd through projection)
- Precompute per training view: 2D edge map (blurred-Canny union, same cfgs as final_recipe:
  ((2.0,100,200),(2.5,75,150))), its DISTANCE TRANSFORM DT_k, and a BILINEAR-samplable torch tensor
  of DT_k (so gradients flow through π_k(p)). Also cache gaussian depth buffer D_k for visibility.
  Cache to ~/3dgs_line/tier1/cache/ (dt maps can be float16; ~100*800*800*2B ok).
- Visibility per linelet per view: visible iff |z_lin - D_k(π_k(p))| < 0.02*z_lin (3x3 min window).
- Loss per linelet:
    E(p_i,t_i) = Σ_{k visible} w_k · Huber( DT3_k )  +  λ_s · smoothness
  where DT3_k = (1/3)[DT_k(π_k(p - l·t)) + DT_k(π_k(p)) + DT_k(π_k(p + l·t))]   (3-point directional
  sampling — GUARD 2: forces the whole segment onto a linear 2D feature, resists perpendicular snap
  into isolated texture edges).
  Huber δ≈2px. w_k = 0 if occluded in view k (GUARD: visibility). Optionally down-weight a view where
  the projected tangent J_πk·t is orthogonal to the local 2D edge direction.
- **Trust region (GUARD 1, δ_max=5px = measured jitter radius):** hard-constrain
  max_k ||π_k(p_i) - π_k(p0_i)|| ≤ 5px. Implement by projecting the update / clamping, or a penalty
  that hard-saturates. A linelet must NOT drift >5px in any view from its seed — prevents cross-feature
  jumps to a parallel texture edge.
- Optimize p_i (and optionally t_i, l_i) with Adam, ~50-100 steps, all linelets in parallel batched on GPU.

### src/linelet_prune.py — multi-view consensus pruning (GUARD: kills silhouette contamination)
- After optimization, for each linelet compute inlier ratio = fraction of visible views with
  DT_k(π_k(p_i)) ≤ 1.5px. **Prune if inlier ratio < 0.50.** True static 3D creases hit ≥80% multi-view
  consensus; view-dependent silhouettes fail multi-view triangulation and are culled. Also prune if
  post-opt median residual > 1.5px.

### scripts/run_m1b.py — end-to-end driver + eval
- For scene (chair first): load seeds (f=0.30 from run_final), init linelets, run dt_pull, prune.
- Report, BEFORE vs AFTER dt-pull, using the M1a harness (mesh_oracle, EVAL ONLY):
    * precision@1.5px, recall@1.5px  (the END-TO-END GATE)
    * also @2.5px for continuity with M1a numbers
    * n_linelets before/after prune, runtime, peak VRAM
- **END-TO-END GATE (the real one): P@1.5px ≥ 85%, R@1.5px ≥ 75% on chair.**
  (M1a alone was P@2.5=0.77; if DT-pull works, post-pull P@1.5 should JUMP because we're removing the
  measured 2.5-5px jitter. That jump IS the thesis result.)
- Visualization: for chair v0 and v25, a 3-panel PNG {RGB | seeds projected (before) | pulled+pruned
  linelets projected (after)} to ~/3dgs_line/tier1/out/m1b_{scene}_v{idx}.png. Draw linelets as short
  segments (p±l·t projected), colored by inlier ratio.

## Temporal-coherence check (the payoff — do after the gate passes on chair)
- scripts/temporal_m1b.py: render the SAME pulled 3D linelets across a smooth camera orbit (interpolate
  ~30 poses between train views), project each frame. Compare temporal warping error vs the M1a
  IMAGE-SPACE baseline (lines_image.py per frame):
    E_temp = mean_t || L_t - reproject(L_{t-1}, flow) ||   — but since linelets are STATIC 3D, their
    projection is exact per frame by construction (zero per-pixel flicker) vs the image-space lines
    which recompute per frame and jitter. Quantify: count of on/off flipping pixels per frame,
    object-space linelets vs image-space baseline. Expect a large reduction (the whole selling point).

## Definition of done
1. `python scripts/run_m1b.py --scene chair` prints BEFORE/AFTER precision/recall @1.5px and @2.5px,
   and reports whether P@1.5≥85% ∧ R@1.5≥75% PASS. Report ACTUAL numbers, not just PASS/FAIL.
2. Writes m1b_chair_v0.png / v25.png 3-panel visualizations.
3. Run lego too (stress) and report honest numbers (lego has the carrier-void hard tail; if it underperforms
   chair that is expected — report which gate it misses and why).
4. If the gate fails on chair, diagnose: is it (a) DT basin multi-modality (seed snapped to parallel
   texture edge — check δ_max, 3-point sampling), (b) visibility errors (occluded linelet saw wrong edge),
   (c) silhouette contamination (consensus prune too weak/strong)? Report which and what you tuned.
5. Do NOT git commit until I review the numbers. Stop after run_m1b + temporal check and show the table.

## Pitfalls
- Reuse the working camera convention (blender c2w -> opencv w2c via diag(1,-1,-1,1) then invert) — it's
  proven in bcr/ and tier1/. Verify seed projection lands on the object in v0 before optimizing.
- Keep gaussian z-buffer (method) and mesh depth (eval) as SEPARATE functions; method never imports mesh_oracle.
- Batch all linelets on GPU; don't python-loop per linelet per view (M1a's run_final shows the vectorized pattern).
- DT must be sampled bilinearly from a torch tensor so autograd reaches p_i through π_k.
