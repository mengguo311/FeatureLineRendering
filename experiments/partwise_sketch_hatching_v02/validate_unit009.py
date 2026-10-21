"""Independent saved-output audit for one frozen stem density edit.

No density selector, CLI, path walker, or renderer is imported or executed.
Actual PNG edit/isolation and analytic axial-bin hatch support are application
gates; file identity and cold reproduction are secondary software contracts.
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
    PARTS, SIZE, VIEWS, footprint, load_npz, native, read_render, sha, strokes,
    write_json,
)
from experiments.partwise_sketch_hatching_v02.validate_unit005 import (
    assert_strokes_equal, read_asset, whole_shape,
)
from experiments.partwise_sketch_hatching_v02.validate_unit008 import (
    anchor_audit, arrays_equal, part_revision, recipe_file, require,
    retained_bytes_equal,
)

DEFAULT_UNIT = Path('/mnt/hdd1/u00134/partwise_sketch_hatching_p1_v02/units/unit_009')
ORIGIN = DEFAULT_UNIT.parent / 'unit_008/outputs/baseline'
BUNDLES = ('baseline', 'edited', 'cold_reselect', 'cold_replay')
EDGES = np.array([.20, .45, .70, .95, 1.20], dtype=float)
THRESHOLDS = dict(
    target_part=2, target_inside_L1_min_exclusive=10.,
    far_other_fraction_max=.02, far_background_fraction_max=.02,
    boundary_band_px=2, hatch_support_ink_threshold_exclusive=.1,
    axial_bin_edges_world_y=EDGES, per_bin_visible_pixels_min=1,
    per_bin_support_pixels_min=3, per_bin_support_fraction_min=.01,
    every_part_support_pixels_min_exclusive=0, whole_shape_margin_px_min=2,
    leakage_control_black_pixel_count=16, drift_control_horizontal_shift_px=3,
)


def edit_regions(labels):
    target = labels == 2
    distance = ndimage.distance_transform_edt(~target)
    return dict(inside=target, boundary_band=(~target) & (distance <= 2),
                far_other_parts=(labels > 0) & (~target) & (distance > 2),
                far_background=(labels == 0) & (distance > 2))


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
                  outside_fraction=(total-masses['inside']) / max(total, 1e-15),
                  region_pixels={name: int(mask.sum()) for name, mask in masks.items()})
    for name, mass in masses.items():
        result[name + '_delta'] = mass
        result[name + '_fraction'] = mass / max(total, 1e-15)
    result['go'] = bool(result['nonzero_edit']
                        and result['far_other_parts_fraction'] <= .02
                        and result['far_background_fraction'] <= .02)
    return result


def axial_masks(depth, labels, camera):
    """Fixed world-y intervals from analytic rays, independent of hatch output."""
    yy, xx = np.indices(labels.shape)
    finite_depth = np.where(np.isfinite(depth), depth, 0.)
    points = core.backproject(np.stack((xx, yy), axis=-1), finite_depth, camera)
    world_y = points[..., 1]
    stem = labels == 2
    bins = []
    for index, (lo, hi) in enumerate(zip(EDGES[:-1], EDGES[1:])):
        upper = world_y <= hi if index == len(EDGES)-2 else world_y < hi
        bins.append(stem & (world_y >= lo) & upper)
    return world_y, bins


def axial_coverage(hatch, labels, world_y, bins):
    rows = []
    for index, mask in enumerate(bins):
        visible = int(mask.sum())
        support = int(np.count_nonzero(mask & (hatch > .1)))
        ratio = support / max(visible, 1)
        rows.append(dict(index=index, y_low=float(EDGES[index]),
                         y_high=float(EDGES[index+1]),
                         upper_endpoint_included=index == len(bins)-1,
                         eligible_pixels=visible, support_pixels=support,
                         support_fraction=ratio, hatch_ink_mass=float(hatch[mask].sum()),
                         go=bool(visible >= 1 and support >= 3 and ratio >= .01)))
    stem = labels == 2
    included = np.logical_or.reduce(bins)
    excluded = stem & ~included
    total = int(stem.sum())
    return dict(bins=rows, go=all(row['go'] for row in rows),
                total_analytic_visible_stem_pixels=total,
                included_visible_stem_pixels=int(included.sum()),
                excluded_visible_stem_pixels=int(excluded.sum()),
                excluded_visible_stem_fraction=float(excluded.sum()) / max(total, 1),
                excluded_below_pixels=int(np.count_nonzero(stem & (world_y < EDGES[0]))),
                excluded_above_pixels=int(np.count_nonzero(stem & (world_y > EDGES[-1]))),
                scope='Four fixed world-y bins; analytic visible pixels only; no boundary erosion; no all-stem coverage claim')


def controls(before, after, labels, world_y, bins):
    noedit = edit_metrics(before, before, labels)
    eligible = np.flatnonzero(edit_regions(labels)['far_other_parts'])
    require(len(eligible) >= 16, 'insufficient independent far-other pixels')
    chosen = eligible[np.argsort(-before.ravel()[eligible], kind='stable')[:16]]
    require(np.all(before.ravel()[chosen] > 0), 'injection needs16 nonblack pixels')
    injected = before.copy()
    injected.ravel()[chosen] = 0.
    fault = edit_metrics(before, injected, labels)
    edited = after.copy()
    edited.ravel()[chosen] = 0.
    edited_fault = edit_metrics(before, edited, labels)
    shifted = np.ones_like(before)
    shifted[:, 3:] = before[:, :-3]
    drift = float(np.abs(before-shifted).sum())
    empty = axial_coverage(np.zeros_like(before), labels, world_y, bins)
    passed = (noedit['total_delta'] == 0 and not noedit['go']
              and fault['far_other_parts_fraction'] > .02
              and np.isclose(fault['far_other_parts_fraction'], 1., atol=1e-12, rtol=0)
              and fault['inside_delta'] == 0 and drift > 0
              and not empty['go'] and all(not row['go'] and row['support_pixels'] == 0
                                           for row in empty['bins']))
    return dict(no_edit=noedit, injected_no_edit_far_other=fault,
                injected_edited_far_other_diagnostic=edited_fault,
                injected_flat_pixel_indices=chosen,
                injection_definition='16 brightest far-other baseline pixels, black; stable index tie break',
                raster_drift=dict(horizontal_shift_px=3, no_drift_L1=0.,
                                  drifted_image_L1=drift,
                                  scope='Raster metric sensitivity, not temporal stability'),
                zero_hatch_coverage=empty, passed=bool(passed))


def audit_bundle(unit, name):
    folder = unit / 'outputs' / name
    manifest, files = read_asset(folder/'asset.json')
    original_manifest = json.loads((ORIGIN/'asset.json').read_text())
    require(manifest['verdict_metadata'] == original_manifest['verdict_metadata'],
            f'{name}: inherited verdict metadata changed')
    for key, filename in files.items():
        suffix = '.json' if key == 'config' else '.npz'
        require(Path(filename) == (folder/(key+suffix)).resolve(),
                f'{name}: asset must bind own {key}')
    paths = strokes(folder/'strokes.npz')
    count = {'1': 260, '2': 48 if name == 'baseline' else 24, '3': 150}
    actual = {str(part): sum(row['part'] == part for row in paths.values()) for part in PARTS}
    require(actual == count and len(paths) == sum(count.values()),
            f'{name}: unexpected counts: {actual}')
    mesh = load_npz(folder/'mesh.npz')
    mesh_keys = arrays_equal(mesh, load_npz(ORIGIN/'mesh.npz'), name+' immutable mesh')
    return dict(name=name, asset_sha256=sha(folder/'asset.json'), files=files,
                counts_by_part=actual, exact_mesh_keys=mesh_keys,
                inherited_verdict_retained=True, anchors=anchor_audit(paths, mesh))


def independent_seed_order(unit):
    baseline = strokes(unit/'outputs/baseline/strokes.npz')
    mesh = load_npz(unit/'outputs/baseline/mesh.npz')
    tri = mesh['vertices'][mesh['faces']]
    area = .5*np.linalg.norm(np.cross(tri[:, 1]-tri[:, 0], tri[:, 2]-tri[:, 0]), axis=1)
    candidates = np.flatnonzero(mesh['parts'] == 2)
    probabilities = area[candidates] / area[candidates].sum()
    rng = np.random.default_rng(np.random.SeedSequence([1729, 2]))
    positions, seed_records = {}, []
    for index in range(48):
        face = int(rng.choice(candidates, p=probabilities))
        q = rng.random(2)
        root = np.sqrt(q[0])
        bary = np.array([1-root, root*(1-q[1]), root*q[1]])
        sid = f'p2:seed{index:04d}:layer0'
        require(sid in baseline, f'original stem ID missing: {sid}')
        path = baseline[sid]
        hits = (path['faces'] == face) & np.all(np.abs(path['bary']-bary) <= 1e-12, axis=1)
        require(bool(hits.any()), f'replayed seed absent from original path: {sid}')
        positions[sid] = bary @ tri[face]
        seed_records.append(dict(id=sid, face=face, bary=bary, point=positions[sid],
                                 original_anchor_index=int(np.flatnonzero(hits)[0])))
    # Recompute distances to all selected seeds at each step, separately from
    # the producer's incremental nearest-distance update.
    names = sorted(positions)
    order = [names[0]]
    remaining = names[1:]
    while remaining:
        selected_points = np.array([positions[sid] for sid in order])
        distances = {sid: float(np.min(np.sum((selected_points-positions[sid])**2, axis=1)))
                     for sid in remaining}
        chosen = min(remaining, key=lambda sid: (-distances[sid], sid))
        order.append(chosen)
        remaining.remove(chosen)
    return dict(ordered_ids=order, selected_ids=sorted(order[:24]),
                seed_records=seed_records, count=48, keep=24,
                method='Independent area sampler plus all-selected-seed distance recomputation; lexical ties')


def audit_density_contract(unit, independent):
    baseline_file = unit/'outputs/baseline/strokes.npz'
    baseline = strokes(baseline_file)
    edited_file = unit/'outputs/edited/strokes.npz'
    edited = strokes(edited_file)
    assert_strokes_equal(strokes(ORIGIN/'strokes.npz'), baseline, 'original selected458 baseline')
    target = set(independent['selected_ids'])
    retained = {sid for sid, row in baseline.items() if row['part'] != 2}
    require(set(edited) == retained | target, 'edited IDs differ from independent prefix24')
    require(len(retained) == 410, 'non-target count must be410')
    byte_check = retained_bytes_equal(baseline_file, edited_file, edited)
    configs = {name: json.loads((unit/'outputs'/name/'config.json').read_text()) for name in BUNDLES}
    require(configs['baseline'] == json.loads((ORIGIN/'config.json').read_text()),
            'baseline config differs from unit008 baseline')
    expected = copy.deepcopy(configs['baseline'])
    expected['density_by_part'] = {'2': .5}
    require(configs['edited'] == expected, 'config changed outside density_by_part.2')
    cold = {}
    for name in ('cold_reselect', 'cold_replay'):
        require(configs[name] == expected, f'{name}: config differs')
        cold[name] = arrays_equal(load_npz(edited_file),
                                  load_npz(unit/'outputs'/name/'strokes.npz'), name+' selected arrays')
    return dict(unchanged_non_target_paths=410, retained_stem_paths=24, removed_stem_paths=24,
                independent_selected_ids=sorted(target), retained_per_field_bytes=byte_check,
                cold_exact_array_keys=cold, only_config_change='add density_by_part={"2":0.5}',
                scope='Secondary selection/identity contract; no path regeneration or spacing guarantee')


def audit_recipe(unit, recipe_path, independent):
    recipe = json.loads(recipe_path.read_text())
    for key, expected in dict(schema='stem_density_recipe_v1', part=2,
                               density=.5, original_count=48, selected_count=24).items():
        require(recipe.get(key) == expected, f'recipe field differs: {key}')
    require(recipe['selector_sha256'] == sha(WORK/'experiments/partwise_sketch_hatching_v02/density_cli.py'),
            'recipe selector SHA differs from frozen implementation')
    require(recipe['numpy_version'] == np.__version__, 'recipe NumPy version differs')
    files = {name: recipe_file(recipe_path, recipe.get(name), name)
             for name in ('mesh', 'source_strokes', 'config')}
    arrays_equal(load_npz(files['mesh']), load_npz(ORIGIN/'mesh.npz'), 'recipe mesh')
    assert_strokes_equal(strokes(files['source_strokes']), strokes(ORIGIN/'strokes.npz'),
                         'recipe source458')
    require(json.loads(files['config'].read_text()) ==
            json.loads((unit/'outputs/edited/config.json').read_text()), 'recipe config differs')
    require(recipe['selection']['ordered_stem_ids'] == independent['ordered_ids'],
            'recipe order differs from independent farthest seed order')
    require(sorted(recipe['selection']['selected_stem_ids']) == independent['selected_ids'],
            'recipe selected IDs differ')
    require(recipe['selection']['available_stem_paths'] == 48
            and recipe['selection']['selected_stem_paths'] == 24
            and recipe['selection']['density'] == .5, 'recipe selection counts/density differ')
    positions = recipe['selection']['seed_positions']
    require(set(positions) == set(independent['ordered_ids']), 'recipe seed position IDs differ')
    for row in independent['seed_records']:
        require(np.allclose(positions[row['id']], row['point'], atol=1e-12, rtol=0),
                'recipe seed position differs: '+row['id'])
    original_manifest = json.loads((ORIGIN/'asset.json').read_text())
    require(recipe['baseline_manifest'] == original_manifest, 'recipe baseline manifest differs')
    baseline = strokes(ORIGIN/'strokes.npz')
    edited = strokes(unit/'outputs/edited/strokes.npz')
    expected_lineage = dict(parent_asset_sha256=sha(ORIGIN/'asset.json'),
                            parent_strokes_sha256=sha(ORIGIN/'strokes.npz'),
                            source_revision=part_revision(baseline),
                            selected_revision=part_revision(edited),
                            non_target_revision=part_revision({sid: p for sid, p in baseline.items()
                                                               if p['part'] != 2}))
    require(recipe['lineage'] == expected_lineage, 'recipe lineage differs from independently read paths')
    if recipe_path.parent.name in ('edited', 'cold_reselect', 'cold_replay'):
        manifest_path = recipe_path.parent/'asset.json'
        manifest = json.loads(manifest_path.read_text())
        require(recipe_file(manifest_path, manifest.get('recipe'), 'recipe') == recipe_path.resolve(),
                'asset must hash-bind its own recipe')
        require(manifest['path_lineage'] == expected_lineage, 'asset lineage differs from recipe')
    return dict(path=str(recipe_path), sha256=sha(recipe_path), files=files,
                original_source_paths=458, selected_target_cache_required=False,
                independent_order_match=True)


def audit_cold_request(unit, independent):
    folder = unit/'cold_request'
    record = audit_recipe(unit, folder/'recipe.json', independent)
    allowed = {(folder/'recipe.json').resolve(), *(Path(p).resolve() for p in record['files'].values())}
    require(all(path.is_relative_to(folder.resolve()) for path in allowed),
            'cold request dependencies not self-contained')
    require({path.resolve() for path in folder.rglob('*') if path.is_file()} == allowed,
            'cold request contains selected output cache or unrelated files')
    return dict(**record, cold_request_files=list(sorted(map(str, allowed))),
                no_selected_strokes_npz_cache=True,
                scope='Cold re-selection uses original458 paths; it does not regenerate curves')


def audit_receipts(unit):
    answer = {}
    operations = dict(baseline='preview', edited='edit', cold_reselect='reselect', cold_replay='replay')
    for name, operation in operations.items():
        folder = unit/'outputs'/name
        row = json.loads((folder/'EDIT.json').read_text())
        require(row['operation'] == operation, f'{name}: operation differs')
        require(sha(row['source']) == row['source_sha256'], f'{name}: source SHA differs')
        expected_count = 458 if name == 'baseline' else 434
        require(row['saved_path_count'] == expected_count, f'{name}: receipt path count differs')
        expected_selection = [2] if name in ('edited', 'cold_reselect') else []
        require(row['selection_parts'] == expected_selection and row['regenerated_parts'] == [],
                f'{name}: unexpected selection/regeneration record')
        expected_counts = {'1': 260, '2': 48 if name == 'baseline' else 24, '3': 150}
        require(row['counts_by_part'] == expected_counts, f'{name}: receipt part counts differ')
        require(row['inherited_verdict'] ==
                json.loads((folder/'asset.json').read_text())['verdict_metadata'],
                f'{name}: receipt inherited verdict differs')
        selected = float(row['selection_seconds'])
        first, complete = (float(row[key]) for key in
                           ('command_to_first_preview_seconds', 'command_to_all_previews_seconds'))
        require(np.isfinite([selected, first, complete]).all() and 0 <= selected < first <= complete,
                f'{name}: invalid latency record')
        require(selected > 0 if name in ('edited', 'cold_reselect') else selected == 0,
                f'{name}: selection timing does not match operation')
        require(set(row['per_view_seconds']) == set(map(str, VIEWS)), f'{name}: camera set differs')
        require(all(np.isfinite(float(s)) and float(s) > 0 for s in row['per_view_seconds'].values()),
                f'{name}: invalid render timing')
        if name == 'cold_reselect':
            require(Path(row['source']).resolve() == (unit/'cold_request/recipe.json').resolve(),
                    'cold selection did not use cache-free request')
        if name == 'cold_replay':
            require(Path(row['source']).resolve() == (unit/'outputs/edited/asset.json').resolve(),
                    'cold replay did not use saved edited bundle')
        answer[name] = dict(operation=operation, selection_seconds=selected,
                            command_to_first_preview_seconds=first,
                            command_to_all_previews_seconds=complete,
                            per_view_seconds=row['per_view_seconds'])
    return dict(bundles=answer, scope='One CPU invocation per operation; includes selection before preview; no FPS claim')


def validate(unit):
    unit = unit.resolve()
    require(unit == DEFAULT_UNIT.resolve(), 'writes restricted to unit009')
    start = time.perf_counter()
    checks, evidence = {}, {}
    metrics = dict(stills=[], frozen_thresholds=THRESHOLDS,
                   metric_scope='Actual8-bit grayscale PNG L1 plus independent analytic y-bin hatch support')

    def check(name, action):
        try:
            evidence[name] = action()
            checks[name] = dict(passed=True)
        except Exception as error:
            checks[name] = dict(passed=False, error_type=type(error).__name__, message=str(error))

    def lock_check():
        lock = json.loads((unit/'SOURCE_LOCK.json').read_text())
        require(bool(lock['files']), 'source lock empty')
        for filename, expected in lock['files'].items():
            require(sha(filename) == expected, 'frozen source/input differs: '+filename)
        protocol = json.loads((unit/'PROTOCOL.json').read_text())
        coverage = protocol['evaluation']['coverage']
        require(coverage['world_y_edges'] == EDGES.tolist()
                and coverage['minimum_eligible_pixels'] == 1
                and coverage['minimum_support_pixels'] == 3
                and coverage['minimum_support_fraction'] == .01,
                'frozen protocol differs from validator coverage gates')
        gates = protocol['evaluation']['gates']
        for key in ('target_part', 'target_inside_L1_min_exclusive',
                    'far_other_fraction_max', 'far_background_fraction_max', 'boundary_band_px'):
            require(gates[key] == THRESHOLDS[key], 'frozen edit gate differs: '+key)
        require(gates['hatch_support_threshold'] == .1, 'frozen support threshold differs')
        return dict(files=len(lock['files']))

    check('frozen_source_and_input_sha256', lock_check)
    for name in BUNDLES:
        check('explicit_bundle_'+name, lambda name=name: audit_bundle(unit, name))
    check('independent_original_seed_order', lambda: independent_seed_order(unit))
    independent = evidence.get('independent_original_seed_order', {})
    check('target_only_nested_selection_config_and_cold_arrays',
          lambda: audit_density_contract(unit, independent))
    for name in ('edited', 'cold_reselect', 'cold_replay'):
        check('explicit_recipe_'+name,
              lambda name=name: audit_recipe(unit, unit/'outputs'/name/'recipe.json', independent))
    check('cold_request_without_selected_cache', lambda: audit_cold_request(unit, independent))
    check('actual_operation_receipts_and_latency', lambda: audit_receipts(unit))
    reference_dir = unit/'references'
    reference_dir.mkdir(exist_ok=True)
    for azimuth in VIEWS:
        def view_action(azimuth=azimuth):
            baseline_dir, edited_dir = (unit/'outputs'/name for name in ('baseline', 'edited'))
            cfg = json.loads((baseline_dir/'config.json').read_text())
            mesh = load_npz(baseline_dir/'mesh.npz')
            camera = core.camera(azimuth, 20, 4.5, SIZE, 600)
            depth, labels = core.analytic_reference(cfg['asset'], camera)
            world_y, bins = axial_masks(depth, labels, camera)
            reference_path = reference_dir/f'{azimuth:03}.npz'
            np.savez_compressed(reference_path, depth=depth, parts=labels, world_y=world_y,
                                axial_bin_masks=np.array(bins), **edit_regions(labels))
            before, old, _ = read_render(baseline_dir/'renders'/f'{azimuth:03}', camera)
            after, new, _ = read_render(edited_dir/'renders'/f'{azimuth:03}', camera)
            old_footprint, new_footprint = footprint(old['hatch'], labels), footprint(new['hatch'], labels)
            all_parts = all(old_footprint[str(p)]['support_pixels'] > 0
                            and new_footprint[str(p)]['support_pixels'] > 0 for p in PARTS)
            old_coverage = axial_coverage(old['hatch'], labels, world_y, bins)
            coverage = axial_coverage(new['hatch'], labels, world_y, bins)
            edit = edit_metrics(before, after, labels)
            shape = whole_shape(labels, mesh['vertices'], camera)
            regression = {key+'_unchanged': bool(np.array_equal(old[key], new[key]))
                          for key in ('contours', 'rings', 'depth', 'parts')}
            regression['no_added_hatch_ink'] = bool(np.all(new['hatch'] <= old['hatch']+1e-12))
            regression['no_added_display_ink'] = bool(np.all(after >= before-1e-12))
            row = dict(azimuth=azimuth, edit=edit, baseline_footprint=old_footprint,
                       candidate_footprint=new_footprint, baseline_axial_coverage=old_coverage,
                       candidate_axial_coverage=coverage, all_three_parts_nonempty=bool(all_parts),
                       stem_hatch_ink_ratio=new_footprint['2']['hatch_ink_mass'] /
                            max(old_footprint['2']['hatch_ink_mass'], 1e-15),
                       whole_shape=shape, regression=regression, cold={},
                       controls=controls(before, after, labels, world_y, bins),
                       quantitative_go=bool(edit['go'] and all_parts and shape['go'] and coverage['go']),
                       reference_mask_path=str(reference_path), reference_mask_sha256=sha(reference_path))
            metrics['stills'].append(row)
            for name in ('cold_reselect', 'cold_replay'):
                folder = unit/'outputs'/name
                replay, repeated, _ = read_render(folder/'renders'/f'{azimuth:03}', camera)
                row['cold'][name] = dict(display_png_pixels_exact=bool(np.array_equal(after, replay)),
                    display_png_file_sha256_exact=sha(edited_dir/'renders'/f'{azimuth:03}.png') ==
                        sha(folder/'renders'/f'{azimuth:03}.png'),
                    saved_layers_exact={key: bool(np.array_equal(new[key], repeated[key]))
                                        for key in ('image', 'hatch', 'contours', 'rings', 'depth', 'parts')})
            require(row['controls']['passed'], 'metric sensitivity failed; raw row retained')
            require(all(regression.values()), 'render regression failed; raw row retained')
            for name, cold in row['cold'].items():
                require(cold['display_png_pixels_exact'] and cold['display_png_file_sha256_exact']
                        and all(cold['saved_layers_exact'].values()), name+' cold output differs')
            return dict(azimuth=azimuth, analytic_mask_recomputed=True,
                        quantitative_go=row['quantitative_go'], controls_passed=True,
                        cold_reselect_and_replay_png_exact=True)
        check(f'actual_images_masks_controls_and_cold_{azimuth:03}', view_action)
    complete = len(metrics['stills']) == len(VIEWS)
    science = dict(
        local_edit_go_four_stills=complete and all(row['edit']['go'] for row in metrics['stills']),
        axial_coverage_go_four_stills=complete and all(row['candidate_axial_coverage']['go'] for row in metrics['stills']),
        all_parts_nonempty_four_stills=complete and all(row['all_three_parts_nonempty'] for row in metrics['stills']),
        whole_shape_visible_four_stills=complete and all(row['whole_shape']['go'] for row in metrics['stills']),
        quantitative_go_four_stills=complete and all(row['quantitative_go'] for row in metrics['stills']),
        metric_controls_go_four_stills=complete and all(row['controls']['passed'] for row in metrics['stills']),
        density_edit_visual_go='REQUIRES_ACTUAL_IMAGE_REVIEW', full_visual='INHERITED_NO_GO',
        inherited_unit004_density_contract='NO_GO_RETAINED_NOT_RETESTED',
        reconstructed_input='BLOCKED', H1_H2='NOT_TESTED', temporal_visibility='NOT_NEWLY_TESTED')
    result = dict(verdict='VALID' if all(row['passed'] for row in checks.values()) else 'INVALID',
                  checks=checks, evidence=evidence, scientific_gates=science,
                  seconds=time.perf_counter()-start,
                  scope='Independent saved-file/analytic-mask/actual-PNG audit; no selector, CLI, walker or renderer imported',
                  limitations=[
                      'Authored GT mesh and labels; no reconstructed-input or auto-segmentation claim.',
                      'Four exposed views from one object; no blind or multi-object conclusion.',
                      'Axial y bins cover only [.20,1.20]; excluded visible stem fractions are reported.',
                      'Hatch support is image coverage, not surface completeness or target-darkness fidelity.',
                      'Seed prefix is Euclidean density control, not guaranteed geodesic/whole-curve spacing.',
                      'File equality and cold reproduction are secondary to actual edit and visible coverage.',
                      'Cold operation reselects original paths; no curve regeneration or whole-recipe generation claim.',
                      'No new orbit/zoom temporal, full hiding, H1/H2 or24FPS evidence.',
                      'Inherited unit004 density NO_GO,17 hidden-profile cases and temporal exclusions remain.',
                  ])
    metrics['scientific_gates'] = science
    metrics['validation_verdict'] = result['verdict']
    write_json(unit/'METRICS.json', metrics)
    write_json(unit/'INDEPENDENT_VALIDATION.json', result)
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
