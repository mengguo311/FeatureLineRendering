# M1b STEP-06 — forward-warped STROKE temporal residual

Metric: forward-warped stroke temporal residual (discrete Frechet, px) + popping penalty P_pop.  Warp: identical depth-based forward warp for both pipelines.
Held-out: TEST views only; trajectory 5->15.  Stroke variant: `cmepiL_pidinet`.

- **A = OURS**: object-space carrier — DT-pulled linelets chained into static 3D polylines, projected into each frame.
- **B = BASELINE**: naive image-space Canny re-traced independently every frame.

| scene | frames | pipeline | Frechet med | Frechet p90 | Chamfer med | **P_pop** | unmatched | cuts | warp-dropped | strokes/frame | verts/stroke |
|---|---|---|---|---|---|---|---|---|---|---|---|
| lego | 30 | OURS | 0.587 | 1.547 | 0.306 | **0.220** | 0.195 | 0.025 | 0.001 | 1440 | 4.99 |
| lego | 30 | BASE | 1.503 | 2.687 | 0.517 | **0.803** | 0.802 | 0.002 | 0.160 | 616 | 2.24 |
| lego | 60 | OURS | 0.308 | 1.236 | 0.177 | **0.136** | 0.110 | 0.026 | 0.000 | 1440 | 4.99 |
| lego | 60 | BASE | 1.397 | 2.631 | 0.481 | **0.764** | 0.762 | 0.002 | 0.160 | 616 | 2.24 |
| lego | 120 | OURS | 0.158 | 0.842 | 0.095 | **0.088** | 0.060 | 0.028 | 0.001 | 1440 | 4.99 |
| lego | 120 | BASE | 1.273 | 2.585 | 0.442 | **0.734** | 0.732 | 0.002 | 0.161 | 617 | 2.24 |
| lego | 240 | OURS | 0.080 | 0.504 | 0.048 | **0.060** | 0.032 | 0.029 | 0.001 | 1441 | 4.99 |
| lego | 240 | BASE | 1.202 | 2.554 | 0.421 | **0.719** | 0.717 | 0.002 | 0.161 | 615 | 2.24 |

## Headline ratios (BASELINE / OURS — higher means our strokes are steadier)

| scene | frames | Frechet med ratio | P_pop ratio |
|---|---|---|---|
| lego | 30 | 2.56x | 3.65x |
| lego | 60 | 4.53x | 5.61x |
| lego | 120 | 8.04x | 8.39x |
| lego | 240 | 15.05x | 11.90x |

## Stroke graphs

| scene | linelets | after 3D NMS | strokes | median vertices/stroke |
|---|---|---|---|---|
| lego | 31461 | 16756 | 2240 | 4 |
