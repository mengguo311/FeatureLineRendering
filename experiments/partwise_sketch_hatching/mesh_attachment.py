"""Mesh-only explicit attachment contract, separate from visibility and truth.

Every supplied segment is straight. A convex triangle contains the whole segment
when both endpoints satisfy its plane and barycentric bounds. Validation never
projects points, welds topology, discovers owners, or changes caller objects.
"""
import numpy as np

WORLD_EPS = 1e-9
BARY_EPS = 1e-9
RELATIVE_AREA_EPS = 1e-12
MIN_EDGE = 1e-12


class AttachmentError(ValueError):
    def __init__(self, code, message):
        self.code = code
        super().__init__(f'{code}: {message}')


def fail(code, message):
    raise AttachmentError(code, message)


def integer_ids(value, code, ndim):
    a = np.asarray(value)
    if a.ndim != ndim or a.dtype.kind not in 'iu':
        fail(code, 'explicit integer indices required')
    return a


def validate_attachment(mesh, owner_faces, segment_faces, path):
    """Return original input references plus measured validation diagnostics."""
    v = np.asarray(mesh['vertices'], dtype=float)
    if v.ndim != 2 or v.shape[1] != 3 or len(v) < 3:
        fail('mesh_shape', 'vertices must have shape (N>=3,3)')
    if not np.isfinite(v).all():
        fail('mesh_nonfinite', 'nonfinite vertex coordinate')
    f = integer_ids(mesh['faces'], 'mesh_face_id', 2)
    if f.shape[1] != 3 or len(f) == 0 or np.any(f < 0) or np.any(f >= len(v)):
        fail('mesh_face_id', 'triangle indices out of range or malformed')
    tri = v[f]
    e0 = tri[:, 1] - tri[:, 0]
    e1 = tri[:, 2] - tri[:, 0]
    e2 = tri[:, 2] - tri[:, 1]
    edge_lengths2 = [np.sum(e*e, axis=1) for e in (e0, e1, e2)]
    max_edge2 = np.maximum.reduce(edge_lengths2)
    min_edge2 = np.minimum.reduce(edge_lengths2)
    cross = np.cross(e0, e1)
    areas2 = np.linalg.norm(cross, axis=1)
    if (not np.isfinite(areas2).all() or not np.isfinite(max_edge2).all()
            or np.any(min_edge2 <= MIN_EDGE**2)
            or np.any(areas2 <= RELATIVE_AREA_EPS * max_edge2)):
        fail('degenerate_triangle', 'zero, ill-conditioned, or unrepresentable triangle')
    if 'tri' in mesh and not np.array_equal(np.asarray(mesh['tri']), tri):
        fail('mesh_cache_mismatch', 'cached triangles disagree with authoritative topology')
    owners = integer_ids(owner_faces, 'owner_face_id', 1)
    if (len(owners) == 0 or np.any(owners < 0) or np.any(owners >= len(f))
            or len(set(owners.tolist())) != len(owners)):
        fail('owner_face_id', 'owners must be unique nonempty in-range face IDs')
    p = np.asarray(path, dtype=float)
    if p.ndim != 2 or p.shape[1] != 3 or len(p) < 2:
        fail('path_shape', 'path must have shape (N>=2,3)')
    if not np.isfinite(p).all():
        fail('path_nonfinite', 'nonfinite path coordinate')
    sf = integer_ids(segment_faces, 'segment_face_id', 1)
    if len(sf) != len(p)-1:
        fail('segment_count', 'one explicit face per straight segment required')
    if np.any(sf < 0) or np.any(sf >= len(f)):
        fail('segment_face_id', 'segment face index out of range')
    if not set(sf.tolist()).issubset(set(owners.tolist())):
        fail('segment_not_owned', 'segment face absent from explicit owner list')
    transitions = []
    for i in range(1, len(sf)):
        if sf[i-1] == sf[i]:
            continue
        shared = sorted(set(f[sf[i-1]].tolist()) & set(f[sf[i]].tolist()))
        if len(shared) != 2:
            fail('disconnected_transition', 'different faces must share exactly two mesh vertex IDs')
        a, b = v[shared]
        edge = b-a
        edge2 = float(edge@edge)
        t = float((p[i]-a)@edge/edge2)
        nearest = a + np.clip(t, 0., 1.) * edge
        residual = float(np.linalg.norm(p[i]-nearest))
        if residual > WORLD_EPS:
            fail('waypoint_not_on_shared_edge', 'transition waypoint outside actual finite mesh edge')
        transitions.append({'waypoint_index': i, 'edge_vertex_ids': shared,
                            'edge_parameter': t, 'edge_residual_world': residual})
    barycentrics = []
    residuals = []
    for i, fi in enumerate(sf):
        delta = p[i:i+2]-tri[fi, 0]
        normal = cross[fi]/areas2[fi]
        residual = abs(delta@normal)
        if np.max(residual) > WORLD_EPS:
            fail('off_plane', 'segment endpoint violates declared triangle plane')
        # Cross-product barycentrics avoid a nearly singular Gram subtraction.
        b1 = np.cross(delta, e1[fi])@normal/areas2[fi]
        b2 = np.cross(e0[fi], delta)@normal/areas2[fi]
        bary = np.column_stack((1-b1-b2, b1, b2))
        if (not np.isfinite(bary).all() or np.min(bary) < -BARY_EPS
                or np.max(bary) > 1+BARY_EPS):
            fail('outside_triangle', 'segment endpoint outside finite triangle')
        barycentrics.append(bary.tolist())
        residuals.extend(residual.tolist())
    return {'mesh': mesh, 'owner_faces': owner_faces, 'segment_faces': segment_faces,
            'path': path, 'diagnostics': {'segments': len(sf),
            'transitions': transitions, 'barycentrics': barycentrics,
            'plane_residual_max_world': max(residuals),
            'barycentric_min': min(np.min(b) for b in barycentrics).item()}}


def render_validated(mesh, owner_faces, segment_faces, path, renderer, *args, **kwargs):
    """Never invoke the supplied renderer if attachment validation fails."""
    validate_attachment(mesh, owner_faces, segment_faces, path)
    return renderer(mesh, owner_faces, path, *args, **kwargs)
