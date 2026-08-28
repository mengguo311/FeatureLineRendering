# LEGO CEILING AUTOPSY — TEED pixel AUC + recall-ceiling decomposition

**Autopsy, not a gateway.** No aggregation heuristic, no v3 multi-cue combination, no
scoring change was built — that decision was frozen before the numbers were read and is
honoured regardless of them. Eval-only: the GT mesh is read solely by
`scripts/lego_ceiling_autopsy.py` via `src/mesh_oracle`, exactly as `ngmec_v2_cuediag.py`
does; the method path stays mesh-free. Held-out TEST views {5,15,…,95}, no tuning.
Protected temporal manifest re-verified **332/332 OK**.

## Headline: both frozen thresholds land in the middle. Report it straight.

| figure | frozen decision rule | measured | verdict |
|---|---|---|---|
| A | pixel AUC > 0.75 ⇒ "representation disconnect"; ≤ 0.55 ⇒ "photometric blur ceiling" | lego **0.618** | **neither caption applies** |
| B | UNCOVERED ≥ 0.45 ⇒ coverage-bound GO; < 0.25 ⇒ loud NO-GO | **0.3663** | **GO threshold NOT met** |

**The coverage-bound hypothesis is not confirmed at its pre-registered threshold.** The
paper cannot honestly write "lego recall is bounded by frozen-3DGS carrier coverage, not by
our scoring" on this evidence. Coverage *is* the single largest cause of the recall gap, but
it does not carry the majority the hypothesis demanded, and a non-trivial third of the gap is
covered-but-culled — i.e. in principle reachable by a better ranker.

---

## FIGURE A — does TEED see lego creases in 2D? `out/lego_ceiling_figA.png`

ROC-AUC of the **raw TEED sigmoid confidence** at GT-crease pixels vs non-crease pixels.

### Confound controls, measured rather than asserted

| control | what it removes | lego AUC with | without | Δ |
|---|---|---|---|---|
| **C1 depth z-peel** | occluded stud/cavity creases counted as GT where not visible | **0.6178** | 0.5553 | **+0.0625** |
| **C2 interior only** | silhouette contrast (TEED fires hard on any object boundary) | **0.6178** | 0.5873 | **+0.0305** |
| **C3 chamfer band** | positive ≤ τ, negative > 2τ, band discarded | τ=1.0 → 0.6092, τ=1.5 → 0.6178, τ=2.5 → 0.6231 | — | stable |

C1 uses `MeshOracle.visible_crease_uv` (3×3 min \|dz\| cull against the GT mesh depth buffer,
eps 0.015). **Both controls move the number upward by a combined ~9 AUC points**: without
them lego reads 0.5553, indistinguishable from its carrier AUC, and the "TEED is blind"
conclusion would have been an artefact of counting unseeable creases as ground truth. The
controls were not cosmetic.

### Result

| scene | pixel AUC (full controls, τ=1.5) | carrier AUC (`ngmec_v2_cuediag.json`) | pixel − carrier |
|---|---|---|---|
| **lego** | **0.6178** | 0.5503 | **+0.0675** |
| chair | **0.7614** | 0.8542 | −0.0928 |

- **lego = 0.618 falls between both captions.** TEED is not blind to lego creases (0.618 is
  clearly above the 0.500 chance floor) but it is far from the 0.75 that would license the
  "representation disconnect" reading. There is a weak but real 2D signal, and roughly
  0.07 AUC of it is lost on the way to the carrier (0.618 → 0.550).
- **chair = 0.761 sits just over the 0.75 line**, and its carrier AUC is *higher* than its
  pixel AUC (0.854 > 0.761) — on chair the 3D carrier *concentrates* the evidence rather
  than losing it. That asymmetry is the cleanest cross-scene contrast in this figure.

### Sensitivity: NMS thinning destroys the ROC
NMS-thinned AUC is 0.49–0.52 on both scenes, i.e. chance. This is expected and is why the
**raw** probability is the primary signal: NMS zeroes non-maximal pixels, turning the score
into a ridge-peak indicator rather than a confidence. Quoted so the choice is auditable.

---

## FIGURE B — why does recall max out at R = 0.408? `out/lego_ceiling_figB.png`

For every **visible** GT crease point on lego TEST views, classified in the *same 2D pixel
space and at the same τ = 1.5 px* as the `R@1.5` metric, against the frozen vanilla-3DGS
carrier (99 721 gaussians) and the f=0.4 proposal set (39 888 seeds):

| bucket | fraction | share of the 0.592 recall gap | meaning |
|---|---|---|---|
| **COVERED and ranked** | **0.4475** | — | a proposal carrier gaussian is within τ |
| **COVERED but culled** | **0.1862** | **31.5%** | carrier exists, not selected as a proposal |
| **UNCOVERED** | **0.3663** | **61.9%** | no carrier gaussian within τ at all |

n = 1 748 144 visible GT crease points over 10 TEST views. Per-view UNCOVERED range
**0.3215 – 0.4478** — it never reaches 0.45 in *any* single view, so the miss is not a
threshold that a different view sample would have crossed.

Two further readings:

- **The pipeline realises 91.2% of what it covers and ranks** (measured R 0.408 vs
  covered-and-ranked 0.4475). Pull + prune lose only ~4 points. The downstream stages are
  not the bottleneck.
- **3D cross-check** (τ = carrier NN spacing 0.00586, independent of projection):
  UNCOVERED = **0.8501**. This is *much* harsher than the 2D figure and is reported rather
  than suppressed. The two are not comparable: crease points are sampled at ds = 0.0015,
  ~4× denser than the carrier spacing, so requiring a carrier within one spacing in 3D is a
  far stricter test than a 1.5 px hit after projection. **The 2D number is the primary one**
  because it is measured in the metric's own space; the 3D number says the carrier is sparse
  relative to the crease sampling, which is consistent but does not license the ≥0.45 claim.

### Honest verdict on the coverage-bound hypothesis

**NOT CONFIRMED.** UNCOVERED = 0.3663 < 0.45. The pre-registered GO condition fails, and the
"surprising NO-GO" trigger (< 0.25) also does not fire — the result sits in the unlabelled
middle band, which the spec did not assign a caption to.

What can be said honestly:
- Coverage absence is the **largest single** contributor, 61.9% of the recall gap. A claim of
  the form *"the majority of lego's recall gap is carrier-coverage absence"* is **supported**
  (61.9% > 50%).
- A claim of the form *"lego recall is bounded by carrier coverage, **not** by our scoring"*
  is **not supported**: 31.5% of the gap is covered-but-culled, so a better ranker or a
  larger f could in principle address roughly a third of it. That is a real, if bounded,
  algorithmic headroom, and it contradicts the strong form of the ceiling claim.
- The ceiling is therefore **mixed**: predominantly representational, but not exclusively so.

Per the frozen decision this is **not** acted on — no new aggregation heuristic was built.
It is recorded so the paper's wording can be chosen to match what was actually measured.

---

## Constraints honoured

| constraint | status |
|---|---|
| no new aggregation / v3 multi-cue heuristic | held — nothing was built regardless of the numbers |
| mesh eval-only, method path mesh-free | held — mesh read only in `lego_ceiling_autopsy.py` |
| held-out TEST, no tuning | held — TEST {5,15,…,95}; every threshold frozen in the spec |
| new artifacts, `lego_ceiling_` prefix, no overwrite | held — all outputs listed below are new |
| protected temporal manifest | **332/332 OK**, 0 failures |

**Artifacts.** `scripts/lego_ceiling_{autopsy,plot}.py`; `out/lego_ceiling_autopsy.json`;
`out/lego_ceiling_fig{A,B}.png`; `logs/lego_ceiling_autopsy.log`.
Carrier-AUC reference values are read from `out/ngmec_v2_cuediag.json`.
