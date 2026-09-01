# Task: Assemble out/PAPER_DRAFT.md — assembly is a GLOBAL AUDIT, not concatenation

Merge the gate-passed section drafts (ABSTRACT_INTRO_DRAFT, SEC2..SEC7) into one out/PAPER_DRAFT.md in order, with figure/table refs wired to the FIGURES.md assets.

## The assembly GATE = Global Claim-Evidence Reconciliation Audit (frozen)
Section-level gates already passed internal validity. The ONE thing they cannot catch and you MUST: **cross-section number/claim drift** (headline-to-body divergence). A prior fire caught a FALSE headline "5.19-8.35x" that the body floor refutes (true range 1.72-8.35x, 1.72x = adversarial-worst-cell floor). Do not let that class of error survive.

Procedure:
1. Extract EVERY quantitative claim/bound/qualifier that appears in Abstract, Intro, and Conclusion.
2. Verify exact 1:1 fidelity against the body tables + worst-case floors (§4-§7 and RESULTS_MASTER.md). Load-bearing numbers to reconcile everywhere they appear: temporal-coherence range 1.72-8.35x (floor MUST accompany the ceiling every time); precision 0.8401/0.9044 exists -> 0.6371 through 0.72 gate (never cite the high number without the gate drop); K_geom~0 GT-mesh AUC 0.3964; coverage ceiling 0.79 chair / 0.56 lego; disocclusion self-refutation 0.407>0.300.
3. Any headline number that appears WITHOUT its strict lower bound or operational constraint = a FAIL to fix in the source section draft, not paper over in assembly.

## Frozen go/no-go
- GO: PAPER_DRAFT.md assembled; every claim in Abstract/Intro/Conclusion has 1:1 fidelity with body + its floor + qualifier stated at every occurrence; zero cross-section contradictions. Write a short out/ASSEMBLY_AUDIT.md listing each load-bearing number and where it appears (proof of the audit). Then commit.
- NO-GO: if you find ANY drift/contradiction, list them in ASSEMBLY_AUDIT.md, fix the offending section draft, re-run the audit. Report the count of drifts found+fixed honestly.

Never fabricate a number; every value must trace to a result file. Report per-number audit outcomes when done.
