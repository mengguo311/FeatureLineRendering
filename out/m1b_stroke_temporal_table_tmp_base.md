# M1b STEP-06 — forward-warped STROKE temporal residual

Metric: forward-warped stroke temporal residual (discrete Frechet, px) + popping penalty P_pop.  Warp: identical depth-based forward warp for both pipelines.
Held-out: TEST views only; trajectory 5->15.  Stroke variant: `base`.

- **A = OURS**: object-space carrier — DT-pulled linelets chained into static 3D polylines, projected into each frame.
- **B = BASELINE**: naive image-space Canny re-traced independently every frame.

| scene | frames | pipeline | Frechet med | Frechet p90 | Chamfer med | **P_pop** | unmatched | cuts | warp-dropped | strokes/frame | verts/stroke |
|---|---|---|---|---|---|---|---|---|---|---|---|
| chair | 30 | OURS | 0.322 | 0.708 | 0.178 | **0.096** | 0.049 | 0.047 | 0.000 | 759 | 4.93 |
| chair | 30 | BASE | 1.383 | 2.646 | 0.469 | **0.788** | 0.786 | 0.003 | 0.150 | 577 | 2.25 |
| chair | 60 | OURS | 0.160 | 0.348 | 0.093 | **0.079** | 0.033 | 0.047 | 0.000 | 756 | 4.93 |
| chair | 60 | BASE | 1.294 | 2.616 | 0.435 | **0.770** | 0.767 | 0.003 | 0.148 | 577 | 2.25 |
| chair | 120 | OURS | 0.080 | 0.173 | 0.047 | **0.072** | 0.026 | 0.047 | 0.000 | 754 | 4.93 |
| chair | 120 | BASE | 1.252 | 2.612 | 0.421 | **0.756** | 0.753 | 0.003 | 0.148 | 575 | 2.25 |
| chair | 240 | OURS | 0.040 | 0.086 | 0.024 | **0.071** | 0.024 | 0.047 | 0.000 | 754 | 4.93 |
| chair | 240 | BASE | 1.225 | 2.616 | 0.414 | **0.755** | 0.752 | 0.003 | 0.148 | 578 | 2.25 |

## Headline ratios (BASELINE / OURS — higher means our strokes are steadier)

| scene | frames | Frechet med ratio | P_pop ratio |
|---|---|---|---|
| chair | 30 | 4.30x | 8.25x |
| chair | 60 | 8.06x | 9.74x |
| chair | 120 | 15.68x | 10.43x |
| chair | 240 | 30.79x | 10.71x |

## Stroke graphs

| scene | linelets | after 3D NMS | strokes | median vertices/stroke |
|---|---|---|---|---|
| chair | 16039 | 8508 | 1166 | 4 |
