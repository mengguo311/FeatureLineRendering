# Extra model examples — Drums and Ficus

The existing `hybrid_overlay_video.py` is now parameterized with `--scenes drums ficus`, preserving the exact existing thresholds, source channels, brush colors, 12 fps camera arc, and the old Lego/Chair media unchanged. No new fit, manual annotation, mesh, TEST, or third-party Hao–Mukai state-field input. Fixed orange curves come from the earlier automatically fitted I arm (previously NO_GO); dense black lines come from the same camera's vanilla-GS RGB, depth edge and alpha. Both are overlaid on the same GS image. The full sequences are not selected hero frames.

- `drums_arc0_overlay.mp4`, `drums_arc0_comparison.mp4` — 33 distinct sequential frames, 800×800 overlay and 1600×800 RGB/overlay comparison.
- `ficus_arc0_overlay.mp4`, `ficus_arc0_comparison.mp4` — same frame count and resolution.
- `*_frame000.png`, `*_frame016.png`, `*_frame032.png` show unmodified whole frames for the start, middle, and end of each arc.
- `*_manifest.json` records 3D, 2D and combined ink pixels for every frame. `check_video.py` decoded all 8 videos (old and new), with 33 distinct frames each and correct dimensions. Six relevant tests pass.

Visual review: Drums remains identifiable; cymbal/drum rims, stands and pedals acquire many edges, including unwanted squiggles and short orange strokes. Ficus foliage and ribbed pot produce dense ink, but leaf contours crowd together; fixed orange 3D strokes drift in spots and sparse isolated marks appear on the white background. These are honest density-first hybrid demonstrations, not evidence of fixed-curve GO, renderer superiority or validated temporal stability. The earlier Drums/Ficus posterior qualification limitations remain; no held-out TEST was opened.

Repository branch: `hybrid-dense-ink-v1`. Render: `PYTHONPATH=scripts /home/u00134/bin/miniconda3/envs/vfsdgs/bin/python scripts/hybrid_overlay_video.py --output artifacts/hybrid_dense_v1/video --arc 0 --scenes drums ficus`.
