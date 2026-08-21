# M1b headline table (measurement only)

Held-out split: 80 train / 10 val / 10 test. All P/R on TEST views [5, 15, 25, 35, 45, 55, 65, 75, 85, 95].

## Scene scoping

| scene | interior frac (solid?) | Canny edge purity@1.5 | GT crease px/kpx | role |
|---|---|---|---|---|
| chair | 0.915 | 0.284 | 90.5 | texture false-positive STRESS scene (most Canny edges are not creases) |
| lego | 0.893 | 0.663 | 230.7 | PRIMARY hard-surface scene (edge field is mostly real geometry) |
| ficus | 0.326 | 0.348 | 134.7 | excluded — thin/foliage: only 33% of object pixels are >4px from a silhouette, so 'crease vs flat surface' is not well posed |

## 1. Held-out TEST P/R — lego (primary, hard-surface)

| protocol | variant | P@1.5 | R@1.5 | P@2.5 | R@2.5 | n |
|---|---|---|---|---|---|---|
| points | ungated | 0.6129 | 0.2720 | 0.7431 | 0.3775 | 25870 |
| points | gated | 0.6251 | 0.2696 | 0.7575 | 0.3735 | 25279 |
| points | **delta** | +0.0123 | -0.0025 | +0.0144 | -0.0040 | |
| segments | ungated | 0.5628 | 0.4193 | 0.7022 | 0.4889 | 25870 |
| segments | gated | 0.5826 | 0.4168 | 0.7259 | 0.4869 | 25279 |
| segments | **delta** | +0.0198 | -0.0025 | +0.0236 | -0.0020 | |

## 2. Temporal flicker — lego, held-out TEST views 5->15

| variant | frames | obj tol % | img tol % | reduction (tol) | a_temp px/f^2 |
|---|---|---|---|---|---|
| ungated | 30 | 9.94 | 9.56 | 0.96x | 5.41064 |
| ungated | 60 | 5.11 | 5.14 | 1.01x | 1.30886 |
| ungated | 120 | 2.43 | 2.90 | 1.19x | 0.32168 |
| ungated | 240 | 1.06 | 1.83 | 1.72x | 0.07973 |
| gated | 30 | 9.88 | 9.56 | 0.97x | 5.41277 |
| gated | 60 | 5.12 | 5.14 | 1.01x | 1.30933 |
| gated | 120 | 2.42 | 2.90 | 1.20x | 0.32179 |
| gated | 240 | 1.05 | 1.83 | 1.74x | 0.07976 |

- **ungated** fitted floors: object-space **-0.10% +- 0.12 (consistent with ZERO)** vs image-space **0.71% +- 0.02** -> **> 5.3x (lower bound; object floor is not resolvably above 0)**
  - directly measured at the finest motion (240 frames): object 1.06% vs image 1.83% = **1.72x** (no model, no extrapolation)

- **gated** fitted floors: object-space **-0.10% +- 0.14 (consistent with ZERO)** vs image-space **0.71% +- 0.02** -> **> 4.0x (lower bound; object floor is not resolvably above 0)**
  - directly measured at the finest motion (240 frames): object 1.05% vs image 1.83% = **1.74x** (no model, no extrapolation)

- temporal guard (gated vs ungated): fitted-floor change +0.004 pp, finest-motion change -0.014 pp (allowed +0.02) -> **PASS**

## 3. chair FP line density inside GT-verified-FLAT regions

| crease clearance | variant | flat area px | FP line px / kpx | FP linelets / kpx |
|---|---|---|---|---|
| crease_clear_5px | ungated | 882582 | 22.12 | 4.30 |
| crease_clear_5px | gated | 882582 | 21.25 | 4.25 |
| crease_clear_5px | **gated vs ungated** | | **-3.9%** | |
| crease_clear_8px | ungated | 803546 | 12.11 | 2.11 |
| crease_clear_8px | gated | 803546 | 11.86 | 2.18 |
| crease_clear_8px | **gated vs ungated** | | **-2.1%** | |
