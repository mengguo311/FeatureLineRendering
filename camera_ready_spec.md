# Camera-Ready Integrity Pass (Path C — final, READ-ONLY on all frozen results)

HARD INVARIANTS (violating any = abort and report):
- Do NOT recompute, re-run, or unfreeze ANY experiment. No shells that touch out/*.json result files for regeneration.
- mesh-never-in-method-path stays sacred (mesh only in mesh_oracle.py / EVAL).
- Do NOT alter any headline number. The banked numbers (temporal 1.72-8.35x floor with 0.6371 recall n=2; DexiNed 2D recall ceilings; K_geom~0.5 controls; TRACK_P survival cells) are LOCKED. You may only fix prose/reference drift, never a value.

TASK — produce out/CAMERA_READY_CHECKLIST.md with an explicit PASS/FAIL per item:

1. FIGURE/TABLE COMPLETENESS: enumerate every figure (fig1..fig5) and table (tab1..tab4) asset in out/. For each, confirm (a) the .png exists, (b) it is referenced at least once in PAPER_DRAFT.md, (c) its caption number matches its reference number. List any orphan asset or dangling reference.

2. NUMBER-CONSISTENCY GREP: for each load-bearing number, grep PAPER_DRAFT.md + all SEC*_DRAFT.md + ABSTRACT_INTRO_DRAFT.md and confirm every occurrence carries its qualifier (floor + n=2 where required, TEST-only where required). Report the count of occurrences and any bare/unqualified occurrence. Do NOT change the number itself; if an occurrence is unqualified, flag it and add ONLY the missing qualifier text.

3. SECTION-ASSEMBLY CHECK: confirm PAPER_DRAFT.md contains all of §1-§7 + Abstract in order, no duplicated/missing section, and the contribution box (CONTRIB_BOX.md) content is present and consistent with the abstract's claims.

4. TRACE-CHAIN SPOT CHECK: pick 3 numbers at random from PAPER_DRAFT.md and confirm each traces to a real out/*.json or *_RESULTS.md value at the stated precision. Report the 3 (claim -> source file -> value).

5. Fix ONLY prose/reference drift found above (missing qualifier text, wrong figure number in a \ref, section-order). For every fix, log it in the checklist. If zero fixes needed, say so explicitly.

Then: git add -A, commit with an honest one-line message describing PASS/FAIL summary + any fixes, git push origin m1b-milestone:tier1-research, report push result + HEAD hash. If the pass finds a genuine blocker you cannot fix without recomputing, STOP and report it rather than papering over it.
