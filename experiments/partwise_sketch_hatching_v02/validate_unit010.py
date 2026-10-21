"""Independent actual-image audit for the frozen base-length edit.

Analytic visible base cells and separately rendered layer ink are the coverage
gates. No producer, path walker, selector, or renderer is imported or executed.
Saved path identity and cold determinism remain secondary software contracts.
"""
import os

os.environ['CUDA_VISIBLE_DEVICES'] = ''
for _name in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS',
              'NUMEXPR_NUM_THREADS'):
    os.environ[_name] = '1'
os.environ['PYTHONDONTWRITEBYTECODE'] = '1'
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
    PARTS, SIZE, VIEWS, load_npz, native, read_render, sha, strokes, write_json,
)
from experiments.partwise_sketch_hatching_v02.validate_unit005 import (
    assert_strokes_equal, read_asset, whole_shape,
)
from experiments.partwise_sketch_hatching_v02.validate_unit008 import (
    anchor_audit, arrays_equal, part_revision, path_revision, recipe_file,
    require, retained_bytes_equal,
)

DEFAULT_UNIT = Path('/mnt/hdd1/u00134/partwise_sketch_hatching_p1_v02/units/unit_010')
ORIGIN = DEFAULT_UNIT.parent / 'unit_009/outputs/edited'
BUNDLES = ('baseline', 'edited', 'cold_regenerate', 'cold_replay')
REGION_NAMES = ('inner_front', 'inner_back', 'outer_front', 'outer_back')
RADIAL_SPLIT = .29
RADIAL_MAX = .580000001
THRESHOLDS = dict(target_part=3, target_inside_L1_min_exclusive=10.,
                  far_other_fraction_max=.02, far_background_fraction_max=.02,
                  boundary_band_px=2, hatch_support_threshold_exclusive=.1,
                  radial_split_world=RADIAL_SPLIT, minimum_eligible_pixels=1,
                  minimum_support_pixels=3, minimum_support_fraction=.01,
                  every_part_support_pixels_min_exclusive=0,
                  whole_shape_margin_px_min=2, leakage_control_black_pixel_count=16,
                  drift_control_horizontal_shift_px=3)


def edit_regions(labels):
    target = labels == 3
    distance = ndimage.distance_transform_edt(~target)
    return dict(inside=target, boundary_band=(~target) & (distance <= 2),
                far_other_parts=(labels > 0) & (~target) & (distance > 2),
                far_background=(labels == 0) & (distance > 2))


def edit_metrics(before, after, labels):
    change = np.abs(after-before)
    masks = edit_regions(labels)
    total = float(change.sum())
    masses = {name: float(change[mask].sum()) for name, mask in masks.items()}
    row = dict(total_delta=total, inside_delta=masses['inside'],
               inside_mean_delta=float(change[masks['inside']].mean())
               if masks['inside'].any() else 0., mask_pixels=int(masks['inside'].sum()),
               nonzero_edit=masses['inside'] > 10., band_px=2,
               outside_fraction=(total-masses['inside'])/max(total, 1e-15),
               region_pixels={name: int(mask.sum()) for name, mask in masks.items()})
    for name, mass in masses.items():
        row[name+'_delta'] = mass
        row[name+'_fraction'] = mass/max(total, 1e-15)
    row['go'] = bool(row['nonzero_edit'] and row['far_other_parts_fraction'] <= .02
                     and row['far_background_fraction'] <= .02)
    return row


def footprint(hatch, labels):
    rows = {}
    for part in (0,) + PARTS:
        mask = labels == part
        count = int(mask.sum())
        support = int(np.count_nonzero(mask & (hatch > .1)))
        rows[str(part)] = dict(mask_pixels=count, support_pixels=support,
                               support_fraction=support/max(count, 1),
                               hatch_ink_mass=float(hatch[mask].sum()))
    return rows


def base_cells(depth, labels, camera):
    """Four cells defined before rendering, using continuous ray intersections."""
    yy, xx = np.indices(labels.shape)
    points = core.backproject(np.stack((xx, yy), axis=-1),
                              np.where(np.isfinite(depth), depth, 0.), camera)
    radius = np.hypot(points[..., 0], points[..., 2])
    # The lathe axis and camera look-at have x=z=0, so the camera eye defines
    # the fixed front half-plane independently of ink or primitive positions.
    facing = points[..., 0]*camera['eye'][0] + points[..., 2]*camera['eye'][2]
    base = (labels == 3) & (radius >= 0) & (radius <= RADIAL_MAX)
    inner, front = radius < RADIAL_SPLIT, facing >= 0
    masks = dict(inner_front=base & inner & front, inner_back=base & inner & ~front,
                 outer_front=base & ~inner & front, outer_back=base & ~inner & ~front)
    return radius, facing, masks


def support(hatch, mask):
    count = int(mask.sum())
    present = int(np.count_nonzero(mask & (hatch > .1)))
    fraction = present/max(count, 1)
    return dict(eligible_pixels=count, support_pixels=present, support_fraction=fraction,
                hatch_ink_mass=float(hatch[mask].sum()),
                go=bool(count >= 1 and present >= 3 and fraction >= .01))


def coverage(hatch, labels, cells, layers=None):
    rows = {name: support(hatch, mask) for name, mask in cells.items()}
    base = labels == 3
    included = np.logical_or.reduce(list(cells.values()))
    excluded = base & ~included
    answer = dict(cells=rows, combined_cells_go=all(row['go'] for row in rows.values()),
                   analytic_visible_base_pixels=int(base.sum()),
                   included_visible_base_pixels=int(included.sum()),
                   excluded_visible_base_pixels=int(excluded.sum()),
                   excluded_visible_base_fraction=float(excluded.sum())/max(int(base.sum()), 1),
                   radial_split_world=RADIAL_SPLIT, boundary_erosion_px=0,
                   physical_hidden_surfaces='UNMEASURED',
                   scope='Analytic visible base pixels partitioned into inner/outer x front/back; no surface-completeness claim')
    if layers is not None:
        answer['layers'] = {str(layer): dict(whole_base=support(ink, base),
            cells={name: support(ink, mask) for name, mask in cells.items()})
            for layer, ink in enumerate(layers)}
        answer['both_layers_go'] = all(row['whole_base']['go'] for row in answer['layers'].values())
        answer['per_cell_per_layer_scope'] = 'Descriptive only; both-layer gate uses whole visible base denominator'
    answer['go'] = bool(answer['combined_cells_go'] and not excluded.any()
                         and answer.get('both_layers_go', True))
    return answer


def read_layers(unit, azimuth, baseline=False):
    prefix = 'baseline_' if baseline else ''
    layers, files = [], []
    for layer in (0, 1):
        path = unit/'layers'/f'{prefix}{azimuth:03}_layer{layer}.npz'
        data = load_npz(path)
        require('hatch' in data, f'missing isolated hatch: {path}')
        ink = data['hatch']
        require(ink.shape == (SIZE, SIZE) and np.isfinite(ink).all()
                and ink.min() >= 0 and ink.max() <= 1, f'invalid layer hatch: {path}')
        layers.append(ink)
        files.append(dict(path=str(path), sha256=sha(path)))
    return layers, files


def controls(before, after, labels, cells, hatch, layers):
    noedit = edit_metrics(before, before, labels)
    eligible = np.flatnonzero(edit_regions(labels)['far_other_parts'])
    require(len(eligible) >= 16, 'insufficient independent far-other injection pixels')
    chosen = eligible[np.argsort(-before.ravel()[eligible], kind='stable')[:16]]
    require(np.all(before.ravel()[chosen] > 0), 'injection requires16 nonblack pixels')
    injected = before.copy()
    injected.ravel()[chosen] = 0
    leak = edit_metrics(before, injected, labels)
    injected_edited = after.copy()
    injected_edited.ravel()[chosen] = 0
    edited_leak = edit_metrics(before, injected_edited, labels)
    shifted = np.ones_like(before)
    shifted[:, 3:] = before[:, :-3]
    drift = float(np.abs(before-shifted).sum())
    empty = coverage(np.zeros_like(hatch), labels, cells,
                     [np.zeros_like(hatch), np.zeros_like(hatch)])
    missing = {}
    for removed in (0, 1):
        replaced = [ink.copy() for ink in layers]
        replaced[removed][:] = 0
        # Keep combined hatch fixed to prove the layer gate independently
        # detects a missing layer even when the combined coverage looks good.
        missing[str(removed)] = coverage(hatch, labels, cells, replaced)
    passed = (noedit['total_delta'] == 0 and not noedit['go']
              and leak['inside_delta'] == 0 and not leak['go']
              and np.isclose(leak['far_other_parts_fraction'], 1., atol=1e-12, rtol=0)
              and drift > 0 and not empty['go']
              and all(row['support_pixels'] == 0 and not row['go'] for row in empty['cells'].values())
              and all(not row['both_layers_go'] and not row['go'] for row in missing.values()))
    return dict(no_edit=noedit, injected_no_edit_far_other=leak,
                injected_edited_far_other_diagnostic=edited_leak,
                injected_flat_pixel_indices=chosen,
                raster_drift=dict(horizontal_shift_px=3, no_drift_L1=0.,
                                  drifted_image_L1=drift, scope='Raster sensitivity, not temporal stability'),
                zero_hatch_coverage=empty, missing_layer_controls=missing,
                missing_layer_control_scope='Combined hatch fixed; named isolated layer zeroed',
                passed=bool(passed))


def audit_bundle(unit, name):
    folder = unit/'outputs'/name
    manifest, files = read_asset(folder/'asset.json')
    original = json.loads((ORIGIN/'asset.json').read_text())
    require(manifest['verdict_metadata'] == original['verdict_metadata'],
            f'{name}: inherited verdict changed')
    for key, filename in files.items():
        suffix = '.json' if key == 'config' else '.npz'
        require(Path(filename) == (folder/(key+suffix)).resolve(), f'{name}: wrong own {key} binding')
    paths = strokes(folder/'strokes.npz')
    counts = {str(part): sum(row['part'] == part for row in paths.values()) for part in PARTS}
    require(len(paths) == 434 and counts == {'1': 260, '2': 24, '3': 150},
            f'{name}: unexpected counts {counts}')
    mesh = load_npz(folder/'mesh.npz')
    keys = arrays_equal(mesh, load_npz(ORIGIN/'mesh.npz'), name+' immutable mesh')
    return dict(name=name, files=files, counts_by_part=counts,
                inherited_verdict_retained=True, exact_mesh_keys=keys,
                anchors=anchor_audit(paths, mesh))


def saved_lengths(paths, mesh):
    tri = mesh['vertices'][mesh['faces']]
    answer = {}
    for sid, row in paths.items():
        points = np.einsum('ni,nij->nj', row['bary'], tri[row['faces']])
        answer[sid] = float(np.linalg.norm(np.diff(points, axis=0), axis=1).sum())
    return answer


def audit_length_contract(unit):
    paths = {name: strokes(unit/'outputs'/name/'strokes.npz') for name in BUNDLES}
    old, new = paths['baseline'], paths['edited']
    require(assert_strokes_equal(strokes(ORIGIN/'strokes.npz'), old, 'selected434 baseline') == 434,
            'wrong source count')
    require(set(old) == set(new), 'length edit changed IDs')
    retained = {sid: row for sid, row in old.items() if row['part'] != 3}
    require(len(retained) == 284, 'retained count must be284')
    bytes_check = retained_bytes_equal(unit/'outputs/baseline/strokes.npz',
                                       unit/'outputs/edited/strokes.npz', retained)
    changed, target = [], []
    for sid in sorted(old):
        require(old[sid]['part'] == new[sid]['part'] and old[sid]['ink'] == new[sid]['ink'],
                'part or ink changed: '+sid)
        if old[sid]['part'] == 3:
            target.append(sid)
            if path_revision(old[sid]) != path_revision(new[sid]):
                changed.append(sid)
    require(len(target) == 150 and len(changed) > 0, 'no changed target paths')
    groups = {}
    for sid in target:
        pair, layer = sid.rsplit(':layer', 1)
        groups.setdefault(pair, set()).add(int(layer))
    require(len(groups) == 75 and all(value == {0, 1} for value in groups.values()),
            'selected75 paired base identity changed')
    configs = {name: json.loads((unit/'outputs'/name/'config.json').read_text()) for name in BUNDLES}
    require(configs['baseline'] == json.loads((ORIGIN/'config.json').read_text()), 'baseline config changed')
    expected = copy.deepcopy(configs['baseline'])
    require(expected['strokes']['length_by_part']['3'] == .18, 'baseline length is not .18')
    expected['strokes']['length_by_part']['3'] = .12
    require(configs['edited'] == expected, 'config changed outside base length .18->.12')
    cold = {}
    for name in ('cold_regenerate', 'cold_replay'):
        require(configs[name] == expected, name+' config differs')
        cold[name] = arrays_equal(load_npz(unit/'outputs/edited/strokes.npz'),
                                  load_npz(unit/'outputs'/name/'strokes.npz'), name+' arrays')
    mesh = load_npz(unit/'outputs/baseline/mesh.npz')
    lengths = {name: saved_lengths({sid: row for sid, row in paths[name].items()
                                  if row['part'] == 3}, mesh) for name in ('baseline', 'edited')}
    require(all(lengths['edited'][sid] <= lengths['baseline'][sid]+1e-10 for sid in target),
            'base length increased for a saved target path')
    require(sum(lengths['edited'].values()) < sum(lengths['baseline'].values()),
            'total target curve length did not decrease')
    return dict(unchanged_non_target_paths_ids_inks=284, retained_per_field_bytes=bytes_check,
                retained_target_paths_ids_inks=150, paired_selected_base_seeds=75,
                changed_target_ids=changed, changed_target_count=len(changed),
                path_lengths_world=lengths,
                total_target_lengths_world={name: sum(rows.values()) for name, rows in lengths.items()},
                cold_exact_array_keys=cold, only_config_change='strokes.length_by_part.3: .18 -> .12',
                scope='Secondary identity, parameter and path-regeneration contract; actual image gates separate')


def audit_seed_identity(unit):
    baseline = strokes(unit/'outputs/baseline/strokes.npz')
    edited = strokes(unit/'outputs/edited/strokes.npz')
    mesh = load_npz(unit/'outputs/baseline/mesh.npz')
    tri = mesh['vertices'][mesh['faces']]
    area = .5*np.linalg.norm(np.cross(tri[:, 1]-tri[:, 0], tri[:, 2]-tri[:, 0]), axis=1)
    candidates = np.flatnonzero(mesh['parts'] == 3)
    probabilities = area[candidates]/area[candidates].sum()
    rng = np.random.default_rng(np.random.SeedSequence([1729, 3]))
    rows, selected = [], []
    for index in range(150):
        face = int(rng.choice(candidates, p=probabilities))
        q = rng.random(2)
        root = np.sqrt(q[0])
        bary = np.array([1-root, root*(1-q[1]), root*q[1]])
        ids = [f'p3:seed{index:04d}:layer{layer}' for layer in (0, 1)]
        if not any(sid in baseline for sid in ids):
            continue
        selected.append(index)
        for sid in ids:
            record = dict(id=sid, seed_index=index, seed_face=face, seed_bary=bary)
            for name, collection in (('baseline', baseline), ('edited', edited)):
                require(sid in collection, name+' missing selected paired ID '+sid)
                row = collection[sid]
                hits = (row['faces'] == face) & np.all(np.abs(row['bary']-bary) <= 1e-12, axis=1)
                require(bool(hits.any()), name+' seed anchor missing: '+sid)
                record[name+'_seed_anchor_index'] = int(np.flatnonzero(hits)[0])
            rows.append(record)
    require(len(rows) == 150 and len(selected) == 75, 'wrong independently replayed paired seeds')
    return dict(selected_seed_indices=selected, selected_count=150,
                original_seed_count=150, paired_seed_count=75, records=rows,
                scope='Independent area-sampling replay only; no walker/producer invoked')


def audit_recipe(unit, recipe_path, independent):
    recipe = json.loads(recipe_path.read_text())
    expected = dict(schema='base_length_recipe_v1', part=3, style='mixed', seed=1729,
                    original_seed_count=150, selected_count=150, length_world=.12,
                    step_world=.015, angle_deg=0.)
    for key, value in expected.items():
        require(recipe.get(key) == value, 'recipe differs: '+key)
    require(recipe['numpy_version'] == np.__version__, 'recipe NumPy differs')
    require(recipe['selected_seed_indices'] == independent['selected_seed_indices'],
            'recipe selected seeds differ from independently replayed membership')
    old = strokes(unit/'outputs/baseline/strokes.npz')
    new = strokes(unit/'outputs/edited/strokes.npz')
    retained = {sid: row for sid, row in old.items() if row['part'] != 3}
    old_target = {sid: row for sid, row in old.items() if row['part'] == 3}
    new_target = {sid: row for sid, row in new.items() if row['part'] == 3}
    require(recipe['selected_stroke_inks'] == {sid: row['ink'] for sid, row in old_target.items()},
            'recipe selected ink mapping differs')
    files = {name: recipe_file(recipe_path, recipe.get(name), name)
             for name in ('mesh', 'retained', 'config')}
    require(assert_strokes_equal(retained, strokes(files['retained']), 'recipe retained') == 284,
            'recipe retained count differs')
    arrays_equal(load_npz(files['mesh']), load_npz(ORIGIN/'mesh.npz'), 'recipe mesh')
    require(json.loads(files['config'].read_text()) ==
            json.loads((unit/'outputs/edited/config.json').read_text()), 'recipe config differs')
    for name in ('legacy/core.py', 'legacy/core_walk_v2.py', 'length_cli.py',
                 'common.py', 'asset_cli.py', 'renderer.py'):
        if name.startswith('legacy/'):
            path = WORK/'experiments/partwise_sketch_hatching'/name.split('/')[-1]
        else:
            path = WORK/'experiments/partwise_sketch_hatching_v02'/name
        require(recipe['generator_sha256'].get(name) == sha(path), 'recipe generator SHA differs: '+name)
    source = unit/'inputs/asset.json'
    parent = json.loads(source.read_text())
    for key in ('recipe', 'path_lineage', 'mesh', 'strokes', 'config'):
        parent.pop(key, None)
    require(recipe['baseline_manifest'] == parent, 'recipe base manifest differs')
    expected_lineage = dict(parent_asset_sha256=sha(source),
                            parent_strokes_sha256=sha(ORIGIN/'strokes.npz'),
                            parent_target_revision=part_revision(old_target),
                            target_path_revision=part_revision(new_target),
                            non_target_revision=part_revision(retained),
                            target_seed_identity='original per-part area-sampled seed index + layer; paired75 selection retained')
    require(recipe['lineage'] == expected_lineage, 'recipe lineage differs from saved path digests')
    if recipe_path.parent.name in ('edited', 'cold_regenerate', 'cold_replay'):
        manifest_path = recipe_path.parent/'asset.json'
        manifest = json.loads(manifest_path.read_text())
        require(recipe_file(manifest_path, manifest.get('recipe'), 'recipe') == recipe_path.resolve(),
                'asset does not bind its own recipe')
        require(manifest['path_lineage'] == expected_lineage, 'asset lineage differs')
    return dict(path=str(recipe_path), sha256=sha(recipe_path), files=files,
                retained_paths=284, selected_target_cache_required=False,
                original_seed_count=150, paired_selected_seed_count=75)


def audit_cold_request(unit, independent):
    folder = unit/'cold_request'
    record = audit_recipe(unit, folder/'recipe.json', independent)
    allowed = {(folder/'recipe.json').resolve(), *(Path(p).resolve() for p in record['files'].values())}
    require(all(path.is_relative_to(folder.resolve()) for path in allowed), 'cold request not self-contained')
    require({path.resolve() for path in folder.rglob('*') if path.is_file()} == allowed,
            'cold request includes target paths or unrelated files')
    return dict(**record, cold_request_files=sorted(map(str, allowed)), no_target_path_cache=True)


def audit_receipts(unit):
    rows = {}
    operations = dict(baseline='preview', edited='edit', cold_regenerate='regenerate', cold_replay='replay')
    for name, operation in operations.items():
        folder = unit/'outputs'/name
        row = json.loads((folder/'EDIT.json').read_text())
        require(row['operation'] == operation, name+' operation differs')
        require(sha(row['source']) == row['source_sha256'], name+' source SHA differs')
        require(row['saved_path_count'] == 434 and row['counts_by_part'] == {'1': 260, '2': 24, '3': 150},
                name+' receipt counts differ')
        expected_parts = [3] if name in ('edited', 'cold_regenerate') else []
        require(row['regenerated_parts'] == expected_parts, name+' regenerated parts differ')
        require(row['inherited_verdict'] == json.loads((folder/'asset.json').read_text())['verdict_metadata'],
                name+' receipt verdict differs')
        generation, first, complete = (float(row[key]) for key in
            ('regeneration_seconds', 'command_to_first_preview_seconds', 'command_to_all_previews_seconds'))
        require(np.isfinite([generation, first, complete]).all() and 0 <= generation < first <= complete,
                name+' invalid latency')
        require(generation > 0 if expected_parts else generation == 0, name+' generation timing mismatch')
        require(set(row['per_view_seconds']) == set(map(str, VIEWS)), name+' camera set differs')
        require(all(np.isfinite(float(s)) and float(s) > 0 for s in row['per_view_seconds'].values()),
                name+' per-view timing invalid')
        if name == 'cold_regenerate':
            require(Path(row['source']).resolve() == (unit/'cold_request/recipe.json').resolve(),
                    'cold regenerate source differs')
        if name == 'cold_replay':
            require(Path(row['source']).resolve() == (unit/'outputs/edited/asset.json').resolve(),
                    'cold replay source differs')
        rows[name] = dict(operation=operation, regeneration_seconds=generation,
                          command_to_first_preview_seconds=first,
                          command_to_all_previews_seconds=complete,
                          per_view_seconds=row['per_view_seconds'])
    return dict(bundles=rows, scope='One actual CPU invocation per operation; no FPS claim')


def audit_no_edit_operation(unit):
    baseline = unit/'outputs/baseline'
    noedit = unit/'outputs/no_edit'
    camera = core.camera(30, 20, 4.5, SIZE, 600)
    before, old, _ = read_render(baseline/'renders/030', camera)
    after, new, _ = read_render(noedit/'renders/030', camera)
    cfg = json.loads((baseline/'config.json').read_text())
    _, labels = core.analytic_reference(cfg['asset'], camera)
    measured = edit_metrics(before, after, labels)
    require(measured['total_delta'] == 0 and not measured['go'], 'actual no-op PNG differs')
    require(sha(baseline/'renders/030.png') == sha(noedit/'renders/030.png'), 'actual no-op PNG bytes differ')
    exact = {key: bool(np.array_equal(old[key], new[key]))
             for key in ('image', 'hatch', 'depth', 'parts', 'contours', 'rings')}
    require(all(exact.values()), 'actual no-op saved render differs')
    require(assert_strokes_equal(strokes(baseline/'strokes.npz'), strokes(noedit/'strokes.npz'),
                                 'actual .18 no-op') == 434, 'actual no-op paths differ')
    require(json.loads((noedit/'config.json').read_text()) == cfg, 'actual no-op config differs')
    receipt = json.loads((noedit/'EDIT.json').read_text())
    require(receipt['operation'] == 'edit' and receipt['regenerated_parts'] == [3]
            and receipt['regeneration_seconds'] > 0, 'actual no-op did not regenerate base')
    return dict(actual_no_edit=measured, all_saved_render_layers_exact=exact,
                regenerated_base_length_world=.18, all434_paths_exact=True,
                scope='Executed length.18 producer compatibility control plus actual PNG no-edit rejection')


def validate(unit):
    unit = unit.resolve()
    require(unit == DEFAULT_UNIT.resolve(), 'validator writes only current unit010')
    start = time.perf_counter()
    checks, evidence = {}, {}
    metrics = dict(stills=[], frames=[], frozen_thresholds=THRESHOLDS,
                   metric_scope='Actual8-bit PNG edit L1; independent analytic visible-base cells; actual rendered layer support')

    def check(name, action):
        try:
            evidence[name] = action()
            checks[name] = dict(passed=True)
        except Exception as error:
            checks[name] = dict(passed=False, error_type=type(error).__name__, message=str(error))

    def lock_check():
        lock = json.loads((unit/'SOURCE_LOCK.json').read_text())
        require(bool(lock['files']), 'source lock empty')
        for filename, digest in lock['files'].items():
            require(sha(filename) == digest, 'frozen source/input differs: '+filename)
        protocol = json.loads((unit/'PROTOCOL.json').read_text())
        require(protocol['source_asset_sha256'] == sha(ORIGIN/'asset.json'),
                'frozen origin asset SHA differs')
        for filename, digest in protocol['inputs'].items():
            require(sha(filename) == digest, 'frozen explicit input differs: '+filename)
        _, source_files = read_asset(unit/'inputs/asset.json')
        for key in ('mesh', 'strokes', 'config'):
            extension = '.json' if key == 'config' else '.npz'
            require(sha(source_files[key]) == sha(ORIGIN/(key+extension)),
                    'frozen input differs from original selected434: '+key)
        gates, cov = protocol['evaluation']['gates'], protocol['evaluation']['coverage']
        for key in ('target_part', 'target_inside_L1_min_exclusive', 'far_other_fraction_max',
                    'far_background_fraction_max', 'boundary_band_px',
                    'every_part_support_pixels_min_exclusive'):
            require(gates[key] == THRESHOLDS[key], 'frozen edit gate differs: '+key)
        require(gates['hatch_support_threshold'] == .1 and gates['full_shape_margin_px_min'] == 2,
                'frozen ink/whole-shape thresholds differ')
        require(cov['radial_edges_world'] == [0, RADIAL_SPLIT, RADIAL_MAX], 'frozen radial cells differ')
        for key in ('minimum_eligible_pixels', 'minimum_support_pixels', 'minimum_support_fraction'):
            require(cov[key] == THRESHOLDS[key], 'frozen coverage threshold differs: '+key)
        require(protocol['media']['orbit']['frames'] == 24 and protocol['media']['zoom']['frames'] == 16,
                'frozen trajectory lengths differ')
        return dict(files=len(lock['files']), protocol_sha256=sha(unit/'PROTOCOL.json'))

    check('frozen_source_and_input_sha256', lock_check)
    for name in BUNDLES:
        check('explicit_bundle_'+name, lambda name=name: audit_bundle(unit, name))
    check('target_only_length_config_retained284_and_cold_arrays', lambda: audit_length_contract(unit))
    check('independent_paired_seed_identity', lambda: audit_seed_identity(unit))
    independent = evidence.get('independent_paired_seed_identity', {})
    for name in ('edited', 'cold_regenerate', 'cold_replay'):
        check('explicit_recipe_'+name,
              lambda name=name: audit_recipe(unit, unit/'outputs'/name/'recipe.json', independent))
    check('cold_request_without_target_cache', lambda: audit_cold_request(unit, independent))
    check('actual_operation_receipts_and_latency', lambda: audit_receipts(unit))
    check('actual_length018_no_edit_operation', lambda: audit_no_edit_operation(unit))
    reference_dir = unit/'references'
    reference_dir.mkdir(exist_ok=True)
    for azimuth in VIEWS:
        def view_action(azimuth=azimuth):
            before_dir, after_dir = (unit/'outputs'/name for name in ('baseline', 'edited'))
            cfg = json.loads((before_dir/'config.json').read_text())
            mesh = load_npz(before_dir/'mesh.npz')
            camera = core.camera(azimuth, 20, 4.5, SIZE, 600)
            depth, labels = core.analytic_reference(cfg['asset'], camera)
            radius, facing, cells = base_cells(depth, labels, camera)
            ref = reference_dir/f'{azimuth:03}.npz'
            np.savez_compressed(ref, depth=depth, parts=labels, radius=radius,
                                front_halfspace_value=facing, **cells, **edit_regions(labels))
            before, old, _ = read_render(before_dir/'renders'/f'{azimuth:03}', camera)
            after, new, _ = read_render(after_dir/'renders'/f'{azimuth:03}', camera)
            new_layers, layer_files = read_layers(unit, azimuth)
            old_layers, baseline_layer_files = read_layers(unit, azimuth, baseline=True)
            for name, combined, separate in (('baseline', old['hatch'], old_layers),
                                             ('edited', new['hatch'], new_layers)):
                for layer, ink in enumerate(separate):
                    require(np.all(ink <= combined+1e-12), f'{name} isolated layer{layer} exceeds combined hatch')
            old_support, new_support = footprint(old['hatch'], labels), footprint(new['hatch'], labels)
            all_parts = all(old_support[str(part)]['support_pixels'] > 0
                            and new_support[str(part)]['support_pixels'] > 0 for part in PARTS)
            old_coverage = coverage(old['hatch'], labels, cells, old_layers)
            new_coverage = coverage(new['hatch'], labels, cells, new_layers)
            edit = edit_metrics(before, after, labels)
            shape = whole_shape(labels, mesh['vertices'], camera)
            regression = {key+'_unchanged': bool(np.array_equal(old[key], new[key]))
                          for key in ('contours', 'rings', 'depth', 'parts')}
            row = dict(azimuth=azimuth, edit=edit, baseline_footprint=old_support,
                       candidate_footprint=new_support, baseline_base_coverage=old_coverage,
                       candidate_base_coverage=new_coverage, all_three_parts_nonempty=bool(all_parts),
                       whole_shape=shape, regression=regression, cold={},
                       base_hatch_ink_ratio=new_support['3']['hatch_ink_mass']/max(old_support['3']['hatch_ink_mass'], 1e-15),
                       controls=controls(before, after, labels, cells, new['hatch'], new_layers),
                       quantitative_go=bool(edit['go'] and all_parts and shape['go'] and new_coverage['go']),
                       reference_mask_path=str(ref), reference_mask_sha256=sha(ref),
                       layer_files=layer_files, baseline_layer_files=baseline_layer_files)
            metrics['stills'].append(row)
            for name in ('cold_regenerate', 'cold_replay'):
                directory = unit/'outputs'/name
                replay, repeated, _ = read_render(directory/'renders'/f'{azimuth:03}', camera)
                row['cold'][name] = dict(display_png_pixels_exact=bool(np.array_equal(after, replay)),
                    display_png_file_sha256_exact=sha(after_dir/'renders'/f'{azimuth:03}.png') ==
                        sha(directory/'renders'/f'{azimuth:03}.png'),
                    saved_layers_exact={key: bool(np.array_equal(new[key], repeated[key]))
                                        for key in ('image', 'hatch', 'depth', 'parts', 'contours', 'rings')})
            require(row['controls']['passed'], 'metric sensitivity failed; raw row retained')
            require(all(regression.values()), 'nonhatch regression failed; raw row retained')
            for name, cold in row['cold'].items():
                require(cold['display_png_pixels_exact'] and cold['display_png_file_sha256_exact']
                        and all(cold['saved_layers_exact'].values()), name+' cold output differs')
            return dict(azimuth=azimuth, quantitative_go=row['quantitative_go'],
                        independent_analytic_mask=True, actual_both_layer_support=new_coverage['both_layers_go'],
                        controls_passed=True, cold_regenerate_and_replay_png_exact=True)
        check(f'actual_images_cells_layers_controls_and_cold_{azimuth:03}', view_action)

    def trajectory_action():
        trajectories = {name: json.loads((unit/f'TRAJECTORY_{name}.json').read_text())
                        for name in ('orbit', 'zoom')}
        for sequence, count in (('orbit', 24), ('zoom', 16)):
            require(len(trajectories[sequence]) == count, sequence+' frame count differs')
            for index, row in enumerate(trajectories[sequence]):
                expected_azimuth = index*15 if sequence == 'orbit' else 30
                expected_distance = 4.5 if sequence == 'orbit' else 4.8-.8*np.cos(2*np.pi*index/15)
                require(row['frame'] == index and row['azimuth'] == expected_azimuth
                        and row['elevation'] == 20 and abs(row['distance']-expected_distance) <= 1e-12,
                        sequence+' trajectory differs from frozen analytic schedule')
                require(row['asset_sha256'] == sha(unit/'outputs/edited/asset.json'),
                        sequence+' frame bound asset differs')
        cfg = json.loads((unit/'outputs/edited/config.json').read_text())
        mesh = load_npz(unit/'outputs/edited/mesh.npz')
        for sequence in ('orbit', 'zoom'):
            directory = reference_dir/sequence
            directory.mkdir(exist_ok=True)
            for item in trajectories[sequence]:
                index = item['frame']
                camera = core.camera(item['azimuth'], item['elevation'], item['distance'], SIZE, 600)
                pixels, rendered, _ = read_render(unit/'frames'/sequence/f'{index:04}', camera)
                depth, labels = core.analytic_reference(cfg['asset'], camera)
                radius, facing, cells = base_cells(depth, labels, camera)
                ref = directory/f'{index:04}.npz'
                np.savez_compressed(ref, depth=depth, parts=labels, radius=radius,
                                    front_halfspace_value=facing, **cells)
                cov = coverage(rendered['hatch'], labels, cells)
                support_rows = footprint(rendered['hatch'], labels)
                all_parts = all(support_rows[str(part)]['support_pixels'] > 0 for part in PARTS)
                shape = whole_shape(labels, mesh['vertices'], camera)
                metrics['frames'].append(dict(sequence=sequence, frame=index,
                    camera_parameters=item, footprint=support_rows, base_coverage=cov,
                    all_three_parts_nonempty=bool(all_parts), whole_shape=shape,
                    quantitative_go=bool(cov['go'] and all_parts and shape['go']),
                    reference_mask_path=str(ref), reference_mask_sha256=sha(ref),
                    image_sha256=sha(unit/'frames'/sequence/f'{index:04}.png')))
        return dict(frames=len(metrics['frames']), all_saved_pngs_checked=True,
                    geometric_cells_recomputed_each_frame=True,
                    scope='Whole-object frame coverage, not per-stroke correspondence or temporal flicker')
    check('all40_orbit_zoom_actual_images_analytic_cells', trajectory_action)
    complete = len(metrics['stills']) == len(VIEWS)
    frames_complete = len(metrics['frames']) == 40
    science = dict(local_edit_go_four_stills=complete and all(row['edit']['go'] for row in metrics['stills']),
        base_cells_and_both_layers_go_four_stills=complete and all(row['candidate_base_coverage']['go'] for row in metrics['stills']),
        all_parts_nonempty_four_stills=complete and all(row['all_three_parts_nonempty'] for row in metrics['stills']),
        whole_shape_visible_four_stills=complete and all(row['whole_shape']['go'] for row in metrics['stills']),
        quantitative_go_four_stills=complete and all(row['quantitative_go'] for row in metrics['stills']),
        metric_controls_go_four_stills=complete and all(row['controls']['passed'] for row in metrics['stills']),
        base_cells_go_all40_frames=frames_complete and all(row['base_coverage']['go'] for row in metrics['frames']),
        all_parts_nonempty_all40_frames=frames_complete and all(row['all_three_parts_nonempty'] for row in metrics['frames']),
        whole_shape_visible_all40_frames=frames_complete and all(row['whole_shape']['go'] for row in metrics['frames']),
        quantitative_go_all40_frames=frames_complete and all(row['quantitative_go'] for row in metrics['frames']),
        base_length_visual_go='REQUIRES_ACTUAL_IMAGE_REVIEW', whole_object_visual='REQUIRES_ACTUAL_IMAGE_REVIEW',
        inherited_unit004_density_contract='NO_GO_RETAINED_NOT_RETESTED', reconstructed_input='BLOCKED',
        H1_H2='NOT_TESTED', temporal_correspondence='NOT_NEWLY_TESTED', physical_hidden_surface_coverage='UNMEASURED')
    result = dict(verdict='VALID' if all(row['passed'] for row in checks.values()) else 'INVALID',
        checks=checks, evidence=evidence, scientific_gates=science, seconds=time.perf_counter()-start,
        scope='Independent saved-file/actual-PNG/continuous analytic-mask audit; no producer, walker or renderer execution',
        limitations=['One authored GT lamp and exposed cameras; no reconstructed or multi-object conclusion.',
            'Four base cells partition visible analytic pixels only; physically hidden surfaces are unmeasured.',
            'Both-layer support is measured on actual isolated raster ink, not inferred from paired IDs.',
            'Per-cell per-layer support is descriptive; whole-base both-layer threshold is frozen.',
            '40 orbit/zoom frames measure whole-object support; no new per-stroke temporal correspondence claim.',
            'File identity and cold regeneration are secondary to actual image response, isolation and coverage.',
            'Inherited unit004 density NO_GO,17 hidden-profile cases and temporal exclusions remain.'])
    metrics['scientific_gates'] = science
    metrics['validation_verdict'] = result['verdict']
    write_json(unit/'METRICS.json', metrics)
    write_json(unit/'INDEPENDENT_VALIDATION.json', result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--unit', type=Path, default=DEFAULT_UNIT)
    result = validate(parser.parse_args().unit)
    print(json.dumps(native(dict(verdict=result['verdict'], checks=result['checks'],
                                 scientific_gates=result['scientific_gates'])), allow_nan=False))
    return 0 if result['verdict'] == 'VALID' else 1


if __name__ == '__main__':
    raise SystemExit(main())
