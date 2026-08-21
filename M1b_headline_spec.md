# M1b HEADLINE TABLE spec (measurement only — NO renderer yet, NO commit/push)

Both gate ideas are FALSIFIED on held-out data:
- geometry gate: fabric dihedral theta_p95=79deg vs crease theta_p05=5deg (overlap)
- albedo-step gate: AUC(fabric>crease)=0.31 chair, 0.500 lego (chance)

DECISION (driver+agy converged): stop inventing per-pixel gates. Lock the
paper's defensible headline table on HARD-SURFACE scenes; scope chair as a
texture false-positive stress test only. Defer the NPR vector renderer until
this table is in hand.

## TASK: one evaluation script over EXISTING extracted linelets. Produce
`out/m1b_headline_table.json` (+ a small md/png) with THREE blocks:

1. HELD-OUT TEST P/R on hard-surface scenes: lego (primary), and ficus IF you
   judge it hard-surface (else note why excluded). Use the SAME held-out
   train/val/test 80/.../.. view split as before; report on TEST ONLY.
   Report P@1.5, R@1.5, P@2.5, R@2.5 for both segments(linelet) and points,
   gated and ungated side by side.

2. TEMPORAL FLICKER (the WIN): object-space vs image-space, on TEST views, for
   lego (and ficus if included): strict + tolerant flicker %, reduction factor,
   a_temp_px (sub-pixel locus preservation). Reuse the temporal harness that
   produced the chair f240 numbers. Confirm no regression of the ~3.2x tolerant
   / ~8x floor win.

3. CHAIR FP-LINE-DENSITY stress test: on chair, lines-per-kilopixel emitted
   INSIDE GT-verified-FLAT regions (cushion etc). Use mesh GT ONLY to build the
   flat-region mask (EVAL-ONLY; mesh-never-in-method-path invariant intact).
   Report gated vs ungated FP density (gating should lower it even if it can't
   hit P>=0.85).

INVARIANTS: mesh EVAL-ONLY. Held-out TEST only for P/R. Do NOT regress the
temporal win. Do NOT build the vector renderer yet. Do NOT git commit or push —
leave that for an explicit validated-milestone instruction.
