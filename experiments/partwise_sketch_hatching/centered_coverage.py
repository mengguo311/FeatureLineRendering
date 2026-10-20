"""Experimental finite butt-cap coverage; unchanged mesh visibility downstream.

Closed integer-site support, not pixel area integration or a general join rule.
No analytic reference geometry is accepted by this module.
"""
import round010_common
import numpy as np
from PIL import Image
import core
import visibility_primitive as visibility

BOUNDARY_EPS = 1e-9


def ribbon_mask(projected_path, size, width=2.):
    p = np.asarray(projected_path, float)
    if p.ndim != 2 or p.shape[1] != 2 or len(p) < 2 or not np.isfinite(p).all():
        raise ValueError('finite projected path (N>=2,2) required')
    if not np.isfinite(width) or width <= 0:
        raise ValueError('positive finite ribbon width required')
    yy, xx = np.mgrid[:size, :size]
    grid = np.stack((xx, yy), axis=-1)
    result = np.zeros((size, size), bool)
    for a, b in zip(p[:-1], p[1:]):
        d = b-a
        length = np.linalg.norm(d)
        if length <= 1e-12:
            raise ValueError('zero projected segment length')
        n = np.array([-d[1], d[0]]) * (width/(2*length))
        polygon = np.array([a+n, a-n, b-n, b+n])
        inside = np.ones(result.shape, bool)
        for start, end in zip(polygon, np.roll(polygon, -1, axis=0)):
            edge = end-start
            q = grid-start
            signed_distance = (edge[0]*q[..., 1]-edge[1]*q[..., 0])/np.linalg.norm(edge)
            inside &= signed_distance >= -BOUNDARY_EPS
        result |= inside
    return result


def render(mesh, owner_faces, path, c, ink=.8, scale=2, width=2.,
           tolerance=visibility.DEPTH_TOLERANCE):
    uv, z = core.project(path, c)
    if not np.isfinite(z).all() or np.any(z <= 0):
        raise ValueError('positive finite endpoint optical depth required')
    mask = ribbon_mask(uv, c['size'], width)
    footprint = mask.astype(float)*ink
    depth, parts = core.raster_surface(mesh, c)
    yy, xx = np.nonzero(mask)
    own, face = visibility.owner_depth(mesh, owner_faces, c, np.column_stack((xx, yy)))
    keep = visibility.visibility_gate(own, depth[yy, xx], tolerance)
    high = np.zeros(depth.shape)
    high[yy[keep], xx[keep]] = ink
    ownmap = np.full(depth.shape, np.inf); ownmap[yy, xx] = own
    facemap = np.full(depth.shape, -1, np.int32); facemap[yy, xx] = face
    gate = np.zeros(depth.shape, bool); gate[yy, xx] = keep
    quantized = np.uint8(np.clip(high, 0, 1)*255)
    final = np.asarray(Image.fromarray(quantized).resize(
        (c['size']//scale, c['size']//scale), Image.Resampling.LANCZOS))
    return {'footprint': footprint, 'owner_depth': ownmap, 'owner_face': facemap,
            'scene_depth': depth, 'scene_owner': parts, 'gate': gate, 'high': high,
            'quantized_uint8': quantized, 'final_uint8': final, 'projected_path': uv}
