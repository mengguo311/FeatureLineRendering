# SHIP_PDF_STATUS — camera-ready PDF rebuilt for real

**VERDICT: the PDF is rebuilt, real, and gate-clean. Two things this task uncovered must be
settled before ship: (a) the content-page budget is over by one page, (b) the premise of the
original ship-blocker was false and three banked docs now assert things that are no longer true.**

- ✅ **`paper/main.pdf` rebuilt for real** — 14 pages, 0 errors, 0 unresolved refs, 0 overfull hboxes.
- ✅ **Fig 9 + Tab 5 verifiably render** — captions, embedded images at native resolution, and the
  shipped PNGs re-verified **byte-identical** to a fresh render whose 38-check ledger drift gate passed.
- ✅ **`phase1h_gate.py` on the fresh PDF: conservation PASS, 304/304, 133/133, 0 lost / 0 invented,
  0 unresolved refs.** Fig9 and Tab5 both flipped `pdf-ref 0 → 1`, `captioned 0 → 1`.
- ✅ **Fig 9 placement: KEEP IN SUPP** — measured on real builds, not guessed. Promotion lands on
  9 content pages in *both* prose states, never ≤ 8.
- ❗ **CORRECTION: no toolchain was installed. There never was a missing toolchain.** tectonic has
  been on this machine since 2026-07-28. The prior "no LaTeX on dss9" blocker was a **false negative**.
- ❌ **content pages = 9, over the declared 8** — with Fig 9 already in SUPP. Cause isolated to
  the prose added in `d5c9650`, **not** the new floats. Not fixed here; a fully measured remedy
  sweep (20 builds) is below.

Every number below is from a real `pdfinfo` / `pdftotext` / `pdfimages` / gate / drift-gate run.
Nothing is estimated or carried over from the stale PDF. All claims were then re-derived by four
independent read-only audits plus an adversarial completeness critic; **35/35 quantitative claims
CONFIRMED, 0 refuted** — and the critic caught one **false narrative claim**, corrected in §1.

---

## 1. Toolchain — CORRECTED: it already existed; nothing was installed

**The original ship-blocker was never real.** Commit `d5c9650` states *"SHIP-BLOCKER: no LaTeX on
dss9 (pdflatex/latexmk/xelatex/tectonic absent) → PDF un-rebuildable"*, and
`out/CROWNJEWEL_FIGSET.md` states the `latex` and `tex` envs *"exist but their `bin/` directories
are empty"*. **Both were false when written:**

```
$ ls ~/bin/miniconda3/envs/{latex,tex}/bin | wc -l     -> 50 each, both include `tectonic`
$ stat envs/latex/bin/tectonic   -> Birth: 2026-08-03 13:13:55   (32 days before this task)
$ stat envs/tex/bin/tectonic     -> Birth: 2026-07-28 05:24:31
$ grep 'cmd:' envs/latex/conda-meta/history
    2026-08-03 13:13:56  conda create -n latex -c conda-forge tectonic -y   (+tectonic-0.17.0)
    2026-09-04 23:04:44  conda install -n latex -c conda-forge tectonic -y  (-openssl-3.6.3 / +openssl-3.6.4)
```

Decisive control: the **`tex` env was never touched by this task** and runs
`conda run -n tex tectonic --version` → `Tectonic 0.16.9`, exit 0, right now. Today's
`conda install` changed exactly one package (`openssl 3.6.3 → 3.6.4`), and `ldd` shows tectonic
does not link openssl at all — so that bump cannot be what made it runnable.

**Root cause of the false blocker: a false-negative detection.** tectonic was installed in
non-default conda envs and therefore not on `PATH`; a bare `command -v tectonic` reports absent.
An earlier `ls .../envs/latex/bin | head -40` on a 50-entry directory also hides `tectonic`, which
sorts last. Any future toolchain probe must check `conda env list` + per-env `bin/`, not `PATH`.

**Which env was used, and why.** Builds ran in the pre-existing **`latex`** env (tectonic 0.17.0),
not `vfsdgs` as the spec suggested. Solving into `vfsdgs` would have risked perturbing the env
every banked experiment runs in, for zero benefit — tectonic is a standalone binary. `vfsdgs`,
`tex` and `base` were left untouched; `vfsdgs` was re-verified working (numpy 1.23.5, torch
2.3.1+cu121) after the fact. The tectonic bundle cache (`~/.cache/tectonic`, 46 MB,
`default_bundle_v33` + prebuilt `latex-33.fmt`) was already warm.

**These three statements are now stale and should be corrected in the repo** (this doc supersedes
them in prose only; neither file was edited):
1. `d5c9650` commit message — "no LaTeX on dss9 … PDF un-rebuildable".
2. `out/CROWNJEWEL_FIGSET.md` — "their `bin/` directories are empty".
3. `out/CROWNJEWEL_FIGSET.md` — "the 8-content-page budget intact" (see §7).

## 2. The build

```
$ cd ~/3dgs_line/tier1/paper && tectonic -X compile main.tex --keep-logs
Output written on main.xdv (14 pages, 72384 bytes).
note: Writing `main.pdf` (2.0373239517211914 MiB)
```

| | value |
|---|---|
| errors (`^!` in `main.log`) | **0** |
| Overfull hboxes | **0** |
| Underfull warnings | **12** (several at badness 10000, incl. one `\vbox` while `\output` is active) |
| font warnings | `TU/ptm/{m,bx}/{n,it}` undefined → `TU/lmr` substituted; "some font shapes not available, defaults substituted" |
| unresolved refs (`??`) | **0** |
| "rerun to get cross-references right" | **0** (tectonic multi-passes internally) |
| fonts | 12 faces, **all Type 1C, all embedded + subset** — satisfies IEEEtran's camera-ready "Type 1 only" rule |

**The Underfull/font warnings are pre-existing, not regressions.** The `bB` control build (§6)
compiled from the exact `2beba1d` sources produces `pdftotext -layout` output **byte-identical**
to the banked stale PDF, and `pdffonts` returns the identical 12 faces with identical subset tags
and object IDs. They are worth resolving before submission but nothing here introduced them.

**The PDF really is new, not relabelled:**

| | stale (banked) | rebuilt |
|---|---|---|
| md5 | `43b0dbdf0d104f219a4bf2df56f007e7` | `13474a03f8d0f3d7c02a158dd83bfb5f` |
| bytes | 1,879,281 | 2,136,289 |
| CreationDate | Wed Sep 2 23:58:45 2026 | Fri Sep 4 23:05:50 2026 |
| pages | 12 | 14 |

Anonymization re-checked on the new file: zero hits for `u00134`, `3dgs_line`, `mizuho`, `/home/`,
`/tmp`, or Author/Title metadata.

## 3. Verified page counts

Counted from the rebuilt PDF: `pdftotext` splits on form-feed, the trailing empty block is
discarded, and headings are matched after whitespace-stripping (**IEEEtran small-caps means a
naive `grep References` returns 0 — the extracted text is `R EFERENCES`**).

| measure | value |
|---|---|
| **total pages** | **14** |
| References heading first appears on page | **10** |
| **CONTENT pages (strictly before References)** | **9** |
| Supplementary heading page | 10 (below the bibliography, same page) |
| Supplementary float pages | 11 – 13 |
| Appendix A starts on page | 14 |
| declared budget | **8 content pages, refs excluded** |
| **budget status** | ❌ **OVER by 1 page** |

Page 9 is a **small partial spill**: 26 non-empty lines / **225 words**, and by `pdftotext -bbox`
every one of those words is in the **left column only** (x ∈ [49, 300] of a 612 pt page,
y stopping at 360 of 792). Full content pages carry 611–953 words; page 9 carries ~24 % of a page.

**How binding is "8"?** The number is self-declared, not venue-imposed: `paper/main.tex` line 1
says *"IEEEtran conference template (neutral stand-in; **no venue banked**)"*, and a repo-wide
grep finds no banked venue. Its only source is `out/LATEX_ASSEMBLY_CHECK.md` (b): *"declared:
CVF/NeurIPS-family norm, 8 content pages excluding references"*. That family is internally split —
**CVF/CVPR is 8, NeurIPS (2022+) is 9** — and the class actually in use is `IEEEtran[conference]`,
whose own norm differs again. So: the **declared** number is definitively exceeded (measured), but
whether it *binds* is an open call the orchestrator owns, and it is cheap to make it moot (§7).

## 4. Fig 9 / Tab 5 really render

| check | result |
|---|---|
| Fig 9 caption in PDF text | ✅ p13 — *"Fig. 9. Object-space feature lines versus per-frame Canny on a held-out orbit…"* |
| `TABLE 5` heading + full caption | ✅ p13 — *"P ER - SCENE HELD - OUT SUMMARY: … FICUS IS EXCLUDED BY SCENE SCOPING …"* (letterspaced small caps) |
| Fig 9 **image** embedded | ✅ obj 26 on p13 at **2312×765** = exactly `assets/fig9_crownjewel.png` |
| Tab 5 **image** embedded | ✅ obj 28 on p13 at **2040×390** = exactly `assets/tab5_per_scene.png` |
| both **after** References | ✅ p13 > p10 — in SUPP, not the main body |
| in-text prose refs | ✅ exactly one `Fig. 9` **and** one `Tab. 5`, both in the same p5 sentence |
| visual render check | ✅ p13 rasterised and inspected: Fig 9's three panels (motion-independent Canny floor / 3.44×→11.49× ratio sweep with the silhouette-controlled bound in red / both confound controls) and Tab 5's chair-lego-ficus-excluded rows all display correctly |
| **values provenance-gated** | ✅ `render_fig9_crownjewel.py` re-run into scratch: **38/38 ledger drift checks OK, 0 mismatches**, and the regenerated PNGs are **md5-identical / 0 max pixel diff** to the shipped `paper/assets/` copies |
| stale PDF contained either | ❌ zero hits for both — the staleness this task closes |
| total embedded images | 15 image XObjects (+15 alpha smasks) = all 15 asset PNGs |

## 5. Gate re-run on the freshly-built PDF

```
{ "pages_total": 14, "references_start_page": 10, "content_pages": 9,
  "supplementary_page": 10, "appendix_page": 14,
  "md_numerals": 304, "md_distinct": 133, "pdf_numerals": 304, "pdf_distinct": 133,
  "lost": {}, "invented": {}, "unresolved_refs": 0, "conservation": "PASS" }
```

| float | stale gate | fresh gate |
|---|---|---|
| Fig9 | md 1 · pdf-ref **0** · captioned **0** | md 1 · pdf-ref **1** · captioned **1** ✅ |
| Tab5 | md 1 · pdf-ref **0** · captioned **0** | md 1 · pdf-ref **1** · captioned **1** ✅ |

All 14 floats now report `captioned ≥ 1` and every `md` count equals its `pdf_ref` count. The gate
reads `paper/main.pdf` through `pdftotext` at run time, so it cannot have served a cached result;
an independent re-run reproduced `out/phase1h_gate.json` byte-identically.

### 5.1 What 304/304 does NOT certify — read this before quoting it

Three coverage limits, all verified:

1. **Every table's numbers are invisible to the gate.** Tab 1–5 are `\includegraphics` **rasters**
   inside `table*` environments; `pdftotext` on pages 11–13 yields captions only, no tabular body.
   So precision, recall, popping rates, Fréchet ratios and the entire frozen-gate ledger live in
   PNG pixels, outside the multiset check. A wrong or stale value in any result table would leave
   the gate at PASS, 0 lost / 0 invented. **304/304 certifies the PROSE.**
   *Countervailing evidence, newly measured:* the two crown-jewel rasters **are** independently
   provenance-gated — `render_fig9_crownjewel.py` asserts all 38 plotted values against the banked
   ledger before writing, and the shipped PNGs reproduce byte-identically (§4). That check now
   covers Fig 9 / Tab 5; Tab 1–4 have no equivalent re-verification in this task.
2. **The gate is invariant to deleting load-bearing prose.** Probe build `bE`, which removes the
   entire 180-word red-team lego-threshold paragraph, still returns 304/304 / PASS.
3. **The metric was partly preserved by removing numbers from the paper.** `d5c9650` states it
   outright: *"De-numeralized threshold para (8 numerals) to keep gate PASS"* — the exact values
   `{30, 213711, 30.000, 30.05, 47, 0.6408, 0.6360, 0.3004}` now live only in
   `RESULTS_MASTER` / `LEGO_THRESHOLD_AUDIT`.

**Fragility worth fixing:** `phase1h_gate.py`'s `first_page()` returns the first page whose
space-stripped text *contains* `REFERENCES`, unrestricted to headings, and `content_pages =
ref_pg - 1` is never validated. Pages 1 and 2 already contain the word "reference"; only the
singular form saves it. Any future plural in the body ("cross-references") would silently resolve
`references_start_page` to 1 or 2 and report `content_pages` 0 or 1 as a clean value. It did not
fire here — page 10 is the only match under the gate's exact logic — but it is unguarded.

## 6. Fig 9 placement — decided on measured builds

**DECISION: Fig 9 STAYS IN SUPP.** Built and measured, not inferred. Every probe ran in an
isolated scratch directory; `~/3dgs_line` was never touched by any of them.

| build | body prose | Fig 9 placement | total pp | refs pg | **content pp** |
|---|---|---|---|---|---|
| **bB** — exact `2beba1d` sources (reproduction control) | banked | absent | 12 | 9 | **8** |
| **bC** — `2beba1d` body + current SUPP floats | banked | SUPP | 13 | 9 | **8** |
| **bD** — `2beba1d` body, Fig 9 promoted | banked | **main body** | 14 | 10 | **9** |
| **SHIPPED** — current HEAD | +16 lines | SUPP | 14 | 10 | **9** |
| **bA** — current HEAD, Fig 9 promoted | +16 lines | **main body** | 14 | 10 | **9** |

Promotion lands on **9 content pages in both prose states**, never ≤ 8 → the spec's promotion
condition fails → **keep in SUPP**. `bD` is decisive: even at the banked prose length that genuinely
fits in 8 pages, moving Fig 9 into the body costs **+1 content page**. The SUPP placement is
**budget-forced, not merely conservative**.

`CROWNJEWEL_FIGSET.md` flagged this as *"a scout simulation suggested … 8 → 9, which I could **not**
verify here … should be treated as unconfirmed."* **Now confirmed by a real build.**

**A plausible-sounding inference that is wrong, and was tested:** *"the stale PDF was only under
budget because it was missing the crown-jewel figure."* False. `bC` adds Fig 9 + Tab 5 as SUPP
floats to the banked body and costs **+1 total page and ZERO content pages** (12 → 13 pp, refs
still p9). The floats were correctly free, exactly as `d5c9650` intended.

## 7. The one open blocker: content pages = 9

Not anticipated by the spec, which assumed the 8-page budget still held. It does not.

**Attribution is measured.** `bB` reproduces the banked 12 pp / refs p9 / 8-content build *exactly*
(its five `.tex` files md5-match `git show 2beba1d:paper/*`, and its extracted text is byte-identical
to the stale PDF) → the toolchain is faithful and the change is real. `bC` then shows the new floats
cost **zero** content pages. `git log 2beba1d..HEAD -- paper/` returns exactly **one** commit
(`d5c9650`, +16 lines in `body_main.tex`) — no confound. The 9th content page is bought by those
**16 lines of prose**: the 3-line Fig 9 / Tab 5 cross-reference sentence plus the 13-line (180-word)
de-numeralised lego threshold-sensitivity paragraph. Word arithmetic agrees: body words went
6331 → 6552, **+221**, essentially the entire 225-word page-9 spill.

**Nothing was edited to fix it.** Cutting frozen-thesis prose and resizing camera-ready figures are
editorial calls that belong to the orchestrator. But the *measurement* half is now done in full —
**20 probe builds**, sweeping both levers to their thresholds:

| remedy | prose cut | float widths (fig1/fig5, fig6) | content pp |
|---|---|---|---|
| shipped | — | 0.70, 0.66 | 9 |
| drop the 180-word paragraph only | 180 w | 0.70, 0.66 | 9 (spill 26 → 9 lines) |
| width-only ladder — 8 probes: 0.66/0.62, 0.64/0.60, 0.62/0.58, 0.58/0.54, 0.56/0.52, 0.54/0.50, **0.53/0.50** | none | 0.66 → 0.53 | **all 9** |
| **bH — width-only, at threshold** | **none** | **0.52, 0.50** (+ Fig2 0.465→0.40, Fig3 →0.88 col) | ✅ **8** |
| para cut + width ladder — 3 probes: 0.68/0.64, 0.66/0.62, 0.64/0.60 | 180 w | 0.68 → 0.64 | all 9 |
| **bG — para cut + mild widths** | **180 w** | **0.60, 0.56** | ✅ **8** |

**Findings from the sweep (these change the recommendation):**

- **No remedy avoids shrinking the two large figures.** Dropping the paragraph alone fails; widths
  alone at anything gentler than 0.52 fail. The real choice is *how much* shrink, traded against
  whether the red-team paragraph stays.
- **Both thresholds are sharp page-break cliffs.** Width-only: **0.53 → 9, 0.52 → 8** — a 0.01
  `\textwidth` margin. Para-cut: **0.64 → 9, 0.60 → 8**. Either remedy is therefore **brittle to any
  future prose edit**, and whichever is adopted should be re-measured after the next source change.
  (My earlier framing of this sweep as "an editorial choice, not a measurement" was wrong — locating
  the minimum sufficient width is a measurement, and it is now made. Only accepting the resulting
  legibility cost is editorial.)
- **`bH` is gate-verified, not merely inferred** (run against a scratch copy of the gate, leaving
  `out/phase1h_gate.json` untouched): `pages_total 13, references_start_page 9, content_pages 8,
  304/304, 133/133, lost {}, invented {}, unresolved_refs 0, conservation PASS, Fig9 1/1, Tab5 1/1`.
- `bH` preserves every banked number and the whole red-team disclosure; `bG` keeps figures ~14 %
  larger but deletes a red-team paragraph whose exact values already live only in
  `RESULTS_MASTER` / `LEGO_THRESHOLD_AUDIT`.

Legibility cost of `bH` (raster resolution *rises* in every case — 468 → 630 ppi for Fig 1 — so
nothing is resampled; only printed size, and therefore in-figure type size, shrinks):

| float | shipped | under bH | Δ |
|---|---|---|---|
| Fig 1 teaser | 5.00 in | 3.71 in | −25.7 % |
| Fig 2 panels | 3.32 in | 2.85 in | −14.0 % |
| Fig 3 | 3.48 in | 3.07 in | −12.0 % |
| Fig 5 survival | 5.00 in | 3.71 in | −25.8 % |
| Fig 6 ceiling | 4.71 in | 3.57 in | −24.2 % |

Under `bG` the three large floats shrink only ~14 %. Note `phase1h_spec.md` grades NO-GO only if
the overflow *"requires cuts of substantive content"* — `bH` requires none, so on the project's own
wording this is a PARTIAL at worst, and closable.

## 8. Invariants

| invariant | status |
|---|---|
| Mesh EVAL-ONLY / no method-path code touched | ✅ `git diff` contains **no** `scripts/` change at all |
| No banked number altered | ✅ no `.tex` source modified (`git diff -- 'paper/*.tex'` empty); no banked `out/*.json` or `*RESULTS*.md` changed other than the gate's own output |
| No fabricated page count or gate result | ✅ every figure traces to a real invocation on a real build; independently re-derived by 4 read-only audits, **35/35 CONFIRMED, 0 refuted** |
| Probe builds isolated | ✅ all 20 ran in scratch; `~/3dgs_line` untouched by every one |
| Working tree | `M out/phase1h_gate.json`, `M paper/main.pdf`, `?? paper/main.log`, `?? out/SHIP_PDF_STATUS.md`, `?? ship_pdf_spec.md` |

⚠️ `paper/main.log` is untracked and **not** covered by `.gitignore` (`git check-ignore -v` returns
nothing), so a naive `git add -A` would commit a LaTeX build log — and would sweep in
`ship_pdf_spec.md` (the orchestrator prompt) too.

## 9. What the orchestrator has to decide

1. **Commit the rebuilt PDF.** It is strictly better than the stale one: real, current, Fig 9 +
   Tab 5 present and ledger-verified, gate PASS. Stage it explicitly — do not `git add -A`.
2. **Close the 9-content-page overrun**: adopt `bH` (no prose touched, figures −26 %) or `bG`
   (red-team paragraph cut, figures −14 %). Both are built, measured and gate-verified. Re-measure
   after any later prose edit — both sit on page-break cliffs. Or, alternatively, decide the
   self-declared 8 does not bind (no venue is banked; the cited "CVF/NeurIPS family" is itself split
   8 vs 9) — but decide it explicitly rather than by drift.
3. **Correct three now-false banked statements** — none were edited by this task:
   - `out/LATEX_ASSEMBLY_CHECK.md` line 2 (top VERDICT) and line 44 (b): both still assert the
     8-content-page budget **PASS — content ends p8; References start p9**. False of the shipped
     PDF (content ends p9, References start p10).
   - `out/CROWNJEWEL_FIGSET.md` line 65: "the 8-content-page budget intact" — that quoted
     `content_pages 8` from the gate reading the **stale** PDF. Its 304/304 half does survive.
   - `out/CROWNJEWEL_FIGSET.md` + commit `d5c9650`: the "no LaTeX on dss9 / empty `bin/`" claim
     (§1). Root cause was a `PATH`-only probe; worth fixing the probe, not just the sentence.
4. **Fig 9 placement needs no further thought: SUPP, measured, settled.**
5. Optional, pre-existing, reviewer-visible: **Fig 1 and Fig 8 have zero in-text callouts** in both
   the `.md` and the PDF (their `md == pdf_ref` check passes vacuously at 0 == 0) — a teaser going
   uncited is usually tolerated, Fig 8 sitting in supplementary with no callout is less so. And
   `supp_floats.tex` pins every float number with hardcoded `\setcounter`, so inserting or
   reordering any float silently misnumbers everything downstream with no LaTeX warning.
