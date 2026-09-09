# DESIGN ARGUE ONLY — NO CODE. Read, push back, converge on ONE experiment + go/no-go.

Step 3 landed an honest result: target R>=0.60@P>=0.75 on cadpartA is MET, but by the
FROZEN consensus-prune ranker at f=1.00 (arm A2), NOT by the new geometric/2DGS cue (arm B
0.93-AUC verifier LOSES to the shipped prune everywhere above P0.65). Good — but it is ONE
solid, and I see TWO discipline holes before any "scene-agnostic" claim is defensible:

HOLE 1 — hidden per-scene knob. The R0.625@P0.749 point was READ at keep-fraction 0.35,
chosen by looking at cadpart's OWN P/R frontier. Choosing kf by inspecting the target metric
IS per-scene tuning in disguise. A scene-agnostic algorithm must fix the operating point
WITHOUT reading P/R — either kf frozen to a constant, or (better) an operating rule expressed
as a PHYSICAL threshold on an internal statistic (e.g. a consensus-residual cutoff in px, or a
dihedral in degrees) that is scene-agnostic by construction.

HOLE 2 — single solid = no generality. rho=4.0/xi=0.25/n_min=5 and f=1.00 are frozen but only
demonstrated on cadpart's graded 41-90deg chamfers.

Two candidate next experiments:

CANDIDATE A: build a SECOND, maximally-different solid NOW (icosahedron, uniform ~138deg
dihedrals — opposite of cadpart's gradation; or cube, pure 90deg) and run the IDENTICAL frozen
A2 pipeline at kf=0.35, zero retuning. Go/no-go: R>=0.50@P>=0.70 on solid#2 with kf frozen.

CANDIDATE B (my lean): FIRST close HOLE 1 on cadpart alone — re-express arm A2's operating
point as a scene-agnostic PHYSICAL rule (a consensus-residual threshold in px, picked WITHOUT
reading P/R) and verify that rule lands near R0.62/P0.75 on cadpart. Only then carry that exact
frozen px-rule to solid#2. Rationale: if we cannot even DEFINE a scene-agnostic operating rule
on the one solid we have, building solid#2 with a kf hand-read off cadpart just launders the
per-scene tuning into the "frozen" set and A's go/no-go would be self-deceiving.

MY POSITION: do B first (cheapest falsification, directly attacks the binding discipline hole),
THEN A carries the same physical rule. But push back hard: (1) is a residual-px cutoff actually
scene-agnostic, or does the consensus residual scale with gaussian density / scene units so the
"physical" px threshold is secretly scale-dependent too? (2) Is rho/xi themselves chair-tuned
and will they break the residual distribution on a different solid, making B's rule non-transportable
anyway? (3) Would you rather spend the 4 GPU-min on solid#2 immediately (A) because a rule
verified on N=1 solid proves nothing about transportability and only N>=2 can?

Give me your expert synthesis + adversarial critique, name which of A/B (or a sharper third
option) you'd run, and converge with me on ONE experiment carrying a PRE-REGISTERED go/no-go.
NO CODE YET — this is design only. Direct reasoning, no heavy multi-agent workflow.
