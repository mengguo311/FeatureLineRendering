"""Freeze unit008 scope before any new candidate or UI behavior."""
import runtime
from runtime import OUTPUT_ROOT,js,sha,now,output_guard
from pathlib import Path
import json,shutil
from geometry import orbit_camera
U=output_guard(OUTPUT_ROOT/'units/unit_008')
if (U/'SCOPE.json').exists():raise FileExistsError('scope already frozen')
sources={s:OUTPUT_ROOT/f'units/{u}/assets/{arm}' for s,u,arm in [('chair','unit_002','edited'),('lego','unit_004','original'),('drums','unit_007','edited')]}
inputs={str(f):sha(f) for a in sources.values() for f in a.iterdir() if f.is_file()}
orig=json.loads((OUTPUT_ROOT/'orchestration/EXISTING_MODEL_INPUTS.json').read_text())
construction=[orbit_camera(az,35,4.9) for az in (237,327,147)]
static=[orbit_camera(az,28,5.1) for az in (53,143,233,323)]
meta=json.loads((sources['lego']/'asset.json').read_text())
static=meta['cameras'][:4]+static
p=dict(unit='unit_008',scene='lego',frozen_utc=now(),source_unit=str(OUTPUT_ROOT/'units/unit_004'),source_asset=str(sources['lego']),sources={s:str(a) for s,a in sources.items()},input_sha256=inputs,original=orig['lego'],originals={s:orig[s] for s in sources},
 changed_variable='Portable multi-scene session switching with preserved per-scene edits/drafts; one bounded manual Lego visible-face selection, then region4 angle -25 to35.',
 fixed='same saved proxy geometry, renderer, hatch generator, inherited non-target styles; no proxy refinement or parameter sweep',
 styles=meta['styles'],region_source='Inherited coarse height regions; up to four manually authored visible rectangles from at most three construction views, frozen after viewing only construction proxy images.',
 construction_cameras=construction,static_cameras=static,orbit=[orbit_camera(11+30*i,28,5.1) for i in range(12)],zoom=[orbit_camera(101,32,5.4-.12*i) for i in range(6)],viewer_camera=dict(azimuth=237,elevation=35,distance=4.9),
 references=json.loads((OUTPUT_ROOT/'units/unit_004/PROTOCOL.json').read_text())['references'],
 expected_tests=['switch scenes without overwriting assets or losing session draft/edits','reject unknown/mismatched scene and stale scene requests','actual browser across all three scenes and Lego pointer selection/four controls/export','non-target saved paths and layers, actual entire object views','new process reload all three saved models; relocated package reload; all trajectory frames decoded'],
 scope='Engineering usability only. H1/H2 not tested; historical GT NO_GO and P2 ZERO_HEADROOM unchanged. Old cameras exposed; new camera sets frozen here, not blind reconstruction holdouts.',
 decision='Combine existing three actual models before Ficus or geometry cleanup; previous Drums output remains rough and selection includes foreign islands.',
 deadline_jst='2026-10-22T05:27:18+09:00')
js(U/'SCOPE.json',p)
for scene,src in sources.items():
 dest=U/'catalog_assets'/scene;shutil.copytree(src,dest)
 if scene=='lego':
  m=json.loads((dest/'asset.json').read_text())
  for key,src_key in [('cameras','static_cameras'),('orbit','orbit'),('zoom','zoom'),('viewer_camera','viewer_camera')]:m[key]=p[src_key]
  js(dest/'asset.json',m)
js(U/'CATALOG.json',dict(schema='partwise_scene_catalog_v1',default_scene='lego',scenes={s:dict(label=s.capitalize(),asset=f'catalog_assets/{s}') for s in sources}))
shutil.copy2(OUTPUT_ROOT/'units/unit_004/DEPENDENCIES.json',U/'DEPENDENCIES.json')
print(U/'SCOPE.json')
