"""Validation-only unit002 supplement; never renders or rewrites science data.

Recomputes contour support from saved layers and independent analytic masks,
checks the explicit frozen external-ink gate, verifies previous-unit immutable
files and part-local stroke identity. Validity and scientific gates are separate.
"""
import os
os.environ['CUDA_VISIBLE_DEVICES'] = ''
for _key in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS'):
    os.environ[_key] = '1'
os.environ['PYTHONDONTWRITEBYTECODE'] = '1'
os.sched_setaffinity(0, [0, 1])

import hashlib
import json
from pathlib import Path
import sys
import time

import numpy as np
from PIL import Image
from scipy import ndimage

WORK = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(WORK))
from experiments.partwise_sketch_hatching import core

UNIT = Path('/mnt/hdd1/u00134/partwise_sketch_hatching_p1_v02/units/unit_002')
PREVIOUS = UNIT.parent / 'unit_001'


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


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as handle:
        for block in iter(lambda: handle.read(1048576), b''):
            digest.update(block)
    return digest.hexdigest()


def independent_contour_metrics(ink, parts):
    """Second implementation of the frozen mask/support definitions.

    The foreground inner boundary is formed with explicit neighbor slices,
    independent of the producer's binary-erosion call. Distance transforms and
    8-connected component labelling use SciPy in both implementations.
    """
    foreground = parts > 0
    padded = np.pad(foreground, 1, constant_values=False)
    h, w = foreground.shape
    eroded = np.logical_and.reduce([padded[dy:dy + h, dx:dx + w]
                                    for dy in range(3) for dx in range(3)])
    boundary = foreground & ~eroded
    support = ink >= .1
    distance = ndimage.distance_transform_edt(~support) if support.any() else np.full(ink.shape, np.inf)
    per_part = {}
    for part in (1, 2, 3):
        eligible = boundary & (parts == part)
        values = distance[eligible]
        missing = eligible & (distance > 1.5)
        labelled, count = ndimage.label(missing, structure=np.ones((3, 3), bool))
        counts = np.bincount(labelled.ravel())[1:]
        coverage = float(np.count_nonzero(values <= 1.5) / values.size) if values.size else None
        p95 = (float(np.percentile(values, 95)) if support.any() else float('inf')) if values.size else None
        per_part[str(part)] = {
            'boundary_pixels': int(values.size),
            'supported_pixels': int(np.count_nonzero(values <= 1.5)),
            'coverage': coverage, 'support_distance_p95_px': p95,
            'support_distance_max_px': float(values.max()) if values.size else None,
            'missing_pixels': int(missing.sum()),
            'missing_connected_components': int(count),
            'max_connected_missing_pixels': int(counts.max()) if counts.size else 0,
            'go': bool(values.size and coverage >= .95 and p95 <= 1.5),
        }
    external = ~foreground
    far = external & (ndimage.distance_transform_edt(external) > 2)
    mass = float(ink.sum())
    far_mass = float(ink[far].sum())
    return {
        'per_part': per_part,
        'all_parts_go': all(v['go'] for v in per_part.values()),
        'contour_ink_mass': mass, 'support_pixels': int(support.sum()),
        'far_external_ink_mass': far_mass,
        'far_external_ink_fraction': far_mass / max(mass, 1e-15),
        'far_external_support_pixels': int(np.count_nonzero(far & support)),
    }


def compare_metrics(recomputed, stored, path=''):
    errors = []
    for key, expected in native(recomputed).items():
        label = f'{path}.{key}' if path else key
        if key not in stored:
            errors.append({'field': label, 'reason': 'missing_stored_field'})
            continue
        actual = stored[key]
        if isinstance(expected, dict):
            errors += compare_metrics(expected, actual, label)
        elif isinstance(expected, float):
            if actual is None or not np.isfinite(actual) or abs(actual - expected) > 1e-10:
                errors.append({'field': label, 'stored': actual, 'recomputed': expected})
        elif actual != expected:
            errors.append({'field': label, 'stored': actual, 'recomputed': expected})
    return errors


def check_layers(stem):
    with np.load(stem.with_suffix('.npz'), allow_pickle=False) as saved:
        layers = {key: saved[key].copy() for key in saved.files}
    for key in ('image', 'hatch', 'contours', 'rings'):
        values = layers[key]
        if values.shape != (512, 512) or not np.isfinite(values).all():
            raise AssertionError(f'invalid {key} shape/nonfinite values: {stem}')
        if values.min() < -1e-12 or values.max() > 1 + 1e-12:
            raise AssertionError(f'out-of-range {key}: {stem}')
    with Image.open(stem.with_suffix('.png')) as image:
        pixels = np.asarray(image.convert('L'))
    expected = np.rint(np.clip(layers['image'], 0, 1) * 255).astype(np.uint8)
    if not np.array_equal(pixels, expected):
        raise AssertionError(f'PNG does not equal quantized saved image: {stem}')
    components = [layers[k] for k in ('hatch', 'contours', 'rings')]
    actual = 1 - pixels / 255.0
    lower = np.maximum.reduce(components)
    upper = np.minimum(np.sum(components, axis=0), 1.0)
    allowance = .5 / 255 + 1e-12
    if np.any(actual < lower - allowance) or np.any(actual > upper + allowance):
        raise AssertionError(f'PNG outside valid premultisample union bounds: {stem}')
    return layers


def verify_old_seal():
    seal = json.loads((PREVIOUS / 'SEAL.json').read_text())
    manifest_path = PREVIOUS / 'SHA256_MANIFEST.json'
    if sha(manifest_path) != seal['manifest_sha256']:
        raise AssertionError('unit001 manifest SHA does not match historical seal')
    manifest = json.loads(manifest_path.read_text())
    checked, skipped, errors = [], [], []
    for row in manifest['files']:
        if row['root'] != 'unit':
            skipped.append(row['path'])
            continue
        path = (PREVIOUS / row['path']).resolve()
        if not path.is_relative_to(PREVIOUS.resolve()):
            errors.append({'path': str(path), 'reason': 'escaped historical unit root'})
            continue
        if not path.is_file():
            errors.append({'path': str(path), 'reason': 'missing'})
            continue
        actual = sha(path)
        if actual != row['sha256'] or path.stat().st_size != row['bytes']:
            errors.append({'path': str(path), 'expected_sha256': row['sha256'], 'actual_sha256': actual})
        checked.append(row['path'])
    return {
        'valid': not errors, 'manifest_sha256': seal['manifest_sha256'],
        'unit_files_checked': len(checked), 'errors': errors,
        'source_snapshot_files_checked': sum(p.startswith('source_snapshot/') for p in checked),
        'skipped_worktree_files': skipped,
        'skip_reason': 'Current worktree renderer is intentionally changed in unit002. Historical unit001 source_snapshot files remain immutable and are checked above.',
    }


def load_strokes(path):
    with np.load(path, allow_pickle=False) as data:
        result = {}
        for i, sid in enumerate(data['ids']):
            start, end = map(int, data['offsets'][i:i + 2])
            sid = str(sid)
            if sid in result:
                raise AssertionError(f'duplicate stroke ID: {sid}')
            result[sid] = {'part': int(data['parts'][i]), 'faces': data['faces'][start:end].copy(),
                           'bary': data['bary'][start:end].copy(), 'ink': float(data['inks'][i])}
    return result


def verify_edit_paths():
    before = load_strokes(PREVIOUS / 'inputs/mixed.npz')
    after = load_strokes(PREVIOUS / 'inputs/angle_edited.npz')
    if set(before) != set(after):
        raise AssertionError('baseline/edit stroke ID sets differ')
    wrong, target_changed, non_target = [], 0, 0
    for sid, row in before.items():
        other = after[sid]
        geometry_equal = np.array_equal(row['faces'], other['faces']) and np.array_equal(row['bary'], other['bary'])
        metadata_equal = row['part'] == other['part'] and row['ink'] == other['ink']
        if row['part'] != 1:
            non_target += 1
            if not geometry_equal or not metadata_equal:
                wrong.append(sid)
        elif not geometry_equal:
            target_changed += 1
    return {'valid': not wrong and target_changed > 0,
            'stroke_count': len(before), 'non_target_strokes': non_target,
            'non_target_changed_ids': wrong, 'target_geometry_changed_ids_count': target_changed,
            'definition': 'Exact persistent ID, part, faces, barycentric coordinates and ink for parts2/3; shade angle edit must actually change target geometry.'}


def verify_contour_outputs():
    cfg = json.loads((WORK / 'docs/partwise_sketch_hatching/round_001/PROTOCOL.json').read_text())
    stills = json.loads((UNIT / 'CONTOUR_STILLS.json').read_text())
    orbit = json.loads((UNIT / 'TRAJECTORY_orbit.json').read_text())
    if len(stills) != 4 or [v['azimuth'] for v in stills] != [30, 120, 210, 300]:
        raise AssertionError('stills list differs from frozen four views')
    if len(orbit) != 24:
        raise AssertionError('orbit must contain exactly24 frames')
    rows, metric_errors = [], []
    for kind, collection in (('still', stills), ('orbit', orbit)):
        for i, row in enumerate(collection):
            azimuth = row['azimuth']
            if kind == 'orbit' and (row['frame'] != i or azimuth != 15 * i or row['elevation'] != 20 or row['distance'] != 4.5):
                raise AssertionError(f'orbit trajectory mismatch: frame{i}')
            camera = core.camera(azimuth, 20, 4.5, 512, 600)
            depth, parts = core.analytic_reference(cfg['asset'], camera)
            folder = UNIT / ('stills' if kind == 'still' else 'frames/orbit')
            ref = folder / (f'reference_{azimuth:03}.npz' if kind == 'still' else f'reference_{i:04}.npz')
            with np.load(ref, allow_pickle=False) as saved:
                if not np.array_equal(saved['parts'], parts) or not np.allclose(saved['depth'], depth, rtol=0, atol=1e-12, equal_nan=True):
                    raise AssertionError(f'saved analytic reference differs: {ref}')
            stem = folder / (f'base_{azimuth:03}' if kind == 'still' else f'{i:04}')
            layers = check_layers(stem)
            metrics = independent_contour_metrics(layers['contours'], parts)
            errors = compare_metrics(metrics, row['candidate'], f'{kind}[{i}].candidate')
            metric_errors += errors
            record = {'kind': kind, 'index': i, 'azimuth': azimuth,
                      'candidate': metrics, 'stored_candidate_matches': not errors,
                      'coverage_gate': metrics['all_parts_go'],
                      'far_external_support_gate': metrics['far_external_support_pixels'] == 0,
                      'full_frozen_contour_gate': metrics['all_parts_go'] and metrics['far_external_support_pixels'] == 0}
            if kind == 'still':
                legacy = check_layers(folder / f'legacy_{azimuth:03}')
                legacy_metrics = independent_contour_metrics(legacy['contours'], parts)
                legacy_errors = compare_metrics(legacy_metrics, row['legacy'], f'{kind}[{i}].legacy')
                metric_errors += legacy_errors
                record['legacy'] = legacy_metrics
                record['stored_legacy_matches'] = not legacy_errors
            rows.append(record)
    return {
        'valid': not metric_errors, 'metric_mismatches': metric_errors, 'observations': rows,
        'still_views_recomputed': 4, 'orbit_frames_recomputed': 24,
        'all_coverage_gates': all(r['coverage_gate'] for r in rows),
        'all_far_external_support_gates': all(r['far_external_support_gate'] for r in rows),
        'all_frozen_contour_gates': all(r['full_frozen_contour_gate'] for r in rows),
        'stored_metric_policy': 'Mismatches invalidate this audit; all original stored outputs are preserved, never corrected in place.',
        'metric_implementation': 'Second boundary/support calculation; shared SciPy EDT/component primitives and unchanged continuous-lathe reference implementation disclosed.',
        'limits': ['Outer-foreground contour only; internal hidden-edge test and visual review remain separate.',
                   'Legacy orbit metrics are not recomputed because legacy orbit contour layers were not retained. Candidate metrics are recomputed for all24 frames.',
                   'No rendered sequence regeneration or performance claim.'],
    }


def main():
    started = time.perf_counter()
    checks, details = {}, {}
    for name, function in (('unit001_sealed_unit_files', verify_old_seal),
                           ('part_local_edit_paths', verify_edit_paths),
                           ('all_still_and_orbit_contour_metrics', verify_contour_outputs)):
        try:
            value = function()
            details[name] = value
            checks[name] = {'valid': bool(value['valid'])}
        except Exception as error:
            checks[name] = {'valid': False, 'error_type': type(error).__name__, 'message': str(error)}
    contour = details.get('all_still_and_orbit_contour_metrics', {})
    result = {
        'verdict': 'VALID' if all(v['valid'] for v in checks.values()) else 'INVALID',
        'checks': checks, 'details': details,
        'scientific_gates': {
            'all_coverage_gates': contour.get('all_coverage_gates'),
            'all_far_external_support_gates': contour.get('all_far_external_support_gates'),
            'all_frozen_contour_gates': contour.get('all_frozen_contour_gates'),
            'whole_object_visual': 'SEPARATE_REVIEW', 'internal_hidden_contours': 'SEPARATE_TESTS_AND_REVIEW',
        },
        'seconds': time.perf_counter() - started,
        'role': 'Validation-only supplement; no candidate, input, threshold or historical result changes.',
    }
    (UNIT / 'AUDIT_UNIT002.json').write_text(json.dumps(native(result), ensure_ascii=False, indent=2, allow_nan=False) + '\n')
    print(json.dumps(native({'verdict': result['verdict'], 'checks': checks,
                            'scientific_gates': result['scientific_gates']}), allow_nan=False))
    return 0 if result['verdict'] == 'VALID' else 1


if __name__ == '__main__':
    raise SystemExit(main())
