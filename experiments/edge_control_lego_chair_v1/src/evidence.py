"""Target-only label-free RGB evidence and conservative normal-profile metrics.

The input is the actual display-encoded training PNG RGB composited with the
declared renderer background, and its original anti-aliased alpha coverage.
RGB internal edges are support evidence, never physical-contact/part labels.
All masks, normals, profile locations, and ROIs are frozen from this input.
Only profile measurement converts display sRGB to linear RGB. Training losses
remain in their declared native display-PNG encoding.
"""

from collections import Counter, defaultdict

import numpy as np
from scipy import ndimage as ndi


SCALES = (0.8, 1.6, 3.2)
MAX_PROFILES = 96
PROFILE_RADIUS = 12.0
PROFILE_SAMPLES = 97
LINEAR_CONTRAST_MIN = 0.02


def srgb_to_linear(values):
    """IEC sRGB decoding, also preserving finite out-of-range render values."""
    values = np.asarray(values, dtype=np.float64)
    result = values / 12.92
    high = values > 0.04045
    result[high] = ((values[high] + 0.055) / 1.055) ** 2.4
    return result


def _input(rgb, alpha=None):
    rgb = np.asarray(rgb)
    if rgb.ndim != 3 or rgb.shape[2] != 3 or min(rgb.shape[:2]) < 8:
        raise ValueError("RGB must have shape H,W,3 with H,W >= 8")
    if not np.isfinite(rgb).all():
        raise ValueError("RGB must be finite")
    if alpha is None:
        return rgb.astype(np.float64, copy=False)
    alpha = np.asarray(alpha)
    if alpha.shape != rgb.shape[:2] or not np.isfinite(alpha).all():
        raise ValueError("AA alpha must be a finite H,W array")
    if rgb.min() < -1e-6 or rgb.max() > 1 + 1e-6:
        raise ValueError("reference PNG RGB must be in [0,1]")
    if alpha.min() < -1e-6 or alpha.max() > 1 + 1e-6:
        raise ValueError("reference AA alpha must be in [0,1]")
    return rgb.astype(np.float64, copy=False), alpha.astype(np.float64, copy=False)


def _tensor_normals(rgb, sigma):
    """Principal normal of a smoothed multichannel RGB structure tensor."""
    channels = rgb[..., None] if rgb.ndim == 2 else rgb
    gx = ndi.gaussian_filter(channels, (sigma, sigma, 0), order=(0, 1, 0), mode="reflect")
    gy = ndi.gaussian_filter(channels, (sigma, sigma, 0), order=(1, 0, 0), mode="reflect")
    jxx = ndi.gaussian_filter(np.sum(gx * gx, axis=2), 0.8, mode="reflect")
    jxy = ndi.gaussian_filter(np.sum(gx * gy, axis=2), 0.8, mode="reflect")
    jyy = ndi.gaussian_filter(np.sum(gy * gy, axis=2), 0.8, mode="reflect")
    discriminant = np.sqrt(np.maximum((jxx - jyy) ** 2 + 4 * jxy**2, 0))
    largest = 0.5 * (jxx + jyy + discriminant)
    smallest = 0.5 * (jxx + jyy - discriminant)
    angle = 0.5 * np.arctan2(2 * jxy, jxx - jyy)
    nx, ny = np.cos(angle), np.sin(angle)
    coherence = (largest - smallest) / np.maximum(largest + smallest, 1e-12)
    return np.sqrt(np.maximum(largest, 0)), nx, ny, coherence


def _nms(strength, nx, ny):
    yy, xx = np.indices(strength.shape, dtype=np.float64)
    left = ndi.map_coordinates(strength, [yy - ny, xx - nx], order=1, mode="constant", cval=0)
    right = ndi.map_coordinates(strength, [yy + ny, xx + nx], order=1, mode="constant", cval=0)
    return (strength >= left) & (strength >= right)


def _band_and_balance(ridge, allowed, strength, sigma):
    """All retained target segments contribute; each has equal evidence mass.

    Nearest-ridge assignment partitions overlapping band pixels deterministically.
    This is a fixed target statistic; it never truncates Gaussian alpha*T terms.
    """
    labels, count = ndi.label(ridge, np.ones((3, 3), dtype=np.uint8))
    if not count:
        z = np.zeros(ridge.shape, np.float32)
        return z, z.copy(), [], labels
    sizes = np.bincount(labels.ravel())
    retain = sizes >= 3
    retain[0] = False
    ridge = retain[labels]
    labels, count = ndi.label(ridge, np.ones((3, 3), dtype=np.uint8))
    if not count:
        z = np.zeros(ridge.shape, np.float32)
        return z, z.copy(), [], labels
    distance, indices = ndi.distance_transform_edt(~ridge, return_indices=True)
    nearest = labels[indices[0], indices[1]]
    band = np.exp(-0.5 * (distance / 2.5)**2) * (distance <= 6) * allowed
    mass = np.bincount(nearest.ravel(), weights=band.ravel(), minlength=count + 1)
    active = mass > 0
    active[0] = False
    denominator = np.maximum(mass[nearest], 1e-20)
    balanced = band / denominator / max(1, int(active.sum()))
    segments = []
    for label_id, sl in enumerate(ndi.find_objects(labels), 1):
        if sl is None or not active[label_id]:
            continue
        region = labels[sl] == label_id
        segments.append({"scale": float(sigma), "label": int(label_id),
                         "bbox": [sl[1].start, sl[0].start, sl[1].stop, sl[0].stop],
                         "ridge_pixels": int(region.sum()), "band_mass": float(mass[label_id]),
                         "edge_strength_sum": float(strength[sl][region].sum())})
    return band.astype(np.float32), balanced.astype(np.float32), segments, labels


def _sample_profile(linear_rgb, config):
    center = np.asarray(config["center"], dtype=np.float64)
    normal = np.asarray(config["normal"], dtype=np.float64)
    if center.shape != (2,) or normal.shape != (2,) or not np.isfinite(center).all() or not np.isfinite(normal).all():
        return None, None, "invalid_configuration"
    norm = np.linalg.norm(normal)
    if norm < 1e-8:
        return None, None, "invalid_normal"
    normal /= norm
    tangent = np.array([-normal[1], normal[0]])
    radius = float(config.get("radius", PROFILE_RADIUS))
    samples = int(config.get("samples", PROFILE_SAMPLES))
    if not 2 <= radius <= 64 or samples < 17 or samples > 513:
        return None, None, "invalid_configuration"
    offsets = np.linspace(-radius, radius, samples)
    points = center[None, None, :] + offsets[:, None, None] * normal + np.array([-1.0, 0.0, 1.0])[None, :, None] * tangent
    h, w = linear_rgb.shape[:2]
    if np.any(points[..., 0] < 0) or np.any(points[..., 0] > w - 1) or np.any(points[..., 1] < 0) or np.any(points[..., 1] > h - 1):
        return None, None, "image_border"
    sampled = np.stack([ndi.map_coordinates(linear_rgb[..., c], [points[..., 1], points[..., 0]],
                                            order=1, mode="nearest").mean(axis=1) for c in range(3)], axis=1)
    return offsets, sampled, None


def _crossing(offsets, projected, threshold):
    # Small accepted numerical/bilinear reversals are not mistaken for new edges.
    monotone = np.maximum.accumulate(projected)
    crossed = np.flatnonzero(monotone >= threshold)
    if not len(crossed) or crossed[0] == 0:
        return None
    j = int(crossed[0])
    delta = monotone[j] - monotone[j - 1]
    if delta <= 1e-12:
        return None
    return float(offsets[j - 1] + (offsets[j] - offsets[j - 1]) * (threshold - monotone[j - 1]) / delta)


def _profile_metrics_linear(linear, profiles):
    results = []
    for index, config in enumerate(profiles):
        record = {"id": config.get("id", str(index)), "kind": config.get("kind", "unknown"),
                  "valid": False, "width": None, "contrast": None,
                  "reason": None, "encoding": "display_sRGB_to_linear_RGB"}
        offsets, sampled, reason = _sample_profile(linear, config)
        if reason:
            record["reason"] = reason
            results.append(record)
            continue
        tail = np.abs(offsets) >= 0.8 * max(abs(offsets[0]), abs(offsets[-1]))
        lo = sampled[tail & (offsets < 0)].mean(axis=0)
        hi = sampled[tail & (offsets > 0)].mean(axis=0)
        delta = hi - lo
        contrast = float(np.linalg.norm(delta) / np.sqrt(3))
        record["contrast"] = contrast
        if contrast < LINEAR_CONTRAST_MIN:
            record["reason"] = "low_contrast"
            results.append(record)
            continue
        projected = (sampled - lo) @ delta / np.dot(delta, delta)
        perpendicular = sampled - (lo + projected[:, None] * delta)
        offaxis = float(np.quantile(np.linalg.norm(perpendicular, axis=1), 0.95) / np.linalg.norm(delta))
        reverse = float(np.maximum(-np.diff(projected), 0).sum())
        record["reverse_variation"] = reverse
        record["off_axis_fraction"] = offaxis
        if offaxis > 0.18:
            record["reason"] = "off_axis_color_texture"
        elif reverse > 0.12 or projected.min() < -0.12 or projected.max() > 1.12:
            record["reason"] = "nonmonotonic_texture"
        elif float(np.std(projected[tail & (offsets < 0)])) > 0.035 or float(np.std(projected[tail & (offsets > 0)])) > 0.035:
            record["reason"] = "unbounded_plateaus"
        else:
            derivative = ndi.gaussian_filter1d(np.diff(projected), 1.0)
            active = derivative > max(0.01, float(derivative.max()) * 0.22)
            # Ignore tiny isolated derivative spikes but reject separated edges.
            components, n = ndi.label(active)
            transitions = sum(np.count_nonzero(components == j) >= 3 for j in range(1, n + 1))
            if transitions > 1:
                record["reason"] = "multiple_transitions"
            else:
                x10 = _crossing(offsets, projected, 0.1)
                x50 = _crossing(offsets, projected, 0.5)
                x90 = _crossing(offsets, projected, 0.9)
                if x10 is None or x90 is None or x50 is None or x90 <= x10:
                    record["reason"] = "missing_crossings"
                elif max(abs(x10), abs(x90)) > 0.8 * max(abs(offsets[0]), abs(offsets[-1])):
                    record["reason"] = "transition_near_profile_end"
                else:
                    record.update(valid=True, width=float(x90 - x10), reason=None,
                                  x10=x10, x50=x50, x90=x90)
        results.append(record)
    return results


def profile_metrics(rgb, profiles):
    """Measure fixed boundary-normal RGB profiles, returning JSON-safe records.

    Width is the linear-RGB projected 10--90 transition in native image pixels.
    No width is assigned to weak, textured, nonmonotonic, unbounded, or border
    profiles. Pair comparisons must use common valid profile IDs and report
    validity/rejection rates. This function does not move target profile centers.
    """
    return _profile_metrics_linear(srgb_to_linear(_input(rgb)), profiles)


def _candidate_order(candidates):
    """Deterministic strongest-first round-robin across target edge segments."""
    by_segment = defaultdict(list)
    for candidate in candidates:
        by_segment[(candidate["kind"], candidate["segment"])].append(candidate)
    for values in by_segment.values():
        values.sort(key=lambda p: (-p["edge_strength"], p["center"][1], p["center"][0]))
    keys = sorted(by_segment, key=lambda k: (-by_segment[k][0]["edge_strength"], k))
    ordered = []
    for depth in range(max((len(v) for v in by_segment.values()), default=0)):
        active = False
        for key in keys:
            if depth < len(by_segment[key]):
                ordered.append(by_segment[key][depth])
                active = True
        if not active:
            break
    return ordered


def build_evidence(rgb, alpha):
    """Extract fixed multi-scale internal evidence and a separate AA outline.

    balanced_maps is a list of three H,W float32 maps; each nonempty map sums
    to one and allocates equal total mass to every connected target edge
    segment at that scale. Average the nonempty maps for a scale-balanced
    exact alpha*T responsibility statistic. Empty maps remain identically zero.
    Segments and profile IDs are target evidence IDs only, never Gaussian or
    physical instance IDs. foreground preserves original AA alpha values.
    """
    rgb, alpha = _input(rgb, alpha)
    h, w = alpha.shape
    foreground = alpha.astype(np.float32, copy=True)
    reliable = alpha >= 0.995
    binary = alpha >= 0.5
    outline_ridge = ndi.binary_dilation(binary, border_value=0) != ndi.binary_erosion(binary, border_value=1)
    if outline_ridge.any():
        distance = ndi.distance_transform_edt(~outline_ridge)
        outline = (np.exp(-0.5 * (distance / 2.0)**2) * (distance <= 6)).astype(np.float32)
    else:
        outline = np.zeros((h, w), np.float32)
    allowed = reliable & (outline <= 0.01)
    internal = np.zeros((h, w), np.float32)
    balanced_maps, segments = [], []
    candidates = []
    for scale_index, sigma in enumerate(SCALES):
        strength, nx, ny, coherence = _tensor_normals(rgb, sigma)
        ridge = _nms(strength, nx, ny) & (strength >= 0.018 / np.sqrt(sigma)) & (coherence >= 0.45) & allowed
        band, balanced, scale_segments, labels = _band_and_balance(ridge, allowed, strength, sigma)
        internal = np.maximum(internal, band)
        balanced_maps.append(balanced)
        segments.extend(scale_segments)
        # Only finest-scale reference normals define profiles; other scales
        # remain contribution evidence and cannot duplicate width samples.
        if scale_index == 0:
            ys, xs = np.nonzero(labels)
            for y, x in zip(ys, xs):
                candidates.append({"kind": "internal", "segment": int(labels[y, x]),
                                   "center": [float(x), float(y)], "normal": [float(nx[y, x]), float(ny[y, x])],
                                   "scale": sigma, "edge_strength": float(strength[y, x])})
    if outline_ridge.any():
        strength, nx, ny, coherence = _tensor_normals(alpha, 0.8)
        outline_labels, _ = ndi.label(outline_ridge, np.ones((3, 3), dtype=np.uint8))
        ridge = outline_ridge & _nms(strength, nx, ny) & (strength >= 0.02) & (coherence >= 0.45)
        ys, xs = np.nonzero(ridge)
        for y, x in zip(ys, xs):
            candidates.append({"kind": "outline", "segment": int(outline_labels[y, x]),
                               "center": [float(x), float(y)], "normal": [float(nx[y, x]), float(ny[y, x])],
                               "scale": 0.8, "edge_strength": float(strength[y, x])})
    ordered = _candidate_order(candidates)
    profiles, selected_centers = [], []
    proposed, rejected = 0, Counter()
    proposed_by_kind, selected_by_kind = Counter(), Counter()
    present_kinds = {p["kind"] for p in candidates}
    kind_budget = {"internal": 64 if "outline" in present_kinds else MAX_PROFILES,
                   "outline": 32 if "internal" in present_kinds else MAX_PROFILES}
    linear = srgb_to_linear(rgb)
    # Target validation happens once. Native renders later use this fixed list.
    for candidate in ordered:
        if selected_by_kind[candidate["kind"]] >= kind_budget[candidate["kind"]]:
            continue
        center = np.array(candidate["center"])
        if any(np.linalg.norm(center - old) < 7 for old in selected_centers):
            continue
        config = dict(candidate, id=f"{candidate['kind']}_{int(center[1]):04d}_{int(center[0]):04d}",
                      radius=PROFILE_RADIUS, samples=PROFILE_SAMPLES)
        metric = _profile_metrics_linear(linear, [config])[0]
        proposed += 1
        proposed_by_kind[candidate["kind"]] += 1
        if metric["valid"]:
            config["reference_width"] = metric["width"]
            config["reference_contrast"] = metric["contrast"]
            profiles.append(config)
            selected_by_kind[candidate["kind"]] += 1
            selected_centers.append(center)
            if len(profiles) >= MAX_PROFILES:
                break
        else:
            rejected[metric["reason"]] += 1
        if proposed >= 768:
            break
    if profiles:
        roi_profile = next((p for p in profiles if p["kind"] == "internal"), profiles[0])
        cx, cy = roi_profile["center"]
        roi = [max(0, int(cx) - 24), max(0, int(cy) - 24), min(w, int(cx) + 25), min(h, int(cy) + 25)]
        roi_basis = "first_validated_reference_normal_profile"
    else:
        ys, xs = np.nonzero((internal > 0.05) | (outline > 0.05))
        if len(xs):
            roi = [max(0, int(xs.min()) - 12), max(0, int(ys.min()) - 12),
                   min(w, int(xs.max()) + 13), min(h, int(ys.max()) + 13)]
        else:
            roi = [0, 0, w, h]
        roi_basis = "reference_evidence_bbox_or_full_image"
    metadata = {"encoding": "display_PNG_RGB", "profile_encoding": "display_sRGB_to_linear_RGB",
                "label_semantics": "label_free_relative_RGB_edge_support; alpha_outline_separate",
                "scales_px": list(SCALES), "foreground_alpha_source": "original_PNG_AA_coverage",
                "reliable_alpha_threshold": 0.995, "internal_pixels": int((internal > 0).sum()),
                "outline_pixels": int((outline > 0).sum()), "reliable_pixels": int(reliable.sum()),
                "segments": len(segments), "balanced_active_scales": sum(bool(m.sum() > 0) for m in balanced_maps),
                "profiles_proposed": proposed, "profiles_valid": len(profiles),
                "profiles_proposed_by_kind": dict(proposed_by_kind), "profiles_valid_by_kind": dict(selected_by_kind),
                "profile_kind_budget": kind_budget,
                "profiles_valid_rate": len(profiles) / proposed if proposed else 0.0,
                "profile_rejections": dict(rejected), "profile_max": MAX_PROFILES,
                "profile_radius_px": PROFILE_RADIUS, "profile_samples": PROFILE_SAMPLES,
                "roi_basis": roi_basis, "width_validation": "analytic_slanted_and_curved_fixture_required",
                "profile_validity_is_conditional": True}
    return {"internal_band": internal, "outline_band": outline, "foreground": foreground,
            "reliable": reliable, "nonband": (1 - np.maximum(internal, outline)).astype(np.float32),
            "balanced_maps": balanced_maps, "segments": segments, "profiles": profiles,
            "roi": roi, "metadata": metadata}
