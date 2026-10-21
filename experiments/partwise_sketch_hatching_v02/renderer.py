"""Bounded CPU renderer for persistent whole-lamp surface curves.

Each projected line segment contributes a round-ended capsule of the requested
screen diameter.  Visibility is tested at *each supersample*, against the mesh
depth at that same ray, using the segment's owning face plane and semantic part.
Coverage is a box average of binary supersamples, never post-raster dilation.

This is a finite-sample engineering backend, not an exact area integrator.  The
face plane is extended across the capsule width; at curved facet joins the
fixed depth tolerance bounds the accepted extension.  Different segments join
by a maximum-ink union, including their round caps.  Near-plane clipping is not
implemented: segments with an endpoint behind the camera are skipped.  The
frozen lamp views stay entirely in front of the camera.

Imports execute no experiments and write no output artifacts.  The inherited
core supplies only camera/mesh primitives; no historical source is modified.
"""

from pathlib import Path
import sys

import numpy as np

_REPOSITORY = Path(__file__).resolve().parents[2]
if str(_REPOSITORY) not in sys.path:
    sys.path.insert(0, str(_REPOSITORY))
from experiments.partwise_sketch_hatching import core


BACKEND = "cpu_supersampled_surface_capsules_v1"


def projected_depth_query(mesh, camera):
    """Nearest triangle depth at arbitrary screen rays, without pixel rounding.

    This query is used only for contour centerlines. It is independent of the
    integer sample surface buffer, but not an independent geometry reference.
    Near-plane crossing triangles are excluded as in the bounded base backend.
    """
    uv, z = core.project(mesh["vertices"], camera)
    p, zz = uv[mesh["faces"]], z[mesh["faces"]]
    a, b, d = p[:, 0], p[:, 1], p[:, 2]
    den = (b[:, 1]-d[:, 1])*(a[:, 0]-d[:, 0]) + (d[:, 0]-b[:, 0])*(a[:, 1]-d[:, 1])
    valid = (np.abs(den) > 1e-12) & (zz.min(axis=1) > 0)
    a, b, d, zz, den = a[valid], b[valid], d[valid], zz[valid], den[valid]
    def query(points):
        answer = np.full(len(points), np.inf)
        for start in range(0, len(points), 256):
            q = points[start:start+256]
            x, y = q[:, 0, None], q[:, 1, None]
            w0 = ((b[:, 1]-d[:, 1])*(x-d[:, 0]) + (d[:, 0]-b[:, 0])*(y-d[:, 1]))/den
            w1 = ((d[:, 1]-a[:, 1])*(x-d[:, 0]) + (a[:, 0]-d[:, 0])*(y-d[:, 1]))/den
            w2 = 1-w0-w1
            inside = (w0 >= -1e-9) & (w1 >= -1e-9) & (w2 >= -1e-9)
            inv = w0/zz[:, 0] + w1/zz[:, 1] + w2/zz[:, 2]
            depths = np.divide(1., inv, out=np.full_like(inv, np.inf), where=inside & (inv > 0))
            answer[start:start+len(q)] = depths.min(axis=1)
        return answer
    return query


def _edge_owners(mesh):
    """Unique physical mesh edges and their incident faces."""
    edges = {}
    for fi, face in enumerate(mesh["faces"]):
        for j in range(3):
            key = tuple(sorted((int(face[j]), int(face[(j + 1) % 3]))))
            edges.setdefault(key, []).append(fi)
    return edges


def _structure_edges(mesh, cfg, camera):
    """Silhouettes/part boundaries and actual profile rings, never all edges."""
    owners = _edge_owners(mesh)
    vertices = mesh["vertices"]
    centers = mesh["tri"].mean(axis=1)
    facing = np.einsum("ij,ij->i", mesh["normals"], camera["eye"] - centers)
    profiles = {
        (round(float(r), 10), round(float(y), 10))
        for profile in cfg["asset"]["profiles_ry"].values()
        for r, y in profile
        if r > 1e-10
    }
    ring_keys = [
        (round(float(np.hypot(v[0], v[2])), 10), round(float(v[1]), 10))
        for v in vertices
    ]
    contours, rings = [], []
    for edge, faces in sorted(owners.items()):
        ff = np.asarray(faces, dtype=np.int32)
        is_contour = (
            len(faces) == 1
            or len(set(map(int, mesh["parts"][ff]))) > 1
            or (np.min(facing[ff]) <= 0 < np.max(facing[ff]))
        )
        if is_contour:
            contours.append((edge, ff))
        # Equal radius/height edges are the polygonal lathe rings.  Diagonals
        # and meridians differ in radius or height, so cannot enter this set.
        if ring_keys[edge[0]] == ring_keys[edge[1]] and ring_keys[edge[0]] in profiles:
            rings.append((edge, ff))
    return contours, rings


def render(mesh, strokes, cfg, azimuth=30, elevation=20, distance=4.5,
           structure=True, selected_ids=None):
    """Render persistent barycentric strokes without changing their geometry.

    ``cfg['widths_by_part']`` supplies absolute pixel diameters (string or int
    part keys), defaulting to 1.0 for each part.  ``selected_ids`` optionally
    selects an ID set before rasterization.  ``structure=False`` suppresses
    profile rings but retains contours, matching the inherited API.  ``hatch``
    always excludes all structural strokes.  Images are float64 in [0, 1].

    ``parts`` and ``depth`` come from an independent output-resolution surface
    raster, so their camera convention is identical to ``camera``.  Diagnostic
    fragment counts include overlap between segments and are not pixel counts.
    """
    renderer = cfg["renderer"]
    resolution = renderer["resolution"]
    if len(resolution) != 2 or resolution[0] != resolution[1]:
        raise ValueError("the inherited camera supports square output only")
    size = int(resolution[0])
    scale = int(renderer.get("supersample", 3))
    if size <= 0 or scale < 1 or scale > 4 or scale != renderer.get("supersample", 3):
        raise ValueError("positive resolution and integer supersample in [1, 4] required")
    tolerance = float(renderer.get("visibility_tolerance_world", 0.006))
    if tolerance != 0.006:
        raise ValueError("this backend freezes visibility tolerance at 0.006 world units")
    widths = cfg.get("widths_by_part", {})
    contour_mode = renderer.get("contour_visibility", "surface_fragments")
    if contour_mode not in ("surface_fragments", "visible_centerline"):
        raise ValueError("unknown contour_visibility mode")
    part_widths = {p: float(widths.get(str(p), widths.get(p, 1.0))) for p in (1, 2, 3)}
    for width in part_widths.values():
        if not np.isfinite(width) or not 0 < width <= 64:
            raise ValueError("part widths must be finite pixel diameters in (0, 64]")

    low_camera = core.camera(azimuth, elevation, distance, size, renderer["focal_px"])
    c = core.camera(azimuth, elevation, distance, size * scale,
                    renderer["focal_px"] * scale)
    # Pixel i averages subpixel samples centered symmetrically about i.  The
    # inherited raster samples integer coordinates, hence this center shift.
    c["center"] = c["center"] + (scale - 1) / 2.0
    depth, parts = core.raster_surface(mesh, c)
    low_depth, low_parts = core.raster_surface(mesh, low_camera)
    hatch = np.zeros(depth.shape, dtype=float)
    normals_camera = mesh["normals"] @ c["R"].T
    origins_camera = mesh["tri"][:, 0] @ c["R"].T + c["t"]
    plane_constant = np.einsum("ij,ij->i", normals_camera, origins_camera)
    selected = None if selected_ids is None else set(selected_ids)
    contour_depth = projected_depth_query(mesh, c) if contour_mode == "visible_centerline" else None
    diagnostics = {
        "backend": BACKEND,
        "supersample": scale,
        "visibility_tolerance_world": tolerance,
        "coverage_method": "binary centered subpixel samples, box average",
        "visibility_method": "same-ray owner-plane depth and same semantic part",
        "hatch_segments": 0,
        "skipped_zero_segments": 0,
        "skipped_behind_camera_segments": 0,
        "candidate_fragments": 0,
        "accepted_fragments": 0,
        "rejected_part_fragments": 0,
        "rejected_depth_fragments": 0,
        "selected_strokes": 0,
        "contour_visibility": contour_mode,
        "contour_covered_fragments": 0,
        "contour_visible_fragments": 0,
        "contour_hidden_fragments": 0,
    }

    def draw_segment(target, a, b, owners, width, ink, count=False, centerline=False):
        if np.linalg.norm(b - a) < 1e-8:
            if count:
                diagnostics["skipped_zero_segments"] += 1
            return
        uv, zz = core.project(np.stack((a, b)), c)
        if np.any(zz <= 0):
            if count:
                diagnostics["skipped_behind_camera_segments"] += 1
            return
        direction = uv[1] - uv[0]
        length2 = float(direction @ direction)
        if length2 < 1e-16:
            if count:
                diagnostics["skipped_zero_segments"] += 1
            return
        radius = width * scale / 2.0
        lo = np.maximum(np.ceil(np.minimum(uv[0], uv[1]) - radius).astype(int), 0)
        hi = np.minimum(np.floor(np.maximum(uv[0], uv[1]) + radius).astype(int), c["size"] - 1)
        if np.any(hi < lo):
            return
        yy, xx = np.mgrid[lo[1]:hi[1] + 1, lo[0]:hi[0] + 1]
        u = np.clip(((xx - uv[0, 0]) * direction[0] +
                     (yy - uv[0, 1]) * direction[1]) / length2, 0.0, 1.0)
        distance2 = ((xx - uv[0, 0] - u * direction[0]) ** 2 +
                     (yy - uv[0, 1] - u * direction[1]) ** 2)
        covered = distance2 <= radius * radius + 1e-12
        if not covered.any():
            return
        if centerline:
            # The nearest projected centerline point has reciprocal-linear
            # optical depth. Query exactly that ray, including background-side
            # capsule samples. A visible centerline emits a symmetric stroke.
            # This is screen-space contour ink, not surface hatch coverage;
            # at occlusion endpoints its round cap can extend <=width/2 px.
            uu = u[covered]
            q = uv[0] + uu[:, None]*direction
            scene_z = contour_depth(q)
            line_z = 1. / ((1.-uu)/zz[0] + uu/zz[1])
            visible = np.isfinite(scene_z) & (np.abs(line_z-scene_z) <= tolerance)
            take = np.zeros_like(covered)
            take[covered] = visible
            region = target[lo[1]:hi[1]+1, lo[0]:hi[0]+1]
            region[take] = np.maximum(region[take], ink)
            diagnostics["contour_covered_fragments"] += int(covered.sum())
            diagnostics["contour_visible_fragments"] += int(visible.sum())
            diagnostics["contour_hidden_fragments"] += int((~visible).sum())
            return
        surface_depth = depth[lo[1]:hi[1] + 1, lo[0]:hi[0] + 1]
        surface_part = parts[lo[1]:hi[1] + 1, lo[0]:hi[0] + 1]
        ray_x = (xx - c["center"][0]) / c["focal"]
        ray_y = (yy - c["center"][1]) / c["focal"]
        accepted = np.zeros(covered.shape, dtype=bool)
        same_part = np.zeros(covered.shape, dtype=bool)
        for fi in owners:
            fi = int(fi)
            part_ok = surface_part == mesh["parts"][fi]
            same_part |= part_ok
            normal = normals_camera[fi]
            denominator = normal[0] * ray_x + normal[1] * ray_y + normal[2]
            owner_depth = np.divide(plane_constant[fi], denominator,
                                    out=np.full_like(denominator, np.inf),
                                    where=np.abs(denominator) > 1e-12)
            finite = np.isfinite(surface_depth) & np.isfinite(owner_depth) & (owner_depth > 0)
            residual = np.full_like(owner_depth, np.inf)
            np.subtract(owner_depth, surface_depth, out=residual, where=finite)
            accepted |= part_ok & finite & (np.abs(residual) <= tolerance)
        take = covered & accepted
        region = target[lo[1]:hi[1] + 1, lo[0]:hi[0] + 1]
        region[take] = np.maximum(region[take], ink)
        if count:
            diagnostics["hatch_segments"] += 1
            diagnostics["candidate_fragments"] += int(covered.sum())
            diagnostics["accepted_fragments"] += int(take.sum())
            diagnostics["rejected_part_fragments"] += int((covered & ~same_part).sum())
            diagnostics["rejected_depth_fragments"] += int((covered & same_part & ~accepted).sum())

    for stroke in strokes:
        if selected is not None and stroke["id"] not in selected:
            continue
        diagnostics["selected_strokes"] += 1
        points = core.anchor_points(mesh, stroke)
        width = part_widths[int(stroke["part"])]
        ink = float(np.clip(stroke["ink"], 0.0, 1.0))
        for i in range(len(points) - 1):
            # The walker inserts an almost-zero edge transition before
            # continuing within the new face.  Never create a connector cap
            # from that numerical transition.
            if stroke["faces"][i] != stroke["faces"][i + 1] and np.linalg.norm(points[i + 1] - points[i]) < 1e-6:
                diagnostics["skipped_zero_segments"] += 1
                continue
            draw_segment(hatch, points[i], points[i + 1], [stroke["faces"][i]], width, ink, count=True)

    contour_ink = np.zeros_like(hatch)
    ring_ink = np.zeros_like(hatch)
    contours, rings = _structure_edges(mesh, cfg, c)
    contour_width = float(renderer.get("contour_width_px", 0.8))
    ring_width = float(renderer.get("structure_width_px", 0.65))
    for edge, owners in contours:
        a, b = mesh["vertices"][list(edge)]
        draw_segment(contour_ink, a, b, owners, contour_width, 0.92,
                     centerline=contour_mode == "visible_centerline")
    contour_keys = {edge for edge, _ in contours}
    if structure:
        for edge, owners in rings:
            if edge in contour_keys:
                continue
            a, b = mesh["vertices"][list(edge)]
            draw_segment(ring_ink, a, b, owners, ring_width, 0.85)
    diagnostics["contour_edges"] = len(contours)
    diagnostics["profile_ring_edges"] = len(rings)
    diagnostics["drawn_profile_ring_edges"] = sum(edge not in contour_keys for edge, _ in rings) if structure else 0

    def down(array):
        return array.reshape(size, scale, size, scale).mean(axis=(1, 3))

    allink = np.maximum(np.maximum(hatch, contour_ink), ring_ink)
    return {
        "image": np.clip(1.0 - down(allink), 0.0, 1.0),
        "hatch": np.clip(down(hatch), 0.0, 1.0),
        "contours": down(contour_ink),
        "rings": down(ring_ink),
        "parts": low_parts,
        "depth": low_depth,
        "camera": low_camera,
        "visible_samples": diagnostics["accepted_fragments"],
        "total_samples": diagnostics["candidate_fragments"],
        "diagnostics": diagnostics,
    }
