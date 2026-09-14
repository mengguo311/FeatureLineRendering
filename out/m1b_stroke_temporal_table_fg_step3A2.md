# M1b STEP-06 — forward-warped STROKE temporal residual

Metric: forward-warped stroke temporal residual (discrete Frechet, px) + popping penalty P_pop.  Warp: identical depth-based forward warp for both pipelines.
Held-out: TEST views only; trajectory 5->15.  Stroke variant: `step3A2`.

- **A = OURS**: object-space carrier — DT-pulled linelets chained into static 3D polylines, projected into each frame.
- **B = BASELINE**: naive image-space Canny re-traced independently every frame.

| scene | frames | pipeline | Frechet med | Frechet p90 | Chamfer med | **P_pop** | unmatched | cuts | warp-dropped | strokes/frame | verts/stroke |
|---|---|---|---|---|---|---|---|---|---|---|---|
| cadpartA | 240 | OURS | 0.034 | 0.088 | 0.026 | **0.169** | 0.169 | 0.000 | 0.000 | 43 | 7.94 |
| cadpartA | 240 | BASE | 1.452 | 2.585 | 0.503 | **0.646** | 0.645 | 0.001 | 0.000 | 76 | 2.30 |

## Headline ratios (BASELINE / OURS — higher means our strokes are steadier)

| scene | frames | Frechet med ratio | P_pop ratio |
|---|---|---|---|
| cadpartA | 240 | 42.55x | 3.82x |

## Stroke graphs

| scene | linelets | after 3D NMS | strokes | median vertices/stroke |
|---|---|---|---|---|
| cadpartA | 11379 | 629 | 46 | 6 |
