# M1b STEP-06 — forward-warped STROKE temporal residual

Metric: forward-warped stroke temporal residual (discrete Frechet, px) + popping penalty P_pop.  Warp: identical depth-based forward warp for both pipelines.
Held-out: TEST views only; trajectory 5->15.  Stroke variant: `tgapS`.

- **A = OURS**: object-space carrier — DT-pulled linelets chained into static 3D polylines, projected into each frame.
- **B = BASELINE**: naive image-space Canny re-traced independently every frame.

| scene | frames | pipeline | Frechet med | Frechet p90 | Chamfer med | **P_pop** | unmatched | cuts | warp-dropped | strokes/frame | verts/stroke |
|---|---|---|---|---|---|---|---|---|---|---|---|
| lego | 30 | OURS | 0.579 | 1.768 | 0.303 | **0.240** | 0.209 | 0.031 | 0.001 | 1514 | 4.90 |
| lego | 30 | BASE | 1.505 | 2.680 | 0.518 | **0.803** | 0.801 | 0.002 | 0.160 | 616 | 2.24 |
| lego | 60 | OURS | 0.308 | 1.360 | 0.179 | **0.153** | 0.119 | 0.034 | 0.001 | 1514 | 4.91 |
| lego | 60 | BASE | 1.396 | 2.633 | 0.482 | **0.763** | 0.761 | 0.002 | 0.160 | 616 | 2.24 |
| lego | 120 | OURS | 0.158 | 0.935 | 0.097 | **0.097** | 0.062 | 0.035 | 0.001 | 1514 | 4.91 |
| lego | 120 | BASE | 1.275 | 2.584 | 0.442 | **0.734** | 0.732 | 0.002 | 0.161 | 617 | 2.24 |
| lego | 240 | OURS | 0.080 | 0.546 | 0.049 | **0.069** | 0.033 | 0.036 | 0.001 | 1515 | 4.90 |
| lego | 240 | BASE | 1.204 | 2.555 | 0.420 | **0.719** | 0.717 | 0.002 | 0.161 | 615 | 2.24 |

## Headline ratios (BASELINE / OURS — higher means our strokes are steadier)

| scene | frames | Frechet med ratio | P_pop ratio |
|---|---|---|---|
| lego | 30 | 2.60x | 3.34x |
| lego | 60 | 4.54x | 4.99x |
| lego | 120 | 8.05x | 7.54x |
| lego | 240 | 15.06x | 10.45x |

## Stroke graphs

| scene | linelets | after 3D NMS | strokes | median vertices/stroke |
|---|---|---|---|---|
| lego | 35521 | 19077 | 2602 | 4 |
