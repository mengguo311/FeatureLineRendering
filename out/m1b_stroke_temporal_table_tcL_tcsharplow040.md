# M1b STEP-06 — forward-warped STROKE temporal residual

Metric: forward-warped stroke temporal residual (discrete Frechet, px) + popping penalty P_pop.  Warp: identical depth-based forward warp for both pipelines.
Held-out: TEST views only; trajectory 5->15.  Stroke variant: `tcsharplow040`.

- **A = OURS**: object-space carrier — DT-pulled linelets chained into static 3D polylines, projected into each frame.
- **B = BASELINE**: naive image-space Canny re-traced independently every frame.

| scene | frames | pipeline | Frechet med | Frechet p90 | Chamfer med | **P_pop** | unmatched | cuts | warp-dropped | strokes/frame | verts/stroke |
|---|---|---|---|---|---|---|---|---|---|---|---|
| lego | 30 | OURS | 0.563 | 1.642 | 0.292 | **0.240** | 0.202 | 0.037 | 0.000 | 1830 | 4.51 |
| lego | 30 | BASE | 1.503 | 2.684 | 0.520 | **0.803** | 0.801 | 0.002 | 0.160 | 617 | 2.24 |
| lego | 60 | OURS | 0.297 | 1.323 | 0.174 | **0.148** | 0.108 | 0.040 | 0.000 | 1829 | 4.51 |
| lego | 60 | BASE | 1.396 | 2.631 | 0.482 | **0.764** | 0.762 | 0.002 | 0.160 | 616 | 2.24 |
| lego | 120 | OURS | 0.152 | 0.872 | 0.094 | **0.097** | 0.055 | 0.042 | 0.000 | 1830 | 4.50 |
| lego | 120 | BASE | 1.273 | 2.583 | 0.442 | **0.734** | 0.732 | 0.002 | 0.161 | 617 | 2.24 |
| lego | 240 | OURS | 0.076 | 0.475 | 0.048 | **0.074** | 0.032 | 0.042 | 0.000 | 1830 | 4.50 |
| lego | 240 | BASE | 1.201 | 2.554 | 0.420 | **0.719** | 0.717 | 0.002 | 0.161 | 615 | 2.24 |

## Headline ratios (BASELINE / OURS — higher means our strokes are steadier)

| scene | frames | Frechet med ratio | P_pop ratio |
|---|---|---|---|
| lego | 30 | 2.67x | 3.35x |
| lego | 60 | 4.70x | 5.16x |
| lego | 120 | 8.39x | 7.55x |
| lego | 240 | 15.81x | 9.67x |

## Stroke graphs

| scene | linelets | after 3D NMS | strokes | median vertices/stroke |
|---|---|---|---|---|
| lego | 35288 | 23273 | 3272 | 4 |
