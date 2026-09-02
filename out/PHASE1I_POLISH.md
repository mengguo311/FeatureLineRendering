# PHASE 1i — camera-ready FINAL POLISH
# **VERDICT: PASS — all five items DONE (none skipped); PDF compiles clean (0 errors, 0 unresolved refs); md→PDF numeral conservation STILL 304/304 (133 distinct, lost {} / invented {}); no banked number altered; final PDF 12 pages (8 content)**

Spec `tier1/phase1i_spec.md`. SACRED invariants honored: no experiment, no re-scoring, no
recompute — every regenerated figure re-ran its own built-in drift gate against the frozen
jsons BEFORE rendering ("drift checks OK"), and the banked source jsons
(`pareto_verdict.json`, `pareto_{chair,lego}.json`, `dexprimary_p1c_{chair,lego}.json`)
are byte-identical to HEAD (sha1 + `git diff` verified, twice: by me and by the
independent audit agent). `pareto_verdict.py` was driven **plot-only** (its `gate()` /
`main()`, which would rewrite the banked `pareto_verdict.json`, were never called).
Mesh-never-in-method-path untouched; temporal win untouched. **Nothing committed**
(orchestrator commits; increment left in working tree).

---

## Per-item log

| item | status | what was done (values identical in every case) |
|---|---|---|
| 1. Tab1/Tab2/Tab4 in-figure text clipping | **DONE** | `render_fig7_tabs.py` layout-only edits (new `figw`/`col_w`/row-scale params): Tab 1 col widths + 11.5in canvas — "E_warp ratio (vs per-frame TEED)" / "Fréchet ratio (vs per-frame Canny)" headers now complete; Tab 2 wider canvas + row-scale 1.6 — the two-line "reading" cell clears its borders; Tab 4 wider canvas + wider disposition column — "claim carried by pop/flicker" complete. Follow-on from the verify audit, also fixed: Tab 3 suptitle edge-clip (wider canvas; cells were already clean). All values read back identical (Tab1 20.44/21.62/6.49/10.38/10.61/3.38 · 4.19/29.92/2.43/14.03 · 8.52/11.35/3.44/11.49; Tab2 2.42/12.8/15.4/12.2, ~0.28 px, p95 1.00; Tab3 0.4110/0.3307/0.3875/0.3964/0.4675/44.52°/44.84°/0.32°/0.1235/0.1211/0.870/0.937; Tab4 2.42/1.72/33.3/0.095/0.6753/0.6371/0.4110) |
| 2. Fig7 suptitle overlap | **DONE** | axes rects lowered + `suptitle(y=0.975)` — title clears both panel titles; bars identical (0.840/0.904/0.820/0.891/0.711/0.660/0.646/0.726) |
| 3. Fig2 annotation font too small | **DONE** (improved; borderline-in-hardcopy logged) | `pareto_verdict.py` plot(): canvas 13×5.4→10.5×4.4, annotations 6→10pt, ticks 12, labels 13, legend 11 → effective print size roughly doubled (audit: "readable on screen or with mild zoom, borderline in hardcopy"; a further bump trades against the two-panel column layout — logged as residual, not a clip/values issue). Operating-point values spot-verified against the banked `pareto_{chair,lego}.json` |
| 4. SketchSplat reference authors | **DONE** | verified against arxiv.org/abs/2503.14786: entry now "H. Ying and M. Zwicker. SketchSplat: 3D edge reconstruction via differentiable multi-view sketch splatting. arXiv preprint arXiv:2503.14786, 2025." (bib only) |
| 5. Fig8 0.8395-vs-0.8401 reconciliation | **DONE** (zero-number footnote) | Fig 8 caption now ends: "The mesh-supervised bars show the ceilings as recomputed in the falsification study; they agree with Act 3's split values quoted in the text to the third decimal." — NO numeric literal introduced (programmatically asserted; gate unchanged). Wording note: the spec suggested "different rounding/precision"; the ledger-accurate relation (`FIGURES.md`) is *recomputed ceiling vs Act-3 split, agreeing to the 3rd decimal*, so the caption states that — neither number changed, neither number added to the text |

## Conservation + build state (frozen bar)

- **Conservation: PASS — 304/304 numerals, 133/133 distinct, lost {} / invented {}**,
  re-run after every edit batch (`out/phase1h_gate.json`; independently re-run by the
  audit agent). No edit needed reverting.
- **Build**: tectonic/IEEEtran, 0 errors, 0 unresolved refs. **Final page count: 12**
  (content p1–8 — budget held; References + supplementary header p9; Tab 1–4 p10;
  Fig 4/7/8 p11; Appendix A p12). A transient reflow to 9 content pages after the Fig 2
  canvas change was caught by the gate and recovered (minipages 0.475→0.465\textwidth)
  before anything was frozen.
- Regenerated PNGs copied to `paper/assets/` (md5-identical to `out/` copies — audited).

## Verification provenance

Two-lens hostile workflow on the rebuilt PDF + regenerated assets: **PASS / PASS,
0 blockers / 0 majors**. Lens 1 visually confirmed all five items on rendered pages;
lens 2 confirmed file hygiene (only sanctioned files modified; zero banked json/md
touched), line-by-line that both render-script diffs are pure layout (no data value,
ledger constant, `check()` call or cellText change), the nine drift constants re-verified
against their jsons, and every regenerated PNG value identical to its banked quote. The
two minors it raised (Tab 2 row height, Tab 3 title edge-clip) were fixed in a final
micro-round and re-gated (still 304/304, content still 8 pages).

## Residual notes (logged, deliberately not chased further)

- Fig 2 annotations remain borderline in hardcopy despite the ~2× improvement (structural
  trade-off of two 2-subplot panels at column width; curve separation, axes and all
  quantitative claims are carried in prose — both audits judged non-blocking).
- Fig 8 caption contains the structural tokens "Act 3"/"Act 4" (section references, not
  metric values; single digits are outside the conservation regex by design).

**This is the final convergence step: path-C paper DONE** — submission-ready PDF, frozen
numbers conserved end-to-end, every deferred typographic item cleared or logged.
Files changed (working tree, for the orchestrator): `scripts/{render_fig7_tabs,
pareto_verdict,phase1h_md2tex}.py` (layout-only), `paper/{main.tex,main.pdf,
body_main.tex,supp_floats.tex,assets/*}`, `out/{tab1..tab4,fig7_semantic,
pareto_chair,pareto_lego}.png`, `out/phase1h_gate.json`, this file.
