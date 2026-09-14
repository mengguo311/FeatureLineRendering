# PROJECT STATUS ANALYSIS — honest, adversarial read of the banked results (2026-09-15)

Written after a multi-day disconnect, from a fresh read of the banked write-ups plus a 15-agent
read-only verification workflow (6 numeric verifiers checking ~90 claims against JSON/log
artifacts, 2 of 3 critics; the 6 refuters and the thesis critic died at the session limit).
The critic findings are therefore un-refuted by a second agent, but the one genuinely new
mechanism they raised (silhouette warp-drop charged as popping on the solids) was spot-checked
directly against the JSON and `src/stroke_metric.py` and holds. Section 4 is the orchestrator's
own synthesis. No code was run for this document beyond reading files.

---

# 1. The current real, defensible result

## 1a. The crown temporal claim, exact scope

The defensible statement is narrower than most of the banked write-ups say:

> On textured objects (chair, lego), object-space strokes bound to a frozen 3DGS are visibly
> more temporally stable than per-frame image-space detection, and this survives matched
> precision and matched pixel density. On untextured solids no visible advantage exists: the
> per-frame baseline is already stable there and draws a more complete drawing than ours.

Where it holds, with the numbers that actually back it:

| Statistic | chair | lego | Source |
|---|---|---|---|
| ink_churn, ours / Canny, consecutive frames | 0.016 / 0.448 = 28.1x | 0.058 / 0.536 = 9.2x | `out/boiltest.json` |
| P_pop ratio, 240f TEST orbit, ungated | 11.35x | 11.49x | `out/m1b_stroke_temporal_table.json` |
| same, silhouette-controlled (fg_only) | 7.01x | 6.49x | same, `control_fg_only` |
| same config, second orbit (VAL 0→10) | 10.18x (−10%) | 8.66x (−25%) | `out/m1b_stroke_temporal_table_etraj_*valorb_ungated.json` |
| PARETO-1 pixel flicker vs memoryless, matched P and density | ≥12.2x | ≥9.78x (PiDiNet only) | `out/pareto_verdict.json` |
| PARETO-2 vs genuinely accumulated oracle-flow EMA | T1 5.19x, T3 5.49x | T3 1.72x; T1 no shared point | `out/pareto2_*.json` |

Corrections the verifiers forced on this bundle:

- **"≥9.8x vs memoryless detectors" is 9.78x**, and on lego it is a PiDiNet-only statement.
  All five lego Canny points are unshared in PARETO-1 because Canny is more precise than ours
  at every density. Under PARETO-2's protocol, where memoryless Canny is shared, lego gives
  7.3x (T1) and 2.8x (T3).
- **"lego-T1 8.35x vs oracle-flow EMA" is against a memoryless baseline.** The α≤0.5 grid rows
  are numerically identical to α=0 because the 0.5 rethreshold makes the EMA a no-op. The
  honest range against accumulated shared points is 1.72x to 9.46x, and lego-T1 has none.
- **"5 of 6 conditions PASS" is wrong**; 4 conditions exist and 3 pass. The paper drafts
  already say 3 of 4; `RESULTS_MASTER.md` and `PARETO2_RESULTS.md` do not.
- **The lego trajectory swing was mislabeled.** `E_LEDGER.md` §8 marks the published lego
  config's −24.6% VAL swing "SAFE", which exceeds E-FMARGIN's own 20% validity gate. The
  E-TRAJ "8.0x SAFE bar" is borrowed from Track O's arm-C spec, not a bar frozen for this
  comparison. Chair is trajectory-robust on two orbits; lego is not closed.
- Minor: the m1b warp-drop figures 19.8%/18.2% are hard-coded literals in
  `scripts/m1b_consolidate.py`; the JSON says 16.1%/14.8%. "12.8x/15.4x" are 12.9x/15.3x.
  "PiDiNet 0.9 pops 3x more" is 1.28x.

Where it does NOT hold, and the new mechanism you need to know about:

- On all five clean solids, the consecutive-frame strips show Canny drawing a complete, steady
  wireframe while ours draws a partial subset. I read the strips myself and agree with BOILTEST
  and TURNTABLE. `VIDEO_RESULTS.md` still records "Canny visibly boils: PASS" for cadpartA
  from an every-20th-frame contact sheet and was never amended.
- **The 10.5x to 20.8x solid P_pop ratios are majority warp-drop artifact, not just identity
  churn.** Every solid temporal run has `fg_only=False`, and the Canny baseline's
  `warp_dropped_frac` is 0.468 cadpartA, 0.406 gcube, 0.675 gicosa, 0.593 gprism, 0.351 gstep.
  Confirmed in `src/stroke_metric.py` `pop_penalty`: `n_dropped_by_warp` is added into
  `unmatched`, so 35% to 67% of the baseline's strokes on each solid are charged as pops
  without ever being compared. The silhouette control that cut lego and chair from 11.5x to
  6.5x was never run on any solid. The rest of the baseline's solid P_pop is the tracer
  re-decomposing junctions, a property of `trace_polylines` (junction split, min_len 4,
  DP eps 1.0), not of Canny.
- The clean-solid ink_churn numbers (cadpartA 6.80x, gcube 3.34x) originally existed only in
  git blob `95f3872:out/boiltest.json`; `scripts/boiltest.py:122` overwrote the live JSON with
  lego/chair. **Resolved 2026-09-15 (HYGIENE item 5):** boiltest re-run over all seven scenes
  into one `out/boiltest.json`, and every solid temporal cell re-run with the silhouette
  control. Results, stroke-identity P_pop ratio vs per-frame Canny, 240-frame TEST orbit:

  | solid cell | uncontrolled (banked) | baseline warp-drop | **fg_only (honest)** | ink_churn ratio |
  |---|---|---|---|---|
  | cadpartA zero-knob (42 strokes) | 10.50x | 0.468 | **4.79x** | 6.82x |
  | cadpartA shipped f=0.30 | 15.28x | 0.468 | **4.93x** | — |
  | cadpartA ribbon B kf0.25 / A2 kf0.35 | 7.62x / 7.51x | 0.468 | **3.36x / 3.82x** | — |
  | cadpartA DexiNed carrier (4,007) | 4.78x | 0.468 | **3.32x** (cut 0.149) | — |
  | cadpartA dd3 carrier (59) | 12.03x | 0.468 | **5.76x** | — |
  | gcube | 20.77x | 0.406 | **7.06x** | 3.34x |
  | gicosa | 13.90x | 0.675 | **5.60x** | 3.10x |
  | gprism | 18.97x | 0.593 | **5.17x** | 1.32x |
  | gstep ship / kf0.22 | 11.24x / 10.74x | 0.351 | **2.80x / 2.17x** (below the 3x trip-wire) | 6.23x |

  Under the control the interior-restricted Canny baseline keeps only 19–127 fragments per
  frame on the solids (most of its ink was silhouette) and OUR P_pop roughly doubles (interior
  clipping cuts our strokes at the eroded boundary). Not re-scored because their carriers were
  never persisted: merge70, de-debris v1, the gicosa-pilot 37-stroke merged carrier. Lego and
  chair boiltest values reproduce within rasteriser drift (9.17x, 28.16x). **On every clean
  solid per-frame Canny is complete and visually stable, and we are not superior there.**

What genuinely survives on solids is an absolute property of our strokes, not a comparison:
P_pop 0.038 to 0.077, cut 0.0000 to 0.0011, warp-drop ≤0.005, cut exactly zero on 99% of
cadpartA's 239 frame pairs (max 0.019 at pair 120, visually invisible), stroke count drifting
by at most 4 per frame. Compactness (23 to 57 strokes vs 271 to 474 Canny fragments) is real
but tracer-dependent. Whether persistent stroke identity is worth anything is asserted in
three places (BOILTEST, PAPER_DRAFT L124, CONTRIB_BOX) and demonstrated nowhere: no
stylization, editing, or texture-mapping experiment exists on disk. The strongest persistence
evidence is the Track P survival curves (mean stroke lifetime 37–183 frames vs 1.0–1.5 for
per-frame TEED), which are chair/lego only.

## 1b. The coverage ceiling

cadpartA, segments at 1.5 px, held-out TEST:

| Operating point | P | R | Provenance |
|---|---|---|---|
| shipped f=0.30 | 0.921 | 0.158 | `logs/cadpartA_m1b.log` only; JSON gone |
| zero-knob f=1.00 spec prune | 0.814 | 0.421 | JSON (n 7,208) |
| A2 consensus prune, kf 0.35 | 0.749 | 0.625 | JSON |
| A2 fine grid, kf 0.33 | 0.770 | 0.616 | **NOT on disk** |
| oracle ceiling on this pool (arm C) | 0.727 | 0.727 | JSON |
| DexiNed triangulated cloud (3D metric) | 0.730 | 0.843 | JSON, key `tri_sup1` (not tri_sup2) |

The "pre-registered target R≥0.60 @ P≥0.75 MET" in commits 4e52b0d and 89393e3 rests entirely
on the fine-grid rows (kf 0.345/0.340/0.330/0.320/0.310), which have no JSON, log, or script
grid (`scripts/geoline_step3.py` KF_GRID contains no 0.33; commit 89393e3 changed only the
.md). On the artifact-backed grid the target is missed by 0.0014 in precision. Either bank the
sweep or drop "MET".

On lego the ceiling is R@1.5 0.557 at f=1.00, with UNCOVERED carrier gaps the largest single
cause (0.3663 of visible GT crease points). The 61.9%/31.5% gap shares in
`LEGO_CEILING_AUTOPSY.md` are relative to the 0.408 re-ranked NGMEC-v2 frontier, not the
0.557 ceiling, and should never be quoted next to it. Across the two textured scenes the GT
crease set itself covers only 37.4% (lego) and 43.1% (chair) of the geometric ≥30° edges
because of split-vertex OBJ topology (`epi/epi_labels_*.json`). Every P/R number in the
project is scored against that subset; on the full geometric set the frozen triangulation's
3D recall is 0.175 lego / 0.598 chair. The lego "213,711-edge 30.000° family" count has no
data artifact (prose and docstring only); the sample-level evidence for a large exactly-30°
family (49% of the miss-set) is solid. Precision at 30.05° is 0.3097, not 0.3004 (0.3004 is
the 45° end of the sweep).

## 1c. The cadpartA visual-first stroke result

The dd3 carrier of record: 59 strokes (42 trunk + 17 fill), arc 14.870 = 1.54x the trunk,
P_pop 0.067, cut 0.0001, 8 join endpoints, and a 240-frame turntable where the numerically
worst pair is visually indistinguishable. It reads as a clean CAD line drawing with sharp
corners. STROKEVIZ's decomposition was the right call: total P_pop says DexiNed-carrier
(4,007 strokes) is 2.2x worse than the STEP3 trunk; the `cut` term says ~780x
(0.1328 vs 0.00017; the write-up's "664x" used rounded values).

Two honest limits: no mesh P/R was ever computed for merge70, dd2 or dd3 (only the input
carriers' P/R is quoted; `out/carrier_dd3_cadpartA.npz` is sitting there ready), and the
"12.03x vs Canny" is the warp-drop-inflated ratio above (baseline `warp_dropped_frac` 0.468 in
`dd3.json`). "Best temporal ratio of any arm built so far" is true only among the four
cadpartA merge arms. The gicosa pilot of the byte-identical pipeline was NO-GO on
completeness: a better cloud (P 0.765 / R 0.969) gave a worse tile (37 strokes, 12 fill)
because gap-filling concentrates the cloud's residual false positives once the trunk has
taken the strong creases. That is a structural property of the trunk-plus-fill architecture,
not a gicosa quirk. The polyhedron-scope limit (min-length, RANSAC straightness, 30° dihedral
gate) is declared and will not survive ficus or chair.

---

# 2. Relationship to the reproduced poster method

**Framing ours as the temporal extension of the poster is not defensible.** The two share one
premise, a frozen vanilla 3DGS with no mesh, and belong to different families:

- The poster as reconstructed (`scripts/poster_repro.py`): five per-frame image-space fields
  computed from the rasterization state (opacity, depth, normal, SH-0 albedo, top-k Gaussian
  IDs with weighted-overlap dissimilarity), rank-max fusion labelled as our stand-in, no
  photographs, no optimization, no 3D primitive.
- Ours: seeds at de-floatered gaussian centres (`src/linelet.py:38-66`), pulled to Canny
  distance-transform fields of the 80 TRAINING PHOTOGRAPHS (`src/dt_pull.py:75-90`,
  `views_pull=80`; `--views 100` is a dead argument under `--pull_split train`), pruned by
  multi-view consensus, chained once in 3D, projected through the 3DGS z-buffer.
  Rasterization state enters only as carrier positions, visibility, and an optional G-buffer
  selector gate (removes 7.8% of photo-Canny pixels on lego). None of the poster's five fields
  is computed or consumed anywhere in our pipeline, and `dt_pull.py`/`linelet.py`
  (commit 1f023c6, 2026-08-21) predate `poster_repro.py` (4d1d02a, 2026-09-14) in this repo
  by 24 days.

The honest one-sentence relationship: **both extract feature lines from a frozen vanilla 3DGS
without a mesh; the poster derives per-frame image-space lines from the rasterization state
itself, whereas ours builds a static object-space stroke set from multi-view photographic edge
evidence anchored on the gaussian cloud and renders it through the 3DGS z-buffer. The poster
is the closest mesh-free per-frame comparator, not a method we extend.**

**The sentence that needs to go.** The comparison figure caption
(`out/featviz/COMPARISON_ours_vs_poster.png`, rendered from `scripts/comparison_fig.py:49-50`)
says:

> "The poster is the baseline our object-space work extends -- view-stable 3D feature lines
> are its own stated future work."

Nothing on disk sources it. No poster PDF, abstract, or bib exists anywhere under
`~/3dgs_line`; `POSTER_REPRO_RESULTS.md` itself says the poster was never seen; the sentence
appears in no write-up and no commit message. The same caption's "(the poster asset)" for lego
is equally unsourced, and the author naming ("Hao and Mukai" on the figure vs "Hao Weiren /
Mukai" in the md) is unverified. Delete the future-work clause until you have the actual
poster in hand.

**The 0.178 / 0.058 / 0.536 stability axis does not support a method ranking.** Confounds, in
order of severity:

1. n=1 scene (lego), 7 adjacent frame pairs (frames 100–107), one orbit, one still view.
2. The fusion is our stand-in, and it is ~62% silhouette by the write-up's own measurement
   (`silhouette_domination.by_q` FUSED 0.62 at q=0.01, measured on the still view, not the
   churn frames). If silhouette ink is stable frame to frame, the composite's interior churns
   at roughly 0.178/0.38 ≈ 0.47, within about 12% of Canny's 0.535. Silhouette share alone
   predicts 1/(1−0.62) ≈ 2.6x of the 3.0x. So 3.0x is a property of outline share, not of the
   poster method. No interior-restricted ink_churn exists for any of the three pipelines.
3. Poster and Canny are ink-matched per frame (`ink_px_fused == ink_px_canny`); our 0.058 is at
   native ink budget (`scripts/boiltest.py` does no matching) and our pixel count is not
   recorded. ink_churn at 1.5 px tolerance is density-sensitive, so 9.2x is not a matched
   comparison. Raw pixel density from PARETO-1 says Canny 50/150 is 1.46x denser than any
   OURS point on chair and comparable on lego.
4. No precision, coverage, interior restriction, or density exists for the composite
   ("mesh EVAL-ONLY is not even exercised"), so it violates the paper's own §4.1 dominance
   rule. Ours on lego is R 0.286; at Canny-matched budget the composite is "essentially an
   outline". An outline-only render vs a 29%-recall interior stroke set is not a stability
   ranking in the paper's sense.
5. The figure shows the rich q=0.05 still (12,784 px) beside a bar measured on ink-matched
   renders (~3.9k px/frame), and shows cadpartA dd3 strokes (a clean solid where Canny is
   visibly stable and more complete) beside a lego number.
6. The reproduction's normal channel is the per-gaussian shortest covariance axis
   (`src/common.py:82`), which this project rates near chance on vanilla 3DGS (lego ribbon
   AUC 0.3875; `src/linelet.py:17-21` "AUC 0.54 ~ chance"). The "top-k is most redundant with
   normal" finding (Jaccard 0.764 at q=0.02) is conditional on that proxy. Not disclosed in
   the md's reconstruction table.
7. Smaller: "every Jaccard is 50–200x its null" is 31x–1700x for non-opacity and only 5–31x
   for opacity; "89.5% full-8 occupancy" and the "five runs, 6431–6517 px" range have no
   artifact; the banked ours/Canny values are hard-coded literals in `poster_repro.py:657`.

**The productive use of the poster reproduction** is (i) as a related-work anchor, phrased as
"closest mesh-free frozen-3DGS per-frame image-space method; ours is object-space", once the
actual poster is obtained and cited; and (ii) as a component hypothesis tied to GEOLINE Step 2:
a per-frame normal-discontinuity field on a 2DGS normal buffer, which is exactly the poster's
channel-3 kind of field, separates crease from prune-survivor off-crease loci on cadpartA at
AUC 0.929 (keep_both TEST; 0.924 keep_only) versus 0.685 on the vanilla-3DGS ribbon
(`geoline_step2_cadpartA.json`). On clean solids, where photo-Canny recall is low (cadpartA
R 0.16–0.42), that field could serve as an extra DT pull target or seed score. Scope it to
clean solids: the same ribbon scores 0.331 on lego, worse than vanilla's 0.388, and it has not
yet moved P/R or the pool ceiling anywhere. The poster's own thinning/fusion rule remains
unknown, so nothing here is a statement about the poster's actual results.

---

# 3. The negative results that bound the contribution

All confirmed against artifacts, with the corrections noted:

- **Retrain KILLED** (`out/xy/xy_expY.json`, `xy_ceiling.json`, `xy_gtdepth_limit.json`).
  Oracle retrain handed GT creases: ΔF1 +0.0156 (0.7833 → 0.7989) against a +0.15 gate.
  Ceiling under a perfect cull moves +0.0001 (0.9552 → 0.9553); exact GT-mesh depth is worth
  +0.0358 (F1 0.8191, both conditions converge). Without the occlusion cull ΔF1 is +0.0002.
  The extractor consumes the 3DGS only as a depth bracket and occlusion cull, so no
  retraining can reach it. The "own-optimum 0.8332/0.8485" robustness rows and the §Y.5
  alpha-band fractions are not on disk; the kill does not depend on them. The controlled
  temporal A arm is a single seed.
- **Line-buffer pivot KILLED** (`out/epi/epi_accum_{lego,chair}.json`). Epipolar accumulation:
  lego AUC 0.698 / R@85P 0.000, structural (deleting the top 5,000 negatives lifts R@85P only
  to 0.055); chair 0.859 / 0.000, knife-edge, since a different negative subsample gives 0.147
  and the top 1,000 negatives removed gives 0.53. Always carry the knife-edge caveat when
  citing chair as a gate failure. Kill mechanism is DexiNed's ~5 px response tail on
  edge-dense surface, not dead zeros (only 11% of lego's miss-set is undetected in every view).
  The first-version lego AUC 0.572 is not on disk.
- **Buffer-edge lift NO-GO, killed by the null** (`out/bufedge_lift.json`). On lego a random
  detector matches the best real buffer (recall gap 0.0012 on the JSON re-run). On cadpartA
  the null reaches 82% of the best buffer's recall. The md tables quote the first 240k run
  (best 0.1625/0.5644, NULL 0.0331/0.4627); the JSON on disk is the disclosed re-run
  (0.1627/0.5652, NULL 0.0325/0.4528). All three legs FAIL either way. The banked DexiNed
  cloud dominates the best buffer arm 4.5x in precision and 1.5x in recall. BUFFEREDGE's
  earlier detection-leg "pass" (2dgs_normal 0.987 cadpartA / 0.208 lego) is superseded by the
  null control and its md was never amended; the "spec-fix flips it to GO" remark is moot.
- **Seed score does not transport** (`logs/scaleadapt.log`). Fixing the 3.2x length-scale
  overfit (L_px 2.681 chair vs 8.632 cadpartA) bought cadpartA −0.003 recall (R 0.158 → 0.155
  vs a 0.45 bar); the seed ceiling is 0.475 pre-prune. The supporting sentence "chair-optimal
  seed score reads AUC 0.446 on lego" is a prose-only citation chain with no artifact. The
  scaleadapt numbers ARE verifiable from `logs/scaleadapt.log`, contrary to the md's
  provenance warning; only the calibration table (lego 2.814, l_world/z columns) is md-only.
  GEOLINE Step 3 later showed the "no reachable frontier point" half of NOT-GENERAL was a
  property of the f=0.30 operating point, not intrinsic.
- **NOT-GENERAL across five solids** (Steps 4–10). The consensus statistic ranks well
  everywhere (AUC 0.82 gicosa to 0.94 gcube; gstep 0.91) but no absolute or percentile cut
  clears all five. Step 4: gicosa R 0.260 vs 0.35 bar at the zero-knob point; every solid is
  ranker-limited, not pool-limited (oracle ceilings R 0.71–0.84). Step 6's kf 0.22 clause-off
  "GO" on four solids was refuted by the concave gstep in Step 8 (R 0.225); realized absolute
  thresholds span 0.30 (gicosa) to 0.68 (gstep), 2.25x. Step 5's 0.279-vs-0.50 mechanism was
  retracted by Step 6: the inlier-ratio clause never binds; the operative constant is
  `max_med` 1.5 px. Step 10: Wilson recalibration shrinks the interval gap 0.102 → 0.073 and
  passes the AUC guard but does not close it; the crowding de-confound is the only constant
  clearing all five (midpoint 0.1929, in-sample, +0.12 to +0.17 recall at P ≥ 0.72 on every
  solid) and fails the AUC guard (gicosa 0.822 → 0.717), which is built on a gapped label
  boundary the campaign twice measured as non-predictive of the deliverable metric. That
  re-registration decision is still yours. Also: `out/geoline_step6.json` was overwritten by
  the gstep run and now carries a false `icosa_ceiling_clears=false`; the four-solid sweep
  lives only in `logs/step6.log`; the Step-8 interval gaps (0.0927 / 0.0065) are not persisted
  and the four-solid near-miss is grid-sensitive (0.0159 on the Step-10 grid).
- **Precision is supervision-bound** (Phases 1c/1d/1e/1f). DINOv2 probe AUC 0.840 chair /
  0.904 lego collapses to 0.637 / 0.657 under the best mesh-free pseudo-labels (gate 0.72);
  transfer works chair→lego 0.825 but lego→chair 0.563. The topological trilemma: no tested
  gate, in-scene mesh oracle included, reaches P≥0.71 at R≥0.596 with topology ≥0.90
  (oracle point-gated P 0.797 at topology 0.637; zero-threshold chain ceiling topology 0.878;
  42.4% of candidates unchained). P1C's md disagrees with itself (0.8394 vs 0.8401); the JSON
  says 0.8401.
- **Geometry cannot discriminate the miss-set on textured scenes** (K_geom ≈ 0): 2DGS surfel
  dihedral 0.411, GT-mesh dihedral 0.396 on lego decals; on cadpartA the vanilla-3DGS normal
  field reads a median crease dihedral of 10.2° against GT 40.9–90° (2DGS restores 40.0°).
- **Rank lever exhausted on lego** three independent ways: detector union
  (0.6429/0.4424 < TEED alone 0.6535/0.4463), agreement-rank (inherits the weakest channel),
  junction-rank (AUC 0.705 < TEED seed score 0.727). TEED's ranking already encodes the
  structure these channels were built to add.
- **Evaluation dependency**: all scenes are NeRF-synthetic with perfect poses; no real capture
  or estimated-pose scene exists anywhere in the repo. The paper text cites a ficus statistic
  ("31% of geometric edges") that has no on-disk artifact in an n=2 paper.

---

# 4. Strongest honest thesis, and the one next experiment

## Candidate theses, ranked

1. **(Strongest)** "Feature lines bound as static object-space primitives on a frozen 3DGS
   have persistent stroke identity by construction; on textured objects this yields visible
   temporal stability at matched precision and density against per-frame and
   oracle-flow-accumulated 2D detection; and the precision such lines can reach is bounded by
   a measured set of ceilings (carrier coverage, no geometric cue in the miss set,
   supervision-bound discriminability, non-transporting consensus thresholds), with the
   obvious repairs pre-registered and falsified." This is Contribution A plus B of the current
   draft with the scope tightened to textured scenes. A hostile reviewer will say: n=2
   synthetic scenes with perfect poses, one trajectory family, per-frame Canny is more precise
   than you on lego, and stroke identity is a metric you defined. Every one of those is
   disclosed, and the first is the only one you can still fix.
2. "A falsification-first evaluation protocol for temporal stability of line rendering from
   neural scene representations." Honest, and the gate ledger is genuinely unusual, but a
   committee will ask where the method is.
3. "Clean, stable line drawings of CAD-like solids from a frozen 3DGS." **Not defensible.**
   Canny beats you on completeness and is visibly stable there; your advantage is a
   stroke-identity number that is 35% to 67% warp-drop.

## The single highest-value next experiment: one real captured textured object

Capture a textured object (fabric, printed pattern, a toy with decals), COLMAP poses, frozen
vanilla 3DGS with the shipped recipe, and run the shipped M1b pipeline plus the temporal
harness unchanged. The crown claim holds only on textured scenes, and it is the only claim in
the project that is fully mesh-free to evaluate: ink_churn, P_pop with the fg_only control,
Track-P survival curves, and PARETO matched-density flicker all need no GT mesh. Only matched
precision does, and you can state that as the one axis not transported. This attacks the one
reviewer objection that is both fatal and fixable: everything so far is NeRF-synthetic with
perfect poses.

Pre-registered rule, frozen before the run:

- **GO** if silhouette-controlled P_pop ratio ≥ 5x at 240 frames (lego/chair controlled
  values are 6.5x and 7.0x), ink_churn ratio ≥ 8x on consecutive frames (lego's 9.2x was
  visible; cadpartA's 6.8x was not), and the consecutive-frame strip is judged visibly
  steadier.
- **NO-GO** if either number misses, or if the pipeline yields fewer than 300 strokes per
  frame, which would mean the primitive itself does not survive estimated poses and real
  photometry.
- Report the memoryless matched-density PARETO flicker too, ungated, since precision cannot be
  matched without a mesh.

Cost is one capture, one COLMAP run, one 3DGS training, one pipeline run. Nothing new is built.

## Hygiene that must happen before any of this is written up (none of it an experiment)

- ~~Re-run `boiltest.py` over all seven scenes into one JSON~~ **DONE 2026-09-15**
  (`out/boiltest.json`, 7 scenes, `logs/boiltest_all7.log`; `scripts/boiltest.py` gained the
  gicosa/gprism/gstep pool mappings, keep masks verified identical to the turntable carriers).
- ~~Re-run every solid temporal cell with `--fg_only`~~ **DONE 2026-09-15** for every persisted
  solid carrier (12 cells: `out/m1b_stroke_temporal_table_fg_*.json`, `out/dd3_fgonly.json`;
  logs `logs/fgonly_{solids,cadA_extra,dd3}.log`); table in §1a. merge70, de-debris v1 and
  the gicosa-pilot merged carrier were never persisted and remain uncontrolled.
- ~~Amend `VIDEO_RESULTS.md` leg 5 to FAIL; propagate the BOILTEST / TURNTABLE bound into
  GEOLINE_STEP3/4/8, STROKEVIZ, MERGE, DEDEBRIS(_V2), DD3, GICOSA~~ **DONE 2026-09-15**: each
  of those write-ups now carries a dated correction block with the fg_only numbers and the
  statement that per-frame Canny is complete and stable on the solids.
- ~~Fix "5 of 6" → "3 of 4" and "≥9.8x" → "≥9.78x" in `RESULTS_MASTER.md` and
  `PARETO2_RESULTS.md`~~ **DONE (commit b21acae)**. Still open: restate the
  accumulated-baseline range as 1.72–9.46x with lego-T1 having no shared accumulated point;
  replace 19.8%/18.2% with 16.1%/14.8%.
- ~~Retract the "SAFE" label on lego's −24.6% swing in `E_LEDGER.md` §8~~ **DONE (b21acae)**.
  Still open: drop the borrowed 8.0x bar from `E_TRAJ_CHAIR_RESULTS.md`; report the envelope
  per scene × orbit × statistic.
- ~~Remove the "stated future work" and "poster asset" clauses from `scripts/comparison_fig.py`~~
  **DONE (b21acae)**. Still open: re-render with the ink-matched poster still and a matching
  ours illustration; label the stability axis as unmatched density.
- Bank the fine-grid A2 sweep as a JSON or drop "target MET" from the Step-3 write-up and the
  commit-message narrative.
- Compute mesh P/R for the dd3 carrier (`out/carrier_dd3_cadpartA.npz`) so the visual-first
  result has a correctness number beside it.
- Restore the four-solid `geoline_step6.json` from `logs/step6.log` or rename the gstep file;
  fill gstep cut 0.0011 in the turntable gallery.
- Mark as unsourced until an artifact exists: "AUC 0.446 on lego", the 213,711-edge count,
  the ficus 31% figure, the 89.5% top-k occupancy, the five-run Canny range.
