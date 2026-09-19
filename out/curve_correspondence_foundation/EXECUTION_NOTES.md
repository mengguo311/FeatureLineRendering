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
