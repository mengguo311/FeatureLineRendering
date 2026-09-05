# Camera-ready FINALIZE — resolve the 9-vs-8 content-page gap, honestly

Ship-PDF milestone is committed+pushed (aa2dae5). The PDF rebuilds for real, gate PASS
304/304, Fig9+Tab5 embedded. One open item: content pages = 9 vs the self-declared 8.

Finalize under TWO HARD INTEGRITY GUARDRAILS (non-negotiable):
1. The lego red-team threshold-sensitivity paragraph MUST remain in the body. It is a
   required honest negative disclosure (ceiling is threshold-fragile; the ANY-ranking claim
   must not ship). Do NOT delete or gut it to save a page.
2. The crown-jewel Fig 9 (temporal headline, the paper's crown jewel) must NOT be shrunk.

Subject to those two, close the page gap the honest way, in this preference order:
  (a) PREFERRED: width-shrink Fig 1 / Fig 5 ONLY (they are not the crown jewel) to reach
      content = 8, keeping ALL prose incl. the red-team paragraph and Fig 9 full size.
  (b) If NO remedy hits content=8 while honoring BOTH guardrails, then STOP shrinking.
      Instead RELABEL the budget to 9 content pages: the "8" is self-declared — main.tex
      banks no venue, and the CVF/NeurIPS family is itself split 8-vs-9. Correct the stale
      banked docs: fix CROWNJEWEL_FIGSET.md's two now-false claims ("bin/ empty" and
      "8-content-page budget intact") and add a one-line note in LATEX_ASSEMBLY_CHECK.md.
      (The d5c9650 commit message is immutable history — leave it; SHIP_PDF_STATUS.md
      already records the correction.)

Then rebuild + run the phase1h gate. Stage explicitly (NOT git add -A — main.log and
ship_pdf_spec.md are untracked & not gitignored). 

FROZEN GO/NO-GO — ship only if ALL hold: gate 304/304 PASS, 0 unresolved refs, red-team
paragraph present in body, Fig 9 full size. Report which path (a/b) you took, final pdfinfo
page count + content-page count, and the gate result. Do NOT fabricate any number.
