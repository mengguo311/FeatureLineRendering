"""Frozen A/typed-B skeleton paths and complete validation line evidence."""
import numpy as np
from scipy.ndimage import maximum_filter, convolve
from scipy.spatial import cKDTree
from skimage.morphology import skeletonize


def arclength(points):
    return float(np.linalg.norm(np.diff(np.asarray(points), axis=0), axis=1).sum())


def resample(points, n):
    points = np.asarray(points, dtype=float)
    if points.ndim != 2 or len(points) < 2 or not np.isfinite(points).all():
        raise ValueError('invalid path')
    s = np.r_[0., np.cumsum(np.linalg.norm(np.diff(points, axis=0), axis=1))]
    keep = np.r_[True, np.diff(s) > 1e-12]
    if s[-1] <= 0:
        raise ValueError('zero length path')
    return np.stack([np.interp(np.linspace(0, s[-1], n), s[keep], points[keep, d])
                     for d in range(points.shape[1])], axis=1)


def trace_paths(mask):
    """Trace each undirected 8-neighbor edge exactly once, no gap insertion."""
    nodes = set(map(tuple, np.argwhere(np.asarray(mask, dtype=bool))))
    neighbors = {p: sorted((p[0]+dy, p[1]+dx)
                           for dy in (-1, 0, 1) for dx in (-1, 0, 1)
                           if (dy or dx) and (p[0]+dy, p[1]+dx) in nodes)
                 for p in nodes}
    used = set()
    traces = []

    def edge(a, b):
        return (a, b) if a < b else (b, a)

    def walk(a, b):
        seq = [a, b]
        used.add(edge(a, b))
        while len(neighbors[b]) == 2:
            c = neighbors[b][0] if neighbors[b][1] == a else neighbors[b][1]
            if edge(b, c) in used:
                break
            used.add(edge(b, c))
            seq.append(c)
            a, b = b, c
        return np.asarray([(x, y) for y, x in seq], dtype=float)

    for a in sorted(nodes):
        if len(neighbors[a]) != 2:
            for b in neighbors[a]:
                if edge(a, b) not in used:
                    traces.append(walk(a, b))
    for a in sorted(nodes):
        for b in neighbors[a]:
            if edge(a, b) not in used:
                traces.append(walk(a, b))
    return traces


def evidence_mask(responses, native, cfg):
    e = cfg['extraction']
    a = np.asarray(responses['A']) >= e['a_threshold']
    bits = a.astype(np.uint8)
    for bit, name in enumerate(e['typed_b'], start=1):
        x = np.asarray(responses[name])
        finite = np.isfinite(x)
        local_max = maximum_filter(np.where(finite, x, -np.inf),
                                   size=2*e['typed_b_nms_radius']+1, mode='nearest')
        b = (finite & (x >= e['typed_b_threshold']) & (x == local_max) &
             (np.asarray(native['alpha']) >= e['alpha_min']))
        bits |= (b.astype(np.uint8) << bit)
    skeleton = skeletonize(bits != 0)
    return skeleton, bits


def extract_paths(responses, native, cfg, view):
    skeleton, source = evidence_mask(responses, native, cfg)
    degree = convolve(skeleton.astype(np.uint8), np.ones((3, 3), np.uint8),
                      mode='constant', cval=0)-skeleton.astype(np.uint8)
    e = cfg['extraction']
    records = []
    traces = trace_paths(skeleton)
    short = 0
    for trace in traces:
        length = arclength(trace)
        if length < e['path_min_length_px']:
            short += 1
            continue
        chunks = int(np.ceil(length/e['path_max_length_px']))
        s = np.r_[0., np.cumsum(np.linalg.norm(np.diff(trace, axis=0), axis=1))]
        for chunk in range(chunks):
            lo, hi = length*chunk/chunks, length*(chunk+1)/chunks
            inside = (s > lo) & (s < hi)
            endpoints = np.stack([np.interp([lo, hi], s, trace[:, d]) for d in range(2)], axis=1)
            raw = np.vstack([endpoints[0], trace[inside], endpoints[1]])
            n = e['sample_count']
            pts = resample(raw, n)
            vec = np.diff(pts, axis=0)
            norms = np.linalg.norm(vec, axis=1)
            cos = np.sum(vec[1:]*vec[:-1], axis=1)/np.maximum(norms[1:]*norms[:-1], 1e-12)
            curvature = np.arccos(np.clip(cos, -1, 1))/np.pi
            ix = np.clip(np.floor(raw[:, 0]+.5).astype(int), 0, skeleton.shape[1]-1)
            iy = np.clip(np.floor(raw[:, 1]+.5).astype(int), 0, skeleton.shape[0]-1)
            records.append(dict(points=pts, raw_points=raw, source_bits=int(np.bitwise_or.reduce(source[iy, ix])),
                                curvature=curvature, endpoint_degrees=degree[iy[[0, -1]], ix[[0, -1]]].tolist(),
                                length=arclength(raw), closed=bool(np.array_equal(raw[0], raw[-1]))))
    records.sort(key=lambda r: (-r['length'], tuple(r['raw_points'][0][::-1]), tuple(r['raw_points'][-1][::-1])))
    total = len(records)
    records = records[:cfg['budget']['max_paths_per_view']]
    for i, r in enumerate(records):
        r['id'] = f'{view}_path{i:03d}'
    return records, dict(skeleton_pixels=int(skeleton.sum()), traced_paths=len(traces),
                         short_paths_excluded=short, length_eligible_paths=total,
                         construction_paths=len(records), capacity_excluded=total-len(records))


class Evidence:
    """All unbudgeted skeleton pixels with unambiguous local tangent."""
    def __init__(self, responses, native, cfg):
        mask, _ = evidence_mask(responses, native, cfg)
        nodes = set(map(tuple, np.argwhere(mask)))
        xy, tangent = [], []
        for y, x in sorted(nodes):
            nei = [(x+dx, y+dy) for dy in (-1, 0, 1) for dx in (-1, 0, 1)
                   if (dy or dx) and (y+dy, x+dx) in nodes]
            if len(nei) == 1:
                t = np.asarray(nei[0])-np.array([x, y])
            elif len(nei) == 2:
                t = np.asarray(nei[1])-np.asarray(nei[0])
            else:
                continue
            norm = np.linalg.norm(t)
            if norm:
                xy.append((x, y)); tangent.append(t/norm)
        self.xy = np.asarray(xy, dtype=float).reshape(-1, 2)
        self.tangent = np.asarray(tangent, dtype=float).reshape(-1, 2)
        self.tree = cKDTree(self.xy)
        self.tol = cfg['validation_rules']['position_tolerance_px']
        self.cos = np.cos(np.deg2rad(cfg['validation_rules']['direction_tolerance_deg']))

    def candidates(self, uv, tangents):
        uv, tangents = np.asarray(uv), np.asarray(tangents)
        result = []
        for pos, tan in zip(uv, tangents):
            norm = np.linalg.norm(tan)
            if not np.isfinite(pos).all() or not np.isfinite(tan).all() or norm <= 1e-12:
                result.append(np.empty((0, 2))); continue
            ids = np.asarray(self.tree.query_ball_point(pos, self.tol), dtype=int)
            if len(ids):
                ids = ids[np.abs(self.tangent[ids] @ (tan/norm)) >= self.cos]
            result.append(self.xy[ids])
        return result
