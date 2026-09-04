# SHIP_PDF_STATUS — camera-ready PDF: rebuilt, finalized, budget closed

**VERDICT: SHIP. All four frozen GO/NO-GO criteria hold on the built artifact.**

| frozen criterion | result |
|---|---|
| gate numeral conservation 304/304 PASS | ✅ 304/304, 133/133, lost {} / invented {} |
| 0 unresolved refs | ✅ 0 (`??` count 0 over the whole PDF; 0 `^!` errors, 0 overfull hboxes) |
| red-team threshold paragraph present in body | ✅ verbatim, 180 words, body **p6** (refs start p9) |
| Fig 9 full size | ✅ printed width **bit-identical** to pre-finalize (≈ 7.00 in) |

**Final artifact: 13 pages, References p9, CONTENT PAGES = 8** — the self-declared budget is met.

Path taken: **(a)**, the spec's preferred route — width-shrink Fig 1 / Fig 5 only, all prose kept.

**Two things the orchestrator must weigh before submitting** (details in §0.3 and §7):
1. The compliance has **zero margin** — the measured flip point is **2.13 pt** of float height. Any
   reflow (a venue `.cls`, a different tectonic, one rebuttal sentence) returns the paper to 9.
2. Fig 1's entire in-figure text layer is now **invisible** at print size. A measured, verified,
   **strictly better** alternative exists and is one line away — see §0.4.

Every number here is from a real `pdfinfo` / `pdftotext` / `pdfimages` / gate run. All claims were
re-derived by four independent read-only audits plus an adversarial critic across two rounds; the
audits corrected four of my numbers and found one harness bug, all fixed and recorded below.

---

## 0. What changed in the finalize

Exactly **two numbers** in `paper/body_main.tex`. `git diff` = 1 file, 2 insertions, 2 deletions:

```
- \includegraphics[width=0.7\textwidth]{assets/fig1_teaser.png}
+ \includegraphics[width=0.36\textwidth]{assets/fig1_teaser.png}
- \includegraphics[width=0.7\textwidth]{assets/fig5_survival.png}
+ \includegraphics[width=0.53\textwidth]{assets/fig5_survival.png}
```

**Not one word of prose changed** — an independent word-level diff of the full extracted PDF text
yields 7 opcodes, all pure reorderings of float captions and one section heading: zero prose lost,
zero added. No asset re-rendered (`git diff -- paper/assets` empty). `main.tex`, `abstract.tex`,
`body_appendix.tex` and `supp_floats.tex` untouched.

Printed size of **every** embedded float, pre-finalize (`aa2dae5`) vs finalized — exactly two moved:

| float | before | after | Δ |
|---|---|---|---|
| **Fig 1 teaser** | 5.000 in | **2.571 in** | **−48.6 %** |
| **Fig 5 survival** | 5.003 in | **3.786 in** | **−24.3 %** |
| Fig 2 / Fig 3 / Fig 6 | 3.318 / 3.484 / 4.708 in | identical | same |
| Fig 4 / Fig 7 / Fig 8 | 5.355 / 6.061 / 5.362 in | identical | same |
| **Fig 9 (crown jewel)** | ≈ 7.00 in | ≈ 7.00 in | **same — guardrail 2 held** |
| Tab 1–5 | 5.716 / 4.431 / 3.923 / 4.431 / 5.862 in | identical | same |

All 15 asset PNGs remain embedded (15 image XObjects + 15 alpha smasks), before and after.

*Precision note on Fig 9's width:* `pdfimages` reports integer ppi, giving 7.006 in; a
content-stream extraction gives 6.997 in; deriving `\textwidth` from two independently-scaled
floats (Fig 1 and Fig 5 both yield 7.1429 in) puts 0.98·`\textwidth` at 7.000 in. The true value
sits in a ±0.005 in band around **7.00 in**. The guardrail claim does not depend on this: the value
is **identical before and after**, since `supp_floats.tex` is unchanged.

### 0.1 Why (0.36, 0.53) — and what was ruled out

**88 isolated probe builds** across both rounds (63 this round, 25 previously) swept the Fig 1 /
Fig 5 widths; every probe asserted both guardrails on its own sources before compiling, and
`~/3dgs_line` was never touched by any of them. The feasible region is **sharply discrete and
not monotone** — it is *not* a smooth trade, and making both figures smaller can *cost* a page:

- Both equal: `0.37 → 9`, **`0.36 → 8`**. Yet `(0.37,0.37)` carries 0.44 in *less* total float
  height than `(0.36,0.53)` and still lands on 9.
- Fig 5 small branch: `(0.53,0.32) → 9`, **`(0.52,0.32) → 8`**; `(0.50,0.34) → 8`.
- Fig 1 small branch: `(0.36,0.54) → 9`, **`(0.36,0.53) → 8`**.
- **No point with both figures ≥ 0.44**: `(0.42,0.42)`, `(0.44,0.40)`, `(0.46,0.38)`,
  `(0.48,0.36)`, `(0.40,0.36)`, `(0.38,0.36)` → all 9.
- **Shrinking Fig 1 further does NOT buy Fig 5 back.** An audit proposed that, since Fig 1's text
  is already destroyed at 0.36, driving it to 0.30 would free ~13 pt against ~6 pt spent lifting
  Fig 5 to 0.56. **Measured and refuted** — 10 probes with Fig 5 > 0.53, spanning Fig 1 from 0.28
  to 0.36, *all* land on 9: `(0.28,0.60) (0.30,0.56) (0.30,0.58) (0.30,0.60) (0.32,0.55)
  (0.32,0.56) (0.34,0.54) (0.36,0.54) (0.36,0.56) (0.36,0.60)`. The reasoning was global-area
  arithmetic; the mechanism is **per-page** — Fig 1 sits on the page-2 float slot and Fig 5 on
  page 6, so height freed at Fig 1 cannot relieve the page-8 overflow. **Fig 5 ≤ 0.53 is a hard
  ceiling independent of Fig 1**, which is exactly what makes `(0.36, 0.53)` the right corner.

`(0.36,0.53)` was chosen over its mirror `(0.52,0.32)` because **Fig 5 is a data plot** (axis
labels, tick labels, a 5-entry legend) while **Fig 1 is a pictorial teaser**. At `(0.36,0.40)`
Fig 5 was rendered and inspected and its legend was **illegible**; at 0.53 it is small but readable.

### 0.2 A harness bug, and six results that were void

The first attempt at the Fig 5 > 0.53 sweep silently rebuilt the *already-finalized* configuration
six times and reported six spurious PASSes. Cause: the probe script patched `width=0.7\textwidth`,
but the real sources had already been changed to 0.36/0.53, so its assertion threw — and the shell
script had no `set -e`, so it continued and compiled the unpatched copy. The harness was rewritten
to substitute **any** width via regex and to `set -euo pipefail`, then re-validated by reproducing
two known points (`0.36/0.53 → 8`, `0.36/0.54 → 9`) before the sweep was re-run. **The six void
results are discarded; every figure quoted in this document comes from the fixed harness.**

### 0.3 The honest cost — stated at full strength

Fig 1 is now **2.571 in** wide. Its eight rendered thumbnails remain interpretable, but **the
figure's entire text layer is gone at print size** — not merely the annotation panel: the internal
title bar, all four column labels (`frame 100/240` … `frames 100+101 overlaid (red=t, blue=t+1)`),
both row labels (`OURS — static 3D lines, projected per frame` / `per-frame image-space detection
(Canny)`) and the right-hand annotation block are all at the same scale. Measured ink-band heights
at 600 dpi: **1.32–1.44 pt**, against **9.00 pt** for body text — 15–21 % of body-text scale. The
annotation block carries the paper's headline numbers (1.72–8.35×, ≥5.19× in 3 of 4 conditions,
1.72× as the frozen floor, ≥9.8× vs memoryless detectors).

**Two facts that partly mitigate this, both measured:** the same panel measured **3.72 pt** at the
original 0.70 width — i.e. it was *already* below print legibility before the finalize. The shrink
took it from unreadable to invisible; it did not destroy a functioning artifact. And every number
in it appears in the body prose, so no information is lost from the paper. Fig 5's in-figure text
measures ~2.6 pt (~29 % of body text) — "small but readable" is generous; it is below common
camera-ready minimums, but that was equally true at 0.70.

Also worth recording: at 2.571 in the teaser is **35 % narrower than a single text column**
(3.484 in) yet still occupies a full-width two-column float slot, leaving ~2.3 in of white space
on each side. That is a visible layout defect independent of legibility — and §0.4 fixes it.

### 0.4 A strictly better alternative, measured and ready

Converting **Fig 1 to a single-column float** (`figure` instead of `figure*`, at `\columnwidth`),
leaving Fig 5 at 0.53, was built and fully gated. It **dominates the shipped configuration on
every axis**:

| | shipped (0.36 `figure*`) | Fig 1 single-column |
|---|---|---|
| content pages | 8 | **8** |
| Fig 1 printed width | 2.571 in | **3.487 in (+35.6 %)** |
| Fig 1 page | p2 | **p1 — beside the abstract, where a teaser belongs** |
| dead white space around it | ~2.3 in each side | **none** |
| Fig 5 | 0.53 | 0.53 (unchanged) |
| column-area consumed by Fig 1 | 2.176 col-in | **1.474 col-in (−32 %)** |
| gate | PASS 304/304 | **PASS 304/304, 133/133, 0 unresolved refs, Fig9/Tab5 1/1** |
| Fig 9 | untouched | untouched |
| prose | unchanged | unchanged |

**It was not applied** because the spec defines path (a) as a *width-shrink* of Fig 1 / Fig 5, and
a float-class change is outside that letter; the instruction was to execute the spec exactly. It
touches only Fig 1, honours both guardrails, and needs one line changed in `body_main.tex`:

```
\begin{figure*}[t]...\includegraphics[width=0.36\textwidth]{assets/fig1_teaser.png}...\end{figure*}
→  \begin{figure}[t]...\includegraphics[width=\columnwidth]{assets/fig1_teaser.png}...\end{figure}
```

Recommended, subject to the orchestrator's judgement on moving the teaser to a single column.

### 0.5 Zero margin — a genuine ship risk

Page 8 is filled to the last line in **both** columns (last ink at the standard 1.02 in bottom
margin, measured on a 150 dpi raster). The measured flip point is **2.13 pt** of vertical height on
the Fig 5 axis (`0.53` PASS / `0.54` FAIL) and **2.18 pt** on the Fig 1 axis (`0.36` PASS / `0.37`
FAIL) — under one-fifth of a text line. A venue's own `.cls`, a different tectonic build, one added
rebuttal sentence, or the font substitution the log already reports (`TU/ptm` undefined → `TU/lmr`,
so a venue compiling with real Times will produce different metrics) all return this to 9 content
pages. **"content = 8" should be treated as achieved, not as robust.** More-shrunk configurations
would carry revision headroom; that robustness axis was not swept.

## 1. Toolchain — CORRECTED: it already existed; nothing was installed

**The original ship-blocker was never real.** Commit `d5c9650` states *"SHIP-BLOCKER: no LaTeX on
dss9 (pdflatex/latexmk/xelatex/tectonic absent) → PDF un-rebuildable"*, and
`out/CROWNJEWEL_FIGSET.md` states the `latex` and `tex` envs *"exist but their `bin/` directories
are empty"*. **Both were false when written:**

```
$ ls ~/bin/miniconda3/envs/{latex,tex}/bin | wc -l     -> 50 each, both include `tectonic`
$ stat envs/latex/bin/tectonic   -> Birth: 2026-08-03 13:13:55   (32 days before the rebuild)
$ stat envs/tex/bin/tectonic     -> Birth: 2026-07-28 05:24:31
$ grep 'cmd:' envs/latex/conda-meta/history
    2026-08-03 13:13:56  conda create -n latex -c conda-forge tectonic -y   (+tectonic-0.17.0)
    2026-09-04 23:04:44  conda install -n latex -c conda-forge tectonic -y  (-openssl-3.6.3 / +openssl-3.6.4)
```

Decisive control: the **`tex` env was never touched** and runs `conda run -n tex tectonic
--version` → `Tectonic 0.16.9` right now. The 2026-09-04 `conda install` changed exactly one
package (`openssl`), and `ldd` shows tectonic does not link openssl at all. Note
`out/LATEX_ASSEMBLY_CHECK.md` line 30 already recorded the PDF *"compiles cleanly with tectonic"* —
two banked docs directly contradict each other on this.

**Root cause: a false-negative detection.** tectonic was installed in non-default conda envs and so
absent from `PATH`; a bare `command -v tectonic` reports absent. An `ls .../envs/latex/bin |
head -40` on a 50-entry directory also hides `tectonic`, which sorts last. Probe toolchains with
`conda env list` + per-env `bin/`, never `PATH` alone.

Builds run in the pre-existing **`latex`** env (tectonic 0.17.0), not `vfsdgs` — solving into
`vfsdgs` would risk perturbing the env every banked experiment uses, for no benefit. `vfsdgs`,
`tex` and `base` untouched; `vfsdgs` re-verified working afterwards.

```
cd ~/3dgs_line/tier1/paper && conda run -n latex tectonic -X compile main.tex --keep-logs
```

## 2. The finalized build

| | value |
|---|---|
| pages | **13** |
| errors (`^!` in `main.log`) | **0**; no undefined-reference/citation/rerun warnings |
| Overfull hboxes | **0** |
| Underfull warnings | **11** (10 `\hbox` + 1 `\vbox`) — pre-existing, not regressions |
| font warnings | `TU/ptm/{m,bx}/{n,it}` undefined → `TU/lmr` substituted; `inputenc` ignored under XeTeX — pre-existing |
| unresolved refs (`??`) | **0** over the whole PDF, bibliography included (stricter than the gate, which excises the bib) |
| fonts | 12 faces, all **Type 1C, embedded + subset**; identical faces, subset tags and object IDs before and after |

Anonymization re-checked: zero hits for `u00134`, `3dgs_line`, `mizuho`, `/home/`, `/tmp`, or
Author/Title metadata. Reproducibility: the shipped `main.pdf` extracted text is **byte-identical**
to an independent scratch build from the same two widths.

## 3. Page counts

`pdftotext` split on form-feed, trailing empty block dropped (no interior block is empty, so
"drop trailing" and "count non-blank" agree); headings matched after whitespace-stripping —
**IEEEtran small caps mean a naive `grep References` returns 0; the extracted text is
`R EFERENCES`**, and a case-insensitive substring grep additionally hits the prose word
"references." further down the same page.

| measure | pre-finalize | **finalized** |
|---|---|---|
| total pages | 14 | **13** |
| References heading page | 10 | **9** (first line of the page) |
| **CONTENT pages** | 9 ❌ | **8 ✅** |
| Supplementary heading page | 10 | 9 |
| Supplementary float pages | 11–13 | 10–12 |
| Appendix A page | 14 | 13 |

Cross-checked three ways: `pdfinfo` → 13; `main.log` → *"Output written on main.xdv (13 pages)"*;
the gate's own non-blank-block count → 13.

**On the authority of "8":** self-declared, not venue-imposed. `paper/main.tex` line 1 says
*"IEEEtran conference template (neutral stand-in; no venue banked)"*, and a repo-wide grep finds no
banked venue. Its only source is `out/LATEX_ASSEMBLY_CHECK.md` (b): *"declared: CVF/NeurIPS-family
norm, 8 content pages excluding references"* — a family internally split (**CVF/CVPR 8, NeurIPS
2022+ 9**), while the class in use is `IEEEtran[conference]`, whose norm differs again. The
finalize meets the declared 8, so this is moot for shipping; it stays documented because it is the
fallback if the Fig 1 cost is rejected (spec path (b)).

## 4. Fig 9 / Tab 5 render — and their values are provenance-gated

| check | result |
|---|---|
| Fig 9 caption in PDF text | ✅ p12 |
| `TABLE 5` heading + full caption | ✅ p12 (letterspaced small caps) |
| Fig 9 image embedded | ✅ 2312×765 = `assets/fig9_crownjewel.png`, ≈ 7.00 in printed |
| Tab 5 image embedded | ✅ 2040×390 = `assets/tab5_per_scene.png`, 5.862 in printed |
| both after References | ✅ p12 > p9 — in SUPP, not the main body |
| in-text prose refs | ✅ exactly one `Fig. 9` and one `Tab. 5`, same body sentence (p5) |
| visual render check | ✅ page rasterised and inspected: Fig 9's three panels and Tab 5's chair/lego/ficus-excluded rows all display correctly |
| **values provenance-gated** | ✅ `render_fig9_crownjewel.py` re-run into scratch: **38/38 ledger drift checks OK, 0 mismatches**; regenerated PNGs **md5-identical / 0 max pixel diff** to the shipped assets |

**Fig 9 placement: SUPP — re-measured on the current layout.** The earlier promotion measurement
predated the finalize, so it was re-run: with the post-shrink layout (which freed ~3.06 column-
inches) and Fig 9 promoted into the body at full 0.98 width, the build still yields **9 content
pages**. The SUPP decision therefore stands on a measurement of the *shipped* layout, not an
inference from the old one. A plausible but **false** inference was also tested and refuted:
*"the old PDF was only under budget because it lacked the crown jewel"* — adding Fig 9 + Tab 5 as
SUPP floats costs **+1 total page and ZERO content pages**.

## 5. Gate on the finalized PDF

```
{ "pages_total": 13, "references_start_page": 9, "content_pages": 8,
  "supplementary_page": 9, "appendix_page": 13,
  "md_numerals": 304, "md_distinct": 133, "pdf_numerals": 304, "pdf_distinct": 133,
  "lost": {}, "invented": {}, "unresolved_refs": 0, "conservation": "PASS" }
```

Idempotent: re-running leaves `out/phase1h_gate.json` byte-identical. The numeral logic was also
independently re-implemented from the docstring and reproduced 304/133 on both sides. All 14 floats
report `captioned ≥ 1`; every `md` count equals its `pdf_ref` count.

### 5.1 What 304/304 does NOT certify — read before quoting it

1. **Every table's numbers are invisible to the gate.** Tab 1–5 are `\includegraphics` **rasters**;
   `pdftotext` on the supplementary pages yields captions only. Precision, recall, popping rates,
   Fréchet ratios and the whole frozen-gate ledger live in PNG pixels, outside the multiset check.
   **304/304 certifies the PROSE.** *Countervailing:* Fig 9 / Tab 5 **are** independently gated
   (§4). Tab 1–4 have no such re-verification here.
2. **The gate is invariant to deleting load-bearing prose.** A probe build removing the entire
   180-word red-team paragraph still returns 304/304 PASS. The gate is therefore *not* what
   protects guardrail 1 — direct textual verification is (§6).
3. **The metric was partly preserved by removing numbers from the paper.** `d5c9650` says so:
   *"De-numeralized threshold para (8 numerals) to keep gate PASS"* — values `{30, 213711, 30.000,
   30.05, 47, 0.6408, 0.6360, 0.3004}` now live only in `RESULTS_MASTER` / `LEGO_THRESHOLD_AUDIT`.
4. **Fragility:** `first_page()` returns the first page whose space-stripped text *contains*
   `REFERENCES`, unrestricted to headings, and `content_pages = ref_pg - 1` is never validated.
   Pages 1–2 already contain the word "reference"; only the singular form saves it.

## 6. Guardrail verification (on the built artifact, not just the sources)

**G1 — red-team threshold paragraph intact in the body.** Source: `body_main.tex` lines 329–341,
**byte-identical to HEAD** (the only diff hunks are the two `\includegraphics` widths), 180 words.
Rendered: verified in reading-order text (`pdftotext` *without* `-layout`; with `-layout` the two
columns interleave line-by-line so multi-line sentences cannot match — a trap that produced a
spurious MISSING on the first attempt), de-hyphenated across line breaks. All eight probes match on
**body page 6**, References start p9:

- "Both figures are stated at the crease definition we use throughout" ✅
- "lego is unusually sensitive to that choice, so we report the sensitivity rather than leave it implicit" ✅
- "lego's mesh contains a single large family of edges lying at exactly the threshold angle" ✅
- "nudging the threshold by a twentieth of a degree therefore discards nearly half of lego's crease pixels and raises the measured ceiling materially, after which it plateaus" ✅
- "This is a property of the asset, not of the reconstruction or of the extractor" ✅
- "precision over the identical rasterised segments falls by more than half across the same range, F-score is flat-to-declining, and the joint operating gate is met at no threshold on either scene" ✅
- "chair, which carries no such family, is unaffected" ✅
- "The ceiling conclusion is therefore robust to the threshold even though the individual number is not; the per-threshold values are tabulated in the results ledger" ✅

**G2 — Fig 9 not shrunk.** `supp_floats.tex` unchanged vs `aa2dae5` (`git diff` empty), still
`width=0.98\textwidth`; printed width identical before and after (§0).

**Float adjacency did not break.** Fig 5 caption p6 / cited p5, unchanged. Fig 6 **improved**
(caption p7 → p6, now co-located with two of its three callouts). Fig 9 cited p5 / printed p12
(was p13) — the pre-existing gap narrowed by one. One cosmetic regression: **Fig 3 was cited on its
own caption page (p5/p5) and is now cited p4 with its caption on p5.**

## 7. Invariants

| invariant | status |
|---|---|
| Mesh EVAL-ONLY / no method-path code touched | ✅ `git diff` contains **no** `scripts/` change |
| No banked number altered | ✅ no prose changed anywhere; no banked `out/*.json` or `*RESULTS*.md` changed except the gate's own output |
| No asset re-rendered | ✅ `git diff -- paper/assets` empty |
| No fabricated page count or gate result | ✅ every figure traces to a real invocation on a real build |
| Probe builds isolated | ✅ all **88** probe builds (63 this round + 25 previously) ran in scratch; `~/3dgs_line` untouched by every one |

Repo-level, four tracked files differ from `aa2dae5`: `paper/body_main.tex`, `paper/main.pdf`,
`out/phase1h_gate.json`, and this document. ⚠️ `paper/main.log`, `ship_pdf_spec.md` and
`ship_finalize_spec.md` are untracked and **not** covered by `.gitignore` — stage explicitly,
never `git add -A`.

## 8. Remaining items for the orchestrator

1. **Decide on Fig 1.** Either accept the −48.6 % shrink and its dead text layer (§0.3), adopt the
   strictly-better single-column variant (§0.4, one line, fully gated), or take spec path (b) and
   relabel the budget to 9 by reverting the two width numbers.
2. **Treat "content = 8" as fragile** (§0.5, 2.13 pt margin) when planning rebuttal edits or a
   venue-`.cls` recompile.
3. **`out/CROWNJEWEL_FIGSET.md` still asserts, as banked fact, that there is no LaTeX toolchain and
   that the conda envs' `bin/` directories are empty.** Both false (§1). The spec bundled this fix
   into path (b) only, so taking path (a) leaves it standing — but it is independent of the page
   budget and should be corrected regardless. Its *other* flagged claim, "8-content-page budget
   intact", is **true again** now that content = 8. Commit `d5c9650`'s message repeats the same
   falsehood; immutable history, left as-is, this document is the correction of record.
4. **`out/LATEX_ASSEMBLY_CHECK.md` is NOT fully correct again** — an earlier draft of this document
   said "no edit needed"; that was an incomplete audit conclusion. Its *page-budget* claims are
   restored (content p1–8, References p9), but three defects introduced by `d5c9650` remain:
   (i) the top-line VERDICT still says **"all 13 assets embedded"** when there are now **15**;
   (ii) its supplementary-float enumeration (p10–12) omits **Fig 9 and Tab 5**;
   (iii) its per-float reference-count list omits **Fig 9 ×1 and Tab 5 ×1**, both of which the gate
   now reports as `md 1 / pdf_ref 1`.
5. Pre-existing, reviewer-visible: **Fig 1 and Fig 8 have zero in-text callouts** in both the `.md`
   and the PDF (their `md == pdf_ref` check passes vacuously at 0 == 0). `supp_floats.tex` pins
   every float number with hardcoded `\setcounter`, so inserting or reordering any float silently
   misnumbers everything downstream with no LaTeX warning. And the finalize leaves an incoherent
   size hierarchy that tracks spec scope rather than importance — Fig 6 (4.708 in, untouched
   because the spec fenced it off) is now larger than Fig 5 (3.786 in) and Fig 1 (2.571 in).
