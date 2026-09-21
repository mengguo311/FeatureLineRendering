"""Assemble the completed audit/report; never changes scientific outputs."""
import json,hashlib,shlex,datetime
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];art=ROOT/'artifacts/adaptive_mass_layered_probe';out=ROOT/'out/adaptive_mass_layered_probe'
read=lambda n:json.loads((art/n).read_text())
g0=read('VERIFICATION.json');g1=read('G1_VERIFICATION.json');integrity=read('FINAL_INTEGRITY.json');review=read('G1_VISUAL_REVIEW.json');suite=read('FULL_SUITE_ACCESS_PREFLIGHT.json')
assert g0['passed'] and g1['passed'] and integrity['passed'] and suite['passed'] and review['decision']=='NO_GO'
audit0=read('ACCESS_AUDIT.json');stages=dict(audit0['stages']);stages.update(suite['stages']);stages.update(g1['audits']);access=dict(passed=all(d['passed'] for d in stages.values()),forbidden_successes=sum(len(d['forbidden_successes']) for d in stages.values()),unparsed_open_lines=sum(len(d['unparsed_open_lines']) for d in stages.values()),stages=stages,scope='Scientific workers and both layout workers use Landlock and native-open traces; completed outer full-suite traces are audited. See BOOKKEEPING_SCOPE.json for opaque historical TEST-named byte-hash reads outside scientific workers. No TEST source image/camera/evidence selected for science; no C/DEV evaluation outputs used. G1 TRAIN views are members of F but no G2 F-stage construction occurred.')
assert access['passed'] and access['forbidden_successes']==0 and access['unparsed_open_lines']==0
(art/'FINAL_ACCESS_AUDIT.json').write_text(json.dumps(access,sort_keys=True,indent=2)+'\n')
gates=read('GATES.json');gates.update(G1='NO_GO',G2='NOT_RUN',G3='NOT_RUN',scientific_verdict='NO_GO',verdict='G1_NO_GO',complete=True,verification_passed=True,g1_verification_passed=True,execution_audit='PASS',g1_scene_go_count=0,g1_required_scene_go_count=3,g1_visual_review='G1_VISUAL_REVIEW.json',g1_control_metrics='G1_CONTROL_SUMMARY.json',stop_reason=review['decision_reason'],worker_gate_snapshot_note='g1_run/GATES.json and g1_rerun/GATES.json remain immutable AWAITING_VISUAL_REVIEW snapshots; this curated artifact records the completed review.',video='NOT_APPLICABLE: G2/G3 not reached')
(art/'GATES.json').write_text(json.dumps(gates,sort_keys=True,indent=2)+'\n')
report=Path('/home/u00134/codex_astra_adaptive_mass_layered_probe_report.md')
rows=[]
for s in ['lego','chair','drums','ficus']:
 m=gates['scenes'][s]['90_128'];c=m['coverage'];q=c['K_roi'];rows.append(f"| {s} | {100*c['mass_capture']:.6f}% | {100*c['fraction_pixels_ge_90']:.6f}% | {q['p50']:g}/{q['p75']:g}/{q['p90']:g}/{q['p95']:g}/{q['p99']:g}/{q['max']:g} | {m['memory']['stored_events']:,} | {m['memory']['csr_total_bytes']/2**20:.2f} |")
control=read('G1_CONTROL_SUMMARY.json');nullrows=[]
for s in ['lego','chair','drums','ficus']:
 ch=control['summary'][s];e=ch['E_occ']['95_70'];fmt=lambda xs:f'{min(xs):.3f}–{max(xs):.3f}';nullrows.append(f"| {s} | {fmt(e['full_minus_no_ids'])} | {fmt(e['full_minus_shuffled_ids'])} | 4/4 | {len(ch['E_shape_ridge']['95_70']['joint_numeric_id_criterion_views'])}/4 | 0/4 | 0/4 |")
journal=sorted(map(json.loads,(art/'TDD.jsonl').read_text().splitlines()),key=lambda r:r['sequence'])
keylabels=['g1_run_fixed','g1_rerun','g1_run_layout','g1_rerun_layout','full_suite_all_integration','full_suite_access_traced','g1_final_verification','final_integrity']
commands='\n\n'.join(f"{r['sequence']:03d} {r['label']} — exit {r['exit_code']}; log SHA256 `{r['output_sha256']}`\n\n```bash\n{shlex.join(r['command'])}\n```" for r in journal if r['label'] in keylabels)
files='\n'.join(f'- [{p}]({ROOT/p}) — SHA256 `{h}`' for p,h in sorted(integrity['sources'].items()))
text=f'''# Adaptive mass layered probe: G0 PASS, G1 NO_GO

The engineering amendment succeeds at tau=.90 with the smallest common Kmax=128. The completed G1 experiment does **not** establish the required visual/mechanistic advantage in any of the four scenes (0/4; required >=3/4). Stopped before G2 lifting, G2 held-out evaluation and G3. No video stage was reached. The negative scientific decision is supported by complete controls and uncapped soft fields, not final masks alone.

Branch remains `adaptive-mass-layered-line-probe` at HEAD `062d7ce73a740e1a817c82e57e516b395e45f417`. No commit or push. All {integrity['preexisting_tracked_files']:,} pre-existing tracked files and all {integrity['preserved_fixed_k_files']} protected fixed-k-family/report files are byte-for-byte unchanged. The old ENGINEERING_NOT_READY result remains intact.

## Protocol and representation

The amendment was frozen before production implementation at SHA256 `b3447ace351398ab3c9a97b3f22564480269f40ffb233f4747ee055f9e95140d`. The approved plan and inherited protocol are incorporated in full and hash-pinned. The inherited G1/G2/G3 scientific gates, controls and split rules were not changed. G1_IMPLEMENTATION.md was separately frozen before any scene line-output inspection at SHA256 `d3d8d9c9d12422a2edee951984aff8d259b224bb00adf5ad04be5c4817e5f9f1`. No scientific threshold changed after inspection.

The additive C++ reader consumes the actual pinned CUDA sorted point_list/ranges, native conics, depths, RGB and final transmittance. It uses deterministic two-pass count/fill CSR with int64 offsets and original IDs, stream positions, equal-depth order, z, incoming T, event alpha, Talpha and RGB. The stopping target is tau*(1-native_final_T); weights are float32 native-rule replay values summed in float64. It stores the shortest accepted front-to-back prefix reaching target, or Kmax/end of stream. It continues replay through the omitted tail and saves full tail RGB/alpha plus separate native and replay final transmittance. No largest-weight ranking, approximate CPU projection/sort or dense HxWx128 event array is used.

This is the calibrated CPU C++ arithmetic over pinned CUDA state explicitly allowed by the inherited and amended protocols. It is **not** a claim of bitwise equivalence to GPU floating-point arithmetic. Stock black/white RGB, final transmittance, original IDs/depth/order, full intrinsics and original native-prefix agreement pass the inherited tolerances. The largest G0 RGB replay discrepancy is Chair ~0.002909, within 1/255; the other scenes' exact errors are saved. Gaussian camera-center z is not a measured physical surface.

## G0 calibration

Same preregistered native 800×800 TRAIN view 1 for all scenes; tau=.90 and .95, each at Kmax=32/64/128. Foreground is native alpha>=.5.

| Scene | Aggregate foreground alpha captured | Foreground pixels reaching 90% | K p50/p75/p90/p95/p99/max | Stored events | CSR MiB |
|---|---:|---:|---|---:|---:|
{chr(10).join(rows)}

Kmax=64 fails Ficus on both required measures: 89.340695% aggregate capture and 79.591341% of foreground pixels reaching 90%. Kmax=32 fails multiple scenes. Therefore 128 is the smallest common qualifying cap. Tau=.95 remains sensitivity evidence and did not rescue G0. [G0_COVERAGE.csv]({art}/G0_COVERAGE.csv) gives all 24 configurations, foreground K quantiles, target-reached fractions, >=90% fractions, aggregate capture, event counts and memory. Per-configuration JSON additionally includes all-pixel K quantiles, stock replay and provenance checks; execution access audits are linked below.

Each qualified prefix is compressed using the frozen local scale max(.002*front, median absolute valid 5x5 neighboring front-depth differences excluding center, 1e-12). Adjacent gap>3*scale splits layers. Retain the earliest four; preserve all assignments/histograms in layer CSR and explicit overflow/tail mass and RGB. Minimum seeding mass is .05*native alpha plus inherited absolute layer mass>=.1 and A>=.5. No residual renormalization. Across all 16 G1 views the retained four layers capture 90.3901–92.5243% aggregate native foreground alpha; overflow is 0.1584–2.4826% of prefix mass. Median layer count is one, with localized higher counts. [G1_LAYER_SUMMARY.json]({art}/G1_LAYER_SUMMARY.json) contains every view and conservation errors.

## G1 execution and visual decision

Lego, Chair, Drums and Ficus each use frozen TRAIN views [1,27,53,79], native 800×800. Channels remain separate: E_occ, E_layer, E_shape_ridge and E_shape_valley. Raw ID turnover alone cannot activate lines. Responses use frozen common normalization, normal NMS and orientation-aware hysteresis at both grids 95/70 and 90/60; no raw-band cleanup and no global Top-N construction output. Matched-ink rankings exist only for pairwise comparisons.

All 18 controls were completed for every view: full, expected depth, front depth, median depth, depth distribution without IDs, uniform weights, shuffled IDs, shuffled depths, previous density-only, RGB Canny, first k=4/8/16, tau95/K128, tau90/K32/K64, tau95/K32/K64. No-ID preserves geometry including exact weighted W1 and removes identity factors/compatibility. Shuffles preserve the frozen seed and valid-slot provenance. All arrays, thresholds, orientations/scales, NMS anchors, centerlines, raw bands and matched comparisons are saved.

- **Lego — NO_GO.** Valley responses show some wheel arcs, cabin/frame and lift-arm/bucket fragments. Occlusion/ridge evidence is fragmented and includes base/stud texture. Depth-only completes more recognizable connected model contours at matched ink. Full/no-ID/uniform shape fields remain similar; E_layer is sparse and lacks a coherent family.
- **Chair — NO_GO.** Some arm, seat and back-rail fragments are recognizable. Occlusion contains upholstery-like interior patches and broken contours. Full occasionally reduces interior clutter but misses substantial chair outline, especially in the rear view. Depth controls are more complete; no-ID keeps similar useful shape fragments. Layer evidence remains sparse.
- **Drums — NO_GO.** Partial cymbal/drum rim arcs and stand segments are useful, but the full method omits much of the kit. Depth controls complete more circular rims and supports; no-ID retains similar curves. Layer evidence is isolated and weak.
- **Ficus — NO_GO.** Occlusion yields short leaf/pot fragments; valley favors leaf patches and loses much stem/pot structure. Front/median/expected depth gives more complete contours. No-ID/uniform resembles full; cap/mass sensitivities do not establish the required advantage.

Every official G1 figure was inspected as a complete overview, with E_occ and E_shape_valley group0 also inspected in 24 exact-pixel single-view crops for views 1/27/53 across the four scenes. View 79 is included in all sheet overviews. I do not claim native-resolution scrutiny of every one of the thousands of panels. Three detailed fixed views per scene fail the comparative criterion, so exact counts of recognizable coherent bands were not invented or used to reject the method. This is model review, not an independent human study. [G1_VISUAL_REVIEW.json]({art}/G1_VISUAL_REVIEW.json) records each figure hash and findings; [INSPECTION_CROPS.json]({art}/INSPECTION_CROPS.json) proves crops are unchanged pixels of their parents.

The numerical ID-null proxy is a qualified positive for occlusion, not a scientific GO. At grid 95/70, full-minus-control long-component ink fractions are:

| Scene | E_occ minus no-ID, range over views | E_occ minus shuffled-ID | E_occ joint >=.05 views | Shape ridge joint views | Shape valley joint views | E_layer joint views |
|---|---:|---:|---:|---:|---:|---:|
{chr(10).join(nullrows)}

Occlusion passes the numerical proxy in all four views of every scene. Its required visible advantage over depth-only is absent. Useful shape-valley bands have no qualifying joint ID-null views and are visually similar without IDs. Numerical connectivity cannot replace recognizable structure and uncapped-soft evidence under the frozen gate. No full ID-mechanistic GO is claimed. [G1_CONTROL_METRICS.csv]({art}/G1_CONTROL_METRICS.csv) contains all 2,304 per-control/view/channel/grid rows; [G1_CONTROL_SUMMARY.json]({art}/G1_CONTROL_SUMMARY.json) includes both grids and every null difference. No single scene or sensitivity setting was used as a rescue.

## Verification and artifacts

G0 verification passes for 57 scientific files per independent run, all 48 saved configuration checks, exact byte/array equality, and 16 PNG decodes. G1 verification passes for {len(g1['hashes']['g1_run'])} scientific files per independent run, {len(g1['arrays']['g1_run'])} NPZ files per run, all {len(g1['controls'])} control semantic checks across both runs, all {len(g1['native'])} native views, exact byte/array equality and {g1['decoded_pngs']} PNG decodes. These include replay, shortest CSR prefixes, IDs/order/provenance, frozen camera K/w2c, layer conservation/grouping/centroids/RGB/histograms, control transforms, normalization, band thresholds/inclusion/nesting, matched comparisons and metrics. Layout-only diagnostic generation verifies all scientific NPZ/JSON hashes before and after; both diagnostic families also rerun byte-identically.

The full untraced suite passes all 196 tests in 56.574 s, including all 164 pre-existing tests. The outer access-traced suite is OK for 196 tests with one skip (87.937 s): its nested-strace layout integration test cannot run under an existing ptrace tracer. That exact integration test passes in the untraced full suite and its targeted GREEN, where it performs and audits actual Landlock-confined rendering. [TEST_SUMMARY.json]({art}/TEST_SUMMARY.json) records every unittest execution, exact command and log hash, including retained failures. No scientific test failure was hidden. All completed full-suite native-open traces pass the access audit, including the earlier failed nested-ptrace harness attempt.

Strict vertical-slice TDD has {len(integrity['tdd'])} completed behavioral RED/GREEN pairs, with exact argv, command/log/source/protocol hashes and timestamps. Retained unsuccessful setup/fixture attempts include: indentation error before corrected RED22/GREEN23; band-audit low-percentile fixture correction after GREEN55 failure; decimal tie fixture not exactly tied before corrected binary-valued RED61/GREEN62; and nested ptrace failure in outer suite 90 before the separate traced/untraced verification arrangement. The valid behavioral RED precedes each final GREEN; none of these failed attempts is represented as a passing test.

A partial first G1 engineering run was interrupted only at its own worker PID 186025 after an exact-distance tie test exposed rear-layer selection. Its {integrity['archived_attempt_files']} files, original sources/binary, trace and partial output are preserved under attempt_01_layer_tie and excluded from science. No normalized scene line output, final bands or line figures from that attempt were inspected. Earliest-layer tie handling was fixed through TDD; batched Hessians also pass bit-identical separate-scale parity on synthetic and saved Lego layer data. The first final-bookkeeping audit also rejected the G1 freeze because its helper compared the entire sha256sum line with a bare digest; parsing the first field corrected that bookkeeping check without changing the frozen file. Scientific thresholds were not altered. All qualifying production and rerun outputs use the same final producer sources.

Complete clickable [figure index]({art}/FIGURES.md), including every official sheet and all enlarged fixed-view comparison crops. Scientific output directories:

- [G0 run]({out}/run), [G0 independent rerun]({out}/rerun): 24 CSR NPZ/JSON configurations and eight full sheets each.
- [G1 run]({out}/g1_run), [G1 independent rerun]({out}/g1_rerun): native stream records, 288 raw and 288 final control NPZ/JSON pairs, normalization and complete figures each.
- Each G1 run has 52 main sheets: 48 comparisons at 16000×5064 pixels and four RGB references at 3200×844. Every comparison panel preserves native 800×800 evidence. Each has 16 diagnostic sheets at 3200×6752. There are 76 unique official figures across G0/G1; independent duplicates match bytes. No final-mask-only selection, omitted controls or video claim.
- [G0 verification]({art}/VERIFICATION.json), [G1 verification]({art}/G1_VERIFICATION.json), [final access audit]({art}/FINAL_ACCESS_AUDIT.json), [integrity audit]({art}/FINAL_INTEGRITY.json), and [curated gates]({art}/GATES.json). Worker G1 GATES snapshots remain AWAITING_VISUAL_REVIEW to preserve their original bytes; the curated artifact records this completed NO_GO review.

## Access, resources and limitations

Scientific workers were Landlock-confined before asset decoding; native successful opens including bootstrap/imports were traced and audited. Final audit has zero forbidden successful opens and zero unparsed open lines. TEST source images/cameras/evidence were not selected for science; C/DEV evaluation evidence was not used. G1 views are TRAIN views and also members of F; no G2 F-stage samples were constructed. The frozen INPUTS.json preserves the older foundation's base_head as provenance; the active branch/base is the user-specified 062d7ce.

Bookkeeping preservation hashing read historical tracked files as opaque bytes, including 62 TEST-named historical outputs. They were not decoded or used for construction, threshold selection or evaluation. BOOKKEEPING_SCOPE.json lists this explicitly; session-wide zero reads of every TEST-named historical file is not claimed. This distinction is part of the access record, not omitted.

Processes and GPU state were inspected repeatedly. Each worker processed scenes sequentially on GPU 1 with OMP/BLAS/MKL=1. Independent run/rerun workers overlapped when resources allowed; unrelated processes were never killed. No GPU process remained at the final production check. The complete output family occupies about 58.8 GiB including independent reruns and the archived attempt. Raw controls deliberately retain full provenance, so disk cost is substantial despite CSR; exact CSR memory/event counts are reported separately from archive disk usage.

The study is limited to the frozen four-scene, four-view G1 construction assessment and calibrated native replay tolerance. Higher alpha completeness does not establish a line mechanism. No held-out lifting/reprojection, G2 null study, multiview 3D line result or video is claimed because the protocol requires stopping at G1 NO_GO. There is no unresolved engineering blocker in the reached stages; these are scientific and scope limitations.

## Changed files and commands

All changes are additive: the 17 code/test files below, artifacts/adaptive_mass_layered_probe/, out/adaptive_mass_layered_probe/, and this external report. Old APIs/tests and all tracked files are unchanged. Exact operational helper files and artifact hashes are included in [FINAL_SEAL.json]({art}/FINAL_SEAL.json). The seal is generated last, directly with `/home/u00134/bin/miniconda3/envs/vfsdgs/bin/python artifacts/adaptive_mass_layered_probe/seal_delivery.py`, after the command index is regenerated; it excludes itself from its hashes.

{files}

Full exact execution/TDD command index: [COMMANDS.md]({art}/COMMANDS.md); machine-readable journal: [TDD.jsonl]({art}/TDD.jsonl). Commands ran in `{ROOT}` with PYTHONPATH=.:tests, PYTHONDONTWRITEBYTECODE=1, OMP_NUM_THREADS=OPENBLAS_NUM_THREADS=MKL_NUM_THREADS=1, OMP_WAIT_POLICY=PASSIVE and CUDA_VISIBLE_DEVICES=1. Key completed commands and log hashes:

{commands}
'''
report.write_text(text)
readme=f'''# Adaptive mass layered probe

Completed: **G0 PASS at tau=.90/Kmax=128; G1 NO_GO (0/4 scenes qualifying); G2/G3 NOT_RUN.** Both reached stages pass deterministic, semantic, access and preservation verification. Full suite:196 tests pass. No commit or push; prior fixed-k negative result is unchanged.

- [Frozen amendment](PROTOCOL.md), [inherited science](INHERITED_PROTOCOL.md), [frozen G1 details](G1_IMPLEMENTATION.md).
- [Complete figure index](FIGURES.md).
- [Final gates](GATES.json), [G0 coverage](G0_COVERAGE.csv), [G1 controls](G1_CONTROL_METRICS.csv), [G1 visual review](G1_VISUAL_REVIEW.json).
- [G0 verification](VERIFICATION.json), [G1 verification](G1_VERIFICATION.json), [final access audit](FINAL_ACCESS_AUDIT.json), [preservation/TDD integrity](FINAL_INTEGRITY.json).
- [Exact commands](COMMANDS.md), [machine journal](TDD.jsonl), [historical TEST-byte-hash scope](BOOKKEEPING_SCOPE.json), [excluded engineering attempt](ATTEMPT_01.json).
- Complete arrays and full-resolution sheets: [G0](../../out/adaptive_mass_layered_probe/run), [G1](../../out/adaptive_mass_layered_probe/g1_run); independent reruns alongside them. G1 figures include all 18 controls, 16 fixed TRAIN views, separate channels, uncapped soft fields, both raw hysteresis grids and matched comparisons. No video stage reached.
- [Complete report]({report}).

Curated GATES.json includes the final review; immutable worker G1 GATES snapshots retain their pre-review status. Scientific TEST inputs were sealed; historical tracked TEST-named artifacts were only byte-hashed for preservation as disclosed. No C/DEV evaluation or G2 F-stage construction occurred.
'''
(art/'README.md').write_text(readme)
print('Final report and curated NO_GO gates written:',report)
