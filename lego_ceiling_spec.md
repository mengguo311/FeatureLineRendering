# LEGO CEILING AUTOPSY — final lego algorithmic probe (NOT a v3 gateway)

Decision frozen BEFORE running: regardless of the numbers below, do NOT implement any
new aggregation heuristic / v3 multi-cue combo. This produces TWO paper-ablation figures
and then lego precision/recall is documented as a representation bound. The paper stands on
the temporal-coherence win (7-13x), which must remain untouched (do not modify anything on
the protected manifest; re-verify 332/332 at the end).

Rationale (from NG-MEC-v2 NO-GO): lego max recall R=0.408 at keep_frac=1.0 (all proposals
kept). Aggregation only reranks along the ROC; it cannot manufacture proposals. So the
binding question is NOT "can we rerank better" — it is "is the 59% of GT crease that we miss
absent from the proposal set (coverage bound), and does TEED even see lego creases in 2D."

## FIGURE A — TEED pixel-level AUC on lego (autopsy, eval-only)
Measure TEED 2D edge confidence at pixels vs mesh-projected GT crease pixels, held-out TEST
views. CRITICAL confound controls (agy flagged these — do them or the number is worthless):
  - Depth-buffer / z-peel the mesh crease projection so occluded (stud/cavity) creases are
    NOT counted as GT where they aren't visible.
  - Chamfer match at +-1.5px tolerance, calibrated tau, so we measure crease alignment not
    silhouette contrast.
  - Report as ROC-AUC. Compare directly against the known lego CARRIER AUC = 0.550
    (ngmec_v2_cuediag.json) and chair pixel-vs-carrier for reference.
Interpretation (for the figure caption only, no action either way):
  - pixel AUC > 0.75  => "representation disconnect": 2D edges exist, no 3D carrier gaussian
    on the vanilla-3DGS surface -> caption Figure "Representation Disconnect".
  - pixel AUC <= 0.55 => "photometric blur ceiling": even TEED sees no lego crease -> caption
    "Photometric Blur Ceiling".

## FIGURE B — recall-ceiling decomposition (this is the load-bearing one)
At keep_frac=1.0 on lego TEST, decompose why R maxes at 0.408. For each GT crease point,
classify as:
  (1) COVERED-and-ranked: a TEED-proposal carrier gaussian within tau -> recoverable.
  (2) COVERED-but-culled: carrier exists but below keep threshold (only relevant if
      keep_frac<1; at 1.0 should be ~0).
  (3) UNCOVERED: NO carrier gaussian within tau of the GT crease at all -> a proposal/
      coverage bound that NO reranking or aggregation can fix.
Report the fraction in each bucket. HYPOTHESIS to test: category (3) accounts for
~(1 - 0.408) = ~0.59 of GT crease. 
  - GO for the paper's information-bound claim: if UNCOVERED >= 0.45 (i.e. the majority of
    the recall gap is genuine coverage absence, not rankability) -> we can honestly write
    "lego recall is bounded by frozen-3DGS carrier coverage, not by our scoring."
  - Surprising NO-GO (would reopen the question): if UNCOVERED < 0.25 (most misses ARE
    covered-but-mis-ranked) -> flag it loudly; that would mean a better ranker COULD help and
    the ceiling claim is wrong. Report either way, straight.

## Constraints
- mesh only in the eval-only autopsy script (like ngmec_v2_cuediag.py). Method path stays
  mesh-free.
- Held-out TEST for the figures; no tuning.
- New artifacts only, prefix `lego_ceiling_*`. Do not overwrite.
- Do NOT touch the protected temporal manifest; re-verify 332/332 at the end.
- Write out/LEGO_CEILING_AUTOPSY.md with both figures, the confound controls you actually
  applied, and an honest verdict on the coverage-bound hypothesis.
