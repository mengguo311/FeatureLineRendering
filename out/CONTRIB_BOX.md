**Contributions.**
1. **An interior temporal-stability finding for object-space lines on a frozen 3DGS.** Object-space 3D feature lines
   whose rendered strokes flicker **1.72–8.35× less** (popped line-pixels, per condition;
   **≥5.19× in three of four conditions**)
   than even an **oracle-flow temporally-accumulated** 2D edge baseline, and ≥9.8× less
   than standard per-frame detectors — which remain the precision reference this primitive
   trades against, not a baseline we claim to beat in general. This is not stability-by-construction bought with
   sparsity or imprecision: every comparison is at **matched precision AND matched line
   density**, the oracle baseline is handed our exact rigid flow, and the stability is
   threshold-invariant. The measured envelope ships with it: the 1.72× cell breached its
   pre-registered 2× bar and stands as the reported floor, and inside disocclusion regions
   the baseline is locally better — both disclosed. All numbers are on n=2 synthetic
   scenes, at precision bounded by contribution 2.
2. **A diagnostic that locates exactly what the primitive's precision needs.** The
   crease-vs-texture signal the pipeline is missing **exists** — frozen DINOv2 features
   separate it at AUC 0.84/0.90 — and we pin down what unlocks it: with mesh labels it is
   fully readable; under the best mesh-free supervision it collapses to 0.64 through a
   pre-registered gate; a mesh-labeled *other* scene transfers at 0.82. Precision is
   supervision-bound under our frozen protocol — a measured boundary with a named route
   forward, not a dead end.

Every experimental gate in this paper was frozen before its numbers existed and evaluated
on its letter; all outcomes are reported, including the unfavorable ones, with
density-matched chance clouds, spread-matched nulls, and leakage-guarded splits throughout
(the full gate ledger is in §3).
