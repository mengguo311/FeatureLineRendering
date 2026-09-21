"""Read-only tabulation of the frozen G1 long-component proxy; not a new gate."""
import csv,json,hashlib
from pathlib import Path
root=Path(__file__).resolve().parents[2];art=root/'artifacts/adaptive_mass_layered_probe';run=root/'out/adaptive_mass_layered_probe/g1_run'
scenes=['lego','chair','drums','ficus'];views=[1,27,53,79];channels=['E_occ','E_layer','E_shape_ridge','E_shape_valley'];grids=['95_70','90_60']
rows=[];data={};sources={}
for p in sorted((run/'final').glob('*.json')):
 s,v,c=p.stem.split('_',2);d=json.loads(p.read_text());data[s,int(v),c]=d;sources[str(p.relative_to(run))]=hashlib.sha256(p.read_bytes()).hexdigest()
 for ch in channels:
  for grid in grids:rows.append(dict(scene=s,view=int(v),control=c,channel=ch,grid=grid,**d[ch][grid]))
with (art/'G1_CONTROL_METRICS.csv').open('w') as f:
 w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
summary={}
for s in scenes:
 summary[s]={}
 for ch in channels:
  summary[s][ch]={}
  for grid in grids:
   values={c:[data[s,v,c][ch][grid]['long_component_ink_fraction'] for v in views] for c in ['full','front_depth','no_ids','shuffled_ids','shuffled_depths','uniform']}
   dn=[a-b for a,b in zip(values['full'],values['no_ids'])];ds=[a-b for a,b in zip(values['full'],values['shuffled_ids'])]
   summary[s][ch][grid]=dict(values=values,full_minus_no_ids=dn,full_minus_shuffled_ids=ds,joint_numeric_id_criterion_views=[v for v,a,b in zip(views,dn,ds) if a>=.05 and b>=.05])
result=dict(metric='Raw-band ink fraction in 8-connected components with skeleton length >=24',views=views,grids=grids,required_absolute_drop=.05,required_views=3,warning='Numeric proxy alone cannot establish GO; required visual and soft-response comparison is independently recorded.',summary=summary,source_sha256=sources,rows=len(rows))
(art/'G1_CONTROL_SUMMARY.json').write_text(json.dumps(result,sort_keys=True,indent=2)+'\n')
for s in scenes:
 print(s,{ch:summary[s][ch]['95_70']['joint_numeric_id_criterion_views'] for ch in channels})
print('metric rows',len(rows))
