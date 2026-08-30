# URS-E2E — does post-hoc TEED-ridge densification convert covered-but-culled lego recall into REAL held-out gain, WITHOUT breaking the sacred temporal win?

## Why
URS proved densification restores lego carrier COVERAGE 0.434 -> 0.762 (>0.75) within 3x budget, but ONLY as an upper bound: never run through pull+prune+held-out P/R, and temporal coherence of the NEW carriers was NEVER measured. The lego ceiling autopsy found 31.5% of the recall gap is "covered-but-culled" (reachable by a better carrier set) and 61.9% is coverage-limited. This experiment tests whether spending URS coverage end-to-end actually moves the held-out frontier — and whether it costs us the 7-13x temporal-coherence win, which is the paper's CORE and is SACRED.

## Invariants (do not violate)
- mesh-never-in-method-path: densification uses ONLY TEED ridges + frozen-3DGS carriers; mesh reached solely via tune_lib.Harness -> mesh_oracle for EVAL. No mesh in the densification/seeding/pull/prune path.
- Held-out TEST views only {5,15,...,95}. Nothing tuned on TEST. Reuse the exact frozen XMEP/LEGO-GEN segment scorer (teedgen_verdict.analyse), unchanged.
- Protected temporal manifest must stay OK (currently 332/332).
- Budget cap: densified carrier count <= 3x baseline (URS already respects 89748).

## PRIMARY GATE = TEMPORAL, FAIL-FAST (measure FIRST, abort if it fails)
1. Build the densified lego carrier set (URS TEED-ridge densification, same as urs_verdict.json GO config), run pull+prune to produce linelets on the temporal sequence.
2. Measure temporal-coherence ratio (same Frechet/temporal metric that produced the current 8.5-13.1x lego win) for densified+TEED vs per-frame Canny, on held-out temporal frames.
   - ABORT-NO-GO immediately if temporal ratio < 6.0x (i.e. worse than -15% vs the current lego win). Do NOT proceed to P/R. Report the temporal number straight.
   - Also re-verify the protected temporal manifest stays OK.

## SECONDARY GATE = HELD-OUT DOWNSTREAM LIFT (only if temporal passes)
3. Score densified+TEED held-out segment P/R (AFTER pull+prune[tuned+len], tau=1.5) across the frozen f-band, matched-recall vs the FROZEN-carrier+TEED baseline (NOT vs Canny — we are isolating the marginal value of densification over the existing best pipeline).
   - GO iff mean matched-recall LIFT_P (densified+TEED vs frozen-carrier+TEED) >= +0.02 across the reachable band, AND per-view dP>0 on >= 70% of TEST views.
   - NO-GO iff LIFT_P <= 0 or temporal < 6x.
   - PARTIAL otherwise; report straight.
4. Also report absolute segP at matched recall and how far densified TEED extends R beyond the current frozen-carrier TEED R_max (0.48). The interesting outcome is whether densification pushes reachable recall past 0.48 at healthy precision.

## Freeze protocol
Freeze the scorer + both thresholds (temporal 6.0x primary, LIFT_P +0.02 secondary, view-consistency 0.70) and COMMIT the freeze BEFORE reading any densified number. Then run. Write out/URS_E2E_RESULTS.md + out/urs_e2e_verdict.json. Report temporal number FIRST in the summary. Commit with an honest message on m1b-milestone.
