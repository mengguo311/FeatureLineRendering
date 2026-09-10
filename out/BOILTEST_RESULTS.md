# BOIL TEST — does per-frame Canny visibly boil on cadpartA? The linchpin.

`scripts/boiltest.py`. 8 CONSECUTIVE orbit frames (100–107 of 240, adjacent, not every-20th),
ours vs per-frame Canny, side by side. **MESH EVAL-ONLY: reads no mesh at all.** Nothing
committed.

---

## VERDICT: NEGATIVE

**Canny does NOT visibly boil on cadpartA at consecutive frames.** On the strip — the
instrument the pre-registration named — the Canny drawing holds its structure across all eight
adjacent frames. It is dense and ragged, individual short fragments differ, but the drawing
does not fall apart or reorganise.

Per the pre-registered rule: **our honest headline collapses to clean + stable +
complete-enough on cadpartA only. Not temporal superiority.**

## 1. What is nonetheless true, measured

I added an **ink-level** churn measure to sit beside P_pop's stroke-identity measure, since the
whole finding that prompted this test is that the two come apart:

> `ink_churn(k)` = fraction of ink pixels in frame k with no ink pixel within 1.5 px in
> frame k+1, symmetrised. P_pop asks "did the stroke keep its identity". This asks "did the
> drawn pixels move", which is what a viewer sees.

| solid | ours | Canny | ratio |
|---|---|---|---|
| **cadpartA** | **0.0145** | **0.0985** | **6.80x** |
| gcube (calibration) | 0.0255 | 0.0852 | 3.34x |

So a real ink-level advantage exists, **6.8x on cadpartA**, but it is far below P_pop's
10–20x, and it does not clear the visibility bar.

## 2. Why the number says one thing and the picture says another

The adjacent-frame overlay (frame 100 red, 101 blue) is stark: **ours is almost entirely black**
— the two frames overlap nearly perfectly, with only thin colour fringes from sub-pixel camera
motion. **Canny shows whole segments in pure red or pure blue**, concentrated exactly where
predicted, at the through-hole and the interior chamfer detail. Ink genuinely appears and
disappears there.

But Canny draws **374 to 465 fragments per frame**. Turning over 10 percent of that many pieces
changes no gestalt. At video rate it would read as a fine crawl or shimmer along the lines, not
as strokes popping in and out of a sparse drawing. **Shimmer, not structural collapse.**

**An honest limitation of the instrument I introduced:** `ink_churn` does not separate shimmer
from structural popping. gcube at 0.0852 was judged steady; cadpartA at 0.0985 is only 16
percent higher and sits in the same regime. The number cannot decide visibility on its own, and
I am not going to let the 6.80x carry more weight than it can.

## 3. What the headline actually is now

Not "10–20x more temporally stable". On clean flat-shaded solids that claim does not survive
contact with the video, because the baseline's ink is already stable there.

What survives, and is defensible on this evidence:

- **Compactness and structural coherence.** Ours is **42 persistent object-space strokes**;
  Canny is **374–465 per-frame fragments**. Ours is a line drawing, Canny is an edge map. That
  is a representational difference visible in every frame.
- **A real but modest ink-level stability edge**, 6.80x on cadpartA and 3.34x on gcube.
- **Stroke identity that actually persists**, which is what makes the strokes editable,
  stylable and traceable through time. P_pop measures this correctly; it is simply not the same
  thing as visible flicker.

**The visible temporal win remains established only on textured scenes** — lego and chair,
where Canny fires on decals and the ink genuinely boils. Nothing in this test touches those
results; it bounds where the claim may be extended.

## 4. Files

`out/featviz/boiltest_cadpartA_consecutive_strip.png` (8 adjacent frames, ours top, Canny
bottom), `_cadpartA_adjacent_overlay.png` (frame 100 red / 101 blue, ours beside Canny), and
the same pair for gcube as calibration. `out/boiltest.json`, `scripts/boiltest.py`.

---

# PART 2 — the same test on the TEXTURED scenes: lego and chair

Identical protocol: 8 consecutive orbit frames (100–107 of 240), ours vs per-frame Canny,
side-by-side strip plus adjacent-frame red/blue overlay plus `ink_churn`. Each scene uses its
**banked shipped carrier**, exactly what `--variant gated` loads, so this reproduces the setup
behind the banked lego and chair temporal cells. **MESH EVAL-ONLY: reads no mesh at all.**

## VERDICT: PASS on both. Judged on the strip.

**chair is unambiguous.** The Canny panel is a dense field of short marks covering the whole
chair — Canny firing on the printed fabric — and that field is in **completely different places
in every frame**. Adjacent frames share almost no stipple. Meanwhile our 1,166 strokes hold the
silhouette and the seat and back structure in place across all eight frames.

**lego passes too.** Its Canny marks relocate frame to frame rather than shimmering in place,
which is whole-segment turnover, not sub-pixel drift. The character differs from chair: lego's
Canny output is sparser, so it reads as a flickering scatter rather than a boiling field. Our
1,895 strokes hold steady.

## The number, and the mechanism it exposes

| scene | ours | Canny | ratio | regime |
|---|---|---|---|---|
| gcube | 0.0255 | **0.0852** | 3.34x | clean solid |
| cadpartA | 0.0145 | **0.0985** | 6.80x | clean solid |
| **lego** | 0.0584 | **0.5359** | **9.18x** | textured |
| **chair** | 0.0159 | **0.4482** | **28.12x** | textured |

**Canny's own instability jumps 5 to 6 fold between the two regimes**, from 0.085–0.099 on
clean solids to 0.448–0.536 on textured ones. On lego and chair the baseline turns over roughly
**half its ink every single frame**. Ours stays between 0.015 and 0.058 everywhere.

That is the mechanism stated properly: **the baseline's instability is driven by texture, not
by per-frame-ness as such.** Texture edges are view-dependent and move; geometric edges on a
flat-shaded solid are crisp and persistent, so a per-frame detector is already stable there.

## The claim, correctly bounded

Not "10–20x more temporally stable". The honest form, which this pair of tests establishes and
delimits:

> **Where texture dominates the image, per-frame edge detection reorganises about half its ink
> between adjacent frames while our object-space strokes hold, a 9x to 28x ink-level gap that
> is plainly visible. Where geometry dominates and the surface is untextured, the baseline is
> already stable and no visible temporal advantage exists.**

Two honest riders. On lego and chair **ours also draws more than Canny**, 1,895 and 1,166
strokes against a sparse or stippled baseline, so the comparison there is favourable on
completeness as well as stability — the reverse of the clean solids. And these two carriers are
the shipped ones rendered with Part B only; they carry no dd3 merge or dihedral gate, so they
are dense working drawings rather than the polished cadpartA aesthetic.

## Files

`out/featviz/boiltest_{lego,chair}_consecutive_strip.png` and `_adjacent_overlay.png`,
alongside the cadpartA and gcube pair from Part 1. `out/boiltest.json` now holds all four
scenes.
