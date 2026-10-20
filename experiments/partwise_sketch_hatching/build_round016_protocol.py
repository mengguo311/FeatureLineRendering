"""Freeze one axial zoom audit before evaluation; all thresholds inherited."""
import round016_common as c
import json
p=json.loads((c.W/'docs/partwise_sketch_hatching/round_015/PROTOCOL.json').read_text())
p.update(round='round_016',authority='Only round015 Astra NEXT; outline 5.8,9.5,14.3',hypothesis='Fixed planar ribbons under axial camera translation follow independent analytic area and known surface correspondence without extra scale-dependent drift or dropout.')
p['trajectory']=[{'frame':i,'eye':[0.,0.,-.25+.5*i/11.],'R':[[1,0,0],[0,1,0],[0,0,1]]} for i in range(12)]
p['reference']='Unchanged physical_area_reference.py area integral; independently project prescribed points and rectangular corners as center+(p0-center)*z/(z-eye_z) at owner/path z=4 and foreground z=3; no candidate projection, clipping or data. Screen ribbon width stays 2 internal pixels, not multiplied by zoom.'
p['resources']['deadline_jst']='2026-10-21T07:21:29.386458+09:00'
p['prior_next_sha256']=c.sha(c.P/'NEXT.json')
p['fixed_sources'].update({n:c.sha(c.W/'experiments/partwise_sketch_hatching'/n) for n in ['planar_temporal_metrics.py','run_round015.py']})
p['gates']['axial_projection_scale_and_occlusion_nonzero']=True
p['gates']['screen_width_unchanged']=True
p['limits'][1]='No renderer changes, sweeps, threshold tuning, geometry extension, general orbit, lamp integration, H2 or training.'
p['limits'][2]='General orbit, AA quality, effective line width, LOD, P1 and RaDe-GS reconstruction remain unproven; passing only establishes finite planar axial scale response.'
c.write(c.D/'PROTOCOL.json',p)
c.status('protocol_frozen_awaiting_implementation',artifacts=[str(c.D/'PROTOCOL.json'),'STATUS.json','NEXT.json'])
print(json.dumps({'frames':12,'prior_seal':c.verify_prior(),'resources':c.resources()}))
