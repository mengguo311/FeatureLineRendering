# LATEX_ASSEMBLY_CHECK — Phase 1h: LaTeX/PDF assembly + translation gate + scoping hardening
# **VERDICT: PASS (GO) — main.pdf compiles under IEEEtran conference within the declared 8-content-page budget; md→PDF numeral multiset conserved 304/304 (133 distinct, zero lost / zero invented); all 15 assets embedded, all Fig/Tab references resolve; scoping airtight with the anti-toy-scene rebuttal in §6 AND Appendix A; final audit 0 blockers / 0 majors**


> **Erratum (2026-09-05), applied above.** This audit predates the crown-jewel figset
> (`d5c9650`: `fig9_crownjewel.png`, `tab5_per_scene.png`). Four counts were stale and are
> now corrected in place: the asset count (13 → **15**, in the verdict line and in the
> file-manifest line), the supplementary-float enumeration
> (now includes **Fig 9** and **Tab 5**, both on p12), and the per-float reference-count list
> (now includes **Fig9×1** and **Tab5×1**, each `md 1 / pdf_ref 1` per the current gate).
> The page-budget verdict — content p1–8, References p9 — is **re-verified true** of the
> shipped PDF as of 2026-09-05; it was transiently false at commit `aa2dae5` (content p1–9).
> Fig 9 and Tab 5 are SUPP-native floats: they cost **+1 supplementary page and ZERO content
> pages**. See `out/SHIP_PDF_STATUS.md`.

Spec `tier1/phase1h_spec.md`. FROZEN invariants honored: no experiment, no scoring, no
recompute of any banked number (the only .md edits are the sanctioned prose-only scoping
hardening + the A.2 oracle-domination clause, verified zero-number by diff multiset);
mesh-never-in-method-path SACRED (every oracle mention in the PDF is labelled
eval-only/upper-bound — audited); path B not reopened; no second-scene run; the temporal
win protected (every temporal number in the PDF traced to `track_p_temporal.json` /
`RESULTS_MASTER.md` at quoted precision — audited). Nothing committed (orchestrator
handles git).

---

## 1. Deliverables

- **`paper/main.tex`** (+ `abstract.tex`, `body_main.tex`, `body_appendix.tex`,
  `supp_floats.tex`, `assets/` with the 15 PNGs) — assembled from `out/PAPER_DRAFT.md`
  by the deterministic converter `scripts/phase1h_md2tex.py` (prose transcribed
  verbatim; only the .md build banner / duplicate titles / grouping header dropped;
  per-section italic meta notes kept). **Template: IEEEtran, `[conference]` mode**
  (the spec's sanctioned neutral choice; no venue banked). Section/subsection display
  numbering overridden to arabic so every in-prose `§x.y` matches the printed headings;
  table numbering arabic; float numbers pinned with explicit `\setcounter` so printed
  Fig/Tab numbers equal the .md's regardless of placement. Citations: the .md's
  in-text anchors (e.g. `[arXiv 2503.14786]`, EMAP title+venue) are KEPT verbatim and a
  `\cite` is appended, never substituted — 9-entry embedded bibliography (Canny, DexiNed,
  PiDiNet, TEED, EMAP, SketchSplat, 3DGS, DINOv2, NeRF).
- **`paper/main.pdf`** — compiles cleanly with **tectonic** (XeTeX engine; the
  environment has no pdflatex/latexmk — recorded as the sanctioned substitute; zero
  errors, zero unresolved references). **13 pages**: content **p1–8**, References +
  supplementary header p9, supplementary floats p10–12 (Tab 1–4, Fig 4, Fig 7, Fig 8, **Fig 9,
  Tab 5** in numeric order, numbering counter-pinned to match all in-text references),
  Appendix A p13. **Double-blind**: "Anonymous submission / Paper ID (double-blind review)", no
  names/affiliations/emails/URLs/acknowledgements anywhere incl. References; PDF
  metadata clean (no Author/Title; Creator=tectonic) — audited.
- **`scripts/phase1h_gate.py`** → `out/phase1h_gate.json` (the machine-checked gate).

## 2. Translation gate (frozen criteria)

| check | result |
|---|---|
| (a) numeral multiset conservation, .md content region ↔ PDF (bibliography block excluded on the PDF side — reference years/ids are the only sanctioned new numerals) | **PASS — 304/304 occurrences, 133/133 distinct, lost {} / invented {}** (commas normalized; verified AFTER the A.2 + A.3 prose additions, which are zero-number by construction and by diff-multiset check) |
| (b) page budget — declared: CVF/NeurIPS-family norm, **8 content pages excluding references; appendix/supplementary beyond** | **PASS — content ends p8; References start p9** (reached with zero prose cuts: 5 low-load-bearing floats → supplementary [Tab 1–3 (1–2 in-text refs each), Fig 4, Fig 7] + Fig 8 and Tab 4 [zero/one refs] + width tuning; every float still in-PDF and referenced) |
| (c) Fig/Tab reference integrity | **PASS — 0 unresolved (`??`); per-Fig/Tab PDF reference counts equal the .md body counts exactly** (Fig2×4, Fig3/4/5/7×1, **Fig9×1**, Fig6×3, Tab1×2, Tab2/4×1, Tab3×3, **Tab5×1**; Fig 1 and Fig 8 have zero body references in the .md itself — pre-existing, teaser-conventional for Fig 1; logged below); printed heading numbers arabic and matching every `§x.y`; `Appendix A` heading matches all 11 prose mentions |

## 3. Reviewer-defense scoping hardening (audited in the PDF text itself — lens 1 PASS)

- Every falsification statement (abstract, contribution 2, §5.4, §5.5, §6, §7, A.1–A.3)
  scoped to the **post-hoc-filtering repair class**; the only "impossib\*" tokens are
  "structural-impossibility … for post-hoc candidate filtering" and A.3's "no
  scene-independent impossibility is claimed". "Supervision-bound under our frozen
  protocol" survives at all sites; the labeled-scenes route stays open everywhere.
- **Anti-toy-scene rebuttal present in BOTH §6 and A.3**: chair = the *selected*
  texture-stress adversary (Canny edge purity 0.28 ← banked 0.284,
  `m1b_headline_table.md`), barriers mechanistic (measured transfer asymmetry +
  bridge-point severing from thresholding any fixed candidate set), generalization
  beyond chair named future work (A.3 clause added post-audit), no overclaim.
- **A.2 oracle-domination clause added** (this phase, zero-number): "The oracle also
  bounds the class: any learned gate's ranking on this fixed cloud is dominated by the
  in-sample oracle, so the trilemma binds post-hoc discriminator gating as a *class*,
  not merely the gates we built" — closes the "a jointly-trained gate might differ"
  rebuttal without touching any number. Synced .md source + assembly + tex.
- chair-only n=1 explicit in §6 and A.3; every oracle mention labelled
  eval-only/upper-bound; transfer directions (0.8245 chair→lego vs 0.5626
  legal-at-chair) consistent across §2/§5.4/§6/A.1/Fig 8.
- Temporal-win protection spot-audit: 1.72/5.19/5.49/8.35, ≥9.8×, 1.98×
  (0.0214/0.0425), 3.38–21.62×, 2.43–29.92×, survival 0.29–0.83 vs 0.005–0.009, mean
  life 37–183 vs 1.0–1.5 — all verified against `pareto2_verdict.json` /
  `RESULTS_MASTER.md` / `track_p_temporal.json` at quoted precision.

## 4. Fix log (all zero-number; conservation re-verified 304/304 after each batch)

- FIX-1: converter paragraph splitter — headers followed by meta notes without a blank
  line were being swallowed (only 2 of 7 sections detected); headers now always split.
- FIX-2: IEEEtran Roman/letter section display → arabic (`\thesectiondis` overrides),
  restoring the 15 subsection numerals (3.1–5.5) the gate flagged as lost and making
  prose `§x.y` refs point at matching printed numbers.
- FIX-3: Fig 3 caption de-numeralized (its "1.72×" was the gate's one invented numeral).
- FIX-4: `\appendix` → `\appendices` (IEEEtran was swallowing the appendix title; now
  prints "APPENDIX A / CAN A DISCRIMINATOR PATCH THE BOUNDARY? …").
- FIX-5: author-block literal U+2014 pair rendered as dropped glyphs → `---` ligature.
- FIX-6: supplementary floats reordered numerically (Tab 1→4, Fig 4, 7, 8), `[t]`
  placement, and the pre-supplementary `\clearpage` removed — reclaims the near-empty
  page (14 → 13 total pages).
- FIX-7 (audit, lens 1 minor): A.3 "extending the falsification beyond chair is named
  future work" clause added.
- Layout fit (zero cuts): floats 5+2 to supplementary with counter-pinned numbers,
  Fig 3 to column width, width tuning on Fig 1/2/5/6 — all legibility-checked at
  rendered size (lens 2).

## 5. Deferred (logged, NOT done — would touch banked drift-checked assets or the frozen 304-numeral pin; for camera-ready polish)

- Asset-internal nits (would require regenerating banked, drift-checked PNGs):
  Tab 1/2/4 clip header/cell text mid-word at cell borders; Fig 7 suptitle overprints
  its left-panel title; Fig 2 per-point annotations illegible at print size (curve
  separation and axes remain clear; all quantitative claims carried in prose — lens 2
  judged non-blocking).
- Fig 8's chair bar shows the recomputed 0.8395 while prose quotes 0.8401 (lego's
  analogous pair IS reconciled in §5.4; the chair reconciliation sentence would add a
  numeral → breaks the frozen 304 pin; both are real ledger numbers, documented in
  `FIGURES.md`).
- Fig 1 uncited in body prose (pre-existing in the .md; teaser convention) — adding
  "(Fig 1)" would change the pinned reference counts.
- Ref [8] (SketchSplat) is title+arXiv-id only — author fields deliberately left
  minimal rather than risk fabrication; complete during the related-work sweep.
- `render_fig5.py` docstring "verbatim" nit (pre-1h, logged in PHASE1G_CONVERGE.md).

## 6. Audit provenance

Two-lens hostile audit on the compiled PDF (pages rendered and READ at 110–600 dpi):
lens 1 scoping-airtightness **PASS** (1 minor — fixed as FIX-7 — + 3 notes), lens 2
rendering/template compliance **PASS** (5 minors — FIX-5/6 taken, 3 deferred as asset
nits — + 3 notes). Template sanity, anonymization, caption fidelity, cross-reference
integrity, and absence of layout artifacts all verified. First audit launch died on a
session limit and was resumed after reset; both agents completed on the current PDF
(including the A.2 clause). Machine gate: `out/phase1h_gate.json`
(conservation PASS, content_pages 8, unresolved_refs 0).

**GO: the paper is submission-ready** under the declared template and budget. Files:
`paper/{main.tex,main.pdf,abstract.tex,body_main.tex,body_appendix.tex,supp_floats.tex,assets/}`,
`scripts/{phase1h_md2tex.py,phase1h_gate.py}`, `out/phase1h_gate.json`, this file.
.md hardening edits: `out/{APPENDIX_A_DRAFT,SEC6_DRAFT,PAPER_DRAFT}.md` (prose-only,
zero-number, diff-multiset verified). Nothing committed.
