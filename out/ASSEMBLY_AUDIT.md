# ASSEMBLY_AUDIT — Global Claim-Evidence Reconciliation (assemble_spec.md gate)

Scope: every quantitative claim in Abstract, Intro, and Conclusion reconciled 1:1 against
the body (§4–§7) and `RESULTS_MASTER.md`; the five named load-bearing numbers additionally
audited at EVERY occurrence across all seven section drafts (grep-verified line by line).

## Verdict: **GO** — after fixing 2 drifts (found 2, fixed 2, re-verified 0 remaining).

## Drifts found & fixed (in the SOURCE drafts, not papered over)

| # | drift | where | fix |
|---|---|---|---|
| D1 | Abstract attached "(two synthetic scenes, **three** trajectories)" to the 1.72–8.35× range, whose four conditions are 2 scenes × **2** trajectories (T1+T3); three trajectories belongs to the stroke-level Track-P results | ABSTRACT_INTRO ¶abstract | corrected to "two scenes × two trajectories, four conditions; a third trajectory appears in the stroke-level results" |
| D2 | §5.3 cites 0.8401/0.9044 with the supervision collapse only in the following subsection, not in-passage | SEC5 §5.3 closing sentence | forward qualifier added: "…though Act 4 shows that reading it out is supervision-bound" |

## Per-number audit (occurrence → floor/qualifier present?)

**A. Temporal range 1.72–8.35× (floor must accompany ceiling, every time)** — 6 sites, all ✓
| where | form |
|---|---|
| Abstract | range + "1.72× as the frozen conservative floor at the adversarial worst cell" ✓ |
| Intro ¶3 | range + "≥5.19× in three of four; the fourth … sets the frozen 1.72× floor" ✓ |
| Intro contribution bullet 1 | range + "(≥5.19× in three of four conditions; 1.72× frozen floor)" ✓ |
| §2 (temporal-coherence ¶) | "failure envelope (disocclusion reversal, 1.72× floor) reported as part of the claim" ✓ |
| §4.3 | all four per-condition values; 1.72× kept as the subsection headline ✓ |
| §7 | range + "5.19× or better in three of four … 1.72× adversarial cell as the frozen conservative floor" ✓ |
| residual check | no occurrence of the refuted "5.19–8.35×"-as-range form anywhere ✓ |

**B. 0.8401/0.9044 never without the 0.6371-through-0.72-gate drop** — 5 sites, all ✓ (post-D2)
| where | form |
|---|---|
| Abstract | "exists … (AUC 0.8401/0.9044) yet collapses to 0.6371 … pre-registered 0.72 gate" ✓ |
| Intro bullet 2 | "signal exists 0.8401/0.9044; mesh-free 0.6371 vs a 0.72 gate" ✓ |
| §5.3→5.4 | high number + in-passage forward qualifier (D2) + full drop in 5.4 (0.6371 / 0.72; lego 0.9046→0.6569) ✓ |
| §6 | "(0.8401/0.9044 with mesh labels) but collapsed to 0.6371 … 0.72 gate (NO-GO)" ✓ |
| §7 | "exists … (0.8401/0.9044) — and collapses … (0.6371 vs a 0.72 bar)" ✓ |

**C. K_geom≈0, GT-mesh AUC 0.3964** — 6 sites (Abstract, §2×2, §5.2, §6, §7), every one in the
"no geometric signal even under the GT mesh" framing; §2's second occurrence explicitly
scopes what transfers (semantic-blindness) vs what does not (our ceiling) ✓

**D. Coverage ceiling 0.7908 / 0.5572** — 3 numeric sites (§5.1 with pool 0.7382/0.6337,
§6 with UNCOVERED 0.3663, §7); Abstract/Intro reference it qualitatively only ("a ceiling
we measure"), no unfloored numeric form ✓

**E. Disocclusion self-refutation 0.407 vs 0.300 (ours worse)** — 2 numeric sites (§4.4, §6),
both in the same sentence as "worse"; Abstract/Intro/§7 carry the qualitative "reverses"
consistently, never a favorable spin ✓

**Cross-checks beyond the five:** ≥9.8× always "vs memoryless … at every shared point"
(Abstract, Intro, §4.2, §7) ✓ · 1.98× always "interior", "at the hardest cell" (§4.4, §6,
§7) ✓ · transfer always "0.8245, one direction" with §5.4/§6 carrying the 0.5626 reverse ✓
· 33.3 % always with the 60 % gate and NO-GO (§4.4, §5-adjacent via §6) ✓ · n=2 stated in
Abstract, §3.4, §6 consistently ✓ · zero occurrences of "impossible"/"unrecoverable"
outside sandwich-rule statements ✓

Every value above traces to `RESULTS_MASTER.md`, which traces each to its result file
(the ledger's own sourcing pass) and was figure-audited by `scripts/render_figs.py` /
`render_fig7_tabs.py` (27 + 9 drift checks, 0 mismatches).
