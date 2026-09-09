# M1b STEP-06 — forward-warped STROKE temporal residual

Metric: forward-warped stroke temporal residual (discrete Frechet, px) + popping penalty P_pop.  Warp: identical depth-based forward warp for both pipelines.
Held-out: TEST views only; trajectory 5->15.  Stroke variant: `svdexined`.

- **A = OURS**: object-space carrier — DT-pulled linelets chained into static 3D polylines, projected into each frame.
- **B = BASELINE**: naive image-space Canny re-traced independently every frame.

| scene | frames | pipeline | Frechet med | Frechet p90 | Chamfer med | **P_pop** | unmatched | cuts | warp-dropped | strokes/frame | verts/stroke |
|---|---|---|---|---|---|---|---|---|---|---|---|
| cadpartA | 240 | OURS | 0.038 | 0.107 | 0.028 | **0.169** | 0.037 | 0.133 | 0.004 | 2665 | 5.13 |
| cadpartA | 240 | BASE | 1.406 | 2.562 | 0.467 | **0.810** | 0.808 | 0.002 | 0.468 | 421 | 2.84 |

## Headline ratios (BASELINE / OURS — higher means our strokes are steadier)

| scene | frames | Frechet med ratio | P_pop ratio |
|---|---|---|---|
| cadpartA | 240 | 36.72x | 4.78x |

## Stroke graphs

| scene | linelets | after 3D NMS | strokes | median vertices/stroke |
|---|---|---|---|---|
| cadpartA | 220680 | 29673 | 4007 | 4 |
