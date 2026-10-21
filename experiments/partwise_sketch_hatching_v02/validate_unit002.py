"""Independent file/media and image-metric validation for frozen unit_002.

No inherited producer is imported. Output paths are explicit. Contour metrics
use the independent continuous-lathe mask, not candidate surface parts. Their
scope is outer foreground coverage; internal hidden-edge correctness must also
be established by the separately preserved occlusion tests and visual review.
"""
import os

os.environ['CUDA_VISIBLE_DEVICES'] = ''
for _name in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS',
              'NUMEXPR_NUM_THREADS'):
    os.environ[_name] = '1'
os.environ['PYTHONDONTWRITEBYTECODE'] = '1'
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

DEFAULT_UNIT = Path('/mnt/hdd1/u00134/partwise_sketch_hatching_p1_v02/units/unit_002')
DEFAULT_PREVIOUS = DEFAULT_UNIT.parent / 'unit_001'
DEFAULT_FFMPEG = '/home/u00134/3dgs_line/partwise_sketch_hatching_p0p1_v01/.runtime_p0/imageio_ffmpeg/binaries/ffmpeg-linux-x86_64-v7.0.2'


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


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


def read_image(path):
    with Image.open(path) as image:
        pixels = np.asarray(image.convert('L'), dtype=np.uint8)
    if pixels.shape != (512, 512):
        raise AssertionError(f'wrong image shape: {path}: {pixels.shape}')
    return pixels.astype(np.float64) / 255.0


def edit_metrics(before, after, parts, target=1, band=2):
    """Independent implementation of the frozen image-L1 leakage definition."""
    change = np.abs(np.asarray(after, float) - np.asarray(before, float))
    if change.ndim == 3:
        change = change.sum(axis=2)
    target_mask = np.asarray(parts) == target
    distance_to_target = ndimage.distance_transform_edt(~target_mask)
    outside = ~target_mask
    near = outside & (distance_to_target <= band)
    other = outside & (distance_to_target > band) & (parts > 0)
    background = outside & (distance_to_target > band) & (parts == 0)
    total = float(change.sum())
    inside = float(change[target_mask].sum())
    denominator = max(total, 1e-15)
    return {
        'total_delta': total, 'inside_delta': inside,
        'nonzero_edit': inside > 10.0,
        'outside_fraction': float(change[outside].sum()) / denominator,
        'boundary_band_fraction': float(change[near].sum()) / denominator,
        'far_other_parts_fraction': float(change[other].sum()) / denominator,
        'far_background_fraction': float(change[background].sum()) / denominator,
        'inside_mean_delta': float(change[target_mask].mean()) if target_mask.any() else 0.0,
        'mask_pixels': int(target_mask.sum()), 'band_px': band,
    }


def contour_metrics(contours, parts):
    """Frozen .1-ink / 1.5px support metrics on independent outer boundary.

    Connected missing counts use 8-connectivity and are pixel counts, not exact
    arc lengths. Internal occlusion boundaries are deliberately not relabelled
    as foreground exterior. Outside ink farther than the fixed 2px band is
    disclosed separately; this is not a proof against internal hidden lines.
    """
    ink = np.asarray(contours, dtype=float)
    labels = np.asarray(parts)
    if ink.shape != labels.shape or ink.ndim != 2:
        raise ValueError('contour and independent part mask shapes differ')
    if not np.isfinite(ink).all() or ink.min() < -1e-12 or ink.max() > 1 + 1e-12:
        raise ValueError('contour ink must be finite and within [0,1]')
    foreground = labels > 0
    boundary = foreground & ~ndimage.binary_erosion(
        foreground, structure=np.ones((3, 3), dtype=bool), border_value=0)
    support = ink >= .1
    distances = ndimage.distance_transform_edt(~support) if support.any() else np.full(ink.shape, np.inf)
    report = {}
    for part in (1, 2, 3):
        selected = boundary & (labels == part)
        sample_distances = distances[selected]
        missing = selected & (distances > 1.5)
        components, count = ndimage.label(missing, structure=np.ones((3, 3), dtype=bool))
        sizes = np.bincount(components.ravel())[1:]
        coverage = float(np.mean(sample_distances <= 1.5)) if sample_distances.size else None
        p95 = (float(np.percentile(sample_distances, 95)) if support.any() else float('inf')) if sample_distances.size else None
        passed = bool(sample_distances.size and coverage >= .95 and p95 <= 1.5)
        report[str(part)] = {
            'boundary_pixels': int(selected.sum()),
            'supported_pixels': int(np.count_nonzero(sample_distances <= 1.5)),
            'coverage': coverage,
            'support_distance_p95_px': p95,
            'support_distance_max_px': float(sample_distances.max()) if sample_distances.size else None,
            'missing_pixels': int(missing.sum()),
            'missing_connected_components': int(count),
            'max_connected_missing_pixels': int(sizes.max()) if sizes.size else 0,
            'go': passed,
        }
    outside = ~foreground
    outside_distance = ndimage.distance_transform_edt(outside)
    far_outside = outside & (outside_distance > 2)
    total_ink = float(ink.sum())
    far_mass = float(ink[far_outside].sum())
    return {
        'per_part': report,
        'all_parts_go': all(row['go'] for row in report.values()),
        'contour_ink_mass': total_ink,
        'support_pixels': int(support.sum()),
        'far_external_ink_mass': far_mass,
        'far_external_ink_fraction': far_mass / max(total_ink, 1e-15),
        'far_external_support_pixels': int(np.count_nonzero(support & far_outside)),
        'frozen_definition': {
            'ink_threshold': .1, 'support_distance_px': 1.5,
            'coverage_min': .95, 'p95_max_px': 1.5,
            'external_band_px': 2, 'boundary_neighborhood': '3x3',
            'missing_connectivity': 8,
        },
        'limitations': [
            'Continuous authored lathe and mesh share asset specification; not independent reconstructed geometry.',
            'Outer-foreground support does not score internal occlusion edges or prove hidden-line correctness.',
            'Connected missing pixels are not continuous arc length or temporal correspondence.',
        ],
    }


def validate(unit, previous, ffmpeg):
    started = time.perf_counter()
    checks, evidence, scientific = {}, {}, {}

    def check(name, action):
        try:
            details = action()
            checks[name] = {'passed': True}
            evidence[name] = details
        except Exception as error:
            checks[name] = {'passed': False, 'error_type': type(error).__name__, 'message': str(error)}

    def locked_files():
        lock = json.loads((unit / 'SOURCE_LOCK.json').read_text())
        records = []
        for filename, expected in lock['files'].items():
            actual = sha(filename)
            if actual != expected:
                raise AssertionError(f'frozen hash differs: {filename}')
            records.append({'path': filename, 'sha256': actual})
        if not records:
            raise AssertionError('empty source/input lock')
        return {'count': len(records), 'files': records}

    check('frozen_source_and_input_sha256', locked_files)
    cfg = json.loads((WORK / 'docs/partwise_sketch_hatching/round_001/PROTOCOL.json').read_text())

    def images_and_metrics():
        views = []
        for azimuth in (30, 120, 210, 300):
            camera = core.camera(azimuth, 20, 4.5, 512, 600)
            ref_depth, ref_parts = core.analytic_reference(cfg['asset'], camera)
            ref_file = unit / 'stills' / f'reference_{azimuth:03}.npz'
            with np.load(ref_file, allow_pickle=False) as stored:
                if not np.array_equal(stored['parts'], ref_parts):
                    raise AssertionError(f'independent mask differs at azimuth {azimuth}')
                if not np.allclose(stored['depth'], ref_depth, atol=1e-12, rtol=0, equal_nan=True):
                    raise AssertionError(f'independent depth differs at azimuth {azimuth}')
            images, layers = {}, {}
            for mode in ('legacy', 'base', 'angle', 'width'):
                stem = unit / 'stills' / f'{mode}_{azimuth:03}'
                images[mode] = read_image(stem.with_suffix('.png'))
                with np.load(stem.with_suffix('.npz'), allow_pickle=False) as saved:
                    layers[mode] = {key: saved[key].copy() for key in saved.files}
                layer = layers[mode]
                if not all(key in layer for key in ('hatch', 'contours', 'rings')):
                    raise AssertionError(f'missing explicit rendering layer in {stem}')
                components = [layer['hatch'], layer['contours'], layer['rings']]
                # Max union precedes box downsampling, so max of the low-res
                # layers is not in general the low-res union. Verify the
                # mathematically valid bounds, including uint8 rounding.
                lower = np.maximum.reduce(components)
                upper = np.minimum(np.sum(components, axis=0), 1.0)
                observed_ink = 1.0 - images[mode]
                rounding = .5 / 255.0 + 1e-12
                if np.any(observed_ink < lower - rounding) or np.any(observed_ink > upper + rounding):
                    raise AssertionError(f'actual PNG violates rendered layer composition bounds: {stem}')
            # Regression checks bound this change; they are not application GO gates.
            for mode in ('base', 'angle', 'width'):
                with np.load(previous / 'stills' / f'{mode}_{azimuth:03}.npz', allow_pickle=False) as old:
                    if not np.array_equal(old['hatch'], layers[mode]['hatch']):
                        raise AssertionError(f'hatch rendering changed: {mode}, azimuth {azimuth}')
            if not np.array_equal(layers['legacy']['hatch'], layers['base']['hatch']):
                raise AssertionError(f'legacy/candidate hatch differs: azimuth {azimuth}')
            if not np.array_equal(layers['legacy']['rings'], layers['base']['rings']):
                raise AssertionError(f'legacy/candidate profile rings differ: azimuth {azimuth}')
            for mode in ('angle', 'width'):
                for layer_name in ('contours', 'rings'):
                    if not np.array_equal(layers['base'][layer_name], layers[mode][layer_name]):
                        raise AssertionError(f'geometry layer changes under edit: {mode}/{layer_name}')
            angle = edit_metrics(images['base'], images['angle'], ref_parts)
            width = edit_metrics(images['base'], images['width'], ref_parts)
            noedit = edit_metrics(images['base'], images['base'], ref_parts)
            injected = images['angle'].copy()
            yy, xx = np.where(ref_parts == 2)
            if not len(yy):
                raise AssertionError('stem mask empty; leakage injection unavailable')
            mid = len(yy) // 2
            cy, cx = int(yy[mid]), int(xx[mid])
            injected[max(0, cy - 4):cy + 4, max(0, cx - 4):cx + 4] = 0
            fault = edit_metrics(images['base'], injected, ref_parts)
            edit_go = all(m['inside_delta'] > 10 and m['far_other_parts_fraction'] <= .02
                          and m['far_background_fraction'] <= .02 for m in (angle, width))
            controls_go = noedit['total_delta'] == 0 and not noedit['nonzero_edit'] and fault['far_other_parts_fraction'] > angle['far_other_parts_fraction']
            if not controls_go:
                raise AssertionError(f'edit metric sensitivity controls fail at {azimuth}')
            legacy = contour_metrics(layers['legacy']['contours'], ref_parts)
            candidate = contour_metrics(layers['base']['contours'], ref_parts)
            contour_delta = layers['base']['contours'] - layers['legacy']['contours']
            views.append({
                'azimuth': azimuth, 'angle': angle, 'width': width,
                'no_edit': noedit, 'leakage_fault': fault, 'edit_go': edit_go,
                'legacy_contour': legacy, 'candidate_contour': candidate,
                'contour_change_L1': float(np.abs(contour_delta).sum()),
                'contour_new_ink_mass': float(np.maximum(contour_delta, 0).sum()),
                'contour_removed_ink_mass': float(np.maximum(-contour_delta, 0).sum()),
                'hatch_regression_exact': True, 'rings_regression_exact': True,
            })
        scientific['contour_coverage_go'] = all(v['candidate_contour']['all_parts_go'] for v in views)
        scientific['local_edit_go'] = all(v['edit_go'] for v in views)
        scientific['full_asset_visual_go'] = 'REQUIRES_SEPARATE_VISUAL_REVIEW'
        scientific['internal_hidden_contour_go'] = 'REQUIRES_SEPARATE_OCCLUSION_TESTS_AND_VISUAL_REVIEW'
        return {'views': views, 'independent_mask_source': 'unchanged core.analytic_reference; never candidate parts'}

    check('actual_stills_layers_masks_and_metrics', images_and_metrics)

    def decode_orbit():
        trajectory = json.loads((unit / 'TRAJECTORY_orbit.json').read_text())
        if len(trajectory) != 24:
            raise AssertionError('orbit trajectory does not have 24 frames')
        for i, row in enumerate(trajectory):
            if row['frame'] != i or row['azimuth'] != 15 * i or row['elevation'] != 20 or row['distance'] != 4.5:
                raise AssertionError(f'orbit camera differs from frozen trajectory: frame {i}')
        command = [ffmpeg, '-v', 'error', '-threads', '1', '-i', str(unit / 'videos/orbit.mkv'),
                   '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-threads', '1', '-']
        decoded = subprocess.run(command, capture_output=True, timeout=120)
        if decoded.returncode != 0:
            raise AssertionError(f'ffmpeg decode failed rc={decoded.returncode}: {decoded.stderr.decode(errors="replace")}')
        pixels = np.frombuffer(decoded.stdout, np.uint8)
        if pixels.size != 24 * 512 * 512 * 3:
            raise AssertionError(f'wrong decoded byte count: {pixels.size}')
        hashes = []
        for i, frame in enumerate(pixels.reshape(24, 512, 512, 3)):
            with Image.open(unit / 'frames/orbit' / f'{i:04}.png') as image:
                original = np.asarray(image.convert('RGB'))
            if not np.array_equal(frame, original):
                raise AssertionError(f'lossless decoded orbit frame differs: {i}')
            hashes.append(hashlib.sha256(frame.tobytes()).hexdigest())
        if len(set(hashes)) < 2:
            raise AssertionError('orbit contains fewer than two distinct actual frames')
        return {'command': command, 'returncode': decoded.returncode, 'decoded_frames': 24,
                'all_rgb_exact': True, 'distinct_frames': len(set(hashes)), 'frame_sha256': hashes}

    check('complete_orbit_video_decode', decode_orbit)
    result = {
        'verdict': 'VALID' if all(c['passed'] for c in checks.values()) else 'INVALID',
        'checks': checks, 'scientific_gates': scientific, 'evidence': evidence,
        'seconds': time.perf_counter() - started,
        'scope': 'Independent output/mask/media verification and frozen outer-contour metrics; not a producer seal, full P1, reconstructed-input, H1 or H2 claim.',
        'limitations': ['No renderer invocation or candidate rerun in this verifier.',
                        'Hatch/ring equalities are regression controls, not the primary application gate.',
                        'Actual full-object visual assessment and internal hidden contour tests remain separate evidence.'],
    }
    output = unit / 'INDEPENDENT_VALIDATION.json'
    output.write_text(json.dumps(native(result), indent=2, ensure_ascii=False, allow_nan=False) + '\n')
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--unit', type=Path, default=DEFAULT_UNIT)
    parser.add_argument('--previous', type=Path, default=DEFAULT_PREVIOUS)
    parser.add_argument('--ffmpeg', default=DEFAULT_FFMPEG)
    args = parser.parse_args()
    if args.unit.resolve() != DEFAULT_UNIT.resolve():
        raise ValueError('this bounded validator writes only the authorized unit_002')
    result = validate(args.unit, args.previous, args.ffmpeg)
    print(json.dumps(native({'verdict': result['verdict'], 'checks': result['checks'],
                             'scientific_gates': result['scientific_gates']}), allow_nan=False))
    return 0 if result['verdict'] == 'VALID' else 1


if __name__ == '__main__':
    raise SystemExit(main())
