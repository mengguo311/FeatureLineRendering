# Phase 1h — LaTeX/PDF assembly + reviewer-defense scoping pass (path-C, gated, NO new experiments)

VERDICT context: Phase 1g cold-read PASSED, committed+pushed (afca8ec). Path B is doubly-closed
(1e legal cross-scene transfer AUC 0.5626=chance; 1f chain-gate all-chains ceiling 0.8782<0.90 &
gated P@1.5 0.6458<baseline 0.6573). We are on path C: converge a submission-ready paper around the
temporal-coherence win (7-13x, held-out TEST) + the rigorous negative-result Appendix A.

FROZEN INVARIANTS (do not violate):
- NO new experiments, NO new scoring, NO GPU, NO recompute of any banked number. Assembly + prose only.
- mesh-never-in-method-path SACRED (mesh appears only as eval/oracle; keep every such label).
- Do NOT reopen path B. Do NOT run a second-scene experiment (lego DexiNed 2D recall ceiling is
  0.385, detector-bound/parked — a lego chain-severing run would be CONFOUNDED by detector recall and
  could not isolate the topology barrier; it would invite a different rebuttal, not disarm one).
- Protect the temporal win; every temporal number must still trace to track_p_temporal.json.

TWO-WAY RECONCILED DESIGN (dss9 synthesis + agy adversarial):
dss9 ranks LaTeX/PDF assembly as the only remaining GATING step (submission target is a PDF; assembly
is the last step producing new failure modes: page budget, anonymization, figure legibility, caption
drift). agy's sharpest threat: a hostile reviewer dismisses Appendix A as "you benchmarked a
pathological chair (n=1), not a method class." We DEFEND against that threat by SCOPING (not by a
confounded second-scene run). So this task = assembly + a defensive scoping hardening pass.

## Deliverables
1. paper/main.tex assembled from the .md drafts (ABSTRACT_INTRO, SEC2, SEC5, SEC6, SEC7, PAPER_DRAFT,
   RESULTS_MASTER, APPENDIX_A_DRAFT, CONTRIB_BOX) into the target conference template (pick a standard
   one — e.g. a two-column CVF/SIGGRAPH-style or the neutral acmart/IEEEtran if no target is banked;
   record which template in the check file). Double-blind anonymized (no author/affiliation/repo URL
   leaking identity).
2. main.pdf that COMPILES cleanly (latexmk/pdflatex+bibtex). All 13 assets embedded, figures legible
   at column width (matplotlib PNG baked-in titles handled; multi-file figures given in-figure numbering).
3. A TRANSLATION GATE, same discipline as 1g, written to out/LATEX_ASSEMBLY_CHECK.md:
   (a) programmatic md->tex->PDF number multiset conservation: every numeral in the extracted PDF text
       traces to PAPER_DRAFT/RESULTS_MASTER, zero loss / zero mutation (same conservation check as 1g);
   (b) page-budget verdict against the template's limit; if OVERFLOW, produce a PRIORITIZED cut list and
       run each cut back through a mini cold-read (no banked number may be cut/altered);
   (c) Fig/Tab numbering + cross-reference integrity verified on the LaTeX side (counts identical to
       the .md HEAD state).
4. REVIEWER-DEFENSE SCOPING HARDENING (agy's threat, folded in — prose only, zero value change):
   audit that the falsification claim is airtight everywhere it appears (abstract, §1 contribution 2,
   §6 Limitations, Appendix A.1/A.2/A.3) as: scoped to the POST-HOC-FILTERING REPAIR CLASS +
   SUPERVISION-BOUND + explicitly chair-only n=1 + we do NOT claim scene-independent impossibility.
   Add one explicit sentence in §6/Appendix A rebutting the "chair is a pathological toy scene" line:
   state that chair was SELECTED as the texture-stress adversarial case (purity 0.28), the barrier is
   mechanistic (supervision gap + topology severing, not chair geometry), and generalization to more
   scenes is named as future work — WITHOUT overclaiming.

## GO / NO-GO (frozen)
GO (PASS): main.pdf compiles under a named template WITHIN page budget AND md->tex number multiset
conserved (zero loss/mutation) AND all 13 assets + all Fig/Tab refs resolve AND the chair-only/
supervision-bound/repair-class scoping is airtight in abstract+§6+Appendix A with the anti-"toy-scene"
rebuttal sentence present. => paper is submission-ready.
NO-GO / PARTIAL: page budget overflows requiring cuts of substantive content, OR any number fails
conservation, OR a figure is illegible at column width. Report it straight in LATEX_ASSEMBLY_CHECK.md
with the specific blocker + prioritized fix list; do NOT paper over it.

Write out/LATEX_ASSEMBLY_CHECK.md with PASS/NO-GO + fix log. Do NOT commit — the orchestrator handles git.
