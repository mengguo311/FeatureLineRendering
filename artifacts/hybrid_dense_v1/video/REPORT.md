# Hybrid ink aligned to frozen GS — continuous camera arc 0

Lego and Chair use 33 sequential camera poses from the earlier direct-curve evaluation arc. Every frame loads its **own same-camera** vanilla-GS native RGB/alpha/depth-edge buffer and visible projection of the **same frozen** I-arm world curves; RGB/alpha 2D edges are recomputed for that frame. No reused still, optical-flow animation, screen translation, crop alignment, mesh, retraining, or new user annotation. Orange = fixed 3D curve projection; black = view-dependent RGB/depth/alpha ink. The frame's RGB array is the exact pixel grid used for all layers. The side-by-side movie has unmodified GS RGB at left and the overlay at right.

Deliverables: `lego_arc0_overlay.mp4`, `chair_arc0_overlay.mp4` (800×800); `*_comparison.mp4` (1600×800); first/middle/last full-frame PNGs and per-frame ink counts in `*_manifest.json`.

Encoding: OpenCV `mp4v`, 12 fps, 33/33 frames decoded in both videos per scene, all frames distinct. The `check_video.py` script checks complete decoding, dimensions, and unique frame hashes. It does not certify temporal stability.

Visual inspection of middle frames: dense ink broadly follows Lego vehicle body, bucket, and board; Chair contours track the model, but some fixed orange strokes are offset from the perceived outline and at least one isolated orange pixel appears on white background. RGB texture produces many extra small marks. This is a visible hybrid compositing demo, not a new fixed-curve GO or a scientifically established temporal result. Prior I-arm 3D-only NO_GO remains in force. These interpolation arc cameras and the underlying GS TRAIN scene are not unseen-real-image generalization evidence; TEST remains closed. No independent blinded visual assessment.

Reproduce: `PYTHONPATH=scripts /home/u00134/bin/miniconda3/envs/vfsdgs/bin/python scripts/hybrid_overlay_video.py --output artifacts/hybrid_dense_v1/video --arc 0`. Run `python artifacts/hybrid_dense_v1/video/check_video.py` after rendering.
