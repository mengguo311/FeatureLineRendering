"""One bounded Ficus transfer with unchanged extraction and rendering parameters."""
import runtime
from runtime import OUTPUT_ROOT, sha, js, now, output_guard
from pathlib import Path
import argparse, json, os, importlib.metadata
import numpy as np
from model_adapter import camera_from_gl
from geometry import normalize, orbit_camera


def freeze(unit):
    unit = output_guard(unit)
    if (unit/'PROTOCOL.json').exists():
        raise FileExistsError('protocol already frozen')
    manifest = OUTPUT_ROOT/'orchestration/EXISTING_MODEL_INPUTS.json'
    original = json.loads(manifest.read_text())['ficus']
    assert sha(original['original_ply']) == original['sha256']
    inp = Path(original['input_directory'])
    train = json.loads((inp/'transforms_train.json').read_text())
    test = json.loads((inp/'transforms_test.json').read_text())
    frames = train['frames']
    directions = normalize(np.array([f['transform_matrix'] for f in frames])[:, :3, 3])
    chosen = [next(i for i, f in enumerate(frames) if f['file_path'].endswith('/r_7'))]
    while len(chosen) < 24:
        distance = np.min(1-directions@directions[chosen].T, axis=1)
        distance[chosen] = -1
        chosen.append(int(np.argmax(distance)))
    def camera(frame, data, split):
        return camera_from_gl(frame['transform_matrix'], data['camera_angle_x'], 400, 400,
                              split+'_'+Path(frame['file_path']).name, split)
    build = [camera(frames[i], train, 'train') for i in chosen]
    selected = [('train', train, frames[chosen[0]])]
    selected += [('test', test, next(f for f in test['frames'] if f['file_path'].endswith('/r_'+str(i))))
                 for i in (1, 27, 79)]
    static = [camera(f, d, s) for s, d, f in selected]
    refs = {c['view']: str((inp/(f['file_path']+'.png')).resolve())
            for c, (_, _, f) in zip(static, selected)}
    static += [orbit_camera(a, 22, 5.1) for a in (71, 161, 251, 341)]
    previous = OUTPUT_ROOT/'units/unit_008'
    inputs = [manifest, inp/'transforms_train.json', inp/'transforms_test.json',
              Path(original['original_ply']), *map(Path, refs.values()), unit/'INVENTORY.json',
              *[previous/f for f in ('STATUS.json', 'REPORT_ZH.md', 'NEXT.json', 'ENGINEERING_SEAL.json')]]
    p = dict(version=9, frozen_utc=now(), scene='ficus', previous_unit=str(previous), original=original,
        inputs_sha256={str(f): sha(f) for f in inputs}, input_cache_probe=None, references=refs,
        build_cameras=build, static_cameras=static,
        camera_selection='24 original training poses: greedy angular farthest from train_r_7; original test names 1/27/79 plus four new frozen virtual poses',
        geometry='CPU covariance-plane median z from exact frozen vanilla 3DGS; confidence/jump-gated TSDF; exploratory, not RaDe-trained, not GT',
        filtering=dict(alpha_min=.95, near=.2, far=6., max_center_difference=.06, max_3x3_jump=.08,
                       voxel=.012, sdf_trunc=.036, remove_components_below_triangles=40,
                       simplify_faces=30000, bounds='opacity > .5 centers min/max plus .06'),
        region_rule=dict(axis='z', cuts=[-.4, .4], assignment='face centroid, persisted face IDs'),
        regions={'1':'Lower: z < -0.4 (blue)', '2':'Middle: -0.4 <= z < 0.4 (amber)',
                 '3':'Upper: z >= 0.4 (green)'},
        region_provenance='Authored world-height thresholds from original coordinate inventory only; NOT pot/trunk/leaf semantics; no geometric repair',
        styles={str(i):dict(angle=a, spacing=.045, length=.22, width=1.) for i,a in ((1,0.),(2,45.),(3,-25.))},
        changed_variable=dict(region=2, angle=95., fixed='geometry, labels, non-target paths, all other styles and cameras'),
        renderer=dict(size=512, supersample=2, depth_tolerance=.004,
                      contour='view mask/depth edges independent of fixed paths'),
        orbit=[orbit_camera(71+30*k,22,5.1) for k in range(12)],
        zoom=[orbit_camera(101,26,float(d)) for d in np.linspace(5.5,4.5,6)],
        viewer_camera=dict(azimuth=71,elevation=22,distance=5.1),
        expected_tests=['direct original PLY extraction', 'target change with non-target preservation',
                        'all full-object and weak views', 'cold reload exact', 'browser and HTTP four controls',
                        'exported asset and relocated four-model catalog cold render', 'all 18 video frames decoded'],
        comparison_scope='fourth-model engineering transfer only; no H1/H2 comparison or geometry accuracy/superiority claim',
        exposure='training views used for fusion; dataset has historical exposure; new virtual poses frozen before outputs, not blind evaluation',
        decision='Existing three-model complete-object/edit/reload workflow works. Test same bounded route on thin foliage; retain partial evidence if leaves/branches are lost. No parameter sweep.',
        permitted_engineering_fix='Standalone edit CLI must reject mismatched --scene before output; test on existing genuine asset before implementation.',
        resource_limits=dict(cpu_affinity=sorted(os.sched_getaffinity(0)),numeric_threads=1,serial=True,gpu=False,nested_models=False),
        unit_deadline_jst='2026-10-22T05:40:09+09:00',no_new_science_after_jst='2026-10-22T09:20:00+09:00',science_wrap_jst='2026-10-22T09:45:00+09:00')
    js(unit/'PROTOCOL.json',p)
    js(Path('docs/partwise_sketch_hatching_v04/UNIT009_PROTOCOL.json'),p)
    js(unit/'DEPENDENCIES.json',dict(python=__import__('platform').python_version(), packages={k:importlib.metadata.version(k)
        for k in ('numpy','scipy','Pillow','open3d','scikit-image','plyfile')},installed_new_dependencies=False))
    print(json.dumps(dict(protocol=str(unit/'PROTOCOL.json'),sha256=sha(unit/'PROTOCOL.json'))))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--unit',required=True,type=Path);freeze(p.parse_args().unit)
