# M1b STEP-06 — forward-warped STROKE temporal residual

Metric: forward-warped stroke temporal residual (discrete Frechet, px) + popping penalty P_pop.  Warp: identical depth-based forward warp for both pipelines.
Held-out: TEST views only; trajectory 5->15.  Stroke variant: `ungated`.

- **A = OURS**: object-space carrier — DT-pulled linelets chained into static 3D polylines, projected into each frame.
- **B = BASELINE**: naive image-space Canny re-traced independently every frame.

| scene | frames | pipeline | Frechet med | Frechet p90 | Chamfer med | **P_pop** | unmatched | cuts | warp-dropped | strokes/frame | verts/stroke |
|---|---|---|---|---|---|---|---|---|---|---|---|
| lego | 120 | OURS | 0.175 | 0.965 | 0.107 | **0.132** | 0.100 | 0.032 | 0.000 | 1048 | 4.55 |
| lego | 120 | BASE | 1.253 | 2.585 | 0.444 | **0.699** | 0.697 | 0.003 | 0.000 | 413 | 2.17 |
| lego | 240 | OURS | 0.088 | 0.549 | 0.055 | **0.105** | 0.073 | 0.032 | 0.000 | 1048 | 4.55 |
| lego | 240 | BASE | 1.189 | 2.568 | 0.419 | **0.680** | 0.678 | 0.002 | 0.000 | 411 | 2.17 |
| chair | 120 | OURS | 0.082 | 0.179 | 0.049 | **0.103** | 0.051 | 0.053 | 0.000 | 712 | 4.59 |
| chair | 120 | BASE | 1.213 | 2.593 | 0.417 | **0.708** | 0.706 | 0.002 | 0.000 | 282 | 2.19 |
| chair | 240 | OURS | 0.041 | 0.089 | 0.025 | **0.100** | 0.047 | 0.053 | 0.000 | 711 | 4.59 |
| chair | 240 | BASE | 1.176 | 2.594 | 0.406 | **0.704** | 0.702 | 0.002 | 0.000 | 283 | 2.19 |

## Headline ratios (BASELINE / OURS — higher means our strokes are steadier)

| scene | frames | Frechet med ratio | P_pop ratio |
|---|---|---|---|
| lego | 120 | 7.15x | 5.29x |
| lego | 240 | 13.44x | 6.49x |
| chair | 120 | 14.83x | 6.85x |
| chair | 240 | 28.79x | 7.01x |

## Stroke graphs

| scene | linelets | after 3D NMS | strokes | median vertices/stroke |
|---|---|---|---|---|
| lego | 25870 | 14302 | 1897 | 4 |
| chair | 16208 | 8679 | 1184 | 4 |
