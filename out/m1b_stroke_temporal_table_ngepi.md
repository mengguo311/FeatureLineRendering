# M1b STEP-06 — forward-warped STROKE temporal residual

Metric: forward-warped stroke temporal residual (discrete Frechet, px) + popping penalty P_pop.  Warp: identical depth-based forward warp for both pipelines.
Held-out: TEST views only; trajectory 5->15.  Stroke variant: `ngepi`.

- **A = OURS**: object-space carrier — DT-pulled linelets chained into static 3D polylines, projected into each frame.
- **B = BASELINE**: naive image-space Canny re-traced independently every frame.

| scene | frames | pipeline | Frechet med | Frechet p90 | Chamfer med | **P_pop** | unmatched | cuts | warp-dropped | strokes/frame | verts/stroke |
|---|---|---|---|---|---|---|---|---|---|---|---|
| chair | 30 | OURS | 0.342 | 0.721 | 0.187 | **0.097** | 0.069 | 0.029 | 0.001 | 717 | 4.83 |
| chair | 30 | BASE | 1.385 | 2.643 | 0.470 | **0.788** | 0.786 | 0.003 | 0.150 | 577 | 2.25 |
| chair | 60 | OURS | 0.172 | 0.357 | 0.099 | **0.073** | 0.044 | 0.029 | 0.001 | 715 | 4.82 |
| chair | 60 | BASE | 1.291 | 2.615 | 0.434 | **0.771** | 0.768 | 0.003 | 0.148 | 577 | 2.25 |
| chair | 120 | OURS | 0.086 | 0.177 | 0.050 | **0.064** | 0.035 | 0.029 | 0.001 | 713 | 4.82 |
| chair | 120 | BASE | 1.252 | 2.611 | 0.421 | **0.756** | 0.753 | 0.003 | 0.148 | 575 | 2.25 |
| chair | 240 | OURS | 0.043 | 0.088 | 0.025 | **0.062** | 0.033 | 0.029 | 0.001 | 712 | 4.82 |
| chair | 240 | BASE | 1.225 | 2.616 | 0.414 | **0.755** | 0.752 | 0.003 | 0.148 | 577 | 2.25 |

## Headline ratios (BASELINE / OURS — higher means our strokes are steadier)

| scene | frames | Frechet med ratio | P_pop ratio |
|---|---|---|---|
| chair | 30 | 4.05x | 8.09x |
| chair | 60 | 7.50x | 10.55x |
| chair | 120 | 14.61x | 11.86x |
| chair | 240 | 28.65x | 12.19x |

## Stroke graphs

| scene | linelets | after 3D NMS | strokes | median vertices/stroke |
|---|---|---|---|---|
| chair | 15724 | 8071 | 1113 | 4 |
