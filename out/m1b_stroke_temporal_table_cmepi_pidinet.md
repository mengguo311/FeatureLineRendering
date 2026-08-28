# M1b STEP-06 — forward-warped STROKE temporal residual

Metric: forward-warped stroke temporal residual (discrete Frechet, px) + popping penalty P_pop.  Warp: identical depth-based forward warp for both pipelines.
Held-out: TEST views only; trajectory 5->15.  Stroke variant: `cmepi_pidinet`.

- **A = OURS**: object-space carrier — DT-pulled linelets chained into static 3D polylines, projected into each frame.
- **B = BASELINE**: naive image-space Canny re-traced independently every frame.

| scene | frames | pipeline | Frechet med | Frechet p90 | Chamfer med | **P_pop** | unmatched | cuts | warp-dropped | strokes/frame | verts/stroke |
|---|---|---|---|---|---|---|---|---|---|---|---|
| chair | 30 | OURS | 0.359 | 0.759 | 0.195 | **0.097** | 0.073 | 0.025 | 0.000 | 649 | 4.98 |
| chair | 30 | BASE | 1.376 | 2.630 | 0.468 | **0.789** | 0.786 | 0.003 | 0.150 | 577 | 2.25 |
| chair | 60 | OURS | 0.181 | 0.375 | 0.104 | **0.071** | 0.046 | 0.025 | 0.000 | 646 | 4.98 |
| chair | 60 | BASE | 1.294 | 2.616 | 0.435 | **0.770** | 0.768 | 0.003 | 0.148 | 577 | 2.25 |
| chair | 120 | OURS | 0.091 | 0.186 | 0.053 | **0.061** | 0.036 | 0.025 | 0.000 | 644 | 4.98 |
| chair | 120 | BASE | 1.255 | 2.612 | 0.421 | **0.756** | 0.753 | 0.003 | 0.148 | 575 | 2.25 |
| chair | 240 | OURS | 0.045 | 0.093 | 0.027 | **0.059** | 0.033 | 0.025 | 0.000 | 644 | 4.98 |
| chair | 240 | BASE | 1.226 | 2.616 | 0.414 | **0.755** | 0.752 | 0.003 | 0.148 | 578 | 2.25 |

## Headline ratios (BASELINE / OURS — higher means our strokes are steadier)

| scene | frames | Frechet med ratio | P_pop ratio |
|---|---|---|---|
| chair | 30 | 3.83x | 8.09x |
| chair | 60 | 7.16x | 10.80x |
| chair | 120 | 13.85x | 12.39x |
| chair | 240 | 27.14x | 12.90x |

## Stroke graphs

| scene | linelets | after 3D NMS | strokes | median vertices/stroke |
|---|---|---|---|---|
| chair | 15521 | 8305 | 1110 | 4 |
