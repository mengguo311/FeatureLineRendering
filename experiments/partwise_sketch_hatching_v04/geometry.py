import runtime
import numpy as np
from scipy import ndimage

def normalize(x):
    return x / np.maximum(np.linalg.norm(x, axis=-1, keepdims=True), 1e-30)

def project(x, c):
    E = np.asarray(c['extrinsic'])
    p = np.asarray(x) @ E[:3, :3].T + E[:3, 3]
    return np.column_stack((p[:, 0] / p[:, 2] * c['fx'] + c['cx'],
                            p[:, 1] / p[:, 2] * c['fy'] + c['cy'])), p[:, 2]

def backproject(uv, z, c):
    E = np.asarray(c['extrinsic'])
    p = np.column_stack(((uv[:, 0]-c['cx'])*z/c['fx'],
                         (uv[:, 1]-c['cy'])*z/c['fy'], z))
    return (p - E[:3, 3]) @ np.linalg.inv(E[:3, :3]).T

def orbit_camera(azimuth=47., elevation=25., distance=4.6, size=512, target=(0, 0, 0)):
    a, e = np.deg2rad([azimuth, elevation])
    target = np.asarray(target, float)
    eye = target + distance * np.array([np.sin(a)*np.cos(e), -np.cos(a)*np.cos(e), np.sin(e)])
    forward = normalize(target-eye)
    right = normalize(np.cross(forward, [0., 0., 1.]))
    down = np.cross(forward, right)
    E = np.eye(4)
    E[:3, :3] = np.stack([right, down, forward])
    E[:3, 3] = -E[:3, :3] @ eye
    return dict(extrinsic=E.tolist(), width=size, height=size, fx=size/2/np.tan(.6911112070083618/2),
                fy=size/2/np.tan(.6911112070083618/2), cx=(size-1)/2, cy=(size-1)/2,
                view=f'orbit_{azimuth:g}_{elevation:g}_{distance:g}')

def resize_camera(c, size):
    c = dict(c)
    scale = size / c['width']
    for name in ('fx', 'fy'):
        c[name] *= scale
    for name in ('cx', 'cy'):
        c[name] = (c[name]+.5)*scale-.5
    c['width'] = c['height'] = size
    return c

def depth_valid(depth, alpha, center):
    valid = np.isfinite(depth) & (depth > .2) & (depth < 6.) & (alpha >= .95)
    valid &= np.isfinite(center) & (np.abs(depth-center) <= .06)
    z = np.where(valid, depth, 0.)
    jump = ndimage.maximum_filter(z, size=3) - ndimage.minimum_filter(z, size=3)
    return valid & (jump <= .08)

def region_ids(points, cuts=(-.35,.20)):
    """Authored height style regions, NOT learned semantic parts."""
    cuts=np.asarray(cuts,float)
    if cuts.shape!=(2,) or not np.isfinite(cuts).all() or cuts[0]>=cuts[1]:
        raise ValueError('two finite increasing world-height cuts are required')
    return np.where(points[:, 2] < cuts[0], 1, np.where(points[:, 2] < cuts[1], 2, 3)).astype(np.int32)

def mesh_data(vertices, faces, face_regions=None):
    tri = vertices[faces]
    cross = np.cross(tri[:, 1]-tri[:, 0], tri[:, 2]-tri[:, 0])
    regions = region_ids(tri.mean(axis=1)) if face_regions is None else np.asarray(face_regions)
    if regions.shape != (len(faces),) or not np.isin(regions, [1, 2, 3]).all():
        raise ValueError('one valid saved region ID per face is required')
    return dict(vertices=vertices, faces=faces, tri=tri, normals=normalize(cross),
                regions=regions.astype(np.int32))

def ray_surface(mesh, c, supersample=2):
    import open3d as o3d
    size = c['width'] * supersample
    cc = resize_camera(c, size)
    E = np.asarray(cc['extrinsic'])
    y, x = np.mgrid[:size, :size]
    local = np.stack([(x-cc['cx'])/cc['fx'], (y-cc['cy'])/cc['fy'], np.ones_like(x)], -1)
    invR = np.linalg.inv(E[:3, :3])
    directions = local @ invR.T
    origin = -invR @ E[:3, 3]
    rays = np.concatenate([np.broadcast_to(origin, directions.shape), directions], -1).astype(np.float32)
    scene = o3d.t.geometry.RaycastingScene(nthreads=1)
    scene.add_triangles(o3d.core.Tensor(mesh['vertices'].astype(np.float32)),
                        o3d.core.Tensor(mesh['faces'].astype(np.uint32)))
    result = scene.cast_rays(o3d.core.Tensor(rays), nthreads=1)
    depth = result['t_hit'].numpy()
    ids = result['primitive_ids'].numpy().astype(np.int64)
    hit = np.isfinite(depth)
    ids[~hit] = -1
    regions = np.zeros_like(ids, dtype=np.int32)
    regions[hit] = mesh['regions'][ids[hit]]
    return depth, ids, regions, cc
