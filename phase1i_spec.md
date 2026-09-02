# Phase 1i — camera-ready FINAL POLISH (path-C convergence, FROZEN-number)

STATUS: path B permanently closed (1e legal transfer AUC 0.5626=chance; 1f chain 0.8782<0.90). Paper is
submission-ready (Phase 1h PASS). This is the LAST-MILE cosmetic pass ONLY. Both adversarial partners agree:
CONVERGE. No new experiment, no scoring, no recompute, ZERO banked-number change.

## SACRED INVARIANTS (do not violate)
- No experiment / no re-scoring / no recompute of any banked number.
- md->PDF numeral conservation must stay 304/304 (133 distinct). Re-run the conservation gate after edits;
  if it drops, REVERT that edit. Any figure you regenerate must reproduce identical numeric values.
- mesh-never-in-method-path; temporal win untouched.

## TASK: clear ONLY the safe deferred typographic/reference items you logged in Phase 1h. For each, if the fix
## cannot be done WITHOUT touching a pinned number, SKIP it and log it as a known-erratum note instead.
1. Tab1/Tab2/Tab4 in-figure text clipping — fix layout/margins so no cell text is cropped. Values identical.
2. Fig7 suptitle overlap — nudge spacing so title doesn't collide with subplots. Values identical.
3. Fig2 point-annotation font too small for print — bump annotation size for legibility. Values identical.
4. SketchSplat reference author field — correct the bib author list. (bib only, no numbers.)
5. Fig8 chair 0.8395-vs-body-0.8401 discrepancy — DO NOT change either number. Add a one-line reconciliation
   footnote stating both are the same quantity reported at different rounding/precision (introduce NO new
   numeric literal beyond the two that already exist). If a footnote would add/alter any pinned number, SKIP
   and instead log it in an erratum note in LATEX_ASSEMBLY_CHECK.md.

## AFTER EDITS
- Rebuild main.pdf (tectonic/IEEEtran, expect 0 errors, 0 unresolved refs).
- Re-run the md->PDF numeral conservation gate; confirm still 304/304 (133 distinct). If not, revert offending edit.
- Re-run your drift-check on any regenerated figure PNG (identical numeric content).
- Write out/PHASE1I_POLISH.md: per-item DONE/SKIPPED(+reason), conservation result, final page count, PASS/NO-GO.
- Do NOT git commit (orchestrator commits). Leave increment in working tree.

## VERDICT BAR
PASS if: all attempted items fixed OR safely skipped-with-log, PDF compiles clean, conservation still 304/304,
no banked number altered. This is the final convergence step — after this the paper is done.
