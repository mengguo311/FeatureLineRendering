# XMEP — Cross-Model Edge-Prior Invariance (chair, held-out TEST)

## Why
The paper's central mechanism claim is: a frozen zero-shot **learned** edge prior buys
RANKABLE seeds that move the precision/recall frontier OUTWARD. So far this rests ENTIRELY
on TEED (BIPED weights). Reviewer-fatal question: is the lift a property of learned edge
priors *in general*, or a TEED-specific artifact? This experiment answers it before we
freeze the paper.

## Task
Reproduce the TEED chair seeding pipeline EXACTLY, swapping only the edge detector for a
second frozen, zero-shot learned detector: **PiDiNet** (table5_pidinet or carv4 pretrained
weights, whichever is already cached / cheapest to fetch; if PiDiNet is impractical to
obtain offline, fall back to **DexiNed** — document which you used and why). Everything
else identical: same seed recipe, same gates, same chair held-out TEST split, same frozen
scorer, same tolerances. NO detector-specific tuning — zero-shot, default threshold family
matching how TEED was run.

## Invariants (hard)
- mesh NEVER in the method path — mesh only in the eval scorer (mesh_oracle). PiDiNet/DexiNed
  import must live in the method/seed path, never the eval.
- Held-out TEST eval only (chair TEST split, same views as the TEED chair run).
- Protect the temporal-coherence manifest — re-verify it still passes (no regression).
- New artifacts only, `xmep_` prefix, do not overwrite any teed_* / urs_* files.
- Freeze the go/no-go threshold in a commit BEFORE computing any lift number.

## Metric & frozen GO / NO-GO
Primary metric = the SAME frontier-outward lift used for TEED on chair (LIFT_P — best
outward move of the f-frontier over the M1a baseline, held-out TEST). Report PiDiNet's
LIFT_P and express it as a FRACTION of TEED's chair LIFT_P (+0.0607).

- **GO (mechanism generalizes):** PiDiNet LIFT_P >= 0.70 * TEED_LIFT_P  (i.e. >= +0.0425),
  AND temporal manifest no-regress, AND gate directions consistent with TEED (dRecall up,
  precision drop modest, frontier moves outward not inward).
- **NO-GO (TEED-specific):** PiDiNet LIFT_P < 0.30 * TEED_LIFT_P (i.e. < +0.0182). This
  downscopes the thesis from "learned-prior seeds generalize" to "TEED-specific alignment"
  — report it straight, it's a real finding either way.
- Middle zone [0.30, 0.70): report as PARTIAL, no spin.

## Deliverables
- scripts/xmep_*.py (seed with PiDiNet/DexiNed), out/xmep_verdict.json, out/xmep_*.json,
  XMEP_RESULTS.md (thorough, honest, include which detector, weights hash, per-arm frontier
  table, temporal re-verify count, the LIFT_P fraction vs TEED, and the GO/NO-GO call).
- Commit the frozen threshold FIRST, then the result, to branch m1b-milestone.

Do NOT re-run or alter the URS or NG-MEC artifacts. This is additive.
