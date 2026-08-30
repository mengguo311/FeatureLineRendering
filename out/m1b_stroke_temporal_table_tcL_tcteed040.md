# M1b STEP-06 — forward-warped STROKE temporal residual

Metric: forward-warped stroke temporal residual (discrete Frechet, px) + popping penalty P_pop.  Warp: identical depth-based forward warp for both pipelines.
Held-out: TEST views only; trajectory 5->15.  Stroke variant: `tcteed040`.

- **A = OURS**: object-space carrier — DT-pulled linelets chained into static 3D polylines, projected into each frame.
- **B = BASELINE**: naive image-space Canny re-traced independently every frame.

| scene | frames | pipeline | Frechet med | Frechet p90 | Chamfer med | **P_pop** | unmatched | cuts | warp-dropped | strokes/frame | verts/stroke |
|---|---|---|---|---|---|---|---|---|---|---|---|
| lego | 30 | OURS | 0.598 | 1.613 | 0.314 | **0.230** | 0.211 | 0.019 | 0.000 | 1641 | 4.86 |
| lego | 30 | BASE | 1.509 | 2.684 | 0.520 | **0.803** | 0.802 | 0.002 | 0.160 | 617 | 2.24 |
| lego | 60 | OURS | 0.316 | 1.267 | 0.183 | **0.139** | 0.119 | 0.020 | 0.000 | 1640 | 4.86 |
| lego | 60 | BASE | 1.397 | 2.631 | 0.481 | **0.764** | 0.762 | 0.002 | 0.160 | 616 | 2.24 |
| lego | 120 | OURS | 0.162 | 0.855 | 0.097 | **0.084** | 0.063 | 0.022 | 0.000 | 1640 | 4.86 |
| lego | 120 | BASE | 1.273 | 2.582 | 0.441 | **0.734** | 0.732 | 0.002 | 0.161 | 617 | 2.24 |
| lego | 240 | OURS | 0.081 | 0.478 | 0.050 | **0.059** | 0.037 | 0.022 | 0.000 | 1640 | 4.86 |
| lego | 240 | BASE | 1.202 | 2.556 | 0.420 | **0.719** | 0.717 | 0.002 | 0.161 | 615 | 2.24 |

## Headline ratios (BASELINE / OURS — higher means our strokes are steadier)

| scene | frames | Frechet med ratio | P_pop ratio |
|---|---|---|---|
| lego | 30 | 2.52x | 3.49x |
| lego | 60 | 4.42x | 5.48x |
| lego | 120 | 7.86x | 8.69x |
| lego | 240 | 14.81x | 12.10x |

## Stroke graphs

| scene | linelets | after 3D NMS | strokes | median vertices/stroke |
|---|---|---|---|---|
| lego | 35028 | 20595 | 2846 | 4 |
