"""Independent audit of one frozen stem-only regeneration and three P1 videos.

No producer or renderer is imported. Previously audited file/media helpers are
reused, while target masks, regenerated paths, and whole-object gates are checked
here. A scientifically unsuccessful candidate can still have VALID artifacts.
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
import json
from pathlib import Path
import subprocess
import sys
import time

import numpy as np
from scipy import ndimage

WORK = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(WORK))
from experiments.partwise_sketch_hatching import core
from experiments.partwise_sketch_hatching_v02.validate_unit003 import (
    DEFAULT_FFMPEG, FRAMES, INK_THRESHOLD, PARTS, SIZE, VIEWS, decode_video,
    footprint, independent_reference, load_npz, native, read_render, rgb, sha,
    strokes, write_json,
)

DEFAULT_UNIT = Path('/mnt/hdd1/u00134/partwise_sketch_hatching_p1_v02/units/unit_004')
THRESHOLDS = {
    'target_part': 2, 'target_inside_L1_min_exclusive': 10.,
    'far_other_fraction_max': .02, 'far_background_fraction_max': .02,
    'boundary_band_px': 2, 'hatch_support_ink_threshold': INK_THRESHOLD,
    'candidate_stem_ink_ratio_min': .15, 'candidate_stem_ink_ratio_max': .75,
    'candidate_stem_support_ratio_min': .15,
    'candidate_stem_support_fraction_min': .05,
    'every_part_support_pixels_min_exclusive': 0, 'whole_shape_margin_px_min': 2,
}


def edit_metrics(before, after, labels):
    change = np.abs(after - before)
    target = labels == 2
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


def whole_shape(labels, vertices, camera):
    yy, xx = np.nonzero(labels > 0)
    if len(xx):
        mask_margins = dict(left=int(xx.min()), right=int(SIZE - 1 - xx.max()),
                            top=int(yy.min()), bottom=int(SIZE - 1 - yy.max()))
    else:
        mask_margins = dict(left=-1, right=-1, top=-1, bottom=-1)
    uv, depth = core.project(vertices, camera)
    projected_margins = dict(left=float(uv[:, 0].min()),
                             right=float(SIZE - 1 - uv[:, 0].max()),
                             top=float(uv[:, 1].min()),
                             bottom=float(SIZE - 1 - uv[:, 1].max()))
    go = (len(xx) > 0 and bool(np.all(depth > 0))
          and min(mask_margins.values()) >= 2
          and min(projected_margins.values()) >= 2)
    return dict(mask_margins_px=mask_margins, mesh_projection_margins_px=projected_margins,
                all_mesh_vertices_in_front=bool(np.all(depth > 0)), go=bool(go),
                scope='Independent analytic foreground mask plus all saved mesh vertices; no image cropping')


def stem_height_coverage(hatch, labels):
    yy, _ = np.nonzero(labels == 2)
    if not len(yy):
        return dict(bins=[], scope='No visible stem pixels; diagnostic only')
    edges = np.linspace(int(yy.min()), int(yy.max()) + 1, 5)
    rows = np.arange(SIZE)[:, None]
    bins = []
    for index, (low, high) in enumerate(zip(edges[:-1], edges[1:])):
        mask = (labels == 2) & (rows >= low) & (rows < high)
        area = int(mask.sum())
        support = int(np.count_nonzero((hatch >= INK_THRESHOLD) & mask))
        bins.append(dict(bin=index, pixel_y_range=[float(low), float(high)],
                         visible_mask_pixels=area, support_pixels=support,
                         support_fraction=support / max(area, 1),
                         hatch_ink_mass=float(hatch[mask].sum()), nonempty=support > 0))
    return dict(bins=bins, scope='Four equal projected-height bins of visible independent stem mask; descriptive, no new gate')


def pair_metrics(before, after, old_layers, new_layers, labels, vertices, camera):
    old = footprint(old_layers['hatch'], labels)
    new = footprint(new_layers['hatch'], labels)
    old_stem, new_stem = old['2'], new['2']
    baseline_nonempty = old_stem['hatch_ink_mass'] > 0 and old_stem['support_pixels'] > 0
    ink_ratio = new_stem['hatch_ink_mass'] / max(old_stem['hatch_ink_mass'], 1e-15)
    support_ratio = new_stem['support_pixels'] / max(old_stem['support_pixels'], 1)
    coverage_go = (baseline_nonempty and .15 <= ink_ratio <= .75 and support_ratio >= .15
                   and new_stem['support_fraction'] >= .05)
    all_parts = all(new[str(part)]['support_pixels'] > 0 for part in PARTS)
    edit = edit_metrics(before, after, labels)
    shape = whole_shape(labels, vertices, camera)
    regression = {
        'contours_unchanged': np.array_equal(old_layers['contours'], new_layers['contours']),
        'rings_unchanged': np.array_equal(old_layers['rings'], new_layers['rings']),
    }
    return dict(edit=edit, baseline_footprint=old, candidate_footprint=new,
                stem_ink_ratio=ink_ratio, stem_support_ratio=support_ratio,
                baseline_stem_nonempty=bool(baseline_nonempty),
                stem_coverage_go=bool(coverage_go), all_three_parts_nonempty=bool(all_parts),
                whole_shape=shape, regression=regression,
                stem_height_coverage=dict(baseline=stem_height_coverage(old_layers['hatch'], labels),
                                          candidate=stem_height_coverage(new_layers['hatch'], labels)),
                quantitative_go=bool(edit['go'] and coverage_go and all_parts and shape['go']
                                     and all(regression.values())),
                scope='Actual rendered image and hatch-layer gates; no monotonic thinning assumption')


def audit_paths(unit, cfg):
    style = json.loads((unit / 'STYLE.json').read_text())
    expected_style = dict(part=2, count=8, y_min=.20, y_max=1.55,
                          first_sector=1, sector_fraction=.37, angular_stride=12,
                          screen_width_px=1.,
                          algorithm='uniform authored-cylinder sectors + v2 axial walk')
    if style != expected_style or cfg['asset']['angular_segments'] != 96:
        raise AssertionError('style differs from frozen bounded eight-line cylinder prescription')
    baseline = strokes(unit / 'inputs/baseline.npz')
    selected = strokes(unit / 'inputs/selected.npz')
    inherited = strokes(unit.parent / 'unit_003/inputs/selected.npz')
    if set(baseline) != set(inherited):
        raise AssertionError('baseline stroke IDs differ from immutable unit003 candidate')
    for sid, old in inherited.items():
        new = baseline[sid]
        if (old['part'] != new['part'] or old['ink'] != new['ink']
                or not np.array_equal(old['faces'], new['faces'])
                or not np.array_equal(old['bary'], new['bary'])):
            raise AssertionError(f'inherited baseline stroke changed: {sid}')
    old_other = {sid for sid, stroke in baseline.items() if stroke['part'] != 2}
    new_other = {sid for sid, stroke in selected.items() if stroke['part'] != 2}
    if old_other != new_other or len(old_other) != 410:
        raise AssertionError('non-target IDs/count changed; expected all410 inherited paths')
    for sid in sorted(old_other):
        old, new = baseline[sid], selected[sid]
        if (old['part'] != new['part'] or old['ink'] != new['ink']
                or not np.array_equal(old['faces'], new['faces'])
                or not np.array_equal(old['bary'], new['bary'])):
            raise AssertionError(f'non-target path or ink changed: {sid}')
    old_stems = {sid for sid, stroke in baseline.items() if stroke['part'] == 2}
    new_stems = {sid for sid, stroke in selected.items() if stroke['part'] == 2}
    if len(old_stems) != 48 or len(new_stems) != 8:
        raise AssertionError('expected48 inherited and8 regenerated stem strokes')
    if old_stems & new_stems:
        raise AssertionError('regenerated stem IDs must declare changed identity')
    mesh = load_npz(unit / 'inputs/lamp_mesh.npz')
    tri = mesh['vertices'][mesh['faces']]
    rows, angles, distances = [], [], []
    expected_ids = {f'p2:axialv1_{index:04d}:layer0' for index in range(8)}
    if new_stems != expected_ids:
        raise AssertionError('regenerated stem IDs differ from frozen prescription')
    for index, sid in enumerate(sorted(new_stems)):
        stroke = selected[sid]
        faces, bary = stroke['faces'], stroke['bary']
        if len(faces) < 2 or bary.shape != (len(faces), 3):
            raise AssertionError(f'insufficient or malformed anchored points: {sid}')
        if (not np.isfinite(bary).all() or np.any(bary < -1e-10)
                or np.any(bary > 1 + 1e-10)
                or not np.allclose(bary.sum(axis=1), 1., atol=1e-10, rtol=0)):
            raise AssertionError(f'invalid barycentric anchors: {sid}')
        if np.any(faces < 0) or np.any(faces >= len(tri)) or not np.all(mesh['parts'][faces] == 2):
            raise AssertionError(f'stem anchor leaves part2: {sid}')
        if not np.isfinite(stroke['ink']) or not 0 < stroke['ink'] <= 1:
            raise AssertionError(f'invalid stem ink: {sid}')
        points = np.einsum('ni,nij->nj', bary, tri[faces])
        sector = 1 + 12 * index
        ends = 2 * np.pi * np.array([sector, sector + 1]) / 96
        expected_xz = .075 * (.63 * np.array([np.cos(ends[0]), np.sin(ends[0])])
                              + .37 * np.array([np.cos(ends[1]), np.sin(ends[1])]))
        if not np.allclose(points[:, (0, 2)], expected_xz, atol=1e-10, rtol=0):
            raise AssertionError(f'stem angular phase/chord interpolation differs: {sid}')
        first_triangle = tri[faces[0]]
        normal = np.cross(first_triangle[1] - first_triangle[0], first_triangle[2] - first_triangle[0])
        normal = normal / np.linalg.norm(normal)
        light = np.array([-1., 2., 1.]) / np.sqrt(6.)
        expected_ink = .30 + .55 * (1 - max(0., float(normal @ light)))
        if not np.isclose(stroke['ink'], expected_ink, atol=1e-12, rtol=0):
            raise AssertionError(f'stem ink differs from fixed world-light rule: {sid}')
        length = float(np.linalg.norm(np.diff(points, axis=0), axis=1).sum())
        if not np.isclose(length, 1.35, atol=1e-9, rtol=0):
            raise AssertionError(f'stem world length not1.35: {sid}: {length}')
        if not np.allclose(points[:, (0, 2)], points[0, (0, 2)], atol=1e-10, rtol=0):
            raise AssertionError(f'stem is not axial: {sid}')
        if not (np.isclose(points[:, 1].min(), .20, atol=1e-9, rtol=0)
                and np.isclose(points[:, 1].max(), 1.55, atol=1e-9, rtol=0)):
            raise AssertionError(f'stem endpoints differ from frozen interval: {sid}')
        dy = np.diff(points[:, 1])
        if not (np.all(dy >= -1e-10) or np.all(dy <= 1e-10)):
            raise AssertionError(f'stem path backtracks: {sid}')
        angle = float(np.arctan2(points[0, 2], points[0, 0]) % (2 * np.pi))
        angles.append(angle)
        radius = np.hypot(points[:, 0], points[:, 2])
        # All points lie inside the frozen cylinder's axial range. The nearest
        # infinite-cylinder distance is therefore the independent surface error.
        radial_distance = np.abs(radius - .075)
        distances.extend(radial_distance.tolist())
        rows.append(dict(stroke_id=sid, anchored_points=len(points), world_length=length,
                         angular_position_radians=angle, ink=stroke['ink'],
                         independent_cylinder_distance_max=float(radial_distance.max())))
    angles = np.sort(angles)
    gaps = np.diff(np.r_[angles, angles[0] + 2 * np.pi])
    if not np.allclose(gaps, 2 * np.pi / 8, atol=1e-9, rtol=0):
        raise AssertionError('new stem paths are not uniformly spaced around cylinder')
    distance = np.asarray(distances)
    diagonal = float(np.linalg.norm(np.ptp(mesh['vertices'], axis=0)))
    return dict(baseline_strokes=len(baseline), candidate_strokes=len(selected),
                frozen_style_exact=True, angular_phase_and_ink_recomputed=True,
                non_target_strokes_exact=410, old_stem_strokes=48, new_stem_strokes=8,
                regenerated_stem_ids_disjoint=True, axial_world_length=1.35,
                angular_gap_radians=gaps, paths=rows,
                attachment=dict(samples=len(distance), mean_world=float(distance.mean()),
                                median_world=float(np.median(distance)),
                                p95_world=float(np.percentile(distance, 95)),
                                max_world=float(distance.max()),
                                p95_bbox_fraction=float(np.percentile(distance, 95) / diagonal),
                                scope='Distance to authored analytic cylinder r=.075; diagnostic GT upper bound'),
                regression_scope='Path identity is a secondary control; whole-object image gates are primary')


def controls(before, after, labels, row):
    noedit = edit_metrics(before, before, labels)
    distance = ndimage.distance_transform_edt(labels != 2)
    eligible = np.flatnonzero((labels == 1) & (distance > 2))
    if len(eligible) < 16:
        raise AssertionError('insufficient independent far-shade pixels for fixed injection')
    chosen = eligible[np.argsort(-after.ravel()[eligible], kind='stable')[:16]]
    injected = after.copy()
    injected.ravel()[chosen] = 0.
    fault = edit_metrics(before, injected, labels)
    shifted = np.ones_like(after)
    shifted[:, 3:] = after[:, :-3]
    drift = dict(horizontal_shift_px=3, no_drift_L1=0.,
                 drifted_image_L1=float(np.abs(after - shifted).sum()),
                 scope='Raster-shift sensitivity only; no correspondence or jitter claim')
    passed = (noedit['total_delta'] == 0 and not noedit['go']
              and fault['far_other_parts_fraction'] > .02
              and fault['far_other_parts_fraction'] > row['edit']['far_other_parts_fraction']
              and drift['drifted_image_L1'] > 0)
    return dict(no_edit=noedit, injected_far_shade=fault,
                injected_flat_pixel_indices=chosen, raster_drift=drift, passed=bool(passed))


def audit_video(unit, ffmpeg, name, sources):
    # Input-only invocation exposes the stored stream codec without writing or
    # decoding the media twice. FFmpeg returns1 because no output was requested.
    command = [ffmpeg, '-hide_banner', '-threads', '1', '-i', str(unit / 'videos' / f'{name}.mkv')]
    header = subprocess.run(command, capture_output=True, timeout=30)
    diagnostic = header.stderr.decode(errors='replace')
    if header.returncode != 1 or 'Video: ffv1' not in diagnostic:
        raise AssertionError(f'{name}: expected readable FFV1 input header, rc={header.returncode}')
    result = decode_video(unit, ffmpeg, name, sources)
    result.update(codec='ffv1', header_inspection_command=command,
                  header_inspection_returncode=header.returncode,
                  header_returncode_reason='Expected input-only FFmpeg invocation without output')
    return result


def validate(unit, ffmpeg):
    start = time.perf_counter()
    checks, evidence, science = {}, {}, {}
    metrics = dict(stills=[], orbit=[], zoom=[], frozen_thresholds=THRESHOLDS)

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
            rows.append(dict(path=filename, sha256=actual))
        if not rows:
            raise AssertionError('source/input lock is empty')
        return dict(count=len(rows), files=rows)

    check('source_and_input_sha256', lock_check)
    cfg = json.loads((unit / 'CONFIG.json').read_text())
    mesh = load_npz(unit / 'inputs/lamp_mesh.npz')
    check('independent_stem_anchors_and_non_target_regression', lambda: audit_paths(unit, cfg))

    def baseline_identity():
        previous = unit.parent / 'unit_003'
        files = [(unit / 'inputs/baseline.npz', previous / 'inputs/selected.npz'),
                 (unit / 'inputs/lamp_mesh.npz', previous / 'inputs/lamp_mesh.npz')]
        for azimuth in VIEWS:
            for suffix in ('.png', '.npz', '.json'):
                files.append((unit / 'stills' / f'baseline_{azimuth:03}{suffix}',
                              previous / 'stills' / f'candidate_{azimuth:03}{suffix}'))
        for index in range(FRAMES):
            for suffix in ('.png', '.npz', '.json'):
                files.append((unit / 'frames/baseline' / f'{index:04}{suffix}',
                              previous / 'frames/orbit' / f'{index:04}{suffix}'))
        rows = []
        for current, old in files:
            expected = sha(old)
            if sha(current) != expected:
                raise AssertionError(f'baseline differs from immutable unit003: {current}')
            rows.append(dict(path=current, source=old, sha256=expected))
        return dict(count=len(rows), exact_identity=True, files=rows)

    check('inherited_baseline_exact_file_identity', baseline_identity)

    def pair(name, key, camera, baseline, candidate, reference):
        labels = independent_reference(unit, cfg, camera, reference)
        before, old, _ = read_render(baseline, camera)
        after, new, _ = read_render(candidate, camera)
        row = pair_metrics(before, after, old, new, labels, mesh['vertices'], camera)
        row.update(key)
        metrics[name].append(row)
        return row, labels, before, after

    for azimuth in VIEWS:
        def still_action(azimuth=azimuth):
            camera = core.camera(azimuth, 20, 4.5, SIZE, 600)
            row, labels, before, after = pair(
                'stills', dict(azimuth=azimuth), camera,
                unit / 'stills' / f'baseline_{azimuth:03}',
                unit / 'stills' / f'candidate_{azimuth:03}',
                unit / 'stills' / f'reference_{azimuth:03}.npz')
            row['controls'] = controls(before, after, labels, row)
            if not row['controls']['passed']:
                raise AssertionError(f'metric sensitivity controls failed at azimuth{azimuth}; metrics retained')
            return dict(azimuth=azimuth, independent_mask_recomputed=True,
                        actual_image_measured=True, metric_controls_passed=True)
        check(f'still_{azimuth:03}_masks_layers_controls', still_action)

    for name in ('orbit', 'zoom'):
        previous = {}
        for index in range(FRAMES):
            def frame_action(name=name, index=index):
                azimuth = 15 * index if name == 'orbit' else 30
                distance = 4.5 if name == 'orbit' else 4.0 + 1.6 * (1 - np.cos(2 * np.pi * index / 24)) / 2
                camera = core.camera(azimuth, 20, distance, SIZE, 600)
                base_dir = 'baseline' if name == 'orbit' else 'zoom_baseline'
                row, labels, before, after = pair(
                    name, dict(frame=index, azimuth=azimuth, distance=distance), camera,
                    unit / 'frames' / base_dir / f'{index:04}',
                    unit / 'frames' / name / f'{index:04}',
                    unit / 'frames' / name / f'reference_{index:04}.npz')
                if previous:
                    union = (labels == 2) | (previous['labels'] == 2)
                    row['temporal_raw_L1_diagnostic'] = dict(
                        baseline_full=float(np.abs(before - previous['baseline']).sum()),
                        candidate_full=float(np.abs(after - previous['candidate']).sum()),
                        baseline_stem_union=float(np.abs(before - previous['baseline'])[union].sum()),
                        candidate_stem_union=float(np.abs(after - previous['candidate'])[union].sum()),
                        stem_union_pixels=int(union.sum()))
                previous.update(labels=labels, baseline=before, candidate=after)
                return dict(frame=index, independent_mask_recomputed=True, camera_checked=True)
            check(f'{name}_{index:04}_mask_layers_camera', frame_action)

    def trajectories():
        if len(metrics['orbit']) != 24 or len(metrics['zoom']) != 24:
            raise AssertionError('trajectory is missing measured frames')
        orbit = [row['azimuth'] for row in metrics['orbit']]
        zoom = np.array([row['distance'] for row in metrics['zoom']])
        expected_zoom = 4.0 + 1.6 * (1 - np.cos(2 * np.pi * np.arange(24) / 24)) / 2
        if orbit != list(range(0, 360, 15)) or not np.array_equal(zoom, expected_zoom):
            raise AssertionError('frozen orbit/zoom trajectories differ')
        if not (np.isclose(zoom[0], 4.) and np.isclose(zoom[12], 5.6)
                and np.all(np.diff(zoom[:13]) > 0) and np.all(np.diff(zoom[12:]) < 0)):
            raise AssertionError('zoom does not traverse prescribed outward-and-back distances')
        return dict(orbit_degrees=orbit, zoom_distances=zoom, resolution=[512, 512],
                    elevation_degrees=20, camera_records_checked_for_every_frame=True,
                    no_per_frame_style_change='fixed candidate path file and style source lock',
                    scope='Frozen camera paths and image responses; no jitter/flicker conclusion')

    check('fixed_orbit_and_zoom_trajectories', trajectories)
    for name in ('orbit', 'zoom'):
        check(f'complete_{name}_video_decode', lambda name=name: audit_video(
            unit, ffmpeg, name, [unit / 'frames' / name / f'{index:04}.png' for index in range(FRAMES)]))
    prescribed = [unit / 'stills/baseline_030.png'] * 12 + [unit / 'stills/candidate_030.png'] * 12
    edit_sources = [unit / 'frames/edit' / f'{index:04}.png' for index in range(FRAMES)]

    def edit_sources_check():
        for index, (saved, expected) in enumerate(zip(edit_sources, prescribed)):
            if not np.array_equal(rgb(saved), rgb(expected)):
                raise AssertionError(f'edit frame{index} differs from prescribed actual still')
        return dict(frames=24, first12='baseline_030', last12='candidate_030',
                    all_source_pngs_exact=True, transition='one actual discrete stem edit; no crossfade')

    check('edit_frame_sources_and_frozen_step', edit_sources_check)
    check('complete_edit_video_decode', lambda: audit_video(unit, ffmpeg, 'edit', edit_sources))

    for name, count in (('stills', 4), ('orbit', 24), ('zoom', 24)):
        rows = metrics[name]
        complete = len(rows) == count
        science[name + '_local_edit_go'] = complete and all(row['edit']['go'] for row in rows)
        science[name + '_stem_coverage_go'] = complete and all(row['stem_coverage_go'] for row in rows)
        science[name + '_whole_object_coverage_go'] = complete and all(
            row['all_three_parts_nonempty'] and row['whole_shape']['go'] for row in rows)
        science[name + '_secondary_render_regression_go'] = complete and all(
            all(row['regression'].values()) for row in rows)
        science[name + '_quantitative_go'] = complete and all(row['quantitative_go'] for row in rows)
        if rows:
            metrics[name + '_summary'] = dict(
                measured_frames=len(rows), expected_frames=count,
                quantitative_go_frames=sum(row['quantitative_go'] for row in rows),
                min_target_inside_L1=min(row['edit']['inside_delta'] for row in rows),
                stem_ink_ratio_min=min(row['stem_ink_ratio'] for row in rows),
                stem_ink_ratio_max=max(row['stem_ink_ratio'] for row in rows),
                stem_support_ratio_min=min(row['stem_support_ratio'] for row in rows),
                candidate_support_fraction_min=min(row['candidate_footprint']['2']['support_fraction'] for row in rows),
                max_far_other_edit_fraction=max(row['edit']['far_other_parts_fraction'] for row in rows),
                max_far_background_edit_fraction=max(row['edit']['far_background_fraction'] for row in rows))
    science['metric_controls_go_four_stills'] = (len(metrics['stills']) == 4 and all(
        row.get('controls', {}).get('passed', False) for row in metrics['stills']))
    science['all52_image_pairs_quantitative_go'] = all(
        science[name + '_quantitative_go'] for name in ('stills', 'orbit', 'zoom'))
    science.update(whole_object_P1_visual_go='REQUIRES_ACTUAL_IMAGE_REVIEW',
                   reconstructed_input='BLOCKED', H1_H2='NOT_TESTED',
                   independent_temporal_jitter='NOT_ESTABLISHED')
    result = dict(verdict='VALID' if all(row['passed'] for row in checks.values()) else 'INVALID',
                  checks=checks, scientific_gates=science, evidence=evidence,
                  seconds=time.perf_counter() - start,
                  scope='Independent images/masks/paths/media audit; no producer import or renderer call',
                  limitations=[
                      'One exposed GT lamp with authored parts and manual styles; no new independent object sample.',
                      'Analytic masks and mesh share authored shape parameters; no reconstructed-lamp claim.',
                      'Primitive equality is a secondary regression control, not the NPR application gate.',
                      'Coverage measures actual image support and ink, not surface coverage or target dark-tone fidelity.',
                      'Raw temporal L1 includes camera motion, occlusion and aliasing; no jitter/flicker claim.',
                      'Inherited17 hidden-profile observations and limited nine-ID temporal evidence remain unresolved.',
                  ])
    metrics.update(scientific_gates=science, validation_verdict=result['verdict'])
    write_json(unit / 'METRICS.json', metrics)
    write_json(unit / 'INDEPENDENT_VALIDATION.json', result)
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--unit', type=Path, default=DEFAULT_UNIT)
    parser.add_argument('--ffmpeg', default=DEFAULT_FFMPEG)
    args = parser.parse_args()
    if args.unit.resolve() != DEFAULT_UNIT.resolve():
        raise ValueError('this bounded validator writes only authorized unit_004')
    result = validate(args.unit, args.ffmpeg)
    print(json.dumps(native(dict(verdict=result['verdict'], checks=result['checks'],
                                 scientific_gates=result['scientific_gates'])), allow_nan=False))
    return 0 if result['verdict'] == 'VALID' else 1


if __name__ == '__main__':
    raise SystemExit(main())
