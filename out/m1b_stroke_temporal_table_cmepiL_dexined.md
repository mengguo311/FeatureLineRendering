# M1b STEP-06 — forward-warped STROKE temporal residual

Metric: forward-warped stroke temporal residual (discrete Frechet, px) + popping penalty P_pop.  Warp: identical depth-based forward warp for both pipelines.
Held-out: TEST views only; trajectory 5->15.  Stroke variant: `cmepiL_dexined`.

- **A = OURS**: object-space carrier — DT-pulled linelets chained into static 3D polylines, projected into each frame.
- **B = BASELINE**: naive image-space Canny re-traced independently every frame.

| scene | frames | pipeline | Frechet med | Frechet p90 | Chamfer med | **P_pop** | unmatched | cuts | warp-dropped | strokes/frame | verts/stroke |
|---|---|---|---|---|---|---|---|---|---|---|---|
| lego | 30 | OURS | 0.593 | 1.656 | 0.314 | **0.223** | 0.200 | 0.023 | 0.000 | 1606 | 4.93 |
| lego | 30 | BASE | 1.506 | 2.679 | 0.517 | **0.803** | 0.801 | 0.002 | 0.160 | 617 | 2.24 |
| lego | 60 | OURS | 0.313 | 1.258 | 0.181 | **0.137** | 0.113 | 0.024 | 0.001 | 1606 | 4.93 |
| lego | 60 | BASE | 1.397 | 2.631 | 0.481 | **0.763** | 0.761 | 0.002 | 0.160 | 616 | 2.24 |
| lego | 120 | OURS | 0.160 | 0.817 | 0.096 | **0.085** | 0.060 | 0.025 | 0.000 | 1605 | 4.93 |
| lego | 120 | BASE | 1.272 | 2.584 | 0.442 | **0.734** | 0.732 | 0.002 | 0.161 | 617 | 2.24 |
| lego | 240 | OURS | 0.080 | 0.456 | 0.049 | **0.062** | 0.035 | 0.026 | 0.000 | 1605 | 4.93 |
| lego | 240 | BASE | 1.202 | 2.556 | 0.420 | **0.719** | 0.717 | 0.002 | 0.161 | 615 | 2.24 |

## Headline ratios (BASELINE / OURS — higher means our strokes are steadier)

| scene | frames | Frechet med ratio | P_pop ratio |
|---|---|---|---|
| lego | 30 | 2.54x | 3.60x |
| lego | 60 | 4.47x | 5.57x |
| lego | 120 | 7.94x | 8.63x |
| lego | 240 | 14.95x | 11.67x |

## Stroke graphs

| scene | linelets | after 3D NMS | strokes | median vertices/stroke |
|---|---|---|---|---|
| lego | 33926 | 19680 | 2655 | 4 |
