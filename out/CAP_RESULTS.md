# CAP — Coverage Attribution Probe (lego)

**Diagnostic only.** No new method, no new score, no new method-path file. EVAL/analysis, so it
reads the GT mesh via `mesh_oracle` as the spec permits. Held-out TEST, stage
`AFTER pull+prune[tuned+len]`, f=1.00 (keep every gaussian). Nothing committed.

---

## Verdict — the frozen gate

> `rho_B2 = |B2| / (|B1| + |B2|)`
> `rho_B2 < 0.30` → **KEEP the 3D carrier**; next method = coverage-preserving pull+prune.
> `rho_B2 >= 0.30` → topology critically absent; pivot to image-space-primary candidate injection.

| lego, held-out TEST | ρ_B2 |
|---|---|
| **spec-literal (B0 excluded from the denominator)** | **0.0799** |
| with B0 folded into B1 | 0.0483 |
| visible-gaussians-only sensitivity | 0.2934 |

**==> `rho_B2 = 0.0799` on lego, far below 0.30. The LOW branch fires: KEEP the 3D carrier.**
**Do NOT pivot to image-space candidate injection.** The verdict is robust — all three readings,
including the most adverse sensitivity, are below the gate.

The stronger form of the same finding: **`|B2|` is only 1.31 % of lego's miss-set, and that is
*below chance*.** A "true void" test (`d_raw > 3.0 px`) fires on **8.0 %** of uniformly random
foreground pixels on the same views. Missed crease loci are therefore **less** likely to sit in a
representational void than an arbitrary point on the object. Lego's recall ceiling is not caused by
absent topology.

---

## 1. Reproduction control

The miss-set must be the one that produces the published recall, or nothing below means anything.
The probe recomputes recall with the same rasteriser, the same GT crease pixels and the same tau
that `run_m1b.eval_segments` uses:

| scene | R@1.5 recomputed here | published (ECO §1 / CMEPI table) |
|---|---|---|
| lego | **0.5572** | 0.5572 |
| chair | **0.7908** | 0.7908 |

Exact on both scenes. The miss-set is exactly `{GT crease pixels : sdt > 1.5}` at the headline
stage.

*One enabling change was needed:* the saved linelet npz stored only the **spec** prune mask, so the
**tuned+len** headline stage was not reconstructible from disk. `run_m1b.py` gained an opt-in
`--dump_tuned` flag (default off ⇒ un-flagged runs write byte-identical output) and f=1.00 was
regenerated for both scenes under a private `_cap_` tag. No existing artifact was overwritten.

---

## 2. Attribution

Classes as specified: **A** `d_pool ≤ 1.5` (a candidate existed; pull+prune discarded it);
**B1** `d_pool > 1.5` and `1.5 < d_raw ≤ 3.0` (gaussian nearby, off-registration);
**B2** `d_pool > 1.5` and `d_raw > 3.0` (true void). `d_pool` / `d_raw` are exact continuous
nearest-neighbour distances (cKDTree over projected uv), not pixel-quantised.

**A case the spec does not name, reported separately rather than folded silently:**
**B0** = `d_pool > 1.5` **and** `d_raw ≤ 1.5` — a gaussian *is* within 1.5 px in the raw `.ply` but
is not in the scored pool, i.e. **de-floatering removed it**. Since `pool ⊂ raw`, this case is
reachable and non-empty. It is representation-present and recoverable, so it belongs with B1 in
spirit, but the spec's ρ_B2 denominator does not mention it. Excluding it (spec-literal) *inflates*
ρ_B2; folding it into B1 *deflates* it. Both are reported; both are far below the gate.

| | **lego** | | **chair** *(reference)* | |
|---|---|---|---|---|
| | count | % of miss-set | count | % of miss-set |
| GT crease px | 409,751 | | 120,655 | |
| **missed** | **181,385** | **44.3 %** of crease set | **25,686** | **21.3 %** |
| A — extraction loss | 132,142 | **72.85 %** | 20,048 | **78.05 %** |
| B0 — removed by de-floatering | 19,491 | 10.75 % | 2,027 | 7.89 % |
| B1 — registration-recoverable | 27,375 | 15.09 % | 3,364 | 13.10 % |
| **B2 — true void** | **2,377** | **1.31 %** | **247** | **0.96 %** |
| ρ_B2 (spec-literal) | | **0.0799** | | 0.0684 |

Distance distributions over the miss-set:

| | lego median | lego p90 | chair median | chair p90 |
|---|---|---|---|---|
| `d_pool` | 0.90 | 2.67 | 0.86 | 2.08 |
| `d_raw` | 0.73 | 1.82 | 0.67 | 1.71 |

Pool sizes: lego 99,721 scored candidates out of 166,044 raw gaussians (66,323 removed as
floaters); chair 56,884 of 119,121 (62,237 removed). Kept at `tuned+len`: lego 56,269, chair 37,374.

**Classifier sanity check — passes.** The spec predicted chair's miss-set should be smaller and more
A/B1-dominated. It is: 21.3 % missed vs lego's 44.3 %, Class A 78.05 % vs 72.85 %, and B2 0.96 %
vs 1.31 %.

---

## 3. The Class-A mass must NOT be read at face value

`d_pool ≤ 1.5 px` is only evidence of "a candidate was there" if it is **not** true of an arbitrary
pixel. It nearly is. Measured on the same views, against 20,000 uniformly sampled foreground pixels
per view:

| fraction with `d_pool ≤ 1.5` | missed crease px | matched crease px | **random foreground px** |
|---|---|---|---|
| **lego** | 0.729 | 0.871 | **0.725** |
| chair | 0.781 | 0.898 | 0.697 |

**On lego the Class-A test is essentially vacuous**: it fires on 72.9 % of missed crease loci and on
72.5 % of *arbitrary* foreground pixels — a 0.4-point margin. With ~100 k centres projected into a
640 k-pixel frame the pool is simply dense everywhere, so "72.85 % Class A" should be read as *the
nearest-centre test cannot discriminate at this density*, **not** as "72.85 % of misses are
demonstrated extraction losses". On chair the margin is larger (8.4 points) but still modest.

This does not weaken the verdict — it strengthens the part the verdict actually rests on. ρ_B2 is a
ratio **within Class B**, so it is unaffected by how much mass Class A absorbs. And the B2 test is
informative in the opposite direction: it fires on 8.0 % of random foreground pixels but only
1.3 % of missed crease loci, i.e. **missed creases are ~6× less likely than chance to be in a
void**.

---

## 4. Sensitivities and what could move the answer

| variant | lego ρ_B2 | below 0.30? |
|---|---|---|
| spec-literal (headline) | 0.0799 | yes |
| B0 folded into B1 | 0.0483 | yes |
| visible-gaussians-only | 0.2934 | yes (narrowly) |

The **visible-only** variant restricts both reference sets to gaussians actually visible in that
view, so an occluded back-surface gaussian cannot "cover" a front-facing crease. The spec's wording
("min projected distance to RAW UNPRUNED 3DGS gaussian centers") carries no visibility qualifier, so
the literal reading is the headline — but this variant is the one that moves the number most, from
0.0799 to 0.2934, and it comes closest to the gate without crossing it. **On chair the same variant
gives 0.3311, i.e. above 0.30** — but chair is the reference scene, not the gated one, and chair's
pool already reaches R = 0.7908.

Stated plainly: the verdict is LOW-branch under every reading applied to lego, but if a future
revision of the spec adopted a visibility-qualified `d_raw`, lego would sit at 0.29 — close enough
that the margin should not be treated as large.

---

## 5. What this licenses, and what it does not

**Licensed by the gate:** keep the 3D carrier; the next method is coverage-preserving pull+prune —
relaxing the aggressive NMS/length prune that discards Class A, plus DT-pull relaxation to capture
B1. Consistent with the arithmetic: lego drops 99,721 candidates to 56,269 survivors at
`tuned+len`, i.e. **43.6 % of the pool is pruned away**, and at f=1.00 there is no ranking stage
left to blame — everything lost between the pool and the output is lost in pull+prune.

**Not licensed by this probe:**
- That relaxing the prune will *recover* those loci at usable precision. Class A says a centre was
  nearby, not that a correctly-oriented linelet survives there — and §3 shows the A test barely
  beats chance on lego. The prune exists because it buys precision; loosening it trades back along
  the same frontier this project has spent the whole arc mapping.
- Anything about **chair**, whose ceiling is R = 0.7908 and whose binding constraint ECO already
  showed is ranking quality, not coverage.
- Any estimate of how much recall is actually recoverable. This probe attributes the miss-set; it
  does not predict a post-fix recall.

**Per the spec, the next method is NOT implemented. Stopping at the diagnosis.**

---

## 6. Invariants

| control | result |
|---|---|
| Published 332-file manifest | `sha256sum -c` → **332/332 OK** after the probe |
| Committed artifacts | no committed file rewritten; all outputs use the private `cap_` prefix |
| Mesh in method path | none added; the probe is EVAL/analysis and is the only new file that reads the oracle |
| Held-out TEST | all reported fractions are TEST-split; VAL not used |
| `run_m1b.py` change | opt-in `--dump_tuned` only, default off ⇒ un-flagged runs byte-identical |
| GPU | `CUDA_VISIBLE_DEVICES=1`, u00134 procs only |

**Artefacts:** `out/cap_miss_attribution_{lego,chair}.json` (per-view counts, distance
distributions, null calibration, all ρ_B2 variants), `out/linelets_{lego,chair}_cap_f1.00.npz`,
`out/m1b_{lego,chair}_cap_f1.00.json`, `scripts/cap_miss_attribution.py`.
