"""Administrative aggregation of frozen, already evaluated outputs; no fitting."""
import json,hashlib
from pathlib import Path
import numpy as np
root=Path.cwd();art=root/'artifacts/direct_curve_global_fit_probe';out=root/'out/direct_curve_global_fit_probe'
journal=[json.loads(x) for x in (art/'JOURNAL.jsonl').read_text().splitlines()]
resources=[json.loads(x) for x in (out/'setup/RESOURCES.jsonl').read_text().splitlines()]
summary={};rows=[];assetdir=art/'curves';assetdir.mkdir(exist_ok=True)
for scene in ['lego','chair','drums','ficus']:
 base=out/'run'/scene;result=json.loads((base/'evaluate/RESULTS.json').read_text());seal=json.loads((base/'fit/SEAL.json').read_text());census=json.loads((base/'evaluate/CENSUS.json').read_text())
 s=dict(arms=result['arms'],F=result['F'],necessary_gates=result['gates'],ambiguity=result['ambiguity'],chosen=seal['chosen'],objectives=seal['objective_components'],domain=result['domain'],census={})
 for split in ['F','C']:
  s['census'][split]={}
  for arm in ['D','I','L']:
   cc=census[split][arm];s['census'][split][arm]=dict(all_cells=len(cc),empty_evidence_cells=sum(c['targets']==0 for c in cc),nonempty_interior_cells=sum(c['strata']['interior']['targets']>0 for c in cc),unknown_tangent_targets=sum(c['unknown_targets'] for c in cc))
 for arm,key in seal['chosen'].items():
  with np.load(base/'fit'/(key+'.npz')) as f:
   controls=f['control'];active=f['active'];gates=f['gate']
  asset=dict(scene=scene,arm=arm,chosen_fit=key,width_native=1.5,opacity=1,color=[0,0,0],coordinate_system='inherited world coordinates',source_npz=str(base/'fit'/(key+'.npz')),source_sha256=seal['assets'][key],curves=[dict(id=i,active=bool(active[i]),control_points=controls[i].tolist(),gate=float(gates[i])) for i in range(128)])
  (assetdir/f'{scene}_{arm}.json').write_text(json.dumps(asset,sort_keys=True,indent=2)+'\n')
  a=s['arms'][arm];rows.append([scene,arm,*[a[k] for k in ['interior_coverage','outline_coverage','coverage','equal_cell_coverage','unsupported_fraction','precision','beyond4_fraction','actual_ink','active_curves']]])
 s['temporal']={}
 for arm in ['D','I','L','depth2d']:
  rr=[r for arc in result['arcs'] for r in arc['motion_defects'][arm]]
  x=dict(transitions=len(rr),motion_popping_components=sum(r['popping_components'] for r in rr),appearing_pixels=sum(r['appearing_pixels'] for r in rr),disappearing_pixels=sum(r['disappearing_pixels'] for r in rr),mean_motion_disagreement=float(np.mean([r['motion_disagreement'] for r in rr])),mean_actual_ink=float(np.mean([r['current_ink'] for r in rr])),unknown_previous_pixels=sum(r['unknown_previous_pixels'] for r in rr))
  if arm!='depth2d':
   frames=[r[arm] for arc in result['arcs'] for r in arc['frame_metrics']]
   x.update(id_popping_count=sum(arc['temporal'][arm]['popping_count'] for arc in result['arcs']),doubling_pairs_frame_sum=sum(r['doubling_pairs'] for r in frames),doubling_length_frame_sum=sum(r['doubling_length'] for r in frames),detachment_runs_frame_sum=sum(r['detachment_runs'] for r in frames),detachment_samples_frame_sum=sum(r['detachment_samples'] for r in frames),visible_length_frame_sum=sum(r['visible_length'] for r in frames))
  s['temporal'][arm]=x
 ratio=s['temporal']['I']['mean_actual_ink']/max(1e-20,s['temporal']['depth2d']['mean_actual_ink']);s['temporal']['I']['depth2d_ink_ratio']=ratio;s['temporal']['I']['comparable_ink']=.8<=ratio<=1.25
 labels=[f'FIT_V2_{scene}',f'RERUN_FIT_{scene}',f'EVALUATE_run_{scene}',f'EVALUATE_rerun_{scene}']
 if scene in ['lego','chair']:labels+=[f'FIT_{scene.upper()}']
 costs=[dict(label=r['label'],seconds=r['seconds'],exit=r['exit']) for r in journal if r['label'] in labels]
 samples=[w for r in resources for w in r['workers'] if f'--scene {scene} ' in w['command'] and w.get('gpu_MiB') is not None]
 s['cost']=dict(worker_wall_seconds_including_rerun_and_excluded=sum(r['seconds'] for r in costs),records=costs,conservative_gpu_hours=sum(r['seconds'] for r in costs)/3600,within_12_gpu_hours=sum(r['seconds'] for r in costs)<=43200,observed_gpu_MiB=max([int(w['gpu_MiB']) for w in samples] or [0]),observed_process_VmHWM_KiB=max([int(w.get('VmHWM','0 kB').split()[0]) for w in samples] or [0]),memory_sampling_seconds=30)
 s['per_arm_fit_seconds']={arm:sum(json.loads(p.read_text())['seconds'] for run in ['run','rerun'] for p in (out/run/scene/'fit').glob(arm+'_*.json')) for arm in ['D','I','L']}
 summary[scene]=s
(art/'SUMMARY.json').write_text(json.dumps(summary,sort_keys=True,indent=2)+'\n')
header='| Scene | Arm | C interior | C outline | C overall | Equal-cell | Unsupported | Evaluable precision | Beyond4px | Mean actual ink | Active |\n|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|\n'
def pct(v):return 'undefined' if v is None else f'{100*v:.2f}%'
body=''.join('| '+' | '.join([r[0],r[1],*[pct(v) for v in r[2:9]],f'{r[9]:.1f}',str(r[10])])+' |\n' for r in rows)
(art/'RESULTS.md').write_text('# Frozen native800 held-out results\n\n'+header+body+'\nCoverage is weighted by equally spaced boundary samples (two native pixels per sample); equal-cell averages use nonempty target cells and retain all empty cells in CENSUS.json. Unknown visibility earns no support and contributes to unsupported ink. Actual ink is summed antialiased raster coverage, not centerline length. Precision excludes unknown visibility from its denominator; unsupported ink includes it. No scene/cell replacements.\n')
print(json.dumps({s:dict(gates=v['necessary_gates'],cost=v['cost']) for s,v in summary.items()},indent=2))
