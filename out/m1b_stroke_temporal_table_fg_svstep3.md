# M1b STEP-06 — forward-warped STROKE temporal residual

Metric: forward-warped stroke temporal residual (discrete Frechet, px) + popping penalty P_pop.  Warp: identical depth-based forward warp for both pipelines.
Held-out: TEST views only; trajectory 5->15.  Stroke variant: `svstep3`.

- **A = OURS**: object-space carrier — DT-pulled linelets chained into static 3D polylines, projected into each frame.
- **B = BASELINE**: naive image-space Canny re-traced independently every frame.

| scene | frames | pipeline | Frechet med | Frechet p90 | Chamfer med | **P_pop** | unmatched | cuts | warp-dropped | strokes/frame | verts/stroke |
|---|---|---|---|---|---|---|---|---|---|---|---|
| cadpartA | 240 | OURS | 0.034 | 0.076 | 0.026 | **0.135** | 0.133 | 0.002 | 0.000 | 31 | 6.40 |
| cadpartA | 240 | BASE | 1.452 | 2.589 | 0.504 | **0.645** | 0.644 | 0.001 | 0.000 | 76 | 2.30 |

## Headline ratios (BASELINE / OURS — higher means our strokes are steadier)

| scene | frames | Frechet med ratio | P_pop ratio |
|---|---|---|---|
| cadpartA | 240 | 42.82x | 4.78x |

## Stroke graphs

| scene | linelets | after 3D NMS | strokes | median vertices/stroke |
|---|---|---|---|---|
| cadpartA | 7208 | 394 | 42 | 5 |
