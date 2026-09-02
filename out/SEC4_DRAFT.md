# §4 — Interior stability at matched precision and density (DRAFT v1)
*(Contribution A, primary. All numbers from `RESULTS_MASTER.md`; figures Fig 2–5, Tab 1–2.)*

## 4.1 Protocol: three axes, one dominance rule

A temporal-stability claim for a line primitive is easy to fake and easy to dismiss: a
method can look stable by drawing fewer lines or blurrier lines. Our protocol closes
those doors — precision and pixel-density are matched jointly — but we name what it does
not close: matched density is not matched *coverage* (§5.1 shows creases with no carrier
at all, which our lines cannot ink at any density), so the comparison certifies stability
of what is drawn, not equivalence of what is drawable. Every method — ours and every baseline — is swept
over its acceptance threshold to trace an operating curve over three axes: precision
(P@1.5 against held-out GT creases), line density (rendered line-pixels per frame), and a
pixel-pooled stability statistic. Stability is compared **only at shared operating
points**: a baseline point counts iff some point of ours matches or beats it on *both*
precision and density; the reported advantage is the *minimum* ratio over all such
dominating points. The stability statistic itself is pooled per pixel, not per line: every
ON line-pixel of frame *t* is forward-warped by the exact rigid flow (rendered depth plus
the two camera poses — the same operator for every method), and the distance transform of
frame *t+1*'s line mask is read at the landing pixel; distances are pooled over all 239
transitions of a 240-frame trajectory. There is no matching step and no per-line
normalization, so a vanished line is charged automatically, and a sparse "sticky" line set
cannot be flattered. All methods are restricted to the object interior (α>0.5, eroded
2 px), which removes the silhouette warp-drop confound at source for everyone (warp-drop
≤0.1 % throughout).

## 4.2 Against memoryless per-frame detection

At every shared operating point on both scenes, our projected object-space lines flicker
**≥9.8×** less than per-frame Canny and PiDiNet (pixel flicker, 1 px-tolerant XOR/union;
Fig 2). The more telling observation is *how* the two families traverse their operating
curves: our pooled pop-rate is **invariant to the acceptance threshold** (P(d>2 px) stays
within 0.0042–0.0049 across the entire sweep on chair) — stability is a property of the
object-space parameterization, not of which lines are kept — while the per-frame
detectors *destabilize* as they sparsify (PiDiNet at thr 0.9 pops 3× more than at 0.1).
One pre-registered gate in this comparison failed, and we report it rather than re-tune
it: the pooled-*mean* statistic's advantage drops to **2.42×** at the sparsest
high-precision Canny point, below our frozen 3× bar. The dissection (Tab 2) shows why the
statistic, not the stability, collapses: our lines are static 3D polylines whose true
inter-frame drift is zero, so their pooled mean sits at the shared ~0.28 px
rasterization/warp quantization floor (p95 = 1.00 px, threshold-invariant), and a mean
over a floor-dominated distribution compresses ratios at sub-pixel motion. The floor-free
statistics at the *same* point read 12.8× (pop) and 12.2× (flicker). We quote pop and
flicker as primary and disclose the mean-statistic collapse.

## 4.3 Against an oracle-flow temporally-accumulated ceiling

The strongest objection to §4.2 is that per-frame detection is a strawman: a reviewer's
baseline would warp and accumulate edges over time. We therefore built the strongest
member of that family we know how to construct — an EMA accumulator
(A_t = α·warp(A_{t−1}) + (1−α)·E_t, rethresholded, α up to 0.85) driven by the **exact
rigid flow** with an occlusion-aware fallback, i.e. an oracle upper bound on every
estimated-flow variant — and swept it on the same three axes (Fig 3); the oracle claim covers the flow *input*
only — we make no claim over accumulator designs beyond this EMA family. Accumulation
genuinely helps the 2D baselines. It does not close the gap on the pooled pop-rate
P(d>2 px) — the floor-free statistic §4.2 motivates: the worst shared advantage per
condition is **5.19×** (chair·orbit), **5.49×** (chair·spline), **8.35×** (lego·orbit),
and **1.72×** (lego·spline); §4.4 decomposes where this advantage lives and how much of
the baseline's residual is its own accumulator drift. The shared operating points sit at
P@1.5 0.28–0.59 on chair (9 and 8 of 21 baseline points shared) and 0.62–0.64 on lego (3
and 5 of 21) — on lego the baseline's highest-precision configurations are not dominated by any
of our points and are therefore outside the comparison, a truncation the dominance rule
imposes by construction and we report rather than hide. The last cell breaches our frozen 2× bar and
we keep it as the headline of this subsection rather than a footnote: **1.72× is the
reported floor of the claim — a breached pre-registered gate, not a designed margin** —
measured against a baseline whose flow input no practical system can exceed, in the
single condition that maximizes occlusion flux.

## 4.4 The operational envelope

Where does the advantage live, and where does it stop? Decomposing the worst cell by
region (Fig 4): the advantage is **interior** — pop-rate 0.0214 vs the accumulator's
0.0425 (**1.98×**) over the 93–97 % of line-pixels away from occlusion boundaries — and it
*reverses* inside disocclusion regions, where our rate (0.407) is worse than the
baseline's (0.300): our visibility test splits chains at occlusion boundaries and the run
endpoints shift. We disclose this rather than a reviewer discovering it. A pre-registered
mechanism gate — "≥60 % of the accumulator's residual popping lies in disocclusion
regions" — came back **33.3 %** (NO-GO): the accumulator's residual is diffuse interior
EMA drift, not a disocclusion-correspondence failure, so this paper makes **no**
mechanism claim about *why* 2D accumulation trails; the bound is empirical. The envelope
is nonetheless predictable: the single sub-2× cell is exactly the condition (micro-relief
geometry × non-uniform multi-axis motion) where per-frame line-pixel turnover is dominated
by occlusion-boundary churn.

## 4.5 Stroke-level corroboration

The pixel-pooled results above are corroborated by the independently built stroke-level
harness (Tab 1, Fig 5): matched-stroke E_warp ratios of **3.38–21.62×** across 2 scenes ×
3 trajectories against per-frame TEED (scorer and thresholds hash-frozen before any number
existed), Fréchet ratios of 2.43–29.92× against per-frame Canny, and — most legibly —
stroke *survival*: object-space strokes persist for 37–183 frames on average where
per-frame strokes persist for 1.0–1.5 (P(lifetime>32): 0.29–0.83 vs 0.005–0.009). Our
stroke residual falls in proportion to per-frame motion, i.e. it is warp-resampling error
and nothing else; the per-frame baselines saturate at a motion-independent popping floor.
These stroke-level harnesses predate the accumulated baseline and compare against
memoryless detection only; the oracle accumulator exists only in the pixel-pooled
protocol, so the third trajectory is covered at stroke level but not against
accumulation.

*(Scope reminder for the section header: frozen 3DGS, static NeRF-synthetic scenes, known
poses; see §6. The precision these curves operate at is itself bounded — §5 characterizes
that boundary.)*
