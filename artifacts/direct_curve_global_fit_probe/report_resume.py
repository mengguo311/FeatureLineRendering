"""Assemble report only after independent engineering verification and actual review."""
import argparse,json,shlex,shutil,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from scripts.schedule_direct_curve_probe import atomic_json,sha
ART=Path(__file__).resolve().parent;OUT=ROOT/'out/direct_curve_global_fit_probe'

def calibration_summary():
 summaries={}
 for run in ['run','rerun']:
  for scene in ['lego','chair','drums','ficus']:
   path=OUT/'scheduler/resume_20260929_v2'/run/'calibration'/f'{scene}_all/RESULT.json';v=json.loads(path.read_text());assert v['passed'] and v['frames']==82
   groups={}
   for group,prefix in [('F','F_'),('C','C_'),('arcs','arc')]:
    rows=[row for row in v['rows'] if row['frame'].startswith(prefix)]
    groups[group]=dict(frames=len(rows),maximum_errors={key:max(row['errors'][key] for row in rows) for key in ['rgb_max','alpha_max','wrapper_max']},legacy_changed_values={key:dict(total=sum(row['legacy_changed_values'][key] for row in rows),maximum_per_frame=max(row['legacy_changed_values'][key] for row in rows),frames_with_changes=sum(row['legacy_changed_values'][key]>0 for row in rows),scalar_denominator=len(rows)*800*800*(3 if key=='quantiles' else 1)) for key in ['alpha','quantiles','front']})
   summaries[run+':'+scene]=dict(source=str(path),source_sha256=sha(path),threshold=v['threshold'],groups=groups,rows=v['rows'],source_hashes=v['source_hashes'])
 return summaries

def resource_summary():
 path=OUT/'scheduler/resume_20260929_v2/RESOURCES.jsonl';workers={};samples=0
 for line in path.read_text().splitlines():
  row=json.loads(line);samples+=1
  for worker in row['workers']:
   command=shlex.split(worker['command'])
   if not command or Path(command[0]).name!='python':continue
   pid=worker['pid'];v=workers.setdefault(str(pid),dict(command=command,scene=command[command.index('--scene')+1],run=command[command.index('--run')+1],cpu_seconds_observed=0,gpu_MiB_observed_peak=0,host_HWM_KiB_observed=0,samples=0))
   v['samples']+=1;v['cpu_seconds_observed']=max(v['cpu_seconds_observed'],worker['cpu_seconds']);v['gpu_MiB_observed_peak']=max(v['gpu_MiB_observed_peak'],worker.get('gpu_MiB') or 0);v['host_HWM_KiB_observed']=max(v['host_HWM_KiB_observed'],int(worker.get('VmHWM','0 kB').split()[0]))
 scenes={}
 for scene in ['lego','chair','drums','ficus']:
  values=[v for v in workers.values() if v['scene']==scene]
  scenes[scene]=dict(cpu_seconds_observed=sum(v['cpu_seconds_observed'] for v in values),worker_gpu_MiB_observed_peak=max([v['gpu_MiB_observed_peak'] for v in values],default=0),worker_host_HWM_KiB_observed=max([v['host_HWM_KiB_observed'] for v in values],default=0))
 return dict(source=str(path),source_sha256=sha(path),sample_rows=samples,scenes=scenes,workers=workers,scope='15-second sampling from resume monitor startup. CPU seconds are lower bounds; GPU/host maxima are per-worker observed peaks, not aggregate or complete lifetime peaks. Historical jobs and short unsampled jobs are absent. strace processes excluded.')

def temporal_summary(result):
 rows={}
 for arm in ['D','I','L','depth2d']:
  motion=[v for arc in result['arcs'] for v in arc['motion_defects'][arm]]
  ink=[]
  for arc in result['arcs']:
   transitions=arc['motion_defects'][arm]
   ink.extend([transitions[0]['previous_ink']]+[v['current_ink'] for v in transitions])
  rows[arm]=dict(transitions=len(motion),popping_components=sum(v['popping_components'] for v in motion),
    mean_motion_disagreement=sum(v['motion_disagreement'] for v in motion)/len(motion),
    mean_actual_ink=sum(ink)/len(ink),ink_frames=len(ink),
    appearing_pixels=sum(v['appearing_pixels'] for v in motion),disappearing_pixels=sum(v['disappearing_pixels'] for v in motion),
    unknown_previous_pixels=sum(v['unknown_previous_pixels'] for v in motion))
  if arm!='depth2d':
   frames=[v[arm] for arc in result['arcs'] for v in arc['frame_metrics']]
   assert len(ink)==len(frames)==66
   assert abs(sum(ink)-sum(v['actual_ink'] for v in frames))<=1e-6
   rows[arm].update(id_pops=sum(arc['temporal'][arm]['popping_count'] for arc in result['arcs']),id_transition_denominator=len(motion)*128,
    frames=len(frames),doubling_pairs=sum(v['doubling_pairs'] for v in frames),doubling_length=sum(v['doubling_length'] for v in frames),
    detachment_runs=sum(v['detachment_runs'] for v in frames),detachment_samples=sum(v['detachment_samples'] for v in frames),detachment_length=sum(v['beyond4_length'] for v in frames),visible_length=sum(v['visible_length'] for v in frames))
   rows[arm]['id_pop_rate']=rows[arm]['id_pops']/rows[arm]['id_transition_denominator']
   rows[arm]['doubling_visible_length_fraction']=rows[arm]['doubling_length']/rows[arm]['visible_length'] if rows[arm]['visible_length'] else None
   rows[arm]['detachment_visible_length_fraction']=rows[arm]['detachment_length']/rows[arm]['visible_length'] if rows[arm]['visible_length'] else None
 ratio=rows['I']['mean_actual_ink']/max(rows['depth2d']['mean_actual_ink'],1e-20)
 rows['I'].update(depth2d_ink_ratio=ratio,comparable_ink=.8<=ratio<=1.25)
 return rows

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--proof',required=True);ap.add_argument('--review',required=True);args=ap.parse_args()
 proof=Path(args.proof);verified=json.loads((proof/'VERIFICATION.json').read_text());assert verified['passed'],verified['failed']
 review=json.loads(Path(args.review).read_text());assert review['scope']=='internal implementing-model review'
 budgets=json.loads((proof/'BUDGETS.json').read_text());cfg=json.loads((ART/'INPUTS.json').read_text());rows={};gates={}
 resources=resource_summary();atomic_json(ART/'RESOURCES_SUMMARY.json',resources)
 calibration=calibration_summary();atomic_json(ART/'CALIBRATION_SUMMARY.json',calibration)
 for scene in ['lego','chair','drums','ficus']:
  r=json.loads((OUT/'run'/scene/'evaluate/RESULTS.json').read_text());s=json.loads((OUT/'run'/scene/'fit/SEAL.json').read_text());v=review['scenes'][scene]
  assert len(v['C_views_reviewed'])==8 and v['arc_frames_reviewed']==[33,33]
  g=dict(r['gates']);g['budget']=budgets[scene]['within_12_hours'];g['visual']=v['legibility_no_worse_than_depth2d'] and v['temporal_defects_fewer_at_comparable_ink']
  g['continue']=all(g[k] for k in ['precision','retain_depth','extra_rgb','global_coupling','unambiguous','visual','budget'])
  numeric=all(g[k] for k in ['precision','retain_depth','extra_rgb','global_coupling','unambiguous'])
  decision='NO_GO' if not numeric else 'INDEPENDENT_VISUAL_REVIEW_REQUIRED'
  if not g['budget']:decision='COMPUTE_BUDGET_EXHAUSTED'
  gates[scene]=dict(engineering_valid=True,necessary_numeric_pass=numeric,internal_visual_pass=g['visual'],gates=g,decision=decision)
  rows[scene]=dict(result=r,seal=s,budget=budgets[scene],visual_review=v,temporal=temporal_summary(r))
  curves=ART/'curves';curves.mkdir(exist_ok=True)
  for arm,key in s['chosen'].items():
   import numpy as np
   with np.load(OUT/'run'/scene/'fit'/(key+'.npz')) as f:
    payload=dict(scene=scene,arm=arm,chosen=key,source_sha256=s['assets'][key],width_native=1.5,opacity=1.,control=f['control'].tolist(),active=f['active'].tolist(),gate=f['gate'].tolist(),stable_ids=list(range(128)))
   atomic_json(curves/(scene+'_'+arm+'.json'),payload)
 verdict='NO_GO' if all(not g['necessary_numeric_pass'] for g in gates.values()) else 'INDEPENDENT_VISUAL_REVIEW_REQUIRED_FOR_NUMERICALLY_PASSING_SCENES'
 atomic_json(ART/'SUMMARY_RESUME.json',rows);atomic_json(ART/'GATES.json',dict(decision=verdict,scenes=gates,independent_human_validation=False))
 def pct(x):return 'undefined' if x is None else f'{100*x:.2f}%'
 lines=[f'# Direct fixed-3D-curve D/I/L probe: {verdict}', '', 'All four preregistered scenes, three arms, three starts, full/LOO fits and independent reruns were completed. The scope is the frozen 128-span, 300-step configuration and the declared F/C/interpolation domain. Mesh was not used; TEST/DEV imagery was not opened.', '', '| Scene | Arm | C interior | C outline | C coverage | Unsupported | Evaluable precision | Beyond 4px |', '|---|---|---:|---:|---:|---:|---:|---:|']
 for scene,v in rows.items():
  for arm,a in v['result']['arms'].items():lines.append('| '+' | '.join([scene,arm,*[pct(a[k]) for k in ['interior_coverage','outline_coverage','coverage','unsupported_fraction','precision','beyond4_fraction']]])+' |')
 lines+=['', '| Scene | Precision | Retain D | Extra RGB | Global coupling | Unambiguous | Budget | Decision |','|---|---|---|---|---|---|---|---|']
 for scene,v in gates.items():lines.append('| '+' | '.join([scene,*['PASS' if v['gates'][k] else 'FAIL' for k in ['precision','retain_depth','extra_rgb','global_coupling','unambiguous','budget']],v['decision']])+' |')
 lines+=['', '| Scene | I−D interior gain (percentage points) | Improved nonempty interior cells | I−L C coverage (percentage points) | Largest eligible I ambiguity disagreement |', '|---|---:|---:|---:|---:|']
 for scene,v in rows.items():
  arms=v['result']['arms'];i,d,l=[arms[k] for k in ['I','D','L']];gain=100*(i['interior_coverage']-d['interior_coverage']) if i['interior_coverage'] is not None and d['interior_coverage'] is not None else None
  ambiguity=v['result']['ambiguity']['I']['reserved_disagreement'];maximum=max(ambiguity.values()) if ambiguity else None
  gain_text='undefined' if gain is None else f'{gain:.2f}'
  lines.append(f"| {scene} | {gain_text} | {pct(i['improved_cell_fraction'])} | {100*(i['coverage']-l['coverage']):.2f} | {pct(maximum) if maximum is not None else 'no eligible pair'} |")
 lines+=['', 'Numerical failures can deny continuation without independent visual approval. Internal implementing-model inspection is not independent validation; no independent visual GO is claimed. Counts retain all 64 cells per F/C view (512 per split/scene/arm), including empty cells. Unknown visibility earns no support. C is held out from curve fitting but belongs to frozen GS TRAIN. Arc imagery is renderer-domain evidence, not unseen real photographs.', '', '## Internal visual review', '']
 for scene,v in rows.items():
  key=json.loads((OUT/'run'/scene/'evaluate/REVIEW_KEY.json').read_text())
  mapping=', '.join(f'{chr(65+i)} = {name}' for i,name in enumerate(key['order']))
  lines += [f'### {scene}', '', mapping+'. Initial observations and reviewed file hashes are preserved in BLINDED_REVIEW_* records; REVIEW_METHOD.md describes the review limits.', '', *['- '+x for x in v['visual_review']['observations']], '']
 lines+=['| Scene | Method | Mean arc ink | Shared popping components / transitions | Mean motion disagreement | ID pops / ID transitions |','|---|---|---:|---:|---:|---:|']
 for scene,v in rows.items():
  for arm,t in v['temporal'].items():
   ids=f"{t['id_pops']} / {t['id_transition_denominator']}" if arm!='depth2d' else 'not applicable'
   lines.append(f"| {scene} | {arm} | {t['mean_actual_ink']:.1f} | {t['popping_components']} / {t['transitions']} | {t['mean_motion_disagreement']:.4f} | {ids} |")
 lines+=['','| Scene | I/depth2D arc ink ratio | Comparable ink |','|---|---:|---|']
 for scene,v in rows.items():
  t=v['temporal']['I'];lines.append(f"| {scene} | {t['depth2d_ink_ratio']:.4f} | {'yes' if t['comparable_ink'] else 'no'} |")
 lines+=['','Mean arc ink includes all 66 frames per scene; motion proxies use the 64 within-arc transitions. Persistent-ID popping has no direct 2D-depth analogue. Shared motion disagreement advects previous ink with frozen GS median depth and inherits its errors; component counts are proxies, not human defect rates. All framewise doubling, detachment, visibility and census data are retained, with aggregate lengths/counts and denominators in SUMMARY_RESUME.json.','']
 lines += ['## Engineering evidence', '', 'The original CPU replay failed Lego arc0_005 because CUDA fused quadratic arithmetic crossed the native alpha cutoff. The replacement independently accumulates RGB/transmittance and contribution-depth quantiles on CUDA using the stock expression. It receives no stock final_T or stock RGB. The literal 1/255 calibration gate, scientific thresholds, objective, capacity, optimizer and camera domain are unchanged. All 82 preregistered views/frames per scene were explicitly calibrated in both runs before resumed evaluation. Detailed arithmetic, regressions, hashes and the preserved failed summary attempt are documented in REPLAY_REPAIR.md.', '', 'The traced suite completed 226 tests: 225 passed and one expected nested-strace test was skipped. Its access audit found zero forbidden successful opens and no unparsed calls. The cutoff regression has observed RED/GREEN evidence, and the independent synthetic oracle invokes unchanged upstream FORWARD::render. Scheduler tests cover failure independence, exclusive atomic seals and preserved-fit hash checks. Final verification checks unchanged Lego fit/proposal/native arrays, both optimization runs, fixed world geometry on all 82 frames, all media decoding, native calibration, source provenance, preserved attempts and scene budgets.', '', f'Proof: {proof}/VERIFICATION.json; COMPARISON.json; GEOMETRY.json; MEDIA.json; ACCESS.json; BUDGETS.json. Exact scene-stage commands, access traces, immutable stage seals, process records and resource samples are under out/direct_curve_global_fit_probe/scheduler/resume_20260929_v2/.', '', 'The original sequential launchers were preserved and replaced with a scene-stage scheduler. All missing scene fits run before evaluations; a scene evaluation failure cannot prevent other fitting. Evaluation reruns archive old directories and hash inventories. No existing fit or output is overwritten, and no sealed Lego asset is refitted. An atomic completion seal is published only after a successful stage and access audit.', '', '| Scene | Conservatively charged GPU-hours | Ceiling |','|---|---:|---:|']
 for scene,b in budgets.items():lines.append(f"| {scene} | {b['conservative_gpu_hours']:.3f} | 12 |")
 lines+=['', '| Scene | Observed CPU seconds | Peak worker GPU MiB | Peak worker host HWM MiB |', '|---|---:|---:|---:|']
 for scene,v in resources['scenes'].items():lines.append(f"| {scene} | {v['cpu_seconds_observed']:.1f} | {v['worker_gpu_MiB_observed_peak']} | {v['worker_host_HWM_KiB_observed']/1024:.1f} |")
 lines+=['', 'The conservative charge includes both runs, historical excluded/interrupted attempts, native preparation and evaluation; interrupted fits receive an additional full 30-minute allowance. CPU wall time is charged while holding a GPU; this is not a kernel profiler. Per-fit 300-step/30-minute allocations remain fixed. GPU process memory, CPU time and process VmHWM are sampled every 15 seconds after the resume monitor starts; these are observed peaks, not complete lifetime GPU peaks. Existing shared GPU jobs were checked before every stage.', '', '## Artifacts and limitations', '', 'Full-resolution F/C panels, complete ordered arc frames, playable videos, quartile sheets, all-frame contacts, metrics, census and alternative-asset ambiguity drawings are under out/direct_curve_global_fit_probe/{run,rerun}/SCENE/evaluate/. Curated selected control points and active stable IDs are in curves/. FIGURES.md links the original outputs. Frozen protocol and input hashes are unchanged.', '', 'The domain has two nearby 33-frame arcs per scene; this does not establish arbitrary-view reconstruction. Drums/Ficus retain inherited GS posterior qualification limitations. The binary image detector is uncalibrated. Fitted curves use finite proposals, fixed capacity and local optimization. Visibility uses frozen GS depth and inherits its errors. Temporal defect proxies are not human defect rates. Comparability requires the frozen [0.8,1.25] ink ratio; no framewise ink deletion or post-hoc tuning was performed. Conclusions apply only to this preregistered bounded experiment.', '']
 lines += [f'Final engineering verification passed {len(verified["checks"])} checks. Exhaustive replay calibration covered {sum(g["frames"] for v in calibration.values() for g in v["groups"].values())} scene/run/view combinations; maximum RGB, alpha and wrapper errors were '+str({key:max(g['maximum_errors'][key] for v in calibration.values() for g in v['groups'].values()) for key in ['rgb_max','alpha_max','wrapper_max']})+'. CALIBRATION_SUMMARY.json retains per-frame legacy differences and exact source hashes.', '', 'The first administrative delivery verification attempt and its audit-filename correction are preserved in DELIVERY_VERIFICATION_ATTEMPTS.md. No scientific output was altered to satisfy verification.', '', '[Complete comparison gallery](index.html) · [Portable proof](proof/VERIFICATION.json) · [Review method](REVIEW_METHOD.md)', '']
 text='\n'.join(lines)+'\n'
 for path in [ART/'REPORT.md',Path('/home/u00134/codex_astra_direct_curve_global_fit_probe_report.md')]:
  with path.open('x') as f:f.write(text)
 figures=['# Complete evidence','']
 for scene in rows:
  base=OUT/'run'/scene/'evaluate';figures += [f'## {scene}','']
  for i in cfg['C']:figures.append(f'- [C {i}]({base}/figures/C_{i}.png)')
  for j in range(2):
   figures.append(f'- [Complete arc {j} video]({base}/videos/arc{j}_complete.mp4)')
   figures.append(f'- [Arc {j} quartiles]({base}/figures/arc{j}_quartiles.png)')
   for page in range(6):figures.append(f'- [Arc {j} frames page {page}]({base}/figures/arc{j}_allframes_{page}.png)')
  figures.append('')
 with (ART/'FIGURES.md').open('x') as f:f.write('\n'.join(figures)+'\n')
 print(json.dumps(dict(verdict=verdict,report=str(ART/'REPORT.md')),indent=2))
if __name__=='__main__':main()
