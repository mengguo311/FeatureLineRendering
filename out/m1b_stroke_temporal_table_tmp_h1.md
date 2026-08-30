# M1b STEP-06 — forward-warped STROKE temporal residual

Metric: forward-warped stroke temporal residual (discrete Frechet, px) + popping penalty P_pop.  Warp: identical depth-based forward warp for both pipelines.
Held-out: TEST views only; trajectory 5->15.  Stroke variant: `h1`.

- **A = OURS**: object-space carrier — DT-pulled linelets chained into static 3D polylines, projected into each frame.
- **B = BASELINE**: naive image-space Canny re-traced independently every frame.

| scene | frames | pipeline | Frechet med | Frechet p90 | Chamfer med | **P_pop** | unmatched | cuts | warp-dropped | strokes/frame | verts/stroke |
|---|---|---|---|---|---|---|---|---|---|---|---|
| chair | 30 | OURS | 0.280 | 0.658 | 0.157 | **0.103** | 0.031 | 0.072 | 0.000 | 603 | 5.04 |
| chair | 30 | BASE | 1.379 | 2.640 | 0.469 | **0.789** | 0.786 | 0.003 | 0.150 | 577 | 2.25 |
| chair | 60 | OURS | 0.139 | 0.323 | 0.083 | **0.090** | 0.018 | 0.072 | 0.000 | 601 | 5.04 |
| chair | 60 | BASE | 1.294 | 2.618 | 0.434 | **0.770** | 0.768 | 0.003 | 0.148 | 577 | 2.25 |
| chair | 120 | OURS | 0.069 | 0.161 | 0.042 | **0.084** | 0.013 | 0.071 | 0.000 | 600 | 5.04 |
| chair | 120 | BASE | 1.254 | 2.613 | 0.421 | **0.756** | 0.753 | 0.003 | 0.148 | 575 | 2.25 |
| chair | 240 | OURS | 0.035 | 0.080 | 0.021 | **0.084** | 0.013 | 0.071 | 0.000 | 600 | 5.04 |
| chair | 240 | BASE | 1.225 | 2.617 | 0.414 | **0.755** | 0.752 | 0.003 | 0.148 | 577 | 2.25 |

## Headline ratios (BASELINE / OURS — higher means our strokes are steadier)

| scene | frames | Frechet med ratio | P_pop ratio |
|---|---|---|---|
| chair | 30 | 4.92x | 7.63x |
| chair | 60 | 9.29x | 8.61x |
| chair | 120 | 18.06x | 8.99x |
| chair | 240 | 35.49x | 8.97x |

## Stroke graphs

| scene | linelets | after 3D NMS | strokes | median vertices/stroke |
|---|---|---|---|---|
| chair | 9967 | 5910 | 810 | 4 |
