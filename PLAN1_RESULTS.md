# Plan #1 — 2DGS-gated multi-view edge fusion: results

Chair, NeRF-synthetic, 100 train views. Split frozen as `src/view_split.py`
(TRAIN 80 / VAL {0,10,..,90} / TEST {5,15,..,95}). Mesh is EVAL-ONLY throughout;
`grep -rn "mesh_oracle\|trimesh" src/*.py` finds only docstrings.
Nothing committed to git.

---

## STEP A — foundation + GO/NO-GO

### Install
`hbb1/2d-gaussian-splatting` @ `335ad61` -> `ext/2dgs`. `simple-knn` already present.
Two build failures, both real:

1. `ModuleNotFoundError: No module named 'torch'` — PEP-517 build isolation.
   Fix: `pip install --no-build-isolation`.
2. `cuda_rasterizer/rasterizer_impl.h(24): error: namespace "std" has no member "uintptr_t"`
   `cuda_rasterizer/rasterizer_impl.h(40): error: identifier "uint32_t" is undefined`
   GCC-13 dropped the transitive `<cstdint>` include. **Toolchain, not repo version** —
   an older commit fails identically. Fix: add `#include <cstdint>` to that header
   (`.orig` kept beside it). Builds clean vs torch 2.3.1+cu121 / nvcc 12.6 / sm_86.

### Training (test PSNR on the 200-view NeRF test split, identical protocol to vanilla)

| run | recipe | 7k | 15k | 30k |
|---|---|---|---|---|
| A `out/2dgs_chair` | lambda_normal 0.05, lambda_dist 0, depth_ratio 1 | 33.12 | 28.41 | **29.98** |
| B `out/2dgs_chair_dist` | + lambda_dist 1000 | 32.89 | 27.60 | 26.82 |
| C `out/2dgs_chair_reporecipe` | repo `nerf_eval.py` recipe (lambda_normal 0) | 33.14 | 34.83 | **35.40** |
| vanilla 3DGS | `~/cglib/outputs/chair_static` | — | **37.73** | — |

Run A is 7.7 dB below vanilla, far outside the +-0.5 dB sanity band. **Run C explains it:**
the repo's own recipe reaches 35.40 dB, matching the 2DGS paper's ~35.1 on NeRF-synthetic.
So the install is healthy; the gap is the price of normal-consistency + median depth
(~5.4 dB) plus the inherent 3DGS->2DGS cost (~2.3 dB). Not a bug.

### Pixel-grid calibration (`scripts/explore/check_2dgs_align.py`)
tier1 puts integer pixel i at `u = f*X/Z + W/2`; 3DGS at `((x_ndc+1)*W-1)/2`. Measured
mesh-vs-photo offset **+0.492 px**, so 2DGS buffers are resampled by **-0.5 px**
(`render2dgs.half_pixel`). The alpha-IoU test is useless here — 2DGS keeps a white
background "splat canvas", `alpha>0.5` covers 99.8% of the frame.
Verdict is insensitive to the choice (normal-theta AUC 0.967 with, 0.963 without).

### The diagnostic (`scripts/explore/gate_falsify_2dgs.py`)
Harness reproduces the published vanilla numbers exactly: fabric p95 **79.3**, crease p05 **4.9**.

**All labelled pixels** (as the spec defines them):

| arm | signal | fab p50 | fab p95 | cre p05 | AUC |
|---|---|---|---|---|---|
| vanilla-3DGS | depth theta | 32.2 | 82.3 | 4.95 | 0.397 |
| 2DGS | depth theta | 15.6 | 78.9 | 3.04 | 0.597 |
| **GT mesh** | depth theta | 2.1 | **71.7** | 3.87 | **0.822** |

**Ground-truth geometry fails the frozen GO rule.** The FABRIC class ("no GT crease within
3px") is contaminated by genuinely non-flat geometry — legs, ornaments, interior
self-occlusions, folds below the oracle's 30 deg criterion — so `fabric_p95 < 15` is
unreachable by any reconstruction and cannot discriminate.

**Restricted to pixels the mesh says are FLAT-and-printed vs genuinely SHARP:**

| arm | signal | fab p50 | fab p95 | cre p05 | cre p50 | AUC |
|---|---|---|---|---|---|---|
| vanilla-3DGS | depth theta | 33.8 | 82.9 | 6.15 | 29.2 | 0.443 |
| 2DGS | depth theta | 10.7 | 75.6 | 7.15 | 37.4 | 0.740 |
| vanilla-3DGS | **normal theta** | 11.9 | 38.5 | 4.45 | 21.4 | 0.696 |
| **2DGS** | **normal theta** | **1.80** | **7.29** | 4.23 | 24.5 | **0.967** |
| GT mesh | depth theta | 0.82 | 4.04 | 21.7 | 41.3 | 1.000 (tautological) |

(The mesh row here is circular — the subsets were defined by its own theta — so it is a
well-formedness check, not a ceiling.)

Other recipes measured: `lambda_dist=1000` is **worse** (normal AUC 0.851, crease p05
collapses to 0.29 — distortion over-flattens creases); mean depth is worse than median
(0.536 vs 0.740), so the median-depth faceting hypothesis was wrong.

### VERDICT: MARGINAL
- Literal rule on the depth dihedral -> NO-GO, but that rule also rejects ground truth.
- The NO-GO *diagnosis* ("2DGS also stairstep-bakes texture") is **disproved**: on GT-flat
  printed surface 2DGS normals read p50 1.8 / p95 7.3 deg vs vanilla 11.9 / 38.5.
- On the channel STEP B gates with: fab p95 7.29 (<15 PASS), AUC 0.967 (>=0.90 PASS),
  crease p05 4.23 (<25 FAIL) -> two of three GO criteria -> MARGINAL.

---

## STEP B — geometry-gated fusion

Gate = `E_v = A_v AND dilate(G_v > tau_geom, 2px)`, `G_v` = dihedral on the 2DGS **normal**
buffer. `tau_geom = 12` picked on VAL (`scripts/tune_tau_geom_2dgs.py`); edge purity
0.313 -> **0.411**, crease_keep 0.863 -> 0.802, 51.8% of edge px survive.

### The gate ablation — identical 2DGS geometry, seeds, pull, prune; only the DT target differs

| n (linelets) | gated P@1.5 | ungated P@1.5 | delta |
|---|---|---|---|
| 2.9k | 0.659 | 0.566 | **+0.093** |
| 9.7k | 0.616 | 0.520 | **+0.096** |
| 14.4k | 0.597 | 0.495 | **+0.102** |
| 27.8k | 0.555 | 0.425 | **+0.130** |
| 38.5k | 0.526 | 0.364 | **+0.162** |

**The gate works.** On vanilla 3DGS the same gating bought +0.004 segment precision
(0.6067 vs 0.6024) — a no-op. Here it buys +0.09..+0.16. That is the Plan #1 mechanism.

### But the pipeline does NOT beat the vanilla-3DGS M1b baseline (TEST views, matched count)

| pipeline | n | pts P@1.5 | pts R@1.5 | seg P@1.5 | seg R@1.5 |
|---|---|---|---|---|---|
| vanilla-3DGS M1b [gated] | 16039 | **0.727** | 0.533 | **0.607** | **0.708** |
| 2DGS-gated (Plan #1) | 14410 | 0.597 | 0.521 | 0.493 | 0.663 |

End-to-end gate `P@1.5>=0.85 AND R@1.5>=0.75`: **FAIL** for Plan #1 (0.597/0.521) and for
the baseline (0.727/0.533).

### Ink anatomy (`scripts/plan1_fp_anatomy.py`) — this refutes the visual impression

At essentially identical total ink (19806 vs 19324 drawn px/view):

| pipeline | ink on flat print /kpx | crease coverage | FP share on contour | FP share on fabric |
|---|---|---|---|---|
| vanilla M1b [gated] | **36.0** | 0.700 | 0.180 | 0.449 |
| 2DGS-gated (Plan #1) | **53.1** | 0.652 | 0.261 | 0.503 |

Plan #1 puts **1.44x more ink on flat printed fabric**, not less. The 3-panel visualisation
suggested the opposite; the measurement is authoritative and the visual read was wrong.

### Temporal coherence — headline preserved, popping regressed

| frames | Plan #1 Frechet / P_pop | published M1b Frechet / P_pop | Frechet ratio (new / old) |
|---|---|---|---|
| 30 | 0.323 / 0.178 | 0.330 / 0.093 | 4.28x / 4.19x |
| 60 | 0.163 / 0.145 | 0.164 / 0.076 | 7.94x / 7.87x |
| 120 | 0.082 / 0.136 | 0.082 / 0.068 | 15.3x / 15.2x |
| 240 | 0.041 / 0.128 | 0.041 / 0.067 | 29.9x / 29.9x |

Fréchet residual is **identical** — the object-space coherence result is intact. `P_pop`
regressed ~2x (953 strokes vs 752; more, shorter strokes pop more).

---

## Where this leaves Plan #1

Raising K_geom **did** work at the level it was supposed to: 2DGS geometry is dramatically
less texture-contaminated (normal-theta AUC 0.967 vs 0.696 on GT-flat print), and gating on
it produces a real precision gain for the first time (+0.10 vs +0.004). The premise of the
plan is validated.

It does **not** translate into better feature lines, and the honest reason is that the gate
is only a partial filter: it keeps 51.8% of edge pixels at purity 0.411, so most surviving
gated edges are still not near a GT crease.

Untested hypothesis for the remaining gap: the 2DGS surfel cloud is a worse seed *carrier*.
Surfels tile surfaces uniformly, including flat fabric, whereas vanilla 3DGS's small
anisotropic gaussians happen to concentrate at creases — which is exactly what the tuned M1a
OVERALL recipe was built to exploit. Porting that recipe's structure onto the surfel cloud
(done here: soft + q90 + local competition) recovered recall but not precision. Testing this
would mean seeding from vanilla 3DGS gaussians while gating with 2DGS normals — a hybrid
neither STEP A nor STEP B specified.
