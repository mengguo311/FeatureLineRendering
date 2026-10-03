"""Frozen native-depth support, visibility, and whole-view validation gates.

Visibility never consults image edges. The optional line-evidence callback is
used only by validation diagnostics after the depth-only sets are fixed.
"""
import numpy as np


def _coordinates(native, uv, z):
    uv = np.asarray(uv, dtype=np.float64).reshape(-1, 2)
    z = np.asarray(z, dtype=np.float64).reshape(-1)
    if len(uv) != len(z):
        raise ValueError('uv and z sample counts differ')
    height, width = np.asarray(native['alpha']).shape
    finite = np.isfinite(uv).all(axis=1) & np.isfinite(z)
    in_frame = finite & (uv[:, 0] >= 0) & (uv[:, 0] < width) & (uv[:, 1] >= 0) & (uv[:, 1] < height)
    safe = np.where(in_frame[:, None], uv, 0)
    # Clip only after the continuous-coordinate in-frame predicate is fixed.
    integer = np.floor(safe + .5).astype(np.int64)
    integer[:, 0] = np.clip(integer[:, 0], 0, width - 1)
    integer[:, 1] = np.clip(integer[:, 1], 0, height - 1)
    return uv, z, finite, in_frame, integer


def _sample(native, key, integer):
    return np.asarray(native[key])[integer[:, 1], integer[:, 0]]


def depth_support(native, uv, z, cfg):
    """Native top-k conflict and support at the observed/projected pixel.

    Absolute native topk_w admits layers. Mean/median are fallback support
    summaries and cannot override any conflict among admitted individual layers.
    """
    uv, z, finite, in_frame, integer = _coordinates(native, uv, z)
    tri = cfg['triangulation']
    near = cfg['visibility']['near_plane']
    valid = in_frame & (z > near)
    depths = _sample(native, 'topk_depth', integer).astype(np.float64)
    weights = _sample(native, 'topk_w', integer).astype(np.float64)
    ids = _sample(native, 'topk_id', integer)
    admitted = valid[:, None] & np.isfinite(depths) & (depths > near) & np.isfinite(weights) & (weights >= tri['layer_min_weight']) & (ids >= 0)
    conflict = np.zeros(len(z), dtype=bool)
    for i in range(depths.shape[1]):
        for j in range(i + 1, depths.shape[1]):
            tolerance = np.maximum(tri['depth_absolute_tolerance'], tri['layer_ambiguity_separation_relative'] * np.minimum(depths[:, i], depths[:, j]))
            conflict |= admitted[:, i] & admitted[:, j] & (np.abs(depths[:, i] - depths[:, j]) > tolerance)
    tolerance = np.maximum(tri['depth_absolute_tolerance'], tri['depth_relative_tolerance'] * z)
    supported_topk = np.any(admitted & (np.abs(depths - z[:, None]) <= tolerance[:, None]), axis=1)
    alpha = _sample(native, 'alpha', integer).astype(np.float64)
    summary_eligible = valid & np.isfinite(alpha) & (alpha >= tri['layer_min_weight'])
    supported_summary = np.zeros(len(z), dtype=bool)
    for key in ['depth', 'median_depth']:
        summary = _sample(native, key, integer).astype(np.float64)
        supported_summary |= summary_eligible & np.isfinite(summary) & (summary > near) & (np.abs(summary - z) <= tolerance)
    supported = valid & ~conflict & (supported_topk | supported_summary)
    diagnostics = []
    for index in np.flatnonzero(conflict):
        diagnostics.append({
            'sample_index': int(index), 'observed_pixel_xy': uv[index].tolist(),
            'layers': [{'slot': int(slot), 'id': int(ids[index, slot]), 'depth': float(depths[index, slot]), 'absolute_weight': float(weights[index, slot])} for slot in np.flatnonzero(admitted[index])],
        })
    return {
        'supported': supported, 'conflict': conflict, 'layer_conflict': conflict,
        'valid': valid, 'in_frame': in_frame, 'invalid': ~finite,
        'admitted_layers': admitted, 'layer_diagnostics': diagnostics,
    }


def classify_visibility(native, uv, z, cfg):
    """Depth-only I/O/V/U sets; unreliable samples remain visible."""
    uv, z, finite, in_frame, integer = _coordinates(native, uv, z)
    c = cfg['visibility']
    I = in_frame & (z > c['near_plane'])
    outside = finite & (z > c['near_plane']) & ~in_frame
    behind = finite & (z <= c['near_plane'])
    depth = _sample(native, 'depth', integer).astype(np.float64)
    median = _sample(native, 'median_depth', integer).astype(np.float64)
    alpha = _sample(native, 'alpha', integer).astype(np.float64)
    moment2 = _sample(native, 'moment2', integer).astype(np.float64)
    support = depth_support(native, uv, z, cfg)
    with np.errstate(divide='ignore', invalid='ignore', over='ignore'):
        variance = np.maximum(moment2 / alpha - depth * depth, 0)
        relative_variance = variance / (depth * depth)
        relative_mean_median = np.abs(median - depth) / depth
    reliable = I & np.isfinite(alpha) & (alpha >= c['reliable_alpha_min'])
    reliable &= np.isfinite(depth) & (depth > c['near_plane']) & np.isfinite(median) & (median > c['near_plane'])
    reliable &= np.isfinite(moment2) & np.isfinite(relative_variance) & (relative_variance <= c['reliable_variance_relative_max'])
    reliable &= np.isfinite(relative_mean_median) & (relative_mean_median <= c['median_mean_relative_max']) & ~support['conflict']
    tolerance = np.maximum(c['depth_absolute_tolerance'], c['depth_relative_tolerance'] * z)
    O = reliable & (z > median + tolerance)
    V = I & ~O
    U = V & ~reliable
    return {
        'I': I, 'O': O, 'V': V, 'U': U,
        'occluded': O, 'visible': V, 'uncertain': U,
        'outside': outside, 'behind': behind, 'reliable': reliable,
        'invalid': ~finite, 'median_depth': median, 'depth_tolerance': tolerance,
        'depth_supported': support['supported'], 'layer_conflict': support['conflict'],
        'layer_diagnostics': support['layer_diagnostics'],
    }


def validate_view(native, uv, z, tangents, evidence_candidates_callback, cfg):
    """Audit one view without changing fixed geometry or visibility.

    callback(uv[I], tangents[I]) returns one Nx2 array per query containing ALL
    observed skeleton pixels passing the fixed position AND direction tests.
    Evidence affects only J/A_absence/K and whole-path acceptance diagnostics.
    An ineligible view can pass its applicable contradiction/absence gates but
    never supplies a positive validation vote.
    """
    uv, z, finite, _, _ = _coordinates(native, uv, z)
    tangents = np.asarray(tangents, dtype=np.float64).reshape(-1, 2)
    if len(tangents) != len(z):
        raise ValueError('tangent and projection sample counts differ')
    rule = cfg['validation_rules']
    vis = classify_visibility(native, uv, z, cfg)
    I, O, V, U = (vis[key] for key in ['I', 'O', 'V', 'U'])
    J = np.zeros(len(z), dtype=bool)
    absence = np.zeros(len(z), dtype=bool)
    eligible_tangent = np.isfinite(tangents).all(axis=1) & (np.linalg.norm(tangents, axis=1) > 0)
    query_indices = np.flatnonzero(I & eligible_tangent)
    if len(query_indices):
        candidates = evidence_candidates_callback(uv[query_indices], tangents[query_indices])
        if len(candidates) != len(query_indices):
            raise ValueError('evidence callback returned the wrong sample count')
        for index, observed in zip(query_indices, candidates):
            observed = np.asarray(observed, dtype=np.float64).reshape(-1, 2)
            if not len(observed):
                continue
            # This is a diagnostic position safeguard; it never changes V/O.
            observed = observed[np.isfinite(observed).all(axis=1) & (np.linalg.norm(observed - uv[index], axis=1) <= rule['position_tolerance_px'])]
            if not len(observed):
                continue
            if V[index]:
                J[index] = True
            if O[index]:
                evidence_support = depth_support(native, observed, np.full(len(observed), z[index]), cfg)
                absence[index] = bool(np.any(evidence_support['supported']))
    D = V & vis['depth_supported']
    reliable_disagreement = I & vis['reliable'] & (np.abs(z - vis['median_depth']) > vis['depth_tolerance']) & ~O
    K = (V & ~J) | (I & vis['layer_conflict']) | reliable_disagreement | absence
    masks = {'I': I, 'O': O, 'V': V, 'U': U, 'J': J, 'D': D, 'A_absence': absence, 'K': K,
             'outside': vis['outside'], 'behind': vis['behind'], 'invalid': vis['invalid']}
    counts = {key: int(mask.sum()) for key, mask in masks.items()}
    def ratio(numerator, denominator):
        return counts[numerator] / counts[denominator] if counts[denominator] else None
    ratios = {
        'position_direction_support': ratio('J', 'V'), 'depth_support': ratio('D', 'V'),
        'uncertain': ratio('U', 'V'), 'unjustified_absence': ratio('A_absence', 'O'),
        'contradiction': ratio('K', 'I'),
    }
    adjacent_visible = V[:-1] & V[1:]
    lengths = np.linalg.norm(uv[1:] - uv[:-1], axis=1)
    length = float(lengths[adjacent_visible].sum())
    visible_uv = uv[V]
    extent = float(np.sqrt(np.max(np.sum((visible_uv[:, None] - visible_uv[None, :]) ** 2, axis=-1)))) if len(visible_uv) > 1 else 0.0
    eligible = bool(counts['V'] >= rule['min_visible_samples_per_view'] and length >= rule['min_projected_length_per_view_px'] and extent >= rule['min_projected_extent_per_view_px'])
    failures = []
    if counts['invalid']:
        failures.append('invalid_geometry')
    if ratios['contradiction'] is not None and ratios['contradiction'] > rule['max_contradiction_fraction']:
        failures.append('contradiction')
    if ratios['unjustified_absence'] is not None and ratios['unjustified_absence'] > rule['max_unjustified_absence_fraction']:
        failures.append('unjustified_absence')
    if eligible:
        if ratios['position_direction_support'] < rule['min_position_direction_support_fraction']:
            failures.append('predicted_missing_or_wrong_direction')
        if ratios['depth_support'] < rule['min_depth_support_fraction']:
            failures.append('depth_support')
        if ratios['uncertain'] > rule['max_uncertain_fraction']:
            failures.append('uncertain')
    return {
        'sample_count': len(z), 'counts': counts, 'ratios': ratios,
        'eligible': eligible, 'projected_length_px': length, 'projected_extent_px': extent,
        'passed': not failures, 'positive_vote': eligible and not failures,
        'invalid_geometry': bool(counts['invalid']), 'failures': failures,
        'layer_diagnostics': vis['layer_diagnostics'],
    }
