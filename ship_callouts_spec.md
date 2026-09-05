# SHIP-POLISH: fix Fig 1 / Fig 8 zero-callout defect (reviewer-visible)

CONTEXT: retrain pivot is KILLED (Exp Y decisive). We are SHIPPING the frozen thesis.
Camera-ready main.pdf is built and gate PASSES 304/304. This is a scoped polish step,
NOT a new direction — no method-path code, mesh EVAL-ONLY, no banked number changed.

SHIP_PDF_STATUS.md §8 item 6 flags a pre-existing reviewer-visible defect:
  "Fig 1 and Fig 8 have zero in-text callouts in both the .md and the PDF — their
   md == pdf_ref check passes vacuously at 0 == 0."

TASK:
1. Add ONE natural in-text \ref callout each for Fig 1 (teaser) and Fig 8, at the
   place in body_main.tex where each figure is first discussed. Do NOT invent new
   claims or numbers — just reference the figure from prose that already discusses
   its content (e.g. "...as shown in Fig.~\ref{fig:teaser}"). If the surrounding
   prose does not already make a factual point the figure supports, do NOT force a
   callout — report that instead and leave it uncalled rather than fabricate.
2. Rebuild main.pdf with the SAME tectonic env used for the last build (env `latex`
   or `tex`; see CROWNJEWEL_FIGSET.md erratum for exact versions/paths).
3. Re-run the phase1h gate. Requirements (FROZEN go/no-go):
   - numeral conservation stays 304/304 (or its current banked count) — PASS
   - 0 unresolved refs, 0 lost/invented numerals
   - Fig 1 / Fig 8 md==pdf_ref now passes NON-vacuously (>=1 == >=1)
   - NO float misnumbering downstream (supp_floats.tex \setcounter is fragile —
     verify every float number is unchanged vs the shipped PDF)
   - page budget still content p1-8, References p9
4. If ANY of the above fails, or adding a callout would require fabricating a claim,
   REVERT the change and report the blocker straight. A clean "cannot add without
   fabrication" is an acceptable, honest outcome.
5. Update SHIP_PDF_STATUS.md §8 item 6 to reflect resolution or the honest blocker.

Report: what callouts added (verbatim), gate result, float-number diff (should be
none), and whether item 6 is RESOLVED or remains open with reason.
