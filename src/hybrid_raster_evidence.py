"""Frozen CPU readout for one calibrated native RaDe-GS traversal.

Hao--Mukai Eq.1--5 are independently reconstructed in the imported source
module; this caller supplies native RaDe state, not that module's older proxy.
OUR dense readout, Canny arm and complement are explicitly separate additions.
RaDe normals remain splat normals and visible SH0 color is not material albedo.
"""
import hashlib
import json

import cv2
import numpy as np
from scipy import ndimage as ndi

from src.hao_mukai_source_2026 import compute_fields, smoothstep, THRESH, PARAMS


CHANNELS = ('delta_D', 'delta_A', 'delta_N', 'delta_C', 'delta_G', 'visibility_raw')
RECIPE = {
    'version': 'hybrid-raster-evidence-v2-frozen-1',
    'channels': list(CHANNELS), 'positive_percentile': 99,
    'dense_smoothstep': [.10, .70], 'reliability_strength': [.35, .65],
    'rgb_fine': {'kernel': 3, 'sigma': .65, 'canny': [18, 48], 'L2gradient': True},
    'rgb_coarse': {'kernel': 5, 'sigma': 1.4, 'canny': [25, 65], 'L2gradient': True},
    'alpha_canny': [25, 65], 'foreground_alpha': .08, 'foreground_dilation': 3,
    'depth_sigma': 1.5, 'depth_foreground_alpha': .5,
    'depth_hysteresis_percentiles': [95, 70], 'depth_relative_floor': .002,
    'depth_local_window': 5, 'brush_pixels': 1, 'mask_thresholds_diagnostic': [.1, .3, .5],
    'author_params': PARAMS, 'author_thresholds': THRESH,
}


def canonical_hash(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def validate_raw(raw, gaussian_count=None):
    """Reject corrupt exports before the legacy formula can nan_to_num them.

    Array validation cannot establish provenance by itself. The production
    runner must additionally calibrate the patched/unpatched same-input pass.
    Optional channel_source_ids enforce the caller's same-traversal manifest.
    """
    if 'alpha' not in raw or np.asarray(raw['alpha']).ndim != 2:
        raise ValueError('alpha must be an HxW native grid')
    h, w = np.asarray(raw['alpha']).shape
    if min(h, w) < 1:
        raise ValueError('native image dimensions must be positive')
    shapes = dict(rgb=(h, w, 3), alpha=(h, w), depth=(h, w), median_depth=(h, w),
                  normal=(h, w, 3), topk_id=(h, w, 4), topk_w=(h, w, 4),
                  topk_depth=(h, w, 4), topk_normal=(h, w, 4, 3),
                  moment2=(h, w), normal_len=(h, w))
    for key, shape in shapes.items():
        if key not in raw:
            raise ValueError('missing native field: ' + key)
        value = np.asarray(raw[key])
        if value.shape != shape:
            raise ValueError('native grid shape mismatch: ' + key)
        if not np.issubdtype(value.dtype, np.number) or not np.isfinite(value).all():
            raise ValueError('nonfinite or nonnumeric native field: ' + key)
    ids = np.asarray(raw['topk_id'])
    weights = np.asarray(raw['topk_w'])
    alpha = np.asarray(raw['alpha'])
    if not np.issubdtype(ids.dtype, np.integer) or np.any(ids < -1):
        raise ValueError('original Gaussian IDs must be integral and -1 only for empty slots')
    if gaussian_count is not None and np.any(ids >= gaussian_count):
        raise ValueError('original Gaussian ID outside checkpoint range')
    if np.any(alpha < 0) or np.any(alpha > 1 + 3e-6) or np.any(weights < 0):
        raise ValueError('alpha or contribution weights outside physical range')
    if np.any(weights[ids < 0] != 0):
        raise ValueError('empty original ID must have zero contribution weight')
    if np.any((ids >= 0) & (weights <= 0)):
        raise ValueError('nonempty contributor must have positive alpha*T')
    if np.any(np.diff(weights, axis=-1) > 3e-6):
        raise ValueError('top4 raw contribution weights must be nonincreasing')
    if np.any(weights.sum(-1) > alpha + 3e-6):
        raise ValueError('top4 alpha*T exceeds full alpha; raw weights must not be normalized')
    if np.any((alpha == 0)[..., None] & (ids != -1)):
        raise ValueError('empty rays must retain sentinel original IDs')
    for i in range(4):
        for j in range(i + 1, 4):
            if np.any((ids[..., i] >= 0) & (ids[..., i] == ids[..., j])):
                raise ValueError('same original Gaussian appears twice in one top4')
    sources = raw.get('channel_source_ids')
    if sources is not None:
        source_id = raw.get('source_id')
        if source_id is None or any(sources.get(key) != source_id for key in shapes):
            raise ValueError('native channel source mismatch')
    return (h, w)


def raw_fields(raw):
    """Return every author field plus unsuppressed visibility and qualifications.

    Raw alpha*T is never overwritten. Only the formula input receives top4
    normalized weights; all-contributor moments define the variance.
    """
    validate_raw(raw)
    alpha = np.asarray(raw['alpha'], np.float32)
    mass = np.asarray(raw['topk_w'], np.float32).sum(-1)
    denom = np.maximum(alpha, 1e-8)
    normalized = np.asarray(raw['topk_w'], np.float32) / np.maximum(mass[..., None], 1e-8)
    variance = np.maximum(np.asarray(raw['moment2']) / denom - np.asarray(raw['depth']) ** 2, 0).astype(np.float32)
    visible_color = np.clip((np.asarray(raw['rgb']) - (1 - alpha)[..., None]) / denom[..., None], 0, 1).astype(np.float32)
    visible_color[alpha == 0] = 0
    topk_mass = np.clip(mass / denom, 0, 1).astype(np.float32)
    coherence = np.clip(np.asarray(raw['normal_len']) / denom, 0, 1).astype(np.float32)
    state = dict(alpha=alpha, depth=raw['depth'], normal=raw['normal'], albedo=visible_color,
                 topk_id=raw['topk_id'], topk_w=normalized, topk_mass=topk_mass,
                 topk_depth=raw['topk_depth'], topk_normal=raw['topk_normal'],
                 depth_variance=variance, normal_coherence=coherence)
    fields = compute_fields(state)
    td, tn = np.asarray(raw['topk_depth']), np.asarray(raw['topk_normal'])
    dz = np.abs(td[..., 0] - td[..., 1]) / np.maximum(np.maximum(td[..., 0], td[..., 1]), 1e-8)
    dn = 1 - np.clip(np.sum(tn[..., 0, :] * tn[..., 1, :], axis=-1), -1, 1)
    visibility = fields['ell'] * np.maximum(smoothstep(dz, *THRESH['VD']), PARAMS['lambda_VN'] * smoothstep(dn, *THRESH['VN']))
    visibility *= (alpha > .05) & (np.asarray(raw['depth']) > 0)
    fields.update(visibility_raw=visibility.astype(np.float32), topk_mass=topk_mass,
                  normal_coherence=coherence, depth_variance=variance,
                  normalized_topk_w=normalized, visible_color=visible_color)
    for key, value in fields.items():
        if not np.isfinite(value).all():
            raise ValueError('nonfinite derived field: ' + key)
    return fields


def fit_normalization(list_fields):
    """Exact pooled positive-P99; production supplies only both primary scenes' F.

    No scene/frame adaptation occurs in compute_evidence. Frame provenance and
    F-list hashes belong to the production lock surrounding this return value.
    """
    list_fields = list(list_fields)
    if not list_fields:
        raise ValueError('F normalization needs at least one field frame')
    scales = {}
    counts = {}
    for key in (*CHANNELS, 'S_L'):
        positives = []
        for fields in list_fields:
            value = np.asarray(fields[key])
            if not np.isfinite(value).all() or np.any(value < 0):
                raise ValueError('invalid F normalization field: ' + key)
            positives.append(value[value > 0].astype(np.float32, copy=False))
        count = sum(len(value) for value in positives)
        counts[key] = count
        scales[key] = float(np.percentile(np.concatenate(positives), 99)) if count else 1.
    return dict(scales={key: scales[key] for key in CHANNELS}, author_scale=scales['S_L'],
                positive_counts=counts, frame_count=len(list_fields), recipe=RECIPE,
                recipe_hash=canonical_hash(RECIPE), normalization_scope='primary F only; caller-enforced')


def depth_evidence(depth, alpha):
    """Native median-depth derivative/NMS 95/70 hysteresis, inherited D rule.

    Unlike the old curve fitter, this arm never reduces to area400 and projects
    back to one arbitrary pixel of each 2x2 block.
    """
    z = np.asarray(depth, np.float64)
    gx = ndi.gaussian_filter(z, 1.5, order=(0, 1))
    gy = ndi.gaussian_filter(z, 1.5, order=(1, 0))
    padded = np.pad(z, 2, mode='edge')
    neighbors = np.lib.stride_tricks.sliding_window_view(padded, (5, 5)).reshape(*z.shape, 25)
    differences = np.abs(neighbors[..., [i for i in range(25) if i != 12]] - z[..., None])
    local = np.maximum.reduce([.002 * z, np.median(differences, axis=-1), np.full(z.shape, 1e-12)])
    magnitude = np.hypot(gx, gy)
    strength = magnitude / local
    yy, xx = np.indices(z.shape)
    nx, ny = gx / np.maximum(magnitude, 1e-30), gy / np.maximum(magnitude, 1e-30)
    minus = ndi.map_coordinates(strength, [yy - ny, xx - nx], order=1, mode='nearest')
    plus = ndi.map_coordinates(strength, [yy + ny, xx + nx], order=1, mode='nearest')
    roi = np.asarray(alpha) >= .5
    nms = (strength >= minus) & (strength >= plus) & (strength > 0) & roi
    positive = strength[nms]
    mask = np.zeros(z.shape, bool)
    hi = lo = None
    if len(positive):
        hi, lo = (float(x) for x in np.percentile(positive, [95, 70]))
        labels, _ = ndi.label(nms & (strength >= lo), np.ones((3, 3)))
        keep = np.unique(labels[nms & (strength >= hi)])
        mask = np.isin(labels, keep[keep > 0])
    outline = roi & ~ndi.binary_erosion(roi, border_value=1)
    mask |= outline
    return dict(ink=mask.astype(np.float32), response=strength.astype(np.float32),
                nms=nms, outline=outline, high=hi, low=lo)


def fuse_channels(a, b):
    a, b = np.asarray(a, np.float32), np.asarray(b, np.float32)
    if a.shape != b.shape or a.ndim != 2:
        raise ValueError('fusion requires equal HxW shapes')
    if not np.isfinite(a).all() or not np.isfinite(b).all() or np.any(a < 0) or np.any(a > 1) or np.any(b < 0) or np.any(b > 1):
        raise ValueError('fusion strengths must be finite [0,1]')
    overlap = a * b
    # Algebraically equal to 1-(1-a)*(1-b), without erasing tiny positive b.
    c = a + b * (1 - a)
    return c, dict(A_support=a > 0, B_support=b > 0,
                   A_only=(a > 0) & (b == 0), B_only=(b > 0) & (a == 0),
                   shared=(a > 0) & (b > 0), overlap=overlap)


def ink_matched(arms):
    mass = {name: float(np.asarray(value).sum(dtype=np.float64)) for name, value in arms.items()}
    target = min(mass.values())
    gains = {name: target / value if value else 0. for name, value in mass.items()}
    return {name: (value * gains[name]).astype(np.float32) for name, value in arms.items()}, dict(target_mass=target, gains=gains, original_mass=mass)


def _distribution(value, mask):
    data = np.asarray(value)[mask]
    if not data.size:
        return dict(count=0, mean=None, min=None, max=None, p05=None, p50=None, p95=None)
    return dict(count=int(data.size), mean=float(data.mean(dtype=np.float64)), min=float(data.min()),
                max=float(data.max()), p05=float(np.percentile(data, 5)),
                p50=float(np.percentile(data, 50)), p95=float(np.percentile(data, 95)))


def compute_evidence(raw, normalization):
    validate_raw(raw)
    if normalization.get('recipe_hash') != canonical_hash(RECIPE):
        raise ValueError('normalization recipe hash mismatch')
    for key in CHANNELS:
        scale = normalization['scales'][key]
        if not np.isfinite(scale) or scale <= 0:
            raise ValueError('normalization scale must be finite and positive: ' + key)
    author_scale = normalization['author_scale']
    if not np.isfinite(author_scale) or author_scale <= 0:
        raise ValueError('author scale must be finite and positive')
    fields = raw_fields(raw)
    alpha = np.asarray(raw['alpha'])
    foreground = cv2.dilate((alpha >= .08).astype(np.uint8), np.ones((3, 3), np.uint8)) > 0
    rgb = np.uint8(np.round(np.clip(raw['rgb'], 0, 1) * 255))
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    fine = cv2.Canny(cv2.GaussianBlur(gray, (3, 3), .65), 18, 48, L2gradient=True) > 0
    coarse = cv2.Canny(cv2.GaussianBlur(gray, (5, 5), 1.4), 25, 65, L2gradient=True) > 0
    silhouette = cv2.Canny(np.uint8(np.round(np.clip(alpha, 0, 1) * 255)), 25, 65) > 0
    depth = depth_evidence(raw['median_depth'], alpha)
    arrays = dict(A_rgb_fine=(fine & foreground).astype(np.float32),
                  A_rgb_coarse=(coarse & foreground).astype(np.float32),
                  A_alpha=(silhouette & foreground).astype(np.float32),
                  A_depth=depth['ink'] * foreground,
                  A_depth_response=depth['response'], A_depth_nms=depth['nms'])
    arrays['A'] = np.maximum.reduce([arrays[key] for key in ('A_rgb_fine', 'A_rgb_coarse', 'A_alpha', 'A_depth')])
    b_channels = []
    reliability = .35 + .65 * fields['q']
    for key in CHANNELS:
        normalized = np.clip(fields[key] / normalization['scales'][key], 0, 1).astype(np.float32)
        ink = (smoothstep(normalized, .10, .70) * reliability * foreground).astype(np.float32)
        arrays['B_normalized_' + key] = normalized
        arrays['B_' + key] = ink
        b_channels.append(ink)
    b_channels = np.stack(b_channels, axis=-1)
    arrays['B'] = b_channels.max(-1)
    arrays['C'], provenance = fuse_channels(arrays['A'], arrays['B'])
    b_bits = np.zeros(alpha.shape, np.uint8)
    for index in range(len(CHANNELS)):
        b_bits |= ((b_channels[..., index] > 0).astype(np.uint8) << index)
    b_argmax = b_channels.argmax(-1).astype(np.int8)
    b_argmax[arrays['B'] == 0] = -1
    a_bits = np.zeros(alpha.shape, np.uint8)
    for index, key in enumerate(('A_rgb_fine', 'A_rgb_coarse', 'A_alpha', 'A_depth')):
        a_bits |= ((arrays[key] > 0).astype(np.uint8) << index)
    provenance.update(B_channel_bits=b_bits, B_argmax=b_argmax, A_channel_bits=a_bits,
                      arm_bits=(arrays['A'] > 0).astype(np.uint8) | ((arrays['B'] > 0).astype(np.uint8) << 1),
                      foreground=foreground)
    # Retain the author's actual expression, with no OUR reliability/mask rewrite.
    arrays['author_absolute'] = fields['S_L'].copy()
    arrays['author_gain'] = np.clip(fields['S_L'] / author_scale, 0, 1).astype(np.float32)
    matched, matching = ink_matched({name: arrays[name] for name in ('A', 'B', 'C')})
    arrays.update({name + '_matched': value for name, value in matched.items()})
    core = alpha >= .5
    outline = ndi.binary_dilation(core, iterations=4) & ~ndi.binary_erosion(core, iterations=4, border_value=0)
    interior = core & ~outline
    strata = dict(background=~(outline | core), outline=outline, interior=interior)
    arm_stats = {}
    for name in ('A', 'B', 'C'):
        ink = arrays[name]
        arm_stats[name] = dict(mass=float(ink.sum(dtype=np.float64)), support=int(np.count_nonzero(ink)),
                               threshold_area={str(t): int(np.count_nonzero(ink >= t)) for t in (.1, .3, .5)},
                               strata={stratum: dict(pixels=int(mask.sum()), mass=float(ink[mask].sum(dtype=np.float64)), support=int(np.count_nonzero(ink[mask]))) for stratum, mask in strata.items()})
    diagnostics = dict(shape=list(alpha.shape), native_rgb_mode='SH0; same buffer for all arms',
                       interpretation='pixel/coverage diagnostics only; no geometric truth or useful-line metric',
                       arms=arm_stats, ink_matching=matching,
                       overlap=dict(A_only=int(provenance['A_only'].sum()), B_only=int(provenance['B_only'].sum()),
                                    shared=int(provenance['shared'].sum()), mass=float(provenance['overlap'].sum(dtype=np.float64))),
                       raw=dict(alpha=_distribution(alpha, np.ones_like(foreground)),
                                top4_coverage=_distribution(fields['topk_mass'], alpha > .05),
                                normal_coherence=_distribution(fields['normal_coherence'], alpha > .05),
                                depth_variance=_distribution(fields['depth_variance'], alpha > .05)),
                       depth_hysteresis=dict(high=depth['high'], low=depth['low']),
                       B_channel_order=list(CHANNELS), A_channel_order=['rgb_fine', 'rgb_coarse', 'alpha', 'depth'],
                       recipe_hash=normalization['recipe_hash'], source_id=raw.get('source_id'))
    return dict(arrays=arrays, provenance=provenance, diagnostics=diagnostics, fields=fields)
