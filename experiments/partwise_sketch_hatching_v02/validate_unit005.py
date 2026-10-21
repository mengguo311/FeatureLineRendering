"""Independent image/mask audit of the frozen explicit-asset shade-width edit.

The producer and renderer are never imported. Analytic continuous geometry gives
the reference masks, while saved PNGs supply the primary local-edit measurement.
Path/config identity and cold replay are secondary software regression checks.
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
import copy
import json
from pathlib import Path
import sys
import time

import numpy as np
from scipy import ndimage

WORK = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(WORK))
from experiments.partwise_sketch_hatching import core
from experiments.partwise_sketch_hatching_v02.validate_unit003 import (
    INK_THRESHOLD, PARTS, SIZE, VIEWS, footprint, load_npz, native, read_render,
    rgb, sha, strokes, write_json,
)

DEFAULT_UNIT = Path('/mnt/hdd1/u00134/partwise_sketch_hatching_p1_v02/units/unit_005')
PREVIOUS = DEFAULT_UNIT.parent / 'unit_004'
THRESHOLDS = {
    'target_part': 1, 'target_inside_L1_min_exclusive': 10.,
    'far_other_fraction_max': .02, 'far_background_fraction_max': .02,
    'boundary_band_px': 2, 'hatch_support_ink_threshold': INK_THRESHOLD,
    'every_part_support_pixels_min_exclusive': 0, 'whole_shape_margin_px_min': 2,
    'no_edit_control_total_L1': 0., 'leakage_control_black_pixel_count': 16,
    'drift_control_horizontal_shift_px': 3,
}


def edit_regions(labels):
    target = labels == 1
    distance = ndimage.distance_transform_edt(~target)
    return {
        'inside': target,
        'boundary_band': (~target) & (distance <= 2),
        'far_other_parts': (labels > 0) & (~target) & (distance > 2),
        'far_background': (labels == 0) & (distance > 2),
    }


def edit_metrics(before, after, labels):
    change = np.abs(after - before)
    masks = edit_regions(labels)
    total = float(change.sum())
    masses = {name: float(change[mask].sum()) for name, mask in masks.items()}
    result = dict(total_delta=total, inside_delta=masses['inside'],
                  inside_mean_delta=float(change[masks['inside']].mean())
                  if masks['inside'].any() else 0.,
                  mask_pixels=int(masks['inside'].sum()),
                  nonzero_edit=masses['inside'] > 10., band_px=2,
                  outside_fraction=(total - masses['inside']) / max(total, 1e-15),
                  region_pixels={name: int(mask.sum()) for name, mask in masks.items()})
    for name, mass in masses.items():
        result[name + '_delta'] = mass
        result[name + '_fraction'] = mass / max(total, 1e-15)
    result['go'] = bool(result['nonzero_edit']
                        and result['far_other_parts_fraction'] <= .02
                        and result['far_background_fraction'] <= .02)
    return result


def whole_shape(labels, vertices, camera):
    yy, xx = np.nonzero(labels > 0)
    mask_margins = (dict(left=int(xx.min()), right=int(SIZE - 1 - xx.max()),
                         top=int(yy.min()), bottom=int(SIZE - 1 - yy.max()))
                    if len(xx) else dict(left=-1, right=-1, top=-1, bottom=-1))
    uv, depth = core.project(vertices, camera)
    projected_margins = dict(left=float(uv[:, 0].min()),
                             right=float(SIZE - 1 - uv[:, 0].max()),
                             top=float(uv[:, 1].min()),
                             bottom=float(SIZE - 1 - uv[:, 1].max()))
    go = (len(xx) > 0 and bool(np.all(depth > 0))
          and min(mask_margins.values()) >= 2
          and min(projected_margins.values()) >= 2)
    return dict(mask_margins_px=mask_margins,
                mesh_projection_margins_px=projected_margins,
                all_mesh_vertices_in_front=bool(np.all(depth > 0)), go=bool(go),
                scope='Continuous analytic foreground plus all saved mesh vertices; no cropped ROI')


def controls(before, after, labels):
    noedit = edit_metrics(before, before, labels)
    eligible = np.flatnonzero(edit_regions(labels)['far_other_parts'])
    if len(eligible) < 16:
        raise AssertionError('insufficient independent far-other pixels for frozen injection')
    chosen = eligible[np.argsort(-before.ravel()[eligible], kind='stable')[:16]]
    if np.any(before.ravel()[chosen] <= 0):
        raise AssertionError('frozen injection requires16 nonblack far-other pixels')
    # Gate sensitivity independently of the strength of the real width edit.
    # Injecting16 pixels into a strong target edit can dilute the fraction below
    # the2% threshold without indicating a broken leakage measurement.
    injected_baseline = before.copy()
    injected_baseline.ravel()[chosen] = 0.
    fault = edit_metrics(before, injected_baseline, labels)
    injected_edited = after.copy()
    injected_edited.ravel()[chosen] = 0.
    edited_fault = edit_metrics(before, injected_edited, labels)
    shifted = np.ones_like(before)
    shifted[:, 3:] = before[:, :-3]
    drift = dict(horizontal_shift_px=3, no_drift_L1=0.,
                 drifted_image_L1=float(np.abs(before - shifted).sum()),
                 scope='White-filled raster-shift sensitivity only; no correspondence/jitter claim')
    passed = (noedit['total_delta'] == 0 and not noedit['nonzero_edit']
              and not noedit['go'] and fault['far_other_parts_fraction'] > .02
              and np.isclose(fault['far_other_parts_fraction'], 1., atol=1e-12, rtol=0)
              and fault['inside_delta'] == 0 and drift['drifted_image_L1'] > 0)
    return dict(no_edit=noedit, injected_no_edit_far_other=fault,
                injected_edited_far_other_diagnostic=edited_fault,
                injected_flat_pixel_indices=chosen,
                injection_definition='16 brightest independent far-other baseline pixels; black; stable index tie-break',
                raster_drift=drift, passed=bool(passed))


def assert_strokes_equal(left, right, context):
    if set(left) != set(right):
        raise AssertionError(f'{context}: stroke IDs differ')
    for sid in sorted(left):
        old, new = left[sid], right[sid]
        if (old['part'] != new['part'] or old['ink'] != new['ink']
                or not np.array_equal(old['faces'], new['faces'])
                or not np.array_equal(old['bary'], new['bary'])):
            raise AssertionError(f'{context}: path/part/ink differs: {sid}')
    return len(left)


def read_asset(path):
    manifest = json.loads(path.read_text())
    if manifest['schema'] != 'partwise_asset_v1':
        raise AssertionError(f'wrong explicit asset schema: {path}')
    files = {}
    for key in ('mesh', 'strokes', 'config'):
        record = manifest[key]
        filename = Path(record['path'])
        if not filename.is_absolute():
            filename = path.parent / filename
        if sha(filename) != record['sha256']:
            raise AssertionError(f'explicit asset hash differs: {path}: {key}')
        files[key] = str(filename.resolve())
    return manifest, files


def audit_assets(unit):
    old_status = json.loads((PREVIOUS / 'STATUS.json').read_text())
    expected_metadata = {key: old_status[key]
                         for key in ('scientific_verdict', 'claim_status', 'blockers')}
    previous_strokes = strokes(PREVIOUS / 'inputs/selected.npz')
    previous_config = json.loads((PREVIOUS / 'CONFIG.json').read_text())
    previous_mesh = load_npz(PREVIOUS / 'inputs/lamp_mesh.npz')
    bundles, manifest_rows = {}, []
    for name in ('baseline', 'edited', 'cold_replay'):
        bundle = unit / 'outputs' / name
        manifest, files = read_asset(bundle / 'asset.json')
        for key, filename in files.items():
            expected_filename = bundle / (key + ('.json' if key == 'config' else '.npz'))
            if Path(filename) != expected_filename.resolve():
                raise AssertionError(f'{name}: saved asset must bind its own{key} file')
        metadata = manifest['verdict_metadata']
        for key, value in expected_metadata.items():
            if metadata.get(key) != value:
                raise AssertionError(f'{name}: inherited verdict field changed: {key}')
        if metadata['claim_status']['frozen_density_contract'] != 'NO_GO':
            raise AssertionError(f'{name}: inherited density NO_GO suppressed')
        if metadata['claim_status']['candidate_promotion'] != 'DIAGNOSTIC_PREVIEW_ONLY':
            raise AssertionError(f'{name}: preview silently promoted')
        if 'unit_004' not in str(metadata.get('source_unit', '')):
            raise AssertionError(f'{name}: wrong inherited source unit')
        config = json.loads((bundle / 'config.json').read_text())
        paths = strokes(bundle / 'strokes.npz')
        count = assert_strokes_equal(previous_strokes, paths, name)
        counts = {str(part): sum(row['part'] == part for row in paths.values()) for part in PARTS}
        if count != 418 or counts != {'1': 260, '2': 8, '3': 150}:
            raise AssertionError(f'{name}: wrong418-path diagnostic preview counts: {counts}')
        mesh = load_npz(bundle / 'mesh.npz')
        for key in ('vertices', 'faces', 'parts'):
            if not np.array_equal(mesh[key], previous_mesh[key]):
                raise AssertionError(f'{name}: immutable mesh differs: {key}')
        bundles[name] = dict(config=config, paths=paths, mesh=mesh)
        manifest_rows.append(dict(bundle=name, name=manifest['name'], files=files,
                                  stroke_count=count, counts_by_part=counts,
                                  verdict_metadata_retained=True,
                                  asset_sha256=sha(bundle / 'asset.json')))
    baseline, edited, replay = (bundles[name]['config']
                                for name in ('baseline', 'edited', 'cold_replay'))
    if baseline != previous_config:
        raise AssertionError('baseline config differs from explicit historical preview')
    expected = copy.deepcopy(baseline)
    if expected['widths_by_part']['1'] != 1.:
        raise AssertionError('baseline shade width is not frozen1.0px')
    expected['widths_by_part']['1'] = 1.5
    if edited != expected:
        raise AssertionError('edited config differs outside shade width1.0->1.5px')
    if replay != edited:
        raise AssertionError('cold replay config differs from edited saved config')
    return dict(bundles=manifest_rows, all418_paths_and_inks_exact=True,
                non_target_paths_and_inks_exact=158, non_target_config_exact=True,
                only_config_change='widths_by_part.1:1.0->1.5',
                inherited_unit004_density_contract='NO_GO',
                inherited_candidate_promotion='DIAGNOSTIC_PREVIEW_ONLY',
                no_path_regeneration_required=True,
                scope='Secondary explicit-input/identity regression, not a visual acceptance gate')


def validate(unit):
    start = time.perf_counter()
    checks, evidence, science = {}, {}, {}
    metrics = dict(stills=[], frozen_thresholds=THRESHOLDS,
                   metric_scope='Actual8-bit grayscale PNG L1; four exposed views of one authored GT object')

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
                raise AssertionError(f'frozen source/input SHA differs: {filename}')
            rows.append(dict(path=filename, sha256=actual))
        if not rows:
            raise AssertionError('source/input lock is empty')
        return dict(count=len(rows), files=rows)

    check('frozen_source_and_input_sha256', lock_check)
    check('explicit_assets_width_only_paths_config_and_retained_NO_GO', lambda: audit_assets(unit))
    baseline_dir = unit / 'outputs/baseline'
    edited_dir = unit / 'outputs/edited'
    replay_dir = unit / 'outputs/cold_replay'
    cfg = json.loads((baseline_dir / 'config.json').read_text())
    mesh = load_npz(baseline_dir / 'mesh.npz')
    reference_dir = unit / 'references'
    reference_dir.mkdir(exist_ok=True)

    for azimuth in VIEWS:
        def view_action(azimuth=azimuth):
            camera = core.camera(azimuth, 20, 4.5, SIZE, 600)
            depth, labels = core.analytic_reference(cfg['asset'], camera)
            masks = edit_regions(labels)
            reference_path = reference_dir / f'{azimuth:03}.npz'
            np.savez_compressed(reference_path, depth=depth, parts=labels, **masks)
            before, old, _ = read_render(baseline_dir / 'renders' / f'{azimuth:03}', camera)
            after, new, _ = read_render(edited_dir / 'renders' / f'{azimuth:03}', camera)
            replay, repeated, _ = read_render(replay_dir / 'renders' / f'{azimuth:03}', camera)
            old_footprint, new_footprint = footprint(old['hatch'], labels), footprint(new['hatch'], labels)
            all_parts = all(new_footprint[str(part)]['support_pixels'] > 0 for part in PARTS)
            edit = edit_metrics(before, after, labels)
            shape = whole_shape(labels, mesh['vertices'], camera)
            regression = {
                'contours_unchanged': np.array_equal(old['contours'], new['contours']),
                'rings_unchanged': np.array_equal(old['rings'], new['rings']),
                'depth_unchanged': np.array_equal(old['depth'], new['depth']),
                'producer_part_labels_unchanged': np.array_equal(old['parts'], new['parts']),
            }
            cold = dict(display_png_pixels_exact=bool(np.array_equal(after, replay)),
                        display_png_file_sha256_exact=sha(edited_dir / 'renders' / f'{azimuth:03}.png')
                        == sha(replay_dir / 'renders' / f'{azimuth:03}.png'),
                        saved_layers_exact={key: bool(np.array_equal(new[key], repeated[key]))
                                            for key in ('image', 'hatch', 'contours', 'rings', 'depth', 'parts')},
                        scope='Cold saved-config render replay; width edit retains paths and requires no regeneration')
            row = dict(azimuth=azimuth, edit=edit, baseline_footprint=old_footprint,
                       candidate_footprint=new_footprint, all_three_parts_nonempty=bool(all_parts),
                       whole_shape=shape, regression=regression, cold_replay=cold,
                       controls=controls(before, after, labels),
                       quantitative_go=bool(edit['go'] and all_parts and shape['go']),
                       reference_mask_path=str(reference_path), reference_mask_sha256=sha(reference_path))
            metrics['stills'].append(row)
            if not row['controls']['passed']:
                raise AssertionError('metric sensitivity control failed; raw row retained')
            if not all(regression.values()):
                raise AssertionError('nonhatch raster regression failed; raw row retained')
            if not (cold['display_png_pixels_exact'] and cold['display_png_file_sha256_exact']
                    and all(cold['saved_layers_exact'].values())):
                raise AssertionError('cold saved-config replay differs; raw row retained')
            return dict(azimuth=azimuth, analytic_mask_recomputed=True,
                        raw_reference_path=str(reference_path),
                        quantitative_go=row['quantitative_go'], controls_passed=True,
                        cold_display_png_exact=True)

        check(f'actual_images_masks_controls_and_cold_replay_{azimuth:03}', view_action)

    complete_views = len(metrics['stills']) == len(VIEWS)
    science.update(
        local_edit_go_four_stills=complete_views and all(row['edit']['go'] for row in metrics['stills']),
        all_parts_nonempty_four_stills=complete_views and all(row['all_three_parts_nonempty'] for row in metrics['stills']),
        whole_shape_visible_four_stills=complete_views and all(row['whole_shape']['go'] for row in metrics['stills']),
        quantitative_go_four_stills=complete_views and all(row['quantitative_go'] for row in metrics['stills']),
        metric_controls_go_four_stills=complete_views and all(row['controls']['passed'] for row in metrics['stills']),
        width_edit_visual_go='REQUIRES_ACTUAL_IMAGE_REVIEW',
        inherited_unit004_frozen_density_contract='NO_GO; retained, not reapplied to a shade-width edit',
        candidate_promotion='DIAGNOSTIC_PREVIEW_ONLY', reconstructed_input='BLOCKED',
        H1_H2='NOT_TESTED', temporal_visibility='NOT_NEWLY_TESTED')
    result = dict(verdict='VALID' if all(row['passed'] for row in checks.values()) else 'INVALID',
                  checks=checks, evidence=evidence, scientific_gates=science,
                  seconds=time.perf_counter() - start,
                  scope='Independent continuous analytic-mask and actual PNG audit; no producer or renderer imported',
                  limitations=[
                      'Analytic reference and mesh share an authored GT specification; no reconstructed lamp claim.',
                      'Four previously exposed views are one object, not independent object samples or blind tests.',
                      'Fixed2px boundary band is reported separately; it is not silently widened.',
                      'Hatch support is thresholded image coverage, not surface coverage or target-darkness fidelity.',
                      'Primitive/config equality is secondary; actual image response/isolation/nonempty/full shape are primary.',
                      'Cold width replay reproduces saved paths and render; no fresh path-regeneration claim.',
                      'Inherited density NO_GO,17 hidden-profile observations and limited temporal coverage remain unresolved.',
                  ])
    metrics['scientific_gates'] = science
    metrics['validation_verdict'] = result['verdict']
    write_json(unit / 'METRICS.json', metrics)
    write_json(unit / 'INDEPENDENT_VALIDATION.json', result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--unit', type=Path, default=DEFAULT_UNIT)
    args = parser.parse_args()
    if args.unit.resolve() != DEFAULT_UNIT.resolve():
        raise ValueError('bounded validator writes only authorized unit_005')
    result = validate(args.unit)
    print(json.dumps(native(dict(verdict=result['verdict'], checks=result['checks'],
                                 scientific_gates=result['scientific_gates'])), allow_nan=False))
    return 0 if result['verdict'] == 'VALID' else 1


if __name__ == '__main__':
    raise SystemExit(main())
