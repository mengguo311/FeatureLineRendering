# M1b STEP-06 — forward-warped STROKE temporal residual

Metric: forward-warped stroke temporal residual (discrete Frechet, px) + popping penalty P_pop.  Warp: identical depth-based forward warp for both pipelines.
Held-out: TEST views only; trajectory 5->15.  Stroke variant: `trackndexined`.

- **A = OURS**: object-space carrier — DT-pulled linelets chained into static 3D polylines, projected into each frame.
- **B = BASELINE**: naive image-space Canny re-traced independently every frame.

| scene | frames | pipeline | Frechet med | Frechet p90 | Chamfer med | **P_pop** | unmatched | cuts | warp-dropped | strokes/frame | verts/stroke |
|---|---|---|---|---|---|---|---|---|---|---|---|
| chair | 30 | OURS | 0.355 | 0.734 | 0.194 | **0.095** | 0.067 | 0.028 | 0.000 | 1001 | 4.80 |
| chair | 30 | BASE | 1.379 | 2.639 | 0.469 | **0.789** | 0.787 | 0.003 | 0.150 | 577 | 2.25 |
| chair | 60 | OURS | 0.178 | 0.362 | 0.103 | **0.071** | 0.043 | 0.028 | 0.000 | 996 | 4.80 |
| chair | 60 | BASE | 1.292 | 2.615 | 0.434 | **0.770** | 0.767 | 0.003 | 0.148 | 577 | 2.25 |
| chair | 120 | OURS | 0.089 | 0.179 | 0.052 | **0.062** | 0.034 | 0.028 | 0.000 | 994 | 4.79 |
| chair | 120 | BASE | 1.251 | 2.612 | 0.421 | **0.755** | 0.753 | 0.003 | 0.148 | 575 | 2.25 |
| chair | 240 | OURS | 0.044 | 0.089 | 0.026 | **0.060** | 0.033 | 0.027 | 0.000 | 993 | 4.79 |
| chair | 240 | BASE | 1.226 | 2.616 | 0.414 | **0.755** | 0.753 | 0.003 | 0.148 | 578 | 2.25 |

## Headline ratios (BASELINE / OURS — higher means our strokes are steadier)

| scene | frames | Frechet med ratio | P_pop ratio |
|---|---|---|---|
| chair | 30 | 3.88x | 8.31x |
| chair | 60 | 7.25x | 10.79x |
| chair | 120 | 14.06x | 12.16x |
| chair | 240 | 27.68x | 12.54x |

## Stroke graphs

| scene | linelets | after 3D NMS | strokes | median vertices/stroke |
|---|---|---|---|---|
| chair | 24625 | 11227 | 1531 | 4 |
