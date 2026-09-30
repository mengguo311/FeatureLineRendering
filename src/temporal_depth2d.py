"""View-dependent 2D polylines; renderer-depth transport is bookkeeping only."""
import hashlib
import json
import os
from pathlib import Path
import cv2
import numpy as np
from scipy import ndimage as ndi
from scipy.spatial import cKDTree
from skimage.morphology import skeletonize

SEED = 20260930


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


def atomic_json(path, value):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + '.tmp')
    with temp.open('w') as f:
        json.dump(value, f, indent=2, allow_nan=False); f.write('\n'); f.flush(); os.fsync(f.fileno())
    os.replace(temp, path)


def validate_camera(camera):
    k = np.asarray(camera['native_K'], float); w = np.asarray(camera['w2c'], float)
    if k.shape != (3, 3) or w.shape != (4, 4) or not np.isfinite(k).all() or not np.isfinite(w).all():
        raise ValueError('nonfinite or malformed camera')
    if k[0, 0] <= 0 or k[1, 1] <= 0 or abs(np.linalg.det(k)) < 1e-10:
        raise ValueError('invalid intrinsics')
    if not np.allclose(w[3], [0, 0, 0, 1], atol=1e-5) or not np.allclose(w[:3, :3] @ w[:3, :3].T, np.eye(3), atol=1e-5) or abs(np.linalg.det(w[:3, :3]) - 1) > 1e-5:
        raise ValueError('nonrigid pose')
    if camera['native_width'] <= 0 or camera['native_height'] <= 0:
        raise ValueError('invalid image size')


def world_points(xy, depth, camera):
    validate_camera(camera)
    inv = np.linalg.inv(np.asarray(camera['w2c'], float))
    rays = np.c_[xy, np.ones(len(xy))] @ np.linalg.inv(camera['native_K']).T
    return (rays * np.asarray(depth)[:, None]) @ inv[:3, :3].T + inv[:3, 3]


def project_world(world, camera):
    validate_camera(camera)
    w = np.asarray(camera['w2c'], float)
    p = world @ w[:3, :3].T + w[:3, 3]; h = p @ np.asarray(camera['native_K']).T
    return h[:, :2] / np.maximum(h[:, 2:], 1e-12), p[:, 2]


def project_points(xy, depth, source, target):
    return project_world(world_points(xy, depth, source), target)


def visible_points(xy, z, frame):
    h, w = frame['depth'].shape
    good = np.isfinite(xy).all(1) & np.isfinite(z) & (z > 0)
    pix = np.rint(np.nan_to_num(xy)).astype(int)
    good &= (pix[:, 0] >= 0) & (pix[:, 0] < w) & (pix[:, 1] >= 0) & (pix[:, 1] < h)
    xx = pix[:, 0].clip(0, w - 1); yy = pix[:, 1].clip(0, h - 1)
    depth = frame['depth'][yy, xx]; tol = np.maximum(.02 * z, .01)
    known = (frame['alpha'][yy, xx] >= .5) & np.isfinite(depth) & (depth > 0)
    occluded = good & known & (z > depth + tol)
    good &= known & (abs(z - depth) <= tol)
    return pix, good, occluded


def transport(ink, source, target):
    """Forward z-tested ink splat plus independently backward-tested target support."""
    y, x = np.nonzero(np.asarray(ink) > 0)
    known = (source['alpha'][y, x] >= .5) & np.isfinite(source['depth'][y, x]) & (source['depth'][y, x] > 0)
    xy, z = project_points(np.c_[x[known], y[known]], source['depth'][y[known], x[known]], source['camera'], target['camera'])
    pix, good, occluded = visible_points(xy, z, target)
    out = np.zeros_like(target['depth'], dtype=float)
    np.maximum.at(out, (pix[good, 1], pix[good, 0]), np.asarray(ink)[y[known][good], x[known][good]])
    yy, xx = np.nonzero((target['alpha'] >= .5) & np.isfinite(target['depth']) & (target['depth'] > 0))
    back, zz = project_points(np.c_[xx, yy], target['depth'][yy, xx], target['camera'], source['camera'])
    _, support, _ = visible_points(back, zz, source)
    valid = np.zeros_like(out, dtype=bool); valid[yy[support], xx[support]] = True
    return out, valid, dict(accepted=int(good.sum()), source_ink_pixels=len(x), unknown=int((~known).sum()), occluded=int(occluded.sum()), rejected=int(len(good) - good.sum()), target_valid_pixels=int(valid.sum()))


def depth2d(edge):
    return cv2.dilate(np.asarray(edge, 'u1'), np.ones((2, 2), 'u1')).astype(float)


def graph(mask):
    """All skeleton vertices; maximal chains, junctions and isolated vertices retained."""
    sk = skeletonize(np.asarray(mask, bool)); y, x = np.nonzero(sk); xy = np.c_[x, y].astype(float)
    lookup = {(int(a), int(b)): i for i, (a, b) in enumerate(xy)}
    adj = [[] for _ in xy]
    for i, (a, b) in enumerate(xy.astype(int)):
        for dx, dy in [(-1,-1),(0,-1),(1,-1),(-1,0),(1,0),(-1,1),(0,1),(1,1)]:
            j = lookup.get((a + dx, b + dy))
            if j is not None:
                # Prevent diagonal shortcut around a connected orthogonal corner.
                if dx and dy and ((a + dx, b) in lookup or (a, b + dy) in lookup):
                    continue
                adj[i].append(j)
    used = set(); chains = []
    def walk(a, b):
        chain = [a]; prev, cur = a, b; used.add(tuple(sorted((a, b))))
        while True:
            chain.append(cur)
            if len(adj[cur]) != 2: break
            nxt = adj[cur][0] if adj[cur][0] != prev else adj[cur][1]
            edge = tuple(sorted((cur, nxt)))
            if edge in used: break
            used.add(edge); prev, cur = cur, nxt
        return np.asarray(chain, int)
    for i, neighbors in enumerate(adj):
        if not neighbors: chains.append(np.array([i]))
        elif len(neighbors) != 2:
            for j in neighbors:
                if tuple(sorted((i, j))) not in used: chains.append(walk(i, j))
    for i, neighbors in enumerate(adj):
        for j in neighbors:
            if tuple(sorted((i, j))) not in used: chains.append(walk(i, j))
    return xy, chains


def texture(ids):
    ids = np.asarray(ids, dtype=np.int64)
    return .90 + .10 * ((ids * 1103515245 + SEED) % 65521) / 65520.


class Tracker:
    def __init__(self):
        self.anchors = {}; self.next_id = 0; self.step = 0; self.previous_components = {}; self.last_seen = {}

    def update(self, frame):
        xy, chains = graph(frame['mask']); labels, _ = ndi.label(frame['mask'], np.ones((3, 3)))
        pixel = np.rint(xy).astype(int); comp = labels[pixel[:, 1], pixel[:, 0]]
        ids = np.full(len(xy), -1, np.int64)
        active = sorted(k for k in self.anchors if self.step - self.last_seen[k] <= 66)
        if active and len(xy):
            projected, z = project_world(np.array([self.anchors[k] for k in active]), frame['camera'])
            _, valid, _ = visible_points(projected, z, frame)
            valid_ids = np.asarray(active)[valid]
            if valid.any():
                distance, near = cKDTree(projected[valid]).query(xy, distance_upper_bound=3.)
                matched = np.isfinite(distance); ids[matched] = valid_ids[near[matched]]
        old_visible = set(self.previous_components)
        appeared = sum(int(k >= 0 and k not in old_visible) for k in np.unique(ids))
        previous_to_current = {}; current_to_previous = {}
        for k, c in zip(ids, comp):
            if k in self.previous_components:
                p = self.previous_components[k]
                previous_to_current.setdefault(p, set()).add(int(c)); current_to_previous.setdefault(int(c), set()).add(p)
        events = dict(split=sum(len(c) > 1 for c in previous_to_current.values()), merge=sum(len(c) > 1 for c in current_to_previous.values()), reappeared=appeared, births=int((ids < 0).sum()), dormant=len(set(active) - set(ids)), visible_vertices=len(xy))
        for j in np.flatnonzero(ids < 0): ids[j] = self.next_id; self.next_id += 1
        if len(xy):
            world = world_points(xy, frame['depth'][pixel[:, 1], pixel[:, 0]], frame['camera'])
            known = (frame['alpha'][pixel[:, 1], pixel[:, 0]] >= .5) & (frame['depth'][pixel[:, 1], pixel[:, 0]] > 0)
            for k, point, valid_anchor in zip(ids, world, known):
                # Only known surface points may become transport anchors.
                if valid_anchor and np.isfinite(point).all(): self.anchors[int(k)] = point; self.last_seen[int(k)] = self.step
        self.previous_components = {int(k): int(c) for k, c in zip(ids, comp)}; self.step += 1
        return dict(xy=xy, chains=chains, ids=ids, events=events)


def render_vectors(xy, chains, ids, shape, edit=None):
    ink = np.zeros(shape, 'u1'); values = texture(ids)
    if edit is not None: values = values * np.where(ids == edit, .5, 1.)
    p = np.rint(xy * 16).astype(int)
    for chain in chains:
        if len(chain) == 1:
            i = chain[0]; cv2.circle(ink, tuple(p[i]), 8, int(round(255 * values[i])), -1, cv2.LINE_AA, shift=4)
        for a, b in zip(chain[:-1], chain[1:]):
            cv2.line(ink, tuple(p[a]), tuple(p[b]), int(round(255 * (values[a] + values[b]) / 2)), 2, cv2.LINE_AA, shift=4)
    return ink.astype(float) / 255


def atlas(frames):
    ordered = sorted(frames, key=lambda f: f['key'])
    if len({f['key'] for f in ordered}) != len(ordered): raise ValueError('duplicate frame keys')
    tracker = Tracker(); result = {}; base = {f['key']: graph(f['mask'])[0] for f in ordered}
    for i, f in enumerate(ordered):
        r = tracker.update(f); xy = r['xy']; shifts = np.zeros_like(xy); count = np.zeros(len(xy))
        for j in [i - 1, i + 1]:
            if j < 0 or j >= len(ordered) or not len(xy): continue
            neighbor = ordered[j]; points = base[neighbor['key']]
            if not len(points): continue
            pix = points.astype(int)
            known = (neighbor['alpha'][pix[:, 1], pix[:, 0]] >= .5) & np.isfinite(neighbor['depth'][pix[:, 1], pix[:, 0]]) & (neighbor['depth'][pix[:, 1], pix[:, 0]] > 0)
            points = points[known]; pix = pix[known]
            if not len(points): continue
            projected, z = project_points(points, neighbor['depth'][pix[:, 1], pix[:, 0]], neighbor['camera'], f['camera'])
            _, valid, _ = visible_points(projected, z, f)
            if not valid.any(): continue
            distance, near = cKDTree(projected[valid]).query(xy, distance_upper_bound=2.)
            good = np.isfinite(distance); shifts[good] += projected[valid][near[good]] - xy[good]; count[good] += 1
        shifts /= np.maximum(count[:, None], 1); shifts *= .5
        shifts /= np.maximum(np.linalg.norm(shifts, axis=1, keepdims=True), 1.)
        r['xy'] = xy + shifts; r['native'] = render_vectors(r['xy'], r['chains'], r['ids'], f['mask'].shape)
        result[f['key']] = r
    return result


def quantize(ink):
    return np.round(np.clip(ink, 0, 1) * 255).astype('u1').astype(float) / 255


def actual_ink(ink):
    return float(np.round(np.clip(ink, 0, 1) * 255).sum() / 255)


def match_ink(ink, target):
    original = np.asarray(ink, float); work = original.copy(); steps = 0; fraction = 0.
    if target <= 0: return quantize(work * 0), dict(opacity=0., dilations=0, fraction=0., deleted_components=0)
    while work.sum() < target and steps < 3:
        bigger = cv2.dilate(work, np.ones((3, 3), 'u1'))
        delta = bigger.sum() - work.sum()
        if delta <= 0: break
        fraction = min(1., (target - work.sum()) / delta); work = work + fraction * (bigger - work); steps += 1
    opacity = min(1., target / max(work.sum(), 1e-12)); out = quantize(work * opacity)
    return out, dict(opacity=float(opacity), dilations=steps, fraction=float(fraction), deleted_components=0, achieved=actual_ink(out), target=float(target))


def seal_directory(stage, dest, metadata):
    stage, dest = Path(stage), Path(dest)
    files = {str(p.relative_to(stage)): sha(p) for p in sorted(stage.rglob('*')) if p.is_file() and p.name != 'SEAL.json'}
    atomic_json(stage / 'SEAL.json', dict(metadata=metadata, files=files))
    if dest.exists(): raise ValueError('refusing overwrite of sealed unit')
    os.rename(stage, dest)
    directory_fd = os.open(dest.parent, os.O_RDONLY); os.fsync(directory_fd); os.close(directory_fd)


def verify_seal(dest, metadata):
    dest = Path(dest); seal = json.loads((dest / 'SEAL.json').read_text())
    if seal['metadata'] != metadata: raise ValueError('source/protocol seal mismatch')
    actual = {str(p.relative_to(dest)) for p in dest.rglob('*') if p.is_file() and p.name != 'SEAL.json'}
    if actual != set(seal['files']): raise ValueError('seal file census mismatch')
    for p, h in seal['files'].items():
        if sha(dest / p) != h: raise ValueError('corrupted sealed asset: ' + p)
    return True
