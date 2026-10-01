# Dense hybrid ink v1 — automatic still-frame pilot

**Status:** four genuine TRAIN-F still views rendered (Lego and Chair, indices 1 and 41). No manual line annotation. Not a full temporal or held-out-view result. This is a **stylized-video/hybrid output contract**; it does not convert the composite into an editable fixed-3D-only asset.

## Inputs and provenance

- Fixed object-space layer: archived, automatically fitted 128-span I-arm world-space curves, projected and visibility-tested by the earlier direct-curve experiment. This arm had a four-scene `NO_GO`; reusing it does **not** reverse that verdict or create new 3D curves. `fit/native/{index}.npz` provides same-view full GS RGB, alpha and a depth-edge field. `evaluate/arrays/F_{index}_I.npz` provides archived projected fixed-curve ink.
- Image-space layer: fresh per-view Canny on the archived full GS RGB, plus the archived D native-depth edge field and Canny of the same-view alpha. Two RGB Gaussian scales and low thresholds preserve detail. Alpha foreground masks background. Within one pixel of an object-curve ink pixel, the 2D layer yields attribution to 3D to avoid an identical overprint; no global ink cap or texture pruning is used.
- Exact absolute source files and parameters are recorded in the per-view JSON. No mesh, TEST/DEV or C image is read by this run. F views are TRAIN frames for the frozen GS; they are not independent image generalization evidence.

## Outputs

Every `*_layers.jpg` displays full 800px panels left to right: frozen vanilla GS RGB, prior fixed-3D curve projection, newly computed view-dependent 2D ink, automatic union. `*_hybrid.png` is full-resolution 800×800 black-on-white composite. JSON records object/image/composite pixel counts.

| Scene/view | Object ink px | Image ink px | Composite ink px |
|---|---:|---:|---:|
| lego F1 | 4547 | 38876 | 43423 |
| lego F41 | 3499 | 31103 | 34602 |
| chair F1 | 3981 | 46067 | 50048 |
| chair F41 | 5291 | 58608 | 63899 |

These counts are **visible ink pixels**, not precision/recall or a scientific GO. Existing curve ink is sparse and incomplete. The dense layer improves still-frame legibility but also draws textured clutter, repeated contours and occasional weak fragments. The 2D pixels dominate the composite; the image is not evidence that fixed-3D extraction itself improved. No independent human visual review, held-out-view verdict or uncut temporal sequence has yet been produced. The predictive cross-view routing proposed for a later algorithm is **not implemented in v1**; v1 only provides deterministic two-layer composition and layer provenance.

## Reproduce

`PYTHONPATH=scripts /home/u00134/bin/miniconda3/envs/vfsdgs/bin/python -W error -m unittest discover -s tests -p test_hybrid_dense_v1.py -v`

`PYTHONPATH=scripts /home/u00134/bin/miniconda3/envs/vfsdgs/bin/python scripts/hybrid_dense_v1.py --output artifacts/hybrid_dense_v1`
