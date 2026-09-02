# PHASE 1g — path-C paper convergence: Phase 1e/1f integration + Fig5 finalization + whole-paper cold-read
# **VERDICT: PASS — appendix integrated, Fig5 finalized, cold-read clean (0 blockers / 0 majors; 3 minors + 5 notes found and fixed at source)**

Spec `tier1/phase1g_paper_converge.md`. Three-way consensus executed: path B stays a
PERMANENT NO-GO on two independent barriers; the path-C paper converges with Phases 1e/1f
as the pre-emptive reviewer knockout. NO new experiments, NO new scoring, NO GPU, mesh-free
arms untouched, no banked headline number altered (verified programmatically, below).
Nothing committed — per the spec the orchestrator handles git. Working-tree state at
hand-off: 8 modified tracked files + 2 new files (`out/APPENDIX_A_DRAFT.md`, this file)
+ the untracked `phase1g_paper_converge.md` task spec.

---

## 1. What was integrated (all edits source-draft + assembly, mirrored byte-identically)

**New Appendix A — "Can a discriminator patch the boundary? A pre-emptive falsification"**
(`out/APPENDIX_A_DRAFT.md`, inserted in `out/PAPER_DRAFT.md` after §7, before the assets
table; verified verbatim-identical). Disarms the reviewer trap *"why not just train a
lightweight discriminator / chain-pool to filter texture edges?"* with the Phase 1e/1f
ceiling characterization: A.1 mesh-free gating converts nothing (legal transfer gate AUC
0.5626 = chance → precision 0.3189→0.3216; best in-scene mesh-free 0.4458, topology
0.8811); A.2 the **topological trilemma** — even the in-scene mesh oracle (P@1.5 0.7970 at
matched recall) retains only 0.6372 of baseline-covered crease segments, chain pooling
repairs it only to 0.7481 (median 0.7970) at a precision cost landing below the 0.6573
baseline, and the zero-threshold all-chains ceiling is 0.8782 < 0.90; A.3 two independent
barriers ⇒ topology-aware construction + labels, with probe scope disclosed (chair-only
n=1, in-sample oracle bound, point rasterisation).

**Contribution 2 reframed** (Contribution 1 untouched): §1 item 2 is now "a measured
precision boundary, with the obvious repair falsified", carrying the
structural-impossibility result *scoped strictly to the post-hoc-filtering repair class*;
`out/CONTRIB_BOX.md` item 2 synced (long form), and the §1 label corrected from
"(verbatim from the contribution box)" to "(condensed …)" — fixing a pre-existing
inaccuracy. A-ANCHOR discipline preserved everywhere: precision itself stays
"supervision-bound under our frozen protocol", never "impossible"; the labeled-scenes
route stays open, now phrased as "labeled scenes feeding a topology-aware construction,
not a post-hoc filter" (§5.5).

**Body hooks** (each in its SEC source + `PAPER_DRAFT.md`): Abstract — one sentence
("no post-hoc discriminator filter we tested — up to an in-scene mesh oracle — reached
the pipeline's own precision at matched recall without severing crease connectivity");
§1 four-act sentence + contribution 2; §2 — SketchSplat curve-aggregation praise scoped
to *reads* vs *gating* (reconciling it with A.2); §5.4 — deployment-granularity closure
of the transfer route's legal direction; §5.5 — patch taxonomy extended to four and the
"one open door" qualified; §6 — deployment-granularity limitation with the chair-only
n=1 qualifier; §7 — "no tested post-hoc filter … reached" added to the
boundary-forensics paragraph.

**Ledger** (`out/RESULTS_MASTER.md`): new ADDITIVE §4 "Appendix A — post-lock
falsification probes (Phases 1e/1f)" — an 8-row table (ungated / transfer / vote-probe /
raw-vote / oracle-point / oracle-chain-mean / oracle-chain-median / all-chains, each with
TEST P@1.5, R@1.5, topology guard, source file), the frozen probe gates, the trilemma
statement, and probe caveats; sources index extended with the phase1e/1f files. No
pre-existing row or number touched.

## 2. Fig5 finalization — CLOSED

`out/fig5_survival.png` was rendered at paper-lock (`3b869ec`, drift gate 100/0). This
pass re-verified it READ-ONLY: the render inspected visually (6 conditions, 2 panels,
legend/values consistent); `render_fig5.py`'s drift gate replicated in memory against
`out/track_p_temporal.json` → **100 checks / 0 mismatches**; every paper-quoted
Fig5-adjacent range recomputed exact from the json (E_warp 3.38–21.62×; P(life>32)
0.29–0.83 vs 0.005–0.009; mean life 37–183 vs 1.0–1.5 frames); the documented 5-cell
3rd-decimal erratum touches no quoted range. Assets table row unchanged. Residual item:
none (a cosmetic docstring nit in `render_fig5.py` — "verbatim" refers to the
pre-erratum 3-decimal prose table — is logged here and deliberately deferred: read-only
pass).

## 3. Whole-paper cold-read integrity pass — **PASS**

Run as three independent hostile lenses (number-trace, figure/table+reference drift,
end-to-end contradiction read), then a fix round, then re-verification.

**Verified clean:**
- **Number trace**: every number in the diff traces at its quoted precision to
  `phase1e_test_eval.json` / `phase1e_scores_meta.json` / `phase1f_test_eval.json` /
  `dexprimary_p1d.json` / `m1b_chair_gated_test.json` (incl. rounding-boundary cases
  0.991034→0.9910, 0.797015→0.7970, 0.796991→0.7970, 0.4457929→0.4458); the
  RESULTS_MASTER §4 table verified cell-by-cell; frozen bars 0.71/0.78/0.90 and
  recall ≥ 0.5959 match the probe specs; the trilemma checked true for every tested arm
  (all eight gated arms' TEST recall ≥ 0.5959 confirmed).
- **No banked number altered**: automated multiset comparison of numerals in removed-vs-
  added diff lines = zero lost (re-run after the fix round); diff confined to the 8
  intended files; Fig/Tab reference counts identical to HEAD (Fig 1×1 … Tab 4×1, 14
  patterns compared).
- **Invariants**: "impossible" appears only scoped to the post-hoc-filtering repair
  class (all occurrences checked); the supervision-bound sandwich intact; transfer
  directions mutually consistent everywhere (0.8245 = chair-fit→lego, illegal as a chair
  gate; 0.5626 = the legal direction; no sentence implies the route is dead); the mesh
  oracle labelled eval-only/upper-bound at every mention; Appendix A placed exactly once,
  all 11 mentions resolve; SEC*/ABSTRACT/APPENDIX source drafts byte-identical to the
  assembly at every changed passage.

**Fix list (all prose; zero value changes):**
- FIX-1 (§2, minor): SketchSplat curve-aggregation sentence scoped to *reads* vs
  *gating* — removes the §2-vs-A.2 quotable tension.
- FIX-2 (abstract/§7/A.2, minor): universal quantifiers tightened to the evidence —
  "no … filter we tested", "no tested post-hoc filter … reached", "no tested operating
  point", "for every ranking we could construct, up to an in-sample oracle".
- FIX-3 (§6, minor): chair-only n=1 qualifier added where the falsified-repair-class
  claim lives in Limitations.
- FIX-4 (A.2, note): the 0.7970 numeral collision (chain-median guard vs point-oracle
  precision) disambiguated in-passage.
- FIX-5 (Appendix header, note): source parenthetical completed ("plus banked ledger
  numbers quoted unchanged").
- FIX-6/7 (RESULTS_MASTER §4, notes): baseline-convention pointer corrected to the
  banked M1b run; chain attribution corrected to "P1c/P1d chain components (1,692)".
- FIX-8 (§1, note): contribution 2 close restored to the box's "named route forward"
  tone.
- Also logged from the audit, deliberately NOT changed: the 1,673-vs-1,675 topology-guard
  denominator delta between the 1e (CUDA) and 1f (CPU) jsons (0.12 %, disclosed in
  `PHASE1F_CHAIN_GATE.md`, ~60× below the decision margin); the `render_fig5.py`
  docstring nit (§2 above).

## 4. Invariant statement

Path B not reopened; mesh-free arms untouched; mesh-never-in-method-path SACRED (mesh
appears only as eval/oracle, and Appendix A says so at every mention); no experiment run,
no score recomputed, no banked headline number altered or unfrozen. Files changed:
`out/{PAPER_DRAFT,RESULTS_MASTER,CONTRIB_BOX,ABSTRACT_INTRO_DRAFT,SEC2_DRAFT,SEC5_DRAFT,
SEC6_DRAFT,SEC7_DRAFT}.md` (modified) + `out/APPENDIX_A_DRAFT.md`, `out/PHASE1G_CONVERGE.md`
(new). Ready for the orchestrator to commit.
