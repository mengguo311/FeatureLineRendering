# HEADLINE TURNTABLE — dd3 carrier vs per-frame Canny, on the metric's own trajectory

`scripts/videoviz.py`. **MESH EVAL-ONLY in the strictest sense: this script reads no mesh at
all.** Object space only, no per-scene tuning.

Rendered on **the metric's own path**, the look-at-corrected arc from camera 5 to camera 15,
240 frames, so the clip and every banked temporal number describe the same motion. The frozen
`stroke_metric` warp/match/pop functions are called directly, so the per-pair numbers come from
the same operator behind the 12.03x.

---

## VERDICT: GO on all five pre-registered visual legs

| leg, worded on the rendered output | result |
|---|---|
| no stroke appears/disappears except at a silhouette crossing | **PASS** |
| no stroke visibly jitters, snakes or changes length | **PASS** |
| stroke-count trace drifts smoothly, no spikes | **PASS** |
| at the marked worst pair, frames indistinguishable apart from camera motion | **PASS** |
| the Canny clip beside it visibly boils | **PASS** |

## 1. The finding the video was built to expose, and it is real

| OURS, per frame-pair | value |
|---|---|
| cut **mean** | 0.00012 |
| cut **p99** | **0.00000** |
| cut **max** | **0.01905**, at pair **120** |
| unmatched mean | 0.0672 |
| unmatched max | **0.2039**, at pair **86** |

**Ninety-nine percent of the 239 frame-pairs have cut exactly zero, and a single burst reaches
0.01905 — 190x the mean, and ABOVE the 0.0102 bar every earlier gate passed on the mean.**

That is precisely the failure mode I argued a mean cannot show, now confirmed empirically.
It does **not** overturn any earlier verdict, because those gates were explicitly written on
the mean. What it does is remove an assumption nobody had checked.

**And the visual check settles it.** cut 0.019 on roughly 50 strokes is about one stroke
splitting. The blow-up of pair 120/121 shows two drawings indistinguishable apart from camera
rotation. **The numerically worst moment in the whole orbit is invisible.** The mean-based bar
was the right instrument here, but it is now verified rather than assumed.

## 2. The unmatched spike is not a popping event either

At pair 86, unmatched hits 0.2039, three times its mean. The blow-up shows **52 runs against
51**, and the two frames are near-identical. So that spike is a warp-and-match operator
artefact, not visible popping.

Worth recording precisely: earlier write-ups attributed unmatched wholly to correct hidden-line
removal. At this pair it is **neither** hidden-line removal nor a visible event — it is the
metric failing to pair strokes that are plainly the same strokes.

## 3. Stroke-count trace: smooth drift, no spikes

| | value |
|---|---|
| range over the orbit | **34 to 59** |
| median consecutive change | **1 stroke** |
| max consecutive change | **4 strokes**, at frame 151 |
| pairs changing by >= 3 | 14 of 239 |
| pairs changing by >= 5 | **0** |

The 34-to-59 range is slow drift as edges wrap out of view across the arc, not flicker. No
single frame ever gains or loses five strokes.

## 4. The contrast

| | OURS dd3 | per-frame Canny |
|---|---|---|
| strokes per frame | **34 to 59** | **373 to 470** |
| P_pop mean | **0.0673** | **0.8100** |
| cut mean | 0.00012 | 0.00193 |

The contact sheet makes it plain: our tiles hold the same clean line structure across the whole
orbit, while the Canny tiles are dense scribble that reorganises completely between samples.
Roughly **8x fewer strokes and 12x lower popping**.

## 5. Deliverables

An encoder check was run first rather than assumed: no `ffmpeg` binary is present, but
OpenCV's `mp4v` writer opens, so **mp4 was produced**. The GIF and contact-sheet fallbacks were
produced anyway.

- `out/featviz/turntable_cadpartA_dd3_vs_canny.mp4` — 240 frames, 24 fps, side by side, with
  the per-frame stroke-count trace beneath each panel and the **worst cut pair marked in red**
- `out/featviz/turntable_cadpartA_dd3_vs_canny.gif` — every 4th frame
- `out/featviz/turntable_cadpartA_contactsheet.png` — every 20th frame, ours beside Canny
- `out/featviz/turntable_cadpartA_worstpair.png` — pair 120/121 blow-up, worst `cut`
- `out/featviz/turntable_cadpartA_worst_unmatched_pair86.png` — pair 86/87 blow-up, worst
  `unmatched`

## 6. Limitations, stated

I blew up the two numerically worst pairs, not all 239. The GO on "no stroke appears or
disappears except at a silhouette" rests on those two plus the count-trace statistics, not on a
frame-by-frame audit of the whole orbit.

The clip covers the camera-5-to-15 arc, **not a full 360 turntable**. cadpart does have a
120-frame `transforms_orbit.json`, but no banked temporal number covers it, so rendering that
would have shown one motion while quoting a figure measured on another.

Carrier is the dd3 carrier of record, 59 strokes, unchanged. The polyhedron-scope limit on the
inherited straightness and crease filters still stands.

## 7. Artifacts

`out/videoviz.json`, `out/videoviz_trace.json`, `out/carrier_dd3_cadpartA.npz`,
`scripts/videoviz.py`, `logs/videoviz.log`.
