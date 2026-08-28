# M1b STEP-06 — forward-warped STROKE temporal residual

Metric: forward-warped stroke temporal residual (discrete Frechet, px) + popping penalty P_pop.  Warp: identical depth-based forward warp for both pipelines.
Held-out: TEST views only; trajectory 5->15.  Stroke variant: `tgapC`.

- **A = OURS**: object-space carrier — DT-pulled linelets chained into static 3D polylines, projected into each frame.
- **B = BASELINE**: naive image-space Canny re-traced independently every frame.

| scene | frames | pipeline | Frechet med | Frechet p90 | Chamfer med | **P_pop** | unmatched | cuts | warp-dropped | strokes/frame | verts/stroke |
|---|---|---|---|---|---|---|---|---|---|---|---|
| lego | 30 | OURS | 0.576 | 1.781 | 0.305 | **0.238** | 0.207 | 0.031 | 0.000 | 1466 | 4.89 |
| lego | 30 | BASE | 1.508 | 2.689 | 0.518 | **0.803** | 0.801 | 0.002 | 0.160 | 616 | 2.24 |
| lego | 60 | OURS | 0.306 | 1.362 | 0.179 | **0.152** | 0.118 | 0.034 | 0.001 | 1467 | 4.90 |
| lego | 60 | BASE | 1.396 | 2.630 | 0.481 | **0.764** | 0.763 | 0.002 | 0.160 | 616 | 2.24 |
| lego | 120 | OURS | 0.157 | 0.928 | 0.097 | **0.097** | 0.062 | 0.035 | 0.000 | 1468 | 4.89 |
| lego | 120 | BASE | 1.274 | 2.586 | 0.441 | **0.734** | 0.732 | 0.002 | 0.161 | 617 | 2.24 |
| lego | 240 | OURS | 0.079 | 0.541 | 0.049 | **0.069** | 0.032 | 0.036 | 0.001 | 1469 | 4.89 |
| lego | 240 | BASE | 1.203 | 2.554 | 0.421 | **0.719** | 0.717 | 0.002 | 0.161 | 615 | 2.24 |

## Headline ratios (BASELINE / OURS — higher means our strokes are steadier)

| scene | frames | Frechet med ratio | P_pop ratio |
|---|---|---|---|
| lego | 30 | 2.62x | 3.38x |
| lego | 60 | 4.56x | 5.04x |
| lego | 120 | 8.09x | 7.56x |
| lego | 240 | 15.15x | 10.47x |

## Stroke graphs

| scene | linelets | after 3D NMS | strokes | median vertices/stroke |
|---|---|---|---|---|
| lego | 34334 | 18528 | 2535 | 4 |
