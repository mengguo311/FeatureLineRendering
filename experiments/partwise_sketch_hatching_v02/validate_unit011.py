"""Independent actual-image audit of the frozen shade seed-dispersion edit.

Coverage uses continuous analytic ray intersections, never a stroke-derived
mask. Spacing uses saved isolated rendered stroke support, never seed distance.
No producer, path generator, walker or renderer is imported or executed.
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

DEFAULT_UNIT = Path('/mnt/hdd1/u00134/partwise_sketch_hatching_p1_v02/units/unit_011')
ORIGIN = DEFAULT_UNIT.parent / 'unit_010/outputs/edited'
BUNDLES = ('baseline', 'edited', 'cold_regenerate', 'cold_replay')
HEIGHT_EDGES = [1.4, 1.7166666666666666, 2.033333333333333, 2.350000001]
AZIMUTH_EDGES = [0., np.pi/2, np.pi, 3*np.pi/2, 2*np.pi]
THRESHOLDS = dict(target_part=1, target_inside_L1_min_exclusive=10.,
    far_other_fraction_max=.02, far_background_fraction_max=.02,
    boundary_band_px=2, hatch_support_threshold_exclusive=.1,
    minimum_eligible_pixels=20, minimum_support_pixels=3,
    minimum_support_fraction=.01, every_part_support_pixels_min_exclusive=0,
    whole_shape_margin_px_min=2, leakage_control_black_pixel_count=16,
    drift_control_horizontal_shift_px=3, distance_manhattan_px=2,
    close_fraction_ratio_max=.8, ink_mass_ratio_min=.8, ink_mass_ratio_max=1.25)


def edit_regions(labels):
    target = labels == 1
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
        inside_mean_delta=float(change[masks['inside']].mean()) if masks['inside'].any() else 0.,
        mask_pixels=int(masks['inside'].sum()), nonzero_edit=masses['inside'] > 10.,
        band_px=2, outside_fraction=(total-masses['inside'])/max(total, 1e-15),
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
        present = int(np.count_nonzero(mask & (hatch > .1)))
        rows[str(part)] = dict(mask_pixels=count, support_pixels=present,
            support_fraction=present/max(count, 1), hatch_ink_mass=float(hatch[mask].sum()))
    return rows


def shade_cells(depth, labels, camera):
    """Twelve world-fixed cells include every visible analytic shade pixel."""
    yy, xx = np.indices(labels.shape)
    points = core.backproject(np.stack((xx, yy), axis=-1),
                             np.where(np.isfinite(depth), depth, 0.), camera)
    height = points[..., 1]
    azimuth = np.mod(np.arctan2(points[..., 2], points[..., 0]), 2*np.pi)
    # Clip only bin indices at numeric extrema; never erase visible pixels.
    height_index = np.clip(np.searchsorted(HEIGHT_EDGES, height, side='right')-1, 0, 2)
    azimuth_index = np.clip(np.searchsorted(AZIMUTH_EDGES, azimuth, side='right')-1, 0, 3)
    shade = labels == 1
    masks = {f'h{h}_q{q}': shade & (height_index == h) & (azimuth_index == q)
             for h in range(3) for q in range(4)}
    return height, azimuth, masks


def support(hatch, mask):
    count = int(mask.sum())
    present = int(np.count_nonzero(mask & (hatch > .1)))
    eligible = count >= 20
    fraction = present/max(count, 1)
    return dict(visible_pixels=count, eligible_pixels=count if eligible else 0,
        eligible=eligible, abstention=not eligible,
        abstention_reason=None if eligible else 'fewer_than20_visible_pixels',
        support_pixels=present, support_fraction=fraction,
        hatch_ink_mass=float(hatch[mask].sum()),
        go=bool(present >= 3 and fraction >= .01) if eligible else None)


def coverage(hatch, labels, cells):
    rows = {name: support(hatch, mask) for name, mask in cells.items()}
    included_count = np.sum(np.stack(list(cells.values())), axis=0)
    shade = labels == 1
    eligible = [name for name, row in rows.items() if row['eligible']]
    abstained = [name for name, row in rows.items() if row['abstention']]
    eligible_pixels = sum(rows[name]['visible_pixels'] for name in eligible)
    partition = np.array_equal(included_count, shade.astype(included_count.dtype))
    return dict(cells=rows, eligible_cell_names=eligible, abstained_cell_names=abstained,
        eligible_cell_count=len(eligible), abstained_cell_count=len(abstained),
        analytic_visible_shade_pixels=int(shade.sum()),
        included_visible_shade_pixels=int(np.count_nonzero(included_count)),
        excluded_visible_shade_pixels=int(np.count_nonzero(shade & (included_count == 0))),
        eligible_visible_shade_pixels=eligible_pixels,
        abstained_visible_shade_pixels=int(shade.sum())-eligible_pixels,
        eligible_visible_shade_fraction=eligible_pixels/max(int(shade.sum()), 1),
        height_edges_world=HEIGHT_EDGES, azimuth_edges_radians=AZIMUTH_EDGES,
        complete_disjoint_visible_partition=bool(partition), boundary_erosion_px=0,
        physical_hidden_surfaces='UNMEASURED',
        scope='Visible analytic shade pixels only; tiny cells explicitly abstain; no hidden-surface coverage claim',
        go=bool(partition and eligible and all(rows[name]['go'] for name in eligible)))


def support_spacing(support_indices, shape=(SIZE, SIZE)):
    """Each own support pixel counts once if another stroke is within L1<=2."""
    counts = np.zeros(shape, dtype=np.uint16)
    dilated_counts = np.zeros(shape, dtype=np.uint16)
    for indices in support_indices:
        binary = np.zeros(shape, dtype=bool)
        binary.ravel()[indices] = True
        counts += binary
        dilated_counts += ndimage.binary_dilation(binary, iterations=2)
    total, close, overlap, rows = 0, 0, 0, []
    for indices in support_indices:
        n = len(indices)
        near = int(np.count_nonzero(dilated_counts.ravel()[indices] > 1))
        exact = int(np.count_nonzero(counts.ravel()[indices] > 1))
        total += n
        close += near
        overlap += exact
        rows.append(dict(support_pixels=n, close_support_pixels=near,
                         exact_overlap_support_pixels=exact))
    return dict(individual_support_pixels=total, close_support_pixels=close,
        close_support_fraction=close/max(total, 1), exact_overlap_support_pixels=overlap,
        exact_overlap_support_fraction=overlap/max(total, 1),
        union_support_pixels=int(np.count_nonzero(counts)),
        spatial_union_overlap_pixels=int(np.count_nonzero(counts > 1)), per_stroke=rows,
        distance_manhattan_px=2,
        scope='Actual isolated raster support>.1 intersect analytic shade; self support excluded')


def read_probe(unit, name, azimuth, labels, actual):
    path = unit/'probes'/name/f'{azimuth:03}.npz'
    data = load_npz(path)
    require(set(('ids', 'offsets', 'indices', 'values', 'full_hatch', 'full_image')).issubset(data),
            'missing sparse stroke probe fields')
    paths = strokes(unit/'outputs'/name/'strokes.npz')
    expected_ids = {sid for sid, row in paths.items() if row['part'] == 1}
    ids = list(map(str, data['ids']))
    require(len(ids) == 260 and len(set(ids)) == 260 and set(ids) == expected_ids,
            'probe does not contain all260 exact shade IDs')
    offsets, indices, values = data['offsets'], data['indices'], data['values']
    require(offsets.shape == (261,) and np.issubdtype(offsets.dtype, np.integer)
            and offsets[0] == 0 and offsets[-1] == len(indices)
            and np.all(np.diff(offsets) >= 0), 'invalid probe offsets')
    require(indices.ndim == 1 and np.issubdtype(indices.dtype, np.integer)
            and np.all((indices >= 0) & (indices < SIZE*SIZE)), 'invalid probe indices')
    require(values.shape == indices.shape and np.isfinite(values).all()
            and np.all((values > 0) & (values <= 1)), 'invalid sparse probe ink')
    require(np.array_equal(data['full_hatch'], actual['hatch'])
            and np.array_equal(data['full_image'], actual['image']), 'probe full render differs')
    shade = (labels == 1).ravel()
    supports, individual_mass, masses = [], 0., []
    for index, sid in enumerate(ids):
        lo, hi = offsets[index:index+2]
        ix, val = indices[lo:hi], values[lo:hi]
        require(len(np.unique(ix)) == len(ix), 'duplicate sparse pixel: '+sid)
        require(np.all(val <= actual['hatch'].ravel()[ix]+1e-12),
                'isolated stroke exceeds full hatch: '+sid)
        supports.append(ix[(val > .1) & shade[ix]])
        mass = float(val[shade[ix]].sum())
        individual_mass += mass
        masses.append(mass)
    measured = support_spacing(supports)
    for sid, mass, row in zip(ids, masses, measured['per_stroke']):
        row['id'] = sid
        row['visible_shade_ink_mass'] = mass
    full_mass = float(actual['hatch'][labels == 1].sum())
    measured.update(path=str(path), sha256=sha(path), individual_shade_ink_mass=individual_mass,
        full_shade_hatch_ink_mass=full_mass,
        union_ink_loss=individual_mass-full_mass,
        union_ink_loss_fraction=(individual_mass-full_mass)/max(individual_mass, 1e-15),
        union_ink_loss_scope='Signed diagnostic: full hatch may include other-part boundary ink',
        strokes_with_nonzero_visible_support=sum(bool(len(ix)) for ix in supports))
    nonempty = next((ix for ix in supports if len(ix)), None)
    require(nonempty is not None, 'spacing probe has no visible shade support')
    single = support_spacing([nonempty])
    duplicate = support_spacing([nonempty, nonempty])
    measured['duplicate_raster_control'] = dict(single=single, duplicate=duplicate,
        passed=bool(single['close_support_fraction'] == 0
                    and duplicate['close_support_fraction'] == 1
                    and duplicate['exact_overlap_support_fraction'] == 1))
    return measured


def controls(before, after, labels, cells, hatch):
    noedit = edit_metrics(before, before, labels)
    eligible = np.flatnonzero(edit_regions(labels)['far_other_parts'])
    require(len(eligible) >= 16, 'insufficient far-other injection pixels')
    chosen = eligible[np.argsort(-before.ravel()[eligible], kind='stable')[:16]]
    require(np.all(before.ravel()[chosen] > 0), 'injection requires16 nonblack pixels')
    injected = before.copy()
    injected.ravel()[chosen] = 0
    leak = edit_metrics(before, injected, labels)
    injected_after = after.copy()
    injected_after.ravel()[chosen] = 0
    edited_leak = edit_metrics(before, injected_after, labels)
    shifted = np.ones_like(before)
    shifted[:, 3:] = before[:, :-3]
    drift = float(np.abs(before-shifted).sum())
    empty = coverage(np.zeros_like(hatch), labels, cells)
    passed = (noedit['total_delta'] == 0 and not noedit['go']
        and leak['inside_delta'] == 0 and not leak['go']
        and np.isclose(leak['far_other_parts_fraction'], 1., atol=1e-12, rtol=0)
        and drift > 0 and not empty['go']
        and all(row['support_pixels'] == 0 and row['go'] is not True
                for row in empty['cells'].values()))
    return dict(no_edit=noedit, injected_no_edit_far_other=leak,
        injected_edited_far_other_diagnostic=edited_leak,
        injected_flat_pixel_indices=chosen,
        raster_drift=dict(horizontal_shift_px=3, no_drift_L1=0., drifted_image_L1=drift,
                          scope='Raster sensitivity, not temporal stability'),
        zero_hatch_coverage=empty, passed=bool(passed))


def audit_bundle(unit, name):
    folder = unit/'outputs'/name
    manifest, files = read_asset(folder/'asset.json')
    original = json.loads((ORIGIN/'asset.json').read_text())
    require(manifest['verdict_metadata'] == original['verdict_metadata'],
            name+' inherited verdict changed')
    for key, filename in files.items():
        suffix = '.json' if key == 'config' else '.npz'
        require(Path(filename) == (folder/(key+suffix)).resolve(), name+' own binding differs')
    paths = strokes(folder/'strokes.npz')
    counts = {str(part): sum(row['part'] == part for row in paths.values()) for part in PARTS}
    require(len(paths) == 434 and counts == {'1': 260, '2': 24, '3': 150}, 'unexpected counts')
    mesh = load_npz(folder/'mesh.npz')
    keys = arrays_equal(mesh, load_npz(ORIGIN/'mesh.npz'), name+' immutable mesh')
    return dict(name=name, files=files, counts_by_part=counts,
        inherited_verdict_retained=True, exact_mesh_keys=keys, anchors=anchor_audit(paths, mesh))


def audit_spacing_contract(unit):
    paths = {name: strokes(unit/'outputs'/name/'strokes.npz') for name in BUNDLES}
    old, new = paths['baseline'], paths['edited']
    require(assert_strokes_equal(strokes(ORIGIN/'strokes.npz'), old, 'baseline') == 434,
            'baseline differs from accepted unit010')
    require(set(old) == set(new), 'spacing edit changed IDs')
    retained = {sid: row for sid, row in old.items() if row['part'] != 1}
    require(len(retained) == 174, 'retained count differs')
    checked = retained_bytes_equal(unit/'outputs/baseline/strokes.npz',
                                   unit/'outputs/edited/strokes.npz', retained)
    changed, target = [], []
    for sid in sorted(old):
        require(old[sid]['part'] == new[sid]['part'] and old[sid]['ink'] == new[sid]['ink'],
                'part or ink changed: '+sid)
        if old[sid]['part'] == 1:
            target.append(sid)
            if path_revision(old[sid]) != path_revision(new[sid]):
                changed.append(sid)
    require(len(target) == 260 and changed, 'no actual target coordinate changes')
    configs = {name: json.loads((unit/'outputs'/name/'config.json').read_text()) for name in BUNDLES}
    require(configs['baseline'] == json.loads((ORIGIN/'config.json').read_text()), 'baseline config changed')
    expected = copy.deepcopy(configs['baseline'])
    expected['seed_placement_by_part'] = {'1': 'band_anisotropic_farthest_v1'}
    require(configs['edited'] == expected, 'config changed outside shade seed placement')
    cold = {}
    for name in ('cold_regenerate', 'cold_replay'):
        require(configs[name] == expected, name+' config differs')
        cold[name] = arrays_equal(load_npz(unit/'outputs/edited/strokes.npz'),
                                  load_npz(unit/'outputs'/name/'strokes.npz'), name+' arrays')
    return dict(unchanged_non_target_paths_ids_inks=174, retained_per_field_bytes=checked,
        retained_target_ids_inks=260, changed_target_count=len(changed), changed_target_ids=changed,
        cold_exact_array_keys=cold, only_config_change='seed_placement_by_part.1',
        scope='Secondary software contract; actual spacing, coverage and edit response gate application')


def independent_face_bands(mesh):
    """Classify triangles using plane/cone equations, not face index ordering."""
    triangles = mesh['vertices'][mesh['faces']]
    result = np.full(len(triangles), -1, dtype=np.int32)
    for face in np.flatnonzero(mesh['parts'] == 1):
        tri = triangles[face]
        radius, y = np.hypot(tri[:, 0], tri[:, 2]), tri[:, 1]
        top = np.all(np.abs(y-2.35) < 1e-9)
        bottom = np.all(np.abs(y-1.4) < 1e-9)
        outer = np.all(np.abs(radius-(.85-.33*(y-1.4)/.95)) < 1e-9)
        inner = np.all(np.abs(radius-(.815-.33*(y-1.4)/.95)) < 1e-9)
        candidates = [band for band, present in enumerate((outer, top, inner, bottom)) if present]
        require(len(candidates) == 1, 'ambiguous analytic triangle profile band')
        result[face] = candidates[0]
    return result


def audit_recipes(unit):
    old = strokes(unit/'outputs/baseline/strokes.npz')
    new = strokes(unit/'outputs/edited/strokes.npz')
    mesh = load_npz(unit/'outputs/baseline/mesh.npz')
    tri = mesh['vertices'][mesh['faces']]
    bands = independent_face_bands(mesh)
    area = .5*np.linalg.norm(np.cross(tri[:, 1]-tri[:, 0], tri[:, 2]-tri[:, 0]), axis=1)
    faces = np.flatnonzero(mesh['parts'] == 1)
    probabilities = area[faces]/area[faces].sum()
    rng = np.random.default_rng(np.random.SeedSequence([1729, 1]))
    original, original_anchors = [], {}
    for index in range(260):
        face = int(rng.choice(faces, p=probabilities))
        q = rng.random(2)
        root = np.sqrt(q[0])
        bary = np.array([1-root, root*(1-q[1]), root*q[1]])
        sid = f'p1:seed{index:04d}:layer0'
        require(sid in old, 'missing original shade ID')
        hit = (old[sid]['faces'] == face) & np.all(np.abs(old[sid]['bary']-bary) <= 1e-12, axis=1)
        require(hit.any(), 'baseline lacks independent original seed: '+sid)
        original.append(dict(id=sid, band=int(bands[face]), ink=old[sid]['ink']))
        original_anchors[sid] = dict(face=face, bary=bary, band=int(bands[face]))
    retained = {sid: row for sid, row in old.items() if row['part'] != 1}
    old_target = {sid: row for sid, row in old.items() if row['part'] == 1}
    new_target = {sid: row for sid, row in new.items() if row['part'] == 1}
    expected_lineage = dict(parent_asset_sha256=sha(unit/'inputs/asset.json'),
        parent_strokes_sha256=sha(ORIGIN/'strokes.npz'),
        parent_target_revision=part_revision(old_target), non_target_revision=part_revision(retained),
        target_identity='Original seed IDs retained; all relocated targets are NEW geometry revisions',
        target_path_revision=part_revision(new_target))
    expected_placement = dict(method='band_anisotropic_farthest_v1', candidate_multiplier=64,
        minimum_candidates=256, rng_entropy=[1729, 11], circumferential_scale_world=.32,
        transverse_scale_world=.08, initial='nearest(theta=0,profile_t=.5)',
        tie='lowest_candidate_index', band_names=['outer', 'top_rim', 'inner', 'bottom_rim'])
    expected = dict(schema='shade_spacing_recipe_v1', part=1, style='mixed', seed=1729,
        count=260, length_world=.32, step_world=.015, angle_deg=0., placement=expected_placement,
        numpy_version=np.__version__, original_seed_identity=original, lineage=expected_lineage,
        ink_policy='retain original per-ID assigned ink; no normal/light recalculation')
    parent = json.loads((unit/'inputs/asset.json').read_text())
    for key in ('recipe', 'path_lineage', 'mesh', 'strokes', 'config'):
        parent.pop(key, None)
    expected['baseline_manifest'] = parent
    expected['baseline_config'] = json.loads((unit/'outputs/baseline/config.json').read_text())
    recipe_records = {}
    for name in ('edited', 'cold_regenerate', 'cold_replay', 'cold_request'):
        folder = unit/name if name == 'cold_request' else unit/'outputs'/name
        recipe_path = folder/'recipe.json'
        recipe = json.loads(recipe_path.read_text())
        for key, value in expected.items():
            require(recipe.get(key) == value, name+' recipe field differs: '+key)
        files = {key: recipe_file(recipe_path, recipe.get(key), key)
                 for key in ('mesh', 'retained', 'config')}
        require(assert_strokes_equal(retained, strokes(files['retained']), name+' recipe retained') == 174,
                'recipe retained count differs')
        arrays_equal(load_npz(files['mesh']), load_npz(ORIGIN/'mesh.npz'), name+' recipe mesh')
        require(json.loads(files['config'].read_text()) ==
                json.loads((unit/'outputs/edited/config.json').read_text()), name+' recipe config differs')
        required_sources = ('spacing_cli.py', 'length_cli.py', 'common.py', 'asset_cli.py', 'renderer.py',
                            'legacy/core.py', 'legacy/core_walk_v2.py')
        require(set(recipe['generator_sha256']) == set(required_sources), 'recipe generator source set differs')
        for source in required_sources:
            path = (WORK/'experiments/partwise_sketch_hatching'/source.split('/')[-1]
                    if source.startswith('legacy/') else WORK/'experiments/partwise_sketch_hatching_v02'/source)
            require(recipe['generator_sha256'][source] == sha(path), 'generator SHA differs: '+source)
        if name == 'cold_request':
            allowed = {recipe_path.resolve(), *(Path(p).resolve() for p in files.values())}
            require(all(path.is_relative_to(folder.resolve()) for path in allowed), 'cold request not self-contained')
            require({path.resolve() for path in folder.rglob('*') if path.is_file()} == allowed,
                    'cold request contains target-path cache or unrelated files')
        else:
            manifest_path = folder/'asset.json'
            manifest = json.loads(manifest_path.read_text())
            require(recipe_file(manifest_path, manifest.get('recipe'), 'recipe') == recipe_path.resolve(),
                    'asset does not bind its own recipe')
            require(manifest['path_lineage'] == expected_lineage, 'asset lineage differs')
        recipe_records[name] = dict(path=str(recipe_path), sha256=sha(recipe_path), files=files)
    original_counts = {str(b): sum(row['band'] == b for row in original) for b in range(4)}
    audit = json.loads((unit/'outputs/edited/SEED_AUDIT.json').read_text())
    require(audit['original_band_counts'] == original_counts, 'reported original counts differ')
    records = audit['strokes']
    require(len(records) == 260 and {row['id'] for row in records} == set(new_target), 'seed audit IDs differ')
    actual_counts = {str(b): 0 for b in range(4)}
    crossing, seed_band_changes, checked = [], [], []
    for row in records:
        sid, face = row['id'], row['seed_face']
        bary = np.asarray(row['seed_bary'])
        require(isinstance(face, int) and 0 <= face < len(bands) and bands[face] >= 0,
                'invalid reported relocated seed face')
        require(bary.shape == (3,) and np.isfinite(bary).all() and bary.min() >= -1e-12
                and abs(bary.sum()-1) <= 1e-10, 'invalid reported seed bary')
        actual_band = int(bands[face])
        actual_counts[str(actual_band)] += 1
        require(row['seed_band'] == actual_band, 'reported seed band differs from independent geometry')
        if actual_band != original_anchors[sid]['band']:
            seed_band_changes.append(sid)
        hit = (new[sid]['faces'] == face) & np.all(np.abs(new[sid]['bary']-bary) <= 1e-12, axis=1)
        require(hit.any(), 'saved relocated path lacks its declared seed: '+sid)
        path_bands = sorted(set(map(int, bands[new[sid]['faces']])))
        require(row['path_bands'] == path_bands, 'reported path bands differ from geometry')
        if path_bands != [actual_band]:
            crossing.append(sid)
        metadata = row['seed_metadata']
        require(metadata['face'] == face and np.array_equal(metadata['bary'], bary)
                and metadata['band'] == actual_band, 'seed metadata mismatch')
        checked.append(dict(id=sid, original_band=original_anchors[sid]['band'],
            seed_band=actual_band, path_bands=path_bands, seed_face=face, seed_bary=bary))
    require(sorted(audit['crossing_ids']) == sorted(crossing), 'producer crossing IDs differ from geometry')
    cold_audit = json.loads((unit/'outputs/cold_regenerate/SEED_AUDIT.json').read_text())
    require(cold_audit == audit, 'cold regenerated seed audit differs')
    return dict(recipes=recipe_records, original_band_counts=original_counts,
        relocated_seed_band_counts=actual_counts, seed_band_changed_ids=seed_band_changes,
        profile_crossing_ids=crossing, records=checked,
        profile_band_go=bool(actual_counts == original_counts and not seed_band_changes and not crossing),
        cold_request_without_target_path_cache=True,
        scope='Independent seed identity replay and plane/cone face classification; no path generator execution')


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
        expected_parts = [1] if name in ('edited', 'cold_regenerate') else []
        require(row['regenerated_parts'] == expected_parts, name+' regenerated parts differ')
        generation, first, complete = (float(row[key]) for key in
            ('regeneration_seconds', 'command_to_first_preview_seconds', 'command_to_all_previews_seconds'))
        require(np.isfinite([generation, first, complete]).all() and 0 <= generation < first <= complete,
                name+' invalid latency')
        require(generation > 0 if expected_parts else generation == 0, name+' timing mismatch')
        require(set(row['per_view_seconds']) == set(map(str, VIEWS)), name+' cameras differ')
        if name == 'cold_regenerate':
            require(Path(row['source']).resolve() == (unit/'cold_request/recipe.json').resolve(),
                    'cold regenerate source differs')
        if name == 'cold_replay':
            require(Path(row['source']).resolve() == (unit/'outputs/edited/asset.json').resolve(),
                    'cold replay source differs')
        rows[name] = dict(operation=operation, regeneration_seconds=generation,
            command_to_first_preview_seconds=first, command_to_all_previews_seconds=complete,
            per_view_seconds=row['per_view_seconds'])
    return dict(bundles=rows, scope='One actual CPU invocation per operation; no FPS claim')


def validate(unit):
    unit = unit.resolve()
    require(unit == DEFAULT_UNIT.resolve(), 'validator writes only current unit011')
    start = time.perf_counter()
    checks, evidence = {}, {}
    metrics = dict(stills=[], frames=[], frozen_thresholds=THRESHOLDS,
        metric_scope='Actual PNG edit; analytic visible shade cells; actual isolated rendered stroke spacing')

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
        require(protocol['source_asset_sha256'] == sha(ORIGIN/'asset.json'), 'origin SHA differs')
        for filename, digest in protocol['inputs'].items():
            require(sha(filename) == digest, 'explicit input differs: '+filename)
        _, source_files = read_asset(unit/'inputs/asset.json')
        for key in ('mesh', 'strokes', 'config'):
            extension = '.json' if key == 'config' else '.npz'
            require(sha(source_files[key]) == sha(ORIGIN/(key+extension)), 'frozen input differs: '+key)
        gates, cov = protocol['evaluation']['gates'], protocol['evaluation']['coverage']
        for key in ('target_part', 'target_inside_L1_min_exclusive', 'far_other_fraction_max',
                    'far_background_fraction_max', 'boundary_band_px',
                    'every_part_support_pixels_min_exclusive'):
            require(gates[key] == THRESHOLDS[key], 'frozen edit gate differs: '+key)
        require(gates['hatch_support_threshold'] == .1 and gates['full_shape_margin_px_min'] == 2,
                'frozen ink/whole-shape threshold differs')
        require(cov['height_edges_world'] == HEIGHT_EDGES, 'frozen height cells differ')
        require(cov['azimuth_edges_radians'] == AZIMUTH_EDGES, 'frozen angular cells differ')
        for key in ('minimum_eligible_pixels', 'minimum_support_pixels', 'minimum_support_fraction'):
            require(cov[key] == THRESHOLDS[key], 'frozen coverage threshold differs: '+key)
        for key in ('distance_manhattan_px', 'close_fraction_ratio_max',
                    'ink_mass_ratio_min', 'ink_mass_ratio_max'):
            require(protocol['evaluation']['spacing'][key] == THRESHOLDS[key],
                    'frozen spacing threshold differs: '+key)
        require(protocol['media']['orbit']['frames'] == 24 and protocol['media']['zoom']['frames'] == 16,
                'frozen trajectory lengths differ')
        return dict(files=len(lock['files']), protocol_sha256=sha(unit/'PROTOCOL.json'))

    check('frozen_source_and_input_sha256', lock_check)
    for name in BUNDLES:
        check('explicit_bundle_'+name, lambda name=name: audit_bundle(unit, name))
    check('target_only_seed_placement_retained174_and_cold_arrays', lambda: audit_spacing_contract(unit))
    check('actual_operation_receipts_and_latency', lambda: audit_receipts(unit))
    # The independent recipe and seed-band audit is added below; no generation is executed.
    check('recipe_and_profile_band_contract', lambda: audit_recipes(unit))
    reference_dir = unit/'references'
    reference_dir.mkdir(exist_ok=True)
    for azimuth in VIEWS:
        def view_action(azimuth=azimuth):
            before_dir, after_dir = (unit/'outputs'/name for name in ('baseline', 'edited'))
            cfg = json.loads((before_dir/'config.json').read_text())
            mesh = load_npz(before_dir/'mesh.npz')
            camera = core.camera(azimuth, 20, 4.5, SIZE, 600)
            depth, labels = core.analytic_reference(cfg['asset'], camera)
            height, angle, cells = shade_cells(depth, labels, camera)
            ref = reference_dir/f'{azimuth:03}.npz'
            np.savez_compressed(ref, depth=depth, parts=labels, world_y=height,
                                world_azimuth_radians=angle, **cells, **edit_regions(labels))
            before, old, _ = read_render(before_dir/'renders'/f'{azimuth:03}', camera)
            after, new, _ = read_render(after_dir/'renders'/f'{azimuth:03}', camera)
            old_support, new_support = footprint(old['hatch'], labels), footprint(new['hatch'], labels)
            all_parts = all(old_support[str(part)]['support_pixels'] > 0
                            and new_support[str(part)]['support_pixels'] > 0 for part in PARTS)
            old_cov, new_cov = coverage(old['hatch'], labels, cells), coverage(new['hatch'], labels, cells)
            edit, shape = edit_metrics(before, after, labels), whole_shape(labels, mesh['vertices'], camera)
            ratio = new_support['1']['hatch_ink_mass']/max(old_support['1']['hatch_ink_mass'], 1e-15)
            row = dict(azimuth=azimuth, edit=edit, baseline_footprint=old_support,
                candidate_footprint=new_support, baseline_shade_coverage=old_cov,
                candidate_shade_coverage=new_cov, all_three_parts_nonempty=bool(all_parts),
                whole_shape=shape, shade_hatch_ink_ratio=ratio, ink_mass_ratio_go=bool(.8 <= ratio <= 1.25),
                regression={key+'_unchanged': bool(np.array_equal(old[key], new[key]))
                            for key in ('contours', 'rings', 'depth', 'parts')},
                cold={}, controls=controls(before, after, labels, cells, new['hatch']),
                reference_mask_path=str(ref), reference_mask_sha256=sha(ref))
            metrics['stills'].append(row)
            row['spacing'] = {name: read_probe(unit, name, azimuth, labels, actual)
                              for name, actual in (('baseline', old), ('edited', new))}
            bs, es = row['spacing']['baseline'], row['spacing']['edited']
            row['spacing']['descriptive_close_fraction_ratio'] = (
                es['close_support_fraction']/max(bs['close_support_fraction'], 1e-15))
            row['quantitative_go_without_pooled_spacing'] = bool(
                edit['go'] and all_parts and shape['go'] and new_cov['go'] and row['ink_mass_ratio_go'])
            for name in ('cold_regenerate', 'cold_replay'):
                directory = unit/'outputs'/name
                replay, repeated, _ = read_render(directory/'renders'/f'{azimuth:03}', camera)
                row['cold'][name] = dict(display_png_pixels_exact=bool(np.array_equal(after, replay)),
                    display_png_file_sha256_exact=sha(after_dir/'renders'/f'{azimuth:03}.png') ==
                        sha(directory/'renders'/f'{azimuth:03}.png'),
                    saved_layers_exact={key: bool(np.array_equal(new[key], repeated[key]))
                        for key in ('image', 'hatch', 'depth', 'parts', 'contours', 'rings')})
            require(row['controls']['passed'], 'metric sensitivity failed; raw row retained')
            require(all(row['regression'].values()), 'nonhatch regression failed; raw row retained')
            require(all(row['spacing'][name]['duplicate_raster_control']['passed']
                        for name in ('baseline', 'edited')), 'duplicate-raster sensitivity failed')
            for name, cold in row['cold'].items():
                require(cold['display_png_pixels_exact'] and cold['display_png_file_sha256_exact']
                        and all(cold['saved_layers_exact'].values()), name+' cold output differs')
            return dict(azimuth=azimuth, independent_analytic_mask=True,
                quantitative_go_without_pooled_spacing=row['quantitative_go_without_pooled_spacing'],
                controls_passed=True, cold_regenerate_and_replay_png_exact=True)
        check(f'actual_images_coverage_spacing_controls_cold_{azimuth:03}', view_action)

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
                    sequence+' trajectory differs')
                require(row['asset_sha256'] == sha(unit/'outputs/edited/asset.json'), sequence+' asset differs')
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
                height, angle, cells = shade_cells(depth, labels, camera)
                ref = directory/f'{index:04}.npz'
                np.savez_compressed(ref, depth=depth, parts=labels, world_y=height,
                                    world_azimuth_radians=angle, **cells)
                cov = coverage(rendered['hatch'], labels, cells)
                support_rows = footprint(rendered['hatch'], labels)
                all_parts = all(support_rows[str(part)]['support_pixels'] > 0 for part in PARTS)
                shape = whole_shape(labels, mesh['vertices'], camera)
                metrics['frames'].append(dict(sequence=sequence, frame=index,
                    camera_parameters=item, footprint=support_rows, shade_coverage=cov,
                    all_three_parts_nonempty=bool(all_parts), whole_shape=shape,
                    quantitative_go=bool(cov['go'] and all_parts and shape['go']),
                    reference_mask_path=str(ref), reference_mask_sha256=sha(ref),
                    image_sha256=sha(unit/'frames'/sequence/f'{index:04}.png')))
        return dict(frames=len(metrics['frames']), all_saved_pngs_checked=True,
            geometric_cells_recomputed_each_frame=True,
            scope='Whole-object support across frames; not temporal correspondence or flicker')
    check('all40_orbit_zoom_actual_images_analytic_cells', trajectory_action)
    complete = len(metrics['stills']) == len(VIEWS)
    frames_complete = len(metrics['frames']) == 40
    spacing_complete = complete and all('spacing' in row for row in metrics['stills'])
    pooled = {}
    if spacing_complete:
        for name in ('baseline', 'edited'):
            total = sum(row['spacing'][name]['individual_support_pixels'] for row in metrics['stills'])
            close = sum(row['spacing'][name]['close_support_pixels'] for row in metrics['stills'])
            overlap = sum(row['spacing'][name]['exact_overlap_support_pixels'] for row in metrics['stills'])
            pooled[name] = dict(individual_support_pixels=total, close_support_pixels=close,
                close_support_fraction=close/max(total, 1), exact_overlap_support_pixels=overlap,
                exact_overlap_support_fraction=overlap/max(total, 1))
        old, new = pooled['baseline'], pooled['edited']
        pooled['close_fraction_ratio'] = new['close_support_fraction']/max(old['close_support_fraction'], 1e-15)
        pooled['go'] = bool(old['individual_support_pixels'] > 0 and old['close_support_fraction'] > 0
                           and new['individual_support_pixels'] > 0 and pooled['close_fraction_ratio'] <= .8)
    metrics['pooled_spacing'] = pooled
    science = dict(
        profile_band_go=bool(evidence.get('recipe_and_profile_band_contract', {}).get('profile_band_go', False)),
        local_edit_go_four_stills=complete and all(row['edit']['go'] for row in metrics['stills']),
        shade_cells_go_four_stills=complete and all(row['candidate_shade_coverage']['go'] for row in metrics['stills']),
        all_parts_nonempty_four_stills=complete and all(row['all_three_parts_nonempty'] for row in metrics['stills']),
        whole_shape_visible_four_stills=complete and all(row['whole_shape']['go'] for row in metrics['stills']),
        ink_mass_go_four_stills=complete and all(row['ink_mass_ratio_go'] for row in metrics['stills']),
        rendered_pooled_spacing_go=spacing_complete and pooled.get('go', False),
        metric_controls_go_four_stills=complete and all(row['controls']['passed'] for row in metrics['stills']),
        shade_cells_go_all40_frames=frames_complete and all(row['shade_coverage']['go'] for row in metrics['frames']),
        all_parts_nonempty_all40_frames=frames_complete and all(row['all_three_parts_nonempty'] for row in metrics['frames']),
        whole_shape_visible_all40_frames=frames_complete and all(row['whole_shape']['go'] for row in metrics['frames']),
        quantitative_go_all40_frames=frames_complete and all(row['quantitative_go'] for row in metrics['frames']))
    quantitative_go = all(science.values())
    science.update(quantitative_application_go=bool(quantitative_go),
        shade_spacing_visual_go='REQUIRES_ACTUAL_IMAGE_REVIEW', whole_object_visual='REQUIRES_ACTUAL_IMAGE_REVIEW',
        inherited_unit004_density_contract='NO_GO_RETAINED_NOT_RETESTED', reconstructed_input='BLOCKED',
        H1_H2='NOT_TESTED', temporal_correspondence='NOT_NEWLY_TESTED', physical_hidden_surface_coverage='UNMEASURED')
    valid = all(row['passed'] for row in checks.values())
    result = dict(verdict='VALID' if valid else 'INVALID',
        scientific_verdict=('GO' if quantitative_go else 'NO_GO') if valid else 'INVALID',
        checks=checks, evidence=evidence, scientific_gates=science, seconds=time.perf_counter()-start,
        scope='Independent saved-file/actual-PNG/analytic-mask/raster-support audit; no renderer execution',
        limitations=['One exposed authored GT lamp; no reconstructed or multi-object conclusion.',
            'Coverage cells include visible analytic shade only; tiny cells abstain; hidden surfaces unmeasured.',
            'Two-pixel Manhattan proximity measures close projected stroke support, not geodesic spacing.',
            'Ink-mass preservation is a bounded tone guard, not a physical shading-fidelity guarantee.',
            '40 frames measure coverage; no new per-stroke temporal correspondence claim.',
            'Path identity and cold replay are secondary to image response, isolation, coverage and spacing.',
            'Inherited unit004 density NO_GO,17 hidden-profile cases and temporal exclusions remain.'])
    metrics['scientific_gates'] = science
    metrics['validation_verdict'] = result['verdict']
    metrics['scientific_verdict'] = result['scientific_verdict']
    write_json(unit/'METRICS.json', metrics)
    write_json(unit/'INDEPENDENT_VALIDATION.json', result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--unit', type=Path, default=DEFAULT_UNIT)
    result = validate(parser.parse_args().unit)
    print(json.dumps(native(dict(verdict=result['verdict'], scientific_verdict=result['scientific_verdict'],
        checks=result['checks'], scientific_gates=result['scientific_gates'])), allow_nan=False))
    return 0 if result['verdict'] == 'VALID' else 1


if __name__ == '__main__':
    raise SystemExit(main())
