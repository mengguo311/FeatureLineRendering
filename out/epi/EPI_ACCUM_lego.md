# EPIPOLAR ACCUMULATION TEST — lego

**VERDICT (lego): NO-GO** — S_bar AUC-ROC = **0.5716**, Recall@85%Precision = **0.0000** against the frozen rule (GO: AUC>=0.8 AND R@85P>=0.55; NO-GO: AUC<=0.65 OR R@85P<=0.42).

- |M_miss| = **437,138**, |M_flat| = **437,138** (balanced). Flat rule: d(any mesh edge with dihedral >= 10 deg) > margin AND visible in >=1 TEST view (mesh depth, 3x3 min |dz| < 0.015); margin 3.0 px-equiv = 0.01016 world; flat points' distance to the nearest GT crease p5 = 0.0110, p50 = 0.0168.
- RAW DexiNed maps: `out/dexined_edges_lego/v###.npz[native]` — sigmoid probability, float16, no threshold / NMS / stretch (continuity asserted at run time).
- Occlusion: 3DGS mean depth (de-floatered gaussians), 3x3-min z-buffer, visible iff z <= zbuf + eps*z with **eps = 0.02** (the pipeline's rule); tight arm eps = 0.005. Pixel offset (photo-index) used = [-0.5, -0.5] (calibrated on the hit-set; best = [-0.5, -0.5]).
- Depth-test calibration on mesh-visible TEST-view points: |3DGS - mesh| dz/z p50/p95 = +0.0024/+0.0578 (miss), +0.0018/+0.0501 (flat); pass fraction at eps 0.02: miss 0.860, flat 0.874; at 0.005: 0.628 / 0.661.

## Headline and arms (native map, bilinear at pi_k(x), eps 0.02, all 100 views)

| aggregator over visible views | AUC | Recall@85%P | precision@R=0.55 |
|---|---|---|---|
| mean **(headline S_bar)** | 0.5716 | 0.0000 | 0.5667 |
| median | 0.5956 | 0.0000 | 0.5857 |
| trim10 | 0.5751 | 0.0000 | 0.5672 |
| topq25 | 0.5485 | 0.0000 | 0.5577 |
| max | 0.5008 | 0.0000 | 0.5281 |
| mean_logit | 0.5983 | 0.0000 | 0.5892 |
| mean_nosil3 | 0.5675 | 0.0000 | 0.5641 |

## Sensitivity grid (mean aggregator)

| map | sampling | eps | views | AUC | Recall@85%P | n_vis p50 miss/flat |
|---|---|---|---|---|---|---|
| nat | bil | loose | all100 | 0.5716 | 0.0000 | 35/45 |
| nat | bil | loose | train80 | 0.5624 | 0.0000 | 27/36 |
| nat | bil | tight | all100 | 0.5709 | 0.0000 | 15/22 |
| nat | bil | tight | train80 | 0.5585 | 0.0000 | 11/17 |
| nat | dil | loose | all100 | 0.5559 | 0.0000 | 35/45 |
| nat | dil | loose | train80 | 0.5459 | 0.0000 | 27/36 |
| nat | dil | tight | all100 | 0.5576 | 0.0000 | 15/22 |
| nat | dil | tight | train80 | 0.5443 | 0.0000 | 11/17 |
| ms | bil | loose | all100 | 0.5596 | 0.0000 | 35/45 |
| ms | bil | loose | train80 | 0.5503 | 0.0000 | 27/36 |
| ms | bil | tight | all100 | 0.5597 | 0.0000 | 15/22 |
| ms | bil | tight | train80 | 0.5469 | 0.0000 | 11/17 |
| ms | dil | loose | all100 | 0.5494 | 0.0000 | 35/45 |
| ms | dil | loose | train80 | 0.5394 | 0.0000 | 27/36 |
| ms | dil | tight | all100 | 0.5515 | 0.0000 | 15/22 |
| ms | dil | tight | train80 | 0.5383 | 0.0000 | 11/17 |

## S_bar distribution (headline)

| class | mean | p10 | p50 | p90 | frac S_bar<0.02 | frac in [0.05,0.5) | frac >=0.5 | any-view P(1.5px)>=0.5 | sub-threshold in EVERY view |
|---|---|---|---|---|---|---|---|---|---|
| M_miss | 0.2204 | 0.0234 | 0.2046 | 0.4401 | 0.090 | 0.778 | 0.053 | 0.945 | 0.055 |
| M_flat | 0.1931 | 0.0090 | 0.1380 | 0.4674 | 0.157 | 0.645 | 0.080 | 0.910 | 0.090 |

## Miss-set subsets (each vs an equal-count random M_flat subset)

| subset | n | share | S_bar p50 | AUC (mean) | R@85P (mean) | AUC (max) | R@85P (max) | rule |
|---|---|---|---|---|---|---|---|---|
| ALL (spec-literal a30) | 437,138 | 1.000 | 0.2046 | 0.5716 | 0.0000 | 0.5008 | 0.0000 | NO-GO |
| theta>=30.05 (drop 30.000deg tessellation family) | 223,135 | 0.510 | 0.2683 | 0.6750 | 0.0000 | 0.5708 | 0.0000 | NO-GO |
| theta in [29.9,30.1) (the 30.000deg family) | 214,007 | 0.490 | 0.1199 | 0.4637 | 0.0000 | 0.4274 | 0.0000 | NO-GO |
| theta>=45 | 198,460 | 0.454 | 0.2660 | 0.6724 | 0.0000 | 0.5730 | 0.0000 | NO-GO |
| theta exactly 90 (box corners) | 108,621 | 0.248 | 0.2725 | 0.6753 | 0.0000 | 0.5651 | 0.0000 | NO-GO |
| sub-threshold everywhere (max over views of 1.5px-max P < 0.5) | 24,194 | 0.055 | 0.0025 | 0.0796 | 0.0000 | 0.0636 | 0.0000 | NO-GO |
| above threshold in >=1 view (lost by triangulation) | 412,944 | 0.945 | 0.2177 | 0.6007 | 0.0000 | 0.5266 | 0.0000 | NO-GO |
| n_vis>=20 (well-observed) | 352,971 | 0.807 | 0.1962 | 0.5600 | 0.0000 | 0.5182 | 0.0000 | NO-GO |

## Single-view baseline and the multi-view lift

- Per-view (RAW bilinear P_k, balanced, 100 views): AUC mean **0.5397** (median 0.5358, min 0.4170, max 0.6895); Recall@85%P mean **0.0000** (max 0.0004, view 84).
- Thresholded single-view detection (P within 1.5 px >= 0.5) of M_miss: per-view mean **0.3644**, any of 100 views 0.9447; M_flat false-alarm per-view 0.3694, any-view 0.9102.
- **Lift** S_bar minus single-view mean: AUC +0.0319, R@85P -0.0000; minus best single view: AUC -0.1179, R@85P -0.0004.

Artefacts: `out/epi/epi_accum_lego.json`, `out/epi/epi_accum_lego.png`, `out/epi/epi_accum_lego_inspect_v*.png`, arrays `out/epi/epi_{labels,samples,scores}_lego.npz`.
