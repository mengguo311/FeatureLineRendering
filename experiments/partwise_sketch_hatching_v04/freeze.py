"""Freeze a compact engineering protocol before proxy construction/rendering."""
import runtime
from runtime import sha, js, now, output_guard
from pathlib import Path
import json
import argparse
import numpy as np
from model_adapter import camera_from_gl
from geometry import normalize, orbit_camera

def freeze(scene, unit):
    unit = output_guard(unit)
    path = unit/'PROTOCOL.json'
    if path.exists():
        raise FileExistsError(path)
    manifest = Path('/mnt/hdd1/u00134/partwise_sketch_hatching_models_v04/orchestration/EXISTING_MODEL_INPUTS.json')
    original = json.loads(manifest.read_text())[scene]
    assert sha(original['original_ply']) == original['sha256']
    inp = Path(original['input_directory'])
    train = json.loads((inp/'transforms_train.json').read_text())
    frames = train['frames']
    directions = normalize(np.array([f['transform_matrix'] for f in frames])[:, :3, 3])
    start = next((i for i, f in enumerate(frames) if f['file_path'].endswith('/r_32')), 0)
    selected = [start]
    while len(selected) < 24:
        dist = np.min(1-directions @ directions[selected].T, axis=1)
        dist[selected] = -1
        selected.append(int(np.argmax(dist)))
    cameras = [camera_from_gl(frames[i]['transform_matrix'], train['camera_angle_x'], 400, 400,
                             'train_'+Path(frames[i]['file_path']).name, 'train') for i in selected]
    refs = ['train_r_32', 'test_r_27', 'test_r_67', 'test_r_86']
    regpath = Path('/mnt/hdd1/u00134/radegs_paper_reproduction_v01/synthetic_three_gaussian_v01/REGISTRY.json')
    reg = json.loads(regpath.read_text())['scenes'][scene]
    static = [c for name in refs for c in reg['cameras'] if c['view']==name]
    inputs = {str(p): sha(p) for p in [manifest, regpath, inp/'transforms_train.json', inp/'transforms_test.json']}
    inputs[original['original_ply']] = original['sha256']
    for c in static:
        p = reg['reference_images'][c['view']]
        inputs[p] = sha(p)
    cache = Path('/mnt/hdd1/u00134/radegs_paper_reproduction_v01/synthetic_three_gaussian_v01/scenes')/scene/'inputs/train_r_32.npz'
    inputs[str(cache)] = sha(cache)
    p = dict(version=1, frozen_utc=now(), scene=scene, original=original, inputs_sha256=inputs,
             input_cache_probe=str(cache), cache_registry=str(regpath), build_cameras=cameras, static_cameras=static,
             references={c['view']:reg['reference_images'][c['view']] for c in static},
             camera_selection='24 training poses, greedy angular farthest from train_r_32; no RGB selection',
             geometry='CPU covariance-plane median z on exact frozen vanilla 3DGS, confidence/jump-gated TSDF; exploratory proxy, not RaDe-trained or GT',
             filtering=dict(alpha_min=.95, near=.2, far=6., max_center_difference=.06, max_3x3_jump=.08,
                            voxel=.012, sdf_trunc=.036, remove_components_below_triangles=40, simplify_faces=30000,
                            bounds='high opacity original centers min/max plus .06, original world frame'),
             regions={'1':'z < -0.35 lower style region','2':'-0.35 <= z < 0.20 middle style region','3':'z >= 0.20 upper style region'},
             region_provenance='authored world-height thresholds; no automatic semantics or PartField',
             styles={str(i):dict(angle=a, spacing=.045, length=.22, width=1.) for i,a in [(1,0.),(2,45.),(3,-25.)]},
             changed_variable=dict(region=2, angle=95., other_parameters_and_paths='fixed'),
             renderer=dict(size=512, supersample=2, depth_tolerance=.004, contour='view mask/depth edges; separate layer'),
             expected_tests=['camera inverse and real cached camera alignment', 'reject low-confidence/jump depths',
                             'non-target 3D paths exact on region edit', 'cold reload exact pixels', 'real ray occlusion',
                             'full-object static views, weak sides and full trajectory contact sheets'],
             orbit=[orbit_camera(17+30*k,20,4.7) for k in range(12)],
             zoom=[orbit_camera(47,25,float(d)) for d in np.linspace(5.1,4.1,6)],
             scientific_scope='engineering milestone only; H1/H2 not tested; historical NO_GO and zero-headroom unchanged',
             exposure='training poses used for proxy; archived reference views historically exposed; virtual views construction holdout, not blind evaluation',
             resources=dict(cpu_affinity=sorted(__import__('os').sched_getaffinity(0)), numeric_threads=1, gpu=False),
             deadline_minutes=55)
    js(path,p)
    js(Path('docs/partwise_sketch_hatching_v04')/'UNIT001_PROTOCOL.json',p)
    print(json.dumps(dict(protocol=str(path),sha256=sha(path),train_views=[c['view'] for c in cameras])))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--scene',default='chair');p.add_argument('--unit',required=True)
    a=p.parse_args();freeze(a.scene,Path(a.unit))
