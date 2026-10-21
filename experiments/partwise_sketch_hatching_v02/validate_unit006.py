"""Audit frozen RGB/camera input without importing its generator or renderer.

Geometry is checked from explicit spherical-camera formulae and the independently
hashed oracle mesh. The actual PNG, camera-only consumer, isolated official
RaDe-GS camera reader, and rejection controls are exercised. No training runs.
"""
import os

os.environ['CUDA_VISIBLE_DEVICES'] = ''
for _key in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS',
             'NUMEXPR_NUM_THREADS'):
    os.environ[_key] = '1'
os.environ['PYTHONDONTWRITEBYTECODE'] = '1'
os.sched_setaffinity(0, [0, 1])

import argparse
import ast
import copy
import hashlib
import json
import math
from pathlib import Path
import shutil
import sys
import time
from typing import NamedTuple

import numpy as np
from PIL import Image

WORK = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(WORK))
DEFAULT_UNIT = Path('/mnt/hdd1/u00134/partwise_sketch_hatching_p1_v02/units/unit_006')
SPLITS = ('train', 'dev', 'test')
CAMERA_FIELDS = {
    'id', 'split', 'azimuth_deg', 'elevation_deg', 'distance', 'width', 'height',
    'focal_px', 'principal_point', 'R_w2c', 't_w2c', 'eye_world', 'c2w_opengl',
    'rgb_path', 'rgb_sha256',
}
TOL = 1e-9


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_json(path, value):
    Path(path).write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def split_dir(root, split):
    return root / ('train' if split == 'train' else f'evaluation/{split}')


def independent_pose(frame, protocol):
    """Closed-form axes: deliberately independent of the producer's look-at API."""
    a, e = math.radians(frame['azimuth_deg']), math.radians(frame['elevation_deg'])
    sa, ca, se, ce = math.sin(a), math.cos(a), math.sin(e), math.cos(e)
    target = np.array(protocol['camera']['look_at'], dtype=np.float64)
    eye = target + frame['distance'] * np.array([sa * ce, se, ca * ce])
    rotation = np.array([[ca, 0., -sa], [se * sa, -ce, se * ca],
                         [-ce * sa, -se, -ce * ca]])
    return rotation, -(rotation @ eye), eye


def camera_metrics(frame, protocol, vertices):
    expected_r, expected_t, expected_eye = independent_pose(frame, protocol)
    rotation = np.asarray(frame['R_w2c'], dtype=np.float64)
    translation = np.asarray(frame['t_w2c'], dtype=np.float64)
    eye = np.asarray(frame['eye_world'], dtype=np.float64)
    gl = np.asarray(frame['c2w_opengl'], dtype=np.float64)
    require(rotation.shape == (3, 3) and translation.shape == (3,)
            and eye.shape == (3,) and gl.shape == (4, 4), 'wrong camera shape')
    require(all(np.isfinite(x).all() for x in (rotation, translation, eye, gl)),
            'nonfinite camera')
    error = {
        'rotation_max_abs': float(np.max(np.abs(rotation - expected_r))),
        'translation_max_abs': float(np.max(np.abs(translation - expected_t))),
        'eye_max_abs': float(np.max(np.abs(eye - expected_eye))),
        'orthogonality_max_abs': float(np.max(np.abs(rotation @ rotation.T - np.eye(3)))),
        'determinant_abs_error': float(abs(np.linalg.det(rotation) - 1.)),
        'center_max_abs': float(np.max(np.abs(rotation @ eye + translation))),
    }
    w2c = np.eye(4)
    w2c[:3, :3], w2c[:3, 3] = rotation, translation
    cv = gl @ np.diag([1., -1., -1., 1.])
    error['opengl_roundtrip_max_abs'] = float(np.max(np.abs(cv @ w2c - np.eye(4))))
    xc = vertices @ rotation.T + translation
    uv = xc[:, :2] / xc[:, 2:] * frame['focal_px'] + frame['principal_point']
    ray = np.column_stack(((uv - frame['principal_point']) / frame['focal_px'],
                           np.ones(len(uv))))
    reconstructed = (ray * xc[:, 2:] - translation) @ rotation
    error['project_backproject_max_abs'] = float(np.max(np.abs(reconstructed - vertices)))
    expected_xc = vertices @ expected_r.T + expected_t
    expected_uv = (expected_xc[:, :2] / expected_xc[:, 2:] * frame['focal_px']
                   + frame['principal_point'])
    error['independent_projection_max_abs_px'] = float(np.max(np.abs(uv - expected_uv)))
    margins = [float(uv[:, 0].min()), float(frame['width'] - 1 - uv[:, 0].max()),
               float(uv[:, 1].min()), float(frame['height'] - 1 - uv[:, 1].max())]
    return dict(errors=error, projection_margins_px=dict(zip(('left', 'right', 'top', 'bottom'), margins)),
                minimum_depth=float(xc[:, 2].min()),
                passed=bool(max(error.values()) < TOL and xc[:, 2].min() > 0
                            and min(margins) >= 8.))


def check_split_sets(records, protocol, root):
    """Reject coordinate, camera, ID, or resolved-file overlap between splits."""
    seen = {key: set() for key in ('angles', 'camera', 'id', 'file')}
    sizes = {}
    for split in SPLITS:
        frames = records[split]['frames']
        expected = {(float(a), float(e)) for e in protocol['camera']['elevations_deg']
                    for a in protocol['splits'][split]['azimuths_deg']}
        angles = {(float(f['azimuth_deg']), float(f['elevation_deg'])) for f in frames}
        require(len(frames) == protocol['splits'][split]['count'], f'{split}: wrong count')
        require(angles == expected and len(angles) == len(frames), f'{split}: frozen angle set differs')
        groups = {
            'angles': angles,
            'camera': {tuple(np.asarray(f['R_w2c']).ravel()) + tuple(f['t_w2c']) for f in frames},
            'id': {f['id'] for f in frames},
            'file': {str((split_dir(root, split) / f['rgb_path']).resolve()) for f in frames},
        }
        for key, values in groups.items():
            require(len(values) == len(frames), f'{split}: duplicate {key}')
            require(not (seen[key] & values), f'{split}: cross-split {key} overlap')
            seen[key].update(values)
        sizes[split] = len(frames)
    return dict(counts=sizes, total=sum(sizes.values()), pairwise_disjoint=True)


def extracted_definitions(path, names, namespace):
    """Compile unmodified AST nodes only, avoiding full-loader import side effects."""
    tree = ast.parse(path.read_text(), filename=str(path))
    nodes = [node for node in tree.body if isinstance(node, (ast.FunctionDef, ast.ClassDef))
             and node.name in names]
    require({n.name for n in nodes} == set(names), f'missing official definitions in {path}')
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(path), 'exec'), namespace)
    return {node.name: [node.lineno, node.end_lineno] for node in nodes}


def official_reader_check(unit, records, vertices):
    inventory = json.loads((unit / 'RECONSTRUCTION_INVENTORY.json').read_text())
    source = Path(inventory['official_loader_compatibility']['source_path'])
    require(sha(source) == inventory['official_loader_compatibility']['sha256'],
            'official camera-reader source hash changed')
    graphics = source.parents[1] / 'utils/graphics_utils.py'
    ndc_source = source.parents[1] / 'submodules/diff-gaussian-rasterization/cuda_rasterizer/auxiliary.h'
    require('return ((v + 1.0) * S - 1.0) * 0.5;' in ndc_source.read_text(),
            'official ndc2Pix formula differs from inspected source')
    namespace = dict(os=os, np=np, json=json, Image=Image, Path=Path,
                     NamedTuple=NamedTuple, math=math)
    ranges = extracted_definitions(graphics, {'focal2fov', 'fov2focal'}, namespace)
    ranges.update(extracted_definitions(source, {'CameraInfo', 'readCamerasFromTransforms'}, namespace))
    result = dict(source_path=str(source), source_sha256=sha(source),
                  graphics_source_path=str(graphics), graphics_sha256=sha(graphics),
                  ndc_source_path=str(ndc_source), ndc_source_sha256=sha(ndc_source),
                  ndc2Pix='((v + 1.0) * S - 1.0) * 0.5',
                  raster_formula_test='Float64 CPU transcription of inspected ndc2Pix and symmetric FoV projection; no CUDA execution.',
                  unmodified_ast_definitions=ranges, splits={},
                  full_scene_loader_called=False, training_called=False)
    for split in SPLITS:
        directory = split_dir(unit / 'dataset', split)
        loaded = namespace['readCamerasFromTransforms'](
            str(directory), f'transforms_{split}.json', True)
        frames = records[split]['frames']
        require(len(loaded) == len(frames), f'official {split} count differs')
        maximum = dict(rotation=0., translation=0., focal=0., projection_px=0.)
        for camera, frame in zip(loaded, frames):
            require(camera.image_name == frame['id'], 'official frame order/name differs')
            require((camera.width, camera.height) == (512, 512), 'official size differs')
            require(camera.depth is None and camera.mask is None, 'official reader loaded oracle')
            r, t = np.asarray(frame['R_w2c']), np.asarray(frame['t_w2c'])
            errors = {
                'rotation': float(np.max(np.abs(camera.R.T - r))),
                'translation': float(np.max(np.abs(camera.T - t))),
                'focal': max(abs(namespace['fov2focal'](camera.FovX, camera.width) - 600.),
                             abs(namespace['fov2focal'](camera.FovY, camera.height) - 600.)),
            }
            canonical = vertices @ r.T + t
            official = vertices @ camera.R + camera.T
            canonical_uv = (canonical[:, :2] / canonical[:, 2:] * frame['focal_px']
                            + frame['principal_point'])
            ndc = official[:, :2] / official[:, 2:] / np.array(
                [math.tan(camera.FovX / 2), math.tan(camera.FovY / 2)])
            official_uv = ((ndc + 1.) * [camera.width, camera.height] - 1.) * .5
            errors['projection_px'] = float(np.max(np.abs(
                canonical_uv - official_uv)))
            for key, value in errors.items():
                maximum[key] = max(maximum[key], value)
            with Image.open(directory / frame['rgb_path']) as image:
                require(np.array_equal(np.array(camera.image), np.array(image)),
                        f'official loaded RGB differs: {frame["id"]}')
            camera.image.close()
        require(max(maximum.values()) < TOL, f'official {split} camera mismatch: {maximum}')
        result['splits'][split] = dict(count=len(loaded), maximum_absolute_errors=maximum,
                                      rgb_pixels_exact=True)
    empty = namespace['readCamerasFromTransforms'](
        str(unit / 'dataset/train'), 'transforms_test.json', True)
    require(not empty, 'training source exposes official test frames')
    require(not (unit / 'dataset/train/points3d.ply').exists(), 'unexpected training PLY')
    result['training_test_list_empty'] = True
    return result


def expect_rejection(action):
    try:
        action()
    except (ValueError, AssertionError, KeyError, PermissionError) as error:
        return dict(rejected=True, error_type=type(error).__name__, message=str(error))
    raise AssertionError('fault was accepted')


def loader_and_fault_checks(unit, records, protocol, vertices):
    from experiments.partwise_sketch_hatching_v02.reconstruction_dataset import load_dataset

    root = unit / 'dataset'
    result = dict(splits={}, faults={})
    for split in SPLITS:
        samples = load_dataset(root) if split == 'train' else load_dataset(root, split=split, purpose='evaluate')
        require(len(samples) == protocol['splits'][split]['count'], f'consumer {split} wrong count')
        for sample, frame in zip(samples, records[split]['frames']):
            require(set(sample) == CAMERA_FIELDS | {'rgb'}, f'consumer unexpected fields: {set(sample)}')
            require(sample['id'] == frame['id'], 'consumer frame order differs')
            require(sample['rgb'].shape == (512, 512, 3) and sample['rgb'].dtype == np.uint8,
                    'consumer RGB layout differs')
        result['splits'][split] = dict(count=len(samples), only_rgb_camera_fields=True)
        del samples
    for split in ('dev', 'test'):
        result['faults'][f'{split}_without_evaluation_purpose'] = expect_rejection(
            lambda split=split: load_dataset(root, split=split))

    # Preserve the mutated fixtures as evidence. Only train inputs are copied.
    fault_root = unit / 'validation_faults'
    fault_root.mkdir(exist_ok=True)
    for kind in ('path_escape', 'oracle_inclusion', 'non_png', 'nonfinite_focal', 'inconsistent_opengl'):
        destination = fault_root / kind
        require(not destination.exists(), f'fault fixture already exists: {destination}')
        shutil.copytree(root / 'train', destination / 'train')
        shutil.copy2(root / 'DATASET.json', destination / 'DATASET.json')
        cameras = copy.deepcopy(records['train'])
        if kind == 'path_escape':
            shutil.copy2(root / 'train' / cameras['frames'][0]['rgb_path'], destination / 'escaped.png')
            cameras['frames'][0]['rgb_path'] = '../escaped.png'
        elif kind == 'oracle_inclusion':
            cameras['frames'][0]['oracle_path'] = str(unit / 'oracle_only/lamp_mesh.npz')
        elif kind == 'non_png':
            shutil.copy2(root / 'train' / cameras['frames'][0]['rgb_path'], destination / 'train/rgb/wrong.npy')
            cameras['frames'][0]['rgb_path'] = 'rgb/wrong.npy'
        elif kind == 'nonfinite_focal':
            cameras['frames'][0]['focal_px'] = '__NONFINITE__'
        else:
            cameras['frames'][0]['c2w_opengl'][0][3] += .1
        camera_path = destination / 'train/cameras.json'
        if kind == 'nonfinite_focal':
            # A syntactically valid large JSON number overflows float64 to inf.
            camera_path.write_text(json.dumps(cameras, indent=2).replace('"__NONFINITE__"', '1e309') + '\n')
        else:
            write_json(camera_path, cameras)
        result['faults'][kind] = expect_rejection(lambda: load_dataset(destination))

    overlap = copy.deepcopy(records)
    for key in ('azimuth_deg', 'elevation_deg', 'R_w2c', 't_w2c', 'eye_world'):
        overlap['dev']['frames'][0][key] = copy.deepcopy(records['train']['frames'][0][key])
    result['faults']['cross_split_overlap'] = expect_rejection(
        lambda: check_split_sets(overlap, protocol, root))
    write_json(fault_root / 'cross_split_overlap_camera_records.json', overlap)
    flipped = copy.deepcopy(records['train']['frames'][0])
    flipped['R_w2c'][0] = [-x for x in flipped['R_w2c'][0]]
    flipped_metrics = camera_metrics(flipped, protocol, vertices)
    require(not flipped_metrics['passed'], 'independent projection accepted flipped camera axis')
    result['faults']['flipped_camera_axis'] = dict(rejected=True, metrics=flipped_metrics)
    write_json(fault_root / 'flipped_camera_axis.json', flipped)
    result['faults_scope'] = ('Dataset loader rejects evaluation access, path escape, unknown oracle key and '
                              'non-PNG/nonfinite/inconsistent-camera input; independent global checks reject '
                              'split overlap and axis flip. Per-split loader does not inspect held-out metadata.')
    return result


def validate(unit):
    start = time.perf_counter()
    protocol = json.loads((unit / 'PROTOCOL.json').read_text())
    root = unit / 'dataset'
    records = {split: json.loads((split_dir(root, split) / 'cameras.json').read_text())
               for split in SPLITS}
    with np.load(unit / 'oracle_only/lamp_mesh.npz', allow_pickle=False) as mesh:
        vertices = np.asarray(mesh['vertices'], dtype=np.float64)
    checks, evidence, frames = {}, {}, []

    def check(name, action):
        try:
            evidence[name] = action()
            checks[name] = dict(passed=True)
        except Exception as error:
            checks[name] = dict(passed=False, error_type=type(error).__name__, message=str(error))

    def input_hashes():
        hashes = []
        for record in protocol['inputs']:
            actual = sha(record['path'])
            require(actual == record['sha256'], f'frozen input changed: {record["path"]}')
            hashes.append(dict(path=record['path'], sha256=actual))
        mesh_input = next(record for record in protocol['inputs'] if record['path'].endswith('/lamp_mesh.npz'))
        require(sha(unit / 'oracle_only/lamp_mesh.npz') == mesh_input['sha256'], 'oracle mesh changed')
        lock_path = unit / 'SOURCE_LOCK.json'
        if lock_path.exists():
            lock = json.loads(lock_path.read_text())
            rows = (lock['files'].items() if isinstance(lock['files'], dict)
                    else ((row['path'], row['sha256']) for row in lock['files']))
            for path, expected in rows:
                require(sha(path) == expected, f'locked source changed: {path}')
                hashes.append(dict(path=path, sha256=expected))
        return dict(inputs=hashes, protocol_sha256=sha(unit / 'PROTOCOL.json'),
                    oracle_mesh_sha256=sha(unit / 'oracle_only/lamp_mesh.npz'))

    check('frozen_input_and_source_hashes', input_hashes)
    check('exact_disjoint_splits', lambda: check_split_sets(records, protocol, root))

    def training_isolation():
        manifest = json.loads((root / 'DATASET.json').read_text())
        require(manifest['schema'] == 'lamp_rgb_camera_v1', 'wrong dataset schema')
        require(manifest['counts'] == {s: protocol['splits'][s]['count'] for s in SPLITS},
                'manifest counts differ')
        require(manifest['splits'] == {'train': 'train/cameras.json',
                                      'dev': 'evaluation/dev/cameras.json',
                                      'test': 'evaluation/test/cameras.json'}, 'manifest paths differ')
        expected_files = {'cameras.json', 'transforms_train.json', 'transforms_test.json'}
        expected_files.update(frame['rgb_path'] for frame in records['train']['frames'])
        files = {str(path.relative_to(root / 'train')) for path in (root / 'train').rglob('*') if path.is_file()}
        require(files == expected_files, f'training source has unexpected or missing files: {files ^ expected_files}')
        require(json.loads((root / 'train/transforms_test.json').read_text())['frames'] == [],
                'training transforms expose test data')
        for split in SPLITS:
            require(records[split]['split'] == split, f'wrong declared split {split}')
            for frame in records[split]['frames']:
                require(set(frame) == CAMERA_FIELDS, f'unexpected camera fields: {set(frame) ^ CAMERA_FIELDS}')
                require(frame['split'] == split, f'wrong frame split: {frame["id"]}')
        return dict(training_files=len(files), only_train_RGB_and_cameras=True,
                    oracle_sibling=str(unit / 'oracle_only'), oracle_never_training_input=True)

    check('training_export_isolation', training_isolation)

    for split in SPLITS:
        for frame in records[split]['frames']:
            def frame_check(frame=frame, split=split):
                path = split_dir(root, split) / frame['rgb_path']
                require(path.resolve().is_relative_to(split_dir(root, split).resolve()), 'RGB escapes split')
                require(path.suffix == '.png', 'RGB suffix is not PNG')
                actual_hash = sha(path)
                require(actual_hash == frame['rgb_sha256'], 'PNG hash differs')
                with Image.open(path) as image:
                    image.load()
                    require(image.format == 'PNG' and image.mode == 'RGB' and image.size == (512, 512),
                            'not full 512x512 RGB PNG')
                    rgb = np.asarray(image)
                require((frame['width'], frame['height'], frame['focal_px'], frame['distance'])
                        == (512, 512, 600., 4.5)
                        and frame['principal_point'] == protocol['camera']['principal_point'],
                        'frozen intrinsics/distance differ')
                geometry = camera_metrics(frame, protocol, vertices)
                oracle_path = unit / 'oracle_only' / split / f'{frame["id"]}.npz'
                with np.load(oracle_path, allow_pickle=False) as oracle:
                    require(set(oracle.files) == {'depth_z', 'normal_world', 'part_id', 'coverage'},
                            'wrong oracle fields')
                    depth, normal, labels, coverage = (oracle[key] for key in
                                                      ('depth_z', 'normal_world', 'part_id', 'coverage'))
                    require(depth.shape == labels.shape == coverage.shape == (512, 512)
                            and normal.shape == (512, 512, 3), 'wrong oracle shape')
                    require(all(np.isfinite(x).all() for x in (depth, normal, labels, coverage)),
                            'nonfinite oracle arrays')
                    require(set(np.unique(labels)) <= {0, 1, 2, 3}, 'unknown part ID')
                    require(depth.min() >= 0 and coverage.min() >= 0 and coverage.max() <= 1,
                            'oracle range invalid')
                    counts = {str(part): int(np.count_nonzero(labels == part)) for part in (1, 2, 3)}
                    actual_rgb_counts = {str(part): int(np.count_nonzero((labels == part) & np.any(rgb != 255, axis=2)))
                                         for part in (1, 2, 3)}
                row = dict(id=frame['id'], split=split, rgb_sha256=actual_hash,
                           oracle_sha256=sha(oracle_path), geometry=geometry,
                           visible_pixels_by_part=counts, nonwhite_RGB_pixels_by_part=actual_rgb_counts,
                           passed=bool(geometry['passed'] and min(counts.values()) >= 50
                                       and min(actual_rgb_counts.values()) >= 50))
                frames.append(row)
                require(row['passed'], 'frozen geometry/part-visibility gate failed; raw row retained')
                return dict(id=frame['id'], decoded=True, passed=True)
            check(f'frame_{frame["id"]}', frame_check)

    check('isolated_loader_and_fault_controls', lambda: loader_and_fault_checks(unit, records, protocol, vertices))
    check('official_RaDeGS_camera_reader', lambda: official_reader_check(unit, records, vertices))

    def cold_replay_check():
        original = root / 'train/rgb/train_e0_a00.png'
        replay = unit / 'cold_replay/train_e0_a00.png'
        receipt = json.loads((unit / 'COLD_REPLAY.json').read_text())
        require(sha(original) == sha(replay), 'cold replay PNG hash differs')
        with Image.open(original) as left, Image.open(replay) as right:
            left.load()
            right.load()
            require(np.array_equal(np.array(left), np.array(right)), 'cold replay RGB differs')
        require(receipt['rgb_exact'] and receipt['png_sha256'] == sha(replay)
                and receipt['original_sha256'] == sha(original), 'cold replay receipt differs')
        return dict(id='train_e0_a00', png_sha256=sha(replay), pixel_exact=True,
                    scope='Secondary deterministic regeneration check; not the application quality gate')

    check('fresh_process_one_view_RGB_replay', cold_replay_check)
    valid = len(frames) == 120 and all(record['passed'] for record in checks.values())
    result = dict(verdict='VALID' if valid else 'INVALID', checks=checks, evidence=evidence,
                  frame_metrics=frames, seconds=time.perf_counter() - start,
                  minimum_visible_pixels_by_part={str(p): min((f['visible_pixels_by_part'][str(p)] for f in frames), default=0)
                                                  for p in (1, 2, 3)},
                  minimum_projected_margin_px=min((min(f['geometry']['projection_margins_px'].values())
                                                   for f in frames), default=0.),
                  scientific_gates=dict(synthetic_input_software='GO' if valid else 'NO_GO',
                                        visual_review='REQUIRES_SEPARATE_ACTUAL_IMAGE_REVIEW',
                                        reconstructed_lamp='BLOCKED_CPU_NO_TRAINED_LAMP',
                                        full_P1='NOT_CLAIMED', H1_H2='NOT_TESTED'),
                  scope='Independent all-view RGB/camera input readiness; no generator/renderer import and no training.',
                  limitations=['Oracle part masks come from the producer; independent camera/mesh bounds do not establish photometric reconstruction accuracy.',
                               'Authored geometry and profiles were previously exposed. Test RGB integrity inspection is not blind scientific evaluation.',
                               'Official compatibility covers the unchanged camera-reader function only; the full loader and training were not invoked.',
                               'Existing NPR density/visibility failures and diagnostic-preview status remain unchanged.'])
    write_json(unit / 'INDEPENDENT_VALIDATION.json', result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--unit', type=Path, default=DEFAULT_UNIT)
    args = parser.parse_args()
    require(args.unit.resolve() == DEFAULT_UNIT.resolve(), 'validator restricted to authorized unit_006')
    result = validate(args.unit)
    print(json.dumps(dict(verdict=result['verdict'], seconds=result['seconds'],
                          failing_checks={k: v for k, v in result['checks'].items() if not v['passed']},
                          minimum_visible_pixels_by_part=result['minimum_visible_pixels_by_part'],
                          minimum_projected_margin_px=result['minimum_projected_margin_px']), allow_nan=False))
    return 0 if result['verdict'] == 'VALID' else 1


if __name__ == '__main__':
    raise SystemExit(main())
