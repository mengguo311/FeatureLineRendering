# M1b STEP-06 — forward-warped STROKE temporal residual

Metric: forward-warped stroke temporal residual (discrete Frechet, px) + popping penalty P_pop.  Warp: identical depth-based forward warp for both pipelines.
Held-out: TEST views only; trajectory 5->15.  Stroke variant: `ungated`.

- **A = OURS**: object-space carrier — DT-pulled linelets chained into static 3D polylines, projected into each frame.
- **B = BASELINE**: naive image-space Canny re-traced independently every frame.

| scene | frames | pipeline | Frechet med | Frechet p90 | Chamfer med | **P_pop** | unmatched | cuts | warp-dropped | strokes/frame | verts/stroke |
|---|---|---|---|---|---|---|---|---|---|---|---|
| lego | 30 | OURS | 0.619 | 1.681 | 0.321 | **0.234** | 0.212 | 0.022 | 0.001 | 1121 | 4.98 |
| lego | 30 | BASE | 1.503 | 2.688 | 0.521 | **0.803** | 0.801 | 0.002 | 0.160 | 617 | 2.24 |
| lego | 60 | OURS | 0.330 | 1.320 | 0.188 | **0.144** | 0.120 | 0.024 | 0.001 | 1121 | 4.98 |
| lego | 60 | BASE | 1.399 | 2.633 | 0.483 | **0.764** | 0.762 | 0.002 | 0.160 | 616 | 2.24 |
| lego | 120 | OURS | 0.170 | 0.882 | 0.102 | **0.091** | 0.065 | 0.025 | 0.001 | 1121 | 4.97 |
| lego | 120 | BASE | 1.272 | 2.584 | 0.442 | **0.734** | 0.732 | 0.002 | 0.161 | 617 | 2.24 |
| lego | 240 | OURS | 0.086 | 0.514 | 0.052 | **0.063** | 0.037 | 0.026 | 0.001 | 1122 | 4.97 |
| lego | 240 | BASE | 1.202 | 2.556 | 0.421 | **0.719** | 0.717 | 0.002 | 0.161 | 615 | 2.24 |
| chair | 30 | OURS | 0.330 | 0.708 | 0.181 | **0.093** | 0.050 | 0.043 | 0.000 | 756 | 4.88 |
| chair | 30 | BASE | 1.380 | 2.639 | 0.470 | **0.788** | 0.786 | 0.003 | 0.150 | 577 | 2.25 |
| chair | 60 | OURS | 0.164 | 0.350 | 0.095 | **0.076** | 0.032 | 0.044 | 0.000 | 754 | 4.87 |
| chair | 60 | BASE | 1.293 | 2.617 | 0.434 | **0.770** | 0.768 | 0.003 | 0.148 | 577 | 2.25 |
| chair | 120 | OURS | 0.082 | 0.174 | 0.049 | **0.068** | 0.025 | 0.043 | 0.000 | 752 | 4.88 |
| chair | 120 | BASE | 1.252 | 2.611 | 0.421 | **0.756** | 0.753 | 0.003 | 0.148 | 575 | 2.25 |
| chair | 240 | OURS | 0.041 | 0.086 | 0.024 | **0.067** | 0.023 | 0.043 | 0.000 | 751 | 4.87 |
| chair | 240 | BASE | 1.225 | 2.616 | 0.414 | **0.755** | 0.752 | 0.003 | 0.148 | 578 | 2.25 |

## Headline ratios (BASELINE / OURS — higher means our strokes are steadier)

| scene | frames | Frechet med ratio | P_pop ratio |
|---|---|---|---|
| lego | 30 | 2.43x | 3.44x |
| lego | 60 | 4.24x | 5.30x |
| lego | 120 | 7.49x | 8.10x |
| lego | 240 | 14.03x | 11.49x |
| chair | 30 | 4.19x | 8.52x |
| chair | 60 | 7.87x | 10.17x |
| chair | 120 | 15.22x | 11.11x |
| chair | 240 | 29.92x | 11.35x |

## Stroke graphs

| scene | linelets | after 3D NMS | strokes | median vertices/stroke |
|---|---|---|---|---|
| lego | 25870 | 14302 | 1897 | 4 |
| chair | 16208 | 8679 | 1184 | 4 |
