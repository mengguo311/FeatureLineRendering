# M1b STEP-06 — forward-warped STROKE temporal residual

Metric: forward-warped stroke temporal residual (discrete Frechet, px) + popping penalty P_pop.  Warp: identical depth-based forward warp for both pipelines.
Held-out: TEST views only; trajectory 0->10.  Stroke variant: `gated`.

- **A = OURS**: object-space carrier — DT-pulled linelets chained into static 3D polylines, projected into each frame.
- **B = BASELINE**: naive image-space Canny re-traced independently every frame.

| scene | frames | pipeline | Frechet med | Frechet p90 | Chamfer med | **P_pop** | unmatched | cuts | warp-dropped | strokes/frame | verts/stroke |
|---|---|---|---|---|---|---|---|---|---|---|---|
| lego | 240 | OURS | 0.104 | 0.474 | 0.062 | **0.082** | 0.043 | 0.039 | 0.001 | 971 | 4.78 |
| lego | 240 | BASE | 1.247 | 2.604 | 0.433 | **0.708** | 0.703 | 0.005 | 0.178 | 602 | 2.26 |

## Headline ratios (BASELINE / OURS — higher means our strokes are steadier)

| scene | frames | Frechet med ratio | P_pop ratio |
|---|---|---|---|
| lego | 240 | 11.96x | 8.64x |

## Stroke graphs

| scene | linelets | after 3D NMS | strokes | median vertices/stroke |
|---|---|---|---|---|
| lego | 25279 | 13998 | 1895 | 4 |
