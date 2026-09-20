"""Deterministic 2D center-KDE and broad positive-ridge diagnostics.

This module implements artifacts/density_ridge_lines/PROTOCOL.md, not persistent
3D strokes. Arrays are float64; masks are bool. Coordinates are (x, y) in pixels.
"""
from __future__ import annotations

import numpy as np
from scipy import ndimage as ndi
from skimage.morphology import skeletonize

BANDWIDTHS = np.array([1., np.sqrt(2), 2., np.sqrt(8), 4.])
SCALES = (1.5, 2.5, 4.)
CHANNELS = ('color', 'axis', 'opacity', 'flattening', 'planarity', 'agreement', 'surface')


def disk(radius):
    y, x = np.mgrid[-radius:radius+1, -radius:radius+1]
    return x*x+y*y <= radius*radius


def axial_tensor(normals):
    n = np.asarray(normals, dtype=np.float64)
    n = n / np.maximum(np.linalg.norm(n, axis=-1, keepdims=True), 1e-15)
    return n[..., :, None] * n[..., None, :]


def bilinear_splat(xy, values, shape):
    """Mass-conserving inside the canvas; zero extension beyond canvas edges."""
    xy = np.asarray(xy, dtype=np.float64)
    values = np.asarray(values, dtype=np.float64)
    if values.ndim == 1:
        values = values[:, None]
    h, w = shape
    out = np.zeros((h*w, values.shape[1]), dtype=np.float64)
    base = np.floor(xy).astype(np.int64)
    frac = xy - base
    for dy in (0, 1):
        for dx in (0, 1):
            ij = base + [dx, dy]
            ok = (ij[:, 0] >= 0) & (ij[:, 0] < w) & (ij[:, 1] >= 0) & (ij[:, 1] < h)
            weight = (frac[:, 0] if dx else 1-frac[:, 0]) * (frac[:, 1] if dy else 1-frac[:, 1])
            index = ij[ok, 1]*w + ij[ok, 0]
            for c in range(values.shape[1]):
                out[:, c] += np.bincount(index, weights=weight[ok]*values[ok, c], minlength=h*w)
    return out.reshape(h, w, -1)


def adaptive_kde(xy, values, shape):
    """Quantized sample-adaptive normalized KDE, with explicit denominator."""
    xy = np.asarray(xy, dtype=np.float64)
    values = np.asarray(values, dtype=np.float64)
    if values.ndim == 1:
        values = values[:, None]
    if not np.isfinite(xy).all() or not np.isfinite(values).all():
        raise ValueError('KDE requires finite coordinates and attributes')
    count = bilinear_splat(xy, np.ones(len(xy)), shape)[..., 0]
    pilot = ndi.gaussian_filter(count, 4., mode='constant', truncate=4.)
    sampled = ndi.map_coordinates(pilot, xy.T[::-1], order=1, mode='constant', prefilter=False)
    positive = sampled > 0
    g = np.exp(np.mean(np.log(sampled[positive]))) if positive.any() else 1.
    adaptive = np.clip(2*np.sqrt(g/np.maximum(sampled, 1e-15)), 1, 4)
    which = np.argmin(np.abs(np.log(adaptive[:, None]/BANDWIDTHS)), axis=1)
    density = np.zeros(shape, dtype=np.float64)
    numerator = np.zeros((*shape, values.shape[1]), dtype=np.float64)
    for i, sigma in enumerate(BANDWIDTHS):
        ok = which == i
        if not ok.any():
            continue
        raster = bilinear_splat(xy[ok], np.c_[np.ones(ok.sum()), values[ok]], shape)
        smooth = ndi.gaussian_filter(raster, (sigma, sigma, 0), mode='constant', truncate=4.)
        density += smooth[..., 0]
        numerator += smooth[..., 1:]
    return {'density': density, 'numerator': numerator,
            'normalized': numerator / np.maximum(density[..., None], 1e-15),
            'pilot': pilot, 'bandwidth': BANDWIDTHS[which], 'pilot_geomean': float(g)}


def gradient_energy(field):
    a = np.asarray(field, dtype=np.float64)
    if a.ndim == 2:
        a = a[..., None]
    gx = ndi.gaussian_filter(a, (1, 1, 0), order=(0, 1, 0), mode='nearest', truncate=4.)
    gy = ndi.gaussian_filter(a, (1, 1, 0), order=(1, 0, 0), mode='nearest', truncate=4.)
    return np.sqrt(np.sum(gx*gx + gy*gy, axis=-1))


def ridge_response(field, scales=SCALES):
    """Scale-normalized anisotropic positive Hessian response and NMS seeds."""
    field = np.asarray(field, dtype=np.float64)
    best = np.zeros_like(field); seeds = np.zeros_like(field); winning = np.zeros_like(field)
    yy, xx = np.indices(field.shape, dtype=np.float64)
    for sigma in scales:
        hxx = sigma**2 * ndi.gaussian_filter(field, sigma, order=(0, 2), mode='nearest', truncate=4.)
        hyy = sigma**2 * ndi.gaussian_filter(field, sigma, order=(2, 0), mode='nearest', truncate=4.)
        hxy = sigma**2 * ndi.gaussian_filter(field, sigma, order=(1, 1), mode='nearest', truncate=4.)
        h = np.empty((*field.shape, 2, 2))
        h[..., 0, 0] = hxx; h[..., 1, 1] = hyy
        h[..., 0, 1] = hxy; h[..., 1, 0] = hxy
        vals, vecs = np.linalg.eigh(h)
        choose = np.abs(vals[..., 1]) > np.abs(vals[..., 0])
        large = np.where(choose, vals[..., 1], vals[..., 0])
        small = np.where(choose, vals[..., 0], vals[..., 1])
        direction = np.where(choose[..., None], vecs[..., :, 1], vecs[..., :, 0])
        ratio = np.abs(small) / np.maximum(np.abs(large), 1e-15)
        response = np.abs(large)*np.exp(-.5*(np.abs(small)/(np.abs(large)*.5+1e-15))**2)
        response[(large >= 0) | (ratio >= .5)] = 0
        plus = ndi.map_coordinates(response, [yy+direction[..., 1], xx+direction[..., 0]],
                                   order=1, mode='constant', prefilter=False)
        minus = ndi.map_coordinates(response, [yy-direction[..., 1], xx-direction[..., 0]],
                                    order=1, mode='constant', prefilter=False)
        keep = (response >= plus) & (response >= minus) & ((response > plus) | (response > minus))
        seeds = np.maximum(seeds, response*keep)
        winning = np.where(response > best, sigma, winning)
        best = np.maximum(best, response)
    return {'response': best, 'seed_score': seeds, 'winning_scale': winning}


def broad_score(score, support):
    return ndi.maximum_filter(score, footprint=disk(1), mode='constant') * support


def pooled_select(scores, supports, count):
    """Exactly count positive pixels, globally ranked with stable tie-breaking."""
    shapes = [a.shape for a in scores]
    sizes = [a.size for a in scores]
    flat = np.concatenate([np.asarray(a).ravel() for a in scores])
    valid = np.concatenate([np.asarray(a, dtype=bool).ravel() for a in supports]) & (flat > 0)
    ids = np.flatnonzero(valid)
    ids = ids[np.argsort(-flat[ids], kind='stable')]
    n = min(max(int(count), 0), len(ids))
    selected = np.zeros(len(flat), dtype=bool); selected[ids[:n]] = True
    masks = [a.reshape(shape) for a, shape in zip(np.split(selected, np.cumsum(sizes)[:-1]), shapes)]
    return masks, {'requested': int(count), 'selected': n, 'positive_candidates': len(ids),
                   'threshold': float(flat[ids[n-1]]) if n else None,
                   'tie_rule': 'stable scene order then row-major pixel index'}


def clean_mask(mask, min_area=12):
    labels, _ = ndi.label(mask, structure=np.ones((3, 3)))
    area = np.bincount(labels.ravel())
    keep = area >= min_area; keep[0] = False
    return keep[labels]


def mask_metrics(mask, support):
    mask = np.asarray(mask, dtype=bool); support = np.asarray(support, dtype=bool)
    labels, count = ndi.label(mask, structure=np.ones((3, 3)))
    area = np.bincount(labels.ravel(), minlength=count+1)
    skel = skeletonize(mask)
    lengths = np.bincount(labels[skel], minlength=count+1)
    long_ids = np.flatnonzero(lengths >= 24)
    long_ids = long_ids[long_ids != 0]
    ink = int(mask.sum()); supported = int(support.sum())
    widths = 2*ndi.distance_transform_edt(mask)[skel]
    return {'ink_pixels': ink, 'ink_canvas': ink/mask.size, 'ink_support': ink/max(supported, 1),
            'support_overlap': float((mask & support).sum()/max(ink, 1)),
            'components': int(count), 'fragments': int(np.count_nonzero(lengths[1:] < 24)),
            'fragments_per_10000_support': float(np.count_nonzero(lengths[1:] < 24)*10000/max(supported, 1)),
            'long_component_fraction': float(area[long_ids].sum()/max(ink, 1)),
            'skeleton_pixels': int(skel.sum()),
            'median_width_px': float(np.median(widths)) if len(widths) else 0.}
