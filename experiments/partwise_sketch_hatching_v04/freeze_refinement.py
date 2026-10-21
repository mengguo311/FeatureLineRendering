"""Freeze one bounded Chair geometry candidate before looking at its outputs."""
import runtime
from runtime import js, sha, now, output_guard
from pathlib import Path
import argparse
import copy
import json
from geometry import orbit_camera


def freeze(previous, unit):
    unit = output_guard(unit)
    if (unit / 'PROTOCOL.json').exists():
        raise FileExistsError('protocol already frozen')
    p = copy.deepcopy(json.loads((previous / 'PROTOCOL.json').read_text()))
    p.update(version=2, unit='unit_002', frozen_utc=now(), previous_unit=str(previous))
    p['geometry'] += '; single bounded topology-preserving Taubin refinement, lower region pinned'
    p['refinement'] = dict(iterations=8, positive_step=.5, negative_step=-.53,
                           max_displacement=.012, pinned_regions=[1],
                           pin_open_nonmanifold_edges=True, pin_region_boundary_vertices=True,
                           adjacency='identical indexed triangle edges only',
                           weights='uniform one-ring, no KNN, no weld or topology edits',
                           face_guard='positive oriented area against original; >= 20% original area',
                           keep_face_regions=True, candidate_count=1)
    p['static_cameras'] += [orbit_camera(a, 32, 4.7) for a in (32, 122, 212, 302)]
    p['orbit'] = [orbit_camera(32 + 30*k, 22, 4.7) for k in range(12)]
    p['zoom'] = [orbit_camera(62, 27, d) for d in (5.2, 4.98, 4.76, 4.54, 4.32, 4.10)]
    p['comparison'] = dict(changed_variable='proxy vertex positions only; regenerate paths with same styles',
        fixed=['faces', 'face region IDs', 'all style values', 'renderer', 'cameras', 'original checkpoint'],
        expected='less jagged seat/back paths without thinning legs or blanking visible regions',
        evidence=['full-object source RGB / both proxies / both hatch outputs at all 8 views',
                  'mesh displacement, topology, face orientation, pinned lower vertices',
                  'path turning per arc, short paths, total length, per-region raster ink/support',
                  'source-model depth residual and silhouette; source-model depths are not independent truth',
                  'selected region edit, unchanged other regions, cold reload, HTTP editor, orbit/zoom'],
        retention_policy='describe ink and coverage, never call fewer lines a quality improvement by itself',
        selection='one candidate; retain as optional if quality is mixed, no parameter sweep')
    p['exposure'] = ('Original 4 views are historically exposed. Added 4 static cameras and new orbit/zoom '
                     'are frozen now before candidate output; no blind evaluation or independent geometry truth.')
    p['changed_variable'] = dict(region=2, angle=95., other_parameters_and_paths='fixed within candidate edit')
    p['expected_tests'] += ['real Chair roughness responds', 'frozen face labels survive reload',
                            'pinned geometry exact', 'bounded displacement without face flips']
    inputs = [previous / 'PROTOCOL.json', previous / 'STATUS.json', previous / 'NEXT.json',
              previous / 'ENGINEERING_SEAL.json', previous / 'media/reference_proxy_regions_hatch.png']
    inputs += sorted((previous / 'assets/baseline').glob('*'))
    inputs += sorted((previous / 'renders/static_baseline').glob('*.npz'))
    for path in inputs:
        p['inputs_sha256'][str(path)] = sha(path)
    js(unit / 'PROTOCOL.json', p)
    js(Path('docs/partwise_sketch_hatching_v04/UNIT002_PROTOCOL.json'), p)
    js(unit / 'REVIEW_BEFORE_RUN.json', dict(utc=now(),
       actual_outputs_reviewed=['unit001/media/reference_proxy_regions_hatch.png'],
       finding='Complete Chair already runs. Noisy seat/back proxy causes wavy lines; sparse thin legs remain.',
       ranked_choices=['one bounded proxy refinement, pin lower geometry and boundaries',
                       'explicitly improve style-region semantics', 'reuse adapter on Lego'],
       decision='Refine current runnable Chair before expanding; protect existing thin lower structures.',
       historical_claims='P1 partial/NO_GO and P2 ZERO_HEADROOM/UNIDENTIFIABLE_FOR_H2 unchanged',
       source_read=['v04 adapter/fusion/geometry/hatching/render/demo/viewer/validator',
                    'P1 core_walk_v2 and v02 renderer', 'P2 diagnostic and report/NEXT']))
    print(json.dumps(dict(protocol=str(unit / 'PROTOCOL.json'), sha256=sha(unit / 'PROTOCOL.json'))))


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--previous', type=Path, required=True)
    p.add_argument('--unit', type=Path, required=True)
    a = p.parse_args()
    freeze(a.previous, a.unit)
