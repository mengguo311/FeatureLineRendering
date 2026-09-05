# EPIPOLAR ACCUMULATION TEST — lego

**VERDICT (lego, pre-registered headline): NO-GO** — S_bar AUC-ROC = **0.6984**, Recall@85%Precision = **0.0000** (n = 437,074 / 436,700) against the frozen rule (GO: AUC>=0.8 AND R@85P>=0.55; NO-GO: AUC<=0.65 OR R@85P<=0.42). Script md5 `bf2e3486a5006970938a944ca7bd801c`, cv2 4.5.5.

- |M_miss| = **437,138** (banked Experiment-X miss-set), |M_flat| = **436,700** (balanced; pool 972,959). Flat rule: d(merged-mesh edge with dihedral >= 10 deg, or boundary, or non-manifold edge) > margin AND visible in >=1 TEST view (mesh depth, 3x3 min |dz| < 0.015); base margin 3.0 px-equiv = 0.01016 world. Flat points' distance to the nearest banked GT crease: p5 = 3.38 px, p50 = 4.71 px.
- Mesh topology (why the merged mesh is needed): split-vertex adjacency edges 2,696,076 (>=10deg 374,572) vs position-merged 3,021,188 (>=10deg 713,686, >=30deg 482,952), boundary 19,357, non-manifold 11,056. Banked a30 crease samples within 1e-4 of a geometric a30 edge: 0.993; geometric a30 samples covered by the banked set: **0.374**.
- RAW DexiNed maps: `out/dexined_edges_lego/v###.npz[native]` — sigmoid probability, float16, no threshold / NMS / stretch (continuity asserted at run time).
- Occlusion: 3DGS mean depth (de-floatered gaussians), 3x3-min z-buffer, visible iff z <= zbuf + eps*z with **eps = 0.02** (the pipeline's rule); tight arm eps = 0.005. Photo-index offset used = [-0.5, -0.5] (calibrated on the hit-set; best = [-0.5, -0.5]).
- Depth-test calibration on mesh-visible TEST-view samples (3DGS minus mesh, dz/z): p50/p95 = +0.0024/+0.0564 (miss), +0.0027/+0.0518 (flat); pass at eps 0.02: 0.861 / 0.860; at 0.005: 0.624 / 0.607. 3DGS gate vs mesh visibility (TEST views): keeps 0.861 of mesh-visible, passes 0.207 of mesh-occluded.

## Headline and arms (native map, bilinear at pi_k(x), eps 0.02, all 100 views)

| aggregator over visible views | AUC | Recall@85%P | precision@R=0.55 | dropped (no view) pos/neg |
|---|---|---|---|---|
| mean **(headline S_bar)** | 0.6984 | 0.0000 | 0.6944 | 64/438 |
| median | 0.7132 | 0.0000 | 0.7030 | 64/438 |
| trim10 | 0.7027 | 0.0000 | 0.6916 | 64/438 |
| topq25 | 0.6848 | 0.0001 | 0.6828 | 64/438 |
| max | 0.6118 | 0.0000 | 0.5922 | 64/438 |
| mean_logit | 0.7108 | 0.0000 | 0.7035 | 64/438 |
| mean_nosil3 | 0.6918 | 0.0000 | 0.6832 | 16288/17985 |

## Sensitivity grid (mean aggregator)

| map | sampling | eps | views | AUC | Recall@85%P | n_vis p50 miss/flat | zero-vis miss/flat |
|---|---|---|---|---|---|---|---|
| nat | bil | loose | all100 | 0.6984 | 0.0000 | 35/42 | 0.0001/0.0010 |
| nat | bil | loose | train80 | 0.6897 | 0.0000 | 27/33 | 0.0004/0.0015 |
| nat | bil | tight | all100 | 0.7091 | 0.0000 | 15/22 | 0.0512/0.0324 |
| nat | bil | tight | train80 | 0.7021 | 0.0000 | 11/18 | 0.0656/0.0392 |
| nat | dil | loose | all100 | 0.6882 | 0.0000 | 35/42 | 0.0001/0.0010 |
| nat | dil | loose | train80 | 0.6783 | 0.0000 | 27/33 | 0.0004/0.0015 |
| nat | dil | tight | all100 | 0.7005 | 0.0034 | 15/22 | 0.0512/0.0324 |
| nat | dil | tight | train80 | 0.6925 | 0.0000 | 11/18 | 0.0656/0.0392 |
| ms | bil | loose | all100 | 0.6838 | 0.0000 | 35/42 | 0.0001/0.0010 |
| ms | bil | loose | train80 | 0.6749 | 0.0000 | 27/33 | 0.0004/0.0015 |
| ms | bil | tight | all100 | 0.6981 | 0.0000 | 15/22 | 0.0512/0.0324 |
| ms | bil | tight | train80 | 0.6912 | 0.0000 | 11/18 | 0.0656/0.0392 |
| ms | dil | loose | all100 | 0.6770 | 0.0000 | 35/42 | 0.0001/0.0010 |
| ms | dil | loose | train80 | 0.6672 | 0.0000 | 27/33 | 0.0004/0.0015 |
| ms | dil | tight | all100 | 0.6923 | 0.0012 | 15/22 | 0.0512/0.0324 |
| ms | dil | tight | train80 | 0.6846 | 0.0000 | 11/18 | 0.0656/0.0392 |

## Negative-class margin sensitivity

3D margin from the nearest geometric (merged-mesh) >=10deg / boundary / non-manifold edge; positives = banked M_miss, balanced by subsampling.

| margin px | n_neg available | AUC (mean) | R@85P (mean) | AUC (median) | R@85P (median) | AUC (max) | rule |
|---|---|---|---|---|---|---|---|
| 3 | 972,959 | 0.6980 | 0.0000 | 0.7129 | 0.0000 | 0.6108 | NO-GO |
| 4.5 | 162,022 | 0.7911 | 0.5077 | 0.8169 | 0.5186 | 0.6811 | MARGINAL |
| 6 | 27,745 | 0.8311 | 0.6647 | 0.8835 | 0.7251 | 0.7043 | GO |
| 8 | 2,511 | 0.8654 | 0.8029 | 0.9572 | 0.9665 | 0.5691 | GO |

Image-space arm: a negative's view counts only if its projection is > m px from ANY projected crease-like mesh edge (no cull, conservative); positives unchanged.

| image margin px | negatives with no clean view | n_vis_neg p50 | AUC | R@85P | rule |
|---|---|---|---|---|---|
| 3 | 0.955 | 0 | 0.9711 | 1.0000 | GO |
| 5 | 0.992 | 0 | 0.9999 | 1.0000 | GO |
| 8 | 0.999 | 0 | 0.9999 | 1.0000 | GO |

DexiNed response on FLAT points vs distance to the nearest geometric edge (S_bar mean / median, pipeline-rule detection rate):

| d(edge) bin px | n | S_bar mean | S_bar p50 | det rate |
|---|---|---|---|---|
| [3,4) | 674,021 | 0.1362 | 0.0857 | 0.1437 |
| [4,5) | 208,916 | 0.0970 | 0.0570 | 0.1007 |
| [5,6) | 62,277 | 0.0727 | 0.0416 | 0.0751 |
| [6,8) | 25,234 | 0.0621 | 0.0311 | 0.0701 |
| [8,12) | 2,511 | 0.0356 | 0.0289 | 0.0449 |
| [12,1e+09) | 0 | — | — | — |

## Geometric-a30 miss-set arm (positives from the merged mesh; same cloud, radius and visibility rule as Experiment X)

- Geometric >=30deg crease samples TEST-visible: 1,580,272; 3D recall of the frozen cloud on them **0.1746** (banked subset 0.1987, non-banked subset 0.1590; 0.391 of the seen samples are in the banked set); misses 1,304,428, arm size 300,000.
- vs base M_flat (balanced): AUC **0.6173**, Recall@85%P **0.0000** (median arm 0.6264/0.0000; max 0.5637) -> NO-GO. S_bar p10/p50/p90 = 0.010/0.141/0.395.
  - subset theta>=30.05: n=240,015 AUC 0.6292 R@85P 0.0000
  - subset theta_exact30: n=59,986 AUC 0.5709 R@85P 0.0000
  - subset theta>=45: n=234,240 AUC 0.6253 R@85P 0.0000

## S_bar distribution (headline)

| class | mean | p10 | p50 | p90 | frac S_bar<0.02 | frac in [0.05,0.5) | frac >=0.5 | detected by pipeline rule in >=1 view | undetected in EVERY view | per-point det rate p50 |
|---|---|---|---|---|---|---|---|---|---|---|
| miss | 0.2203 | 0.0231 | 0.2044 | 0.4394 | 0.092 | 0.778 | 0.052 | 0.889 | 0.111 | 0.189 |
| flat | 0.1215 | 0.0038 | 0.0718 | 0.3247 | 0.241 | 0.568 | 0.020 | 0.746 | 0.254 | 0.068 |
| geo_arm | 0.1758 | 0.0104 | 0.1409 | 0.3948 | 0.145 | 0.706 | 0.035 | 0.836 | 0.164 | 0.133 |

## Banked miss-set subsets (each vs an equal-count random subset of the base M_flat)

| subset | n | share | S_bar p50 | AUC (mean) | R@85P (mean) | AUC (max) | R@85P (max) | rule |
|---|---|---|---|---|---|---|---|---|
| ALL (spec-literal a30) | 437,138 | 1.000 | 0.2044 | 0.6984 | 0.0000 | 0.6118 | 0.0000 | NO-GO |
| theta>=30.05 (drop 30.000deg tessellation family) | 223,135 | 0.510 | 0.2682 | 0.8031 | 0.0000 | 0.6880 | 0.0000 | NO-GO |
| theta in [29.9,30.1) (the 30.000deg family) | 214,007 | 0.490 | 0.1199 | 0.5884 | 0.0000 | 0.5323 | 0.0000 | NO-GO |
| theta>=45 | 198,460 | 0.454 | 0.2659 | 0.8012 | 0.0000 | 0.6889 | 0.0000 | NO-GO |
| theta exactly 90 (box corners) | 108,621 | 0.248 | 0.2730 | 0.8063 | 0.0000 | 0.6854 | 0.0000 | NO-GO |
| undetected by pipeline rule (NMS>=0.5, 1.5px) in EVERY visible view | 48,379 | 0.111 | 0.0098 | 0.2164 | 0.0000 | 0.1613 | 0.0000 | NO-GO |
| detected by pipeline rule in >=1 view (lost downstream) | 388,759 | 0.889 | 0.2302 | 0.7582 | 0.0000 | 0.6677 | 0.0000 | NO-GO |
| n_vis>=20 (well-observed) | 354,572 | 0.811 | 0.1971 | 0.6882 | 0.0000 | 0.6281 | 0.0000 | NO-GO |

## Single-view baseline and the multi-view lift (paired)

- Per-view (RAW bilinear P_k, balanced, 100 views): AUC mean **0.6436** (median 0.6392, min 0.5241, max 0.7581 at view 95); Recall@85%P mean **0.0004** (max 0.0052).
- **Paired multi-view lift** (S_bar minus single view on the same points): AUC mean +0.0486 (range -0.0171 .. +0.1117; vs the best view +0.0049); R@85P +0.0105.
- Frozen 2D-stage detection rule (NMS-thinned native >= 0.5, within 1.5 px): M_miss per-view mean **0.2026**, any of 100 views 0.8893; M_flat false-alarm per-view **0.1274**, any-view 0.7456. (3x3-max raw P >= 0.5, no NMS — a superset: miss 0.3651, flat 0.2282.)

Artefacts: `out/epi/epi_accum_lego.json`, `out/epi/epi_accum_lego.png`, `out/epi/epi_accum_lego_inspect_v*.png`, arrays `out/epi/epi_{labels,samples,scores}_lego.npz`.
