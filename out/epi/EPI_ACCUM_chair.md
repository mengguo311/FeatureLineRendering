# EPIPOLAR ACCUMULATION TEST — chair

**VERDICT (chair, pre-registered headline): NO-GO** — S_bar AUC-ROC = **0.8587**, Recall@85%Precision = **0.0000** (n = 73,371 / 73,371) against the frozen rule (GO: AUC>=0.8 AND R@85P>=0.55; NO-GO: AUC<=0.65 OR R@85P<=0.42). Script md5 `bf2e3486a5006970938a944ca7bd801c`, cv2 4.5.5.

- |M_miss| = **73,371** (banked Experiment-X miss-set), |M_flat| = **73,371** (balanced; pool 877,763). Flat rule: d(merged-mesh edge with dihedral >= 10 deg, or boundary, or non-manifold edge) > margin AND visible in >=1 TEST view (mesh depth, 3x3 min |dz| < 0.015); base margin 3.0 px-equiv = 0.01031 world. Flat points' distance to the nearest banked GT crease: p5 = 5.59 px, p50 = 40.59 px.
- Mesh topology (why the merged mesh is needed): split-vertex adjacency edges 134,381 (>=10deg 63,494) vs position-merged 382,888 (>=10deg 257,476, >=30deg 175,671), boundary 9,946, non-manifold 6. Banked a30 crease samples within 1e-4 of a geometric a30 edge: 1.000; geometric a30 samples covered by the banked set: **0.431**.
- RAW DexiNed maps: `out/dexined_edges_chair/v###.npz[native]` — sigmoid probability, float16, no threshold / NMS / stretch (continuity asserted at run time).
- Occlusion: 3DGS mean depth (de-floatered gaussians), 3x3-min z-buffer, visible iff z <= zbuf + eps*z with **eps = 0.02** (the pipeline's rule); tight arm eps = 0.005. Photo-index offset used = [-0.5, -1.0] (calibrated on the hit-set; best = [-0.5, -1.0]).
- Depth-test calibration on mesh-visible TEST-view samples (3DGS minus mesh, dz/z): p50/p95 = +0.0028/+0.0344 (miss), -0.0019/+0.0310 (flat); pass at eps 0.02: 0.893 / 0.936; at 0.005: 0.612 / 0.864. 3DGS gate vs mesh visibility (TEST views): keeps 0.919 of mesh-visible, passes 0.171 of mesh-occluded.

## Headline and arms (native map, bilinear at pi_k(x), eps 0.02, all 100 views)

| aggregator over visible views | AUC | Recall@85%P | precision@R=0.55 | dropped (no view) pos/neg |
|---|---|---|---|---|
| mean **(headline S_bar)** | 0.8587 | 0.0000 | 0.8313 | 0/0 |
| median | 0.8584 | 0.0000 | 0.8343 | 0/0 |
| trim10 | 0.8593 | 0.0000 | 0.8297 | 0/0 |
| topq25 | 0.8339 | 0.0000 | 0.8007 | 0/0 |
| max | 0.6744 | 0.0000 | 0.6204 | 0/0 |
| mean_logit | 0.8417 | 0.2622 | 0.7763 | 0/0 |
| mean_nosil3 | 0.8503 | 0.0000 | 0.8254 | 0/342 |

## Sensitivity grid (mean aggregator)

| map | sampling | eps | views | AUC | Recall@85%P | n_vis p50 miss/flat | zero-vis miss/flat |
|---|---|---|---|---|---|---|---|
| nat | bil | loose | all100 | 0.8587 | 0.0000 | 51/60 | 0.0000/0.0000 |
| nat | bil | loose | train80 | 0.8584 | 0.1794 | 41/48 | 0.0000/0.0000 |
| nat | bil | tight | all100 | 0.8494 | 0.5570 | 22/48 | 0.0001/0.0009 |
| nat | bil | tight | train80 | 0.8524 | 0.5812 | 17/38 | 0.0005/0.0015 |
| nat | dil | loose | all100 | 0.8734 | 0.3630 | 51/60 | 0.0000/0.0000 |
| nat | dil | loose | train80 | 0.8724 | 0.3673 | 41/48 | 0.0000/0.0000 |
| nat | dil | tight | all100 | 0.8729 | 0.7290 | 22/48 | 0.0001/0.0009 |
| nat | dil | tight | train80 | 0.8754 | 0.7363 | 17/38 | 0.0005/0.0015 |
| ms | bil | loose | all100 | 0.8839 | 0.6523 | 51/60 | 0.0000/0.0000 |
| ms | bil | loose | train80 | 0.8833 | 0.6066 | 41/48 | 0.0000/0.0000 |
| ms | bil | tight | all100 | 0.8813 | 0.7504 | 22/48 | 0.0001/0.0009 |
| ms | bil | tight | train80 | 0.8842 | 0.7625 | 17/38 | 0.0005/0.0015 |
| ms | dil | loose | all100 | 0.8806 | 0.4350 | 51/60 | 0.0000/0.0000 |
| ms | dil | loose | train80 | 0.8788 | 0.4278 | 41/48 | 0.0000/0.0000 |
| ms | dil | tight | all100 | 0.8867 | 0.7629 | 22/48 | 0.0001/0.0009 |
| ms | dil | tight | train80 | 0.8888 | 0.7685 | 17/38 | 0.0005/0.0015 |

## Negative-class margin sensitivity

3D margin from the nearest geometric (merged-mesh) >=10deg / boundary / non-manifold edge; positives = banked M_miss, balanced by subsampling.

| margin px | n_neg available | AUC (mean) | R@85P (mean) | AUC (median) | R@85P (median) | AUC (max) | rule |
|---|---|---|---|---|---|---|---|
| 3 | 877,763 | 0.8580 | 0.1468 | 0.8580 | 0.0000 | 0.6730 | NO-GO |
| 4.5 | 722,121 | 0.8906 | 0.7148 | 0.8837 | 0.6773 | 0.7184 | GO |
| 6 | 634,186 | 0.9034 | 0.7737 | 0.8918 | 0.7192 | 0.7423 | GO |
| 8 | 552,504 | 0.9113 | 0.8075 | 0.8958 | 0.7403 | 0.7695 | GO |

Image-space arm: a negative's view counts only if its projection is > m px from ANY projected crease-like mesh edge (no cull, conservative); positives unchanged.

| image margin px | negatives with no clean view | n_vis_neg p50 | AUC | R@85P | rule |
|---|---|---|---|---|---|
| 3 | 0.112 | 27 | 0.9015 | 0.8391 | GO |
| 5 | 0.215 | 21 | 0.8983 | 0.8712 | GO |
| 8 | 0.300 | 15 | 0.8879 | 0.8860 | GO |

DexiNed response on FLAT points vs distance to the nearest geometric edge (S_bar mean / median, pipeline-rule detection rate):

| d(edge) bin px | n | S_bar mean | S_bar p50 | det rate |
|---|---|---|---|---|
| [3,4) | 112,967 | 0.2891 | 0.2375 | 0.3015 |
| [4,5) | 76,636 | 0.2651 | 0.2148 | 0.2744 |
| [5,6) | 53,973 | 0.2250 | 0.1887 | 0.2223 |
| [6,8) | 81,683 | 0.1880 | 0.1607 | 0.1794 |
| [8,12) | 99,867 | 0.1588 | 0.1283 | 0.1463 |
| [12,1e+09) | 452,637 | 0.1153 | 0.0631 | 0.0990 |

## Geometric-a30 miss-set arm (positives from the merged mesh; same cloud, radius and visibility rule as Experiment X)

- Geometric >=30deg crease samples TEST-visible: 844,397; 3D recall of the frozen cloud on them **0.5976** (banked subset 0.6654, non-banked subset 0.5446; 0.439 of the seen samples are in the banked set); misses 339,744, arm size 300,000.
- vs base M_flat (balanced): AUC **0.8195**, Recall@85%P **0.0000** (median arm 0.8189/0.0000; max 0.6289) -> NO-GO. S_bar p10/p50/p90 = 0.158/0.357/0.591.
  - subset theta>=30.05: n=299,793 AUC 0.8200 R@85P 0.0000
  - subset theta_exact30: n=436 AUC 0.8344 R@85P 0.0000
  - subset theta>=45: n=210,256 AUC 0.8250 R@85P 0.0000

## S_bar distribution (headline)

| class | mean | p10 | p50 | p90 | frac S_bar<0.02 | frac in [0.05,0.5) | frac >=0.5 | detected by pipeline rule in >=1 view | undetected in EVERY view | per-point det rate p50 |
|---|---|---|---|---|---|---|---|---|---|---|
| miss | 0.4097 | 0.1964 | 0.3990 | 0.6455 | 0.001 | 0.726 | 0.271 | 0.993 | 0.007 | 0.342 |
| flat | 0.1692 | 0.0112 | 0.1248 | 0.3990 | 0.142 | 0.664 | 0.054 | 0.865 | 0.135 | 0.096 |
| geo_arm | 0.3648 | 0.1580 | 0.3573 | 0.5910 | 0.000 | 0.796 | 0.200 | 0.991 | 0.009 | 0.289 |

## Banked miss-set subsets (each vs an equal-count random subset of the base M_flat)

| subset | n | share | S_bar p50 | AUC (mean) | R@85P (mean) | AUC (max) | R@85P (max) | rule |
|---|---|---|---|---|---|---|---|---|
| ALL (spec-literal a30) | 73,371 | 1.000 | 0.3990 | 0.8587 | 0.0000 | 0.6744 | 0.0000 | NO-GO |
| theta>=30.05 (drop 30.000deg tessellation family) | 73,315 | 0.999 | 0.3991 | 0.8587 | 0.0000 | 0.6745 | 0.0000 | NO-GO |
| theta in [29.9,30.1) (the 30.000deg family) | 117 | 0.002 | 0.3089 | 0.8310 | 0.0000 | 0.5193 | 0.0000 | NO-GO |
| theta>=45 | 47,994 | 0.654 | 0.4104 | 0.8727 | 0.2614 | 0.6941 | 0.0000 | NO-GO |
| theta exactly 90 (box corners) | 16 | — | — | — | — | — | — | skipped (<100) |
| undetected by pipeline rule (NMS>=0.5, 1.5px) in EVERY visible view | 502 | 0.007 | 0.0823 | 0.3882 | 0.0000 | 0.1838 | 0.0000 | NO-GO |
| detected by pipeline rule in >=1 view (lost downstream) | 72,869 | 0.993 | 0.4002 | 0.8620 | 0.1554 | 0.6780 | 0.0000 | NO-GO |
| n_vis>=20 (well-observed) | 73,345 | 1.000 | 0.3990 | 0.8587 | 0.0000 | 0.6745 | 0.0000 | NO-GO |

## Single-view baseline and the multi-view lift (paired)

- Per-view (RAW bilinear P_k, balanced, 100 views): AUC mean **0.7377** (median 0.7601, min 0.5705, max 0.8281 at view 6); Recall@85%P mean **0.0134** (max 0.3673).
- **Paired multi-view lift** (S_bar minus single view on the same points): AUC mean +0.1329 (range +0.0434 .. +0.2956; vs the best view +0.0847); R@85P +0.3496.
- Frozen 2D-stage detection rule (NMS-thinned native >= 0.5, within 1.5 px): M_miss per-view mean **0.3576**, any of 100 views 0.9932; M_flat false-alarm per-view **0.1477**, any-view 0.8647. (3x3-max raw P >= 0.5, no NMS — a superset: miss 0.6501, flat 0.2402.)

Artefacts: `out/epi/epi_accum_chair.json`, `out/epi/epi_accum_chair.png`, `out/epi/epi_accum_chair_inspect_v*.png`, arrays `out/epi/epi_{labels,samples,scores}_chair.npz`.
