# ECO — Epipolar-Consensus-Only seed reweighting

**Question (frozen in `tier1/eco_spec.md` before any ECO number existed):** the residual false
positives of a frozen learned edge prior are mostly **view-dependent occluding contours**, not
hallucination. Occluding contours slide non-rigidly across views; true creases are view-stable 3D
loci. Does multi-view **epipolar consensus**, spent **additively** into the M1a ranking vector
(never as a veto, and with **no normal/geometry gate**), cull exactly that FP class and move the
**absolute precision** gate?

Held-out TEST for every headline number. Mesh EVAL-ONLY. Every knob selected on **chair VAL** and
transferred to lego unchanged. Nothing committed.

New code, all additive: `scripts/eco_consensus.py` (METHOD PATH, mesh-free),
`scripts/eco_{score,lam_sweep,table}.py` (analysis / EVAL-only drivers),
`scripts/eco_{band_sweep,m1b,post}.sh`. No existing behaviour changed; no published file rewritten.

---

## Verdict

| leg of the frozen rule | outcome |
|---|---|
| **PRIMARY GO** — P@1.5 ≥ 0.85 **and** R@1.5 ≥ 0.65 at some band f on **both** scenes, **with temporal P_pop ratio ≥ 8×** | **FAIL** on the precision leg alone; on lego also **structurally impossible** (§1) |
| **PARTIAL / PROMISE** — ECO strictly increases P@1.5 at matched R (paired per-view, t>2, ≥7/10 views) on **both** scenes, LIFT_P sign preserved | **MET ON CHAIR, EMPHATICALLY. NOT MET ON LEGO. So, as written ("both scenes"), NOT MET.** |
| **NO-GO** *(three legs)* | precision leg does **not** fire (chair improved, t=+12.73); temporal leg is ambiguous, reported both ways (§7); the **R-collapse leg ("R below 0.60") fires on lego** — but lego's recall is under 0.60 for the base carrier and for every arm in the entire corpus (§1), so it is a property of the scene, not something ECO caused |

**The mechanism works, and it works exactly where the arc's conditional law says it should.**
On chair, spending epipolar consensus additively buys **+0.0146 segment precision at matched f,
t=+12.73, 10/10 held-out views** on the DexiNed carrier and **+0.0143, t=+19.97, 10/10** on the
TEED carrier, without paying recall (segR +0.0030 / +0.0057). *Matched-f and matched-recall are
different measurements and are kept apart throughout:* the matched-**recall** gain at that same
f=0.40 is **+0.0129** (DexiNed) and **+0.0181** (TEED) (§5a). ECO also raises the arm's LIFT_P
above its own carrier's on chair (DexiNed +0.0625 → **+0.0935**, Δ+0.0310; TEED +0.0776 →
**+0.1002**, Δ+0.0226). Both of the spec's mandated ablations
come out as the spec predicted: **consensus (K=3) beats single-view (K=1)** and **additive beats
veto**. On lego it does not work: precision is flat (t=−1.48) and recall is significantly *lost*
(−0.0196, t=−17.49, 0/10 views).

**But the headline the spec was chasing — the absolute gate — is not reached and cannot be reached
by this class of method.** ECO is a re-ranking of a fixed candidate pool; §1 shows why that bounds
it, and the bound is the most decision-relevant result in this report.

---

## 1. The PRIMARY gate is out of reach, and on lego provably so

This was measured **before** any ECO arm was run, from the 308 M1b runs already on disk.

**Best P@1.5 ever achieved subject to R@1.5 ≥ 0.65**, headline stage `AFTER pull+prune[tuned+len]`:

| scene | best P at R≥0.65 | arm | gap to P=0.85 |
|---|---|---|---|
| chair | **0.6513** (R 0.6748) | `ng_epi_t1.5_r0_m3` f=0.30 | **+0.1987** |
| lego | **no operating point with R ≥ 0.65 exists at all** (0 of 126 runs) | — | not expressible |

No run in the corpus has P@1.5 ≥ 0.85 at any stage, any f (corpus max P over all stages: 0.7551
chair / 0.7193 lego). At the **headline stage** the closest any arm has come to the gate corner is
L∞ = 0.1607 (chair) / 0.1857 (lego); allowing *any* stage it is 0.1202 (chair) / 0.1722 (lego).

**The structural bound.** At a fixed keep-fraction f, `n_seeds = round(f·M)` is **bit-identical
across every arm** (verified: 30 (scene,f) cells, 306 runs, zero mismatches; M_chair = 56,884,
M_lego = 99,721). Every arm — ECO included — is a **re-ranking of one identical candidate pool**.
So the f=1.00 point, which keeps *every* gaussian, bounds the recall of every possible re-ranking:

| | f=1.00 (keep everything), headline stage |
|---|---|
| chair | P 0.3606 / **R 0.7908** |
| lego | P 0.6360 / **R 0.5572** |

- **lego: R ≥ 0.65 is unreachable by ANY re-ranking whatsoever** — additive ECO, veto ECO, or a
  perfect oracle. The entire pool yields R = 0.5572 and every f < 1 selects a subset of it. The
  lego half of the PRIMARY gate is therefore not an experimental question.
- **chair: the RECALL half of the gate is inside the pool.** Chair's f=1.00 recall is 0.7908, so
  unlike lego there is no structural bar to R ≥ 0.65. Whether the *precision* half is reachable by
  a perfect re-ranking was estimated by an auxiliary purity-greedy oracle at roughly **P ≈ 0.87 /
  R ≈ 0.72 at f=0.30** — which would be a PASS, and would make chair a ranking-quality failure
  rather than a coverage failure. ⚠️ **That oracle estimate is NOT reproducible from anything saved
  in this repo**: no oracle script or output exists, and the projection from the `prune[spec]` stage
  to the headline stage was never defined operationally. It is recorded as an unverified auxiliary
  estimate, not as a result; nothing else in this document depends on it.

This is reported up front because it reframes what ECO could ever have delivered: on chair it is
chipping at a gap of ~0.20 absolute precision with a mechanism whose own prior (the NG-MEC veto)
measured **+0.024**; on lego the target was unreachable before the first line of code ran.

---

## 2. What was built, and the control that licenses it

For a detector cache, a band (τ, ρ) and a neighbour count K, `src.epipolar_consensus.support_counts`
gives per evidence view t the detector's thinned+thresholded edge set `E_t` and a per-pixel support
count `cnt_t ∈ 0..K` — how many of the K nearest **TRAIN-split** cameras see edge evidence where
the pixel's 3DGS-depth-back-projected ray lands. With the nested sets `E_t^m = E_t & (cnt_t ≥ m)`
and DTs `DT_t^m` (and `DT_t^0` of `E_t` itself):

```
A[i] = Σ_t vis[t,i] · exp(−DT_t^0(proj) / σ)                          all edge evidence
B[i] = Σ_t vis[t,i] · (1/K) Σ_{m=1..K} exp(−DT_t^m(proj) / σ)
C[i] = B[i] / max(A[i], ε)                             ∈ [0,1]
```

`C[i]` is **"of the photometric edge evidence this gaussian actually draws on, what fraction is
multi-view consistent"**. It is threshold-free in m, and it is **normalised by the very evidence it
reweights**, so it does not smuggle in a second copy of the photometric channel: a gaussian sitting
on a strong but view-dependent contour has high A and **low C**, which is precisely the FP class
the spec targets. Measured orthogonality of the frozen field to its own carrier's ranking vector: Spearman
**+0.578** (chair) / **+0.443** (lego). It is meaningfully non-redundant on chair; on lego it is
**appreciably more redundant**, which is consistent with the mechanism failing there.

**Licensing self-check, and it passes on both scenes.** The consensus must be computed on exactly
the edge set the M1a photometric channel consumes, or it is reweighting a score it was not measured
on. `eco_consensus.py` asserts, on the first evidence view of every run:

```
assert np.array_equal(Ev,  FR.photo_edge_map(rgb_path) > 0)      # same edge set
assert np.array_equal(dt0, FR.photo_edge_dt(rgb_path))           # same distance transform
```

Both PASS on chair and lego, for every detector/band/K combination built.

**Spending.** `s = base + λ · _R(C)`, with `_R = rankdata/len` — `final_recipe`'s own transform, and
its own idiom (`g = _R(soft) + 0.5·_R(rq90)`). Consensus enters as one more rank-transformed
channel. **Never as a cull**, and **no normal/geometry gate anywhere** — the refuted half of NG-MEC
is deliberately absent.

*The spec's literal alternative `base·(1+λc)` was measured and dropped:* the base spans a factor of
only 1.615 inside the top 30% but 1019× in the bottom 30%, so a multiplicative form does most of its
reordering where nothing is ever selected. Measured top-f=0.30 churn on chair at λ=0.25: **additive
0.0602 vs multiplicative 0.0045** (0.0063 for the raw `base·(1+λC)` form) — a ~13× difference in how
much the reweight actually moves the selected set.

**Two** consensus constructions were implemented and compared (`--cmode nested|nearest`, §3).

---

## 3. Selection — chair VAL only, then frozen and transferred

Swept on chair VAL: construction ∈ {nested, nearest-edge}, K ∈ {1,3,5}, τ ∈ {1.5,2.5},
ρ ∈ {0,0.2}, σ_c ∈ {4,8,16}, λ ∈ {0.1,0.25,0.5,1,2}. **59 consensus fields were built in total**;
the λ sweep covers **184 cells** (90 additive-nested + 90 additive-nearest + 4 veto) over the
**36 chair ρ=0 fields**. The 18 chair ρ=0.2 fields were built and inspected but not λ-swept (they
are vacuous, below); the remaining 5 fields are the lego and TEED-carrier transfers, which by
design are never swept.

- **ρ = 0.2 is vacuous** and was dropped: the depth band makes support near-universal (C mean
  → 0.93–0.99), reproducing NG-MEC's own finding that the depth-free reading (ρ=7) removes 0.7% of
  pixels. Only depth-anchored ρ = 0 discriminates.
- **The nearest-edge construction lost on VAL** — every one of its 18 configs is VAL-negative
  (best −0.0011) against the nested form's +0.0036. (An independent audit had preferred
  nearest-edge a priori on orthogonality grounds; chair VAL disagreed, and VAL is the arbiter.)
- **FROZEN: nested, K=3, τ=2.5, ρ=0, σ_c=16, additive, λ=0.25.** Transferred to lego unchanged and
  applied unchanged to the second carrier (TEED@0.5).

**An M1b-level VAL confirmation was run — something CMEPI never did and explicitly listed as a
weakness.** At the M1b headline stage on chair VAL, the frozen arm gives dP at matched recall of
**+0.0048 … +0.0129, 4/4 band f positive**. The gain is *larger* at M1b than at the seed stage
(+0.0036), i.e. the pipeline **amplifies** the consensus signal — the opposite of NG-MEC's veto,
which was ~10× weaker downstream than its 2D effect predicted.

---

## 4. Held-out TEST — the absolute gate

Segments, stage `AFTER pull+prune[tuned+len]`, τ=1.5. Bands: chair [0.30,0.50], lego [0.15,0.50].

**chair** — P@1.5 / R@1.5:

| arm | f=0.50 | f=0.45 | f=0.40 | f=0.35 | f=0.30 | gate |
|---|---|---|---|---|---|---|
| DexiNed@0.7 *(base carrier)* | 0.5604/0.7546 | 0.5771/0.7425 | 0.5939/0.7305 | 0.6041/0.7066 | 0.6116/0.6831 | fail |
| **ECO add K=3 (DexiNed)** | 0.5798/0.7600 | 0.5945/0.7496 | 0.6073/0.7293 | 0.6146/0.7121 | **0.6246/0.6875** | fail |
| TEED@0.5 *(base carrier)* | 0.5726/0.7560 | 0.5925/0.7348 | 0.6148/0.7207 | 0.6297/0.6982 | 0.6417/0.6759 | fail |
| **ECO add K=3 (TEED)** | 0.5927/0.7563 | 0.6123/0.7460 | 0.6266/0.7247 | 0.6370/0.7006 | **0.6486/0.6824** | fail |

**lego** — best ECO P@1.5 is 0.6592 at f=0.50 (R 0.4564); R never approaches 0.65, as §1 requires.

**No arm reaches P ≥ 0.85 on either scene.** The best ECO precision at a recall that clears 0.65 is
**0.6486** (chair, TEED carrier, f=0.30, R 0.6824) — **0.2014 short** of the gate. (ECO's highest
precision anywhere is 0.6753, chair TEED carrier at f=0.15, but there R = 0.5543 and the recall leg
fails.)
Against **its own carrier** at that operating point (TEED@0.5, f=0.30: P 0.6417 / R 0.6759),
ECO adds **+0.0069 precision at higher recall** — i.e. it closes about **3.3%** of the 0.2083 gap
to the gate. The DexiNed carrier gains more, **+0.0130** (0.6116 → 0.6246 at f=0.30).

---

## 5. Held-out TEST — dP at matched recall, and LIFT_P

### 5a. dP at matched recall vs the arm's OWN base carrier — the PARTIAL criterion

The base carrier's own f-frontier is the interpolant, so this isolates **what consensus added**
with the detector held fixed.

**chair** (band f):

| arm | f=0.45 | f=0.40 | f=0.35 | f=0.30 | best | n>0 |
|---|---|---|---|---|---|---|
| **ECO add K=3 (DexiNed)** | +0.0272 | +0.0129 | +0.0129 | **+0.0144** | **+0.0272** | **4/4** |
| ECO add K=5 | +0.0188 | +0.0118 | +0.0115 | +0.0132 | +0.0188 | 4/4 |
| ECO add K=1 *(single-view)* | +0.0233 | +0.0091 | +0.0098 | +0.0086 | +0.0233 | 4/4 |
| ECO **veto** c=0.9 *(ablation)* | +0.0215 | +0.0127 | +0.0082 | +0.0076 | +0.0215 | 4/4 |
| ECO **veto** q=0.20 *(transferable ablation)* | +0.0160 | +0.0120 | +0.0061 | +0.0078 | +0.0160 | 4/4 |
| **ECO add K=3 (TEED)** | +0.0303 | +0.0181 | +0.0089 | +0.0103 | **+0.0303** | **4/4** |

**lego** (band f): every additive arm is ≈0 (K=3 best **+0.0017**, 2/6 f positive; K=1 +0.0006,
4/6; K=5 +0.0006, 1/6) and every veto arm is **negative at every f** (c=0.9: 0/6, best −0.0034;
q=0.20: 0/6, best −0.0006).

### 5b. LIFT_P vs the published Canny f-frontier — sign preserved AND increased on chair

| scene | arm | best interp | best envelope |
|---|---|---|---|
| chair | DexiNed@0.7 *(carrier)* | +0.0625 | +0.0817 |
| chair | **ECO add K=3 (DexiNed)** | **+0.0935** | **+0.1012** |
| chair | TEED@0.5 *(carrier)* | +0.0776 | +0.0940 |
| chair | **ECO add K=3 (TEED)** | **+0.1002** | **+0.1141** |
| lego | DexiNed@0.7 *(carrier)* | +0.0305 | +0.0221 |
| lego | ECO add K=3 (DexiNed) | +0.0314 | +0.0232 |
| lego | TEED@0.5 *(carrier)* | +0.0402 | +0.0245 |
| lego | ECO add K=3 (TEED) | **+0.0381** | **+0.0209** |

On chair, ECO does not merely preserve the CMEPI lift — it **adds to it on both carriers**:
**Δ+0.0310** on DexiNed and **Δ+0.0226** on TEED (interpolated; +0.0195 / +0.0201 on the envelope),
5/5 band f positive under both estimators. This is the clearest evidence that epipolar consensus
carries information **orthogonal to** the learned prior rather than duplicating it.

**On lego it does not, and the two carriers disagree in sign.** DexiNed is flat (+0.0305 →
+0.0314, Δ+0.0009) but the **TEED carrier LOSES lift** (+0.0402 → +0.0381, Δ−0.0021; envelope
+0.0245 → +0.0209). "LIFT_P sign preserved" holds on lego, but only in the weak sense that both
remain positive.

---

## 6. Paired per-view significance, and the two mandated ablations

Matched f=0.40, paired over the 10 held-out TEST views, stage `pull+prune[spec]`. The spec's bar is
**t > 2 and ≥ 7/10 views**.

**chair**

| arm vs its carrier | segP mean d | t | views | segR mean d | t |
|---|---|---|---|---|---|
| **ECO add K=3 (DexiNed)** | **+0.0146** | **+12.73** | **10/10** | +0.0030 | +1.74 |
| **ECO add K=3 (TEED)** | **+0.0143** | **+19.97** | **10/10** | +0.0057 | +3.34 |
| ECO add K=5 | +0.0138 | +9.23 | 10/10 | +0.0050 | +2.48 |
| ECO add **K=1** *(single-view)* | +0.0092 | +7.51 | 10/10 | +0.0015 | +1.01 |
| ECO **veto** c=0.9 | +0.0118 | +9.73 | 10/10 | +0.0025 | +1.41 |

**lego**

| arm vs its carrier | segP mean d | t | views | segR mean d | t | views |
|---|---|---|---|---|---|---|
| ECO add K=3 (DexiNed) | −0.0015 | −1.48 | 3/10 | **−0.0196** | **−17.49** | **0/10** |
| ECO add K=1 | +0.0002 | +0.14 | 4/10 | −0.0143 | −6.91 | 0/10 |
| ECO add K=5 | −0.0007 | −0.73 | 5/10 | −0.0213 | −9.24 | 0/10 |
| ECO **veto** c=0.9 | −0.0094 | −3.85 | 0/10 | −0.0710 | −20.50 | 0/10 |
| ECO add K=3 (TEED) | −0.0011 | −1.61 | 5/10 | −0.0153 | −15.35 | 0/10 |

**Ablation (b) — consensus beats single-view.** K=3 (+0.0146, t=+12.73) > K=1 (+0.0092, t=+7.51)
on chair, and K=3 ≥ K=5 (+0.0138). **Confirmed.** K=1 is not "no consensus" — it is one neighbour —
so the margin is the value of *multi*-view agreement specifically.

**Ablation (a) — additive beats veto.** Additive K=3 (+0.0146, t=+12.73) > veto c=0.9 (+0.0118,
t=+9.73) on chair at matched f; on the frontier metric, additive +0.0272 > veto c=0.9 +0.0215 >
veto q=0.20 +0.0160; and on **lego the veto is actively destructive** (segR −0.0710, t=−20.50)
while the additive form is merely flat. **Confirmed on both scenes, in the same direction NG-MEC
found.** The "orthogonal information must be spent additively, not as a veto" law survives this
re-test on new machinery.

*The veto ablation was run twice.* An **absolute** threshold is not a transferable operating point —
c=0.9 culls 23.0% of chair's pool but 32.8% of lego's — so a **quantile-anchored** veto (q=0.20,
culling exactly 20% on both scenes) was added and is the version to quote for cross-scene claims.
Both are reported; both lose to additive.

---

## 7. Temporal no-regress — and an ambiguity in the bar

P_pop ratio = BASELINE/OURS (higher = steadier). ECO arms use `--viz_tag`, so the eight published
`out/m1b_vector_*` figures were untouched.

| arm | 30 | 60 | 120 | **240** |
|---|---|---|---|---|
| chair f=0.30 canny *(published)* | 8.25× | 9.74× | 10.43× | 10.71× |
| chair f=0.30 TEED *(published)* | 8.50× | 11.35× | 12.85× | **13.12×** |
| chair f=0.30 DexiNed *(CMEPI)* | 8.25× | 11.28× | 12.70× | **13.33×** |
| **chair f=0.30 ECO add K=3** | **7.89×** | 10.55× | 11.88× | **12.42×** |
| lego f=0.40 canny *(published)* | 3.44× | 5.30× | 8.11× | 11.61× |
| lego f=0.40 TEED *(published)* | 3.49× | 5.48× | 8.69× | **12.10×** |
| **lego f=0.40 ECO add K=3** | **3.67×** | 5.76× | 8.92× | **12.09×** |

**The spec's "P_pop ratio ≥ 8×" bar is ambiguous and is reported both ways rather than resolved
favourably:**

- **As the 240-frame headline** (where the published "8.5–13.1×" claim lives): chair ECO **12.42×
  PASS**, lego ECO **12.09× PASS**. No regress on lego (12.09× vs TEED's 12.10×, above canny's
  11.61×).
- **As a minimum over all frame counts:** chair ECO is **7.89× at 30 frames**, marginally below 8×.
  But this reading is untenable as a bar, because **the published baselines themselves fail it** —
  lego canny is 3.44× and lego TEED 3.49× at 30 frames.

**The honest statement:** ECO costs a little temporal coherence on chair relative to its own
carrier (12.42× vs DexiNed's 13.33× at 240 frames; 7.89× vs 8.25× at 30) while staying above the
canny baseline. On lego it is marginally better than canny and than DexiNed at 30–120 frames, and
essentially tied with TEED at 240 (12.094× vs 12.105×, i.e. fractionally *below*). This is a real
if small cost on chair — and it is **not** the only place ECO is worse than the arm it modifies:
on lego ECO is worse than its carrier at almost every operating point (§5a, §6).

---

## 8. Controls and invariants

| control | result |
|---|---|
| Published 332-file manifest | `sha256sum -c` → **332/332 OK**, before and after every ECO stage |
| Committed CMEPI artifacts | `git status` shows **no tracked file modified**; `out/cmepi_table.json` and the manifest-protected `out/teedgen_verdict_*.json` / `out/teedgen_perview_*.json` never rewritten (ECO uses a private `_ec_` prefix and always passes `--out`) |
| Consensus edge set == M1a edge set | licensing self-check **PASS**, both scenes, all 59 builds (§2) |
| `n_seeds` identical across arms at matched f | verified — every ECO arm re-ranks one identical pool; ECO can never enlarge coverage |
| Downstream pipeline bit-identical | only `--score` and `--tag` differ; `--edge sharp` DT-pull unchanged in every arm |
| Held-out TEST for headline; VAL for tuning only | all **84** ECO TEST arms have `eval_split=test`; the 15 VAL arms are a separate `_ecv_` prefix and were used only to confirm the chair-VAL selection |
| Mesh isolation | `eco_consensus.py` imports `common/render/visibility/view_split/epipolar_consensus` — none touch the mesh; neighbour pool is TRAIN-split only |
| No normal/geometry gate | none present anywhere in ECO, per the spec's rejection of that half of NG-MEC |

---

## 9. Caveats that must travel with this result

1. **The PARTIAL criterion is written "on BOTH scenes" and is therefore NOT met.** Chair passes by
   a wide margin; lego fails. Reporting this as a PARTIAL pass would require dropping the word
   "both".
2. **The NO-GO precision clause is ambiguous.** "P@1.5 not improved at matched R on *either* scene"
   reads either as "improved on neither" (does not fire — chair is improved at t=+12.73) or "fails
   on at least one" (fires — lego). Under the first reading ECO is a partial success; under the
   second it is a NO-GO. The underlying facts are not in dispute.
3. **The temporal bar is ambiguous and ECO is marginally below one reading of it** (§7), and is a
   little worse than its own carrier on chair.
4. **Consensus is spent AFTER the local-competition term, not inside it.** `base` is the published
   final vector (`_R(soft)+0.5·_R(rq90)+0.5·local_rank`), so C never passes through the local
   competition (a ball of `RAD_MULT = 2.0` median-1NN-spacings) where much of the useful reordering
   happens. Injecting before `local_rank`
   was identified as a likely improvement and **was not run** — it is the single most promising
   untested variant.
5. **λ, and every band knob, was selected on a VAL signal that is weak.** Only **13 of the 90**
   swept chair additive cells were VAL-positive at all (and **0 of 90** for the nearest-edge
   construction), the best was +0.0036, and VAL/TEST rank-correlate at only ~0.45.
   The selection is honest (chair VAL only, transferred unchanged) but it is not a strong selector;
   the M1b-level VAL confirmation in §3 is the better evidence that the frozen choice was sound.
6. **ECO's chair gain is ~3.3% of the gap to the PRIMARY gate.** The mechanism is real and
   significant but small in absolute terms, and §1 bounds how far this class of method can go.
7. **lego's R ≥ 0.65 clause was unreachable before the experiment began** (§1). Any report of the
   PRIMARY gate on lego is a statement about the pool, not about ECO.
8. **The two carriers are not independent.** DexiNed and TEED are both BIPED-trained (CMEPI's
   finding); ECO's chair gain replicating on both is evidence of robustness to the detector, not to
   the training corpus.

---

## 10. Artefacts

| file | contents |
|---|---|
| `out/eco_table.json` | the gate / dP-vs-base / LIFT_P tables of §4–5 |
| `out/eco_perview_{chair,lego}.json` | the paired per-view test of §6 |
| `out/eco_temporal_table.json` | the temporal table of §7 |
| `out/eco_lam_sweep_chair_dexined_{add,add_near,veto}.json` | the chair-VAL selection sweeps of §3 |
| `out/eco_C_{chair,lego}__*.npy` + `out/eco_consensus_*.json` | 59 consensus fields + provenance (band, K, σ_c, cmode, support histograms, C statistics). The licensing self-check is an in-process assert; its PASS line is in `logs/eco_transfer_builds.log` (the band-sweep log greps it away) |
| `out/m1b_{chair,lego}_ec_*.json` | the 84 ECO TEST arms |
| `out/m1b_{chair}_ecv_*.json` | the 15 M1b-level VAL confirmation arms |
| `out/m1b_stroke_temporal_table_eco_{chair,lego}.{json,md}` | temporal runs |
| `scripts/eco_*.py`, `scripts/eco_*.sh` | the code |
