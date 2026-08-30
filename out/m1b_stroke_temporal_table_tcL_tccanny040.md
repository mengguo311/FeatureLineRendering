# M1b STEP-06 — forward-warped STROKE temporal residual

Metric: forward-warped stroke temporal residual (discrete Frechet, px) + popping penalty P_pop.  Warp: identical depth-based forward warp for both pipelines.
Held-out: TEST views only; trajectory 5->15.  Stroke variant: `tccanny040`.

- **A = OURS**: object-space carrier — DT-pulled linelets chained into static 3D polylines, projected into each frame.
- **B = BASELINE**: naive image-space Canny re-traced independently every frame.

| scene | frames | pipeline | Frechet med | Frechet p90 | Chamfer med | **P_pop** | unmatched | cuts | warp-dropped | strokes/frame | verts/stroke |
|---|---|---|---|---|---|---|---|---|---|---|---|
| lego | 30 | OURS | 0.628 | 1.669 | 0.322 | **0.234** | 0.211 | 0.023 | 0.000 | 1422 | 4.93 |
| lego | 30 | BASE | 1.509 | 2.692 | 0.517 | **0.803** | 0.801 | 0.002 | 0.160 | 617 | 2.24 |
| lego | 60 | OURS | 0.332 | 1.294 | 0.186 | **0.144** | 0.119 | 0.025 | 0.000 | 1422 | 4.93 |
| lego | 60 | BASE | 1.395 | 2.630 | 0.480 | **0.764** | 0.762 | 0.002 | 0.160 | 616 | 2.24 |
| lego | 120 | OURS | 0.171 | 0.870 | 0.101 | **0.091** | 0.064 | 0.026 | 0.000 | 1424 | 4.93 |
| lego | 120 | BASE | 1.273 | 2.586 | 0.442 | **0.734** | 0.732 | 0.002 | 0.161 | 617 | 2.24 |
| lego | 240 | OURS | 0.086 | 0.506 | 0.052 | **0.062** | 0.034 | 0.028 | 0.000 | 1424 | 4.93 |
| lego | 240 | BASE | 1.201 | 2.555 | 0.420 | **0.719** | 0.717 | 0.002 | 0.161 | 615 | 2.24 |

## Headline ratios (BASELINE / OURS — higher means our strokes are steadier)

| scene | frames | Frechet med ratio | P_pop ratio |
|---|---|---|---|
| lego | 30 | 2.40x | 3.44x |
| lego | 60 | 4.20x | 5.30x |
| lego | 120 | 7.46x | 8.11x |
| lego | 240 | 13.95x | 11.61x |

## Stroke graphs

| scene | linelets | after 3D NMS | strokes | median vertices/stroke |
|---|---|---|---|---|
| lego | 33133 | 17916 | 2408 | 4 |
