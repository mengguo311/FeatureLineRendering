# M1b STEP-06 — forward-warped STROKE temporal residual

Metric: forward-warped stroke temporal residual (discrete Frechet, px) + popping penalty P_pop.  Warp: identical depth-based forward warp for both pipelines.
Held-out: TEST views only; trajectory 5->15.  Stroke variant: `cmepi_dexined`.

- **A = OURS**: object-space carrier — DT-pulled linelets chained into static 3D polylines, projected into each frame.
- **B = BASELINE**: naive image-space Canny re-traced independently every frame.

| scene | frames | pipeline | Frechet med | Frechet p90 | Chamfer med | **P_pop** | unmatched | cuts | warp-dropped | strokes/frame | verts/stroke |
|---|---|---|---|---|---|---|---|---|---|---|---|
| chair | 30 | OURS | 0.356 | 0.740 | 0.194 | **0.096** | 0.075 | 0.021 | 0.000 | 682 | 5.09 |
| chair | 30 | BASE | 1.384 | 2.641 | 0.470 | **0.788** | 0.786 | 0.003 | 0.150 | 577 | 2.25 |
| chair | 60 | OURS | 0.180 | 0.366 | 0.102 | **0.068** | 0.047 | 0.022 | 0.001 | 679 | 5.08 |
| chair | 60 | BASE | 1.294 | 2.615 | 0.434 | **0.770** | 0.767 | 0.003 | 0.148 | 577 | 2.25 |
| chair | 120 | OURS | 0.090 | 0.182 | 0.052 | **0.059** | 0.038 | 0.021 | 0.001 | 678 | 5.08 |
| chair | 120 | BASE | 1.256 | 2.612 | 0.421 | **0.756** | 0.753 | 0.003 | 0.148 | 575 | 2.25 |
| chair | 240 | OURS | 0.045 | 0.091 | 0.026 | **0.057** | 0.035 | 0.022 | 0.001 | 677 | 5.08 |
| chair | 240 | BASE | 1.225 | 2.616 | 0.414 | **0.755** | 0.753 | 0.003 | 0.148 | 578 | 2.25 |

## Headline ratios (BASELINE / OURS — higher means our strokes are steadier)

| scene | frames | Frechet med ratio | P_pop ratio |
|---|---|---|---|
| chair | 30 | 3.88x | 8.25x |
| chair | 60 | 7.20x | 11.28x |
| chair | 120 | 14.00x | 12.70x |
| chair | 240 | 27.36x | 13.33x |

## Stroke graphs

| scene | linelets | after 3D NMS | strokes | median vertices/stroke |
|---|---|---|---|---|
| chair | 15456 | 8144 | 1056 | 4 |
