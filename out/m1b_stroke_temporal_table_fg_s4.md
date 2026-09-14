# M1b STEP-06 — forward-warped STROKE temporal residual

Metric: forward-warped stroke temporal residual (discrete Frechet, px) + popping penalty P_pop.  Warp: identical depth-based forward warp for both pipelines.
Held-out: TEST views only; trajectory 5->15.  Stroke variant: `step4`.

- **A = OURS**: object-space carrier — DT-pulled linelets chained into static 3D polylines, projected into each frame.
- **B = BASELINE**: naive image-space Canny re-traced independently every frame.

| scene | frames | pipeline | Frechet med | Frechet p90 | Chamfer med | **P_pop** | unmatched | cuts | warp-dropped | strokes/frame | verts/stroke |
|---|---|---|---|---|---|---|---|---|---|---|---|
| gcube | 240 | OURS | 0.024 | 0.047 | 0.019 | **0.084** | 0.084 | 0.000 | 0.000 | 22 | 8.75 |
| gcube | 240 | BASE | 1.286 | 2.487 | 0.440 | **0.595** | 0.593 | 0.002 | 0.000 | 88 | 2.31 |
| gicosa | 240 | OURS | 0.034 | 0.077 | 0.025 | **0.098** | 0.098 | 0.000 | 0.000 | 16 | 4.97 |
| gicosa | 240 | BASE | 1.244 | 2.435 | 0.428 | **0.549** | 0.544 | 0.005 | 0.000 | 19 | 2.16 |
| gprism | 240 | OURS | 0.028 | 0.078 | 0.018 | **0.121** | 0.121 | 0.000 | 0.000 | 31 | 5.37 |
| gprism | 240 | BASE | 1.393 | 2.565 | 0.477 | **0.626** | 0.625 | 0.001 | 0.000 | 26 | 2.29 |

## Headline ratios (BASELINE / OURS — higher means our strokes are steadier)

| scene | frames | Frechet med ratio | P_pop ratio |
|---|---|---|---|
| gcube | 240 | 53.88x | 7.06x |
| gicosa | 240 | 36.96x | 5.60x |
| gprism | 240 | 49.08x | 5.17x |

## Stroke graphs

| scene | linelets | after 3D NMS | strokes | median vertices/stroke |
|---|---|---|---|---|
| gcube | 5610 | 265 | 23 | 6 |
| gicosa | 3828 | 226 | 25 | 5 |
| gprism | 5760 | 360 | 44 | 6 |
