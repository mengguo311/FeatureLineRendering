"""Prepare one bounded whole-object temporal audit, before rendering."""
from common import *
import shutil,subprocess,math
from datetime import datetime,timezone
U=OUT.parent/'unit_007'; P=OUT.parent/'unit_006'; B=OUT.parent/'unit_003'
def cp(a,b):
 b.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(a,b)
def main():
 U.mkdir(exist_ok=True)
 assert not (U/'PROTOCOL.json').exists()
 for n in ('STATUS.json','NEXT.json','SEAL.json','SHA256_MANIFEST.json'):
  cp(P/n,U/'previous_snapshot'/n)
 cp(P/'inherited_failures/FROZEN_GATE_FAILURES.json',U/'inherited_failures/unit004_density_NO_GO.json')
 for n in ('STATUS.json','NEXT.json','SEAL.json'):
  cp(B/n,U/'inherited_failures'/('unit003_'+n))
 for q in ('unit_001','unit_002'):
  for n in ('TEMPORAL_PROBES.json','STATUS.json'):
   p=OUT.parent/q/n
   if p.exists():cp(p,U/'inherited_failures'/(q+'_'+n))
 for n in ('lamp_mesh.npz','selected.npz'):cp(B/'inputs'/n,U/'inputs'/n)
 cp(B/'CONFIG.json',U/'CONFIG.json')
 a=np.load(U/'inputs/lamp_mesh.npz');mesh=core.finalize_mesh(a['vertices'],a['faces'],a['parts'])
 strokes=load_strokes(U/'inputs/selected.npz'); pool=[]
 for s in strokes:
  xyz=core.anchor_points(mesh,s);mid=xyz.mean(axis=0)
  pool.append(dict(id=s['id'],part=s['part'],length=float(np.linalg.norm(np.diff(xyz,axis=0),axis=1).sum()),y=float(mid[1]),theta=float(np.arctan2(mid[2],mid[0]))))
 selected=[]
 for part in (1,2,3):
  rows=[x for x in pool if x['part']==part]
  for reason, key in [('shortest',lambda x:(x['length'],x['id'])),('lowest',lambda x:(x['y'],x['id'])),('highest',lambda x:(-x['y'],x['id']))]+[(f'azimuth_{deg}',lambda x,d=deg:(abs(np.arctan2(np.sin(x['theta']-np.radians(d)),np.cos(x['theta']-np.radians(d)))),x['id'])) for deg in (0,120,240)]:
   row=min([x for x in rows if x['id'] not in [r['id'] for r in selected]],key=key)
   selected.append(dict(row,stratum=reason))
 write_json(U/'SAMPLE_SELECTION.json',dict(rule='Six geometry-only IDs per part: shortest, lowest/highest path mean y, closest mean theta to0/120/240; sequential exclusion and lexical ID tie-break. No rendered selection.',selected=selected,all_path_inventory=pool))
 trajectories={
 'orbit':[dict(frame=i,azimuth=15*i,elevation=20,distance=4.5) for i in range(24)],
 'zoom':[dict(frame=i,azimuth=30,elevation=20,distance=4.8-.8*math.cos(2*math.pi*i/11)) for i in range(12)]}
 write_json(U/'TRAJECTORIES.json',trajectories)
 protocol=dict(id='unit007_whole_lamp_actual_temporal_audit',frozen_utc=datetime.now(timezone.utc).isoformat(),
 question='Do actual fixed-ID hatch outputs remain aligned and present on independently common-visible parts of the complete lamp over orbit/zoom?',
 changed_variable='Camera only; renderer instrumentation exports isolated actual per-ID hatch buffers without changing rendering rules.',
 asset=dict(path=str(B/'inputs/selected.npz'),sha256=sha(B/'inputs/selected.npz'),stroke_count=458,part_counts={'1':260,'2':48,'3':150},label='unit003 accepted base-cleanup asset; baseline comparator for unit004; NOT unit004 candidate',geometry='Authored analytic lathe GT / triangulated proxy, manual GT parts and axis/circumferential/cross direction rules. No reconstruction.'),
 inputs={str(U/n):sha(U/n) for n in ('CONFIG.json','inputs/lamp_mesh.npz','inputs/selected.npz','SAMPLE_SELECTION.json','TRAJECTORIES.json')},
 exposure=dict(train=[],dev=[],test=[],note='All geometry/view families previously exposed. New measurements on exposed engineering diagnostic. No blind test or parameter tuning.'),
 renderer=dict(source='unchanged renderer.py copied to renderer_probe_unit007.py with optional isolated buffer instrumentation',resolution=[512,512],supersample=2,width_px=1,visibility_tolerance_world=.006,contour_visibility='visible_centerline',limits=['2x box AA','owner plane across width','no near-plane clipping; all frozen object points in front']),
 fixed_controls=['mesh, all458 paths, IDs, inks, styles, light','no LOD, edits, tone change or resampling','18 preselected IDs and exact camera trajectories','Inherited17 hidden-profile observations, rim outliers and density NO_GO remain preserved'],
 metric=dict(reference='Direct continuous analytic lathe rays at sample UV; analytic output pixel labels only for fixed2px boundary margin. Independent from mesh raster; shares authored shape.',samples='Fixed equal-world-arclength midpoint bins per ID; n=clip(ceil(length/.008),8,128), weights length/n; no frame-dependent resampling',support='Actual isolated uint8 hatch PNG, profile +/-2px at0.25px; peak>=.05',eligibility='same analytic part, abs(optical-depth gap)<=.006, fixed2px mask/image/end margin, nondegenerate tangent; nonlocal same-ID projected overlap ambiguous at4px',coverage='All classes, projected and world length, all sampled IDs and unique samples, per part and trajectory; no hidden/excluded observations omitted',temporal='Adjacent common-visible same sample correspondences within trajectory only; normal-centroid residual difference conditional on both present; absent cases retained separately; never anchor hash as quality gate',gates=dict(eligible_raw_visible_world_fraction_min=.2,common_visible_length_min_exclusive=0,centroid_p95_px_max=.75,normal_residual_delta_p95_px_max=.75,missing_fraction_max=.02),hidden='Diagnostic support only; self-projection aliasing can remain. Do not reinterpret old17 as resolved.'),
 controls=['no-edit repeated output must agree','drift actual selected stroke raster +3px x and +3px y separately; at least one produces increased missing or centroid error for each part','drop one eligible whole stroke/frame: missing fraction1 and common-visible dropout detected','independent oracle primitive cylinder/plane closed-form checks','instrumented full outputs vs original renderer; 3 isolated IDs at orbit frame0 vs original selected_ids hatch'],
 videos=dict(orbit_frames=24,zoom_frames=12,fps=12,codec='FFV1',decode='all frames RGB exactly against PNG; first/middle/last and all-frame sheets'),
 visual_go='Full lamp stays readable/in frame, three parts and distinct styles visible; inspect actual isolated crops and overlay all samples; prior dense stem remains full quality limitation. Contact sheets do not establish flicker-free viewing.',
 go_no_go='Software GO requires oracle/control/identity/media checks; temporal gates independently per part/sequence, failures retained. FullP1/reconstruction/H1/H2 remain unproven.',
 budgets=dict(cpu_affinity=[0,1],numeric_threads=1,ffmpeg_threads=1,gpu=False,invocation_seconds=590,unit_end_jst='2026-10-21T19:08:25+09:00',task_cap_bytes=20*2**30),
 outline_sections=['5.8','9.5','11.1','14.3'])
 write_json(U/'PROTOCOL.json',protocol);cp(U/'PROTOCOL.json',WORK/'docs/partwise_sketch_hatching_v02/PROTOCOL_unit007.json')
 write_json(U/'STATUS_INITIAL.json',dict(stage='protocol_frozen_implementation_pending',execution_state='in_progress',scientific_verdict='NOT_EVALUATED',tests=[],artifacts=['PROTOCOL.json'],blockers=['Actual temporal evaluation pending'],outline_milestone='P1/W4/W9',p1_progress='Frozen whole-object audit; no success claimed'))
 cp(U/'STATUS_INITIAL.json',U/'STATUS.json')
 print(json.dumps(native(dict(selected=selected,protocol_sha256=sha(U/'PROTOCOL.json')))))
if __name__=='__main__':main()
