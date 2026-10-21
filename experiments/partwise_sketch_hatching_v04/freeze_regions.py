"""Freeze one manual region authoring demo before candidate output."""
import runtime
from runtime import js, sha, now, output_guard
from pathlib import Path
import json
import shutil
from geometry import orbit_camera

def freeze(unit):
    unit=output_guard(unit)
    if (unit/'PROTOCOL.json').exists(): raise FileExistsError('protocol already frozen')
    old=unit.parent/'unit_003'; prior=json.loads((old/'PROTOCOL.json').read_text())
    inputs={str(p):sha(p) for p in sorted((old/'assets/baseline').iterdir()) if p.is_file()}
    original=prior['original']; assert sha(original['original_ply'])==original['sha256']
    protocol=dict(schema='manual_region_demo_v1',frozen_utc=now(),scene='lego',
        source_unit=str(old),source_asset=str(old/'assets/baseline'),input_sha256=inputs,
        original=original,geometry=prior['geometry'],
        region_provenance='Inherited authored height labels plus one explicitly authored world AABB on face centroids; no semantic learner or GT.',
        selection=dict(source_region=3,bounds=[-.70,-1.20,.45,.70,-.35,1.10],
                       name='Front bucket area (manual)',new_region=4,
                       rule='inclusive world xyz face centroid box AND source region 3; save exact proxy face IDs'),
        styles=prior['styles'],edit=dict(region=4,angle=35.),
        static_cameras=prior['static_cameras'][:4]+[orbit_camera(a,28,4.9) for a in (41,131,221,311)],
        references=prior['references'],
        orbit=[orbit_camera(11+30*k,25,4.9) for k in range(12)],
        zoom=[orbit_camera(41,28,d) for d in (5.4,5.2,5.,4.8,4.6,4.4)],
        viewer_camera=dict(azimuth=41,elevation=28,distance=4.9),
        fixed='vertices/faces; prior styles; supersample2; original depth/contour renderer; donor paths outside selected faces retained exactly',
        changed='manual face labels -> new region; then only new region angle -25 to 35 degrees',
        expected_tests=['selection rejects empty/nonfinite/draining source',
            'same geometry and exact face IDs saved; outside selected faces original path fields preserved',
            'style edit leaves all other regions files/layers exact, positive target delta; fixed 2px AA band',
            'browser preview/create/edit/export; fresh process reload and relocated package replay',
            'entire objects and weak views; actual source-model RGB and all orbit/zoom frames decoded'],
        scope='engineering demo; no automatic semantic segmentation, H1/H2 proof, independent geometry truth or full temporal certification',
        exposure='All prior unit003 images reviewed. New virtual cameras frozen before candidate output; not blind or independent reconstruction holdouts.',
        authored_cost='One box chosen from inherited mesh coordinates and exposed train/previous views. No candidate sweep; not human annotation benchmark.',
        alternatives_ranked=['persistent manual region authoring','bounded hatch readability improvement','third scene'],
        previous_review='Lego complete-object/edit/reload works but height region ties bucket to roof. Coarse holes and busy hatch remain; no geometry smoothing in this unit.')
    js(unit/'PROTOCOL.json',protocol)
    shutil.copy2(unit/'PROTOCOL.json',Path('docs/partwise_sketch_hatching_v04/UNIT004_PROTOCOL.json'))
    js(unit/'READING_RECORD.json',dict(brief='complete',outline='all sections read',
        p1='unit010 REPORT/NEXT and spacing_cli source; unit011 REPORT/NEXT absent (read-only cat rc1)',
        p2='experiment001 REPORT/NEXT, runtime and diagnostic source',
        old_verdicts='P1 visual NO_GO/PARTIAL; P2 ZERO_HEADROOM unchanged',
        previous_actual_images=['unit003/media/reference_proxy_regions_hatch.png','unit003/media/local_edit_all_views.png']))
    print(json.dumps(dict(protocol_sha256=sha(unit/'PROTOCOL.json'),frozen_utc=protocol['frozen_utc'])))

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--unit',type=Path,required=True);freeze(p.parse_args().unit)
