"""Bounded axial style regeneration for the authored straight cylindrical stem.

This uses known GT geometry and a manual axial direction. It is not a general
mesh parameterization, learned direction field, or reconstruction method.
"""
from common import *
import time

STYLE = dict(part=2, count=8, y_min=.20, y_max=1.55,
             first_sector=1, sector_fraction=.37, angular_stride=12,
             screen_width_px=1., algorithm='uniform authored-cylinder sectors + v2 axial walk')


def regenerate_stem(mesh, strokes, cfg, style=None):
    start = time.perf_counter()
    style = dict(STYLE if style is None else style)
    if style != STYLE:
        raise ValueError('unit004 supports only the frozen eight-line style')
    if int(cfg['asset']['angular_segments']) != 96:
        raise ValueError('bounded style requires the authored 96-sector lamp')
    side = np.flatnonzero((mesh['parts'] == 2) & (np.abs(mesh['normals'][:, 1]) < 1e-10))
    if len(side) != 192:
        raise ValueError('expected the straight GT cylindrical side')
    radius = .075
    y = (style['y_min'] + style['y_max']) / 2
    generated, seeds = [], []
    for k in range(style['count']):
        j = style['first_sector'] + style['angular_stride'] * k
        angles = 2 * np.pi * np.array([j, j+1]) / 96
        xz = radius * np.stack((np.cos(angles), np.sin(angles)), axis=1)
        xz = (1-style['sector_fraction']) * xz[0] + style['sector_fraction'] * xz[1]
        point = np.array([xz[0], y, xz[1]])
        choices = []
        for face in side:
            bary = core.barycentric(mesh, face, point)
            if bary.min() >= -1e-12 and np.linalg.norm(bary @ mesh['tri'][face] - point) < 1e-10:
                choices.append((int(face), bary))
        if len(choices) != 1:
            raise ValueError('seed must lie strictly inside one side triangle')
        face, bary = choices[0]
        halves = []
        audits = [{}, {}]
        for i, sign in enumerate((-1, 1)):
            halves.append(walker.walk(mesh, face, bary, 2, 'mixed', 0, 0.,
                (style['y_max']-style['y_min'])/2, cfg['strokes']['step_world'], sign, audits[i]))
        (fa, ba), (fb, bb) = halves
        if any(a['reason'] != 'length_reached' for a in audits):
            raise ValueError('bounded axial path did not reach its fixed length')
        ink = .30 + .55 * (1-max(0., float(mesh['normals'][face] @ core.unit([-1, 2, 1]))))
        generated.append(dict(id=f'p2:axialv1_{k:04d}:layer0', part=2,
            faces=np.array(fa[::-1]+fb[1:], np.int32), bary=np.array(ba[::-1]+bb[1:]),
            ink=ink, style='mixed', layer=0, angle=0., walk_audit=audits))
        seeds.append(dict(index=k, sector=j, point=point, face=face, bary=bary, ink=ink, audit=audits))
    retained = [s for s in strokes if s['part'] != 2]
    output = sorted(retained + generated, key=lambda s:s['id'])
    return output, dict(style=style, seeds=seeds, regenerated_part=2,
        removed_ids=[s['id'] for s in strokes if s['part']==2],
        created_ids=[s['id'] for s in generated], non_target_strokes=len(retained),
        generation_seconds=time.perf_counter()-start,
        limitation='GT cylinder-specific/manual axial rule; new stem IDs; no general mesh spacing or tone fidelity claim')
