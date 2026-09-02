# Phase 1e — CHEAP go/no-go: discriminator-gated Phase-1b cloud precision check

STATUS: The path-C paper is LOCKED (camera-ready 4856be7). This is an EXPLORATORY probe
BEYOND the locked paper. It MUST NOT alter, recompute, or unfreeze ANY banked paper number.
It writes only NEW files. If it succeeds it becomes an additive appendix; if not, the paper
stands as-is.

## Why this exact shape (three-way reconciliation)
The naive plan was "gate the Phase-1b cloud by the 0.90 DINOv2 discriminator." BLOCKED:
the 0.90 is the MESH-SUPERVISED probe. Phase 1d already froze its mesh-free collapse to
0.6371. Using the in-scene 0.90 as a GATE puts mesh in the method path = violates the
SACRED mesh-never-in-method-path invariant. So:

- The GATE discriminator MUST be mesh-free at the target scene. Use ONE of:
  (i) TRANSFER probe: DINOv2 discriminator FIT on the OTHER scene's mesh labels, applied
      zero-shot to the target (banked transfer AUC ~0.8245 chair<-lego). This is method-legal
      (no target-scene mesh touches the gate).
  (ii) GUARDED operating point (the mesh-free-selected constants already in the paper).
- The in-scene MESH-SUPERVISED 0.90 probe may be reported ONLY as an ORACLE UPPER BOUND,
  clearly labelled, NEVER as a GO trigger.

## The experiment
On the Phase-1b chair 3D cloud (the triangulated DexiNed cloud, recall 0.6753, R_miss 0.6914):
1. Score every 3D candidate point with the mesh-free gate discriminator (transfer probe (i)
   as PRIMARY; also compute guarded-point (ii) if cheap). Also compute the in-scene 0.90
   mesh-probe score PURELY as labelled oracle upper bound.
2. Threshold selection: pick the gate threshold tau on VAL views ONLY. Freeze it. Do NOT
   iterate tau against any measured TEST number. Evaluate TEST exactly ONCE.
3. Metric convention: reproduce the EXACT baseline convention — macro segment-raster P@1.5px
   on TEST views (the 0.657 vanilla-M1b number), NOT point-P. Match recall to baseline's
   recall (report R actually achieved; if the gated cloud cannot reach baseline recall,
   report the unmatched recall HONESTLY — do not silently compare at different recall).
4. TOPOLOGY GUARD (agy's trap): also report a connectivity metric — fraction of baseline
   TEST crease segments that still have >=1 surviving gated point within 1.5px (coverage of
   segments), so a point-P win that SEVERS bridging points and fragments chains is caught.

## FROZEN GO / NO-GO (one-shot on TEST)
GO (justifies the full end-to-end build) requires BOTH:
  (a) mesh-free gate (transfer/guarded, NOT the mesh oracle) gated P@1.5 >= 0.71 at recall
      >= baseline recall (i.e. lift >= +0.05 over 0.657 at matched-or-better recall); AND
  (b) topology guard: segment-coverage does NOT collapse — >= 0.90 of baseline crease
      segments retain a surviving gated point (chains don't fragment).
STRETCH / STRONG-GO: P@1.5 >= 0.78 (agy's +0.12 bar) with (b) held — greenlight full build
      with high confidence.
NO-GO: mesh-free gated P@1.5 < 0.71 at matched recall, OR segment-coverage < 0.90
      (fragmentation), OR recall starvation prevents matching baseline recall at any tau.
      => the discriminator's in-scene AUC does NOT convert to method-legal precision; the
      locked path-C paper is the deliverable, and this probe is reported as an oracle-vs-
      mesh-free gap appendix (0.90 oracle vs <=0.71 mesh-free = the supervision-bound story
      the paper already tells, now quantified at the cloud level).

## Deliverable
Write out/PHASE1E_GATE_CHECK.md with: the frozen tau + which VAL views set it; baseline
recall & P; mesh-free-gated recall & P (transfer AND guarded); oracle-upper-bound P
(labelled); the segment-coverage topology number; and a one-line GO/STRETCH/NO-GO verdict
against the frozen bar above. Do NOT commit until numbers are in and checked. Report every
number from a real result file. This is ONE cheap check — do not build the full pipeline yet.
