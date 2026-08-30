# CAP — Coverage Attribution Probe (lego)

## Why
ECO closed the ranking question: §1 of ECO_RESULTS.md proved every arm re-ranks ONE
identical candidate pool (n_seeds bit-identical at matched f). Lego's full pool (f=1.0)
yields only R@1.5 = 0.5572, so R>=0.65 is UNREACHABLE by any re-ranking (ECO, veto,
oracle). The binding constraint on lego is POOL COVERAGE, not ranking. Before building
any new method we must attribute WHERE lego's recall ceiling comes from.

## Task (DIAGNOSTIC ONLY — no new method, no new score)
On the lego HELD-OUT TEST split, at the headline stage `AFTER pull+prune[tuned+len]`,
f=1.00 (keep every gaussian). Take the mesh-oracle GT crease set (EVAL-ONLY, mesh_oracle.py).
Define the MISS-SET = GT crease loci NOT matched within tau=1.5 px by any selected seed's
projection, aggregated over the 10 held-out TEST views (use the SAME 2D matching harness
that produces P@1.5/R@1.5 today — do not invent a new metric).

For each missed GT crease locus compute, in the same projected 2D image space per view:
- d_pool = min projected distance to the PRE-SCORING candidate pool (all raw candidate seeds).
- d_raw  = min projected distance to RAW UNPRUNED 3DGS gaussian centers.

Classify each miss:
- Class A (extraction loss): d_pool <= 1.5  (a candidate existed but pull+prune discarded it)
- Class B (representation): d_pool > 1.5, then split by d_raw:
    - B1 (registration-recoverable): 1.5 < d_raw <= 3.0  (a gaussian exists nearby; sub-pixel
      off-registration — the thesis image-space DT corrector's basin)
    - B2 (true void):               d_raw > 3.0  (no gaussian ever placed near this crease)

Report the histogram / mass fractions |A|, |B1|, |B2| over the total miss-set, plus the
raw d_raw and d_pool distributions (median, p90). Also report the same A/B1/B2 split on
CHAIR as a reference (chair pool already reaches R=0.7908, so its miss-set should be
smaller and more B1/A-dominated — a sanity check on the classifier).

## FROZEN GO/NO-GO (decided with adversarial partner agy this fire)
Let rho_B2 = |B2| / (|B1| + |B2|)  (fraction of Class-B mass that is true void).
- rho_B2 < 0.30  -> KEEP the 3D carrier. Next method = coverage-preserving pull+prune
  (relax the aggressive NMS/length prune that discards A, plus DT-pull-relaxation to
  capture B1). The lines ARE in the representation.
- rho_B2 >= 0.30 -> topology critically absent; PIVOT to image-space-primary candidate
  injection (epipolar back-projection of multi-view 2D edge rays synthesizing candidate
  seeds INTO the pool before ranking — the thesis corrector as a candidate SOURCE).

## INVARIANTS (unchanged)
- mesh-never-in-method-path: mesh only via mesh_oracle.py for EVAL. This probe is EVAL/analysis,
  so it MAY read GT, but no new METHOD-PATH file may import mesh.
- Held-out TEST for all reported fractions; VAL only if you need to sanity-check the classifier.
- Do NOT touch the published 332-file manifest; verify sha256sum -c 332/332 after.
- Do NOT rewrite committed artifacts; use a private prefix (e.g. cap_) and always pass --out.
- Only touch u00134 procs; CUDA_VISIBLE_DEVICES=1.
- Do NOT fabricate: every fraction from a real computed array saved to out/cap_*.json.

## Deliverable
out/cap_miss_attribution_{lego,chair}.json + a short out/CAP_RESULTS.md stating |A|/|B1|/|B2|,
rho_B2, and which branch of the frozen gate fires. Do NOT implement the next method yet —
stop after the diagnosis so the go/no-go can be read cleanly.
