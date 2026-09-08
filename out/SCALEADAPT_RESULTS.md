# SCALE-ADAPT — falsifying the generality of the shipped extractor with ONE frozen change

**VERDICT: NOT-GENERAL.** The frozen `L_px = 2.681` did not rescue cadpartA. Chair and lego
pass the non-regression leg comfortably; cadpartA misses the recall bar by a factor of three.
**The length-scale overfit is real and measurable (3.2x) but is NOT the binding constraint. It
is a precision/recall dial, not a frontier shift. The binding constraint is the SEED SCORE.**

> **PROVENANCE WARNING, READ FIRST.** This document was rewritten from the session record on
> 2026-09-09 after a working-tree clean (`git checkout` + `git clean`) removed the original.
> The clean also removed the run artifacts: the `--l_px` patch to `scripts/run_m1b.py`, every
> `out/m1b_*_scaleadapt.json` and every `out/m1b_cadpart*.json`. Only the three gitignored
> `out/linelets_{cadpartA,chair,lego}_scaleadapt.npz` survive. **The numbers below are
> faithfully quoted from the run that produced them, but they are no longer re-derivable from
> disk without re-running.** Treat them as a record, not as a live gate, until re-run.

---

## 1. The disease

The pipeline looked overfit to chair and lego. The user forbade per-scene re-tuning outright:
if every new object needs hand-tuned thresholds, there is no generality to claim. So the task
was not to fix cadpartA. It was to design the **falsification of generality** and run it.

## 2. Constants audit — where the world-scale coupling actually lives

The seed score's constants are already mostly dimensionless or pixel-space: `TAU_ANG = 45.0`
deg is physical, `TAU_RESID = 0.005` is relative to z, `RAD_MULT = 2.0` is in median-1NN
spacing units, `DP = 4` and `SIGMA = 16` are pixels. The one constant carrying raw **world**
units into the geometry is the linelet half-length `l`, set in `src/linelet.py` to the median
largest-axis `exp(scale)` over the kNN gaussians, and inherited downstream by
`src/strokes.py` (3D NMS radius and the chaining gap, both multiples of `median(l)`).

## 3. Why median gaussian spacing is the WRONG invariant

Spacing normalises to the reconstruction's own density, which is itself a function of how the
optimiser happened to subdivide. It would make the constant self-referential: a scene that
reconstructs coarsely would get long linelets *because* it reconstructed coarsely. The
quantity the evaluation actually cares about is **apparent size in the image**, because P/R is
measured at a 1.5 px raster tolerance. That argues for a pixel-anchored length.

## 4. THE ONE CHANGE

`l_world = L_px * z / f`, where z is the linelet's median depth over the visible views and f
the focal length. `L_px` is calibrated **once on chair** and then **frozen**. No other constant
may move on any scene. Implemented as an additive `--l_px` flag defaulting to `None`, so every
unflagged run stays byte-identical to the published behaviour.

### Calibration (measured)

| scene | median l_world | median z | median half-length (px) |
|---|---|---|---|
| chair | 0.00960 | 4.090 | **2.681** |
| lego | 0.00973 | 3.876 | **2.814** |
| cadpartA | 0.03078 | 3.725 | **8.632** |

**FROZEN VALUE: L_px = 2.681 (chair). Used unchanged on all three scenes.**

Chair and lego agree to within 5 percent, which is why this went unnoticed. That agreement is
two samples of one accident, not evidence of invariance. cadpartA is 3.2x larger.

## 5. Pre-registration (frozen before any number was looked at)

- **GENERAL** if cadpartA reaches R@1.5 >= 0.45 at P@1.5 >= 0.70 with no cadpart-specific
  tuning, AND chair and lego each regress by < 0.02 in both P and R.
- **NOT-GENERAL** otherwise. Report honestly; do not rescue by tuning.
- Report the FULL P/R frontier per scene, not one operating point, so a near-miss is
  diagnosable. Also report the seed-level ceiling per scene, to separate the length-scale
  overfit (fixable) from the seed-score overfit (deeper).

---

# RESULTS

## 6. Headline (segments @1.5, `tuned+len`) — one frozen L_px, three scenes

| scene | shipped P / R | scale-adapt P / R | dP | dR |
|---|---|---|---|---|
| **cadpartA** | 0.9211 / 0.1584 | **0.8992 / 0.1553** | −0.0219 | **−0.0032** |
| chair | 0.6573 / 0.5959 | 0.6688 / 0.5851 | +0.0116 | −0.0108 |
| lego | 0.6196 / 0.2856 | 0.6287 / 0.2960 | +0.0091 | +0.0104 |

## 7. Verdict against the frozen bars

| leg | requirement | measured | |
|---|---|---|---|
| cadpartA | R@1.5 >= 0.45 at P@1.5 >= 0.70 | **no point on the entire frontier reaches it** | **FAIL** |
| chair | regress < 0.02 in P and R | +0.0116 / −0.0108 | PASS |
| lego | regress < 0.02 in P and R | +0.0091 / +0.0104 | PASS |

**NOT-GENERAL**, driven entirely by cadpartA.

Frontier scan across every keep fraction and both prune stages: cadpartA **NONE** (flat
frontier; best tuned 0.8634/0.1521, best spec 0.8388/0.2073); lego **NONE**; chair reaches it
at keep = 0.90 with P 0.7276 / R 0.4836.

## 8. Why the fix failed — it is a dial, not a frontier shift

Shortening the linelets did what a length dial does on **all three** scenes: raised precision,
lowered recall, at the seed level.

| scene, pre-prune (SEED CEILING) | shipped P / R | scale-adapt P / R |
|---|---|---|
| cadpartA | 0.2480 / **0.4750** | 0.2842 / **0.3879** |
| chair | 0.5612 / **0.7306** | 0.5892 / **0.6953** |
| lego | 0.5289 / **0.4315** | 0.5519 / **0.4124** |

On cadpartA the prune did retain more (spec 3,049 -> 3,104; tuned 2,179 -> 2,524), so the
mechanism predicted in the design was directionally real. But each surviving linelet now draws
about 3x less ink, and the two effects cancelled to **dR = −0.0032**.

**The hypothesis is falsified.** The prune's 31 percent retention on cadpartA, against 85 to 94
percent on chair and lego, was never caused by linelet length.

## 9. THE TWO CEILINGS, separated

**(a) Length-scale overfit — REAL but nearly worthless.** The 3.2x discrepancy is genuine and
was previously invisible. Normalising it is harmless-to-mildly-positive on chair and lego and
buys approximately **zero recall** on cadpartA.

**(b) Seed-score overfit — THE binding constraint.** cadpartA seed-level precision is **0.3362
at 1.5 px**: only a third of the 9,743 seeds land near a crease, because the M1a OVERALL recipe
is chair-tuned and places those seeds for just 60 crease edges. The prune is then *correctly*
discarding the other two thirds. Pre-prune segment recall of **0.4750** is a hard ceiling that
nothing downstream can raise, since prune and length modulation only remove.

Corroborating: the chair-optimal seed score reads **AUC 0.446, below chance, on lego**.

**The overfit is deeper than a length scale. Fixing the pipeline's only world-scale constant
changes nothing, because the generality failure lives in the seed score — the one component
that is a hand-weighted combination tuned on a single object.**

## 10. What this finding led to

The follow-up audit (see the GEOLINE line of work) located the constraint one level deeper
still: on cadpartA the **gaussian-centre pool itself** caps at 3D recall 0.2021 at the 1.5 px
equivalent radius, against 0.8431 for a multi-view triangulated candidate cloud on the same
frozen 3DGS (`out/dexprimary_p1b_cadpartA_ref40.json`). A GT-crease-supervised **oracle**
retrain moves that pool recall only to 0.3419. So no seed score over gaussian centres, however
scored, can reach the bar — the container is the limit, not the ranking.

## 11. Invariants

`--l_px` was additive with default `None`; unflagged runs stayed byte-identical, and the
shipped `m1b_{lego,chair}_gated_test.json` were re-read, not re-run. Mesh EVAL-ONLY throughout.
Nothing was committed. See the provenance warning at the top for what survives on disk.
