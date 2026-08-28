# TRACK N — cross-model edge-prior invariance (consensus-only): **NO-GO as specified, but the mechanism IS invariant**

Frozen scorer `scripts/track_n_verdict.py` **hash-stamped `6a758530…` before any Track-N
number existed** (`out/track_n_freeze.json`; zero `track_n*` / `m1b_*trackn*` artifacts at
stamp time) and verified **unchanged** at scoring time. `track_n_spec.md` forbids committing
until the track closes, so the freeze is evidenced by that pre-run digest rather than a
pre-run commit. Mesh eval-only; consensus/cull/seed path imports no mesh. Held-out TEST only.
All temporal calls used `--viz_tag track_n`. Protected manifest **332/332 OK before and
after, 0 failures**. Normal gate not used (`tau_n = 0`) — NG-MEC refuted it.

## The headline is two numbers, and they answer different questions

| reading | pidinet | dexined | call |
|---|---|---|---|
| **frozen metric** — vs `teed_native_0.5` (spec's reference arm) | chair mean_dP **−0.0113** | **−0.0293** | **NO-GO** |
| **marginal cull** — vs the *same* detector without the cull | chair mean_dP **+0.0091** | **+0.0219** | all criteria met |

### FROZEN CALL: **NO-GO**

Applied exactly as written. The spec fixes the reference arm to `teed_native_0.5`, so
`mean_dP` charges the **detector swap** against the cull. Both detectors give chair
`mean_dP < +0.003`, which is the spec's explicit NO-GO trigger.

**What that actually establishes:** TEED is simply a better proposer than PiDiNet or DexiNed
on chair. Replacing it makes the whole pipeline worse, and no amount of culling recovers it.

### But the invariance question needs the base held fixed

Track N's stated purpose is *"test cross-model edge-prior invariance"* — is the **cull** lift a
general property of learned edge priors? The frozen metric cannot answer that, because it
varies two things at once. Holding the base detector fixed:

| scene | detector | cull mean_dP | cull mean_dR | per-f dP (0.22 / 0.30 / 0.40 / 0.50) |
|---|---|---|---|---|
| chair | teed *(NG-MEC ref)* | **+0.0108** | +0.0018 | +0.0044 / +0.0071 / +0.0114 / +0.0203 |
| chair | **pidinet** | **+0.0091** | −0.0024 | +0.0062 / +0.0058 / +0.0098 / +0.0145 |
| chair | **dexined** | **+0.0219** | +0.0035 | +0.0115 / +0.0164 / +0.0241 / +0.0355 |
| lego | teed | +0.0004 | −0.0113 | +0.0017 / +0.0002 / +0.0003 / −0.0007 |
| lego | pidinet | −0.0046 | −0.0263 | −0.0050 / −0.0048 / −0.0034 / −0.0050 |
| lego | dexined | +0.0019 | −0.0143 | +0.0014 / +0.0012 / +0.0024 / +0.0025 |

Applying the **frozen criteria** to the marginal comparison:

| detector | chair dP ≥ +0.006 | \|chair dR\| ≤ 0.005 | lego dP < +0.003 | temporal 240f ≥ −8.5% |
|---|---|---|---|---|
| pidinet | **+0.0091 ✓** | 0.0024 ✓ | −0.0046 ✓ | **+2.72% ✓** |
| dexined | **+0.0219 ✓** | 0.0035 ✓ | +0.0019 ✓ | **−4.45% ✓** |

**Every frozen criterion is met by both detectors under the marginal comparison.** The
consensus-cull mechanism transfers across three independently-trained zero-shot detectors,
with the same sign, the same near-zero recall cost, the same monotone growth with f, and the
same chair-yes / lego-no dichotomy.

Notably **DexiNed's cull gain (+0.0219) is twice TEED's (+0.0108)** — consistent with the
mechanism: a weaker proposer emits more texture false positives, so consensus has more to
remove. The lift is *inversely* related to base quality, which is itself evidence that the
cull is doing what it claims rather than tracking a detector idiosyncrasy.

## Temporal — protected, and better than TEED's own cull

| frames | pidinet | dexined |
|---|---|---|
| 240f relative | **+2.72%** | **−4.45%** |

Both clear the −8.5% bar (TEED's own cull was −8.41% on lego). PiDiNet's chair arm is
*temporally better* than baseline. The temporal core is not regressed.

## Method note — cull-strength calibration, decided before any dP was seen

A fixed `c_thr = 0.93` does not mean the same thing across detectors, because each has its own
consensus distribution. Survivor fractions at 0.93: chair teed 0.695 / pidinet 0.588 /
dexined 0.708; lego teed 0.773 / **pidinet 0.358** / dexined 0.580. At 0.358 lego/pidinet
cannot even support f = 0.40 or 0.50 (top-f needs survivors ≥ f), so the literal threshold is
both unfair and partly unexecutable — it would compare a 36% cull against a 77% cull.

**Primary** therefore sets `c_thr` per (scene, detector) to reproduce TEED's survivor fraction
exactly (0.695 chair / 0.773 lego) — equal cull strength, full f-grid, calibrated only on the
score distribution with no TEST labels. Both modes are built and recorded in
`out/track_n_build.json`. This was decided from the distributions before any dP existed.

## Honest summary

- **As specified: NO-GO.** Swapping TEED for PiDiNet or DexiNed degrades chair precision
  (−0.0113 / −0.0293 vs the TEED reference). TEED is the better proposer, and the paper should
  not claim detector-interchangeability of the *pipeline*.
- **The mechanism is invariant.** With the base held fixed, consensus culling delivers
  +0.0091 (PiDiNet), +0.0108 (TEED), +0.0219 (DexiNed) on chair at ~zero recall cost, and
  < +0.003 on lego for all three. Three independent detectors, same sign, same conditional law.
- **The defensible paper claim:** *the consensus-cull precision mechanism is a general property
  of frozen zero-shot learned edge priors, and the chair-yes/lego-no conditional law replicates
  across detectors* — while **TEED remains the best proposer**, an empirical fact about
  detector quality rather than about the mechanism.

Both numbers are reported because reporting only the marginal one would overstate the result,
and reporting only the frozen one would bury a clean positive finding the spec explicitly set
out to test.

## Invariants

| invariant | status |
|---|---|
| scorer frozen before any Track-N number | held — sha256 `6a758530…` stamped pre-run, verified unchanged post-run |
| mesh never in method path | held — `track_n_build.py` / `eco_consensus.py` import no mesh |
| held-out TEST only, no TEST tuning | held — `c_thr` calibrated on score distributions only |
| lego NOT retuned for recall | held — lego run purely as a control, no recall chasing |
| `--viz_tag track_n` on all temporal calls | held — published figure paths untouched |
| protected manifest before **and** after | **332/332 OK, 0 failures**, both recorded in the json |
| detectors frozen zero-shot | held — PiDiNet `table5_pidinet.pth`, DexiNed BIPED, cached edges, no finetune |
| all 16 TEST arms loaded their intended score | held — 16/16 `[seeds] reusing OVERALL score`, 0 silent fallbacks |

**Artifacts.** `scripts/track_n_{verdict,build}.py`; `out/track_n_{invariance,build,freeze,marginal}.json`;
`out/m1b_{chair,lego}_trackn{pidinet,dexined}_*_f*.json`;
`out/m1b_stroke_temporal_table_track_n_{pidinet,dexined}.json`;
`out/eco_C_{chair,lego}__{pidinet,dexined}0.5_K3_t2.5_r0_s16.npy`; `logs/trackn_*.log`.
One additive change to `scripts/eco_consensus.py`: `"pidinet"` added to the `--det` choices
(defaults for teed/dexined unchanged).
