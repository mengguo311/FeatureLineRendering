# P2 v03 — user-accepted visual baseline, one bounded association experiment

## New user decision (authoritative)
User's latest exact message: **“感觉目前的质量以及足够，直接开始下一步实验”**。
Accept current GT-lamp visual quality as SUFFICIENT TO ADVANCE. Do not continue shade-spacing polish, density threshold chasing, or generic rasterizer refinement. This is a NEW stage authorization, not an extension of the expired22:00 supervisor. Preserve every old NO_GO and incomplete unit011 record; do not retrospectively relabel/seal them.

Freeze the latest fully sealed **unit010 outputs/edited named434 asset** as the reproducible GT-lamp baseline (260shade0deg,24stem,150shortened-base). unit011 is unsealed WIP and must NOT silently replace it. Record this acceptance as `USER_ACCEPTED_GT_VISUAL_BASELINE_FOR_P2`; it is not RaDe-GS reconstruction completion, full temporal certification or H1/H2 research success.

## Read first
1. Entire `docs/partwise_sketch_hatching/experiment_outline_v1.md`, especially §5.3,§5.9,§8.1–8.3,§9.
2. `docs/partwise_sketch_hatching_v02/P1_ROADMAP_ZH.md`, REPORT_unit010 and current renderer/walker/asset APIs; inspect actual source, not only reports.
3. Existing data and source hashes; oldNEXT about unit011 aesthetics is SUPERSEDED by user's acceptance. Start P2, not that pending polish task.

## Scope / immutable state
- Writable worktree+branch ONLY `/home/u00134/3dgs_line/partwise_sketch_hatching_p2_v03`, `partwise-sketch-hatching-p2-v03`, base653db72d8888ff63ebaa60638c119b374960dfe7.
- New code preferred `experiments/partwise_sketch_hatching_v03/`, docs `docs/partwise_sketch_hatching_v03/`.
- Heavy science ONLY `/mnt/hdd1/u00134/partwise_sketch_hatching_p2_v03/experiment_001/`; orchestration is parent-owned/read-only, except inherited process temp path is provided there. Never run an old producer or sealer that writes previous output roots; inspect hardcoded paths first. All v01/v02 worktrees,26 old seals,originalGS/C8/joint and old raw data are read-only.
- One bounded experiment <=90 minutes. No autonomous multi-round research loop or expansion into P3/H3/H4/H5. Write recoverable STATUS early, milestones after actual runs. Local commits allowed after tests; NO push/merge/reset/clean. User's earlier push request was fulfilled for v02, not standing permission to push new research.
- CPU-only, total numeric threads<=2, two-core affinity for compute, CUDA_VISIBLE_DEVICES='' before imports, no GPU/queue/build/training. Use read-only existing venv `/mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_8build_part_prior_feasibility_v03/venv/bin/python` explicitly (barepython absent). No model switching/nested agents/CLIs. No installs/upgrades/download unless essential and isolated; prefer existing packages.
- No credential/auth/token/private-key/secret files, no environment output; process inspection only PID/comm, never signal others. TMPDIR stays under new orchestration/scratch; no/tmp scripts. Root>=1GiB,HDD>=10GiB,new output<=8GiB; serial loops and invocation<=10min. Preserve original nonzero exits rather than rewriting them; JSON stdout must normalize NumPy.

## Scientific question: P2 association, not automatic reconstruction
A first controlled **GT/oracle diagnostic** of outline experiment family B (H2 candidate): on the SAME surface, SAME coarse labels, SAME starting seeds/style/camera/renderer, does adding a declared boundary/structure relation reduce visible crossing/near-boundary clutter, without just deleting ink or damaging the accepted whole-object appearance?

Prefer three tightly scoped arms:
- U: no association (fixed coarse segmentation + generated hatches; any structure drawing held explicit).
- S: U + confirmed boundary stop/leave-white rule.
- D: S + local direction guidance where the declared style actually requests it.

The exact arm design must be justified and frozen BEFORE evaluation. Distinguish outline B1/B2/B3 from these sub-ablations: current P1 renderer ALREADY draws rings/contours, so do not rename an already present component as new B2 benefit. Keep physical structure lines, edit boundaries and view-dependent contours separate. Initial curves may be clearly labeled authored GT/oracle rings/seams for this controlled diagnostic, NOT claimed ordinary-depth multiview recovery or automatic extraction. No silent use of TEST image edges.

### Mandatory cheap headroom/leakage audit (critical)
Current paths were generated with exact GT parts and the renderer may filter fragments using GT part IDs. This can make baseline crossing zero by construction, or make a purported coarse-label test secretly use perfect labels.
- Inspect part masks in path generation, renderer visibility/owner checks, sampling and scoring. All compared methods must share identical geometry visibility; independent GT labels can score only, not secretly fix the coarse baseline.
- Before the association evaluation, establish whether the original three physical components have sufficient connected surface/eligible boundary support for this question. Disconnected surfaces must not be connected by KNN or fabricated chains.
- If using a controlled coarse-label perturbation, define its field, amplitude, seed, exposed views and masks before candidate evaluation; identical realization for every arm. Mark it synthetic noise, NOT a learned segmentation failure. Preserve the no-noise/strong3D baseline or a bounded matched-ink control where needed to tell real structure help from simple trimming/less ink.
- If exact part boundaries already make crossing impossible, report ZERO_HEADROOM/UNIDENTIFIABLE_FOR_H2, not a successful H2 experiment and not global methodNO_GO. You may instead execute a genuine B1-vs-B2 fixed-structure display/feasibility test with all same downstream inputs and label H2 untested. Do not manufacture a new weakness merely to show improvement.
- A fixed authored edit-region boundary can be tested only if explicitly distinguished from a physical geometric edge, with additional regionIDs and full provenance; it is an oracle style-boundary diagnostic, not recovered semantic parts. Keep all3physical lamp parts and full-object views. Choose at most ONE coherent diagnostic after this audit, not multiple toyproof rounds.

## Required execution / delivery
1. Write `BASELINE_ACCEPTANCE_ZH.md` preserving exact user decision and baseline hashes. Freeze PROTOCOL.json (source/asset/camera/curve/label provenance, exact changedterm, masks/noise, style/ink/width, sampling/visible support, valid/invalid gates) and commit before outputs. Aesthetic baseline is user accepted: do not inherit unit004's unrelated .75 density gate as a P2 veto. Catastrophic loss of accepted structure still counts as regression.
2. TDD for new computational logic: one real failing behavior test then minimal implementation then pass; cover crossing/stop, invalid curve or missing evidence =>UNKNOWN, fixed non-target geometry, and no-edit/delete-all/drift sensitivity. Do not repeat all historical arrays or create universal renderer proofs.
3. ACTUALLY execute the bounded comparison or the scientifically valid zero-headroom alternative. Use same complete lamp, shared cameras and same actual drawing backend; all arms use identical input labels/geometry. Freeze compact native-resolution static and short orbit/zoom paths before evaluating; four existing az30/120/210/300 views are historically EXPOSED, not blind. If new views selected from metadata before evidence, say construction holdout only, not reconstructed-GS-unseen.
4. Save complete-object same-camera side-by-side images and boundary closeups; show coverage/ink/spacing changes beside clutter/leakage, not counts alone. Save at least a short per-camera-rendered comparison orbit with fixed3D paths if feasible (no animated stills). For fixed-camera two-state edit, label it accurately. Full decode and source-frame matching/frame count, preservedSHA. No real-time claim from CPUoffline output.
5. Metrics separate unchanged coarse segmentation from hatch clipping: do NOT claim mIoU/segmentation improved if labels unchanged. Separate true expected hiding, AA boundary band and far wrong-part leakage. Report eligible length/area coverage, nonzero target operation, retained ink/darkness and boundary support. If scores require GT and use it, label diagnosticoracle. If no measurable eligible boundary or valid control, return UNDETERMINED/ENGINEERING_INVALID, not a fakepass. GTdemo is not evidence of noisy RaDe-GS reconstruction benefit or novelty.
6. Write Chinese concise REPORT with actual code/commits/commands/returncodes, raw metrics and complete views, allpositive/negative/unknown scope. STATUS.json keys `stage,execution_state,scientific_verdict,artifacts,tests,blockers`; NEXT.json one recommended next experiment with reasoning, notautomatic continuation. SEAL+SHA manifest only after real validation; keep runtimefinal outside seals. Do not run pending unit011 sealer. This is a single-stage experiment; stop after delivery.

## Success interpretation
Implementation done != mechanism useful. Desired outcome is evidence about whether this association adds value on the stated diagnostic, including honest zero-headroom or no incremental gain. User accepted the baseline's quality so lack of artistic perfection is NOT a reason to refuse moving to this next test. Conversely acceptance does not permit fabricated method benefit, hidden GT repair, TEST tuning or rewriting prior failures.
