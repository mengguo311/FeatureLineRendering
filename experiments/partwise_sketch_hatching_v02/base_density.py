"""Nested selection of existing base seed pairs; no path regeneration.

Euclidean farthest-seed prefixes improve spatial dispersion of retained seeds.
They are not geodesic/Poisson spacing and do not bound overlap of whole curves.
"""
from common import *
import time


def base_seed_positions(mesh, cfg):
    """Replay only the frozen area-weighted seed sampler, not its curve walker."""
    rng = np.random.default_rng(np.random.SeedSequence([cfg['seed'], 3]))
    candidates = np.flatnonzero(mesh['parts'] == 3)
    probability = mesh['areas'][candidates] / mesh['areas'][candidates].sum()
    positions = {}
    for i in range(int(cfg['strokes']['counts_by_part']['3'])):
        face = int(rng.choice(candidates, p=probability))
        q = rng.random(2); sq = np.sqrt(q[0])
        bary = np.array([1-sq, sq*(1-q[1]), sq*q[1]])
        positions[f'p3:seed{i:04d}'] = bary @ mesh['tri'][face]
    return positions


def select_base_pairs(mesh, strokes, cfg, keep_pairs):
    start = time.perf_counter()
    positions = base_seed_positions(mesh, cfg)
    pairs = {}
    for stroke in strokes:
        if stroke['part'] != 3:
            continue
        pair, layer = stroke['id'].rsplit(':layer', 1)
        if layer not in ('0', '1') or layer in pairs.setdefault(pair, {}):
            raise ValueError('duplicate or unknown base layer')
        pairs[pair][layer] = stroke
    if set(pairs) != set(positions) or any(set(v) != {'0', '1'} for v in pairs.values()):
        raise ValueError('selection requires all original two-layer base seed pairs')
    if isinstance(keep_pairs, bool) or not isinstance(keep_pairs, int) or not 0 <= keep_pairs <= len(pairs):
        raise ValueError('keep_pairs must be an integer in the original pair range')
    # Confirm the sampled point is actually an anchor in both inherited paths.
    for pair, layers in pairs.items():
        for stroke in layers.values():
            points = core.anchor_points(mesh, stroke)
            if np.linalg.norm(points-positions[pair], axis=1).min() > 1e-10:
                raise ValueError(f'seed/path provenance mismatch: {stroke["id"]}')
    names = sorted(pairs)
    points = np.array([positions[name] for name in names])
    nearest = np.full(len(names), np.inf)
    available = np.ones(len(names), bool)
    order = []
    for _ in names:
        index = int(np.argmax(np.where(available, nearest, -np.inf)))
        order.append(names[index]); available[index] = False
        nearest = np.minimum(nearest, np.sum((points-points[index])**2, axis=1))
    selected = set(order[:keep_pairs])
    output = [s for s in strokes if s['part'] != 3 or s['id'].rsplit(':layer', 1)[0] in selected]
    record = dict(algorithm='Euclidean farthest seed; seed0000 first; lexical ID tie break; nested prefixes',
                  keep_pairs=keep_pairs, available_pairs=len(pairs), ordered_pair_ids=order,
                  selected_pair_ids=sorted(selected), seed_positions=positions,
                  selection_seconds=time.perf_counter()-start, retained_strokes=len(output),
                  non_target_strokes=sum(s['part'] != 3 for s in output),
                  limitation='Density proxy, not surface-geodesic or whole-curve minimum spacing; no rescaling of retained ink.')
    return output, record
