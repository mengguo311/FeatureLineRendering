# EPIPOLAR ACCUMULATION TEST — lego

**VERDICT (lego): NO-GO** — S_bar AUC-ROC = **0.4439**, Recall@85%Precision = **0.0000** against the frozen rule (GO: AUC>=0.8 AND R@85P>=0.55; NO-GO: AUC<=0.65 OR R@85P<=0.42).

- |M_miss| = **437,138**, |M_flat| = **437,138** (balanced). Flat rule: d(any mesh edge with dihedral >= 10 deg) > margin AND visible in >=1 TEST view (mesh depth, 3x3 min |dz| < 0.015); margin 8.0 px-equiv = 0.02709 world; flat points' distance to the nearest GT crease p5 = 0.0276, p50 = 0.0318.
- RAW DexiNed maps: `out/dexined_edges_lego/v###.npz[native]` — sigmoid probability, float16, no threshold / NMS / stretch (continuity asserted at run time).
- Occlusion: 3DGS mean depth (de-floatered gaussians), 3x3-min z-buffer, visible iff z <= zbuf + eps*z with **eps = 0.02** (the pipeline's rule); tight arm eps = 0.005. Pixel offset (photo-index) used = [-0.5, -0.5] (calibrated on the hit-set; best = [-0.5, -0.5]).
- Depth-test calibration on mesh-visible TEST-view points: |3DGS - mesh| dz/z p50/p95 = +0.0024/+0.0578 (miss), +0.0007/+0.0441 (flat); pass fraction at eps 0.02: miss 0.860, flat 0.889; at 0.005: 0.628 / 0.738.

## Headline and arms (native map, bilinear at pi_k(x), eps 0.02, all 100 views)

| aggregator over visible views | AUC | Recall@85%P | precision@R=0.55 |
|---|---|---|---|
| mean **(headline S_bar)** | 0.4439 | 0.0000 | 0.5000 |
| median | 0.5061 | 0.0000 | 0.5271 |
| trim10 | 0.4551 | 0.0000 | 0.5032 |
| topq25 | 0.3928 | 0.0000 | 0.5000 |
| max | 0.3157 | 0.0000 | 0.5000 |
| mean_logit | 0.4963 | 0.0000 | 0.5194 |
| mean_nosil3 | 0.4653 | 0.0000 | 0.5131 |

## Sensitivity grid (mean aggregator)

| map | sampling | eps | views | AUC | Recall@85%P | n_vis p50 miss/flat |
|---|---|---|---|---|---|---|
| nat | bil | loose | all100 | 0.4439 | 0.0000 | 35/47 |
| nat | bil | loose | train80 | 0.4327 | 0.0000 | 27/38 |
| nat | bil | tight | all100 | 0.4863 | 0.0001 | 15/22 |
| nat | bil | tight | train80 | 0.4726 | 0.0000 | 11/16 |
| nat | dil | loose | all100 | 0.4056 | 0.0000 | 35/47 |
| nat | dil | loose | train80 | 0.3970 | 0.0000 | 27/38 |
| nat | dil | tight | all100 | 0.4382 | 0.0004 | 15/22 |
| nat | dil | tight | train80 | 0.4243 | 0.0001 | 11/16 |
| ms | bil | loose | all100 | 0.4012 | 0.0000 | 35/47 |
| ms | bil | loose | train80 | 0.3943 | 0.0000 | 27/38 |
| ms | bil | tight | all100 | 0.4317 | 0.0001 | 15/22 |
| ms | bil | tight | train80 | 0.4190 | 0.0000 | 11/16 |
| ms | dil | loose | all100 | 0.3847 | 0.0000 | 35/47 |
| ms | dil | loose | train80 | 0.3786 | 0.0000 | 27/38 |
| ms | dil | tight | all100 | 0.4095 | 0.0003 | 15/22 |
| ms | dil | tight | train80 | 0.3969 | 0.0001 | 11/16 |

## S_bar distribution (headline)

| class | mean | p10 | p50 | p90 | frac S_bar<0.02 | frac in [0.05,0.5) | frac >=0.5 | any-view P(1.5px)>=0.5 | sub-threshold in EVERY view |
|---|---|---|---|---|---|---|---|---|---|
| M_miss | 0.2204 | 0.0234 | 0.2046 | 0.4401 | 0.090 | 0.778 | 0.053 | 0.945 | 0.055 |
| M_flat | 0.2726 | 0.0304 | 0.2350 | 0.5989 | 0.073 | 0.683 | 0.169 | 0.965 | 0.035 |

## Miss-set subsets (each vs an equal-count random M_flat subset)

| subset | n | share | S_bar p50 | AUC (mean) | R@85P (mean) | AUC (max) | R@85P (max) | rule |
|---|---|---|---|---|---|---|---|---|
| ALL (spec-literal a30) | 437,138 | 1.000 | 0.2046 | 0.4439 | 0.0000 | 0.3157 | 0.0000 | NO-GO |
| theta>=30.05 (drop 30.000deg tessellation family) | 223,135 | 0.510 | 0.2683 | 0.5432 | 0.0000 | 0.3710 | 0.0000 | NO-GO |
| theta in [29.9,30.1) (the 30.000deg family) | 214,007 | 0.490 | 0.1199 | 0.3405 | 0.0000 | 0.2586 | 0.0000 | NO-GO |
| theta>=45 | 198,460 | 0.454 | 0.2660 | 0.5404 | 0.0000 | 0.3732 | 0.0000 | NO-GO |
| theta exactly 90 (box corners) | 108,621 | 0.248 | 0.2725 | 0.5433 | 0.0000 | 0.3631 | 0.0000 | NO-GO |
| sub-threshold everywhere (max over views of 1.5px-max P < 0.5) | 24,194 | 0.055 | 0.0025 | 0.0342 | 0.0000 | 0.0255 | 0.0000 | NO-GO |
| above threshold in >=1 view (lost by triangulation) | 412,944 | 0.945 | 0.2177 | 0.4678 | 0.0000 | 0.3327 | 0.0000 | NO-GO |
| n_vis>=20 (well-observed) | 352,971 | 0.807 | 0.1962 | 0.4314 | 0.0000 | 0.3307 | 0.0000 | NO-GO |

## Single-view baseline and the multi-view lift

- Per-view (RAW bilinear P_k, balanced, 100 views): AUC mean **0.4791** (median 0.4753, min 0.3481, max 0.6156); Recall@85%P mean **0.0000** (max 0.0014, view 7).
- Thresholded single-view detection (P within 1.5 px >= 0.5) of M_miss: per-view mean **0.3644**, any of 100 views 0.9447; M_flat false-alarm per-view 0.4848, any-view 0.9651.
- **Lift** S_bar minus single-view mean: AUC -0.0352, R@85P -0.0000; minus best single view: AUC -0.1716, R@85P -0.0014.

Artefacts: `out/epi/epi_accum_lego.json`, `out/epi/epi_accum_lego.png`, `out/epi/epi_accum_lego_inspect_v*.png`, arrays `out/epi/epi_{labels,samples,scores}_lego.npz`.
