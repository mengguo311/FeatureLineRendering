# OUTLINE spec — path-C paper skeleton with claim->figure matrix (NO new experiments)

CONTEXT: RESULTS_MASTER.md is the FROZEN canonical ledger (committed, b13666c..353a2e5).
Do NOT run or re-run any experiment. This is a structuring task only. Reconciled three-way
(dss9 agent + agy): agy's sharpest reviewer-kill = the "failed system in denial" read;
counter it by structure, not by new numbers.

TWO TASKS this session, both cheap:

## Task 1 (first, 2 min): fix a stale note in RESULTS_MASTER.md
The ledger currently marks PARETO2_RESULTS.md as [NEEDS-SOURCE] / "never written". That is
STALE — out/PARETO2_RESULTS.md EXISTS (6876B, committed b57f1a1) and its numbers match the
ledger. Remove both stale [NEEDS-SOURCE] PARETO2 markers (the §1.2 oracle-flow bullet and
the closing "Known gap" sentence); replace with a plain source citation to PARETO2_RESULTS.md.
Do NOT touch any number. Verify with: grep -n "NEEDS-SOURCE\|never written" out/RESULTS_MASTER.md
should return only genuinely-unsourced items (ideally none).

## Task 2: write out/OUTLINE.md — the submittable paper skeleton
Structure the paper as: forensic diagnostic (Contribution B) + surgical honest stabilization
primitive (Contribution A). Sections: Abstract / 1 Intro / 2 Related (SketchSplat curve-level
agg, EMAP semantic-blindness) / 3 Method (mesh-never-in-path invariant stated once; object-
space carrier x image-space DT corrector) / 4 The coverage-ceiling characterization (B, the
4-act arc as PRIMARY scientific insight) / 5 Interior stability at matched precision & density
(A, scoped; disocclusion envelope disclosed IN this section) / 6 Limitations (n=2 synthetic,
perfect geom, known poses -> owned as in-vitro geometric characterization, NOT patched) / 7 Conclusion.

For EACH section include a bullet list of the exact claims it makes, each tagged with the
RESULTS_MASTER.md source and its target FIGURE or TABLE id (Fig 1..N, Tab 1..M). Then a
CLAIM->FIGURE/TABLE MATRIX table at the end: one row per headline number in RESULTS_MASTER.md
sections 1-3, columns = [claim | value | source file | fig/tab id]. Also a short FIGURE LIST
(what each Fig/Tab plots, from which json/md — no rendering, just the spec).

## Completeness gate (frozen, self-check before you stop)
OUTLINE.md is COMPLETE iff:
  (a) every headline number in RESULTS_MASTER.md sec 1-3 appears in the matrix mapped to exactly
      one fig/tab id (no orphaned numbers);
  (b) Contribution B is positioned as a PRIMARY contribution, A scoped to "interior stability";
  (c) BOTH self-disclosed failures get explicit fig/tab real-estate: the disocclusion regression
      (0.407 vs 0.300) AND the PARETO-2 1.72x NO-GO lower bound — never buried;
  (d) NO claim in the outline needs a number absent from the ledger.
If any headline number is orphaned or any failed gate is hidden, the outline is INCOMPLETE —
fix before stopping. Do NOT invent numbers; if something needs a number not in the ledger,
mark it [NO-DATA] rather than fabricating.

Do NOT commit — leave the working tree for the orchestrator to review + push next fire.
Report a one-line completeness verdict against the gate above when done.
