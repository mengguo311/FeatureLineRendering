"""Freeze a single whole-lamp base length operation before evaluation."""
from common import *
import shutil
from datetime import datetime,timezone
U=OUT.parent/'unit_010';P=U.parent/'unit_009'
def cp(src,dst):
    assert not dst.exists(),dst
    dst.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(src,dst)
source=P/'outputs/edited/asset.json';manifest=json.loads(source.read_text())
for key in ('mesh','strokes','config'):
    src=source.parent/manifest[key]['path'];dst=U/'inputs'/src.name
    cp(src,dst);assert sha(dst)==manifest[key]['sha256'];manifest[key]['path']=dst.name
# Source density recipe remains historical provenance, not a runnable length recipe.
manifest.pop('recipe',None);manifest.pop('path_lineage',None)
manifest['input_parent_asset']=dict(path=str(source),sha256=sha(source))
write_json(U/'inputs/asset.json',manifest)
for name in ('STATUS.json','NEXT.json','SEAL.json','SHA256_MANIFEST.json','PROTOCOL.json'):
    cp(P/name,U/'previous_snapshot'/name)
if (P/'inherited_failures').exists():shutil.copytree(P/'inherited_failures',U/'inherited_failures')
cp(U.parent.parent/'orchestration/BRIEF.md',U/'BRIEF_SNAPSHOT.md')
blockers=json.loads((P/'STATUS.json').read_text())['blockers']
s=dict(stage='base_length_protocol_frozen',execution_state='running',scientific_verdict='PENDING',tests={},artifacts=['PROTOCOL.json'],blockers=blockers,outline_milestone='P1/W3/W4/W9; outline5.5,7.2,7.3,9.2,9.5,9.6,9.7,11.1,14.3',p1_progress='One base-only length operation on complete434 GT lamp; evaluation has not begun')
write_json(U/'STATUS_INITIAL.json',s);write_json(U/'STATUS.json',s)
p=dict(unit='unit_010',created_utc=datetime.now(timezone.utc).isoformat(),question='Can one base-only length .18->.12 operation reduce foreground crossing clutter while preserving readable crosshatching, coverage and isolated editing on the complete selected434 lamp?',changed_variable='Only base requested total world length .18->.12; no density/count/seed/direction/width/ink/renderer changes',candidate_count=1,source_asset=str(source),source_asset_sha256=sha(source),inputs={str(x):sha(x) for x in (U/'inputs').glob('*')},
provenance=dict(geometry='Authored analytic GT lamp868vertices1728faces; not reconstructed',parts='GT1shade2stem3base',directions='Unchanged manual circumferential shade0deg, short axial stem, two base cross layers',paths='unit009 selected434:260shade24stem150base from75selected seed pairs;284non-target retained; original area sampler has150base seeds'),
exposure=dict(train=[],dev=[0],diagnostic=[30,120,210,300],test=[],note='Previously exposed GT object/view family. One frozen candidate, no tuning/retry or new held-out science claim'),
operation=dict(part=3,length_before=.18,length_after=.12,length_api_domain=[.06,.24],absolute=True,seed=1729,original_sampler_count=150,selected_pairs=75,selected_paths=150,step_world=.015,layers=[0,1],ink='Preserve original selected path ink and IDs; sample original seed sequence, walk only selected seeds, no compensation',cold='Fresh process from recipe+mesh+retained284+config, selected seed/ink identity and dependency hashes; no target path cache',preserve='284non-target paths and all selected seed IDs/inks'),
renderer=dict(backend='Unchanged cpu_supersampled_surface_capsules_v1',resolution=[512,512],supersample=2,focal_px=600,widths={'1':1.,'2':1.,'3':1.},depth_tolerance=.006,contour_width=.8,structure_width=.65,contour_visibility='visible_centerline',LOD=False,light='Unchanged inherited world light',limitations=['2x sampled AA','owner-plane extension across width','no near-plane clipping']),
camera=dict(azimuths=[30,120,210,300],dev_azimuth=0,elevation=20,distance=4.5),
evaluation=dict(primary='Actual full-lamp/base quality, nonzero isolated edit, geometric coverage and both layers retained; primitive-array equality secondary',independent_masks='Continuous analytic profile ray intersections; separate from triangle renderer, same authored GT geometry disclosed',gates=dict(target_part=3,target_inside_L1_min_exclusive=10,far_other_fraction_max=.02,far_background_fraction_max=.02,boundary_band_px=2,hatch_support_threshold=.1,every_part_support_pixels_min_exclusive=0,full_shape_margin_px_min=2),
coverage=dict(radial_edges_world=[0,.29,.580000001],hemispheres='front dot(world[x,z],camera.eye[x,z])>=0; back<0',cells='inner/front,inner/back,outer/front,outer/back; analytic part==3; no erosion',minimum_eligible_pixels=1,minimum_support_pixels=3,minimum_support_fraction=.01,scope='Four stills and all40 orbit/zoom rendered frames; visible pixels only; report every denominator and exclusions, no hidden-surface completeness claim',both_layer_gate='At each four still views, separately render each selected base layer against complete mesh; EACH whole visible analytic base >=3 pixels ink>.1 and >=.01 support fraction; per-cell layer support descriptive',ink_ratio='Report relative before/after ink descriptively; no oldunit004 .75 closing threshold'),
controls=['Noedit image totalL1=0 fails target nonzero gate','Blacken16brightest independent far-other pixels of baseline: fraction1 fails leakage','White-filled3px raster drift produces nonzero L1','Zero-hatch fails four coverage cells','Remove one rendered layer fails both-layer gate'],
secondary=['Original selected75 seed pairs/150 IDs and inks unchanged','284non-target paths per-field bytes exact','Cold recipe regeneration and separate saved-path replay reproduce4PNG views','Length.18 regenerates baseline target for implementation compatibility/noop','Reject invalid length, stale/bad dependencies, historical/existing output'],
visual_go='Less tangled base still readable and visibly crosshatched in full object and base crops; complete3parts across frozen trajectories; fullvisual remains NO_GO if inherited shade/stem defects persist',no_go='Empty/fragmented/unreadable base, lost direction layer, coverage/isolation failure, cold mismatch or loss of non-target identity; retain failure without length/threshold retry'),
media=dict(orbit=dict(frames=24,azimuth='15*k,k=0..23',elevation=20,distance=4.5),zoom=dict(frames=16,azimuth=30,elevation=20,distance='4.8-.8*cos(2*pi*k/15),k=0..15'),edit=dict(frames=24,switch_frame=12,azimuth=30,elevation=20,distance=4.5,operation='12before+12after discrete actual edit; no interpolation'),fps=12,format='FFV1 lossless MKV',validation='All64frames decode RGB-exact against sourcePNG; all-frame and first/middle/last contacts; no independent temporal stability claim'),
timing='Module entry and external process wall include imports/hash/load/target regeneration/save/render; no24FPS claim',
budgets=dict(cpu_affinity=[0,1],numeric_threads=1,ffmpeg_threads=1,gpu=False,serial_compute=True,invocation_max_seconds=590,unit_max_minutes=45,finish_before_jst='2026-10-21T20:00:35+09:00',task_cap_bytes=20*2**30),
claims=dict(software='PENDING',length_edit_visual='PENDING',full_visual='NO_GO_RETAINED',reconstructed_input='BLOCKED',full_P1='PARTIAL',H1_H2='NOT_TESTED',temporal='NOT_INDEPENDENTLY_AUDITED_FOR_UPDATED_ASSET'),retained_failures=blockers,outline_sha256=sha(WORK/'docs/partwise_sketch_hatching/experiment_outline_v1.md'),brief_sha256=sha(U/'BRIEF_SNAPSHOT.md'),previous_next_sha256=sha(P/'NEXT.json'))
write_json(U/'PROTOCOL.json',p);write_json(WORK/'docs/partwise_sketch_hatching_v02/PROTOCOL_unit010.json',p)
write_json(U/'RESOURCES_INITIAL.json',dict(root_free_bytes=shutil.disk_usage(WORK).free,hdd_free_bytes=shutil.disk_usage(U).free,cpu_affinity=sorted(os.sched_getaffinity(0)),gpu=False))
print(json.dumps(dict(protocol_sha256=sha(U/'PROTOCOL.json'),unit=str(U))))
