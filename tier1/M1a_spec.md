# Tier-1 / M1a — Gaussian Line Extraction Infrastructure & Baseline

**Context:** Research project = post-hoc feature-line extraction + NPR line rendering from a FROZEN
vanilla 3DGS (no mesh, no retraining). This is milestone M1a: build the infrastructure (G-buffer,
seeds, DT cache, visibility), the image-space line BASELINE (the flicker control condition), and an
honest validation gate against a GT-mesh crease oracle. The hero (M1b: 3D linelets + multi-view DT
pull + temporal coherence) comes next and CONSUMES M1a's outputs.

**HARD INVARIANT — mesh-never-in-method-path:** the METHOD operates ONLY on the 3D Gaussians
(μ, Σ from scale+quat, opacity, SH). The GT mesh is used EXCLUSIVELY inside `mesh_oracle.py` for
evaluation. Depth/normal rasterization, de-floatering, C_N seeds, gaussian z-buffer visibility, and
(later) DT optimization must have ZERO mesh dependency, so results transfer to real captures.

## Environment & assets (dss9)
- conda env `vfsdgs`: `source ~/bin/miniconda3/etc/profile.d/conda.sh; conda activate vfsdgs`
  (torch2.3+cu121, cv2, plyfile, trimesh, scipy). Use `CUDA_VISIBLE_DEVICES=1` (GPU tight, ~3GB free).
- Vanilla 3DGS plys: `~/cglib/outputs/{chair,lego,ficus}_static/point_cloud.ply`
  (props: x y z, nx ny nz, f_dc_*, f_rest_*, opacity, scale_0/1/2, rot_0/1/2/3 quat).
- Cameras + RGB: `~/cglib/data/full/{scene}/transforms_train.json` (blender: camera_angle_x + per-frame
  4x4 c2w transform_matrix; file_path like "./train/r_0"), RGB in `~/cglib/data/full/{scene}/train/r_*.png`
  (800x800 RGBA). focal f = 0.5*W/tan(0.5*camera_angle_x) = 1111.11 for these.
- GT meshes (EVAL ONLY): `~/3dgs_line/bcr/meshes/NeRF_Mesh/{scene}_new.obj`.
- Reference code you can reuse (already working, in `~/3dgs_line/bcr/`): camera projection
  (blender c2w -> opencv w2c via `diag(1,-1,-1,1)` then invert), mesh depth rasterizer (centroid
  z-buffer in torch), KD-tree over gaussians, ply loading with sigmoid(opacity) and exp(scale).
- Put all new code under `~/3dgs_line/tier1/` (src/ + scripts/). This is inside the git repo
  FeatureLineRendering; commit when the gate passes.

## Per-gaussian normal
Normal = shortest-covariance axis. Build R from the quaternion (rot_0..3, w-first; normalize first),
S = diag(exp(scale)). The covariance principal axes are R's columns; the normal is the column with the
smallest scale. Orient toward the camera (flip so n·(cam_center - μ) > 0) at projection time.

## Modules (all under src/)

### render.py — lean gaussian G-buffer (NO diff-gaussian-rasterization, NO fancy EWA)
- Input: gaussian arrays + one camera (K, w2c, H, W).
- De-floater: keep opacity>0.1 AND kNN-mean-dist < 3×median(kNN). (kNN via scipy cKDTree, k=8.)
- Splat each kept gaussian as a small disc: screen radius r_i = clamp(scale_max,i * f / z_i, 1, ~15) px.
  Front-to-back alpha compositing (sort by z) accumulating: depth D=Σ T_i α_i z_i, normal
  N=normalize(Σ T_i α_i n_i), alpha A=Σ T_i α_i, with T_i=Π(1-α_prev). α_i can be the gaussian
  opacity attenuated by a gaussian falloff within the disc (cheap approx is fine — this is for lines,
  not photorealism). Vectorize on GPU; a per-gaussian scatter with z-sorting is acceptable.
- Output dict of torch tensors: {"depth":[H,W], "normal":[H,W,3], "alpha":[H,W]}.

### lines_image.py — image-space line BASELINE (the flicker control)
- Input: G-buffer dict.
- depth-discontinuity: Sobel gradient magnitude on normalized inverse-depth, threshold τ_d.
- normal-crease ridge: κ_N = ||∇²N|| (Laplacian magnitude on the 3-channel normal), threshold τ_n.
- combine masked by alpha: I_line = (I_depth OR I_normal) AND (A>0.5). Output bool [H,W].
- Thresholds as CLI/const params; pick sane defaults, expose for tuning.

### seeds.py — object-space crease/corner seeds via normal-structure-tensor C_N
- Input: gaussian centers X[N,3], per-gaussian normals n[N,3], k=16.
- C_N^(i) = mean over kNN of (n_j - n̄_i)(n_j - n̄_i)^T. Eigen λ1≥λ2≥λ3, eigenvecs e1,e2,e3.
- crease saliency s_crease = λ1 - λ2, crease tangent t_i = e3. corner saliency s_corner = λ2 - λ3.
- keep seeds with s_crease > τ_seed; non-max-suppress along e1 within local kNN.
- Output npz: pos[M,3], tangent[M,3], saliency[M], type[M] ('crease'|'corner').

### dt_field.py — multi-view 2D edge + distance-transform cache
- For each of the 100 train RGBs: Canny (τ_low=50, τ_high=150 on 0-255 grayscale; composite RGBA over
  white first), then cv2.distanceTransform(1-edge, DIST_L2, 5). Also Sobel grads of DT for later autograd.
- Cache to disk: dt_maps[V,H,W] float16, dt_grads[V,2,H,W] float16 (npz or .npy; ~100*800*800*2B ≈ 128MB ok).
- (TEED/PiDiNet is an optional later upgrade; Canny first.)

### visibility.py — METHOD-PATH occlusion cull (gaussian z-buffer ONLY, no mesh)
- Input: 3D points P[M,3], camera, the render.py gaussian depth D[H,W].
- Project P -> (u,v), camera depth z_P. Sample z_buf=D[round(v),round(u)] (use a 3x3 min window to
  avoid single-pixel dropout at depth steps). Visible iff z_P ≤ z_buf + 0.02*z_P.
- Output bool mask [M] per view.

### mesh_oracle.py — EVAL ONLY (imports mesh; never called by method modules)
- Load {scene}_new.obj (trimesh, concatenate if Scene). Crease edges = face_adjacency_edges where
  face_adjacency_angles ≥ 30°. Render GT mesh depth per view (reuse bcr centroid z-buffer) for occlusion.
- Provide: project GT crease points to a view with GT-depth occlusion culling -> 2D crease pixel set,
  and the 3D crease points, for precision/recall scoring.

### scripts/verify_m1a.py — validation + visualization harness
- Scenes chair (primary) + lego (stress), views 0 and 25.
- 4-panel PNG per (scene,view): [RGB | image-space lines | raw seed projection | occlusion-culled seeds
  with tangent ticks]. Save to ~/3dgs_line/tier1/out/verify_m1a_{scene}_v{idx}.png.
- GATE (compute vs mesh_oracle, print to stdout):
   * Seed precision: ≥80% of visible projected seeds (chair) within ≤2.5px of a projected GT-mesh crease.
   * Crease recall: ≥70% of visible GT-mesh crease lines have a projected seed within ≤3.0px.
   * Advisory (report only): median seed→nearest-2D-Canny-edge distance (≤2.0px is a good sign).
   * Budget: total runtime <15s for the 2 views (excluding one-time DT cache); peak VRAM <1.5GB.

## Definition of done
- `python scripts/verify_m1a.py --scene chair` prints precision≥80% recall≥70% PASS and writes the
  4-panel PNGs for chair v0/v25 and lego v0/v25.
- Report the actual numbers (don't just claim PASS). If a gate fails, tune thresholds
  (τ_seed, τ_d, τ_n, k) and report what moved it; if it structurally can't pass, say why.
- Commit to the FeatureLineRendering repo under tier1/ with a short message; push (SSH remote already set).

## Notes / pitfalls
- Verify camera convention on view 0 by overlaying seed projection on RGB — must land on the object,
  not mirrored/rotated. (BCR already proved diag(1,-1,-1,1) works with these cams — reuse it.)
- Keep the gaussian z-buffer and the mesh depth rasterizer as SEPARATE functions; never let the method
  import mesh_oracle.
- If diff-gaussian-rasterization is importable and fast enough it's fine to use for the depth buffer,
  but the hand-rolled splat must exist as the portable fallback and is the primary path.
