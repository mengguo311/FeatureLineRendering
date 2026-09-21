# Top-k Layered 3DGS Line Detection Implementation Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task only after user approval.

**Goal:** Use each pixel's top-k Gaussian IDs, camera-space depths, and compositing weights `T_i α_i` to detect layer-aware image evidence, lift it into persistent 3D candidates, and test whether it yields cleaner, more stable NPR line assets than depth-only or density-only methods.

**Architecture:** Separate the method into three objects: (1) calibrated per-pixel contributor distributions, (2) layer-aware 2D line evidence that never treats raw ID changes as lines by themselves, and (3) persistent 3D samples/paths aggregated across TRAIN views. The first experiment is a cheap falsification probe; it stops before 3D path tracing unless top-k evidence gives a visual and held-out advantage over depth-only controls.

**Tech Stack:** pinned vanilla 3DGS rasterizer/CUDA buffers, NumPy/PyTorch, SciPy/scikit-image for diagnostics, existing project TRAIN/F/C/DEV/TEST isolation and official camera intrinsics.

---

## 1. Scope and non-claims

- Frozen vanilla 3DGS only; no retraining, mesh, 2DGS, SDF, external normals, or learned edge detector.
- Use TRAIN views to construct and tune. Use F/C/DEV for frozen evaluation. Keep TEST sealed until a later full method exists.
- Final ink, if reached, must come from persistent 3D paths. Per-frame 2D maps are evidence only.
- The first probe tests identifiability and visual usefulness. It does not claim a final line renderer.
- Raw Gaussian-ID turnover is not a line cue by itself: neighboring splats on one smooth surface naturally exchange ownership.

## 2. Per-pixel contributor representation

For pixel `x`, save the first `k` contributors in front-to-back compositing order:

```text
C(x) = {(id_i, z_i, alpha_i, T_i, w_i=T_i alpha_i)} for i=1..k
```

Also save:

```text
A(x)       = Σ_i w_i                    accumulated top-k coverage
p_i(x)     = w_i / max(Σ_j w_j, eps)    normalized contributor mass
z_mean(x)  = Σ_i p_i z_i                expected top-k depth
z_var(x)   = Σ_i p_i (z_i-z_mean)^2     depth-layer ambiguity
H_id(x)    = -Σ_i p_i log p_i           contributor entropy
z_50(x)    = weighted median depth
```

Recommended initial `k`: `8`, with diagnostic reruns at `k=4` and `k=16`; `k` is not tuned per scene.

### Gate G0: exact buffer calibration

Before any line detector:

1. IDs are valid original Gaussian indices.
2. `z_i` is monotonically nondecreasing in stored front-to-back order, modulo documented equal-depth ties.
3. `w_i = T_i α_i` recomputes the native top-k accumulated alpha.
4. Top-k RGB replay plus residual transmittance matches the stock renderer within frozen tolerance.
5. `k=8` captures a preregistered fraction of native alpha; report missing tail rather than renormalizing it away.
6. Full camera intrinsics (`fx, fy, cx, cy`) and pixel-center convention match the official renderer.

Failure is `ENGINEERING_NOT_READY`, not scientific NO-GO.

## 3. Layer construction

Do not interpret rank `i` as one globally consistent surface. At each pixel, cluster contributors into depth layers using adjacent relative depth gaps:

```text
g_i = (z_{i+1}-z_i) / max(local_depth_scale(x), eps)
new layer if g_i > tau_gap
```

`local_depth_scale` is frozen from neighboring front-depth variation, not fitted per scene. Each layer stores:

```text
mass_l       = Σ_{i in l} w_i
z_l          = Σ w_i z_i / mass_l
ID histogram = {id_i : w_i/mass_l}
X_l          = camera ray point at z_l
```

Low-mass layers remain visible in diagnostics but cannot seed lines.

## 4. Evidence channels

### 4.1 Contributor-distribution discontinuity

For neighboring pixels `x,y`, compare normalized ID mass using a Bhattacharyya/Hellinger term:

```text
BC_id(x,y) = Σ over shared IDs sqrt(p_i(x) p_i(y))
D_id(x,y)  = sqrt(max(0, 1-BC_id))
```

This is permutation-invariant and respects contribution mass. However, `D_id` is only auxiliary. It may support a line only when accompanied by depth/layer evidence.

### 4.2 Front-layer depth discontinuity

```text
D_front(x,y) = |z_front(x)-z_front(y)| / local_depth_scale
```

Use robust, sign-aware directed depth ordering to label likely foreground/background sides.

### 4.3 Depth-distribution transport

Compare top-k depth distributions without IDs using a one-dimensional weighted Wasserstein distance:

```text
D_zdist(x,y) = W1({z_i,p_i}_x, {z_j,p_j}_y) / local_depth_scale
```

This distinguishes the value of depth layering from the value of persistent IDs.

### 4.4 Layer split/merge evidence

Detect spatial locations where:

- one depth layer becomes two;
- front-layer mass changes abruptly;
- contributor entropy or depth variance has a ridge;
- foreground/background ordering changes consistently across adjacent pixels.

This channel is intended for occlusion and disocclusion boundaries.

### 4.5 Within-layer shape ridge

For each sufficiently supported layer, compute a smooth layer-depth field and its multiscale Hessian. Detect broad positive/negative depth ridges and valleys separately. This is the candidate channel for internal shape/crease lines; it must not mix front and back layers into one expected depth.

## 5. Proposed line scores

Keep three line classes separate through evaluation.

### A. Occlusion-boundary score

```text
E_occ = support
        × robust(D_front or D_zdist)
        × robust(D_id)
        × front_mass_confidence
```

Require depth separation. ID change alone cannot activate `E_occ`.

### B. Layer-transition score

```text
E_layer = support
          × ridge(depth_variance / entropy / layer_count transition)
          × ordering_consistency
```

Use this only when a stable front/back split exists over a local neighborhood.

### C. Within-layer shape score

```text
E_shape = support_l
          × multiscale_depth_Hessian_response(z_l)
          × layer_identity_consistency
```

Keep ridge and valley polarity separate until visual review.

Do not combine A/B/C into one score in the first probe. A union may be shown only as an additional diagnostic.

## 6. Broad-line extraction

Avoid the previous global Top-6% failure mode.

1. Normalize each evidence channel with frozen robust scales.
2. Use high-threshold NMS points only as anchors.
3. Run orientation-aware hysteresis through a lower response threshold along the local tangent.
4. Permit continuation only when depth class, contributor distribution, and tangent remain compatible.
5. Generate width from the winning detector scale rather than a fixed three-pixel band.
6. Preserve a soft-alpha response rendering alongside every binary band.
7. Do not pool threshold competition across scenes for the visual output. Pooled/matched-ink masks remain controls only.

Frozen threshold bands should be preregistered as a small grid, for example high/low percentiles `(95/70, 90/60)`, not tuned independently per scene.

## 7. 2D-to-3D lifting

For each accepted evidence sample, avoid using only the Gaussian center.

### Occlusion sample

- Foreground point: ray point at front-layer depth `X_front`.
- Persistent provenance: weighted foreground ID histogram plus dominant foreground/background ID pair.
- Store camera, pixel, depth gap, line tangent, evidence class, and visibility mass.

### Shape sample

- Ray point at the selected layer depth `X_l`.
- Provenance: layer ID histogram and contributing Gaussian IDs.
- Lift 2D tangent to a 3D tangent by intersecting the image tangent constraint with local multi-view evidence; do not use Gaussian covariance PCA as the primary tangent.

## 8. Cross-view persistence

Aggregate TRAIN-view samples in 3D with two simultaneous compatibilities:

1. spatial proximity relative to local scene scale;
2. contributor-set compatibility (weighted ID overlap), with depth-layer and line-class agreement.

A cluster must have support from multiple separated camera baselines. Fit an unoriented local 3D tangent only after clustering. Then trace short 3D ridge tubes/linelets through neighboring clusters using tangent, class, and provenance consistency.

No joining across depth classes or incompatible foreground/background ordering.

## 9. Controls and ablations

Run all at matched visible ink for evaluation, while also showing uncapped soft responses.

1. RGB Canny on official 3DGS RGB — 2D visual baseline only.
2. Expected-depth edge (`z_mean`) — demonstrates layer averaging failure.
3. Front/median depth edge (`z_front` or `z_50`).
4. Depth-distribution only (`D_zdist`), no IDs.
5. Full IDs + depth + `Tα`.
6. IDs + depth but uniform contributor weights — tests value of `Tα`.
7. Shuffled IDs within each view — null for persistent identity.
8. Shuffled depths while preserving weights — null for layer geometry.
9. Density-only broad ridge from the previous experiment.
10. `k=4/8/16` sensitivity without retuning thresholds.

Key interpretation:

- If full ≈ depth-distribution-only, IDs add no useful information.
- If shuffled IDs ≈ full, persistent IDs are not the mechanism.
- If expected depth fails but layered depth succeeds, layer separation is the useful mechanism.
- If all variants fail on Ficus, top-k buffers do not solve projected layer ambiguity sufficiently.

## 10. Cheap kill-test and gates

### Frozen scenes and views

Use Lego, Chair, Drums, Ficus. Use the existing isolated TRAIN/F/C/DEV protocol. No per-scene thresholds.

### G1: 2D evidence quality

GO only if, in at least three of four scenes:

- full top-k produces several recognizable, coherent broad bands in fixed views;
- it is visibly cleaner or more complete than front-depth and depth-distribution-only controls at matched ink;
- uncapped soft responses show that the gain is not created by threshold selection;
- Ficus is reported separately and cannot be hidden by aggregate success.

Otherwise STOP before 3D tracing.

### G2: held-out reprojection consistency

After lifting TRAIN evidence, project frozen 3D samples into held-out views. GO only if:

- a preregistered majority of visible 3D line length lies within a fixed pixel distance of the same evidence class;
- support comes from multiple separated TRAIN views, not adjacent-frame duplication;
- shuffled-ID and shifted-camera nulls are materially worse;
- no single scene alone carries the result.

Use actual frame/contact-sheet inspection as the primary gate; pixel distance and supported length are diagnostics.

### G3: persistent broad-line visual result

Only after G1 and G2:

- trace persistent 3D paths;
- render fixed stills and a complete orbit;
- compare full method, depth-only, density-only, and matched-ink controls;
- judge clean shape description, continuity, occlusion behavior, and temporal stability.

No mesh precision/recall gate.

## 11. Required visual artifacts

For every scene:

1. official RGB;
2. top-k accumulated alpha and missing-tail map;
3. front/median/expected depth;
4. depth variance and contributor entropy;
5. dominant ID and weighted ID-overlap discontinuity;
6. depth-distribution transport;
7. layer split/merge map;
8. `E_occ`, `E_layer`, `E_shape` soft responses;
9. hysteresis broad bands before cleanup;
10. lifted 3D samples reprojected into source and held-out views;
11. fixed multi-method contact sheet;
12. complete orbit video if G2 passes.

Never show only final masks.

## 12. Likely files after approval

- Create: `src/topk_layered_evidence.py`
- Create: `src/topk_layered_lifting.py`
- Create: `scripts/render_topk_layered_probe.py`
- Create: `scripts/verify_topk_layered_probe.py`
- Create: `tests/test_topk_layered_evidence.py`
- Create: `tests/test_topk_layered_lifting.py`
- Create: `artifacts/topk_layered_probe/PROTOCOL.md`
- Modify only if required after calibration: pinned rasterizer wrapper/native-buffer reader; preserve stock output equality tests.

## 13. Test-first implementation sequence

### Task 1: Freeze protocol and source hashes

Write and hash the protocol before implementation. Record branch, checkpoint, cameras, splits, `k`, thresholds, controls, gates, and output schema.

### Task 2: Calibrate top-k buffers

Write synthetic and real tests for ID validity, order, `Tα`, alpha/RGB replay, tail mass, ties, and full intrinsics. Stop on failure.

### Task 3: Implement contributor metrics

Test Hellinger/ID overlap, depth Wasserstein distance, entropy, expected/median/front depth, and independent ID permutation invariance.

### Task 4: Implement deterministic layer clustering

Test one layer, separated layers, close-depth duplicates, low-mass tails, split/merge, and camera-depth scale covariance.

### Task 5: Implement evidence maps

Use synthetic occlusion, smooth surface, crease, crossing layers, and random-ID tessellation. Verify raw ID turnover alone cannot trigger an occlusion line.

### Task 6: Implement broad hysteresis bands

Test weak-span recovery, direction consistency, scale-dependent width, crossings, and deterministic thresholds. Preserve soft responses.

### Task 7: Run G1 on four scenes

Generate all maps and controls with frozen parameters. Perform complete visual review and machine consistency checks. Stop if G1 fails.

### Task 8: Implement 3D lifting only if G1 passes

Test ray-depth lifting, full intrinsics, contributor provenance, layer/class separation, and source-view reprojection.

### Task 9: Run held-out G2

Freeze lifted samples before opening held-out evidence. Compare full method and nulls. Stop if persistence is unsupported.

### Task 10: Trace/render persistent paths only if G2 passes

Create short 3D paths, render fixed stills and orbit, run matched-ink controls, verify all outputs, commit, and push the independent branch.

## 14. Main risks

- Tile-level center-depth sorting is not exact per-pixel surface order.
- Densification creates many same-surface IDs; ID boundaries can be tessellation artifacts.
- Top-k truncation may omit meaningful translucent rear layers.
- Gaussian center depth is not a ray/surface intersection.
- Layer clustering can merge thin surfaces or split one broad Gaussian layer.
- Ficus may remain underdetermined because many leaves overlap with low opacity.
- Better 2D evidence may still fail to define persistent 3D tangents.

## 15. Decision requested from user

Before execution, review these design choices:

1. Primary first-stage target: keep `E_occ`, `E_layer`, and `E_shape` separate rather than immediately fusing them.
2. Initial `k=8`, with `k=4/16` only as sensitivity controls.
3. Use ID overlap only jointly with depth/layer evidence; never raw ID edges alone.
4. Use ray-depth points for lifting, with Gaussian IDs as provenance rather than using centers as geometry.
5. Stop after the four-scene 2D G1 probe if top-k does not beat depth-only controls visually.
6. Use hysteresis broad bands instead of a global Top-N ink budget for the candidate output.
