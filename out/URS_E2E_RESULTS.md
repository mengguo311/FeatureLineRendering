# URS-E2E — does densification convert covered-but-culled lego recall into real gain? **ABORT-NO-GO (temporal)**

Scorer and both thresholds frozen and committed at **`2f9a852`, before any densified number
existed**. Mesh eval-only; the densification/seeding/pull/prune path
(`scripts/urs_e2e_run.py`) imports no mesh. Held-out TEST {5,15,…,95}, nothing tuned on TEST.
Carrier 89 748 pts = exactly the 3× budget cap, **within budget**.

# 1. TEMPORAL — the primary gate, reported first

| frames | densified P_pop ratio | baseline (frozen carrier + TEED) | relative |
|---|---|---|---|
| 30 | **2.18×** | 3.49× | **−37.6 %** |
| 60 | **3.95×** | 5.48× | −27.9 % |
| 120 | **6.86×** | 8.69× | −21.1 % |
| 240 | **10.21×** | 12.10× | −15.7 % |

Fréchet-median ratios, same order: densified 1.75 / 2.71 / 4.64 / 8.64× vs baseline
2.52 / 4.42 / 7.86 / 14.81×.

**MIN P_pop ratio = 2.178× against a frozen gate of 6.0× → ABORT-NO-GO.**
**Per the frozen protocol, P/R was deliberately NOT scored.**

Protected temporal manifest: **332/332 OK, 0 failures** (see §3 — it was broken mid-run and
restored).

### Densification costs temporal coherence at every frame count
This is not a threshold artefact. Against the *baseline it should be compared to*, the
densified carrier is worse at **all four** frame counts, by **−15.7 % to −37.6 %**. The spec's
own stated tolerance was −15 %; the worst point is more than twice that. The mechanism is
visible in the stroke chain: densified linelets chain into **2 858 strokes** from 23 638 kept
linelets — many more, shorter strokes, and more strokes pop.

### An important caveat about the gate itself
**The 6.0× gate would also fail the existing pipeline.** The frozen-carrier+TEED baseline has
min P_pop ratio **3.49×** (at 30 frames), likewise under 6.0×. The 6.0× bar was derived from
the **8.5–13.1× figure, which is the *chair* win**, not lego's — lego's actual baseline range
is **3.49–12.10×**. So the absolute gate is mis-calibrated for lego and, taken alone, would
be an unfair test.

That does **not** rescue the result. The conclusion rests on the *relative* comparison, which
is scene-appropriate and unambiguous: densification degrades lego temporal coherence at every
frame count, worst −37.6 %, beyond the spec's own −15 % tolerance. Both readings — the frozen
absolute gate and the fair relative one — say the same thing. Reported this way so the
mis-calibration is visible rather than silently load-bearing.

# 2. Secondary gate — not evaluated, by design

The spec makes temporal fail-fast: *"ABORT-NO-GO immediately if temporal ratio < 6.0×. Do NOT
proceed to P/R."* No held-out P/R, LIFT_P, per-view dP, or recall-extension number was
computed for the densified arm. `out/urs_e2e_verdict.json` contains no secondary-gate fields.
This is deliberate: scoring P/R after a failed primary gate would invite quoting a downstream
number the protocol says is unreachable.

**What this leaves open, honestly:** URS's coverage result (0.4338 → 0.7617) still stands as
an upper bound, and it remains *unknown* whether that coverage converts into held-out P/R
gain. This experiment did not answer that question — it answered the prior one, whether the
attempt is affordable, and the answer is no at this carrier configuration.

# 3. I broke the protected manifest during this run, and restored it

**What happened.** The first temporal invocation omitted `--viz_tag`. With the default empty
tag, `m1b_stroke_temporal.py` writes its stroke-visualisation files to the *published* paths,
and four of those are manifest-protected. The manifest went to **328/332, 4 failures**:
`out/m1b_vector_lego_{A_ours,B_baseline}.{png,svg}`.

**This was my error, and the guard existed.** The script's own docstring
(`m1b_stroke_temporal.py:217-221`) states: *"`--viz_tag` (default "", i.e. the published file
names bit-for-bit) … Any run that is not re-deriving the published figures must pass a
non-empty `--viz_tag`."* I did not read it before invoking.

**Recovery.** All four files were git-tracked, so the running job was killed and they were
restored with `git checkout --` from HEAD. Manifest verified **332/332 OK, 0 failures**
immediately after, and again after the corrected re-run. The re-run passed
`--viz_tag _urse2e040`, so its figures went to `out/m1b_vector_lego_urse2e040_*` and the
published paths were untouched.

**Blast radius.** Only those four visualisation files were affected — no result json, no
linelet set, no stroke table. The temporal numbers reported above come from the corrected
re-run and are unaffected; the killed run's partial 30-frame figure (2.18×) reproduced exactly
in the clean run, which is a useful consistency check.

# 4. Configuration

| | |
|---|---|
| carrier | URS GO config: TRAIN source views, TEED thr 0.5, K_MIN=1 (no consensus culling), budget 89 748 |
| carrier count | **89 748** (= 3× cap, within budget) |
| seeds this arm | 39 888, matched to the frozen-carrier arm at f=0.40 |
| seed placement | at unprojected TEED ridge positions — **not** snapped to gaussian centroids |
| subsampling | spatially uniform voxel dedup (bisected), never a quality ranking |
| pull+prune | `dt_pull.pull` / `linelet_prune.consensus_prune`, identical config to `m1b_lego_tc_*` |
| kept linelets | 23 638 of 39 888 (59.3 %) → 2 858 strokes |
| temporal config | frames 30/60/120/240, trajectory TEST 5→15, all other args identical to the `tcL_tcteed040` baseline |

## Invariants

| invariant | status |
|---|---|
| scorer + thresholds frozen before any densified number | held — `2f9a852` |
| mesh never in the densification/seed/pull/prune path | held — `urs_e2e_run.py` imports no mesh |
| held-out TEST only, nothing tuned on TEST | held |
| budget ≤ 3× baseline | held — 89 748 = cap exactly |
| protected temporal manifest | **332/332 OK, 0 failures** — broken mid-run, fully restored, see §3 |
| P/R not scored after temporal abort | held, deliberately |

**Artifacts.** `scripts/urs_e2e_{verdict,run}.py`; `out/urs_e2e_verdict.json`,
`out/urs_e2e_build.json`; `out/linelets_lego_urse2e040_test.npz`;
`out/m1b_stroke_temporal_table_urse2e040.json`; `out/m1b_vector_lego_urse2e040_*`;
`logs/urs_e2e_*.log`.
