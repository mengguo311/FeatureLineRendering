"""Bounded actual-ink temporal audit using continuous analytic lathe rays.

This reference shares the authored lamp profile, never the renderer mesh,
visibility buffer or accepted fragments. It is a GT engineering diagnostic.
Visibility tolerance permits the disclosed mesh/continuous-profile mismatch.
Equal world-arclength midpoint observations retain their length weights, so a
short stroke does not acquire the influence of a long one by oversampling.
"""
import math
import numpy as np
from scipy.ndimage import distance_transform_edt, map_coordinates


PARAMETERS = dict(sample_step_world=.008, sample_min=8, sample_max=128,
                  boundary_band_px=2., depth_tolerance_world=.006,
                  profile_extent_px=2., profile_step_px=.25,
                  support_threshold=.05, ambiguity_radius_px=4.,
                  local_projected_arclength_px=4.)
GATES = dict(eligible_over_raw_visible_world_min=.20,
             centroid_abs_p95_px_max=.75, temporal_residual_p95_px_max=.75,
             missing_world_fraction_max=.02, common_visible_world_min_exclusive=0.)
CLASSES = ('visible', 'hidden', 'ambiguous', 'boundary', 'outside', 'unmeasured')


def native(value):
    if isinstance(value, dict):
        return {str(k): native(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [native(v) for v in value]
    if isinstance(value, np.ndarray):
        return native(value.tolist())
    if isinstance(value, np.generic):
        return native(value.item())
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


def _path(points):
    points = np.asarray(points, dtype=float)
    if points.ndim != 2 or points.shape[1] != 3 or len(points) < 2 or not np.isfinite(points).all():
        raise ValueError('A finite Nx3 path with at least two points is required')
    arc = np.r_[0., np.cumsum(np.linalg.norm(np.diff(points, axis=0), axis=1))]
    keep = np.r_[True, np.diff(arc) > 1e-12]
    points, arc = points[keep], arc[keep]
    if len(points) < 2 or arc[-1] <= 0:
        raise ValueError('A positive-length path is required')
    return points, arc


def sample_path(points):
    """Fixed midpoint quadrature; cap coarsens sampling, never truncates a path."""
    points, arc = _path(points)
    n = min(PARAMETERS['sample_max'], max(PARAMETERS['sample_min'],
            int(np.ceil(arc[-1] / PARAMETERS['sample_step_world']))))
    edge_arc = np.linspace(0., arc[-1], n + 1)
    middle = (edge_arc[:-1] + edge_arc[1:]) / 2
    interp = lambda ar: np.column_stack([np.interp(ar, arc, points[:, j]) for j in range(3)])
    return dict(world=interp(middle), edges=interp(edge_arc), world_weight=np.diff(edge_arc),
                world_arclength=middle, length_world=float(arc[-1]), count=n,
                capped=bool(np.ceil(arc[-1] / PARAMETERS['sample_step_world']) > n))


def project(points, camera):
    xyz = np.asarray(points) @ np.asarray(camera['R']).T + np.asarray(camera['t'])
    with np.errstate(divide='ignore', invalid='ignore'):
        uv = xyz[..., :2] / xyz[..., 2, None] * camera['focal'] + camera['center']
    return uv, xyz[..., 2]


def analytic_rays(asset, camera, uv):
    """Nearest continuous profile intersection at arbitrary screen coordinates.

    Rays have camera-z component one. The returned parameter is camera z,
    rather than Euclidean distance. No mesh or pixel-depth interpolation.
    """
    uv = np.asarray(uv, dtype=float)
    camray = np.concatenate(((uv - np.asarray(camera['center'])) / camera['focal'],
                             np.ones(uv.shape[:-1] + (1,))), axis=-1)
    ray = camray @ np.asarray(camera['R'])
    origin = np.asarray(camera['eye'])
    best = np.full(uv.shape[:-1], np.inf)
    labels = np.zeros(best.shape, np.int32)

    def submit(t, valid, part):
        take = valid & np.isfinite(t) & (t > 0) & (t < best)
        best[take], labels[take] = t[take], part

    for label, profile in asset['profiles_ry'].items():
        for (r0, y0), (r1, y1) in zip(profile[:-1], profile[1:]):
            if abs(y1 - y0) < 1e-12:
                t = np.divide(y0 - origin[1], ray[..., 1], out=np.full_like(best, np.inf),
                              where=np.abs(ray[..., 1]) > 1e-12)
                with np.errstate(invalid='ignore'):
                    radius = np.hypot(origin[0] + t * ray[..., 0], origin[2] + t * ray[..., 2])
                submit(t, (radius >= min(r0, r1) - 1e-10) &
                       (radius <= max(r0, r1) + 1e-10), int(label))
                continue
            slope = (r1 - r0) / (y1 - y0)
            r_origin = slope * origin[1] + r0 - slope * y0
            r_direction = slope * ray[..., 1]
            aa = ray[..., 0]**2 + ray[..., 2]**2 - r_direction**2
            bb = 2 * (origin[0] * ray[..., 0] + origin[2] * ray[..., 2] - r_origin * r_direction)
            cc = origin[0]**2 + origin[2]**2 - r_origin**2
            disc = bb**2 - 4 * aa * cc
            root = np.sqrt(np.maximum(disc, 0))
            for sign in (-1, 1):
                t = np.divide(-bb + sign * root, 2 * aa, out=np.full_like(best, np.inf),
                              where=np.abs(aa) > 1e-12)
                linear = (np.abs(aa) <= 1e-12) & (np.abs(bb) > 1e-12)
                np.divide(-cc, bb, out=t, where=linear)
                with np.errstate(invalid='ignore'):
                    yy = origin[1] + t * ray[..., 1]
                submit(t, ((disc >= 0) | linear) & (yy >= min(y0, y1) - 1e-10) &
                       (yy <= max(y0, y1) + 1e-10), int(label))
    return best, labels


def reference_maps(asset, camera):
    """Independent pixel-center labels used only for the fixed boundary band."""
    yy, xx = np.mgrid[:int(camera['size']), :int(camera['size'])]
    depth, parts = analytic_rays(asset, camera, np.stack((xx, yy), axis=-1))
    boundary = np.zeros(depth.shape, dtype=float)
    for label in np.unique(parts):
        if label:
            region = parts == label
            boundary[region] = distance_transform_edt(region)[region]
    return dict(depth=depth, parts=parts, boundary_distance=boundary)


def _at(array, uv, cval=0., order=1):
    return map_coordinates(np.asarray(array, dtype=float), [uv[..., 1], uv[..., 0]],
                           order=order, mode='constant', cval=cval)


def projected_ambiguity(points, samples, camera):
    """Conservative self-overlap exclusion, independent of observed ink.

    For each sample, test its closest point on every original projected segment.
    A segment is nonlocal if that point is more than 4px away along the projected
    path, and ambiguous if Euclidean distance is at most 4px. Hidden segments are
    also included, making the exclusion conservative. Report all exclusions.
    """
    points, arc = _path(points)
    uv, z = project(points, camera)
    mid_uv, _ = project(samples['world'], camera)
    vec = np.diff(uv, axis=0)
    length = np.linalg.norm(vec, axis=1)
    projected_arc = np.r_[0., np.cumsum(length)]
    # Locate each material midpoint on the exact original projected polyline.
    owner = np.clip(np.searchsorted(arc, samples['world_arclength'], side='right') - 1, 0, len(points)-2)
    owner_vec = vec[owner]
    owner_len2 = np.sum(owner_vec**2, axis=1)
    owner_u = np.divide(np.sum((mid_uv - uv[owner]) * owner_vec, axis=1), owner_len2,
                        out=np.zeros(len(owner)), where=owner_len2 > 1e-16)
    mid_arc = projected_arc[owner] + np.clip(owner_u, 0, 1) * length[owner]
    q = mid_uv[:, None, :] - uv[None, :-1, :]
    ll = np.sum(vec**2, axis=1)
    uu = np.clip(np.divide(np.sum(q * vec[None], axis=2), ll[None],
                           out=np.zeros(q.shape[:2]), where=ll[None] > 1e-16), 0, 1)
    distances = np.linalg.norm(q - uu[..., None] * vec[None], axis=2)
    along = projected_arc[None, :-1] + uu * length[None]
    nonlocal_part = np.abs(along - mid_arc[:, None]) > PARAMETERS['local_projected_arclength_px'] + 1e-8
    valid_segment = (z[:-1] > 0) & (z[1:] > 0) & (ll > 1e-16)
    ambiguous = np.any(nonlocal_part & valid_segment[None] &
                       (distances <= PARAMETERS['ambiguity_radius_px']), axis=1)
    return ambiguous, mid_arc, float(projected_arc[-1])


def weighted_stats(values, weights):
    values, weights = np.asarray(values, float), np.asarray(weights, float)
    good = np.isfinite(values) & np.isfinite(weights) & (weights > 0)
    values, weights = values[good], weights[good]
    if not len(values):
        return dict(count=0, weight=0., mean=None, p95=None, max=None)
    order = np.argsort(values, kind='stable')
    position = np.searchsorted(np.cumsum(weights[order]), .95 * weights.sum(), side='left')
    return dict(count=int(len(values)), weight=float(weights.sum()),
                mean=float(np.average(values, weights=weights)),
                p95=float(values[order[min(position, len(values)-1)]]), max=float(values.max()))


def evaluate_frame(ink, points, part, camera, asset, stroke_id, sequence, frame, reference=None):
    """Evaluate one actual isolated hatch raster; return a fully JSON-safe row."""
    image = np.asarray(ink)
    scale = 255. if np.issubdtype(image.dtype, np.integer) or image.max() > 1. else 1.
    image = image.astype(float) / scale
    if image.ndim == 3:
        image = image[..., :3].mean(axis=2)
    if image.shape != (int(camera['size']), int(camera['size'])) or not np.isfinite(image).all():
        raise ValueError('Finite isolated ink must match the camera resolution')
    image = np.clip(image, 0., 1.)
    sample = sample_path(points)
    uv, depth = project(sample['world'], camera)
    edges, _ = project(sample['edges'], camera)
    tangent = np.diff(edges, axis=0)
    screen_weight = np.linalg.norm(tangent, axis=1)
    normal = np.column_stack((-tangent[:, 1], tangent[:, 0])) / np.maximum(screen_weight[:, None], 1e-12)
    refz, labels = analytic_rays(asset, camera, uv)
    reference = reference_maps(asset, camera) if reference is None else reference
    margin = _at(reference['boundary_distance'], uv)
    size = int(camera['size'])
    inside = (depth > 0) & np.isfinite(uv).all(axis=1) & (uv[:, 0] >= 0) & (uv[:, 0] <= size-1) & (uv[:, 1] >= 0) & (uv[:, 1] <= size-1)
    gap = depth - refz
    raw_visible = inside & (labels == int(part)) & (np.abs(gap) <= PARAMETERS['depth_tolerance_world'])
    raw_hidden = inside & (labels > 0) & (gap > PARAMETERS['depth_tolerance_world'])
    ambiguous, projected_arc, total_projected_arc = projected_ambiguity(points, sample, camera)
    band = PARAMETERS['boundary_band_px']
    image_margin = np.minimum.reduce((uv[:, 0], uv[:, 1], size-1-uv[:, 0], size-1-uv[:, 1]))
    endpoint_margin = np.minimum(projected_arc, total_projected_arc-projected_arc)
    interior = inside & (labels > 0) & (margin > band) & (image_margin > band) & (endpoint_margin > band)
    cls = np.full(sample['count'], 'unmeasured', dtype='U12')
    cls[~inside] = 'outside'
    cls[inside & ~interior] = 'boundary'
    cls[interior & raw_hidden] = 'hidden'
    cls[interior & raw_visible & (screen_weight > 1e-9)] = 'visible'
    cls[interior & (raw_visible | raw_hidden) & ambiguous] = 'ambiguous'
    offsets = np.arange(-2., 2. + .125, .25)
    profile = _at(image, uv[:, None, :] + offsets[None, :, None] * normal[:, None, :])
    peak, mass = profile.max(axis=1), profile.sum(axis=1)
    present = peak >= PARAMETERS['support_threshold']
    centroid = np.divide(profile @ offsets, mass, out=np.full(sample['count'], np.nan),
                         where=present & (mass > 0))
    support = image >= PARAMETERS['support_threshold']
    distance = _at(distance_transform_edt(~support), uv, cval=np.nan) if support.any() else np.full(sample['count'], np.nan)
    row = dict(stroke_id=str(stroke_id), part=int(part), sequence=str(sequence), frame=int(frame),
               sample_count=sample['count'], path_length_world=sample['length_world'], sampling_capped=sample['capped'],
               image_ink_mass=float(image.sum()), image_support_pixels=int(support.sum()),
               samples=dict(world=sample['world'], uv=uv, world_weight=sample['world_weight'],
                            projected_length_weight=screen_weight, projected_arclength=projected_arc,
                            normal=normal, **{'class': cls.tolist()}, raw_visible=raw_visible,
                            raw_hidden=raw_hidden, ambiguous_geometry=ambiguous,
                            analytic_depth_gap=gap, analytic_part=labels, part_boundary_distance_px=margin,
                            image_margin_px=image_margin, endpoint_margin_px=endpoint_margin,
                            normal_centroid_px=centroid, profile_present=present, profile_peak=peak,
                            support_distance_px=distance))
    row = native(row)
    row['summary'] = _aggregate([row])
    return row


def _aggregate(rows):
    counts = {name: 0 for name in CLASSES}
    world = {name: 0. for name in CLASSES}
    screen = {name: 0. for name in CLASSES}
    raw_world = raw_screen = missing_world = missing_screen = 0.
    all_world = all_screen = 0.
    missing_count = hidden_present = raw_hidden_present = 0
    residuals, rw, rs, distances, dw = [], [], [], [], []
    unique, ids = set(), set()
    for row in rows:
        raw = row['samples']; ids.add(row['stroke_id'])
        for i, cls in enumerate(raw['class']):
            ww, sw = raw['world_weight'][i], raw['projected_length_weight'][i]
            counts[cls] += 1; world[cls] += ww; screen[cls] += sw
            all_world += ww; all_screen += sw
            if raw['raw_visible'][i]:
                raw_world += ww; raw_screen += sw
            present = raw['profile_present'][i]
            hidden_present += cls == 'hidden' and present
            raw_hidden_present += raw['raw_hidden'][i] and present
            if cls != 'visible':
                continue
            unique.add((row['stroke_id'], i))
            if not present:
                missing_count += 1; missing_world += ww; missing_screen += sw
            elif raw['normal_centroid_px'][i] is not None:
                residuals.append(abs(raw['normal_centroid_px'][i])); rw.append(ww); rs.append(sw)
            if raw['support_distance_px'][i] is not None:
                distances.append(raw['support_distance_px'][i]); dw.append(ww)
    return dict(records=len(rows), stroke_ids=len(ids), class_counts=counts,
                class_world_length=world, class_projected_length=screen,
                all_world_length=all_world, all_projected_length=all_screen,
                raw_visible_world_length=raw_world, raw_visible_projected_length=raw_screen,
                eligible_over_raw_visible_world=world['visible']/raw_world if raw_world else None,
                eligible_over_raw_visible_screen=screen['visible']/raw_screen if raw_screen else None,
                eligible_over_all_world=world['visible']/all_world if all_world else None,
                eligible_over_all_screen=screen['visible']/all_screen if all_screen else None,
                unique_visible_material_samples=len(unique), missing_visible_samples=missing_count,
                missing_world_length=missing_world, missing_projected_length=missing_screen,
                missing_world_fraction=missing_world/world['visible'] if world['visible'] else None,
                missing_screen_fraction=missing_screen/screen['visible'] if screen['visible'] else None,
                centroid_abs_px=weighted_stats(residuals, rw),
                centroid_abs_screen_weighted_px=weighted_stats(residuals, rs),
                support_distance_px=weighted_stats(distances, dw),
                hidden_profile_present=hidden_present, raw_hidden_profile_present=raw_hidden_present)


def _pairs(rows):
    output = []
    keys = sorted({(r['sequence'], r['stroke_id']) for r in rows})
    for sequence, sid in keys:
        group = sorted((r for r in rows if (r['sequence'], r['stroke_id']) == (sequence, sid)), key=lambda r: r['frame'])
        for before, after in zip(group[:-1], group[1:]):
            if after['frame'] != before['frame'] + 1:
                continue
            a, b = before['samples'], after['samples']
            common = [i for i, (x, y) in enumerate(zip(a['class'], b['class'])) if x == y == 'visible']
            both = [i for i in common if a['profile_present'][i] and b['profile_present'][i]]
            drop = [i for i in common if a['profile_present'][i] and not b['profile_present'][i]]
            appear = [i for i in common if not a['profile_present'][i] and b['profile_present'][i]]
            missing = [i for i in common if not (a['profile_present'][i] and b['profile_present'][i])]
            ww = np.asarray(a['world_weight'])
            sw = np.minimum(a['projected_length_weight'], b['projected_length_weight'])
            errors = [abs(b['normal_centroid_px'][i] - a['normal_centroid_px'][i]) for i in both]
            common_world = float(ww[common].sum())
            output.append(dict(sequence=sequence, stroke_id=sid, part=before['part'],
                frames=[before['frame'], after['frame']], common_visible_samples=len(common),
                common_visible_world_length=common_world, common_visible_projected_length=float(sw[common].sum()),
                both_present_samples=len(both), both_present_world_length=float(ww[both].sum()),
                missing_either_samples=len(missing), missing_either_world_length=float(ww[missing].sum()),
                missing_either_world_fraction=float(ww[missing].sum()/common_world) if common_world else None,
                dropout_samples=len(drop), dropout_world_length=float(ww[drop].sum()),
                reappearance_samples=len(appear), reappearance_world_length=float(ww[appear].sum()),
                normal_residual_change_abs_px=weighted_stats(errors, ww[both]),
                raw=dict(sample_indices=both, residual_change_abs_px=errors, world_weight=ww[both].tolist(),
                         projected_length_weight=sw[both].tolist())))
    return output


def _group(rows, pairs):
    result = _aggregate(rows)
    common = sum(p['common_visible_world_length'] for p in pairs)
    errors = [v for p in pairs for v in p['raw']['residual_change_abs_px']]
    weights = [v for p in pairs for v in p['raw']['world_weight']]
    temporal = weighted_stats(errors, weights)
    result['temporal'] = dict(adjacent_pairs=len(pairs), common_visible_world_length=common,
        common_visible_projected_length=sum(p['common_visible_projected_length'] for p in pairs),
        both_present_world_length=sum(p['both_present_world_length'] for p in pairs),
        missing_either_world_fraction=sum(p['missing_either_world_length'] for p in pairs)/common if common else None,
        dropout_world_fraction=sum(p['dropout_world_length'] for p in pairs)/common if common else None,
        reappearance_world_fraction=sum(p['reappearance_world_length'] for p in pairs)/common if common else None,
        normal_residual_change_abs_px=temporal)
    coverage = result['eligible_over_raw_visible_world']
    centroid = result['centroid_abs_px']['p95']
    missing = result['missing_world_fraction']
    measured = coverage is not None and coverage >= GATES['eligible_over_raw_visible_world_min'] and common > 0
    gates = dict(coverage=measured,
                 alignment=centroid is not None and centroid <= GATES['centroid_abs_p95_px_max'],
                 temporal=temporal['p95'] is not None and temporal['p95'] <= GATES['temporal_residual_p95_px_max'],
                 missing=missing is not None and missing <= GATES['missing_world_fraction_max'])
    result['gates'] = gates
    result['status'] = 'UNMEASURED' if not measured else ('GO' if all(gates.values()) else 'NO_GO')
    return result


def summarize(rows):
    """World-length weighted part gates; all IDs and exclusions remain visible."""
    if len({(r['sequence'], r['stroke_id'], r['frame']) for r in rows}) != len(rows):
        raise ValueError('Duplicate sequence/stroke/frame observations')
    pairs = _pairs(rows)
    by_sequence = {}
    for sequence in sorted({r['sequence'] for r in rows}):
        selected = [r for r in rows if r['sequence'] == sequence]
        sp = [p for p in pairs if p['sequence'] == sequence]
        per_part = {str(part): _group([r for r in selected if r['part'] == part], [p for p in sp if p['part'] == part]) for part in (1, 2, 3)}
        by_sequence[sequence] = dict(all=_group(selected, sp), per_part=per_part)
    per_part = {str(part): _group([r for r in rows if r['part'] == part], [p for p in pairs if p['part'] == part]) for part in (1, 2, 3)}
    per_stroke = {sid: _group([r for r in rows if r['stroke_id'] == sid], [p for p in pairs if p['stroke_id'] == sid]) for sid in sorted({r['stroke_id'] for r in rows})}
    checks = [p['status'] for sequence in by_sequence.values() for p in sequence['per_part'].values()]
    status = 'NO_GO' if 'NO_GO' in checks else ('GO' if checks and all(s == 'GO' for s in checks) else 'UNMEASURED')
    return native(dict(status=status, all=_group(rows, pairs), per_part=per_part,
                       per_stroke=per_stroke, per_sequence=by_sequence, adjacent_frame_pairs=pairs,
                       parameters=PARAMETERS, limits=GATES,
                       hidden_visibility_verdict='DIAGNOSTIC_ONLY_NO_FALSE_HIDDEN_GO',
                       limitations=['Authored profiles shared with the mesh; not reconstructed or independent acquisition.',
                           'Fixed .006-world tolerance admits mesh/analytic surface disagreement.',
                           'Boundary distance uses independent integer-pixel labels; probe depth uses continuous rays; image and path endpoint margins are fixed2px.',
                           'Conservative self-overlap exclusion includes hidden nonlocal segments.',
                           'Normal-profile centroid cannot measure tangential displacement; missing ink stays in denominators.',
                           'Residual changes include subpixel/raster effects and rotating profile normals.',
                           'Hidden profile ink may originate on another segment and is never automatic leakage success.',
                           'Repeated views are one exposed object, not independent scientific samples.']))
