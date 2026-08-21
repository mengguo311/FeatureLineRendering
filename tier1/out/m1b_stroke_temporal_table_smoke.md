# M1b STEP-06 — forward-warped STROKE temporal residual

Metric: forward-warped stroke temporal residual (discrete Frechet, px) + popping penalty P_pop.  Warp: identical depth-based forward warp for both pipelines.
Held-out: TEST views only; trajectory 5->15.  Stroke variant: `ungated`.

- **A = OURS**: object-space carrier — DT-pulled linelets chained into static 3D polylines, projected into each frame.
- **B = BASELINE**: naive image-space Canny re-traced independently every frame.

| scene | frames | pipeline | Frechet med | Frechet p90 | Chamfer med | **P_pop** | unmatched | cuts | strokes/frame |
|---|---|---|---|---|---|---|---|---|---|
| lego | 8 | OURS | 1.571 | 2.616 | 0.762 | **0.620** | 0.615 | 0.005 | 329 |
| lego | 8 | BASE | 1.935 | 2.813 | 0.832 | **0.950** | 0.949 | 0.001 | 410 |

## Headline ratios (BASELINE / OURS — higher means our strokes are steadier)

| scene | frames | Frechet med ratio | P_pop ratio |
|---|---|---|---|
| lego | 8 | 1.23x | 1.53x |

## Stroke graphs

| scene | linelets | after 3D NMS | strokes | median vertices/stroke |
|---|---|---|---|---|
| lego | 25870 | 14302 | 805 | 3 |
