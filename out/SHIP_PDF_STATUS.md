# SHIP_PDF_STATUS — camera-ready PDF: rebuilt, finalized, Fig 1 approved, callouts closed

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
| every float `md == pdf_ref` **non-vacuously** | ✅ all 14 at ≥1 == ≥1 (Fig 1 / Fig 8 flipped 0==0 → 1==1, §0.6) |

**Final artifact: 13 pages, References p9, CONTENT PAGES = 8.** `md5 551c2ad450198c6f4a92f7c047fc36d7`
*(the step-1/step-2 artifact was `md5 963059db94806106c7949c4b960f5bae`; superseded by the step-3
callout rebuild of 2026-09-05, §0.6 — content, page budget and every float number are unchanged.)*

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

The camera-ready was closed in three approved steps. Steps 1–2 touched only Fig 1 / Fig 5
presentation; step 3 (§0.6) added two in-text figure callouts and is the only one that touches prose:

**Step 1 — path (a) width-shrink** (`ship_finalize_spec.md`): Fig 1 `0.70 → 0.36\textwidth`,
Fig 5 `0.70 → 0.53\textwidth`. Closed the 9→8 content-page gap.

**Step 2 — approved Fig 1 upgrade** (`ship_fig1_approve_spec.md`): Fig 1 converted from a
two-column `figure*` at `0.36\textwidth` to a **single-column `figure` at `\columnwidth`**.
Exactly one line changed; Fig 5 left at 0.53 as instructed:

```
- \begin{figure*}[t]...\includegraphics[width=0.36\textwidth]{assets/fig1_teaser.png}...\end{figure*}
+ \begin{figure}[t]...\includegraphics[width=\columnwidth]{assets/fig1_teaser.png}...\end{figure}
```

**Not one word of prose changed** across steps 1–2 (step 3 adds exactly two parentheticals, §0.6). An independent word-level diff of the
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

*(Re-measured on the post-callout sources in step 3 and **unchanged** — 0.53/0.56/0.58/0.59 → 8,
0.60/0.62 → 9. See §0.6.)* Shipping at 0.53 therefore leaves **0.06 `\textwidth` = 0.429 in of
Fig 5 width = ≈12.8 pt of float height** in hand — about **6× the step-1 margin**. Freeing Fig 1's second column bought
genuine slack, not just a bigger teaser. The budget should still be re-checked after any prose
edit or a venue-`.cls` recompile (the build substitutes fonts: `TU/ptm` undefined → `TU/lmr`, so a
venue compiling with real Times will produce different metrics), but this is no longer a knife-edge.

*Unused option, measured and available:* Fig 5 could be enlarged to as much as 0.59 (4.21 in,
+11 % over shipped) while keeping content = 8. It was left at 0.53 because the approval spec said
to change only Fig 1.

### 0.6 Step 3 — the Fig 1 / Fig 8 callouts (2026-09-05, `ship_callouts_spec.md`)

§8 item 6 flagged that **Fig 1 and Fig 8 had zero in-text callouts** in both the `.md` and the PDF,
so their `md == pdf_ref` check passed **vacuously at 0 == 0**. Both are now called out, once each,
in prose that already made the factual point the figure carries — no new claim, no new number:

| | added text (verbatim) |
|---|---|
| **Fig 1**, Intro ¶1 | `.md` → `…do not survive even one frame transition (Fig 1). With 3D Gaussian` |
| | `.tex` → `…do not survive even one frame transition (Fig.~\ref{fig:1}). With 3D Gaussian` |
| **Fig 8**, §5.4 Act 4 | `.md` → `…but it collapses under mesh-free supervision (Fig 8): trained` |
| | `.tex` → `…but it collapses under mesh-free supervision (Fig.~\ref{fig:8}): trained` |

**Why these two anchors carry no fabrication.** Fig 1's fourth column is a two-frame overlap
(frames 100+101, red = *t*, blue = *t+1*) in which the per-frame Canny row resolves into separated
red and blue fringes while the object-space row composites to purple — which *is* the sentence it
is attached to, "most of its strokes do not survive even one frame transition." Fig 8's left panel
plots chair 0.8395 / 0.6371 and lego 0.9046 / 0.6569 against a dashed `frozen NO-GO bar 0.72`, and
its own title is "Act 4: the semantic signal is supervision-bound" — which *is* the clause it is
attached to, "it collapses under mesh-free supervision." The Fig 8 callout is deliberately placed
**before** the sentence's photometric aside (0.7326 / 0.5637), because Fig 8 does **not** plot
those two numbers; attaching it later would have implied it does. Fig 8's chair bar reads 0.8395
where the prose quotes Act 3's 0.8401 — the caption already reconciles this ("as recomputed in the
falsification study … agree … to the third decimal"), and the prose was **not** harmonised to the
figure, which would have moved a banked number.

**Everything the frozen go/no-go asked for, measured on the rebuilt artifact:**

| frozen requirement | result |
|---|---|
| numeral conservation stays 304/304 | ✅ **304/304, 133/133, lost {} / invented {}** — unchanged. A single digit is not a numeral to `NUM = \d+\.\d+\|\d{2,}`, so `Fig 1` / `Fig 8` add none |
| 0 unresolved refs, 0 lost/invented numerals | ✅ `unresolved_refs 0`; `??` count 0 over the whole PDF |
| Fig 1 / Fig 8 `md == pdf_ref` **non-vacuous** | ✅ both **md 1 / pdf_ref 1 / captioned 1**. Zero floats now pass vacuously; zero `md != pdf_ref` mismatches |
| **no float misnumbering downstream** | ✅ float **numbers and caption pages byte-identical** to the shipped PDF (Fig 1 p1; 2,3 p5; 5,6 p6; 4,7,8 p11; 9 p12; Tab 1–4 p10, Tab 5 p12), and all 15 printed image sizes identical. `supp_floats.tex` untouched |
| page budget content p1–8, References p9 | ✅ `content_pages 8`, `references_start_page 9`, `pages_total 13`, supp p9, appendix p13 — every value unchanged |

Compile health is unchanged: **0 errors, 0 Overfull hboxes, the same 12 Underfull warnings**, and
`main.log` is **identical to the shipped build except one line** — `main.xdv` grew 72260 → 72316
bytes. `out/phase1h_gate.json` changes in **exactly two fields**: the Fig1 and Fig8 blocks, 0/0 →
1/1. Nothing else in it moved.

A whole-PDF word-multiset diff adds exactly four real tokens — `(Fig.` ×2, `1).` and `8):` — and
alters no word. It is *not* a pure addition, and the difference is worth stating precisely: two
tokens are **re-punctuated** (`transition.` → `transition`, `supervision:` → `supervision`) because
the period and the colon moved outside the new parentheses, and five more are `pdftotext`
de-hyphenation artifacts of moved line breaks (`perframe` → `per-` + `frame`, `pseudolabels` →
`pseudo-labels`, `inscene` → `in-scene`, `frame-by-frame` → `frame-byframe`). No word is added,
removed or changed beyond the two parentheticals, and the numeral multiset is untouched — but
"removes nothing" would be wrong, so it is not claimed. Prose reflowed across the p1→p5 boundaries and was fully absorbed by
p5; pages 6–13 are untouched apart from the Fig 8 line in §5.4. Both edits are **in-line**: neither
file gained or lost a line (`body_main.tex` 528, `PAPER_DRAFT.md` 677, unchanged), so the
line-number citations banked elsewhere still resolve — `body_main.tex:329–341` is still the
red-team threshold paragraph and is still **byte-identical to `7fb5976`**.

**The `.md` and the `.tex` were edited by hand, in lockstep, and the converter was not re-run.**
`scripts/phase1h_md2tex.py` would regenerate `body_main.tex` with Fig 1 back as a `figure*` at
`0.7\textwidth`, destroying step 2 and the page budget with it. Instead the hand edit was *verified
against* the converter: running it on the edited `.md` into a scratch directory reproduces both new
lines character-for-character, and the resulting file differs from the shipped `body_main.tex` by
**exactly the two pre-existing camera-ready float lines** (Fig 1 single-column, Fig 5 at 0.53) —
i.e. the same divergence set as before this step. The callout step introduces **no new drift**
between the `.md` source of truth and the shipped `.tex`.

**Page-budget headroom re-measured, as §0.5 requires.** §0.5 says the budget "should still be
re-checked after any prose edit", and step 3 is a prose edit, so the Fig 5 width sweep was re-run in
scratch **on the post-callout sources** rather than inheriting the pre-callout result. The ceiling
is **unchanged**: content = 8 at Fig 5 = 0.53 / 0.56 / 0.58 / **0.59**, and content = 9 at 0.60 /
0.62 — the same flip point as before the callouts. Shipping at 0.53 therefore still leaves the
≈12.8 pt of float height §0.5 claims. Six probe builds, all in scratch; `~/3dgs_line` untouched by
every one, and each asserted its own sources (post-callout, Fig 1 single-column, Fig 5 at the swept
width) before compiling.

**One honest interaction with §0.3, stated rather than buried.** The Fig 1 callout now invites the
reader to look at a teaser whose in-figure text §0.3 measures as **still below print-legible**
(~1.8–2.6 pt), and the fourth-column header the callout leans on — "frames 100+101 overlaid
(red = *t*, blue = *t+1*)" — is one of the four column labels named there. The *visual* content the
callout points at is legible at 1× (two rows of panels; a purple composite on top, separated red and
blue fringes below), and every number the teaser carries is in the body prose, so nothing is lost —
but item 6a does not repair item 1's residual cost, and the two should be read together.

**Source drafts kept in parity.** `out/PAPER_DRAFT.md` is an *assembly* of the section drafts
(`assemble_spec.md`), and this repo's discipline is to edit the source draft and mirror it, never
the assembly alone. Both callouts were therefore also applied to `out/ABSTRACT_INTRO_DRAFT.md`
(Fig 1) and `out/SEC5_DRAFT.md` (Fig 8), which were byte-identical to the assembly at both passages
before the edit and are byte-identical again after it. Without this, a future re-assembly would
regenerate `PAPER_DRAFT.md` *without* the callouts while the PDF kept its two `\ref`s — flipping the
gate to `md 0 / pdf_ref 1`, a **real mismatch, strictly worse than the 0 == 0 vacuity 6a fixed**.

*Ordering note:* `out/phase1h_gate.json` is git-tracked and the gate compares the `.md` against
`paper/main.pdf`. It must be run **after** the rebuild — running it in between would bank a real
`md 1 / pdf_ref 0` mismatch. Sources were edited, then tectonic ran, then the gate.

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
report `captioned ≥ 1`; every `md` count equals its `pdf_ref` count — and **since step 3 (§0.6)
none of those equalities is vacuous**: the last two 0 == 0 matches, Fig 1 and Fig 8, are now
1 == 1. *(The gate block quoted above is the step-1/step-2 run; the step-3 run is identical to it
except that the Fig1 and Fig8 `figtab` entries read `md 1 / pdf_ref 1 / captioned 1`.)*

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
| Fig 1 | p2 / — | **p1** / — → **p1 / p1** after step 3 |
| Fig 2 | p5 / p4, p6 | p5 / p4, p6 |
| Fig 3 | p5 / p4 | p5 / p4 |
| Fig 5 | p6 / p5 | p6 / p5 |
| Fig 6 | p6 / p5, p6, p7 | p6 / p5, p6, p7 |
| Fig 8 | p11 / — | p11 / — → **p11 / p7** after step 3 |
| Fig 9 | p12 / p5 | p12 / p5 |

*(The `cited` column is measured on the PDF. Step 3 changed it for Fig 1 and Fig 8 only, and moved
no caption: every caption page in this table is the same before and after. The Fig 8 row is new —
the original table measured only the six floats step 2 could plausibly have moved.)*

*Correction to an earlier draft:* three adjacency changes previously reported here — Fig 6's caption
moving p7 → p6, Fig 9's p13 → p12, and Fig 3's citation splitting from p5/p5 to p4/p5 — are all
**step-1** effects relative to `aa2dae5`. They were already true before this step and are wrongly
attributed if credited to the single-column change. Fig 1 moving to p1 is the only adjacency change
this step caused, and it is an improvement: the teaser now sits on the first page.

## 7. Invariants

| invariant | status |
|---|---|
| Mesh EVAL-ONLY / no method-path code touched | ✅ `git diff` contains **no** `scripts/` change |
| No banked number altered | ✅ **no banked number altered in any step.** Steps 1–2 changed no prose at all; step 3 (§0.6) adds two figure callouts and nothing else — the numeral multiset is byte-for-byte the same 304/133. No `*RESULTS*.md` changed; the only `out/*.json` change is the gate's own output |
| No asset re-rendered | ✅ `git diff -- paper/assets` empty |
| No fabricated page count or gate result | ✅ every figure traces to a real invocation on a real build |
| Probe builds isolated | ✅ all **97** probe builds across three rounds ran in scratch; `~/3dgs_line` untouched by every one |

Repo-level, **step 2** changed five tracked files vs `7fb5976`: `paper/body_main.tex` (one line),
`paper/main.pdf`, `out/CROWNJEWEL_FIGSET.md`, `out/LATEX_ASSEMBLY_CHECK.md`, and this document; at
that point `out/phase1h_gate.json` was **byte-identical**, because the single-column change altered
no value the gate reports.

**Step 3** (§0.6) changes eight tracked files on top of that: `paper/body_main.tex` (one line, again),
`out/PAPER_DRAFT.md` (one line — the `.md` is the gate's source of truth and must move in lockstep),
`out/ABSTRACT_INTRO_DRAFT.md` and `out/SEC5_DRAFT.md` (the two section drafts the assembly is built
from, kept byte-identical to it),
`paper/main.pdf`, `out/phase1h_gate.json` (**no longer byte-identical** — the Fig1 and Fig8 `figtab`
blocks go 0/0 → 1/1, and nothing else in the file moves), `out/LATEX_ASSEMBLY_CHECK.md` (Erratum 2),
and this document. `paper/assets` is still untouched and `scripts/` is still untouched.

⚠️ `paper/main.log`, `ship_pdf_spec.md`, `ship_finalize_spec.md`, `ship_fig1_approve_spec.md` and
`ship_callouts_spec.md` are untracked and **not** covered by `.gitignore` — stage explicitly,
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
6. *(This item originally bundled **three** independent defects. Only the first is fixed; the
   other two are re-listed unchanged rather than retired with it.)*

   **6a. Zero in-text callouts for Fig 1 and Fig 8 — RESOLVED (2026-09-05, §0.6).** Both figures
   now carry one callout each, placed in prose that already made the point the figure supports:
   Fig 1 in Introduction ¶1, Fig 8 in §5.4 (Act 4). Their `md == pdf_ref` check is now
   **non-vacuous at 1 == 1**, and no float anywhere in the paper still matches at 0 == 0. The
   frozen go/no-go held on every clause: 304/304 numeral conservation, 0 unresolved refs, 0
   lost / 0 invented, **zero float-number or caption-page change**, content p1–8 / References p9.
   Verbatim text, the fabrication check on both anchors, and the full measurement table are in
   §0.6. The callouts were applied to the **source drafts too** (`out/ABSTRACT_INTRO_DRAFT.md`,
   `out/SEC5_DRAFT.md`), not just to the `PAPER_DRAFT.md` assembly — otherwise a re-assembly would
   silently regress this fix into a real `md 0 / pdf_ref 1` mismatch. `out/LATEX_ASSEMBLY_CHECK.md`
   carried the same claim in two places and now carries a dated **Erratum 2** (item 7 below).

   **6b. `\setcounter` fragility — STILL OPEN, untouched.** `supp_floats.tex` pins every float
   number with a hardcoded `\setcounter`, so inserting or reordering any float silently misnumbers
   everything downstream with no LaTeX warning. Step 3 added **no float** — only two `\ref`s — so
   this hazard is neither triggered nor reduced; the 9 hardcoded `\setcounter` calls are all still
   there. It was verified *empirically* rather than assumed: every float number and caption page in
   the rebuilt PDF is identical to the shipped one.

   **6c. Size hierarchy tracks spec scope rather than importance — STILL OPEN, untouched.**
   Fig 6 (4.708 in, never in scope for any spec) remains larger than Fig 5 (3.786 in) and Fig 1
   (3.487 in). Step 3 changed no float width; all 15 printed image sizes are identical.

7. **`out/LATEX_ASSEMBLY_CHECK.md` — ERRATUM 2 added (2026-09-05).** Two of its statements were
   falsified by the callout step and one was already wrong. Row (c) asserted *"Fig 1 and Fig 8 have
   zero body references in the .md itself"* — struck, and the per-float list now carries **Fig1×1**
   and **Fig8×1**. Row (b)'s *"every float still in-PDF and referenced"* was **false** for exactly
   those two floats while the callouts were missing, and is now true of all 14. And §5's deferred
   entry recorded the blocker as *"adding \"(Fig 1)\" would change the pinned reference counts"* —
   **factually wrong**, since the gate's `\d+\.\d+|\d{2,}` never matches a single digit; that
   mistaken belief is what kept the defect open, so it is corrected on the record rather than just
   deleted. §5's *other* Fig 8 item (the 0.8395-vs-0.8401 chair-bar reconciliation) is a different
   defect and remains genuinely deferred.

8. **Doc debt found while doing item 6a — reported, deliberately NOT edited.** Four banked
   documents quote per-float reference counts. They are dated audits of earlier commits, and
   editing them would corrupt the record rather than fix anything — so they are left stale on
   purpose, not overlooked. **One of them this step really does falsify, and saying otherwise would
   be wrong:** `out/CAMERA_READY_CHECKLIST.md` lines 11–13 count **whole-file** `Fig N` occurrences
   in `PAPER_DRAFT.md` (including the asset table), a different convention from the gate's body-only
   count; under that convention Fig 1 and Fig 8 each go **1 → 2** because of the callouts, so two of
   its twelve numbers are now stale. They were correct at the commit they audit, and the other ten
   still match exactly. `out/PHASE1G_CONVERGE.md` line 84 uses the same convention but is a
   *diff-vs-HEAD* statement about commit `afca8ec` ("reference counts identical to HEAD"), so it is
   self-dating and stays true of what it asserts; `out/CROWNJEWEL_FIGSET.md` §6 still says the gate reports
   `Fig9: md 1 pdf-ref 0 captioned 0`, which commit `aa2dae5` already superseded; and
   `out/PAPER_DRAFT.md`'s asset table has no Fig 9 or Tab 5 row (it sits *below* the gate's md
   cut-off, which is why it drifted unnoticed). Item 4 above says "all three stale counts" while
   the erratum it describes says "Four counts" — a pre-existing off-by-one that turns on whether
   the asset count is counted once or twice; left as found.

> **Erratum 3 (2026-09-05, B3 close-out resync).** `paper/*.tex` regenerated from the updated
> `out/PAPER_DRAFT.md` via `scripts/phase1h_md2tex.py` (converter now emits the shipped Fig 1
> `\columnwidth` and Fig 5 `0.53\textwidth` layouts itself, and maps `S̄`, `10⁻⁹`, `σ` to LaTeX);
> `main.pdf` rebuilt with tectonic (env `latex`); gate re-run (`out/phase1h_gate.json`):
> **numeral conservation PASS 393/393 (183/183 distinct), lost {} / invented {}, 0 unresolved
> refs, all 14 Fig/Tab reference counts md == pdf**. New PDF `md5 5b76cdb48e9971f9d1919ccae3cc0618`,
> 15 pages, References p10, Appendix A p14–15. **RESIDUAL: content pages = 9 (criterion 8).**
> The shipped p8 sat on a page cliff; the mandated disclosures (Canny/TEED pull-field attribution
> in §3.2/§3.4/§3.5, the GT-subset pointer in §5.1, the line-field NO-GO in §6 — ≈15 md lines
> after compression; the long versions live in Appendix A.4/A.5, outside the content budget)
> spill 23 layout lines of §7 onto p9. Restoring 8 content pages requires cutting ≈25 column
> lines of frozen prose — an editorial decision left to the orchestrator; no banked numeral
> changed and no LaTeX numeral was hand-edited.
