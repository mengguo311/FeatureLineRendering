# M1b STEP-06 — forward-warped STROKE temporal residual

Metric: forward-warped stroke temporal residual (discrete Frechet, px) + popping penalty P_pop.  Warp: identical depth-based forward warp for both pipelines.
Held-out: TEST views only; trajectory 5->15.  Stroke variant: `eco_lego`.

- **A = OURS**: object-space carrier — DT-pulled linelets chained into static 3D polylines, projected into each frame.
- **B = BASELINE**: naive image-space Canny re-traced independently every frame.

| scene | frames | pipeline | Frechet med | Frechet p90 | Chamfer med | **P_pop** | unmatched | cuts | warp-dropped | strokes/frame | verts/stroke |
|---|---|---|---|---|---|---|---|---|---|---|---|
| lego | 30 | OURS | 0.580 | 1.597 | 0.307 | **0.219** | 0.197 | 0.022 | 0.001 | 1581 | 4.95 |
| lego | 30 | BASE | 1.510 | 2.685 | 0.519 | **0.803** | 0.801 | 0.002 | 0.160 | 616 | 2.24 |
| lego | 60 | OURS | 0.304 | 1.236 | 0.177 | **0.133** | 0.109 | 0.023 | 0.000 | 1580 | 4.95 |
| lego | 60 | BASE | 1.394 | 2.626 | 0.480 | **0.764** | 0.762 | 0.002 | 0.160 | 616 | 2.24 |
| lego | 120 | OURS | 0.156 | 0.793 | 0.094 | **0.082** | 0.059 | 0.024 | 0.001 | 1581 | 4.94 |
| lego | 120 | BASE | 1.274 | 2.582 | 0.442 | **0.734** | 0.732 | 0.002 | 0.161 | 617 | 2.24 |
| lego | 240 | OURS | 0.078 | 0.440 | 0.048 | **0.059** | 0.035 | 0.024 | 0.000 | 1581 | 4.94 |
| lego | 240 | BASE | 1.204 | 2.556 | 0.421 | **0.719** | 0.717 | 0.002 | 0.161 | 615 | 2.24 |

## Headline ratios (BASELINE / OURS — higher means our strokes are steadier)

| scene | frames | Frechet med ratio | P_pop ratio |
|---|---|---|---|
| lego | 30 | 2.60x | 3.67x |
| lego | 60 | 4.59x | 5.76x |
| lego | 120 | 8.19x | 8.92x |
| lego | 240 | 15.42x | 12.09x |

## Stroke graphs

| scene | linelets | after 3D NMS | strokes | median vertices/stroke |
|---|---|---|---|---|
| lego | 33698 | 19123 | 2574 | 4 |
