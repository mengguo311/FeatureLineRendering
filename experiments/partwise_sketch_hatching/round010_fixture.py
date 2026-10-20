"""Independent analytic centered support and new finite planar fixtures."""
import round010_common
import numpy as np
import core
import coverage_fixture


def analytic_support(grid, prescribed_path, width=2., eps=1e-9):
    """Distance/end-bound oracle; no candidate polygon or coverage calls."""
    p = np.asarray(prescribed_path, float)
    support = np.zeros(grid.shape[:-1], bool)
    for a, b in zip(p[:-1], p[1:]):
        d = b-a; q = grid-a; length2 = float(d@d); length = np.sqrt(length2)
        if length <= 1e-12:
            raise ValueError('oracle requires nonzero projected length')
        along = q@d
        cross = d[0]*q[..., 1]-d[1]*q[..., 0]
        support |= ((along >= -eps*length) & (along <= length2+eps*length)
                    & (cross*cross <= (width/2+eps)**2*length2))
    return support


def rectangle(grid, bounds):
    x0, y0, x1, y1 = bounds
    return ((grid[..., 0] >= x0) & (grid[..., 0] <= x1)
            & (grid[..., 1] >= y0) & (grid[..., 1] <= y1))


def fixture(protocol, spec):
    g = protocol['geometry']; cam = coverage_fixture.camera(protocol)
    vertices = list(g['vertices']); faces = list(g['faces']); parts = list(g['parts'])
    if 'extra' in spec:
        extra = spec['extra']; x0, y0, x1, y1 = extra['bounds_high_xyxy']; z = extra['z']
        # Mesh construction uses the prescribed fronto-parallel geometry.
        uv = np.array([[x0,y0], [x1,y0], [x1,y1], [x0,y1]], float)
        xy = (uv-np.array([64.,64.]))*z/64.
        start = len(vertices); vertices.extend(np.column_stack((xy, np.full(4,z))).tolist())
        faces.extend([[start,start+1,start+2], [start,start+2,start+3]])
        parts.extend([extra['part_id']]*2)
    mesh = core.finalize_mesh(vertices, faces, parts)
    yy, xx = np.mgrid[:128, :128]; grid = np.stack((xx, yy), axis=-1)
    domain = rectangle(grid, g['analytic_owner']['bounds_high_xyxy'])
    owner = np.where(domain, float(g['analytic_owner']['z']), np.inf)
    scene = owner.copy(); part = np.where(domain,1,0).astype(np.int32)
    if 'extra' in spec:
        extra = spec['extra']; take = rectangle(grid,extra['bounds_high_xyxy']) & (extra['z']<scene)
        scene[take] = extra['z']; part[take] = extra['part_id']
    visible = domain & (owner <= scene)
    truth = {'owner':owner,'scene':scene,'part':part,'visible':visible,
             'hidden':domain & ~visible,'unsupported':~domain}
    return mesh, cam, np.asarray(spec['path'],float), list(g['owners']), list(spec['segment_faces']), grid, truth
