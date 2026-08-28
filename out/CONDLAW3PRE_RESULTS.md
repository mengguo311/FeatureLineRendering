# CONDLAW-3-PRE — a-priori rho_flat survey + FROZEN pre-registration

**Stage 1 of 2. MESH-ONLY. Nothing was trained.** No 2DGS/3DGS was fitted, no image was
read, no rendering was performed. The GT meshes are read through the same `trimesh` path
`scripts/diag2dgs.py` uses for its GT-mesh arm (`src/mesh_oracle.MESH_DIR/<scene>_new.obj`),
EVAL/label use only; no method-path file was touched. Protected temporal manifest re-verified
**332/332 OK**.

**Selected 3rd scene: `ship`. Pre-registered prediction: DRR@80(ship) = 0.803, band
[0.723, 0.883], hard floor > 0.5281.** Frozen below, before any rankability run exists.

Mesh availability confirmed (`ls ~/3dgs_line/bcr/meshes/NeRF_Mesh/`): chair, ficus, lego,
materials, mic, ship. **No `hotdog` mesh** — the spec's constraint is correct, so the third
scene had to come from {materials, mic, ship}.

---

## 0. A defect found and fixed before any number was trusted

The first implementation (`scripts/condlaw3pre_rhoflat.py`, kept for the record) measured
local normal dispersion over the mesh **face centroids** inside a ball and required
`n_min = 5` of them. That is **biased by tessellation density**: flat panels are meshed with
few large triangles, curved relief with many small ones, so ">=5 centroids in the ball"
preferentially **deletes flat surface** — and by a different amount per scene.

| scene | v1 valid samples @R=0.01 | v1 rho_flat | v2 valid | v2 rho_flat |
|---|---|---|---|---|
| chair | **0.323** | 0.004488 | 1.000 | 0.443172 |
| lego | 0.801 | 0.012298 | 1.000 | 0.129450 |
| materials | 0.924 | 0.751488 | 1.000 | 0.760650 |
| mic | 0.671 | 0.166952 | 1.000 | 0.215400 |
| ship | 0.578 | 0.026034 | 0.999 | 0.316603 |

The bias **inverted the anchors**: v1 made chair (0.0045) look *less* flat than lego (0.0123),
contradicting CONDLAW's established ground truth (chair's flat class = 134 805 loci, lego's
= 0 of 3814). A `D_hat` built on that would have had a **negative denominator**. Reported
here rather than silently discarded.

**Fix (`scripts/condlaw3pre_rhoflat2.py`)**: decouple the neighbourhood from the tessellation.
Resample each surface into an **area-uniform point cloud at a fixed density**
(63 662 pts / unit area => ~20 expected neighbours at R=0.01, identical for every scene),
each point carrying its source face normal **exactly** (no smoothing). Neighbour count is
then proportional to ball *surface area*, independent of triangulation. Because the cloud is
area-uniform, an unweighted scatter already *is* the area-weighted one, so a count fraction
over samples is genuinely an **area** fraction. Validity became 1.000 everywhere.

**The fix is validated against the ground truth it must respect** (`out/condlaw3pre_anchorcheck.json`):
at the frozen CONDLAW radius the debiased instrument reads lego **exactly 0.000000**, independently
reproducing CONDLAW's "0 of 3814 distractors flat", while chair reads 0.2364.

---

## 1. rho_flat_mesh — the a-priori, image-free scalar

`rho_flat_mesh(scene, R)` = fraction of GT-mesh **surface area** whose local undirected-normal
dispersion within radius R is `< 5°`. Dispersion is `normal_spread` **copied verbatim** from
`scripts/diag2dgs.py`: `arccos(sqrt(lambda_1))` of the normal scatter, in degrees.

**Primary radius R = 0.04 = the FROZEN CONDLAW radius** (`diag2dgs` mesh arm ran at
`rho=4.0 x` median linelet half-length `0.010007` = `R=0.04003`). R=0.01/0.02 are reported as
sensitivity. Source: `out/condlaw3pre_rhoflat2.json`.

| scene | role | rho_flat @0.01 | @0.02 | **@0.04 (primary)** | rho_flat_far @0.04 | median disp @0.04 |
|---|---|---|---|---|---|---|
| **lego** | ANCHOR (D=0.512) | 0.129450 | 0.003650 | **0.000000** | 0.000000 | 43.997° |
| mic | candidate | 0.215400 | 0.134500 | **0.007950** | 0.001285 | 42.869° |
| materials | candidate | 0.760650 | 0.339100 | **0.024850** | 0.027479 | 11.132° |
| **ship** | candidate | 0.316603 | 0.223650 | **0.144950** | 0.527285 | 29.958° |
| **chair** | ANCHOR (D=0.986) | 0.443172 | 0.334200 | **0.236400** | 0.579997 | 36.191° |

Ordering at the primary radius: **lego < mic < materials < ship < chair** — both anchors sit at
the extremes, which is exactly what a two-point calibration requires.

`rho_flat_far` = the same fraction restricted to surface farther than `1.5R` from any GT crease
(creases = mesh edges of dihedral >= 30°, resampled at ds=0.0015 — **identical** to
`src/mesh_oracle.MeshOracle`). It is the mesh-only analogue of CONDLAW's *distractor* class
("a confident non-crease locus"), since CONDLAW's binding quantity was flat-class
**membership among non-crease loci**, not raw global area.

Crease machinery validated: this code returns **971 793** lego crease points, byte-matching
the archived `out/diag2dgs_lego_scale.json` `n_crease_pts`.

### Note on the archived lego reference
`condlaw3pre_spec.md` cites `out/diag2dgs_lego_surface_flatness.json` (lego = 0.69% @R=0.01).
That file's producing script **is not in the repo** and is not byte-reproducible from it. My
area-weighted centroid reimplementation gives 1.23% and an unweighted one gives 1.12%, whose
`frac<20` (0.0358) matches the archive's (0.0365) — so the archive was likely unweighted.
Rather than reverse-engineer a lost script, **one definition is applied identically to all five
scenes**, and both anchors are recomputed under it, so the calibration is internally consistent.
The archived 0.69% is *not* used as an input anywhere.

---

## 2. Second a-priori proxy — flat-class area per crease locus

Spec item 2, at R=0.04. `flat_area = rho_flat x surface_area`; crease count = `n_crease_pts`.

| scene | rho_flat | surface area | flat area | n_crease_pts | **flat area / crease pt** |
|---|---|---|---|---|---|
| lego | 0.000000 | 55.755 | 0.0000 | 971 793 | **0.000e+00** |
| mic | 0.007950 | 6.995 | 0.0556 | 798 926 | **6.960e-08** |
| materials | 0.024850 | 17.989 | 0.4470 | 116 892 | **3.824e-06** |
| ship | 0.144950 | 21.980 | 3.1860 | 595 128 | **5.353e-06** |
| chair | 0.236400 | 11.520 | 2.7232 | 228 079 | **1.194e-05** |

Same ordering, and it independently reproduces the anchor extremes.

---

## 3. Two-point calibration

Anchors are the solid CONDLAW numbers (`out/CONDLAW_RESULTS.md`): chair **0.986** (exact
0.985772, CI [0.9848, 0.9866]), lego **0.512** (exact 0.512323, CI [0.4976, 0.5281]).

`t = (rho_cand - rho_lego)/(rho_chair - rho_lego)`, `D_hat = 0.512 + t x (0.986 - 0.512)`.
Interior <=> t near 0.5. Source: `out/condlaw3pre_prereg.json`.

| variant | materials | mic | **ship** |
|---|---|---|---|
| rho_flat @0.01 | t=2.012 D=1.466 **OUTSIDE** | t=0.274 D=0.642 | t=0.597 D=0.795 |
| rho_flat_far @0.01 | t=1.632 D=1.286 **OUTSIDE** | t=0.078 D=0.549 | t=0.482 D=0.741 |
| rho_flat @0.02 | t=1.015 D=0.993 **OUTSIDE** | t=0.396 D=0.700 | t=0.666 D=0.827 |
| rho_flat_far @0.02 | t=0.663 D=0.826 | t=0.416 D=0.709 | t=0.863 D=0.921 |
| **rho_flat @0.04 (PRIMARY)** | t=0.105 D=0.562 | t=0.034 D=0.528 | **t=0.613 D=0.803** |
| rho_flat_far @0.04 | t=0.047 D=0.534 | t=0.002 D=0.513 | t=0.909 D=0.943 |
| proxy2 @0.04 | t=0.320 D=0.664 | t=0.006 D=0.515 | t=0.448 D=0.725 |
| **"most interior" wins** | **0 / 7** | 2 / 7 | **5 / 7** |
| **variants pinning OUTSIDE** | **3 / 7** | 0 / 7 | **0 / 7** |

---

## 4. SELECTION: `ship`

- **ship is the only candidate that is interior under every variant** (t in [0.448, 0.909],
  never < 0 or > 1) and it wins "most interior" in 5 of 7. Its primary t = 0.613 sits
  usefully off both anchors, so a measurement can discriminate.
- **materials is disqualified**: it pins *outside* (t up to 2.012, beyond the chair anchor) in
  3 of 7 variants and swings from t=2.01 to t=0.105 across radii. It is a nearly-flat scene
  (spheres on a plane; median dispersion 2.59° at R=0.01) — it saturates the flat end and its
  position is not scale-stable, so it carries little discriminating power.
- **mic is disqualified**: it pins to the **lego** anchor at the primary radius (t=0.034,
  D_hat=0.528, indistinguishable from lego's own 0.512 given lego's CI upper 0.5281). A
  prediction there is untestable — "lego-like" is the null.

---

## 5. FROZEN PRE-REGISTRATION — `ship` (recorded 2026-08-29, BEFORE any rankability run)

`rho_flat_mesh(ship, R=0.04) = 0.144950`, `t = 0.6132`, **`D_hat = 0.8026`**.

### PRIMARY — strict monotonicity (functional-form-free; the load-bearing test)
> **0.5281 < DRR@80(ship) < 0.9848**, i.e. strictly between the lego 95% CI upper bound and
> the chair 95% CI lower bound, ordered consistently with rho_flat: **lego < ship < chair**.

Two points cannot fix a curve shape, so monotonicity — not the fitted value — is the law claim.

### SECONDARY — affine heuristic band
> **DRR@80(ship) in [0.723, 0.883]** (`D_hat +/- 0.08`).

Missing this band while **keeping** monotonicity is to be reported as evidence of
**nonlinearity / a possible sigmoidal phase transition in flat-mass — NOT a law failure**.
Across all seven scalar variants D_hat(ship) spans **[0.725, 0.943]**, so the +/-0.08 band
encodes less uncertainty than the choice of scalar does; that spread is disclosed here in
advance rather than used later to excuse a miss.

### HARD GO FLOOR
> **DRR@80(ship) > 0.5281** confirms the flat class is non-vacuous on ship.

### Falsification conditions, stated in advance
| outcome | reading |
|---|---|
| DRR@80(ship) <= 0.5281 | **LAW FALSIFIED** — a scene with 0.145 flat mass (vs lego's 0.000) is still at the lego ceiling, so rho_flat does not predict rankability |
| DRR@80(ship) >= 0.9848 | **LAW FALSIFIED** — monotonicity broken at the top; ship matches/exceeds chair despite 0.61x its flat mass |
| in (0.5281, 0.9848) but outside [0.723, 0.883] | monotonicity **HOLDS**, affine form does not — nonlinear flat-mass -> rankability map |
| in [0.723, 0.883] | law confirmed in both form and magnitude |

### Pre-registration integrity — verified, not assumed
- **No trained 2DGS/3DGS exists for materials, mic, or ship.** `out/` has only `2dgs_chair*`
  and `2dgs_lego`; `~/cglib/outputs/` has only `chair_static`, `ficus_static`, `lego_static`.
- **No results file reports any number for the candidates.** The single `ship` hit across all
  `.md` files is `RECALL_RESULTS.md:97`, the verb ("checkpoints **ship** inside the repo").
- **No `out/` or `cache/` artifact** is named for materials/mic/ship.
- Therefore the prediction is genuinely a-priori: the quantity being predicted **does not yet
  exist anywhere in this repository**.

### Stage-2 feasibility — verified
All five scenes have exactly **100 train frames and 100 PNGs** under
`~/cglib/data/full/<scene>/`, so the frozen `src/view_split.py` (`N_VIEWS=100`,
TEST = {5,15,…,95}) transfers to ship unchanged. `ship_new.obj` is present, so
`MeshOracle("ship")` will work for labels. Stage 2 (train 2DGS on ship, then TEED-rankability
DRR@80 on held-out TEST against this frozen prediction) is executable as specified.

---

## 5b. Adversarial audit of this pre-registration (run before freezing; findings folded in)

A 6-agent adversarial audit was run against this stage. Its leakage sweep (whole-home model
search, git history on all branches, cache token histogram) **independently CONFIRMED** the
integrity check in §5. Its headline "blockers" targeted the **v1 estimator** and are resolved
by the §0 debiasing — the audit itself reached the same root cause ("rho is a proxy for mesh
tessellation density ... its debiased estimator restores the ordering"). Four findings are
real and are recorded here rather than dismissed.

### (a) The interiority metric is a forking path — disclosed
"Most interior" is not uniquely defined. Raw-midpoint and **log**-midpoint (geometric mean)
disagree on this data:

| radius | raw-midpoint picks | log-midpoint picks |
|---|---|---|
| R=0.01 | ship | **mic** |
| R=0.02 | **mic** | mic |
| **R=0.04 (primary)** | **ship** | **UNDEFINED** — `rho_lego = 0` exactly, so the geometric mean is 0 |

At the primary radius the log metric is undefined, so raw-midpoint is the only well-posed
choice there — but at R=0.01/0.02 the metric choice would change the selected scene. This is
why §4 rests on *robustness across all 7 variants* (ship interior in 7/7, never outside)
rather than on a single interiority score. `mic` winning 2/7 is already shown in §3.

### (b) The lego anchor is upward-biased as a calibration endpoint — quantified
CONDLAW's lego value **0.512 is a MAXIMUM** over 11 non-circular adversarial attempts and 3
orientation policies — deliberately conservative *against* the ceiling claim, but that makes
it an upper bound, not a point estimate, when reused as the bottom of an interpolation. Under
the literal frozen sign(+1) policy the same statistic gives **0.279**:

| lego anchor | D_hat(ship) | band |
|---|---|---|
| 0.512 (best-over-attempts — **used**) | **0.8026** | [0.723, 0.883] |
| 0.5281 (lego CI upper) | 0.8087 | [0.729, 0.889] |
| 0.279 (frozen sign +1) | 0.7124 | [0.632, 0.792] |

**The anchor-policy swing alone is 0.090 — larger than the ±0.08 band half-width.** Declared
in advance: if the measurement lands in [0.632, 0.723] it is inside the band under the
sign(+1) anchor and outside it under the best-over-attempts anchor, and that ambiguity must
be resolved in favour of **reporting both**, not of whichever passes.

### (c) Stage 2's measurement pipeline must be NAMED — and one route is blocked
The two anchors were measured with **different statistics on different class definitions**
(chair: rendered-normal ribbon on mesh-flat-restricted Canny classes; lego: mesh dihedral on
TEED-defined decals). A monotonicity claim is only meaningful if the candidate is scored by a
named pipeline. Additionally:

- **BLOCKER on the lego-lineage route**: no candidate has a vanilla 3DGS model
  (`~/cglib/outputs/{materials,mic,ship}_static` do not exist), so `common.load_gaussians`
  and everything built on it (`scripts/diag2dgs.py`, `scripts/tgap_pull.py`) raises
  FileNotFoundError. `scripts/condlaw_drr.py` is additionally hardcoded to lego inputs with
  no `--scene`. That route needs extra per-scene artifacts, not one training run.
- **Viable route**: `scripts/condlaw_chair_test.py` already accepts `--scene` and
  `--no_vanilla`; with that flag its only dependencies are `load_cameras`, `MeshOracle`, and a
  trained 2DGS model — all satisfiable for ship after one ~10-15 min 2DGS run.

**PRE-REGISTERED PIPELINE for Stage 2**: `scripts/condlaw_chair_test.py --scene ship
--views test --no_vanilla`, scoring the **2DGS rendered-normal ribbon (`theta_normal`) on the
refined (mesh-flat vs mesh-sharp) classes** — i.e. the *chair-lineage* statistic. The chair
anchor 0.986 is directly comparable to it. The lego end is a cross-lineage comparison and
must be labelled as such when the monotonicity test is reported.

**Code defect found and fixed**: `condlaw_chair_test.py` wrote to `out/condlaw_chair_{views}.*`
regardless of `--scene`, so a Stage-2 run on ship would have **silently overwritten the chair
anchor's per-locus artifacts**. Now `out/condlaw_{scene}_{views}.*` — byte-identical for
chair (so the committed CONDLAW artifacts keep their paths), distinct for every other scene.

### (d) Test power — the spec's 1-scene design is weak, and this is stated up front
A single new point landing inside a wide interval is weak evidence: under a no-information
null it passes roughly half the time. Measuring **all three** candidates and testing the
*predicted ordering* `mic < materials < ship` (from rho_flat@0.04: 0.0080 < 0.0249 < 0.1450)
is a 1-in-6 chance-level test instead of ~1-in-2, at the cost of 3 trainings rather than 1.
The spec froze the 1-scene design and this stage executes it as written; the ordering
prediction above is **also frozen here**, so it is available at no extra cost if Stage 2 is
ever widened.

---

## 6. Invariants

| invariant | status |
|---|---|
| mesh never in method path | held — mesh read only via the `mesh_oracle` MESH_DIR path, for eval/labels; no method-path file changed |
| no training this stage | held — no 2DGS/3DGS fitted, no images read, no rendering |
| held-out TEST for eval / VAL for fitting | n/a this stage (no eval, no fit); Stage 2 will use frozen TEST |
| protected temporal results untouched | **332/332 OK** re-verified after all work |
| new artifacts under a condlaw3pre_ prefix | held — every output listed below |
| pre-registration is a-priori | held w.r.t. the OUTCOME (no DRR@80 for any candidate exists anywhere); **not blind w.r.t. the PREDICTOR** — rho was necessarily computed for all five scenes before the scene was selected, exactly as the spec prescribes. Stated explicitly so the audit trail is complete. |

**Artifacts.** `scripts/condlaw3pre_{rhoflat,rhoflat2,calib}.py`;
`out/condlaw3pre_{rhoflat,rhoflat2,anchorcheck,prereg}.json`; `out/CONDLAW3PRE_RESULTS.md`;
`logs/condlaw3pre_rhoflat{,2}.log`. Mesh-side only, CPU; `CUDA_VISIBLE_DEVICES=1`, u00134
processes only.
