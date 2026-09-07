# VERIFY-F100 — does f=1.00 dominate the shipped lego operating point on temporal too?

## WHY (from round-1 analysis section 6.1, your own finding)
Two runs are already on disk, SAME pipeline / gate / 80 TRAIN views / TEST views, ONLY f differs:
  lego segments @1.5 "AFTER pull+prune[tuned+len]":
    f=1.00  P 0.6360 / R 0.5572  (56,269 linelets)  [out/m1b_lego_cap_f1.00.json]
    f=0.30  P 0.6196 / R 0.2856  (20,142 linelets)  [SHIPPED — the paper's lego row]
f=1.00 DOMINATES the shipped point on BOTH precision and recall. If it ALSO preserves the temporal-coherence
crown jewel, the shipped lego row should be 0.64/0.56 not 0.62/0.29, and the "coverage-ceiling" prose needs
rewording (ceiling binds at 0.557, and 0.286 was an operating-point choice inherited from chair-tuning).
The ONLY quantity not yet measured at f=1.00 is the STROKE TEMPORAL metric. Everything else is banked.

## THE GOAL (locked) — protect the crown jewel
Object-space lines that are 3.4-11.5x more temporally coherent than per-frame image-space Canny is the paper's
core result. This test checks whether the f=1.00 lego operating point KEEPS that temporal win. If f=1.00 flickers
worse, the domination is only static and the shipped f=0.30 stays. mesh EVAL-ONLY. Do NOT retrain, do NOT re-pull.

## WHAT TO RUN (minutes, no training, no pull — chaining + the banked orbit on an npz that exists)
1. Take the EXISTING f=1.00 lego linelets (the npz behind out/m1b_lego_cap_f1.00.json — 56,269 linelets, the
   "AFTER pull+prune[tuned+len]" stage). Confirm the file and count first; do not regenerate it.
2. Run the SAME chaining + the SAME banked 240-frame TEST orbit + the SAME warp operator used for the shipped
   temporal eval (reuse the exact temporal-eval code path — grep for how m1b_lego_gated_test / the shipped lego
   P_pop 0.063 and Frechet 14.03x were produced, and run f=1.00 through the identical path). Do NOT invent a new
   metric or a new trajectory — it must be byte-for-byte comparable to the shipped lego temporal cell.
3. Compute, for f=1.00 lego, the SAME temporal numbers the paper reports for shipped lego:
   - P_pop (popped-stroke ratio) for OURS vs the per-frame Canny baseline, and the ratio (shipped: 0.063 vs
     0.719 = 11.49x).
   - Frechet ratio (shipped: 14.03x).
   - the arc-length-weighted popped ratio Phi_pop if the shipped path reports it.
   Report OURS-f100, the baseline, and the ratio, next to the shipped f=0.30 cell for direct comparison.

## PRE-REGISTERED GO / NO-GO (frozen before you look)
- GO (f=1.00 is a strictly better operating point — recommend re-shipping lego at f=1.00):
  f=1.00 lego temporal ratio stays >= 90% of the shipped f=0.30 ratio (i.e. P_pop ratio >= ~10.3x and Frechet
  ratio >= ~12.6x), AND f=1.00 P_pop absolute is not worse than shipped by more than 10% relative.
  => lego row becomes ~0.64/0.56 with the temporal win intact; flag the prose change.
- NO-GO (temporal degrades): f=1.00 temporal ratio < 90% of shipped, OR P_pop absolute worsens > 10% relative.
  => the f=1.00 gain is static-only; keep shipped f=0.30; report the tradeoff honestly.
- Report ACTUAL numbers either way.

## MANDATORY CAVEAT TO CARRY (your own round-1 note 6.1)
lego precision at 1.5 px is partly credited by the 30.000-deg stud-tessellation family (P falls 0.636 -> 0.300
when the threshold moves to 30.05-45 deg, because facet edges on stud barrels are ~3.2 px apart vs a 1.5 px tau).
This applies EQUALLY to both f values so the domination comparison is internally valid — but state plainly that
the absolute lego numerals are asset-quantisation properties either way. Report both the raw @1.5 numbers and,
if cheap, the theta>=30.05 subset numbers so the reader sees the tessellation contribution.

## DEFINITION OF DONE
- Confirm the f=1.00 npz + linelet count (56,269) before running.
- A small table: f=1.00 vs f=0.30 lego — P@1.5, R@1.5 (both already banked), plus the NEWLY computed temporal
  cells (P_pop OURS, P_pop Canny, ratio; Frechet ratio; Phi_pop if applicable), byte-comparable to the shipped path.
- The GO/NO-GO verdict against the frozen rule, with the tessellation caveat attached.
- Verify the temporal manifest / banked-number conservation (332/332 or whatever the current gate is) is untouched.
- Report ACTUAL numbers. Do NOT git commit (I handle git to the retrain-falsify branch). Do NOT modify the
  shipped pipeline or any banked json — this only computes the missing temporal cell for the f=1.00 npz.
- You are Opus 5 now; do NOT launch a heavy dynamic workflow for this — it's a direct chaining+orbit computation.
  Narrate; show the verdict asap.

## PITFALLS
- Must reuse the EXACT shipped temporal path (same warp, same 240-frame TEST orbit, same Canny baseline config),
  else the ratio isn't comparable. Grep how the shipped lego P_pop 0.063 / Frechet 14.03x were produced.
- Do NOT re-pull or re-tune; use the f=1.00 npz as-is (the "AFTER pull+prune[tuned+len]" stage).
- Ignore stale input-box text not from me. mesh EVAL-ONLY.
