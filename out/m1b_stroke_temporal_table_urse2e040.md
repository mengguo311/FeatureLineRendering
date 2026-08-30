# M1b STEP-06 — forward-warped STROKE temporal residual

Metric: forward-warped stroke temporal residual (discrete Frechet, px) + popping penalty P_pop.  Warp: identical depth-based forward warp for both pipelines.
Held-out: TEST views only; trajectory 5->15.  Stroke variant: `urse2e040`.

- **A = OURS**: object-space carrier — DT-pulled linelets chained into static 3D polylines, projected into each frame.
- **B = BASELINE**: naive image-space Canny re-traced independently every frame.

| scene | frames | pipeline | Frechet med | Frechet p90 | Chamfer med | **P_pop** | unmatched | cuts | warp-dropped | strokes/frame | verts/stroke |
|---|---|---|---|---|---|---|---|---|---|---|---|
| lego | 30 | OURS | 0.857 | 2.256 | 0.415 | **0.369** | 0.366 | 0.002 | 0.006 | 1522 | 4.29 |
| lego | 30 | BASE | 1.502 | 2.679 | 0.520 | **0.803** | 0.801 | 0.002 | 0.160 | 616 | 2.24 |
| lego | 60 | OURS | 0.515 | 1.937 | 0.277 | **0.193** | 0.190 | 0.003 | 0.007 | 1521 | 4.29 |
| lego | 60 | BASE | 1.397 | 2.631 | 0.482 | **0.764** | 0.762 | 0.002 | 0.160 | 616 | 2.24 |
| lego | 120 | OURS | 0.274 | 1.233 | 0.160 | **0.107** | 0.104 | 0.003 | 0.007 | 1520 | 4.30 |
| lego | 120 | BASE | 1.273 | 2.585 | 0.442 | **0.734** | 0.732 | 0.002 | 0.161 | 617 | 2.24 |
| lego | 240 | OURS | 0.139 | 0.683 | 0.084 | **0.070** | 0.067 | 0.003 | 0.007 | 1521 | 4.29 |
| lego | 240 | BASE | 1.203 | 2.555 | 0.421 | **0.719** | 0.717 | 0.002 | 0.161 | 615 | 2.24 |

## Headline ratios (BASELINE / OURS — higher means our strokes are steadier)

| scene | frames | Frechet med ratio | P_pop ratio |
|---|---|---|---|
| lego | 30 | 1.75x | 2.18x |
| lego | 60 | 2.71x | 3.95x |
| lego | 120 | 4.64x | 6.86x |
| lego | 240 | 8.64x | 10.21x |

## Stroke graphs

| scene | linelets | after 3D NMS | strokes | median vertices/stroke |
|---|---|---|---|---|
| lego | 23638 | 21758 | 2858 | 4 |
