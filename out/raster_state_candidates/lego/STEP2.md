# Step 2: TRAIN ID anchoring checkpoint

16 TRAIN views; 6.51 s. Each source supplied 9,600 samples. Accepted:
top-k 8,218; SH-0 RGB 4,107; entropy 7,599; margin 8,283;
depth variance 6,082; normal dispersion 7,512. RGB lost 5,084 samples to
the frozen median-layer mass gate. These rejections must not be silently
restored: they expose ambiguity near boundaries, rather than prove RGB is bad.

Median across views of accepted reprojection medians: top-k 0.454 px,
RGB 0.636 px, entropy 0.803 px, margin 0.837 px, variance 0.922 px,
dispersion 0.692 px (400 px image). The pure depth backprojection comparison
is a coordinate roundtrip diagnostic, not a correctness oracle.

Personally inspected `step2/anchor_053.png`: anchors mostly remain near their
evidence pixels; this alone does not establish coherent curves. Both exterior
boundaries and many interior surface responses are present.

Data, rejection reasons and per-view statistics: `step2.json`,
`step2/{real,shifted}_observations.npz`. No DEV/TEST image was read.
The entry file gained the not-yet-executed Step 3 function while Step 2 ran;
the recorded source hash can include that addition. Step 2 logic was unchanged.
