"""Independent saved-output audit of one explicit shade-direction edit.

Only analytic reference, image and file helpers are imported. The CLI, path
walker and renderer are never imported or executed by this validator. Actual
PNG edit response, isolation, hatch support and full shape are the application
gates; path identity and cold determinism are secondary software contracts.
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
import hashlib
import json
from pathlib import Path
import sys
import time

import numpy as np

WORK = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(WORK))
from experiments.partwise_sketch_hatching import core
from experiments.partwise_sketch_hatching_v02.validate_unit003 import (
    INK_THRESHOLD, PARTS, SIZE, VIEWS, footprint, load_npz, native, read_render,
    sha, strokes, write_json,
)
from experiments.partwise_sketch_hatching_v02.validate_unit005 import (
    assert_strokes_equal, controls, edit_metrics, edit_regions, read_asset,
    whole_shape,
)

DEFAULT_UNIT = Path('/mnt/hdd1/u00134/partwise_sketch_hatching_p1_v02/units/unit_008')
ORIGIN = DEFAULT_UNIT.parent / 'unit_003'
BUNDLE_NAMES = ('baseline', 'edited', 'cold_regenerate', 'cold_replay')
THRESHOLDS = {
    'target_part': 1, 'target_inside_L1_min_exclusive': 10.,
    'far_other_fraction_max': .02, 'far_background_fraction_max': .02,
    'boundary_band_px': 2, 'hatch_support_ink_threshold': INK_THRESHOLD,
    'every_part_support_pixels_min_exclusive': 0, 'whole_shape_margin_px_min': 2,
    'no_edit_control_total_L1': 0., 'leakage_control_black_pixel_count': 16,
    'drift_control_horizontal_shift_px': 3,
}


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def arrays_equal(left, right, context):
    require(set(left) == set(right), f'{context}: saved NPZ keys differ')
    for key in sorted(left):
        require(left[key].dtype == right[key].dtype,
                f'{context}: dtype differs: {key}')
        require(np.array_equal(left[key], right[key]),
                f'{context}: saved array differs: {key}')
    return list(sorted(left))


def path_revision(path):
    """Independent digest for reporting path changes, not generator identity."""
    digest = hashlib.sha256()
    digest.update(np.ascontiguousarray(path['faces'], dtype='<i8').tobytes())
    digest.update(np.ascontiguousarray(path['bary'], dtype='<f8').tobytes())
    return digest.hexdigest()


def part_revision(paths):
    """Read the declared lineage digest format independently from saved arrays."""
    digest = hashlib.sha256()
    for sid in sorted(paths):
        path = paths[sid]
        digest.update(sid.encode())
        digest.update(np.asarray([path['part']], dtype=np.int64).tobytes())
        digest.update(np.asarray([path['ink']], dtype=np.float64).tobytes())
        digest.update(np.asarray(path['faces'], dtype=np.int32).tobytes())
        digest.update(np.asarray(path['bary'], dtype=np.float64).tobytes())
    return digest.hexdigest()


def anchor_audit(paths, mesh):
    samples = 0
    max_sum_error = 0.
    min_bary = 1.
    for sid, path in paths.items():
        faces, bary = path['faces'], path['bary']
        require(faces.ndim == 1 and len(faces) > 0, f'empty/invalid path: {sid}')
        require(bary.shape == (len(faces), 3), f'invalid bary shape: {sid}')
        require(np.isfinite(bary).all(), f'nonfinite bary: {sid}')
        require(np.all((faces >= 0) & (faces < len(mesh['faces']))),
                f'face index outside saved mesh: {sid}')
        require(np.all(mesh['parts'][faces] == path['part']),
                f'path crosses a GT part boundary: {sid}')
        error = float(np.max(np.abs(bary.sum(axis=1) - 1.)))
        minimum = float(bary.min())
        require(error <= 1e-10 and minimum >= -1e-12,
                f'illegal barycentric coordinates: {sid}')
        samples += len(faces)
        max_sum_error = max(max_sum_error, error)
        min_bary = min(min_bary, minimum)
    return dict(strokes=len(paths), anchor_samples=samples,
                max_barycentric_sum_error=max_sum_error, minimum_barycentric=min_bary,
                scope='Saved mesh attachment legality; not independent reconstruction accuracy')


def audit_bundle(unit, name):
    folder = unit / 'outputs' / name
    manifest, files = read_asset(folder / 'asset.json')
    for key, filename in files.items():
        suffix = '.json' if key == 'config' else '.npz'
        require(Path(filename) == (folder / (key + suffix)).resolve(),
                f'{name}: asset must bind its own {key} file')
    origin_status = json.loads((ORIGIN / 'STATUS.json').read_text())
    metadata = manifest['verdict_metadata']
    for key in ('scientific_verdict', 'claim_status', 'blockers'):
        require(metadata.get(key) == origin_status[key],
                f'{name}: inherited unit003 verdict field changed: {key}')
    require('unit_003' in str(metadata.get('source_unit', '')),
            f'{name}: wrong inherited source unit')
    paths = strokes(folder / 'strokes.npz')
    counts = {str(part): sum(row['part'] == part for row in paths.values())
              for part in PARTS}
    require(len(paths) == 458 and counts == {'1': 260, '2': 48, '3': 150},
            f'{name}: not the selected458 asset: {counts}')
    mesh = load_npz(folder / 'mesh.npz')
    original_mesh = load_npz(ORIGIN / 'inputs/lamp_mesh.npz')
    mesh_keys = arrays_equal(mesh, original_mesh, name + ' immutable mesh')
    attached = anchor_audit(paths, mesh)
    return dict(name=name, asset_sha256=sha(folder / 'asset.json'),
                files=files, counts_by_part=counts, inherited_verdict_retained=True,
                exact_mesh_keys=mesh_keys, anchors=attached)


def audit_direction_contract(unit):
    folders = {name: unit / 'outputs' / name for name in BUNDLE_NAMES}
    baseline = strokes(folders['baseline'] / 'strokes.npz')
    edited = strokes(folders['edited'] / 'strokes.npz')
    original = strokes(ORIGIN / 'inputs/selected.npz')
    assert_strokes_equal(original, baseline, 'baseline vs unit003 selected458')
    require(set(edited) == set(baseline), 'direction edit changed stroke IDs')
    retained = {sid: path for sid, path in baseline.items() if path['part'] != 1}
    edited_retained = {sid: path for sid, path in edited.items() if path['part'] != 1}
    require(assert_strokes_equal(retained, edited_retained, 'untouched parts') == 198,
            'non-target count is not198')
    revisions = []
    for sid in sorted(baseline):
        old, new = baseline[sid], edited[sid]
        require(old['part'] == new['part'] and old['ink'] == new['ink'],
                f'direction edit changed part or ink: {sid}')
        if old['part'] == 1:
            old_hash, new_hash = path_revision(old), path_revision(new)
            revisions.append(dict(id=sid, parent_path_sha256=old_hash,
                                  edited_path_sha256=new_hash, changed=old_hash != new_hash))
    changed = sum(row['changed'] for row in revisions)
    require(changed > 0, 'direction edit regenerated no changed target path')
    configs = {name: json.loads((folder / 'config.json').read_text())
               for name, folder in folders.items()}
    require(configs['baseline'] == json.loads((ORIGIN / 'CONFIG.json').read_text()),
            'baseline config differs from unit003')
    expected = copy.deepcopy(configs['baseline'])
    expected['direction_by_part'] = {'1': 15.0}
    require(configs['edited'] == expected,
            'edited config differs outside direction_by_part.1=15deg')
    cold = {}
    for name in ('cold_regenerate', 'cold_replay'):
        require(configs[name] == configs['edited'], f'{name}: config differs')
        cold[name] = arrays_equal(load_npz(folders['edited'] / 'strokes.npz'),
                                  load_npz(folders[name] / 'strokes.npz'),
                                  name + ' edited stroke arrays')
        require(assert_strokes_equal(edited, strokes(folders[name] / 'strokes.npz'), name) == 458,
                f'{name}: wrong count')
    return dict(unchanged_non_target_paths_ids_inks=198,
                retained_target_seed_ids=260, changed_target_paths=changed,
                target_revisions=revisions, cold_exact_array_keys=cold,
                only_config_change='add direction_by_part={"1":15.0}',
                scope='Secondary target-only edit/identity/determinism contract, not image quality')


def audit_seed_identity(unit):
    """Replay area-weighted seed sampling only; never call the path generator."""
    baseline = strokes(unit / 'outputs/baseline/strokes.npz')
    edited = strokes(unit / 'outputs/edited/strokes.npz')
    mesh = load_npz(unit / 'outputs/baseline/mesh.npz')
    triangles = mesh['vertices'][mesh['faces']]
    areas = np.linalg.norm(np.cross(triangles[:, 1] - triangles[:, 0],
                                    triangles[:, 2] - triangles[:, 0]), axis=1) * .5
    candidates = np.flatnonzero(mesh['parts'] == 1)
    probabilities = areas[candidates] / areas[candidates].sum()
    rng = np.random.default_rng(np.random.SeedSequence([1729, 1]))
    records = []
    for index in range(260):
        face = int(rng.choice(candidates, p=probabilities))
        q = rng.random(2)
        root = np.sqrt(q[0])
        bary = np.array([1 - root, root * (1 - q[1]), root * q[1]])
        sid = f'p1:seed{index:04d}:layer0'
        row = dict(id=sid, seed_face=face, seed_bary=bary)
        for name, paths in (('baseline', baseline), ('edited', edited)):
            require(sid in paths, f'{name}: missing seed ID {sid}')
            path = paths[sid]
            hits = (path['faces'] == face) & np.all(
                np.abs(path['bary'] - bary[None, :]) <= 1e-12, axis=1)
            require(bool(hits.any()), f'{name}: seed anchor missing or changed: {sid}')
            row[name + '_seed_anchor_index'] = int(np.flatnonzero(hits)[0])
        records.append(row)
    return dict(seed=1729, part=1, count=260, all_seed_anchors_preserved=True,
                records=records,
                scope='Independent sampling replay and saved-anchor membership; no path walker imported')


def recipe_file(recipe_path, record, name):
    require(isinstance(record, dict) and 'path' in record and 'sha256' in record,
            f'recipe missing explicit hash-bound {name}')
    path = Path(record['path'])
    if not path.is_absolute():
        path = recipe_path.parent / path
    path = path.resolve(strict=True)
    require(sha(path) == record['sha256'], f'recipe {name} SHA differs: {recipe_path}')
    return path


def audit_recipe(unit, recipe_path):
    recipe = json.loads(recipe_path.read_text())
    expected = dict(schema='shade_direction_recipe_v1', part=1, style='mixed',
                    seed=1729, count=260, length_world=.32, step_world=.015, angle_deg=15.)
    for key, value in expected.items():
        require(recipe.get(key) == value, f'recipe field differs: {key}: {recipe_path}')
    files = {name: recipe_file(recipe_path, recipe.get(name), name)
             for name in ('mesh', 'retained', 'config')}
    for filename in ('core.py', 'core_walk_v2.py'):
        expected_hash = sha(WORK / 'experiments/partwise_sketch_hatching' / filename)
        require(recipe['generator_sha256'].get(filename) == expected_hash,
                f'recipe generator hash differs: {filename}')
    baseline = strokes(unit / 'outputs/baseline/strokes.npz')
    retained = {sid: path for sid, path in baseline.items() if path['part'] != 1}
    count = assert_strokes_equal(retained, strokes(files['retained']), 'recipe retained paths')
    require(count == 198, 'recipe retained must contain exactly198 non-target paths')
    arrays_equal(load_npz(files['mesh']), load_npz(unit / 'outputs/baseline/mesh.npz'),
                 'recipe immutable mesh')
    require(json.loads(files['config'].read_text()) ==
            json.loads((unit / 'outputs/edited/config.json').read_text()),
            'recipe config differs from edited config')
    baseline_receipt = json.loads((unit / 'outputs/baseline/EDIT.json').read_text())
    parent_asset = Path(baseline_receipt['source'])
    parent_manifest = json.loads(parent_asset.read_text())
    require(recipe.get('baseline_manifest') == parent_manifest,
            'recipe baseline manifest differs from explicit original asset')
    edited = strokes(unit / 'outputs/edited/strokes.npz')
    expected_lineage = dict(
        parent_asset_sha256=sha(parent_asset),
        parent_strokes_sha256=parent_manifest['strokes']['sha256'],
        target_seed_identity='stroke_id',
        parent_target_revision=part_revision({sid: p for sid, p in baseline.items() if p['part'] == 1}),
        target_path_revision=part_revision({sid: p for sid, p in edited.items() if p['part'] == 1}),
        non_target_revision=part_revision(retained))
    require(recipe.get('lineage') == expected_lineage,
            'recipe lineage differs from independently read baseline/edited arrays')
    if recipe_path.parent.name in ('edited', 'cold_regenerate', 'cold_replay'):
        manifest = json.loads((recipe_path.parent / 'asset.json').read_text())
        require(manifest.get('path_lineage') == expected_lineage,
                'asset lineage differs from recipe')
        linked_recipe = recipe_file(recipe_path.parent / 'asset.json', manifest.get('recipe'), 'recipe')
        require(linked_recipe == recipe_path.resolve(), 'asset must bind its own recipe')
    return dict(path=str(recipe_path), sha256=sha(recipe_path), inputs=files,
                retained_paths=198, fixed_recipe=expected, lineage=recipe['lineage'])


def audit_receipts(unit):
    answer = {}
    expected_operations = dict(baseline='preview', edited='edit',
                               cold_regenerate='regenerate', cold_replay='replay')
    for name, operation in expected_operations.items():
        folder = unit / 'outputs' / name
        record = json.loads((folder / 'EDIT.json').read_text())
        require(record['operation'] == operation, f'{name}: wrong receipt operation')
        expected_regenerated = [1] if name in ('edited', 'cold_regenerate') else []
        require(record['regenerated_parts'] == expected_regenerated,
                f'{name}: wrong regenerated part record')
        generation = float(record['regeneration_seconds'])
        first = float(record['command_to_first_preview_seconds'])
        complete = float(record['command_to_all_previews_seconds'])
        require(np.isfinite([generation, first, complete]).all()
                and 0 <= generation < first <= complete,
                f'{name}: invalid command/generation timing')
        require(generation > 0 if expected_regenerated else generation == 0,
                f'{name}: regeneration timing does not match operation')
        require(record['saved_path_count'] == 458 and
                record['counts_by_part'] == {'1': 260, '2': 48, '3': 150},
                f'{name}: incorrect receipt path counts')
        require(sha(record['source']) == record['source_sha256'],
                f'{name}: receipt source SHA mismatch')
        metadata = json.loads((folder / 'asset.json').read_text())['verdict_metadata']
        require(record['inherited_verdict'] == metadata,
                f'{name}: receipt changed inherited verdict')
        if name == 'cold_regenerate':
            require(Path(record['source']).resolve() == (unit / 'cold_request/recipe.json').resolve(),
                    'cold regenerate receipt did not use the cache-free request')
        if name == 'cold_replay':
            require(Path(record['source']).resolve() == (unit / 'outputs/edited/asset.json').resolve(),
                    'cold replay receipt did not use the edited saved bundle')
        require(set(record['per_view_seconds']) == set(map(str, VIEWS)),
                f'{name}: receipt camera set differs')
        require(all(np.isfinite(float(value)) and float(value) > 0
                    for value in record['per_view_seconds'].values()),
                f'{name}: invalid per-view timings')
        answer[name] = dict(operation=operation, regenerated_parts=expected_regenerated,
                            regeneration_seconds=generation,
                            command_to_first_preview_seconds=first,
                            command_to_all_previews_seconds=complete,
                            per_view_seconds=record['per_view_seconds'])
    return dict(bundles=answer,
                timing_scope='One actual CPU invocation per operation; module entry through preview, not FPS or interactive benchmark')


def audit_cold_request(unit):
    folder = unit / 'cold_request'
    recipe_path = folder / 'recipe.json'
    record = audit_recipe(unit, recipe_path)
    allowed = {recipe_path.resolve(), *(Path(p).resolve() for p in record['inputs'].values())}
    require(all(path.is_relative_to(folder.resolve()) for path in allowed),
            'cold request inputs must be self-contained within cold_request')
    actual = {path.resolve() for path in folder.rglob('*') if path.is_file()}
    require(actual == allowed, 'cold request contains files beyond recipe/mesh/retained/config')
    return dict(**record, no_target_path_cache=True, files=list(sorted(map(str, actual))),
                scope='Cold generation input has198 retained paths and no saved target-path cache')


def validate(unit):
    unit = unit.resolve()
    require(unit == DEFAULT_UNIT.resolve(), 'validator may write only authorized unit_008')
    start = time.perf_counter()
    checks, evidence, science = {}, {}, {}
    metrics = dict(stills=[], frozen_thresholds=THRESHOLDS,
                   metric_scope='Actual8-bit grayscale PNG L1; four exposed views of one authored GT object')

    def check(name, action):
        try:
            evidence[name] = action()
            checks[name] = dict(passed=True)
        except Exception as error:
            checks[name] = dict(passed=False, error_type=type(error).__name__, message=str(error))

    def lock_check():
        lock = json.loads((unit / 'SOURCE_LOCK.json').read_text())
        rows = []
        for filename, expected in lock['files'].items():
            actual = sha(filename)
            require(actual == expected, f'frozen source/input SHA differs: {filename}')
            rows.append(dict(path=filename, sha256=actual))
        require(bool(rows), 'source/input lock is empty')
        return dict(count=len(rows), files=rows)

    check('frozen_source_and_input_sha256', lock_check)
    for name in BUNDLE_NAMES:
        check('explicit_bundle_' + name, lambda name=name: audit_bundle(unit, name))
    check('target_only_direction_config_paths_and_cold_arrays', lambda: audit_direction_contract(unit))
    check('independent_seed_identity', lambda: audit_seed_identity(unit))
    for name in ('edited', 'cold_regenerate', 'cold_replay'):
        check('explicit_recipe_' + name,
              lambda name=name: audit_recipe(unit, unit / 'outputs' / name / 'recipe.json'))
    check('cold_request_without_target_cache', lambda: audit_cold_request(unit))
    check('actual_operation_receipts_and_latency', lambda: audit_receipts(unit))

    reference_dir = unit / 'references'
    reference_dir.mkdir(exist_ok=True)
    for azimuth in VIEWS:
        def view_action(azimuth=azimuth):
            baseline_dir, edited_dir = (unit / 'outputs' / name for name in ('baseline', 'edited'))
            cfg = json.loads((baseline_dir / 'config.json').read_text())
            mesh = load_npz(baseline_dir / 'mesh.npz')
            camera = core.camera(azimuth, 20, 4.5, SIZE, 600)
            depth, labels = core.analytic_reference(cfg['asset'], camera)
            reference_path = reference_dir / f'{azimuth:03}.npz'
            np.savez_compressed(reference_path, depth=depth, parts=labels, **edit_regions(labels))
            before, old, _ = read_render(baseline_dir / 'renders' / f'{azimuth:03}', camera)
            after, new, _ = read_render(edited_dir / 'renders' / f'{azimuth:03}', camera)
            old_footprint = footprint(old['hatch'], labels)
            new_footprint = footprint(new['hatch'], labels)
            all_parts = all(old_footprint[str(part)]['support_pixels'] > 0
                            and new_footprint[str(part)]['support_pixels'] > 0 for part in PARTS)
            edit = edit_metrics(before, after, labels)
            shape = whole_shape(labels, mesh['vertices'], camera)
            regression = {key + '_unchanged': bool(np.array_equal(old[key], new[key]))
                          for key in ('contours', 'rings', 'depth', 'parts')}
            row = dict(azimuth=azimuth, edit=edit, baseline_footprint=old_footprint,
                       candidate_footprint=new_footprint, all_three_parts_nonempty=bool(all_parts),
                       whole_shape=shape, regression=regression, cold={},
                       controls=controls(before, after, labels),
                       quantitative_go=bool(edit['go'] and all_parts and shape['go']),
                       reference_mask_path=str(reference_path), reference_mask_sha256=sha(reference_path))
            metrics['stills'].append(row)
            for name in ('cold_regenerate', 'cold_replay'):
                directory = unit / 'outputs' / name
                replay, repeated, _ = read_render(directory / 'renders' / f'{azimuth:03}', camera)
                row['cold'][name] = dict(
                    display_png_pixels_exact=bool(np.array_equal(after, replay)),
                    display_png_file_sha256_exact=(sha(edited_dir / 'renders' / f'{azimuth:03}.png') ==
                                                   sha(directory / 'renders' / f'{azimuth:03}.png')),
                    saved_layers_exact={key: bool(np.array_equal(new[key], repeated[key]))
                                        for key in ('image', 'hatch', 'contours', 'rings', 'depth', 'parts')})
            require(row['controls']['passed'], 'metric sensitivity control failed; raw row retained')
            require(all(regression.values()), 'nonhatch raster regression failed; raw row retained')
            for name, cold in row['cold'].items():
                require(cold['display_png_pixels_exact'] and cold['display_png_file_sha256_exact']
                        and all(cold['saved_layers_exact'].values()),
                        f'{name} differs; raw row retained')
            return dict(azimuth=azimuth, analytic_mask_recomputed=True,
                        quantitative_go=row['quantitative_go'], controls_passed=True,
                        cold_regenerate_and_replay_png_exact=True)

        check(f'actual_images_masks_controls_and_cold_{azimuth:03}', view_action)

    complete_views = len(metrics['stills']) == len(VIEWS)
    science.update(
        local_edit_go_four_stills=complete_views and all(row['edit']['go'] for row in metrics['stills']),
        all_parts_nonempty_four_stills=complete_views and all(row['all_three_parts_nonempty'] for row in metrics['stills']),
        whole_shape_visible_four_stills=complete_views and all(row['whole_shape']['go'] for row in metrics['stills']),
        quantitative_go_four_stills=complete_views and all(row['quantitative_go'] for row in metrics['stills']),
        metric_controls_go_four_stills=complete_views and all(row['controls']['passed'] for row in metrics['stills']),
        direction_edit_visual_go='REQUIRES_ACTUAL_IMAGE_REVIEW',
        whole_object_visual='INHERITED_NO_GO; direction edit is not full visual cleanup',
        inherited_unit004_frozen_density_contract='NO_GO; selected458 unit003 is used, unit004 is not promoted',
        reconstructed_input='BLOCKED', H1_H2='NOT_TESTED', temporal_visibility='NOT_NEWLY_TESTED')
    result = dict(verdict='VALID' if all(row['passed'] for row in checks.values()) else 'INVALID',
                  checks=checks, evidence=evidence, scientific_gates=science,
                  seconds=time.perf_counter() - start,
                  scope='Independent saved-file/analytic-mask/actual-PNG audit; no producer, path walker or renderer imported',
                  limitations=[
                      'Analytic reference and mesh share an authored GT specification; no reconstructed lamp claim.',
                      'Four previously exposed views are one object, not independent object samples or blind tests.',
                      'Fixed2px boundary band is reported separately; it is never widened after results.',
                      'Hatch support is thresholded image coverage, not surface coverage or target-darkness fidelity.',
                      'Seed/primitive equality and cold reproduction are secondary; actual output gates are primary.',
                      'Independent seed replay validates identity; full target path generation is compared across saved cold outputs.',
                      'A static discrete edit provides no new temporal stability or edit-animation smoothness evidence.',
                      'Inherited density NO_GO,17 hidden-profile observations and temporal exclusions remain unresolved.',
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
    result = validate(args.unit)
    print(json.dumps(native(dict(verdict=result['verdict'], checks=result['checks'],
                                 scientific_gates=result['scientific_gates'])), allow_nan=False))
    return 0 if result['verdict'] == 'VALID' else 1


if __name__ == '__main__':
    raise SystemExit(main())
