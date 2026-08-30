# M1b STEP-06 — forward-warped STROKE temporal residual

Metric: forward-warped stroke temporal residual (discrete Frechet, px) + popping penalty P_pop.  Warp: identical depth-based forward warp for both pipelines.
Held-out: TEST views only; trajectory 5->15.  Stroke variant: `ngmec040`.

- **A = OURS**: object-space carrier — DT-pulled linelets chained into static 3D polylines, projected into each frame.
- **B = BASELINE**: naive image-space Canny re-traced independently every frame.

| scene | frames | pipeline | Frechet med | Frechet p90 | Chamfer med | **P_pop** | unmatched | cuts | warp-dropped | strokes/frame | verts/stroke |
|---|---|---|---|---|---|---|---|---|---|---|---|
| lego | 30 | OURS | 0.582 | 1.595 | 0.306 | **0.228** | 0.202 | 0.026 | 0.001 | 1638 | 4.87 |
| lego | 30 | BASE | 1.507 | 2.683 | 0.519 | **0.803** | 0.801 | 0.002 | 0.160 | 617 | 2.24 |
| lego | 60 | OURS | 0.305 | 1.184 | 0.177 | **0.145** | 0.117 | 0.028 | 0.001 | 1636 | 4.87 |
| lego | 60 | BASE | 1.399 | 2.633 | 0.482 | **0.763** | 0.762 | 0.002 | 0.160 | 616 | 2.24 |
| lego | 120 | OURS | 0.157 | 0.820 | 0.095 | **0.091** | 0.062 | 0.029 | 0.001 | 1637 | 4.87 |
| lego | 120 | BASE | 1.272 | 2.585 | 0.442 | **0.734** | 0.732 | 0.002 | 0.161 | 617 | 2.24 |
| lego | 240 | OURS | 0.079 | 0.469 | 0.048 | **0.065** | 0.035 | 0.030 | 0.001 | 1636 | 4.87 |
| lego | 240 | BASE | 1.202 | 2.556 | 0.420 | **0.719** | 0.717 | 0.002 | 0.161 | 615 | 2.24 |

## Headline ratios (BASELINE / OURS — higher means our strokes are steadier)

| scene | frames | Frechet med ratio | P_pop ratio |
|---|---|---|---|
| lego | 30 | 2.59x | 3.52x |
| lego | 60 | 4.58x | 5.28x |
| lego | 120 | 8.11x | 8.11x |
| lego | 240 | 15.24x | 11.09x |

## Stroke graphs

| scene | linelets | after 3D NMS | strokes | median vertices/stroke |
|---|---|---|---|---|
| lego | 34987 | 19919 | 2744 | 4 |
