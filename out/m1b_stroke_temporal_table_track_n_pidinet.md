# M1b STEP-06 — forward-warped STROKE temporal residual

Metric: forward-warped stroke temporal residual (discrete Frechet, px) + popping penalty P_pop.  Warp: identical depth-based forward warp for both pipelines.
Held-out: TEST views only; trajectory 5->15.  Stroke variant: `tracknpidinet`.

- **A = OURS**: object-space carrier — DT-pulled linelets chained into static 3D polylines, projected into each frame.
- **B = BASELINE**: naive image-space Canny re-traced independently every frame.

| scene | frames | pipeline | Frechet med | Frechet p90 | Chamfer med | **P_pop** | unmatched | cuts | warp-dropped | strokes/frame | verts/stroke |
|---|---|---|---|---|---|---|---|---|---|---|---|
| chair | 30 | OURS | 0.365 | 0.744 | 0.199 | **0.092** | 0.070 | 0.022 | 0.000 | 960 | 4.80 |
| chair | 30 | BASE | 1.379 | 2.643 | 0.469 | **0.789** | 0.786 | 0.003 | 0.150 | 577 | 2.25 |
| chair | 60 | OURS | 0.183 | 0.367 | 0.105 | **0.067** | 0.046 | 0.021 | 0.000 | 957 | 4.79 |
| chair | 60 | BASE | 1.290 | 2.611 | 0.434 | **0.770** | 0.768 | 0.003 | 0.148 | 577 | 2.25 |
| chair | 120 | OURS | 0.091 | 0.182 | 0.053 | **0.059** | 0.038 | 0.021 | 0.000 | 955 | 4.79 |
| chair | 120 | BASE | 1.251 | 2.611 | 0.421 | **0.756** | 0.753 | 0.003 | 0.148 | 575 | 2.25 |
| chair | 240 | OURS | 0.046 | 0.091 | 0.027 | **0.056** | 0.035 | 0.021 | 0.000 | 954 | 4.79 |
| chair | 240 | BASE | 1.224 | 2.614 | 0.414 | **0.756** | 0.753 | 0.003 | 0.148 | 578 | 2.25 |

## Headline ratios (BASELINE / OURS — higher means our strokes are steadier)

| scene | frames | Frechet med ratio | P_pop ratio |
|---|---|---|---|
| chair | 30 | 3.78x | 8.55x |
| chair | 60 | 7.04x | 11.44x |
| chair | 120 | 13.68x | 12.87x |
| chair | 240 | 26.84x | 13.49x |

## Stroke graphs

| scene | linelets | after 3D NMS | strokes | median vertices/stroke |
|---|---|---|---|---|
| chair | 24515 | 11167 | 1517 | 4 |
