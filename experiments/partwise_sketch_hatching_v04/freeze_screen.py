"""Freeze the visible-face authoring demonstration before new candidate output."""
import runtime
from runtime import js, sha, now, OUTPUT_ROOT
from pathlib import Path
import json, shutil
from geometry import orbit_camera

unit=OUTPUT_ROOT/'units/unit_006'
old=unit.parent/'unit_005'
prior=json.loads((old/'PROTOCOL.json').read_text())
assert not (unit/'PROTOCOL.json').exists()
assert sha(prior['original']['original_ply'])==prior['original']['sha256']
inputs={str(p):sha(p) for p in (old/'assets/baseline').iterdir() if p.is_file()}
p=dict(schema='visible_face_authoring_v1',frozen_utc=now(),scene='drums',
    source_unit=str(old),source_asset=str(old/'assets/baseline'),input_sha256=inputs,
    original=prior['original'],geometry=prior['geometry'],styles=prior['styles'],
    selection=dict(source_region=3,rectangle=[128,128,260,240],
        camera=orbit_camera(157,24,4.9),name='Visible upper patch (manual)',new_region=4,
        rule='frontmost proxy triangle IDs hit by 2x pixel-center rays inside image-edge rectangle; full selected triangles retained; no hidden-face expansion'),
    edit=dict(region=4,angle=35.),viewer_camera=dict(azimuth=157,elevation=24,distance=4.9),
    static_cameras=prior['static_cameras'][:4]+[orbit_camera(a,28,5.1) for a in (79,169,259,349)],
    references=prior['references'],orbit=[orbit_camera(19+30*k,25,5.1) for k in range(12)],
    zoom=[orbit_camera(169,28,d) for d in (5.6,5.4,5.2,5.,4.8,4.6)],
    fixed='geometry, ray/depth renderer, inherited styles and unselected path segments; no geometry repair or parameter search',
    changed='screen picking and visible rectangle -> saved proxy face region; angle -25 to 35 only in new region',
    scope='engineering usability; manually authored visible patch, not whole semantic part or automatic segmentation; H1/H2 not tested',
    exposure='unit005 all static images reviewed; new evaluation/orbit/zoom cameras frozen before this implementation; existing train/test are historically exposed',
    expected_tests=['occluded faces excluded; background/invalid/stale requests rejected',
        'real Drums saved IDs, unselected segments and other region files exact',
        'actual browser pointer pick/drag/save/style/undo/orbit/zoom/refresh/export',
        'fresh CLI exported replay and relocated package preview exact',
        'eight full-object comparisons including inherited clipped test_r_79; 18 frames encoded and fully decoded'],
    ranked_alternatives=['visible-face authoring usability','bounded hatch readability','fourth model later'],
    previous_review='Recognizable Drums, fragmented stands, holes and rough rims. Height region changes multiple pieces. No claim of repair.',
    annotation='One rectangle selected from exposed previous overview; no candidate scan; not a human usability study')
js(unit/'PROTOCOL.json',p)
shutil.copy2(unit/'PROTOCOL.json',Path('docs/partwise_sketch_hatching_v04/UNIT006_PROTOCOL.json'))
js(unit/'READING_RECORD.json',dict(brief='complete',outline='all 851 lines read',
    p1='unit010 REPORT/NEXT and length_cli source',p2='REPORT/NEXT, runtime and diagnostic source',
    previous='unit005 STATUS/REPORT/NEXT, actual 8-view reference and edit sheets',
    historical_verdicts='P1 visual NO_GO/PARTIAL and P2 ZERO_HEADROOM unchanged',
    read_errors=['repository unit011 report absent; rg AGENTS returned no matches'],nested_agents=False))
print(sha(unit/'PROTOCOL.json'))
