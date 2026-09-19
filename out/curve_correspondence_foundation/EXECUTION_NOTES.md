# Execution notes

Preregistration ea3e94d was pushed before any scene extraction or matching.
The inherited DEV convention is train-image indices 2/22/42/62, as used by the
corrected runner; it was checked and written correctly before the freeze.
No sub-agents or independent reviewers have been used.

Synthetic development failures are preserved. The mutual-ambiguity fixture first
used arbitrary IDs without specifying their common view pair; adding views=[1,2]
corrected that fixture. The robust triangulation fixture with a high-leverage
outlier in a four-camera endpoint was conservatively rejected by the frozen
all-observation Huber loss; the positive robustness fixture uses five cameras and
one central outlier. No production threshold or robust-loss rule was changed.
The pipeline test exposed duplicate keyword arguments when serializing a rejected
triangulation; the constructor was fixed. Its two-view positive fixture was also
moved to a nondegenerate baseline exceeding the frozen 20-degree criterion.
All original failed GREEN logs remain, along with subsequent passing attempts.

The core refactor review consolidated shared arclength, projection and serialization
helpers without changing frozen science. No unnecessary rearrangement followed the
passing synthetic suite. Every new scientific process uses one BLAS/OpenMP thread.

The first Lego evaluator finished numerical C/DEV/repeatability measurements but
failed while drawing extraction overlays: reference RGB storage was noncontiguous
for OpenCV. Slice11 reproduces the exact layout error on synthetic data; RGB
conversion and drawing now use contiguous buffers. The entire first evaluator
output and trace are preserved under attempts/evaluation_lego_00 and
setup/attempt_00. Only evaluation/media is rerun; no method output or threshold
changes. Numerical metrics are byte-identical across these attempts.
The first access audit already passed native-open checks for this failed display
attempt; execution completion was separately false and is retained.

The complete legacy repository suite contains a test that recompiles
out/point_feature_foundation/setup/composite.so. To preserve the earlier experiment,
setup/repository_suite is an exact source-byte mirror with a private copy of that
binary. All other archived dependencies are read-only links. The full suite runs
with the original repository read-only under Landlock, and temporary fixtures stay
inside this experiment. This is the complete unchanged test suite, not a filtered
subset; source equality and the original binary hash are checked.

The first complete-suite run found wrapper/environment problems: the mirrored
stock renderer was a symlink (violating its existing exact-path assertion), the
legacy ffmpeg environment and Git runtime configuration were outside the wrapper
allowlist, and CUDA initializes thread names through /proc writes. The stock site
was copied byte-for-byte into the mirror, runtime access was completed, and /proc
was allowed for CUDA initialization. Original scientific files remained read-only.
The unchanged complete 127-test suite then passed. Both attempts are retained.

The visibility-stratified diagnostic promised in the preregistration was completed
after the main numerical/media run. Slice12 tests its count/length partition and
empty-denominator handling. It reads only frozen projections and the inherited,
hash-verified seed1729 F/C/DEV contribution layers. It cannot modify the generation,
all-in-frame scores, thresholds or decisions. Supplemental outputs live in
visibility/SCENE with separate native traces and seals.
