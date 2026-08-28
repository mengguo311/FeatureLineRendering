# ECO — Epipolar-Consensus-Only seed culling (isolate the multi-view rigidity mechanism)

## Why this, why now
CMEPI closed: the TEED f-frontier lift reproduces on DexiNed (non-TEED, same BIPED corpus) —
architecture/capacity invariance CONFIRMED; corpus-generality OPEN (PiDiNet reversed on lego).
We are NOT chasing more same-corpus detectors (HED/BDCN are both BSDS500 like PiDiNet — low upside,
risks reframing the win as corpus-specific, and makes ZERO progress on the real unmet gate
P@1.5>=0.85 AND R>=0.65). We pivot to the precision gate.

DECIDED (argued with agy, pushed back twice):
- REJECT the normal-gate half of NG-MEC. Vanilla-3DGS geometry is AUC~0.5 for crease-vs-fabric
  (K_geom~0, proven 4 ways); a normal/geometry VETO is a refuted dead-end (2DGS-normal veto put
  14/15 arms BELOW the f-frontier). Seed COVERAGE is binding; orthogonal info must be spent
  ADDITIVELY, not as a veto. NO normal gate in this experiment.
- ISOLATE the epipolar-consensus mechanism alone. TEED/DexiNed residual FPs are mostly
  VIEW-DEPENDENT occluding contours / sub-30deg — NOT hallucination. Occluding contours slide
  non-rigidly across views; true creases are view-stable 3D loci. Multi-view epipolar consensus
  culls exactly that FP class WITHOUT any photometric/geometric veto.

## The experiment (mesh EVAL-ONLY, held-out TEST, method never imports mesh)
For DexiNed@0.7 and TEED@0.5 seed proposals (the two CMEPI carriers), on chair AND lego:
1. For each 2D edge seed in a reference TEST view, back-project along its ray using the FROZEN 3DGS
   depth to a candidate 3D point p (method-path depth only, no mesh).
2. Gather K=3 nearest TEST/train poses (reuse the pull_split=train views so held-out TEST eval is
   clean). Reproject p into each; measure edge support at the reprojected pixel using the SAME
   cached detector probability maps (no new detector). A true crease reprojects onto edge evidence
   in all K views; an occluding contour drifts off it.
3. Consensus score c(seed) = fraction (or soft min) of K views with detector-prob above the seed's
   own native threshold within a small epipolar search band (tune band on chair VAL only, transfer
   to lego unchanged — same discipline as CMEPI thr selection).
4. Spend c ADDITIVELY into the M1a ranking vector (e.g. rank = base_score * (1+lambda*c) or a
   monotone reweight), NOT as a hard veto. Sweep lambda on chair VAL, freeze, transfer to lego.
5. Re-run the identical run_m1b.py path (--edge sharp DT-pull unchanged in every arm; only --score
   changes) and score against the published Canny f-frontier, band f in [0.30,0.50] chair /
   [0.15,0.50] lego, tau=1.5, stage AFTER pull+prune[tuned+len]. Report LIFT_P both estimators,
   AND the absolute gate P@1.5 & R at each band f (this is the number that matters now).

## Controls (mandatory, same rigor as CMEPI)
- Protect the 332-file published manifest (sha256 before/after). Untouched temporal figures
  (--viz_tag). Bit-identical n_seeds across arms at matched f (re-ranking one candidate pool).
- Ablate: (a) veto version of the SAME consensus (hard cull c<thr) to CONFIRM it under-performs the
  additive version — this directly re-tests the "additive not veto" law on new machinery;
  (b) K sweep {1,3,5} to show consensus (K>=3) beats single-view.
- Held-out TEST only; VAL used solely for band/lambda/thr selection.
- Temporal no-regress: chair f=0.30, lego f=0.40, P_pop ratio must stay >=8x (protect the win).

## FROZEN GO / NO-GO (set before any number exists)
- PRIMARY GO: on BOTH chair and lego, at some band f, the additive-ECO arm reaches
  P@1.5 >= 0.85 AND R >= 0.65 simultaneously, with temporal P_pop ratio no-regress (>=8x).
- PARTIAL/PROMISE: does not hit the joint gate, but ECO strictly increases P@1.5 at matched R
  (paired per-view, t>2, >=7/10 views) over the DexiNed/TEED baseline on BOTH scenes AND LIFT_P
  sign preserved -> mechanism works, iterate (add 2DGS normals additively, AUC 0.958, next fire).
- NO-GO: P@1.5 not improved at matched R on either scene (t<=2 or <6/10 views), OR any temporal
  regress below 8x, OR R collapses below 0.60 -> epipolar consensus does not isolate the FP class;
  report straight and reconsider.
- Report a thorough ECO_RESULTS.md like CMEPI_RESULTS.md. Do NOT fabricate; every number from a
  real json. Nothing committed until validated.
