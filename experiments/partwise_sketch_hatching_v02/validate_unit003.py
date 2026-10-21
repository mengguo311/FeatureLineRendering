"""Independent file, image, mask, and video audit for the frozen base edit.

This module never imports a producer or invokes its renderer. It independently
replays seed selection, reconstructs analytic masks, and measures actual PNGs.
Primitive equality is a secondary regression control, not an application gate.
"""
import os

os.environ['CUDA_VISIBLE_DEVICES'] = ''
for _name in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS',
              'NUMEXPR_NUM_THREADS'):
    os.environ[_name] = '1'
os.environ['PYTHONDONTWRITEBYTECODE'] = '1'
os.environ['TMPDIR'] = '/mnt/hdd1/u00134/partwise_sketch_hatching_p1_v02/orchestration/scratch'
os.sched_setaffinity(0, [0, 1])

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time

import numpy as np
from PIL import Image
from scipy import ndimage

WORK = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(WORK))
from experiments.partwise_sketch_hatching import core

DEFAULT_UNIT = Path('/mnt/hdd1/u00134/partwise_sketch_hatching_p1_v02/units/unit_003')
DEFAULT_FFMPEG = '/home/u00134/3dgs_line/partwise_sketch_hatching_p0p1_v01/.runtime_p0/imageio_ffmpeg/binaries/ffmpeg-linux-x86_64-v7.0.2'
VIEWS = (30, 120, 210, 300)
SIZE = 512
FRAMES = 24
PARTS = (1, 2, 3)
INK_THRESHOLD = .1


def native(value):
    if isinstance(value, dict):
        return {str(k): native(v) for k, v in value.items()}
    if isinstance(value, (tuple, list)):
        return [native(v) for v in value]
    if isinstance(value, np.ndarray):
        return native(value.tolist())
    if isinstance(value, np.generic):
        return native(value.item())
    if isinstance(value, float) and not np.isfinite(value):
        return None
    if isinstance(value, Path):
        return str(value)
    return value


def write_json(path, value):
    Path(path).write_text(json.dumps(native(value), indent=2, ensure_ascii=False,
                                    allow_nan=False) + '\n')


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def load_npz(path):
    with np.load(path, allow_pickle=False) as data:
        return {key: data[key].copy() for key in data.files}


def rgb(path):
    with Image.open(path) as image:
        result = np.array(image.convert('RGB'), dtype=np.uint8)
    if result.shape != (SIZE, SIZE, 3):
        raise AssertionError(f'wrong image dimensions: {path}: {result.shape}')
    if not np.array_equal(result[..., 0], result[..., 1]) or not np.array_equal(result[..., 0], result[..., 2]):
        raise AssertionError(f'expected grayscale display image: {path}')
    return result


def image(path):
    return rgb(path)[..., 0].astype(np.float64) / 255.


def strokes(path):
    data = load_npz(path)
    ids = list(map(str, data['ids']))
    if len(set(ids)) != len(ids):
        raise AssertionError('duplicate stroke IDs')
    answer = {}
    for index, sid in enumerate(ids):
        lo, hi = data['offsets'][index:index + 2]
        answer[sid] = dict(part=int(data['parts'][index]),
                           faces=data['faces'][lo:hi], bary=data['bary'][lo:hi],
                           ink=float(data['inks'][index]))
    return answer


def edit_metrics(before, after, labels):
    """Display-image L1, with independently obtained base mask and fixed band."""
    change = np.abs(after - before)
    target = labels == 3
    distance = ndimage.distance_transform_edt(~target)
    masks = {
        'inside': target,
        'boundary_band': (~target) & (distance <= 2),
        'far_other_parts': (labels > 0) & (~target) & (distance > 2),
        'far_background': (labels == 0) & (distance > 2),
    }
    total = float(change.sum())
    masses = {name: float(change[mask].sum()) for name, mask in masks.items()}
    result = dict(total_delta=total, inside_delta=masses['inside'],
                  inside_mean_delta=float(change[target].mean()) if target.any() else 0.,
                  mask_pixels=int(target.sum()), nonzero_edit=masses['inside'] > 10.,
                  band_px=2, outside_fraction=(total - masses['inside']) / max(total, 1e-15),
                  region_pixels={name: int(mask.sum()) for name, mask in masks.items()})
    for name, mass in masses.items():
        result[name + '_delta'] = mass
        result[name + '_fraction'] = mass / max(total, 1e-15)
    result['go'] = bool(result['nonzero_edit'] and result['far_other_parts_fraction'] <= .02
                        and result['far_background_fraction'] <= .02)
    return result


def footprint(ink, labels):
    """Actual hatch coverage, excluding contour/ring support from this measure."""
    answer = {}
    for part in (0,) + PARTS:
        mask = labels == part
        area = int(mask.sum())
        support = int(np.count_nonzero((ink >= INK_THRESHOLD) & mask))
        mass = float(ink[mask].sum())
        answer[str(part)] = dict(mask_pixels=area, hatch_ink_mass=mass,
                                 support_pixels=support,
                                 support_fraction=support / max(area, 1),
                                 mean_hatch_ink=mass / max(area, 1))
    return answer


def pair_metrics(before, after, old_layers, new_layers, labels):
    old = footprint(old_layers['hatch'], labels)
    new = footprint(new_layers['hatch'], labels)
    old_base, new_base = old['3'], new['3']
    if old_base['hatch_ink_mass'] <= 0 or old_base['support_pixels'] <= 0:
        raise AssertionError('baseline base is empty')
    ink_ratio = new_base['hatch_ink_mass'] / old_base['hatch_ink_mass']
    support_ratio = new_base['support_pixels'] / old_base['support_pixels']
    coverage_go = (.35 <= ink_ratio <= .8 and support_ratio >= .35
                   and new_base['support_fraction'] >= .05)
    edit = edit_metrics(before, after, labels)
    regression = {
        'contours_unchanged': np.array_equal(old_layers['contours'], new_layers['contours']),
        'rings_unchanged': np.array_equal(old_layers['rings'], new_layers['rings']),
        'base_thinning_adds_no_hatch_ink': bool(np.all(new_layers['hatch'] <= old_layers['hatch'] + 1e-12)),
        'base_thinning_adds_no_display_ink': bool(np.all(after >= before - 1e-12)),
    }
    return dict(edit=edit, baseline_footprint=old, candidate_footprint=new,
                base_ink_ratio=ink_ratio, base_support_ratio=support_ratio,
                base_coverage_go=bool(coverage_go), regression=regression,
                quantitative_go=bool(edit['go'] and coverage_go and all(regression.values())))


def assert_camera(stored, expected, path):
    for key in ('R', 't', 'eye', 'center', 'size', 'focal'):
        if not np.allclose(stored[key], expected[key], atol=1e-12, rtol=0):
            raise AssertionError(f'camera mismatch {key}: {path}')


def read_render(stem, camera):
    pixels = image(stem.with_suffix('.png'))
    layers = load_npz(stem.with_suffix('.npz'))
    record = json.loads(stem.with_suffix('.json').read_text())
    assert_camera(record['camera'], camera, stem)
    for key in ('image', 'hatch', 'contours', 'rings', 'depth', 'parts'):
        if key not in layers or layers[key].shape != (SIZE, SIZE):
            raise AssertionError(f'missing/wrong {key}: {stem}')
    for key in ('image', 'hatch', 'contours', 'rings'):
        layer = layers[key]
        if not np.isfinite(layer).all() or layer.min() < -1e-12 or layer.max() > 1 + 1e-12:
            raise AssertionError(f'invalid ink/image range: {stem}/{key}')
    rounded = np.uint8(np.rint(np.clip(layers['image'], 0, 1) * 255))
    if not np.array_equal(rounded, np.uint8(np.rint(pixels * 255))):
        raise AssertionError(f'PNG differs from saved display image: {stem}')
    components = [layers[key] for key in ('hatch', 'contours', 'rings')]
    lower = np.maximum.reduce(components)
    upper = np.minimum(np.sum(components, axis=0), 1.)
    observed_ink = 1. - pixels
    tolerance = .5 / 255. + 1e-12
    if np.any(observed_ink < lower - tolerance) or np.any(observed_ink > upper + tolerance):
        raise AssertionError(f'PNG violates pre-downsampling union bounds: {stem}')
    return pixels, layers, record


def independent_reference(unit, cfg, camera, path):
    depth, labels = core.analytic_reference(cfg['asset'], camera)
    stored = load_npz(path)
    if not np.array_equal(stored['parts'], labels):
        raise AssertionError(f'saved independent mask differs: {path}')
    if not np.allclose(stored['depth'], depth, atol=1e-12, rtol=0, equal_nan=True):
        raise AssertionError(f'saved independent depth differs: {path}')
    return labels


def audit_selection(unit, cfg):
    baseline = strokes(unit / 'inputs/mixed.npz')
    selected = strokes(unit / 'inputs/selected.npz')
    metadata = json.loads((unit / 'SELECTION.json').read_text())
    if not set(selected).issubset(baseline):
        raise AssertionError('selection introduced new IDs')
    unchanged = 0
    for sid, old in baseline.items():
        if old['part'] != 3 and sid not in selected:
            raise AssertionError(f'non-target stroke removed: {sid}')
        if sid in selected:
            new = selected[sid]
            if old['part'] != new['part'] or old['ink'] != new['ink'] or not np.array_equal(old['faces'], new['faces']) or not np.array_equal(old['bary'], new['bary']):
                raise AssertionError(f'retained stroke changed: {sid}')
            unchanged += int(old['part'] != 3)
    groups = {}
    selected_groups = {}
    for collection, target in ((baseline, groups), (selected, selected_groups)):
        for sid, stroke in collection.items():
            if stroke['part'] == 3:
                pair, layer = sid.rsplit(':layer', 1)
                target.setdefault(pair, set()).add(int(layer))
    if len(groups) != 150 or len(selected_groups) != 75:
        raise AssertionError('frozen 75-of-150 pair count differs')
    if any(layers != {0, 1} for layers in list(groups.values()) + list(selected_groups.values())):
        raise AssertionError('incomplete cross-layer pair')
    source = load_npz(unit / 'inputs/lamp_mesh.npz')
    mesh = core.finalize_mesh(source['vertices'], source['faces'], source['parts'])
    rng = np.random.default_rng(np.random.SeedSequence([cfg['seed'], 3]))
    candidate_faces = np.flatnonzero(mesh['parts'] == 3)
    probabilities = mesh['areas'][candidate_faces]
    probabilities = probabilities / probabilities.sum()
    positions = []
    pair_ids = [f'p3:seed{i:04d}' for i in range(150)]
    for index in range(150):
        face = int(rng.choice(candidate_faces, p=probabilities))
        random = rng.random(2)
        square = np.sqrt(random[0])
        bary = np.array([1 - square, square * (1 - random[1]), square * random[1]])
        positions.append(bary @ mesh['tri'][face])
    positions = np.array(positions)
    ordered = [0]
    distance = np.sum((positions - positions[0]) ** 2, axis=1)
    available = np.ones(150, dtype=bool)
    available[0] = False
    for _ in range(149):
        # np.argmax breaks exact ties by ascending seed ID in this ordered array.
        next_index = int(np.argmax(np.where(available, distance, -np.inf)))
        ordered.append(next_index)
        available[next_index] = False
        distance = np.minimum(distance, np.sum((positions - positions[next_index]) ** 2, axis=1))
    expected = [pair_ids[index] for index in ordered]
    if set(selected_groups) != set(expected[:75]):
        raise AssertionError('selected pairs differ from independent farthest-seed prefix')
    if list(metadata['ordered_pair_ids']) != expected or set(metadata['selected_pair_ids']) != set(expected[:75]):
        raise AssertionError('reported selection IDs/order differ')
    if metadata['keep_pairs'] != 75 or metadata['available_pairs'] != 150:
        raise AssertionError('selection metadata pair counts differ')
    for index, pair in enumerate(pair_ids):
        if not np.allclose(metadata['seed_positions'][pair], positions[index], atol=1e-12, rtol=0):
            raise AssertionError(f'replayed seed position differs: {pair}')
    return dict(available_pairs=150, retained_pairs=75,
                retained_strokes=len(selected), non_target_strokes_unchanged=unchanged,
                full_farthest_seed_order_reproduced=True,
                selected_pair_ids=expected[:75], both_layers_retained=True,
                algorithm_scope='Euclidean farthest-seed ordering; no geodesic or physical stroke-spacing guarantee',
                regression_scope='Saved paths/ink/IDs are secondary controls, not visual application acceptance')


def decode_video(unit, ffmpeg, name, sources):
    command = [ffmpeg, '-v', 'error', '-threads', '1', '-i', str(unit / 'videos' / f'{name}.mkv'),
               '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-threads', '1', '-']
    result = subprocess.run(command, capture_output=True, timeout=120)
    if result.returncode != 0:
        raise AssertionError(f'{name} decode rc={result.returncode}: {result.stderr.decode(errors="replace")}')
    frames = np.frombuffer(result.stdout, dtype=np.uint8)
    if frames.size != FRAMES * SIZE * SIZE * 3:
        raise AssertionError(f'{name}: wrong decoded byte count: {frames.size}')
    hashes = []
    for index, frame in enumerate(frames.reshape(FRAMES, SIZE, SIZE, 3)):
        if not np.array_equal(frame, rgb(sources[index])):
            raise AssertionError(f'{name}: decoded frame {index} differs from frozen PNG source')
        hashes.append(hashlib.sha256(frame.tobytes()).hexdigest())
    if len(set(hashes)) < 2:
        raise AssertionError(f'{name}: no actual image change')
    return dict(command=command, returncode=result.returncode, decoded_frames=FRAMES,
                all_rgb_exact=True, distinct_frames=len(set(hashes)), frame_sha256=hashes)


def validate(unit, ffmpeg):
    start = time.perf_counter()
    checks, evidence, science = {}, {}, {}
    metrics = {'stills': [], 'orbit': [], 'frozen_thresholds': {
        'target_inside_L1_min_exclusive': 10., 'far_other_fraction_max': .02,
        'far_background_fraction_max': .02, 'boundary_band_px': 2,
        'hatch_support_ink_threshold': INK_THRESHOLD,
        'candidate_base_ink_ratio_min': .35, 'candidate_base_ink_ratio_max': .8,
        'candidate_base_support_ratio_min': .35, 'candidate_base_support_fraction_min': .05,
        'both_isolated_direction_layers_ink_min_exclusive': 0.,
    }}

    def check(name, action):
        try:
            evidence[name] = action()
            checks[name] = {'passed': True}
        except Exception as error:
            checks[name] = dict(passed=False, error_type=type(error).__name__, message=str(error))

    def lock_check():
        lock = json.loads((unit / 'SOURCE_LOCK.json').read_text())
        rows = []
        for filename, expected in lock['files'].items():
            actual = sha(filename)
            if actual != expected:
                raise AssertionError(f'frozen file SHA differs: {filename}')
            rows.append({'path': filename, 'sha256': actual})
        if not rows:
            raise AssertionError('source/input lock is empty')
        return dict(count=len(rows), files=rows)

    check('source_and_input_sha256', lock_check)
    cfg = json.loads((unit / 'CONFIG.json').read_text())
    check('independent_pair_selection_and_non_target_regression', lambda: audit_selection(unit, cfg))

    def baseline_identity():
        previous = unit.parent / 'unit_002'
        files = []
        for azimuth in VIEWS:
            for suffix in ('.png', '.npz', '.json'):
                files.append((unit / 'stills' / f'baseline_{azimuth:03}{suffix}',
                              previous / 'stills' / f'base_{azimuth:03}{suffix}'))
        for index in range(FRAMES):
            for suffix in ('.png', '.npz', '.json'):
                files.append((unit / 'frames/baseline' / f'{index:04}{suffix}',
                              previous / 'frames/orbit' / f'{index:04}{suffix}'))
        records = []
        for current, old in files:
            expected = sha(old)
            if sha(current) != expected:
                raise AssertionError(f'baseline copy differs from immutable unit002: {current}')
            records.append(dict(path=current, source=old, sha256=expected))
        return dict(count=len(records), exact_identity=True, files=records)

    check('inherited_baseline_exact_file_identity', baseline_identity)

    def stills_check():
        for azimuth in VIEWS:
            camera = core.camera(azimuth, 20, 4.5, SIZE, 600)
            labels = independent_reference(unit, cfg, camera, unit / 'stills' / f'reference_{azimuth:03}.npz')
            before, old, _ = read_render(unit / 'stills' / f'baseline_{azimuth:03}', camera)
            after, new, _ = read_render(unit / 'stills' / f'candidate_{azimuth:03}', camera)
            row = pair_metrics(before, after, old, new, labels)
            row['azimuth'] = azimuth
            isolated = {}
            for layer in (0, 1):
                data = load_npz(unit / 'stills' / f'layer{layer}_{azimuth:03}.npz')
                hatch = data['hatch']
                if hatch.shape != (SIZE, SIZE) or not np.isfinite(hatch).all() or hatch.min() < 0:
                    raise AssertionError('invalid isolated layer hatch')
                isolated[str(layer)] = footprint(hatch, labels)['3']
                if np.any(hatch > new['hatch'] + 1e-12):
                    raise AssertionError('isolated base layer exceeds full candidate hatch')
            row['isolated_base_direction_layers'] = isolated
            row['both_direction_layers_visible'] = all(layer['hatch_ink_mass'] > 0 for layer in isolated.values())
            noedit = edit_metrics(before, before, labels)
            distance = ndimage.distance_transform_edt(labels != 3)
            eligible = np.flatnonzero((labels == 2) & (distance > 2))
            if len(eligible) < 16:
                raise AssertionError('insufficient independent far-stem pixels for fixed injection')
            chosen = eligible[np.argsort(-after.ravel()[eligible], kind='stable')[:16]]
            injected = after.copy()
            injected.ravel()[chosen] = 0.
            fault = edit_metrics(before, injected, labels)
            shifted = np.ones_like(after)
            shifted[:, 3:] = after[:, :-3]
            drift = dict(horizontal_shift_px=3,
                         no_drift_L1=float(np.abs(after - after).sum()),
                         drifted_image_L1=float(np.abs(after - shifted).sum()),
                         scope='Known raster displacement sensitivity; no correspondence or temporal stability proof')
            controls_go = (noedit['total_delta'] == 0 and not noedit['nonzero_edit']
                           and fault['far_other_parts_fraction'] > .02
                           and fault['far_other_parts_fraction'] > row['edit']['far_other_parts_fraction']
                           and drift['drifted_image_L1'] > drift['no_drift_L1'])
            row['controls'] = dict(no_edit=noedit, injected_far_stem=fault,
                                   injected_flat_pixel_indices=chosen, raster_drift=drift,
                                   passed=bool(controls_go))
            row['quantitative_go'] = bool(row['quantitative_go'] and row['both_direction_layers_visible'])
            metrics['stills'].append(row)
        science['local_edit_go_four_stills'] = all(row['edit']['go'] for row in metrics['stills'])
        science['nonempty_base_density_go_four_stills'] = all(row['base_coverage_go'] and row['both_direction_layers_visible'] for row in metrics['stills'])
        science['secondary_regression_go_four_stills'] = all(all(row['regression'].values()) for row in metrics['stills'])
        science['quantitative_go_four_stills'] = all(row['quantitative_go'] for row in metrics['stills'])
        science['metric_controls_go_four_stills'] = all(row['controls']['passed'] for row in metrics['stills'])
        if not science['metric_controls_go_four_stills']:
            failed_views = [row['azimuth'] for row in metrics['stills'] if not row['controls']['passed']]
            raise AssertionError(f'metric sensitivity controls failed; all rows retained: {failed_views}')
        return dict(views=list(VIEWS), all_masks_recomputed=True, metric_controls_passed=True)

    check('four_actual_still_views_masks_layers_and_metric_controls', stills_check)

    def orbit_check():
        previous = {}
        for index in range(FRAMES):
            camera = core.camera(15 * index, 20, 4.5, SIZE, 600)
            labels = independent_reference(unit, cfg, camera, unit / 'frames/orbit' / f'reference_{index:04}.npz')
            before, old, _ = read_render(unit / 'frames/baseline' / f'{index:04}', camera)
            after, new, _ = read_render(unit / 'frames/orbit' / f'{index:04}', camera)
            row = pair_metrics(before, after, old, new, labels)
            row.update(frame=index, azimuth=15 * index)
            if previous:
                union = (labels == 3) | (previous['labels'] == 3)
                row['temporal_raw_L1_diagnostic'] = {
                    'baseline_full': float(np.abs(before - previous['baseline']).sum()),
                    'candidate_full': float(np.abs(after - previous['candidate']).sum()),
                    'baseline_base_union': float(np.abs(before - previous['baseline'])[union].sum()),
                    'candidate_base_union': float(np.abs(after - previous['candidate'])[union].sum()),
                    'base_union_pixels': int(union.sum()),
                }
            metrics['orbit'].append(row)
            previous = dict(labels=labels, baseline=before, candidate=after)
        metrics['orbit_diagnostic_summary'] = {
            'frames': FRAMES,
            'frames_meeting_still_numeric_thresholds': sum(row['quantitative_go'] for row in metrics['orbit']),
            'base_ink_ratio_min': min(row['base_ink_ratio'] for row in metrics['orbit']),
            'base_ink_ratio_max': max(row['base_ink_ratio'] for row in metrics['orbit']),
            'base_support_ratio_min': min(row['base_support_ratio'] for row in metrics['orbit']),
            'candidate_support_fraction_min': min(row['candidate_footprint']['3']['support_fraction'] for row in metrics['orbit']),
            'max_far_other_edit_fraction': max(row['edit']['far_other_parts_fraction'] for row in metrics['orbit']),
            'max_far_background_edit_fraction': max(row['edit']['far_background_fraction'] for row in metrics['orbit']),
        }
        return dict(frames=FRAMES, all_cameras_checked=True, all_masks_recomputed=True,
                    scope='All-frame diagnostics; raw temporal image change includes expected projected motion and is not a jitter gate')

    check('all_orbit_frames_masks_and_rendered_temporal_diagnostics', orbit_check)
    check('complete_orbit_video_decode', lambda: decode_video(unit, ffmpeg, 'orbit',
          [unit / 'frames/orbit' / f'{index:04}.png' for index in range(FRAMES)]))
    prescribed_edit = [unit / 'stills/baseline_030.png'] * 12 + [unit / 'stills/candidate_030.png'] * 12
    edit_sources = [unit / 'frames/edit' / f'{index:04}.png' for index in range(FRAMES)]

    def edit_frame_sources():
        for index, (saved, prescribed) in enumerate(zip(edit_sources, prescribed_edit)):
            if not np.array_equal(rgb(saved), rgb(prescribed)):
                raise AssertionError(f'edit PNG frame {index} differs from prescribed baseline/candidate still')
        return dict(frames=FRAMES, first12='baseline_030', last12='candidate_030',
                    all_source_pngs_exact=True)

    check('edit_frame_png_sources_and_frozen_step', edit_frame_sources)
    check('complete_edit_video_decode_and_frozen_step', lambda: decode_video(unit, ffmpeg, 'edit', edit_sources))
    science.update(base_visual_go='REQUIRES_ACTUAL_IMAGE_REVIEW',
                   whole_object_P1_visual_go='REQUIRES_SEPARATE_REVIEW; inherited stem clutter remains',
                   reconstructed_input='BLOCKED', H1_H2='NOT_TESTED')
    result = dict(verdict='VALID' if all(row['passed'] for row in checks.values()) else 'INVALID',
                  checks=checks, scientific_gates=science, evidence=evidence,
                  seconds=time.perf_counter() - start,
                  scope='Independent audit of one exposed GT-lamp base-density edit; no producer import or renderer call',
                  limitations=[
                      'Analytic masks and mesh share authored shape specification; not independent real reconstruction.',
                      'Four views and24 orbit frames are one exposed object, not independent object samples.',
                      'Stroke equality and thinning monotonicity are regression controls, not visual quality gates.',
                      'Hatch support is thresholded image coverage, not surface-area coverage or dark-tone fidelity.',
                      'Raw orbit image differences include camera motion, visibility and aliasing; no jitter or flicker claim.',
                      'Inherited17 hidden-profile observations and limited nine-ID temporal evidence remain unresolved.',
                  ])
    metrics['scientific_gates'] = science
    metrics['validation_verdict'] = result['verdict']
    write_json(unit / 'METRICS.json', metrics)
    write_json(unit / 'INDEPENDENT_VALIDATION.json', result)
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--unit', type=Path, default=DEFAULT_UNIT)
    parser.add_argument('--ffmpeg', default=DEFAULT_FFMPEG)
    args = parser.parse_args()
    if args.unit.resolve() != DEFAULT_UNIT.resolve():
        raise ValueError('this bounded validator writes only authorized unit_003')
    result = validate(args.unit, args.ffmpeg)
    print(json.dumps(native({'verdict': result['verdict'], 'checks': result['checks'],
                             'scientific_gates': result['scientific_gates']}), allow_nan=False))
    return 0 if result['verdict'] == 'VALID' else 1


if __name__ == '__main__':
    raise SystemExit(main())
