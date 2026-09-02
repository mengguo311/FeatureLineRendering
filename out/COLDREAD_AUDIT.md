# COLDREAD_AUDIT — end-to-end hostile cold-read of PAPER_DRAFT.md as ONE artifact

Readers: one fully-cold hostile agent (front-to-back, teleological bait-and-switch as the
primary attack) + the assembling agent's own gate-checklist pass. First-pass verdict
against the frozen gate: **NO-GO** → 26 fixes applied in the SOURCE drafts → re-assembled
→ **GO**. Nothing papered over; three findings rebutted with reasons (bottom).

## The frozen gate, evaluated

| clause | first pass | after fixes |
|---|---|---|
| Title+abstract+intro = diagnostic characterization + isolated temporal finding (no working-tool pitch in §§1–3) | **FAIL** — "We present a… primitive", "What the primitive buys", artifact-noun contribution bullet, "which we ship" | **PASS** — title re-led ("an Isolated Finding … and a Measured Precision Boundary"), "We report a … finding", bullet 1 = finding-noun, ship→release |
| Every 1.72–8.35× mention carries the 0.6371 precision context AND n=2 boundary in-passage | **FAIL** — 4/4 mentions lacked in-passage 0.6371; 3/4 lacked n=2 | **PASS** — all 4 mentions (abstract, intro ¶3, bullet 1, §7) qualified in-passage |
| §5 pivot must not read as unannounced failure | **PASS as filed** — cold reader: "the story never switches… a reviewer who files this attack as written will be pointed at the abstract and lose" | unchanged |

## The bait-and-switch attack — outcome

Blocked in its stated form (boundary is co-equal from the title onward; §4.5 forward-
points to §5). The cold read instead located THREE real cracks elsewhere, all fixed:
- **C1 "floor" laundering** (abstract/§1/§7 "frozen conservative floor" vs §4.3 "breaches
  our frozen 2× floor" — a failed gate rebranded as a designed margin). FIX: every
  headline mention now says the 1.72× cell **breached its pre-registered 2× bar and
  stands as the reported floor**.
- **C2 the early self-demotion** (§2's "any static curve set shares our by-construction
  stability" + "our contribution is the measurement discipline" quietly deflating
  contribution 1). FIX: contribution 1 renamed a *finding* (making §2's sentence aligned,
  not contradictory) and §2 now states the counterpart: the finding quantifies what
  staticness is worth against the strongest dynamic family — a number no static-curve
  paper reports.
- **C3 §4.4 arriving after the headline**. FIX: §4.3's delivery sentence now forward-flags
  the decomposition and the accumulator-drift caveat.

## Findings log (cold reader's numbering) → disposition

| # | finding | fix (in source draft) |
|---|---|---|
| 1 | floor laundering | = C1 above (abstract, §4.3, §7) |
| 2 | "oracle no practical system can exceed" overreach | §4.3: oracle claim scoped to the flow *input*; family hedge repeated in-body |
| 3 | lego absolute precision never stated | §4.3 now discloses shared-point P ranges: chair 0.30–0.59, lego ≈0.63 (from pareto2_verdict.json) |
| 4 | dominance-rule truncation unreported | §4.3: shared counts (9/8/3/5 of 21) + explicit statement that lego's highest-precision baseline configs are excluded by construction |
| 5 | matched density ≠ matched coverage | §4.1 rewritten: names what the protocol does NOT close, cross-refs §5.1 |
| 6 | §5.1 selectivity point 17% sparser than "matched" | §5.1 adds the dominance-consistent point: ours denser AND more precise (0.636 @ 7,942 px vs 0.532 @ 5,973; pareto_chair.json) |
| 7 | §5.2 "≤chance" vs §5.3 "≈0.65 geometric" | §5.3: populations/feature sets reconciled in-passage |
| 8 | 0.9044 vs 0.9046 | §5.4: both explained (Act-3 split vs supervision-study recomputation) — both ledger values, not drift |
| 9 | photometric mesh-free omitted | §5.4 now states the best mesh-free number anywhere: chair photometric 0.7326 (touches the gate on one scene; 0.5637 on the other) — dexprimary_p1d.json |
| 10 | "one-direction-tested" ambiguity | §1: "worked in one of the two directions tested (0.8245 / 0.5626)" |
| 11 | threshold-invariance "where measured" opaque | §1 + §7: "(the chair sweep; not repeated on lego)" |
| 12 | §4.3 statistic unnamed | §4.3: "on the pooled pop-rate P(d>2 px) — the floor-free statistic §4.2 motivates" |
| 13 | §4.5 corroboration scope | §4.5: stroke harnesses = memoryless-only; accumulator never run there; 3rd trajectory not covered vs accumulation |
| 14 | §5.1 categorical "No" vs §6 retreat | §5.1: "Not on the evidence — though the evidence is single-scene"; lego converse promoted out of parentheses |
| 15 | §6 missing four elsewhere-disclosed limits | §6 "Further disclosed limits, collected" bullet added (dev-time tuning, failed 3× gate, no static-curve comparison, lego shared-point P + truncation) |
| 16 | §3.4↔§5.4 reflexive loop unclosed | §3.4 closes it: mesh-less deployment needs mesh-free selection, whose strongest tested form §5.4 bounds; transfer is the tested mitigation |
| 17 | chair recall 0.7908 > coverage 0.7382 inversion | §5.1: segment rasterization interpolates between carriers; binding form of the ceiling is lego's zero-carrier 0.3663 |
| 18 | "adversarial worst cell" post-hoc label | replaced by "stress spline" (T3 was designed a priori as the stress trajectory) / "worst cell" |
| 19 | AUC 0.3964 read as "no signal" (sign-flip ≈0.60) | §5.2: "no geometric channel is *usable*… even sign-flipped they reverse the intended semantics" |
| 20 | Fig 5 unrendered in a "rendered" table; grid-count aside | assets table now carries per-row status; Fig 5 marked NOT yet rendered |
| — | tool-pitch inventory (§3 of the cold read) | abstract/bullet/§5.5/§3.4/§7 reworded (finding/report/release); §3.3's descriptive rendering text retained |

## Rebutted (no change, with reasons)
- **"Temporal metric measures persistence of hallucinated floaters"**: blocked by §5.1's
  selectivity evidence on chair (now dominance-consistent) and by precision matching
  itself — the compared line sets are precision-verified against GT creases at every
  operating point; "hallucinated" structure would depress P@1.5, which is an axis of the
  match. On lego the honest form ("stability-only advantage") is already the draft's own
  statement.
- **Item 4's implication that truncation is illegitimate**: the dominance rule is the
  pre-registered protocol and the only known guard against the fewer-lines confound; the
  cure is disclosure (applied), not post-hoc rule changes.
- **Item 19's sign-flipped 0.6036 as a live cue**: using a below-chance direction requires
  knowing the labels that define the flip — circular without supervision; wording fixed,
  substance stands.

## Residuals carried forward (not fixable by wording; already disclosed)
Single-scene selectivity; no third-party static-curve comparison (frozen evaluation);
accumulator family limited to oracle-flow EMA; Fig 5 to be rendered at camera-ready.
