"""Identified actual raster support and independent continuous visibility.

No stroke generation, style change, GPU, training, or prior-output mutation.
The diagnostic is deliberately narrower than subpixel centerline tracking.
"""
import os
os.environ['CUDA_VISIBLE_DEVICES'] = ''
for key in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS',
            'NUMEXPR_NUM_THREADS', 'VECLIB_MAXIMUM_THREADS'):
    os.environ[key] = '2'
os.sched_setaffinity(0, sorted(os.sched_getaffinity(0))[:2])
import hashlib
import numpy as np
from scipy import ndimage
from scipy.spatial import cKDTree
from PIL import Image
import core


def match_support(uv, pixels):
    """Only caller-supplied SAME-ID observed pixels can support a sample."""
    if len(pixels) == 0:
        return np.full(len(uv), np.inf), np.full(uv.shape, np.nan)
    d, j = cKDTree(pixels).query(uv, workers=1)
    return d, pixels[j] - uv


def shift_image(a, dx, dy):
    out = np.zeros_like(a)
    h, w = a.shape[:2]
    x0, x1 = max(0, -dx), min(w, w-dx)
    y0, y1 = max(0, -dy), min(h, h-dy)
    if x1 > x0 and y1 > y0:
        out[y0+dy:y1+dy, x0+dx:x1+dx] = a[y0:y1, x0:x1]
    return out


def downsample(a, scale=2):
    h, w = a.shape
    return np.asarray(Image.fromarray(np.uint8(np.clip(a, 0, 1)*255)).resize(
        (w//scale, h//scale), Image.Resampling.LANCZOS))


def layer_crop(q, ink, parts, scale, width):
    """Exact phase-aligned local raster, including finite LANCZOS support."""
    if len(q) == 0:
        return 0, 0, np.zeros((0, 0), np.uint8), None
    h, w = parts.shape
    lo = np.maximum(0, (q.min(axis=0)-8)//scale*scale)
    hi = np.minimum([w, h], (q.max(axis=0)+9+scale-1)//scale*scale)
    x0, y0 = lo; x1, y1 = hi
    a = np.zeros((y1-y0, x1-x0))
    a[q[:, 1]-y0, q[:, 0]-x0] = ink
    a = ndimage.maximum_filter(a, size=width)
    a[parts[y0:y1, x0:x1] == 0] = 0
    return int(x0//scale), int(y0//scale), downsample(a, scale), (lo, hi)


def analytic_rays(asset, c, uv):
    """First positive intersection with continuous profile surfaces.

    Uses arbitrary subpixel rays, never mesh z-buffer or stroke output.
    Ray parameter is camera optical z because camera ray z is one.
    """
    ray = np.column_stack(((uv-c['center'])/c['focal'], np.ones(len(uv)))) @ c['R']
    o = c['eye']; best = np.full(len(uv), np.inf); parts = np.zeros(len(uv), np.int16)
    def submit(t, valid, part):
        take = valid & np.isfinite(t) & (t > 0) & (t < best)
        best[take] = t[take]; parts[take] = part
    for part, profile in asset['profiles_ry'].items():
        for (r0, y0), (r1, y1) in zip(profile[:-1], profile[1:]):
            if abs(y1-y0) < 1e-12:
                t = np.divide(y0-o[1], ray[:, 1], out=np.full(len(uv), np.inf), where=abs(ray[:, 1]) > 1e-12)
                with np.errstate(invalid='ignore'):
                    radius = np.hypot(o[0]+t*ray[:, 0], o[2]+t*ray[:, 2])
                submit(t, (radius >= min(r0, r1)-1e-10) & (radius <= max(r0, r1)+1e-10), int(part))
                continue
            slope = (r1-r0)/(y1-y0); intercept = r0-slope*y0
            ro = slope*o[1]+intercept; rd = slope*ray[:, 1]
            a = ray[:, 0]**2+ray[:, 2]**2-rd**2
            b = 2*(o[0]*ray[:, 0]+o[2]*ray[:, 2]-ro*rd)
            cc = o[0]**2+o[2]**2-ro**2
            discriminant = b*b-4*a*cc
            root = np.sqrt(np.maximum(discriminant, 0))
            for sign in (-1, 1):
                t = np.divide(-b+sign*root, 2*a, out=np.full(len(uv), np.inf), where=abs(a) > 1e-12)
                linear = (abs(a) <= 1e-12) & (abs(b) > 1e-12)
                t[linear] = -cc/b[linear]
                with np.errstate(invalid='ignore'):
                    yy = o[1]+t*ray[:, 1]
                submit(t, (discriminant >= 0) & (yy >= min(y0, y1)-1e-10) &
                       (yy <= max(y0, y1)+1e-10), int(part))
    return best, parts


def load_strokes(path):
    z = np.load(path)
    return [{'id': str(z['ids'][i]), 'part': int(z['parts'][i]),
             'faces': z['faces'][a:b], 'bary': z['bary'][a:b], 'ink': float(z['inks'][i])}
            for i, (a, b) in enumerate(zip(z['offsets'][:-1], z['offsets'][1:]))]


def sample_paths(mesh, strokes, spacing):
    xyz, owners, weights, offsets = [], [], [], [0]
    for i, s in enumerate(strokes):
        points = core.anchor_points(mesh, s)
        lengths = np.linalg.norm(np.diff(points, axis=0), axis=1)
        good = lengths > 1e-14
        starts, ends, lengths = points[:-1][good], points[1:][good], lengths[good]
        arc = np.r_[0., np.cumsum(lengths)]; total = arc[-1]
        if total <= 0:
            offsets.append(offsets[-1]); continue
        n = int(np.ceil(total/spacing)); t = (np.arange(n)+.5)*total/n
        j = np.searchsorted(arc, t, side='right')-1
        p = starts[j]+((t-arc[j])/lengths[j])[:, None]*(ends[j]-starts[j])
        xyz.append(p); owners.append(np.full(n, i, np.int32)); weights.append(np.full(n, total/n))
        offsets.append(offsets[-1]+n)
    return {'xyz': np.concatenate(xyz), 'owner': np.concatenate(owners),
            'weight': np.concatenate(weights), 'offsets': np.array(offsets),
            'parts': np.concatenate([np.full(offsets[i+1]-offsets[i], s['part'], np.int16)
                                     for i, s in enumerate(strokes)])}


def expected_samples(samples, asset, c, boundary_band=2, tolerance=.006):
    uv, z = core.project(samples['xyz'], c)
    refz, refpart = analytic_rays(asset, c, uv)
    _, partmap = core.analytic_reference(asset, c)
    bd = ndimage.distance_transform_edt(~core.contour_mask(partmap))
    pix = np.rint(uv).astype(int)
    inside = (z > 0) & (pix[:, 0] >= 0) & (pix[:, 0] < c['size']) & (pix[:, 1] >= 0) & (pix[:, 1] < c['size'])
    band = np.zeros(len(uv), bool)
    band[inside] = bd[pix[inside, 1], pix[inside, 0]] <= boundary_band
    # Mutually exclusive exclusions, plus independent pre-band visibility.
    visible = inside & (refpart == samples['parts']) & (abs(z-refz) <= tolerance)
    code = np.zeros(len(uv), np.uint8)
    code[~inside] = 1
    code[inside & ~np.isfinite(refz)] = 2
    code[inside & np.isfinite(refz) & (refpart != samples['parts'])] = 3
    code[inside & (refpart == samples['parts']) & (abs(z-refz) > tolerance)] = 4
    code[visible & band] = 5
    return {'uv': uv, 'expected_depth': refz, 'sample_depth': z, 'code': code,
            'visible': visible, 'eligible_geometry': code == 0,
            'partmap': partmap}


def drop_id(stroke_id):
    return int(hashlib.sha256(stroke_id.encode('utf-8')).hexdigest(), 16) % 5 == 0


def instrumented_render(mesh, strokes, cfg, params, drop_active):
    scale = cfg['renderer']['supersample']; size = cfg['renderer']['resolution'][0]
    c = core.camera(params['azimuth_deg'], params['elevation_deg'], params['distance'],
                    size*scale, cfg['renderer']['focal_px']*scale)
    depth, parts = core.raster_surface(mesh, c)
    width = max(1, round(cfg['strokes']['screen_width_px']*scale))
    raw = np.zeros(depth.shape); raw_drop = np.zeros(depth.shape); layers = []
    for s in strokes:
        points = core.dense_path(core.anchor_points(mesh, s), c)
        uv, _ = core.project(points, c); pix = np.rint(uv).astype(int)
        q = pix[core.visible_points(points, c, depth, cfg['renderer']['visibility_tolerance_world'])]
        q = q[parts[q[:, 1], q[:, 0]] > 0]
        if len(q):
            np.maximum.at(raw, (q[:, 1], q[:, 0]), s['ink'])
            if not (drop_active and drop_id(s['id'])):
                np.maximum.at(raw_drop, (q[:, 1], q[:, 0]), s['ink'])
        layers.append(layer_crop(q, s['ink'], parts, scale, width)[:3])
    hatch = ndimage.maximum_filter(raw, size=width); hatch[parts == 0] = 0
    drop = ndimage.maximum_filter(raw_drop, size=width); drop[parts == 0] = 0
    allink = hatch.copy(); allink[core.contour_mask(parts)] = .92
    for part, profile in cfg['asset']['profiles_ry'].items():
        for r, y in profile:
            if r < .1: continue
            theta = np.linspace(0, 2*np.pi, 385)
            points = np.column_stack((r*np.cos(theta), np.full_like(theta, y), r*np.sin(theta)))
            points = core.dense_path(points, c)
            uv, _ = core.project(points, c); pix = np.rint(uv).astype(int)
            q = pix[core.visible_points(points, c, depth, cfg['renderer']['visibility_tolerance_world'])]
            q = q[parts[q[:, 1], q[:, 0]] > 0]
            if len(q): allink[q[:, 1], q[:, 0]] = .85
    # Same quantization then /255*255 conversion as inherited image_save.
    full = np.uint8((downsample(1-allink, scale)/255.)*255.)
    hatch = downsample(hatch, scale); drop = downsample(drop, scale)
    count = np.zeros((size, size), np.uint16)
    for x0, y0, a in layers:
        count[y0:y0+a.shape[0], x0:x0+a.shape[1]] += a > 0
    return {'full': full, 'hatch': hatch, 'drop': drop, 'layers': layers, 'count': count}


def ambiguous_samples(uv, count, radius=1.5):
    mask = np.zeros(len(uv), bool); center = np.rint(uv).astype(int)
    for dx in range(-2, 3):
        for dy in range(-2, 3):
            pix = center + [dx, dy]
            valid = (np.linalg.norm(pix-uv, axis=1) <= radius) & (pix[:, 0] >= 0) & (pix[:, 0] < count.shape[1]) & (pix[:, 1] >= 0) & (pix[:, 1] < count.shape[0])
            take = np.flatnonzero(valid)
            mask[take] |= count[pix[take, 1], pix[take, 0]] > 1
    return mask


def observe(samples, uv, render, strokes, drift_active, drop_active):
    n = len(uv)
    distance = np.full((3, n), np.inf); offset = np.full((3, n, 2), np.nan)
    provenance_xy, provenance_owner = [], []
    drift = shift_image(render['hatch'], 6, 6) if drift_active else render['hatch'].copy()
    for i, (x0, y0, a) in enumerate(render['layers']):
        count = render['count'][y0:y0+a.shape[0], x0:x0+a.shape[1]]
        comp = render['hatch'][y0:y0+a.shape[0], x0:x0+a.shape[1]]
        yy, xx = np.nonzero((a/255. > .04) & (comp/255. > .04) & (count == 1))
        pixels = np.column_stack((xx+x0, yy+y0))
        provenance_xy.append(pixels); provenance_owner.append(np.full(len(pixels), i, np.int16))
        lo, hi = samples['offsets'][i:i+2]
        distance[0, lo:hi], offset[0, lo:hi] = match_support(uv[lo:hi], pixels)
        shifted = pixels + ([6, 6] if drift_active else [0, 0])
        valid = (shifted[:, 0] < drift.shape[1]) & (shifted[:, 1] < drift.shape[0])
        shifted = shifted[valid]
        shifted = shifted[drift[shifted[:, 1], shifted[:, 0]]/255. > .04]
        distance[1, lo:hi], offset[1, lo:hi] = match_support(uv[lo:hi], shifted)
        if drop_active and drop_id(strokes[i]['id']):
            observed_drop = np.empty((0, 2), int)
        else:
            observed_drop = pixels[render['drop'][pixels[:, 1], pixels[:, 0]]/255. > .04]
        distance[2, lo:hi], offset[2, lo:hi] = match_support(uv[lo:hi], observed_drop)
    return {'distance': distance, 'offset': offset, 'drift': drift,
            'provenance_xy': np.concatenate(provenance_xy).astype(np.int16),
            'provenance_owner': np.concatenate(provenance_owner)}


def weighted_stats(values, weights):
    valid = np.isfinite(values) & (weights > 0)
    if not valid.any():
        return {'count': 0, 'weight_world': 0., 'mean': None, 'p95': None, 'max': None}
    v, w = values[valid], weights[valid]; order = np.argsort(v)
    p95 = v[order][np.searchsorted(np.cumsum(w[order]), .95*w.sum())]
    return {'count': int(valid.sum()), 'weight_world': float(w.sum()),
            'mean': float(np.average(v, weights=w)), 'p95': float(p95), 'max': float(v.max())}


def frame_summary(samples, expected, ambiguity, observation, subset=None):
    w = samples['weight']; subset = np.ones(len(w), bool) if subset is None else subset
    eligible = expected['eligible_geometry'] & ~ambiguity & subset
    total = float(w[subset].sum()); denom = float(w[eligible].sum())
    visible = float(w[subset & expected['visible']].sum())
    out = {'total_samples': int(subset.sum()), 'total_length_world': total,
           'visible_length_world': visible, 'eligible_samples': int(eligible.sum()),
           'eligible_length_world': denom, 'eligible_fraction_of_total': denom/total if total else None,
           'eligible_fraction_of_visible': denom/visible if visible else None,
           'eligible_strokes': int(len(np.unique(samples['owner'][eligible]))),
           'exclusions': {str(k): {'samples': int((subset & (expected['code'] == k)).sum()),
                                  'length_world': float(w[subset & (expected['code'] == k)].sum())}
                          for k in range(1, 6)},
           'overlap_ambiguous_after_geometry': {'samples': int((subset & expected['eligible_geometry'] & ambiguity).sum()),
                                               'length_world': float(w[subset & expected['eligible_geometry'] & ambiguity].sum())},
           'variants': {}}
    for v, name in enumerate(('baseline', 'drift', 'drop')):
        d = observation['distance'][v]; detected = d <= 1.5
        out['variants'][name] = {'missing_samples': int((eligible & ~detected).sum()),
                                'missing_fraction': float(w[eligible & ~detected].sum()/denom) if denom else None,
                                'finite_support_distance_px': weighted_stats(d[eligible], w[eligible]),
                                'detected_support_distance_px': weighted_stats(d[eligible & detected], w[eligible & detected])}
    return out


def pair_summary(samples, previous, current, subset=None):
    w = samples['weight']; subset = np.ones(len(w), bool) if subset is None else subset
    bothvisible = previous['visible'] & current['visible'] & subset
    geometry = previous['eligible_geometry'] & current['eligible_geometry'] & subset
    eligible = geometry & ~previous['ambiguity'] & ~current['ambiguity']
    den = float(w[eligible].sum()); vis = float(w[bothvisible].sum()); total = float(w[subset].sum())
    out = {'common_samples': int(eligible.sum()), 'common_length_world': den,
           'jointly_visible_length_world': vis, 'joint_geometry_length_world': float(w[geometry].sum()),
           'total_length_world': total, 'common_fraction_of_total': den/total if total else None,
           'common_fraction_of_jointly_visible': den/vis if vis else None,
           'common_strokes': int(len(np.unique(samples['owner'][eligible]))), 'variants': {}}
    for v, name in enumerate(('baseline', 'drift', 'drop')):
        a = previous['distance'][v] <= 1.5; b = current['distance'][v] <= 1.5
        masks = {'both_detected': a & b, 'disappearance': a & ~b,
                 'reappearance': ~a & b, 'both_missing': ~a & ~b}
        events = {k: {'samples': int((eligible & m).sum()),
                      'length_world': float(w[eligible & m].sum()),
                      'fraction': float(w[eligible & m].sum()/den) if den else None}
                  for k, m in masks.items()}
        selected = eligible & a & b
        residual = np.linalg.norm(current['offset'][v, selected]-previous['offset'][v, selected], axis=1)
        events['raster_support_reprojection_residual_px'] = weighted_stats(residual, w[selected])
        out['variants'][name] = events
    return out
