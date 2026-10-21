"""Per-ID output probes against independent analytic-lathe depth and part maps.

Input ink must come from an isolated stroke, without contours. Analytic maps are
bilinearly sampled pixel-center references, not exact continuous probe rays.
The oracle shares the procedural asset specification, but not mesh rasterization.
Hidden-sample support is diagnostic: another segment of the same stroke can
project there. Adjacent-frame normal residuals include raster/subpixel effects;
they are not a reconstruction or universal temporal-consistency claim.
"""
import numpy as np
from scipy.ndimage import distance_transform_edt, map_coordinates


def sample_stroke(points, samples=41):
    """Fixed equal world-arclength correspondences, including both endpoints."""
    points = np.asarray(points, dtype=float)
    if points.ndim != 2 or points.shape[1] != 3 or len(points) < 1:
        raise ValueError("points must be a nonempty Nx3 path")
    arc = np.r_[0., np.cumsum(np.linalg.norm(np.diff(points, axis=0), axis=1))]
    keep = np.r_[True, np.diff(arc) > 1e-12]
    arc, points = arc[keep], points[keep]
    targets = np.linspace(0, arc[-1], samples)
    return np.column_stack([np.interp(targets, arc, points[:, j]) for j in range(3)])


def _at(array, uv, order=1, cval=0.):
    return map_coordinates(np.asarray(array, float), [uv[..., 1], uv[..., 0]],
                           order=order, mode="constant", cval=cval)


def _stats(values):
    values = np.asarray(values, float)
    values = values[np.isfinite(values)]
    return {"count": int(values.size), "mean": float(values.mean()) if values.size else None,
            "p95": float(np.percentile(values, 95)) if values.size else None,
            "max": float(values.max()) if values.size else None}


def _finite_list(values):
    return [float(x) if np.isfinite(x) else None for x in values]


def evaluate_probe(ink, points, part, camera, reference_depth, reference_parts,
                   stroke_id, frame, *, depth_tolerance=.006, samples=41,
                   band_px=2., support_threshold=.05, image_is_ink=True):
    """Return JSON-safe summary and raw sample arrays for one ID and frame.

    Classes are visible, hidden, boundary, outside, or unmeasured. 'Unmeasured'
    includes a mesh/analytic depth mismatch in front of the reference surface.
    A normal profile spans fixed +/-2 output pixels at 0.25-pixel spacing.
    Missing profiles remain missing in denominators; absent ink never scores 0.
    """
    image = np.asarray(ink)
    scale = 255. if np.issubdtype(image.dtype, np.integer) or image.max() > 1. else 1.
    image = image.astype(float) / scale
    if image.ndim == 3:
        image = image[..., :3].mean(axis=2)
    image = np.clip(image if image_is_ink else 1. - image, 0., 1.)
    depth, labels = np.asarray(reference_depth), np.asarray(reference_parts)
    if image.shape != depth.shape or image.shape != labels.shape:
        raise ValueError("ink and reference maps must have matching output resolution")
    xyz = sample_stroke(points, samples)
    camxyz = xyz @ np.asarray(camera["R"]).T + camera["t"]
    uv = camxyz[:, :2] / camxyz[:, 2, None] * camera["focal"] + camera["center"]
    z = camxyz[:, 2]
    h, w = image.shape
    inside = (z > 0) & (uv[:, 0] >= 0) & (uv[:, 0] <= w-1) & (uv[:, 1] >= 0) & (uv[:, 1] <= h-1)
    nearest_part = _at(labels, uv, order=0).astype(int)
    margin_map = np.zeros(labels.shape, float)
    for label in np.unique(labels):
        if label:
            region = labels == label
            margin_map[region] = distance_transform_edt(region)[region]
    margin = _at(margin_map, uv)
    finite = np.isfinite(depth)
    depth_mass = _at(np.where(finite, depth, 0.), uv)
    depth_weight = _at(finite, uv)
    refz = np.divide(depth_mass, depth_weight, out=np.full(samples, np.nan), where=depth_weight > .999)
    gap = z - refz
    interior = inside & (nearest_part > 0) & (margin > band_px) & np.isfinite(refz)
    classes = np.full(samples, "unmeasured", dtype="U12")
    classes[~inside] = "outside"
    classes[inside & ~interior] = "boundary"
    classes[interior & (gap > depth_tolerance)] = "hidden"
    classes[interior & (nearest_part == part) & (np.abs(gap) <= depth_tolerance)] = "visible"
    tangent = np.gradient(uv, axis=0)
    length = np.linalg.norm(tangent, axis=1)
    normal = np.column_stack((-tangent[:, 1], tangent[:, 0])) / np.maximum(length[:, None], 1e-12)
    classes[(classes == "visible") & (length < 1e-9)] = "unmeasured"
    offsets = np.linspace(-2., 2., 17)
    profile = _at(image, uv[:, None, :] + offsets[None, :, None] * normal[:, None, :])
    mass, peak = profile.sum(axis=1), profile.max(axis=1)
    present = peak >= support_threshold
    centroid = np.divide(profile @ offsets, mass, out=np.full(samples, np.nan), where=present & (mass > 0))
    support = image >= support_threshold
    distance = _at(distance_transform_edt(~support), uv, cval=np.nan) if support.any() else np.full(samples, np.nan)
    visible, hidden = classes == "visible", classes == "hidden"
    counts = {name: int((classes == name).sum()) for name in ("visible", "hidden", "boundary", "outside", "unmeasured")}
    summary = {"samples": int(samples), "class_counts": counts,
               "eligible_fraction": float(visible.mean()), "missing_visible": int((visible & ~present).sum()),
               "missing_fraction": float((visible & ~present).sum()/visible.sum()) if visible.any() else None,
               "centroid_abs_px": _stats(np.abs(centroid[visible & present])),
               "support_distance_px": _stats(distance[visible]),
               "hidden_profile_present": int((hidden & present).sum()),
               "image_ink_mass": float(image.sum()), "image_support_pixels": int(support.sum())}
    return {"stroke_id": str(stroke_id), "part": int(part), "frame": int(frame), "summary": summary,
            "samples": {"world": xyz.tolist(), "uv": uv.tolist(), "class": classes.tolist(),
                        "analytic_depth_gap": _finite_list(gap), "part_boundary_distance_px": margin.tolist(),
                        "profile_peak": peak.tolist(), "profile_present": present.tolist(),
                        "normal_centroid_px": _finite_list(centroid), "support_distance_px": _finite_list(distance)}}


def summarize_probes(rows, *, required_per_part=32, centroid_p95_limit=1.5, missing_limit=.02):
    """Aggregate coverage per part and per ID, then same-ID temporal probes.

    Eligible counts pool frame/sample observations. Unique visible-ever sample
    counts are also given, to expose repeated frames or short/occluded paths.
    """
    def aggregate(group):
        counts = {name: 0 for name in ("visible", "hidden", "boundary", "outside", "unmeasured")}
        centroids, distances, seen, missing = [], [], set(), 0
        for row in group:
            for name, count in row["summary"]["class_counts"].items():
                counts[name] += count
            raw = row["samples"]
            for i, cls in enumerate(raw["class"]):
                if cls != "visible":
                    continue
                seen.add((row["stroke_id"], i))
                missing += not raw["profile_present"][i]
                if raw["normal_centroid_px"][i] is not None:
                    centroids.append(abs(raw["normal_centroid_px"][i]))
                if raw["support_distance_px"][i] is not None:
                    distances.append(raw["support_distance_px"][i])
        eligible = counts["visible"]
        ratio = missing/eligible if eligible else None
        stats = _stats(centroids)
        status = "UNMEASURED" if eligible < required_per_part else (
            "GO" if ratio <= missing_limit and stats["p95"] is not None and stats["p95"] <= centroid_p95_limit else "NO_GO")
        return {"status": status, "records": len(group), "class_counts": counts,
                "unique_visible_samples": len(seen), "missing_visible": int(missing), "missing_fraction": ratio,
                "centroid_abs_px": stats, "support_distance_px": _stats(distances)}
    per_part = {str(part): aggregate([r for r in rows if r["part"] == part]) for part in (1, 2, 3)}
    per_stroke, pairs = {}, []
    for sid in sorted({r["stroke_id"] for r in rows}):
        group = sorted([r for r in rows if r["stroke_id"] == sid], key=lambda r: r["frame"])
        per_stroke[sid] = aggregate(group)
        for before, after in zip(group[:-1], group[1:]):
            a, b = before["samples"], after["samples"]
            common = [i for i, (x, y) in enumerate(zip(a["class"], b["class"])) if x == y == "visible"]
            valid = [i for i in common if a["profile_present"][i] and b["profile_present"][i]]
            delta = [abs(b["normal_centroid_px"][i]-a["normal_centroid_px"][i]) for i in valid]
            pairs.append({"stroke_id": sid, "part": before["part"], "frames": [before["frame"], after["frame"]],
                          "common_visible_samples": len(common), "both_present_samples": len(valid),
                          "normal_residual_change_abs_px": _stats(delta)})
    status = "GO" if all(p["status"] == "GO" for p in per_part.values()) else (
        "NO_GO" if any(p["status"] == "NO_GO" for p in per_part.values()) else "UNMEASURED")
    return {"status": status, "all": aggregate(rows), "per_part": per_part, "per_stroke": per_stroke,
            "adjacent_frame_pairs": pairs,
            "limits": {"eligible_observations_per_part": required_per_part,
                       "normal_centroid_abs_p95_px": centroid_p95_limit, "missing_fraction": missing_limit},
            "limitations": ["Analytic pixel-depth interpolation; common asset specification with independent geometry implementation.",
                            "No photometric independent reference; normal-profile residual includes raster/subpixel bias.",
                            "Hidden profile support can come from another segment of this same stroke."]}
