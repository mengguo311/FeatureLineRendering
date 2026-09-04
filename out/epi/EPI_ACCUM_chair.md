# EPIPOLAR ACCUMULATION TEST — chair

**VERDICT (chair): NO-GO** — S_bar AUC-ROC = **0.7330**, Recall@85%Precision = **0.0000** against the frozen rule (GO: AUC>=0.8 AND R@85P>=0.55; NO-GO: AUC<=0.65 OR R@85P<=0.42).

- |M_miss| = **73,371**, |M_flat| = **73,371** (balanced). Flat rule: d(any mesh edge with dihedral >= 10 deg) > margin AND visible in >=1 TEST view (mesh depth, 3x3 min |dz| < 0.015); margin 3.0 px-equiv = 0.01031 world; flat points' distance to the nearest GT crease p5 = 0.0136, p50 = 0.0819.
- RAW DexiNed maps: `out/dexined_edges_chair/v###.npz[native]` — sigmoid probability, float16, no threshold / NMS / stretch (continuity asserted at run time).
- Occlusion: 3DGS mean depth (de-floatered gaussians), 3x3-min z-buffer, visible iff z <= zbuf + eps*z with **eps = 0.02** (the pipeline's rule); tight arm eps = 0.005. Pixel offset (photo-index) used = [-0.5, -1.0] (calibrated on the hit-set; best = [-0.5, -1.0]).
- Depth-test calibration on mesh-visible TEST-view points: |3DGS - mesh| dz/z p50/p95 = +0.0033/+0.0339 (miss), -0.0016/+0.0300 (flat); pass fraction at eps 0.02: miss 0.881, flat 0.936; at 0.005: 0.589 / 0.822.

## Headline and arms (native map, bilinear at pi_k(x), eps 0.02, all 100 views)

| aggregator over visible views | AUC | Recall@85%P | precision@R=0.55 |
|---|---|---|---|
| mean **(headline S_bar)** | 0.7330 | 0.0000 | 0.6842 |
| median | 0.7405 | 0.0000 | 0.6931 |
| trim10 | 0.7342 | 0.0000 | 0.6841 |
| topq25 | 0.6933 | 0.0000 | 0.6507 |
| max | 0.5669 | 0.0000 | 0.5500 |
| mean_logit | 0.7079 | 0.0000 | 0.6405 |
| mean_nosil3 | 0.7377 | 0.0000 | 0.6922 |

## Sensitivity grid (mean aggregator)

| map | sampling | eps | views | AUC | Recall@85%P | n_vis p50 miss/flat |
|---|---|---|---|---|---|---|
| nat | bil | loose | all100 | 0.7330 | 0.0000 | 51/58 |
| nat | bil | loose | train80 | 0.7340 | 0.0000 | 41/47 |
| nat | bil | tight | all100 | 0.7461 | 0.0000 | 21/41 |
| nat | bil | tight | train80 | 0.7489 | 0.0000 | 16/33 |
| nat | dil | loose | all100 | 0.7484 | 0.0000 | 51/58 |
| nat | dil | loose | train80 | 0.7481 | 0.0000 | 41/47 |
| nat | dil | tight | all100 | 0.7749 | 0.0000 | 21/41 |
| nat | dil | tight | train80 | 0.7769 | 0.0000 | 16/33 |
| ms | bil | loose | all100 | 0.7544 | 0.0000 | 51/58 |
| ms | bil | loose | train80 | 0.7549 | 0.0000 | 41/47 |
| ms | bil | tight | all100 | 0.7785 | 0.0000 | 21/41 |
| ms | bil | tight | train80 | 0.7813 | 0.0000 | 16/33 |
| ms | dil | loose | all100 | 0.7522 | 0.0000 | 51/58 |
| ms | dil | loose | train80 | 0.7511 | 0.0000 | 41/47 |
| ms | dil | tight | all100 | 0.7884 | 0.0000 | 21/41 |
| ms | dil | tight | train80 | 0.7901 | 0.0000 | 16/33 |

## S_bar distribution (headline)

| class | mean | p10 | p50 | p90 | frac S_bar<0.02 | frac in [0.05,0.5) | frac >=0.5 | any-view P(1.5px)>=0.5 | sub-threshold in EVERY view |
|---|---|---|---|---|---|---|---|---|---|
| M_miss | 0.4100 | 0.1957 | 0.4010 | 0.6435 | 0.001 | 0.725 | 0.272 | 1.000 | 0.000 |
| M_flat | 0.2564 | 0.0268 | 0.2090 | 0.5687 | 0.080 | 0.679 | 0.150 | 0.953 | 0.047 |

## Miss-set subsets (each vs an equal-count random M_flat subset)

| subset | n | share | S_bar p50 | AUC (mean) | R@85P (mean) | AUC (max) | R@85P (max) | rule |
|---|---|---|---|---|---|---|---|---|
| ALL (spec-literal a30) | 73,371 | 1.000 | 0.4010 | 0.7330 | 0.0000 | 0.5669 | 0.0000 | NO-GO |
| theta>=30.05 (drop 30.000deg tessellation family) | 73,315 | 0.999 | 0.4011 | 0.7332 | 0.0000 | 0.5671 | 0.0000 | NO-GO |
| theta in [29.9,30.1) (the 30.000deg family) | 117 | 0.002 | 0.3097 | 0.6594 | 0.0085 | 0.4776 | 0.0000 | NO-GO |
| theta>=45 | 47,994 | 0.654 | 0.4126 | 0.7531 | 0.0000 | 0.5908 | 0.0000 | NO-GO |
| theta exactly 90 (box corners) | 16 | — | — | — | — | — | — | skipped (<100) |
| sub-threshold everywhere (max over views of 1.5px-max P < 0.5) | 15 | — | — | — | — | — | — | skipped (<100) |
| above threshold in >=1 view (lost by triangulation) | 73,356 | 1.000 | 0.4010 | 0.7332 | 0.0000 | 0.5670 | 0.0000 | NO-GO |
| n_vis>=20 (well-observed) | 73,332 | 0.999 | 0.4010 | 0.7331 | 0.0000 | 0.5670 | 0.0000 | NO-GO |

## Single-view baseline and the multi-view lift

- Per-view (RAW bilinear P_k, balanced, 100 views): AUC mean **0.6563** (median 0.6786, min 0.4764, max 0.7694); Recall@85%P mean **0.0003** (max 0.0214, view 10).
- Thresholded single-view detection (P within 1.5 px >= 0.5) of M_miss: per-view mean **0.6539**, any of 100 views 0.9998; M_flat false-alarm per-view 0.3695, any-view 0.9531.
- **Lift** S_bar minus single-view mean: AUC +0.0768, R@85P -0.0003; minus best single view: AUC -0.0364, R@85P -0.0214.

Artefacts: `out/epi/epi_accum_chair.json`, `out/epi/epi_accum_chair.png`, `out/epi/epi_accum_chair_inspect_v*.png`, arrays `out/epi/epi_{labels,samples,scores}_chair.npz`.
