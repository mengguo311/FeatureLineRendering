"""Freeze the single reconstruction-input bridge before any RGB generation."""
from common import *
import shutil
from datetime import datetime, timezone
U=OUT.parent/'unit_006'
D=WORK/'docs/partwise_sketch_hatching_v02'
mesh=OUT/'inputs/lamp_mesh.npz'
source_paths=[WORK/'docs/partwise_sketch_hatching/experiment_outline_v1.md',Path('/mnt/hdd1/u00134/partwise_sketch_hatching_p1_v02/orchestration/BRIEF.md'),U.parent/'unit_005/NEXT.json',mesh]
p={
 'unit':'unit_006','status':'FROZEN_BEFORE_EVALUATION','created_utc':datetime.now(timezone.utc).isoformat(),
 'question':'Can the current complete three-part authored lamp become an explicit RGB/camera-only reconstruction input with disjoint splits, usable loader and isolated oracle?',
 'changed_variable':'One input-bridge addition only; inherited NPR styles, paths, renderer and failed density gates are not changed.',
 'scope':'Synthetic input readiness only; no trained reconstruction, main reconstructed proxy, H1/H2, or full-P1 claim.',
 'fallback':'Bounded <=5min read-only known-root inventory; absent verified trained lamp, execute frozen synthetic route.',
 'inputs':[{'path':str(x),'sha256':sha(x)} for x in source_paths],
 'geometry':{'source':'authored_lathe_lamp_gt_v1 inherited byte-identical mesh','labels':{'1':'shade','2':'stem','3':'base'},'labels_provenance':'authored GT; oracle only','direction':'no hatching or direction field in RGB generation','training_geometry':'NONE; no GT points or mesh in training export'},
 'camera':{'resolution':[512,512],'supersample':2,'focal_px':600.0,'principal_point':[256.0,256.0],'distance':4.5,'look_at':[0,1.17,0],'elevations_deg':[10,25,40],'world':'right-handed y-up','canonical':'x-right,y-down,z-forward; W2C row-vector Xc=Xw@R.T+t; depth optical z','export':'NeRF/OpenGL C2W x-right,y-up,z-back; C2W_cv @ diag(1,-1,-1,1); pixel centers integer'},
 'splits':{'train':{'count':36,'azimuths_deg':[30*m for m in range(12)]},'dev':{'count':12,'azimuths_deg':[7.5+90*m for m in range(4)]},'test':{'count':72,'azimuths_deg':[3.75+15*m for m in range(24)]},'exposure':'New RGB viewpoints, authored geometry and profile already exposed in prior units; this is preparation and inspection, not blind research evaluation. Test RGB inspected for integrity only; no tuning after freeze.'},
 'renderer':{'name':'CPU triangle z-buffer, perspective-correct world interpolation, 2x2 box AA','normal':'flat oriented face normals, two-sided triangles, no backface cull','lighting':{'ambient':0.35,'diffuse':0.65,'world_light_to_source':[0.4,0.8,0.6]},'materials_linear_rgb':{'1':[0.72,0.38,0.20],'2':[0.22,0.24,0.27],'3':[0.12,0.28,0.37]},'background_linear_rgb':[1,1,1],'encoding':'linear lighting then IEC sRGB transfer, uint8 rounded PNG RGB','shadows':'local Lambert only; no cast shadows, specular, textures or ambient occlusion','randomness':'none','hatch_structure_ink':'none'},
 'layout':{'dataset/train':'RGB PNG + canonical cameras + transforms_train.json + EMPTY transforms_test.json; only train is reconstruction source','dataset/evaluation/dev':'RGB and cameras, separate explicit evaluator input','dataset/evaluation/test':'RGB and cameras, locked evaluator input','oracle_only':'GT mesh/face parts + per-view output-resolution optical-z depth/world normals/part IDs/coverage, never a reconstructed proxy','metadata':'RGB/camera-only loader defaults to train; explicit evaluation purpose required for dev/test; no oracle paths in returned samples'},
 'go_no_go':{'software':'all 120 PNG fully decode; exact split sizes and pairwise disjoint angle/camera/file sets; loader returns only expected RGB/camera keys; source and image hashes verified; injected split overlap and oracle/path-escape cases rejected','geometry':'all vertices positive depth; all projected vertex bounds >=8px from image edge; every frame >=50 visible pixels for EACH of 3 parts; independent camera axis/center/project-backproject <1e-9 and OpenGL conversion roundtrip <1e-9','visual':'inspect ALL full-view contact sheets plus native first/middle/last per split; full lamp present, stem/base discernible, no blank/clipped/corrupt image; no test-driven changes','no_go':'Any frozen failure retained with failing views, no angle/material/threshold tuning; no input-readiness promotion until explained','application_gate':'actual RGB completeness/part visibility/usable isolated loader; not primitive-array equality'},
 'validation':{'camera_fault':'flipped camera axis must fail independent projection validation','isolation_fault':'cross-split overlap and path outside split must fail','cold_replay':'one fixed train view train_e0_a00 regenerated in fresh child and compared to original RGB, not main quality gate','official_compatibility':'read local official RaDe-GS loader source; isolated unchanged camera-reader function execution if dependencies allow, otherwise explicit limitation; no training invocation'},
 'resources':{'affinity':[0,1],'numeric_threads':1,'total_threads_max':2,'GPU':False,'timeout_s':590,'unit_minutes_max':45,'unit_deadline_jst':'2026-10-21T18:50:07+09:00','output_cap_bytes':20*2**30},
 'preserved_failures':['unit004 stem density frame19 az285 0.7521462443170939 >0.75 NO_GO','unit001/002 visual NO_GO; inherited17 hidden-profile observations/rim outliers','historical rc1/143/UNKNOWN and round004/012/013 NO_GO','unit005 preview is DIAGNOSTIC_PREVIEW_ONLY'],
}
assert not (U/'PROTOCOL.json').exists()
write_json(U/'PROTOCOL.json',p);write_json(D/'PROTOCOL_unit006.json',p)
(U/'oracle_only').mkdir(exist_ok=True);shutil.copy2(mesh,U/'oracle_only/lamp_mesh.npz')
for name in ['STATUS','NEXT','SEAL']:
 dest=U/'previous_snapshot'/f'{name}.json';dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(U.parent/'unit_005'/f'{name}.json',dest)
write_json(U/'STATUS_INITIAL.json',dict(stage='protocol_frozen',execution_state='in_progress',scientific_verdict='PENDING',outline_milestone='P1 RGB/camera reconstruction input bridge',p1_progress='No result yet; plan frozen before evaluation'))
write_json(U/'RESOURCES_INITIAL.json',dict(root_free_bytes=shutil.disk_usage(WORK).free,hdd_free_bytes=shutil.disk_usage(U).free,cpu_affinity=sorted(os.sched_getaffinity(0)),numeric_threads=1,GPU=False))
print('unit006 protocol frozen; no RGB generated')
