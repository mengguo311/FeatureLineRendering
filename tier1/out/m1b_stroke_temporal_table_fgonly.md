# M1b STEP-06 — forward-warped STROKE temporal residual

Metric: forward-warped stroke temporal residual (discrete Frechet, px) + popping penalty P_pop.  Warp: identical depth-based forward warp for both pipelines.
Held-out: TEST views only; trajectory 5->15.  Stroke variant: `ungated`.

- **A = OURS**: object-space carrier — DT-pulled linelets chained into static 3D polylines, projected into each frame.
- **B = BASELINE**: naive image-space Canny re-traced independently every frame.

| scene | frames | pipeline | Frechet med | Frechet p90 | Chamfer med | **P_pop** | unmatched | cuts | warp-dropped | strokes/frame | verts/stroke |
|---|---|---|---|---|---|---|---|---|---|---|---|
| lego | 120 | OURS | 0.189 | 1.063 | 0.112 | **0.160** | 0.123 | 0.036 | 0.000 | 745 | 4.46 |
| lego | 120 | BASE | 1.310 | 2.629 | 0.451 | **0.703** | 0.700 | 0.003 | 0.000 | 271 | 2.17 |
| lego | 240 | OURS | 0.096 | 0.638 | 0.058 | **0.115** | 0.078 | 0.037 | 0.000 | 744 | 4.46 |
| lego | 240 | BASE | 1.214 | 2.584 | 0.426 | **0.673** | 0.670 | 0.003 | 0.000 | 271 | 2.17 |
| chair | 120 | OURS | 0.083 | 0.180 | 0.051 | **0.144** | 0.084 | 0.060 | 0.000 | 427 | 4.39 |
| chair | 120 | BASE | 1.199 | 2.575 | 0.411 | **0.728** | 0.725 | 0.003 | 0.000 | 168 | 2.19 |
| chair | 240 | OURS | 0.041 | 0.089 | 0.026 | **0.132** | 0.073 | 0.059 | 0.000 | 426 | 4.39 |
| chair | 240 | BASE | 1.164 | 2.560 | 0.401 | **0.718** | 0.716 | 0.002 | 0.000 | 166 | 2.19 |

## Headline ratios (BASELINE / OURS — higher means our strokes are steadier)

| scene | frames | Frechet med ratio | P_pop ratio |
|---|---|---|---|
| lego | 120 | 6.94x | 4.41x |
| lego | 240 | 12.69x | 5.83x |
| chair | 120 | 14.46x | 5.05x |
| chair | 240 | 28.09x | 5.44x |

## Stroke graphs

| scene | linelets | after 3D NMS | strokes | median vertices/stroke |
|---|---|---|---|---|
| lego | 25870 | 14302 | 1897 | 4 |
| chair | 16208 | 8679 | 1184 | 4 |
