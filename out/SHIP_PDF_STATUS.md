# SHIP_PDF_STATUS — camera-ready PDF: rebuilt, finalized, Fig 1 approved

**VERDICT: SHIP. All frozen guardrails hold on the built artifact.**

| frozen criterion | result |
|---|---|
| gate numeral conservation 304/304 PASS | ✅ 304/304, 133/133, lost {} / invented {} |
| `content_pages == 8` | ✅ |
| `references_start_page == 9` | ✅ |
| 0 unresolved refs | ✅ 0 over the whole PDF (bibliography included) |
| red-team threshold paragraph present in body | ✅ verbatim & ungutted, body **p6** (§6) |
| Fig 9 full size | ✅ `width=0.98\textwidth`, printed 7.006 in, **unchanged**; `supp_floats.tex` untouched |
| Fig 1 single-column | ✅ `\columnwidth`, printed **3.487 in**, on **p1** |

**Final artifact: 13 pages, References p9, CONTENT PAGES = 8.** `md5 963059db94806106c7949c4b960f5bae`

Shipped configuration: **Fig 1 as a single-column float at `\columnwidth`; Fig 5 at 0.53\textwidth.**
This supersedes the interim path-(a) config (Fig 1 as a 0.36\textwidth `figure*`), which is
retained below only as the measurement baseline it now improves on.

**The single-column change also fixed the zero-margin problem** — see §0.5. Compliance is no
longer balanced on a 2.13 pt cliff.

Every number here is from a real `pdfinfo` / `pdftotext` / `pdfimages` / gate run. All claims were
re-derived by independent read-only audits plus adversarial critics across three rounds; those
audits corrected several of my numbers and found one harness bug, all fixed and recorded below.

---

## 0. What changed

The camera-ready was closed in two approved steps, both touching only Fig 1 / Fig 5 presentation:

**Step 1 — path (a) width-shrink** (`ship_finalize_spec.md`): Fig 1 `0.70 → 0.36\textwidth`,
Fig 5 `0.70 → 0.53\textwidth`. Closed the 9→8 content-page gap.

**Step 2 — approved Fig 1 upgrade** (`ship_fig1_approve_spec.md`): Fig 1 converted from a
two-column `figure*` at `0.36\textwidth` to a **single-column `figure` at `\columnwidth`**.
Exactly one line changed; Fig 5 left at 0.53 as instructed:

```
- \begin{figure*}[t]...\includegraphics[width=0.36\textwidth]{assets/fig1_teaser.png}...\end{figure*}
+ \begin{figure}[t]...\includegraphics[width=\columnwidth]{assets/fig1_teaser.png}...\end{figure}
```

**Not one word of prose changed** across either step. An independent word-level diff of the
extracted PDF text confirms the token stream is preserved (similarity 0.986; per-page multisets
identical on pages 9–13). Prose *did* reflow across page boundaries — ~4.2 % of words changed page
as Fig 1 vacated the page-2 float slot — but no word was added, removed or altered. No asset re-rendered
(`git diff -- paper/assets` empty). `main.tex`, `abstract.tex`, `body_appendix.tex` and
`supp_floats.tex` untouched throughout.

Printed size of **every** float, original (`aa2dae5`) → step 1 → **shipped**:

| float | original | after step 1 | **shipped** |
|---|---|---|---|
| **Fig 1 teaser** | 5.00 in, `figure*`, p2 | 2.571 in, `figure*`, p2 | **3.487 in, single-col, p1** |
| **Fig 5 survival** | 5.00 in | 3.786 in | 3.786 in (unchanged) |
| Fig 2 / Fig 3 / Fig 6 | 3.318 / 3.484 / 4.708 in | identical | identical |
| Fig 4 / Fig 7 / Fig 8 | 5.355 / 6.061 / 5.362 in | identical | identical |
| **Fig 9 (crown jewel)** | 7.006 in | 7.006 in | **7.006 in — guardrail 2 held** |
| Tab 1–5 | 5.716 / 4.431 / 3.923 / 4.431 / 5.862 in | identical | identical |

A float-by-float diff of the shipped PDF against the step-1 PDF reports exactly one size change:
`Fig1 2.571 → 3.487 in`. All 15 asset PNGs remain embedded (15 image XObjects + 15 alpha smasks).

*Precision note on Fig 9's width:* `pdfimages` reports integer ppi, giving 7.006 in; a
content-stream extraction gives 6.997 in; deriving `\textwidth` from two independently-scaled
floats puts 0.98·`\textwidth` at 7.000 in. The true value sits in a ±0.005 in band around
**7.00 in**. The same ±0.008 in method drift is why Fig 1 and Fig 5 are quoted at a common 5.00 in
above rather than the 5.000/5.003 that integer-ppi readout suggests — both were `0.70\textwidth`,
so their original printed widths were necessarily *identical* (content-stream value 4.998 in). The guardrail does not depend on this — the value is *identical* before and after,
and `supp_floats.tex` is unmodified.

### 0.1 How step 1 landed on Fig 5 = 0.53 — and what was ruled out

*(Record of the step-1 width sweep. Fig 5 is still shipped at 0.53; Fig 1's value here has since
been superseded by the single-column float, which also lifted the Fig 5 ceiling — see §0.5.)*

**97 isolated probe builds** across three rounds (25 + 63 + 9) swept the Fig 1 /
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
  ceiling independent of Fig 1's *width*, so long as Fig 1 stays a two-column `figure*`** — which
  is exactly what made `(0.36, 0.53)` the right corner for step 1. That ceiling is **not** absolute:
  changing Fig 1's float *class* rather than its width lifts it to 0.59 (§0.5). The sweep varied one
  dimension; the second dimension was where the slack actually was.

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

### 0.3 The Fig 1 cost, restated for the shipped config

Fig 1 is now **3.487 in** wide: **+35.6 % vs the step-1 config it replaces**, but still
**−30.3 % vs the original 5.000 in** two-column teaser. Its in-figure text scales with it, so the
honest position is:

| Fig 1 config | printed width | annotation ink band | vs 9.00 pt body text |
|---|---|---|---|
| original, 0.70 `figure*` | 5.000 in | ~3.7 pt | 41 % — already sub-legible in print |
| step 1, 0.36 `figure*` | 2.571 in | ~1.3–1.9 pt | 15–21 % — invisible |
| **shipped, single-column** | **3.487 in** | **~1.8–2.6 pt** | **20–29 % — improved, still below print-legible** |

So: the upgrade is a real and substantial improvement over the config it replaces, but it does
**not** restore print legibility to Fig 1's internal text — the title bar, four column labels, two
row labels and the annotation block remain too small to read at 1×. Two facts bound how much this
matters, both measured: that text was **already sub-legible at the original full width** (~3.7 pt),
so nothing functioning was destroyed at any step; and every number it carries (1.72–8.35×, ≥5.19×
in 3 of 4 conditions, 1.72× as the frozen floor, ≥9.8× vs memoryless detectors) appears in the body
prose, so no information is lost from the paper. Rendered at magnification the glyphs are intact —
this is purely a question of print scale, not of rendering.

**What the upgrade does fix outright** is the layout defect: at 2.571 in the teaser was 35 %
narrower than a single text column yet still occupied a full-width two-column float slot, stranded
with ~2.3 in of white space on each side, on page 2. It is now a properly-sized single-column float
**on page 1, beside the abstract**, where a teaser belongs, consuming **1.474 col-in instead of
2.176 (−32 %)**.

### 0.4 Why the single-column variant was adopted

It dominates the step-1 configuration on every measured axis, at equal page count:

| | step 1 (0.36 `figure*`) | **shipped (single-column)** |
|---|---|---|
| content pages | 8 | **8** |
| Fig 1 printed width | 2.571 in | **3.487 in (+35.6 %)** |
| Fig 1 page | p2 | **p1 — beside the abstract** |
| dead white space around it | ~2.3 in each side | **none** |
| column-area consumed | 2.176 col-in | **1.474 col-in (−32 %)** |
| Fig 5 | 0.53 | 0.53 (unchanged, per spec) |
| Fig 5 headroom before overflow | **0.53 — none** | **0.59 ceiling (§0.5)** |
| gate | PASS 304/304 | **PASS 304/304, 133/133, 0 unresolved refs** |
| Fig 9 | untouched | untouched |
| prose | unchanged | unchanged |

### 0.5 Margin — the zero-margin risk is now RESOLVED

The step-1 config met the budget with **no margin at all**: Fig 5 passed at 0.53 and failed at
0.54, a flip point of **2.13 pt** of float height — under one-fifth of a text line. Any reflow
would have returned the paper to 9 content pages.

**Re-measured under the shipped single-column config, the Fig 5 ceiling moves 0.53 → 0.59:**

```
Fig1 = single-column, Fig5 = 0.53 / 0.54 / 0.56 / 0.57 / 0.58 / 0.59  -> content 8  PASS
Fig1 = single-column, Fig5 = 0.60 / 0.66 / 0.70                        -> content 9  fail
```

Shipping at 0.53 therefore leaves **0.06 `\textwidth` = 0.429 in of Fig 5 width = ≈12.8 pt of
float height** in hand — about **6× the step-1 margin**. Freeing Fig 1's second column bought
genuine slack, not just a bigger teaser. The budget should still be re-checked after any prose
edit or a venue-`.cls` recompile (the build substitutes fonts: `TU/ptm` undefined → `TU/lmr`, so a
venue compiling with real Times will produce different metrics), but this is no longer a knife-edge.

*Unused option, measured and available:* Fig 5 could be enlarged to as much as 0.59 (4.21 in,
+11 % over shipped) while keeping content = 8. It was left at 0.53 because the approval spec said
to change only Fig 1.

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
| Underfull warnings | **12** (10 `\hbox` + 2 `\vbox`) — pre-existing class of warning, not regressions |
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
   red-team threshold paragraph still returns 304/304 PASS. The gate is therefore *not* what
   protects guardrail 1 — direct textual verification is (§6).
3. **The metric was partly preserved by removing numbers from the paper.** `d5c9650` says so:
   *"De-numeralized threshold para (8 numerals) to keep gate PASS"* — values `{30, 213711, 30.000,
   30.05, 47, 0.6408, 0.6360, 0.3004}` now live only in `RESULTS_MASTER` / `LEGO_THRESHOLD_AUDIT`.
4. **Fragility:** `first_page()` returns the first page whose space-stripped text *contains*
   `REFERENCES`, unrestricted to headings, and `content_pages = ref_pg - 1` is never validated.
   Pages 1–2 already contain the word "reference"; only the singular form saves it.

## 6. Guardrail verification (on the built artifact, not just the sources)

**G1 — red-team threshold paragraph intact in the body.** Source: `body_main.tex` lines 329–341,
**byte-identical to `7fb5976`** — this step's whole diff to `body_main.tex` is *one* hunk, the Fig 1
float line (the Fig 5 width was already at 0.53 in `7fb5976`; the "two width hunks" figure belongs to
step 1, measured against `aa2dae5`). The block is 191 words as delimited by blank lines; the
threshold-sensitivity argument proper — "Both figures are stated…" through "…tabulated in the results
ledger." — is 178 of them, the remainder being one trailing sentence on a different topic that shares
the block. Earlier drafts of this document rounded that to "180 words"; the exact counts are given
here instead.
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

**G2 — Fig 9 not shrunk.** `supp_floats.tex` unchanged (`git diff` empty), still
`width=0.98\textwidth`; printed width 7.006 in, identical across every step (§0).

**Fig 1 single-column, as approved.** `\begin{figure}[t]` … `width=\columnwidth` …
`\end{figure}`; printed **3.487 in on page 1**. A float-by-float printed-size diff against the
step-1 PDF reports exactly one change — `Fig1 2.571 → 3.487 in` — and 15 images before and after.

**Float adjacency did not break.** Measured against the correct baseline for *this* step (the
step-1 PDF, `7fb5976`), the single-column change moved **exactly one caption: Fig 1, p2 → p1.**
Everything else is identical across the two builds:

| float | step-1 caption / cited | shipped caption / cited |
|---|---|---|
| Fig 1 | p2 / — | **p1** / — |
| Fig 2 | p5 / p4, p6 | p5 / p4, p6 |
| Fig 3 | p5 / p4 | p5 / p4 |
| Fig 5 | p6 / p5 | p6 / p5 |
| Fig 6 | p6 / p5, p6, p7 | p6 / p5, p6, p7 |
| Fig 9 | p12 / p5 | p12 / p5 |

*Correction to an earlier draft:* three adjacency changes previously reported here — Fig 6's caption
moving p7 → p6, Fig 9's p13 → p12, and Fig 3's citation splitting from p5/p5 to p4/p5 — are all
**step-1** effects relative to `aa2dae5`. They were already true before this step and are wrongly
attributed if credited to the single-column change. Fig 1 moving to p1 is the only adjacency change
this step caused, and it is an improvement: the teaser now sits on the first page.

## 7. Invariants

| invariant | status |
|---|---|
| Mesh EVAL-ONLY / no method-path code touched | ✅ `git diff` contains **no** `scripts/` change |
| No banked number altered | ✅ no prose changed anywhere; no banked `out/*.json` or `*RESULTS*.md` changed except the gate's own output |
| No asset re-rendered | ✅ `git diff -- paper/assets` empty |
| No fabricated page count or gate result | ✅ every figure traces to a real invocation on a real build |
| Probe builds isolated | ✅ all **97** probe builds across three rounds ran in scratch; `~/3dgs_line` untouched by every one |

Repo-level, this step changes five tracked files vs `7fb5976`: `paper/body_main.tex` (one line),
`paper/main.pdf`, `out/CROWNJEWEL_FIGSET.md`, `out/LATEX_ASSEMBLY_CHECK.md`, and this document.
`out/phase1h_gate.json` is **byte-identical** — the single-column change alters no value the gate
reports. ⚠️ `paper/main.log`, `ship_pdf_spec.md`, `ship_finalize_spec.md` and
`ship_fig1_approve_spec.md` are untracked and **not** covered by `.gitignore` — stage explicitly,
never `git add -A`.

## 8. Status of the previously-flagged items

1. **Fig 1 — RESOLVED.** The single-column variant was approved and applied (§0.4). Its residual
   cost (in-figure text still below print-legible) is documented at full strength in §0.3.
2. **Zero margin — RESOLVED.** The Fig 5 ceiling moved 0.53 → 0.59; shipping at 0.53 leaves
   ≈12.8 pt of float height in hand, ~6× the step-1 margin (§0.5).
3. **`out/CROWNJEWEL_FIGSET.md` — FIXED.** Its false claim that there is "no LaTeX toolchain on
   this machine" and that the `latex`/`tex` conda `bin/` directories are empty now carries a dated
   **ERRATUM** recording the truth (tectonic 0.17.0 in env `latex` since 2026-08-03, 0.16.9 in env
   `tex` since 2026-07-28; both `bin/` hold 50 entries including `tectonic`), the root cause
   (`PATH`-only probe → false negative), and the note that the de-numeralization it describes was
   undertaken under a mistaken belief. The original text is preserved beneath the erratum so the
   milestone record stays auditable. Its other flagged claim, "8-content-page budget intact", is
   **true again** now that content = 8.
4. **`out/LATEX_ASSEMBLY_CHECK.md` — FIXED.** All three stale counts corrected in place, with a
   dated erratum explaining the change: asset count **13 → 15**; the supplementary-float
   enumeration now includes **Fig 9 and Tab 5** (both p12); the per-float reference-count list now
   includes **Fig9×1 and Tab5×1** (each `md 1 / pdf_ref 1` per the current gate). Its page-budget
   verdict (content p1–8, References p9) is re-verified true of the shipped PDF; it was transiently
   false only at commit `aa2dae5`.
5. **Commit `d5c9650`'s message** repeats the same false "no LaTeX on dss9" claim. Immutable
   history — left as-is; this document and the `CROWNJEWEL_FIGSET.md` erratum are the correction
   of record.
6. **Still open, pre-existing, reviewer-visible** (not introduced by any of this work):
   **Fig 1 and Fig 8 have zero in-text callouts** in both the `.md` and the PDF — their
   `md == pdf_ref` check passes vacuously at 0 == 0. `supp_floats.tex` pins every float number
   with hardcoded `\setcounter`, so inserting or reordering any float silently misnumbers
   everything downstream with no LaTeX warning. And the size hierarchy still tracks spec scope
   rather than importance — Fig 6 (4.708 in, never in scope for any spec) remains larger than
   Fig 5 (3.786 in) and Fig 1 (3.487 in).
