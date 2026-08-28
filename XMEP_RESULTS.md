# XMEP — Cross-Model Edge-Prior Invariance (chair, held-out TEST): **PARTIAL**

Thresholds frozen and committed at **`2dd8d8c`, before any lift number was computed**.
Analysis-only and mesh-free: `scripts/xmep_verdict.py` / `xmep_final.py` read jsons
`run_m1b.py` already wrote; the detector import lives in the method/seed path
(`scripts/cmepi_cache_edges.py`), never in the eval. Chair held-out TEST. Protected temporal
manifest re-verified **332/332 OK, 0 failures**. Additive only — no `urs_*`, `teed_*` or
NG-MEC artifact was altered.

## Headline

| | |
|---|---|
| detector | **PiDiNet** (primary; DexiNed also reported) |
| weights | `ext/pidinet/weights/table5_pidinet.pth`, config `carv4`, `sa=True`, `dil=True` |
| sha256 | `80860ac267258b5f27486e0ef152a211d0b08120f62aeb185a050acc30da486c` |
| size | 2 871 148 bytes |
| citation | Su et al., *Pixel Difference Networks for Efficient Edge Detection*, ICCV 2021 |
| **PiDiNet LIFT_P** | **+0.0277** |
| TEED chair reference | +0.0607 |
| **fraction of TEED** | **0.456** |
| frozen bands | GO ≥ 0.70 · NO-GO < 0.30 |

### CALL: **PARTIAL** — the mechanism transfers, but at roughly half strength.

Not a TEED-specific artifact: PiDiNet's lift is positive, moves the frontier **outward**, and
sits comfortably above the NO-GO band. But it does not reach the 0.70 bar that would license
"learned-prior seeds generalize" without qualification.

## A metric mis-specification in my own frozen script — read this before the numbers

The scorer I froze at `2dd8d8c` measured LIFT_P as **points / pull+prune[tuned]**, with the
Pareto-envelope lower bound, over the **full** canny frontier (f ≤ 1.00). Under that variant
PiDiNet scores **+0.0583 = 0.961 → GO**.

That variant is **not the metric the +0.0607 reference came from**, so comparing it against a
threshold derived from +0.0607 is apples-to-oranges — and generous: it scores TEED itself at
+0.0800, ~32 % above the reference it is being normalised by.

The published +0.0607 is reproduced **exactly** by:

- **segments** / `pull+prune[tuned+len]`
- **interpolated** canny P at the same recall (not the envelope)
- rows beyond canny's reach **excluded**
- canny frontier restricted to **f ∈ {0.15, 0.22, 0.30, 0.35, 0.40, 0.45, 0.50}**

which returns **teed05 = +0.0607 at f = 0.40, segP 0.6148, segR 0.7207** — byte-matching
`RECALL_RESULTS.md:198`. `xmep_spec.md` mandates "the SAME frontier-outward lift used for
TEED on chair", so **that** is the primary metric and the spec-compliant answer is PARTIAL.

I am not standing on "I froze it first". The freeze protects against fitting a threshold to a
result; it does not make a mis-specified metric correct. Both numbers are reported.

## Per-arm frontier table (chair TEST, f-band [0.22, 0.50])

| arm | **LIFT_P (spec metric)** | frac | call | LIFT_P (frozen variant) | frac | call |
|---|---|---|---|---|---|---|
| teed05 *(reference)* | **+0.0607** | 1.000 | GO | +0.0800 | 1.319 | GO |
| teed09 | +0.0424 | 0.698 | PARTIAL | +0.0127 | 0.209 | NO-GO |
| **pidinet_native_0.5** | **+0.0277** | **0.456** | **PARTIAL** | +0.0583 | 0.961 | GO |
| pidinet_native_0.9 | +0.0130 | 0.214 | NO-GO | +0.0305 | 0.502 | PARTIAL |
| dexined_native_0.5 | +0.0163 | 0.269 | NO-GO | +0.0393 | 0.648 | PARTIAL |
| dexined_native_0.7 | +0.0338 | 0.557 | PARTIAL | +0.0576 | 0.949 | GO |

PiDiNet's best operating point under the spec metric: **f = 0.40, segP 0.5883, segR 0.7150**.

### Gate directions — consistent with TEED
At matched f the PiDiNet arm moves the same way TEED does: recall **up**, precision drop
**modest**, frontier **outward** (LIFT_P > 0). All three direction checks pass, so this is a
genuine outward frontier move, not a precision-for-recall trade the f dial could have bought.

## The finding that complicates the simple story

**Threshold choice inside one detector matters more than detector identity.** Under the spec
metric, TEED itself spans +0.0607 (thr 0.5) down to +0.0424 (thr 0.9) — and under the frozen
variant it spans +0.0800 down to **+0.0127**, which would be **NO-GO for TEED**. The spread
across the two thresholds of a single detector is comparable to, or larger than, the spread
across detectors at matched threshold.

Two consequences, both honest:

1. It **supports** the generality claim in the weak form: no detector is special; what varies
   is where you set the operating point. DexiNed at 0.7 (+0.0338) beats PiDiNet at 0.5
   (+0.0277), and PiDiNet at 0.5 beats TEED at 0.9 under the frozen variant.
2. It **undercuts** any single-number headline, TEED's +0.0607 included. That number is one
   detector at one threshold on one scene, and a same-detector threshold change moves it by
   more than the PiDiNet-vs-TEED gap.

## Verdict against the frozen bands

| | spec metric | frozen variant |
|---|---|---|
| PiDiNet fraction | 0.456 | 0.961 |
| GO (≥ 0.70) | no | yes |
| NO-GO (< 0.30) | no | no |
| **call** | **PARTIAL** | GO |

**Reported call: PARTIAL.** No spin: the paper may claim that a frozen zero-shot learned edge
prior other than TEED also moves the chair frontier outward — that is measured and holds for
PiDiNet (+0.0277) and DexiNed (+0.0338 at thr 0.7). The paper may **not** claim the lift is
detector-invariant at full strength; at matched default threshold PiDiNet recovers 46 % of
TEED's chair lift.

## Invariants

| invariant | status |
|---|---|
| thresholds frozen before any lift computed | held — `2dd8d8c`, no `xmep_*` artifact existed |
| mesh never in the method path | held — XMEP scripts are analysis-only; detector import is in the seed path |
| held-out TEST only | held — chair TEST, same split as the TEED chair run |
| temporal manifest no-regress | **332/332 OK**, 0 failures |
| new artifacts, `xmep_` prefix | held |
| no `urs_*` / `teed_*` touched | held — read-only reuse of existing `m1b_chair_tc_*` jsons |
| no detector-specific tuning | held — zero-shot cached edges, same native threshold family (0.5 / 0.9) TEED was run at |

**Artifacts.** `scripts/xmep_{verdict,final}.py`; `out/xmep_verdict.json`,
`out/xmep_verdict_*.json`, `out/xmep_final.json`, `out/xmep_published_metric.json`,
`out/xmep_published_metric_reproduced.json`.
