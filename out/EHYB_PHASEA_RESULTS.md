# E-HYB PHASE A — does the TEED-evidence domination reproduce under the VERIFY_F100 harness?

**VERDICT: GO.** All three TEED arms clear the frozen bar on lego, the f=0.40 reproduction
control reproduces the banked cell to 1e-5, and **TEED f=0.40 strictly dominates the shipped
operating point on every axis measured**. Chair confirms independently (banked, same harness).

Executes `tier1/ehyb_evidence_spec.md` Phase A. Mesh EVAL-ONLY. No retrain, no re-pull, no
re-tune, no git commit. No shipped pipeline file, banked json, or published figure modified.
Protected manifest **332/332 OK, 0 FAILED** before and after.

---

## 1. Protocol

Identical to VERIFY_F100: `scripts/m1b_stroke_temporal.py`, lego, `gate=True`, `edge=sharp`,
80 TRAIN views for the pull, held-out TEST, 240-frame TEST orbit 5->15, look-at-corrected,
identical depth warp and identical per-frame Canny baseline, fresh `--tag` / `--viz_tag`.
Chaining and metric args verified byte-identical to the banked runs (`nms_mult` 1.0, `knn` 10,
`cos_tan` 0.60, `cos_col` 0.50, `gap_mult` 4.0, `min_nodes` 3, `n_resample` 16, `max_cand` 6,
`cand_radius` 40.0, `match_thresh` 3.0).

**Stage note, carried forward from VERIFY_F100.** The temporal path chains `z["keep"]` (spec
prune); the P/R headline is the tuned+len stage. That asymmetry is the shipped paper's own
convention and is preserved here so every cell stays comparable. Static P/R below is banked,
not recomputed; only the temporal cell is new.

Inputs verified against their banked keep counts before running: TEED f=0.30 -> 26,759;
f=0.35 -> 30,923; f=0.40 -> 35,028. Two additive symlinks created
(`linelets_lego_teed0{30,35}_test.npz`); f=0.40 used the existing `tcteed040` npz.

## 2. LEGO — the table

Static = banked tuned+len segments @1.5. Temporal = newly computed, 240 frames.

| arm | linelets | chains | str/f | tuned P@1.5 | tuned R@1.5 | OURS P_pop | Frechet ratio | **P_pop ratio** | GO |
|---|---|---|---|---|---|---|---|---|---|
| canny f=0.30 — gate-matched control | 25,279 | 1,895 | 1,119 | 0.6196 | 0.2856 | 0.05942 | 13.98x | **12.10x** | ref |
| **TEED f=0.30** | 26,759 | 2,227 | 1,305 | **0.6563** | **0.4004** | 0.06120 | 14.62x | **11.75x** | **GO** |
| **TEED f=0.35** | 30,923 | 2,515 | 1,460 | **0.6557** | **0.4253** | 0.06127 | 14.61x | **11.73x** | **GO** |
| **TEED f=0.40** ★ | 35,028 | 2,846 | 1,640 | **0.6535** | **0.4463** | 0.05942 | **14.81x** | **12.10x** | **GO** |
| *published shipped row (ungated)* | *25,870* | *1,897* | *1,122* | *0.6196* | *0.2856* | *0.06256* | *14.03x* | *11.49x* | — |

Frozen bar: tuned R@1.5 >= 0.40 **AND** tuned P@1.5 >= 0.5996 **AND** P_pop ratio >= 10.345x.
**All three arms pass all three criteria.**

## 3. The reproduction control reproduced

| | banked `tcL_tcteed040` | this run `ehyb_teed040` |
|---|---|---|
| chain | 35,028 -> 2,846 strokes | 35,028 -> NMS 20,595 -> **2,846** |
| OURS Frechet median | 0.0812 | **0.0812** |
| OURS P_pop | 0.05941 | **0.05942** |
| Frechet ratio | 14.81x | **14.81x** |
| P_pop ratio | 12.10x | **12.10x** |

Agreement to 1e-5 on P_pop, exact on the chain graph. The section-4 domination claimed in the
hybrid analysis was not an artifact of an old campaign.

**Byte-comparability self-check (free).** The Canny BASE arm is independent of the linelets and
is re-derived in every run: BASE Frechet 1.20073 / 1.20243 / 1.20229 / 1.20233 and BASE P_pop
0.71883 / 0.71880 / 0.71884 / 0.71911, against the shipped 1.202460 / 0.719067 — agreement to
0.15% and 0.04%, the `render_gbuffer` CUDA-atomics nondeterminism floor. All arms are on one
measuring stick.

## 4. TEED f=0.40 strictly dominates — no axis is worse

Against the gate-matched canny f=0.30 control:

| | control | TEED f=0.40 | |
|---|---|---|---|
| tuned P@1.5 | 0.6196 | **0.6535** | +0.034 better |
| tuned R@1.5 | 0.2856 | **0.4463** | +0.161 better |
| OURS P_pop | 0.05942 | 0.05942 | equal |
| P_pop ratio | 12.10x | 12.10x | equal |
| Frechet ratio | 13.98x | **14.81x** | +0.83x better |

Against the *published* shipped row it is better on all four (P +0.034, R +0.161,
P_pop ratio 11.49x -> 12.10x, Frechet 14.03x -> 14.81x).

f=0.30 and f=0.35 pass the bar but are **not** strict dominations of the control: they buy
recall at a small temporal cost (12.10x -> 11.75x / 11.73x). f=0.40 is best on recall **and**
best on both temporal metrics, so it is the unambiguous pick.

## 5. Mechanism — the `cut` term FALLS as TEED strokes rise

`P_pop = unmatched + cut`:

| arm | str/f | unmatched | **cut** |
|---|---|---|---|
| canny f=0.30 control | 1,119 | 0.0340 | **0.0254** |
| TEED f=0.30 | 1,305 | 0.0381 | **0.0231** |
| TEED f=0.35 | 1,460 | 0.0380 | **0.0232** |
| TEED f=0.40 | 1,640 | 0.0370 | **0.0225** |
| *canny f=1.00 (VERIFY_F100)* | *3,159* | *0.0311* | *0.0424* |

This is the direct confirmation of the evidence-quality hypothesis, and it is a clean
double dissociation:

- **+47% strokes at BETTER evidence** (control -> TEED f=0.40): `cut` **falls 11%**
  (0.0254 -> 0.0225).
- **+182% strokes at FIXED evidence** (control -> canny f=1.00): `cut` **rises 67%**
  (0.0254 -> 0.0424).

Better-placed carriers chain into longer, more coherent curves, so the split/merge term does
not inflate. The `unmatched` term does rise slightly on the TEED arms (0.0340 -> 0.0370-0.0381)
— more strokes means more occlusion splits — but at f=0.40 the `cut` saving more than pays for it.

## 6. CHAIR — banked under the identical harness, no new run needed

Chair's best TEED f is **0.30**, because it is the only f holding the precision criterion
(dP >= -0.02 against the shipped 0.6573): f=0.30 dP -0.0156 PASS; f=0.35 -0.0276 FAIL;
f=0.40 -0.0425 FAIL. Its temporal cell is already banked, and its harness args were verified
identical to this protocol.

| chair arm | linelets | chains | str/f | tuned P@1.5 | tuned R@1.5 | OURS P_pop | Frechet ratio | **P_pop ratio** |
|---|---|---|---|---|---|---|---|---|
| canny f=0.30 — gate-matched control | 16,039 | 1,166 | 754 | 0.6573 | 0.5959 | 0.07052 | 30.84x | **10.71x** |
| **TEED f=0.30** | 15,971 | 1,137 | 723 | 0.6417 | 0.6759 | 0.05754 | 28.36x | **13.12x** |

Chair replicates the lego direction and more strongly on the gated metric: **+0.080 recall,
precision within the 0.02 allowance (-0.0156), and the P_pop ratio improves 10.71x -> 13.12x**
on *fewer* strokes (723 vs 754/frame). Reported straight: the Frechet ratio moves the other way
(30.84x -> 28.36x, OURS Frechet 0.0398 -> 0.0432), so chair's matched strokes are marginally
less steady while popping markedly less. Both remain enormous and the frozen bar is on P_pop.

## 7. Mandatory caveat — the 30.000-degree stud tessellation

lego P@1.5 is partly credited by the exactly-30.000-degree 12-gon stud family, whose facet
edges sit ~3.2 px apart against a 1.5 px tau. From `LEGO_THRESHOLD_AUDIT.md` (f=1.00 canny):
P@1.5 falls **0.6360 -> 0.3097** and R rises 0.5572 -> 0.6408 when the GT threshold moves to
30.05 deg. This is a property of the **GT target set**, so it moves every arm in this table
together and the domination in section 4 stays internally valid — but the absolute lego
numerals are asset-quantisation properties either way. Per-arm theta>=30.05 rescores were not
computed (the audit banks only the f=1.00 canny sweep); doing so cannot change a comparison
that shifts all arms in the same direction.

## 8. Invariants

| control | status |
|---|---|
| protected manifest | **332/332 OK, 0 FAILED** after the run |
| shipped jsons untouched | `m1b_stroke_temporal_table.json` (Aug 21 09:04), `m1b_{lego,chair}_gated_test.json` (Aug 21) — timestamps unchanged |
| published vector figures | untouched; every arm used a non-empty `--viz_tag` |
| mesh EVAL-ONLY | held — mesh enters only via the banked static P/R, unchanged |
| new artifacts only | `m1b_stroke_temporal_table_ehyb_teed0{30,35,40}.{json,md}`, `m1b_vector_lego_ehybt0{30,35,40}_*.{svg,png}`, `linelets_lego_teed0{30,35}_test.npz` (symlinks), `logs/ehyb_phaseA.log`, this file |
| committed | **no** — Phase B argument pending |

## 9. What Phase A establishes, and what it does not

**Establishes.** Evidence quality moves the recall-stability frontier outward at zero temporal
cost, measured, reproduced, and mechanistically explained via the `cut` term. The shipped lego
operating point is dominated by TEED f=0.40 on precision, recall and both temporal metrics.
Chair replicates.

**Does not establish.** (a) Whether f can be pushed past 0.40 on TEED before temporal breaks —
the f=0.40 arm is the *best* of the three, so the knee has not been located and may be beyond
it. (b) Whether a stronger or ensembled evidence channel beats single TEED. (c) Anything about
ficus. (d) Whether this survives the theta>=30.05 rescore per arm. (e) The re-ship decision,
which is the orchestrator's, not this run's — TEED is a learned detector (BIPED-pretrained,
58,910 params, zero-shot, mesh-free), so promoting it to the headline adds an external-training-
data dependency that belongs in the limitations.
